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

import hashlib
import os
import random
import sys
from typing import TYPE_CHECKING, Callable, Protocol, Sequence

from sidira_simulator.schemas.benchmark import BenchmarkCase, GroundTruth
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.schemas.scoring import (
    BenchmarkBaseline,
    BenchmarkCaseResult,
    BenchmarkRunResult,
    NullIntegrityCertificate,
)
from sidira_simulator.services.null_integrity import certify_null_integrity
from sidira_simulator.services.statistics import bootstrap_percentile_ci, spearman_rho

if TYPE_CHECKING:
    # Engine-only types — imported for annotations ONLY, never at runtime. The
    # core scoring path (run_blind_eval) stays engine-free-importable; the live
    # engine is built solely inside the gated `score_with_engine` below.
    from sidira_simulator.schemas.persona import PersonaPack
    from sidira_simulator.schemas.simulation import SimulationResult

# A blind predictor maps one renderable case → one signed predicted effect
# (sign = direction, value = rank material). It MUST NOT read case.ground_truth.
Predictor = Callable[[BenchmarkCase], float]

# The Upworthy metric is CTR — the engine must report a "ctr" lift for a case to
# be scorable. A run that comes back with a different metric_name (or no lift) is
# a wiring error, not a silent zero: the case is DROPPED and surfaced.
_ENGINE_METRIC_NAME = "ctr"

# The Upworthy headline A/B is a symmetric, paired comparison: half the panel
# sees the control headline, half the proposed one (#90 paired-seed invariant at
# f=0.5). The benchmark always drives the engine at this locked fraction.
_ENGINE_TREATMENT_FRACTION = 0.5

# The CTR click label for the Upworthy headline card: clicking the promoted story
# headline opens the article. The CTR elicitor defaults this to "click it" when a
# hypothesis omits it; we name it explicitly so the on-screen ask matches the
# headline-card click being benchmarked (the metric is "reader clicks the card").
_ENGINE_CTR_CLICK_LABEL = "open the story"


# The on-screen CTR decision moment for a promoted-headline card. ARM-NEUTRAL by
# design (codex P1): the SAME CTR Hypothesis drives BOTH the treatment and control
# arms, and the composer renders each arm's OWN headline into the per-arm
# standalone state view. So the decision_point must NOT name a specific headline —
# baking the proposed (treatment) headline in here would ask the CONTROL agent
# about the treatment copy, contaminating the paired treatment−control lift. It
# only describes the generic click moment; the headline the agent reacts to is the
# one rendered for THAT agent's arm.
_ENGINE_CTR_DECISION_POINT = (
    "A promoted story card is on your feed right now; tapping its headline " "opens the article."
)


def _ctr_hypothesis_for_case(case: BenchmarkCase) -> Hypothesis:
    """Build a VALIDATED CTR hypothesis for a case (metric forced to "ctr").

    Takes the case's hypothesis verbatim and adds the CTR metric fields the
    registry requires — `decision_point` (the on-screen click moment) and the
    click label — then re-runs the `Hypothesis` validator via `model_validate`.
    `model_copy(update=...)` is deliberately NOT used: it bypasses the validator,
    so a hypothesis missing a required CTR field (e.g. `decision_point`) would
    reach the live engine and run CTR elicitation on an empty moment (codex P2).
    Re-validating makes a missing field fail LOUD here instead of silently
    scoring malformed click intent.

    The decision_point is ARM-NEUTRAL (`_ENGINE_CTR_DECISION_POINT`): the same
    hypothesis drives both arms and each arm's own headline is rendered into its
    per-arm state view by the composer, so the decision_point must not name a
    specific headline (codex P1) — that would expose the control arm to the
    treatment copy and contaminate the lift.

    BLIND: every added field is derived from `case.hypothesis` ONLY —
    `case.ground_truth` is never read.
    """
    data = case.hypothesis.model_dump()
    data.update(
        {
            "metric_name": _ENGINE_METRIC_NAME,
            "decision_point": _ENGINE_CTR_DECISION_POINT,
            "conversion_action_label": _ENGINE_CTR_CLICK_LABEL,
        }
    )
    # model_validate re-runs the Hypothesis validator (required CTR fields), unlike
    # model_copy(update=...) which would skip it.
    return Hypothesis.model_validate(data)


class CaseRunner(Protocol):
    """The injected per-case engine call (dependency-injection seam, §4 cell).

    A `CaseRunner` runs ONE benchmark case through the engine and returns its
    `SimulationResult`. The real implementation wraps `SimulationRunner.run(...)`
    (async → sync) and is built only inside the gated `score_with_engine`; tests
    inject a FAKE that records its kwargs and returns a canned result, so the
    eval core is exercised with NO live LLM.

    The contract is deliberately keyword-only on `(capability, hypothesis)` plus
    run params: the eval core derives `capability` + `hypothesis` from the case's
    `(capability, hypothesis)` ONLY — never from `case.ground_truth` — so the
    structural blindness of the predictor is provable from this signature.
    """

    def __call__(
        self,
        *,
        capability: object,
        hypothesis: object,
        treatment_fraction: float,
        run_seed: int,
        population_size: int,
        max_agents: int | None,
        model_id: str | None,
    ) -> "SimulationResult": ...


def _case_run_seed(case_id: str, seed: int) -> int:
    """Deterministic per-case run seed derived from `(case_id, base seed)`.

    A stable SHA-256 digest of the case id (NOT Python's process-salted `hash()`)
    is XOR-mixed with the base seed, so every case gets a distinct-but-reproducible
    engine seed and the same `(case_id, seed)` ALWAYS yields the same seed across
    runs / PYTHONHASHSEED values. This is what makes the per-case engine call (and
    its cache) deterministic for a fixed base seed.
    """
    digest = hashlib.sha256(case_id.encode("utf-8")).digest()
    # 63-bit unsigned value so the XOR with `seed` stays a non-negative int.
    case_component = int.from_bytes(digest[:8], "big") & ((1 << 63) - 1)
    return case_component ^ (seed & ((1 << 63) - 1))


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
    # Per-case records (in input order, scored AND dropped) so a downstream
    # reporting layer can stratify without re-running a stochastic predictor.
    case_results: list[BenchmarkCaseResult] = []
    for case in cases:
        try:
            effect = float(predictor(case))
        except Exception:
            # No silent truncation: a predictor failure drops the case but is
            # reported, never folded into the denominator as a 0.
            dropped_case_ids.append(case.case_id)
            case_results.append(
                BenchmarkCaseResult(
                    case_id=case.case_id,
                    source=case.source,
                    observed_lift=case.ground_truth.observed_lift,
                    dropped=True,
                )
            )
            continue
        scored_cases.append(case)
        predictions.append(effect)
        actuals.append(case.ground_truth.observed_lift)
        case_results.append(
            BenchmarkCaseResult(
                case_id=case.case_id,
                source=case.source,
                observed_lift=case.ground_truth.observed_lift,
                prediction=effect,
            )
        )

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
            case_results=case_results,
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
        case_results=case_results,
        seed=seed_for_run,
    )


# ── Engine-eval CORE (testable, engine-free-importable, dependency-injected) ───
#
# This is the §4 "engine cell": it drives an INJECTED per-case runner as the blind
# predictor and scores it through `run_blind_eval`. It imports NOTHING from the
# live engine (the `CaseRunner` is injected, the engine types are TYPE_CHECKING-
# only), so it is exercised in tests with a fake runner and no live LLM. Only the
# gated `score_with_engine` below builds the real `SimulationRunner`.


def eval_engine_blind(
    cases: Sequence[BenchmarkCase],
    *,
    runner: CaseRunner,
    customer_id: str,
    model_id: str | None,
    population_size: int,
    max_agents: int | None,
    seed: int,
    n_permutations: int = 1000,
    n_resamples: int = _BOOTSTRAP_RESAMPLES,
) -> BenchmarkRunResult:
    """Score the engine (an injected `CaseRunner`) as the blind predictor (§4).

    Builds a blind predictor closure around `runner` and hands it to
    `run_blind_eval`. The closure is the §4 "engine cell": for each case it runs
    the engine ONCE and returns the predicted CTR delta.

    STRUCTURAL BLINDNESS (the load-bearing invariant). The predictor derives the
    engine's `run(...)` args ONLY from `case.capability` and `case.hypothesis`
    (with `metric_name` forced to "ctr") — it NEVER reads `case.ground_truth`. The
    engine is therefore label-invariant BY CONSTRUCTION: the answer key is not an
    input to the run, so re-running on a scrambled-label copy of a case would
    produce the IDENTICAL result. We exploit that by running the engine once per
    case and CACHING the prediction keyed by `case_id` (NOT by the scrambled
    labels). The null-cert `predict_fn` then returns the cached per-case value
    independent of the shuffle.

    Why this discharges the null-cert TRUST BOUNDARY (and is NOT the "frozen-vector
    stub" the cert docstring warns against): the cert cannot, in principle,
    distinguish an honest label-independent predictor from a leaking one disguised
    as a constant closure — both return a fixed vector under the shuffle. Here the
    blindness is STRUCTURAL and PROVABLE, not asserted: the predictor's only inputs
    are `(capability, hypothesis)`, so caching is EXACT (a re-run is byte-identical),
    and a leaking predictor is impossible by construction because `ground_truth` is
    never passed to `runner`. We mark the resulting certificate metadata via the
    caller's reporting as `structurally_blinded` — the run's certifying cert PASSes
    because the cached, label-independent predictions center the scrambled-label
    null at chance, exactly as the §4 protocol requires.

    Per-case scoring contract:
      * `hypothesis = _ctr_hypothesis_for_case(case)` (metric forced to "ctr" with
        a VALIDATED CTR decision_point + click label — `model_validate`, not
        `model_copy`, so the registry's required CTR fields are enforced),
        `treatment_fraction = 0.5`, `run_seed = _case_run_seed(case.case_id, seed)`.
      * The engine returns a `SimulationResult`; we REQUIRE
        `result.metric_name == "ctr"` AND `result.metric_lift_pp is not None`,
        else the predictor RAISES — which `run_blind_eval` records as a DROPPED
        case (surfaced in `n_dropped` / `dropped_case_ids`), NEVER zero-filled.
      * Unit conversion: the engine reports `metric_lift_pp` in PERCENTAGE POINTS;
        `GroundTruth.observed_lift` is a RAW CTR probability delta, so the
        predicted effect is `metric_lift_pp / 100.0` to match units.

    The cache makes the predictor deterministic for a fixed `seed` and means the
    expensive engine call happens exactly once per case (not once per case per
    null permutation), which is what makes the faithful §4 re-run affordable.
    """
    # Run-once-per-case cache keyed by case_id. The cached value is the predicted
    # CTR delta (raw probability units). Built lazily by the predictor closure;
    # the null `predict_fn` reads it back keyed ONLY by case_id (never by label).
    prediction_cache: dict[str, float] = {}

    def _predict(case: BenchmarkCase) -> float:
        if case.case_id in prediction_cache:
            return prediction_cache[case.case_id]
        # Force the CTR metric on the hypothesis (with the required, VALIDATED CTR
        # decision_point + click label); everything else is taken verbatim from the
        # case's (capability, hypothesis). ground_truth is NOT referenced —
        # structural blindness.
        ctr_hypothesis = _ctr_hypothesis_for_case(case)
        result = runner(
            capability=case.capability,
            hypothesis=ctr_hypothesis,
            treatment_fraction=_ENGINE_TREATMENT_FRACTION,
            run_seed=_case_run_seed(case.case_id, seed),
            population_size=population_size,
            max_agents=max_agents,
            model_id=model_id,
        )
        if result.metric_name != _ENGINE_METRIC_NAME or result.metric_lift_pp is None:
            # No scorable CTR lift — DROP the case honestly (run_blind_eval turns a
            # raised predictor into an n_dropped entry). Never impute a 0 effect.
            raise ValueError(
                f"engine returned no scorable CTR lift for case {case.case_id} "
                f"(metric_name={result.metric_name!r}, "
                f"metric_lift_pp={result.metric_lift_pp!r})"
            )
        # pp → raw CTR delta to match GroundTruth.observed_lift's units.
        effect = result.metric_lift_pp / 100.0
        prediction_cache[case.case_id] = effect
        return effect

    return run_blind_eval(
        cases,
        _predict,
        seed=seed,
        n_permutations=n_permutations,
        n_resamples=n_resamples,
    )


# ── Gated live-engine entry point (NEVER runs in CI / under pytest) ────────────
#
# The real engine path requires live LLM calls and a persona panel, so it is the
# only place that builds the production `SimulationRunner`. The eval CORE above
# (eval_engine_blind) and the scoring path (run_blind_eval) never import the
# engine; this function does, lazily, AFTER the pytest/CI guard.


def score_with_engine(
    cases: Sequence[BenchmarkCase] | None = None,
    *,
    persona_pack: "PersonaPack | None" = None,
    customer_id: str = "benchmark",
    model_id: str | None = None,
    population_size: int = 10,
    max_agents: int | None = None,
    seed: int = 0,
    n_permutations: int = 1000,
    n_resamples: int = _BOOTSTRAP_RESAMPLES,
) -> BenchmarkRunResult:
    """GATED real-engine entry point — refuses to run under pytest / CI.

    Constructs the production `SimulationRunner` + uses the supplied real
    `PersonaPack`, wraps `SimulationRunner.run(...)` as a synchronous `CaseRunner`,
    and delegates to `eval_engine_blind`. This is the ONLY place the live engine is
    built; it needs live LLM keys at runtime, so it MUST NOT execute in CI / under
    pytest. The engine-free eval core is fully exercised in tests with a fake
    runner; this wrapper only adds the live wiring.

    Raises RuntimeError under pytest/CI (the guard), and ValueError if
    `cases`/`persona_pack` are missing when invoked for real.
    """
    # Refuse under pytest AND under CI — same guard discipline as
    # `upworthy_archive.fetch_upworthy_archive`. The pytest checks catch the test
    # harness; the CI check catches a script/helper running in CI OUTSIDE pytest
    # (the standard `CI` env var is truthy on GitHub Actions / GitLab / …), so an
    # automated job can never accidentally spend on live LLM calls (codex P2).
    if (
        "PYTEST_CURRENT_TEST" in os.environ
        or "pytest" in sys.modules
        or os.environ.get("CI", "").strip().lower() in {"1", "true", "yes"}
    ):
        raise RuntimeError(
            "score_with_engine is a gated live-LLM entry point and must not run "
            "under pytest / CI. Use eval_engine_blind with an injected fake runner "
            "(or run_blind_eval with a mock predictor) in tests; invoke this only "
            "in a deliberate real-data benchmark run with live LLM keys."
        )
    if not cases:
        raise ValueError("score_with_engine requires at least one BenchmarkCase")
    if persona_pack is None:
        raise ValueError("score_with_engine requires a real PersonaPack panel")

    import asyncio

    from sidira_simulator.services.simulation_runner import SimulationRunner

    def _run_case(
        *,
        capability: object,
        hypothesis: object,
        treatment_fraction: float,
        run_seed: int,
        population_size: int,
        max_agents: int | None,
        model_id: str | None,
    ) -> "SimulationResult":
        # Drive the real engine for one case (async → sync). A FRESH
        # SimulationRunner is built PER CASE: the runner owns an asyncio.Semaphore
        # bound to the event loop it first runs under, so reusing one runner across
        # the repeated `asyncio.run(...)` calls (one new loop per case) would bind
        # the semaphore to the first loop and break agent materialization on every
        # later case (codex P1). A fresh runner per case keeps each run self-
        # contained in its own loop. The benchmark panel is a fixed pre-registered
        # fixture, so feature_pack_version is a constant label, not a customer
        # artifact version.
        sim_runner = SimulationRunner()
        simulation = asyncio.run(
            sim_runner.run(
                customer_id=customer_id,
                persona_pack=persona_pack,
                capability=capability,  # type: ignore[arg-type]
                feature_pack_version=f"benchmark:{persona_pack.version}",
                hypothesis=hypothesis,  # type: ignore[arg-type]
                population_size=population_size,
                run_seed=run_seed,
                max_agents=max_agents,
                treatment_fraction=treatment_fraction,
                model_id=model_id,
            )
        )
        return simulation.result

    return eval_engine_blind(
        cases,
        runner=_run_case,
        customer_id=customer_id,
        model_id=model_id,
        population_size=population_size,
        max_agents=max_agents,
        seed=seed,
        n_permutations=n_permutations,
        n_resamples=n_resamples,
    )
