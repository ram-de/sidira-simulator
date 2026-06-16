"""Tests for the Tier-0 blind-eval runner (#222, ablation-protocol §4–§5).

The runner scores a BLIND predictor over adapter-produced `BenchmarkCase`s and
ships the null-integrity certificate. The load-bearing assertions:

- a PERFECT blind predictor → direction-accuracy + rank-ρ ≈ 1, cert PASSes;
- a NOISE blind predictor → cert PASSes (it is label-independent) and its result
  beats neither the floor convincingly (non-significant p-value);
- a LEAKING predictor (peeks at `case.ground_truth`) → cert VOIDs the run;
- the always-flat + random-rank baselines are computed correctly;
- the paired direction-delta bootstrap CI is deterministic under a fixed seed;
- a failing predictor drops the case honestly (no silent truncation);
- rank-ρ is the reported PRIMARY endpoint.

The fixture is SYNTHETIC: there is no Upworthy archive checked into the repo (the
real-data + live-LLM run is gated and deferred), so cases are produced through
the real `upworthy_test_to_cases` adapter from a hand-built `UpworthyTest`. The
honest predictors read the TREATMENT HEADLINE (the rendered proposed state) — a
legitimate blind signal — never `case.ground_truth`.
"""

from __future__ import annotations

import hashlib
import random
import re

import pytest

from sidira_simulator.schemas.benchmark import (
    BenchmarkCase,
    UpworthyTest,
    UpworthyVariant,
)
from sidira_simulator.services.benchmark_adapter import upworthy_test_to_cases
from sidira_simulator.services.benchmark_runner import (
    Predictor,
    run_blind_eval,
    score_with_engine,
)

# How many challengers (= scored cases) the fixture carries. Must clear the
# null-integrity certification floor (_MIN_EXPERIMENTS = 8) so a clean cell can
# actually PASS rather than being marked underpowered.
_N_CHALLENGERS = 12


# ── Fixture: a synthetic Upworthy test → adapter-produced cases ────────────────


def _build_cases() -> list[BenchmarkCase]:
    """A synthetic clickability test enumerated through the real adapter.

    The baseline is variant 0; each challenger's headline embeds an
    ``EFFECT=<n>`` token whose value tracks that challenger's true CTR delta vs
    the baseline. The honest predictors parse this token from the RENDERED
    treatment headline — a blind read of the proposed state, not the answer key —
    which is what makes "perfect" honest rather than leaking.
    """
    base_clicks = 120
    impressions = 10_000
    baseline = UpworthyVariant(
        headline="Baseline story headline",
        clicks=base_clicks,
        impressions=impressions,
        eyecatcher_id=None,
    )
    challengers: list[UpworthyVariant] = []
    for i in range(1, _N_CHALLENGERS + 1):
        # Spread clicks above and below the baseline so the sign distribution is
        # mixed (some +, some −, with an exact tie at the midpoint) — exercises
        # the three-way sign logic and a non-trivial rank ordering.
        clicks = base_clicks + (i - (_N_CHALLENGERS // 2)) * 8
        delta_clicks = clicks - base_clicks
        challengers.append(
            UpworthyVariant(
                headline=f"Challenger headline {i} EFFECT={delta_clicks}",
                clicks=clicks,
                impressions=impressions,
                eyecatcher_id=None,
            )
        )
    test = UpworthyTest(test_id="synthetic-1", variants=[baseline, *challengers])
    result = upworthy_test_to_cases(test)
    assert not result.skipped, "pure headline swaps should never be skipped"
    return result.cases


def _treatment_headline(case: BenchmarkCase) -> str:
    for screen in case.hypothesis.proposed_figma.screens:
        for comp in screen.components:
            if comp.role == "headline":
                return comp.text or ""
    return ""


def _honest_perfect(case: BenchmarkCase) -> float:
    """Reads the EFFECT token from the rendered treatment headline (BLIND)."""
    match = re.search(r"EFFECT=(-?\d+)", _treatment_headline(case))
    return float(match.group(1)) if match else 0.0


def _honest_noise(case: BenchmarkCase) -> float:
    """Deterministic per-case pseudo-random effect, independent of the outcome.

    Seeds off a STABLE digest of the case id (not Python's process-salted
    `hash()`), so the fixture is reproducible across runs / PYTHONHASHSEED values
    and the non-significance assertion below can't fail nondeterministically.
    """
    digest = hashlib.sha256(case.case_id.encode("utf-8")).hexdigest()
    rng = random.Random(int(digest[:8], 16))
    return rng.uniform(-1.0, 1.0)


def _leaking(case: BenchmarkCase) -> float:
    """Peeks at the answer key — the exact failure §4 exists to catch."""
    return case.ground_truth.observed_lift


# ── Tests ──────────────────────────────────────────────────────────────────────


def test_perfect_predictor_scores_high_and_certifies():
    cases = _build_cases()
    result = run_blind_eval(cases, _honest_perfect, seed=7, n_permutations=300)

    assert result.n_cases == _N_CHALLENGERS
    assert result.n_dropped == 0
    # PRIMARY endpoint (§5) is rank-ρ and it is reported.
    assert result.rank_rho == pytest.approx(1.0)
    assert result.direction_accuracy == pytest.approx(1.0)
    # The certificate is the faithful (certifying) re-run and it PASSes.
    assert result.certificate is not None
    assert result.certificate.certifying is True
    assert result.certificate.passed is True
    assert result.void is False
    assert result.void_reason is None


def test_noise_predictor_certifies_and_is_not_significant():
    cases = _build_cases()
    result = run_blind_eval(cases, _honest_noise, seed=7, n_permutations=300)

    # A label-independent predictor must still PASS the null gate (it ignores the
    # answer key, so its scrambled-label null centers at chance).
    assert result.certificate is not None
    assert result.certificate.passed is True
    assert result.void is False
    # And it is NOT distinguishable from chance: the permutation p-value for the
    # primary rank-ρ does not clear significance.
    assert result.certificate.rank_rho_p_value is not None
    assert result.certificate.rank_rho_p_value > 0.05


def test_leaking_predictor_voids_the_run():
    """The leaking predictor reads case.ground_truth, so when the runner re-runs
    it on scrambled-label copies of the cases its predictions track the shuffle —
    the scrambled-label scores do NOT center at chance, so the null-integrity
    certificate VOIDs the run (passed=False, void=True, a leakage void_reason)."""
    cases = _build_cases()
    result = run_blind_eval(cases, _leaking, seed=7, n_permutations=300)

    # Observed scores look perfect — exactly why the scores alone can't be trusted.
    assert result.rank_rho == pytest.approx(1.0)
    assert result.direction_accuracy == pytest.approx(1.0)
    # ...but the null gate catches the leak and VOIDs the run.
    assert result.certificate is not None
    assert result.certificate.passed is False
    assert result.void is True
    assert result.void_reason is not None
    assert "leakage" in result.void_reason.lower()


def test_baselines_are_computed_correctly():
    cases = _build_cases()
    actuals = [c.ground_truth.observed_lift for c in cases]
    n = len(actuals)
    n_flat = sum(1 for a in actuals if a == 0.0)
    n_pos = sum(1 for a in actuals if a > 0.0)
    n_neg = sum(1 for a in actuals if a < 0.0)

    result = run_blind_eval(cases, _honest_perfect, seed=7, n_permutations=200)
    by_name = {b.name: b for b in result.baselines}
    assert set(by_name) == {"always_flat", "random_rank"}

    # always-flat: predicts sign 0 everywhere → correct only on flat actuals,
    # rank-ρ 0 (constant prediction).
    assert by_name["always_flat"].direction_accuracy == pytest.approx(n_flat / n)
    assert by_name["always_flat"].rank_rho == 0.0

    # random-rank: marginal collision probability Σ_s (n_s/n)², rank-ρ 0.
    expected = (n_neg / n) ** 2 + (n_flat / n) ** 2 + (n_pos / n) ** 2
    assert by_name["random_rank"].direction_accuracy == pytest.approx(expected)
    assert by_name["random_rank"].rank_rho == 0.0


def test_paired_direction_delta_ci_is_deterministic():
    cases = _build_cases()
    r1 = run_blind_eval(cases, _honest_perfect, seed=99, n_permutations=200)
    r2 = run_blind_eval(cases, _honest_perfect, seed=99, n_permutations=200)
    # Same seed → byte-identical paired bootstrap CI.
    assert r1.direction_delta_ci == r2.direction_delta_ci
    assert r1.direction_delta_ci is not None
    lo, hi = r1.direction_delta_ci
    assert lo <= hi
    # A perfect predictor beats the flat floor on every non-flat case, so the
    # paired direction-delta point estimate is the non-flat share and positive.
    assert r1.direction_delta_vs_flat is not None
    assert r1.direction_delta_vs_flat > 0.0


def test_dropped_experiment_is_surfaced_not_truncated():
    cases = _build_cases()
    target = cases[0].case_id

    def _flaky(case: BenchmarkCase) -> float:
        if case.case_id == target:
            raise RuntimeError("predictor blew up on this case")
        return _honest_perfect(case)

    result = run_blind_eval(cases, _flaky, seed=7, n_permutations=200)
    assert result.n_cases == _N_CHALLENGERS - 1
    assert result.n_dropped == 1
    assert result.dropped_case_ids == [target]
    # The surviving cases still certify (predictor still blind on them).
    assert result.certificate is not None
    assert result.certificate.passed is True


def test_all_cases_dropped_is_an_honest_void():
    cases = _build_cases()

    def _always_fail(_case: BenchmarkCase) -> float:
        raise RuntimeError("nope")

    result = run_blind_eval(cases, _always_fail, seed=7)
    assert result.n_cases == 0
    assert result.n_dropped == _N_CHALLENGERS
    assert result.void is True
    assert result.certificate is None
    assert result.rank_rho is None


def test_empty_cases_raises():
    with pytest.raises(ValueError, match="at least one case"):
        run_blind_eval([], _honest_perfect, seed=1)


def test_score_with_engine_is_gated_under_pytest():
    """The live-LLM entry point must refuse to run under pytest / CI."""
    with pytest.raises(RuntimeError, match="gated live-LLM"):
        score_with_engine()


def test_predictor_type_alias_is_exported():
    # The injected-predictor seam is part of the public surface (DI for testing).
    assert Predictor is not None
