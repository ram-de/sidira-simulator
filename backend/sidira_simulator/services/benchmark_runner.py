"""Tier-0 blind-eval runner (ablation-protocol §4 / §5, ticket #222).

The #228 adapter (`services.benchmark_adapter`) turns an archived Upworthy test
into `BenchmarkCase`s — the SAME `(Capability, Hypothesis)` shape production
builds, each carrying its measured `GroundTruth`. This module is the RUNNER that
actually evaluates a predictor against those real outcomes: it drives the
predictor BLIND over each case, scores the predicted-vs-observed effect across
cases, and ships the §4 null-integrity certificate alongside the result.

What "blind" means (the trust boundary). The predictor takes a `BenchmarkCase`
and returns ONE signed predicted effect — its SIGN is the predicted direction,
its VALUE is the rank material. A blind predictor MUST derive that effect from
the case's `(capability, hypothesis)` ONLY; it must NOT read
`case.ground_truth`, which is the held-out answer key. The runner cannot
syntactically forbid a predictor from peeking, so it PROVES blindness
statistically via the null-integrity certificate: it re-runs the predictor on
scrambled-label copies of the cases (§4), and a predictor that read
`ground_truth` tracks the scramble and VOIDs the run. An honest predictor
ignores `ground_truth`, so its predictions are invariant under the scramble and
the null collapses to chance → PASS.

Scoring (ablation-protocol §4–§5):
- PRIMARY endpoint: Spearman rank-ρ of predicted vs observed effect (§5 l.79).
- Secondary: direction-accuracy (share of cases with matching sign).
- Paired-across-cases bootstrap CI on the per-case direction delta vs the
  always-flat baseline (§4 l.69), so the gain is a paired statistic.
- The ALWAYS-FLAT and RANDOM-RANK baselines printed alongside (§4 l.72), so a
  gain is read against the real floor, not zero.

Honesty (no silent truncation, §1/§2/§4): a predictor failure or a case with no
scorable label is DROPPED and surfaced (`n_dropped` + `dropped_case_ids`), never
quietly removed from the denominator. The magnitude stays directional/relative
pre-calibration (#221 shrinkage is still identity) — `rank_rho` /
`direction_accuracy` are the trustworthy reads; an uncalibrated effect size is
never presented as truth.

Dependency injection (testability). The predictor is an INJECTED callable, so
unit tests use a deterministic mock (no live LLM). The real engine
(`SimulationRunner`) is wired ONLY behind `score_with_engine`, a gated entry
point that refuses to run under pytest / CI (it would require live LLM calls and
a persona panel). Nothing in the core scoring path imports the engine.
"""

from __future__ import annotations

import os
import random
import sys
from typing import Callable, Sequence

from sidira_simulator.schemas.benchmark import BenchmarkCase, GroundTruth
from sidira_simulator.schemas.scoring import (
    BenchmarkBaseline,
    BenchmarkRunResult,
    NullIntegrityCertificate,
)
from sidira_simulator.services.null_integrity import certify_null_integrity
from sidira_simulator.services.statistics import bootstrap_percentile_ci, spearman_rho

# A blind predictor maps one renderable case → one signed predicted effect
# (sign = direction, value = rank material). It MUST NOT read case.ground_truth.
Predictor = Callable[[BenchmarkCase], float]

# Arbitrary integer XOR mask used to derive the runner's bootstrap RNG seed from
# the caller's seed, so the per-case direction-delta bootstrap stream cannot
# collide with the null-permutation stream (which mixes a DIFFERENT mask in
# null_integrity.py) nor the scoring bootstrap. Same defense-in-depth discipline.
_RUNNER_SEED_MIX = 0x42_45_4E_43_48_5F_52  # "BENCH_R" as hex bytes

# Bootstrap resamples for the paired direction-delta CI. Matches the 1000-resample
# convention in scoring.py / statistics.py.
_BOOTSTRAP_RESAMPLES = 1000


def _sign(x: float) -> int:
    """Sign of `x` with an explicit zero class (matches null_integrity._sign)."""
    if x > 0.0:
        return 1
    if x < 0.0:
        return -1
    return 0


def _with_scrambled_label(case: BenchmarkCase, scrambled_lift: float) -> BenchmarkCase:
    """A copy of `case` whose ground-truth effect is replaced by `scrambled_lift`.

    Used to build the faithful §4 null `predict_fn`: the runner hands the
    predictor cases whose ANSWER KEY has been shuffled. An honest predictor
    ignores `ground_truth` and returns the same effect regardless; a predictor
    that peeks at `ground_truth.observed_lift` (or `.winner`) tracks the shuffle
    and is correctly VOIDed.

    The whole `ground_truth` is rebuilt so a peeking predictor cannot dodge the
    scramble by reading `winner`, `control_metric`, or `treatment_metric`: the
    winner is re-derived from the scrambled lift's sign, and the metrics are set
    to a synthetic (control, treatment) pair whose delta IS the scrambled lift,
    so every ground-truth field is consistent with the shuffled label.
    """
    gt = case.ground_truth
    if scrambled_lift > 0.0:
        winner = "treatment"
    elif scrambled_lift < 0.0:
        winner = "control"
    else:
        winner = "tie"
    # Re-anchor the metrics on the control's value so both stay >= 0 (the schema
    # forbids negatives) and treatment − control == scrambled_lift exactly.
    control_metric = gt.control_metric
    treatment_metric = control_metric + scrambled_lift
    if treatment_metric < 0.0:
        # A large negative scrambled lift could push treatment below 0; re-anchor
        # on treatment instead so neither metric is negative and the delta holds.
        treatment_metric = gt.treatment_metric
        control_metric = treatment_metric - scrambled_lift
    scrambled_gt = GroundTruth(
        metric_name=gt.metric_name,
        control_metric=control_metric,
        treatment_metric=treatment_metric,
        observed_lift=scrambled_lift,
        winner=winner,
    )
    return case.model_copy(update={"ground_truth": scrambled_gt})


def _always_flat_baseline(actuals: Sequence[float]) -> BenchmarkBaseline:
    """The "nothing moves" floor: predict 0 effect for every case.

    Direction-accuracy is the share of cases whose actual effect is itself flat
    (sign 0). Rank-ρ is 0.0 — a constant prediction has no rank variation, which
    `spearman_rho` returns as 0.0 (the honest "no monotone signal" answer).
    """
    n = len(actuals)
    flat_correct = sum(1 for a in actuals if _sign(a) == 0) / n
    return BenchmarkBaseline(name="always_flat", direction_accuracy=flat_correct, rank_rho=0.0)


def _random_rank_baseline(actuals: Sequence[float]) -> BenchmarkBaseline:
    """The chance floor: marginal-expected direction-accuracy under a random
    relabeling, with rank-ρ 0.0 in expectation.

    A no-information predictor reuses the actuals' own sign marginals (it has no
    extra signal), so the expected accuracy of scoring a uniformly random
    PERMUTATION of those signs against the actuals is the collision probability
    Σ_s (n_s / n)². This is exactly the closed-form chance baseline the
    null-integrity certificate brackets (`_marginal_chance_accuracy`), so the
    random-rank floor here and the certificate's gate read identically. Rank-ρ is
    0.0 in expectation under any relabeling (permuting labels mean-centers ρ).
    """
    n = len(actuals)
    counts: dict[int, int] = {-1: 0, 0: 0, 1: 0}
    for a in actuals:
        counts[_sign(a)] += 1
    expected_acc = sum((counts[s] / n) ** 2 for s in (-1, 0, 1))
    return BenchmarkBaseline(name="random_rank", direction_accuracy=expected_acc, rank_rho=0.0)


def run_blind_eval(
    cases: Sequence[BenchmarkCase],
    predictor: Predictor,
    *,
    seed: int,
    n_permutations: int = 1000,
    n_resamples: int = _BOOTSTRAP_RESAMPLES,
) -> BenchmarkRunResult:
    """Score a BLIND predictor over adapter-produced cases (§4–§5).

    For each case the runner calls `predictor(case)` to get the predicted signed
    effect — BLIND: the predictor must derive it from `(capability, hypothesis)`
    and must not read `case.ground_truth`. A predictor that raises is DROPPED and
    surfaced in `n_dropped` / `dropped_case_ids` (no silent truncation); a case
    whose ground-truth metric is missing is likewise dropped.

    Returns a `BenchmarkRunResult` carrying:
      * `rank_rho` (PRIMARY, §5) and `direction_accuracy`,
      * the paired-across-cases bootstrap CI on the per-case direction delta vs
        the always-flat baseline (§4 l.69),
      * the always-flat + random-rank baselines (§4 l.72),
      * the null-integrity certificate (§4) built from the FAITHFUL re-run: the
        predictor is re-applied to scrambled-label copies of the cases, so a
        label-peeking predictor VOIDs the run.

    The certificate's `predict_fn` is constructed HERE (the runner owns the
    genuine re-run, per `certify_null_integrity`'s TRUST BOUNDARY note) — it is
    not a frozen-vector stub. If the certificate does not PASS, `void=True` and
    the scores are leakage-suspect.

    Raises ValueError on an empty `cases` (nothing to score is a caller bug).
    """
    if not cases:
        raise ValueError("run_blind_eval requires at least one case")

    # ── Blind pass: predict each case, dropping (and surfacing) failures. ──
    scored_cases: list[BenchmarkCase] = []
    predictions: list[float] = []
    actuals: list[float] = []
    dropped_case_ids: list[str] = []
    for case in cases:
        try:
            effect = float(predictor(case))
        except Exception:
            # No silent truncation: a predictor failure drops the case but is
            # reported, never folded into the denominator as a 0.
            dropped_case_ids.append(case.case_id)
            continue
        scored_cases.append(case)
        predictions.append(effect)
        actuals.append(case.ground_truth.observed_lift)

    n = len(scored_cases)
    seed_for_run = seed
    if n == 0:
        # Every case dropped — nothing scorable. Honest empty result (void, no
        # certificate to compute since there are no predictions/actuals).
        return BenchmarkRunResult(
            n_cases=0,
            n_dropped=len(dropped_case_ids),
            dropped_case_ids=dropped_case_ids,
            void=True,
            void_reason="No case produced a prediction (every case dropped).",
            seed=seed_for_run,
        )

    # ── Scores over the real labels. ──
    rank_rho = spearman_rho(predictions, actuals)
    direction_accuracy = sum(1 for p, a in zip(predictions, actuals) if _sign(p) == _sign(a)) / n

    baselines = [_always_flat_baseline(actuals), _random_rank_baseline(actuals)]

    # ── Paired-across-cases bootstrap CI on the per-case direction delta vs the
    # always-flat baseline (§4 l.69). Per case, the delta is
    # (1 if engine sign correct else 0) − (1 if flat sign correct else 0); the
    # bootstrap resamples THESE paired deltas, so the CI is a paired statistic. ──
    per_case_deltas = [
        (1 if _sign(p) == _sign(a) else 0) - (1 if _sign(a) == 0 else 0)
        for p, a in zip(predictions, actuals)
    ]
    direction_delta = sum(per_case_deltas) / n
    direction_delta_ci: tuple[float, float] | None = None
    if n_resamples >= 1:
        boot_rng = random.Random(seed ^ _RUNNER_SEED_MIX)
        direction_delta_ci = bootstrap_percentile_ci(
            per_case_deltas,
            lambda sample: sum(sample) / len(sample),
            n_resamples=n_resamples,
            rng=boot_rng,
        )

    # ── Faithful §4 null `predict_fn`: re-run the predictor on scrambled-label
    # copies of the cases. The runner OWNS this re-run (TRUST BOUNDARY in
    # certify_null_integrity): it is the genuine predictor over cases whose answer
    # key is shuffled, NOT a frozen-vector stub. An honest blind predictor ignores
    # ground_truth and reproduces the observed predictions; a peeking predictor
    # tracks the shuffle and VOIDs. ──
    def predict_fn(scrambled_actuals: Sequence[float]) -> list[float]:
        if len(scrambled_actuals) != n:
            raise ValueError(f"predict_fn got {len(scrambled_actuals)} labels, expected {n}")
        out: list[float] = []
        for case, lift in zip(scored_cases, scrambled_actuals):
            out.append(float(predictor(_with_scrambled_label(case, float(lift)))))
        return out

    certificate: NullIntegrityCertificate = certify_null_integrity(
        predictions,
        actuals,
        n_permutations=n_permutations,
        seed=seed,
        predict_fn=predict_fn,
    )

    void = not certificate.passed
    void_reason = certificate.void_reason or certificate.caveat if void else None

    return BenchmarkRunResult(
        rank_rho=rank_rho,
        direction_accuracy=direction_accuracy,
        direction_delta_vs_flat=direction_delta,
        direction_delta_ci=direction_delta_ci,
        baselines=baselines,
        certificate=certificate,
        void=void,
        void_reason=void_reason,
        n_cases=n,
        n_dropped=len(dropped_case_ids),
        dropped_case_ids=dropped_case_ids,
        seed=seed_for_run,
    )


# ── Gated live-engine entry point (NEVER runs in CI / under pytest) ────────────
#
# The real engine path (SimulationRunner → ConversionLiftResult.lift_pp as the
# predicted effect) requires live LLM calls and a persona panel, so it is OUT OF
# SCOPE to RUN here and is wired only behind this guarded seam. The core scoring
# path above never imports the engine; only this function does, lazily.


def score_with_engine(*args: object, **kwargs: object) -> BenchmarkRunResult:
    """GATED real-engine entry point — refuses to run under pytest / CI.

    Wires the production `SimulationRunner` as the blind predictor: each case's
    `(capability, hypothesis)` flows through `run(...)` and the resulting
    `SimulationResult.conversion_lift_pp` (§3a paired treatment−control delta) is
    the predicted effect. This is the §4 "engine cell" — but it needs live LLM
    calls and a real persona panel, so it MUST NOT execute in CI / under pytest.

    Deferred (documented seam, not run here): the live-LLM real-data run. This
    function asserts the guard, documents the wiring, and raises until invoked
    deliberately outside the test harness with a real persona pack + engine. The
    statistics it would feed into (`run_blind_eval`) are fully mock-tested.
    """
    if "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules:
        raise RuntimeError(
            "score_with_engine is a gated live-LLM entry point and must not run "
            "under pytest / CI. Use run_blind_eval with an injected mock predictor "
            "in tests; invoke this only in a deliberate real-data benchmark run."
        )
    raise NotImplementedError(
        "Live-LLM real-data benchmark run is deferred (ticket #222 follow-up). "
        "The blind-eval seam is in place: build a predictor that drives "
        "SimulationRunner.run(...) per case and returns "
        "SimulationResult.conversion_lift_pp, then pass it to run_blind_eval. "
        "Wiring the real engine + persona panel and executing it is out of scope "
        "for this PR (no live-behavior change)."
    )
