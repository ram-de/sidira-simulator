"""Tests for services/null_integrity.py — the §4 null-integrity certificate.

The certificate is the engine-validation gate: scramble the outcome labels and
a CLEAN cell must score at chance on direction and ρ≈0 on rank. These tests pin
that the gate reads the NULL (not the observed scores), that a constructed
LEAKING cell goes VOID, that the significance read stays separate from the gate,
that the hash-commit is deterministic and input-sensitive, and that the honesty
guards (small-N, ties, degenerate input) behave.

Pure/deterministic, scipy-free — same discipline as test_statistics.py.
"""

from __future__ import annotations

import pytest

from sidira_simulator.schemas.scoring import NullIntegrityCertificate
from sidira_simulator.services.null_integrity import (
    _MIN_EXPERIMENTS,
    _direction_accuracy,
    _sign,
    certify_null_integrity,
)
from sidira_simulator.services.statistics import _average_ranks, spearman_rho

# A comfortably-above-floor experiment count for the "real" scenarios.
_N = 24
_SEED = 12345


def _linspace(lo: float, hi: float, n: int) -> list[float]:
    step = (hi - lo) / (n - 1)
    return [lo + step * i for i in range(n)]


# ── Spearman helper (added in statistics.py) ────────────────────────────


def test_spearman_perfect_monotone() -> None:
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert spearman_rho(x, x) == pytest.approx(1.0)
    assert spearman_rho(x, list(reversed(x))) == pytest.approx(-1.0)


def test_spearman_handles_ties_with_average_ranks() -> None:
    # [10, 10, 30, 40] → ranks [1.5, 1.5, 3, 4] (the tie averages ranks 1,2).
    assert _average_ranks([10.0, 10.0, 30.0, 40.0]) == [1.5, 1.5, 3.0, 4.0]
    # Monotone-with-ties pair still gives a high (but <1 because of the tie) ρ.
    rho = spearman_rho([10.0, 10.0, 30.0, 40.0], [1.0, 2.0, 3.0, 4.0])
    assert 0.0 < rho < 1.0


def test_spearman_zero_variance_returns_zero() -> None:
    # All-ties on one side → undefined correlation → honest 0.0, not a crash.
    assert spearman_rho([5.0, 5.0, 5.0], [1.0, 2.0, 3.0]) == 0.0
    # n == 1 → no rank variation.
    assert spearman_rho([1.0], [9.0]) == 0.0


def test_spearman_rejects_bad_input() -> None:
    with pytest.raises(ValueError):
        spearman_rho([1.0, 2.0], [1.0])
    with pytest.raises(ValueError):
        spearman_rho([], [])


# ── sign + direction accuracy primitives ────────────────────────────────


def test_sign_three_way() -> None:
    assert _sign(0.0) == 0
    assert _sign(-0.0) == 0
    assert _sign(2.5) == 1
    assert _sign(-2.5) == -1


def test_direction_accuracy_counts_flat_agreement() -> None:
    # pred/actual signs: (+,+), (-,-), (0,0), (+,-) → 3/4 match.
    preds = [1.0, -1.0, 0.0, 1.0]
    acts = [2.0, -2.0, 0.0, -1.0]
    assert _direction_accuracy(preds, acts) == pytest.approx(0.75)


# ── Perfect predictor: observed maxed, null still at chance, PASS ────────


def test_perfect_predictor_passes_with_tiny_p_values() -> None:
    actuals = _linspace(-1.0, 1.0, _N)
    predictions = list(actuals)  # pred == actual: a perfect predictor.

    # An honest perfect predictor: it computes its prediction from the held-out
    # FEATURES, never the label, so re-running it on scrambled labels returns the
    # same fixed vector. Certification needs this rerun path (codex P1).
    def honest_perfect(_shown):
        return predictions

    cert = certify_null_integrity(
        predictions, actuals, n_permutations=500, seed=_SEED, predict_fn=honest_perfect
    )

    # Observed is maxed out.
    assert cert.observed_direction_accuracy == pytest.approx(1.0)
    assert cert.observed_rank_rho == pytest.approx(1.0)
    # The NULL still centers at chance even though the predictor is perfect —
    # scrambling the labels destroys the signal. THIS is what PASS reads. The
    # direction baseline is the cell's marginal-expected accuracy (≈0.5 for this
    # sign-balanced linspace), not a hard-coded 0.5.
    base = cert.marginal_chance_accuracy
    assert cert.null_direction_accuracy_ci[0] <= base <= cert.null_direction_accuracy_ci[1]
    assert cert.null_rank_rho_ci[0] <= 0.0 <= cert.null_rank_rho_ci[1]
    assert cert.certifying is True
    assert cert.passed is True
    assert cert.void_reason is None
    # The SEPARATE significance read: a perfect predictor is wildly better than
    # the null, so both permutation p-values are tiny (smallest possible is
    # 1/(B+1) under the add-one correction).
    assert cert.direction_accuracy_p_value < 0.05
    assert cert.rank_rho_p_value == pytest.approx(1 / 501)


# ── Pure-noise predictor: observed ≈ chance, still PASS ──────────────────


def test_noise_predictor_passes() -> None:
    import random as _r

    rng = _r.Random(99)
    actuals = [rng.gauss(0.0, 1.0) for _ in range(_N)]
    predictions = [rng.gauss(0.0, 1.0) for _ in range(_N)]  # independent of actuals.

    cert = certify_null_integrity(
        predictions, actuals, n_permutations=500, seed=_SEED, predict_fn=lambda _s: predictions
    )
    # A noise predictor's scrambled-label scores center at chance → PASS. (The
    # gate is about the NULL, and an independent predictor's null is clean.)
    assert cert.certifying is True
    assert cert.passed is True
    assert cert.void_reason is None


# ── Non-certifying diagnostic path (predict_fn=None) never PASSes (codex P1) ──


def test_fixed_prediction_path_is_non_certifying() -> None:
    """Without `predict_fn` the certificate is diagnostic only: it reports the
    observed scores, the fixed-prediction null and the p-values, but REFUSES to
    PASS — it cannot rule out a cell that leaked labels while producing those
    predictions (codex P1). No void_reason: this is 'not certifiable here', not
    'leakage proven'."""
    actuals = _linspace(-1.0, 1.0, _N)
    predictions = list(actuals)  # would look perfect...

    cert = certify_null_integrity(predictions, actuals, n_permutations=500, seed=_SEED)
    assert cert.certifying is False
    assert cert.passed is False
    assert cert.void_reason is None
    assert cert.caveat is not None and "Non-certifying" in cert.caveat
    # Diagnostics are still populated.
    assert cert.observed_direction_accuracy == pytest.approx(1.0)
    assert cert.null_direction_accuracy_ci is not None
    assert cert.direction_accuracy_p_value is not None


# ── Imbalanced-but-honest marginals must NOT void (codex P2) ─────────────


def test_all_positive_actuals_pass_not_void() -> None:
    """All-positive outcomes are common (qa §1: flat/positive dominates 67–92%)
    and are NOT leakage. The gate brackets the cell's MARGINAL chance baseline,
    not a fixed 0.5, so an all-positive perfect predictor PASSes.

    Regression guard for the codex P2 finding: an earlier fixed-0.5 gate falsely
    VOIDed this clean cell because its permutation null direction-accuracy sits
    at 1.0 (every scrambled positive label still matches a positive prediction).
    """
    actuals = [float(i + 1) for i in range(_N)]  # all strictly positive.
    predictions = list(actuals)

    cert = certify_null_integrity(
        predictions, actuals, n_permutations=500, seed=_SEED, predict_fn=lambda _s: predictions
    )

    # Marginal baseline IS 1.0 here, the null CI sits at 1.0 and brackets it.
    assert cert.marginal_chance_accuracy == pytest.approx(1.0)
    assert cert.null_direction_accuracy_ci[0] == pytest.approx(1.0)
    assert cert.passed is True
    assert cert.void_reason is None


# ── LEAKING cell (predict_fn peeks at labels): null stays high → VOID ─────


def test_leaking_predict_fn_is_void() -> None:
    """The faithful §4 leakage test: a cell whose predictions are a function of
    the label set at predict-time. The certificate re-runs `predict_fn` on each
    scrambled label set, so the leaking cell keeps predicting the scrambled
    labels — its null direction-accuracy stays pinned at 1.0, way above the
    marginal chance baseline — and the cell is correctly VOIDed.

    Sign-balanced actuals (baseline ≈ 0.5) make the leak unmistakable: an honest
    cell would score ≈0.5 on scrambled labels, but the leaking cell scores 1.0.
    """
    actuals = [float(i - (_N // 2)) for i in range(_N)]  # crosses zero → balanced signs.
    actuals = [a if a != 0.0 else 1.0 for a in actuals]  # avoid a zero label.
    observed = list(actuals)  # the cell's real, unscrambled output.

    # A LEAKING predictor: it returns whatever labels it is shown (peeks).
    def leaking_predict_fn(shown_labels):
        return list(shown_labels)

    cert = certify_null_integrity(
        observed,
        actuals,
        n_permutations=400,
        seed=_SEED,
        predict_fn=leaking_predict_fn,
    )

    # Leak signature: scrambled-label direction accuracy is pinned at 1.0 (the
    # cell predicts the scramble), far above the ≈0.5 marginal baseline → VOID.
    assert cert.marginal_chance_accuracy == pytest.approx(0.5, abs=0.15)
    assert cert.null_direction_accuracy_ci[0] == pytest.approx(1.0)
    assert cert.passed is False
    assert cert.void_reason is not None
    assert "Leakage detected" in cert.void_reason
    assert "does not bracket the marginal chance baseline" in cert.void_reason
    # The OBSERVED scores + hash still reflect the real (unscrambled) output.
    assert cert.observed_direction_accuracy == pytest.approx(1.0)


def test_honest_predict_fn_passes() -> None:
    """A cell whose predict_fn IGNORES the shown labels (returns its fixed
    output) is honest: re-running it on scrambled labels reproduces the
    fixed-prediction null, which centers at the marginal baseline → PASS.

    Confirms predict_fn does not itself bias the gate toward VOID — only an
    actually-leaking function trips it."""
    actuals = [float(i - (_N // 2)) for i in range(_N)]
    actuals = [a if a != 0.0 else 1.0 for a in actuals]
    observed = list(actuals)

    def honest_predict_fn(_shown_labels):
        return observed  # ignores the labels entirely.

    cert = certify_null_integrity(
        observed, actuals, n_permutations=400, seed=_SEED, predict_fn=honest_predict_fn
    )
    # Identical to the predict_fn=None path for this honest cell.
    fixed = certify_null_integrity(observed, actuals, n_permutations=400, seed=_SEED)
    assert cert.passed is True
    assert cert.null_direction_accuracy_ci == fixed.null_direction_accuracy_ci


def test_predict_fn_must_reproduce_observed_predictions() -> None:
    """CODEX P1: the certifying predictor must be the SAME one that produced the
    observed predictions. The exploit: submit a LEAKED observed vector
    (predictions == actuals) but hand a clean/noisy predict_fn whose null looks
    fine — that must NOT PASS. We require predict_fn(actuals) == predictions and
    VOID on mismatch."""
    actuals = [float(i - (_N // 2)) or 1.0 for i in range(_N)]
    leaked_observed = list(actuals)  # the reported (leaked) vector.
    noise = [(-1.0) ** i for i in range(_N)]  # an UNRELATED clean closure.

    cert = certify_null_integrity(
        leaked_observed,
        actuals,
        n_permutations=500,
        seed=1,
        predict_fn=lambda _shown: noise,  # does NOT reproduce leaked_observed.
    )
    # The clean closure's null would look fine, but the predictor doesn't match
    # the reported vector → the gate refuses to certify.
    assert cert.passed is False
    assert cert.void_reason is not None
    assert "Inconsistent inputs" in cert.void_reason


def test_predict_fn_wrong_length_raises() -> None:
    actuals = [float(i + 1) for i in range(_N)]
    cert_inputs = list(actuals)
    with pytest.raises(ValueError):
        certify_null_integrity(
            cert_inputs,
            actuals,
            n_permutations=10,
            seed=_SEED,
            predict_fn=lambda shown: [1.0],  # wrong length.
        )


# ── Determinism: same seed → identical cert AND identical hash ───────────


def test_determinism_same_seed() -> None:
    actuals = _linspace(-1.0, 1.0, _N)
    predictions = [a + 0.1 for a in actuals]
    a = certify_null_integrity(predictions, actuals, n_permutations=400, seed=2024)
    b = certify_null_integrity(predictions, actuals, n_permutations=400, seed=2024)
    assert a.model_dump() == b.model_dump()
    assert a.integrity_hash == b.integrity_hash


def test_different_seed_changes_null_but_not_hash() -> None:
    # The hash commits to inputs + config (incl. seed). Same inputs + DIFFERENT
    # seed → different null draws AND a different hash (seed is part of config).
    actuals = _linspace(-1.0, 1.0, _N)
    predictions = [a + 0.1 for a in actuals]
    a = certify_null_integrity(predictions, actuals, n_permutations=400, seed=1)
    b = certify_null_integrity(predictions, actuals, n_permutations=400, seed=2)
    assert a.integrity_hash != b.integrity_hash


# ── Hash-commit: moves iff any input/config changes (§5) ────────────────


def test_hash_is_input_and_config_sensitive() -> None:
    actuals = _linspace(-1.0, 1.0, _N)
    predictions = [a + 0.1 for a in actuals]
    base = certify_null_integrity(predictions, actuals, n_permutations=200, seed=5)

    # Perturb one prediction → hash moves.
    p2 = list(predictions)
    p2[0] += 1e-6
    moved_pred = certify_null_integrity(p2, actuals, n_permutations=200, seed=5)
    assert moved_pred.integrity_hash != base.integrity_hash

    # Perturb one actual → hash moves.
    a2 = list(actuals)
    a2[-1] += 1e-6
    moved_act = certify_null_integrity(predictions, a2, n_permutations=200, seed=5)
    assert moved_act.integrity_hash != base.integrity_hash

    # Change n_permutations → hash moves.
    moved_perm = certify_null_integrity(predictions, actuals, n_permutations=201, seed=5)
    assert moved_perm.integrity_hash != base.integrity_hash

    # Identical inputs/config → identical hash (pre-registration property).
    same = certify_null_integrity(predictions, actuals, n_permutations=200, seed=5)
    assert same.integrity_hash == base.integrity_hash


# ── Small-N honesty guard ───────────────────────────────────────────────


def test_underpowered_never_certifies() -> None:
    n = _MIN_EXPERIMENTS - 1
    actuals = _linspace(-1.0, 1.0, n)
    predictions = list(actuals)  # a perfect predictor...
    # Use the certifying path so the UNDERPOWERED branch (not the non-certifying
    # branch) is what blocks PASS.
    cert = certify_null_integrity(
        predictions, actuals, n_permutations=200, seed=_SEED, predict_fn=lambda _s: predictions
    )
    # ...still cannot PASS: too few experiments to certify the null.
    assert cert.certifying is True
    assert cert.underpowered is True
    assert cert.passed is False
    assert cert.caveat is not None and "Underpowered" in cert.caveat
    assert cert.n_experiments == n
    # Observed scores are still reported (the run sees the numbers).
    assert cert.observed_direction_accuracy == pytest.approx(1.0)


def test_at_floor_can_pass() -> None:
    # Exactly _MIN_EXPERIMENTS is NOT underpowered.
    actuals = _linspace(-1.0, 1.0, _MIN_EXPERIMENTS)
    predictions = list(actuals)
    cert = certify_null_integrity(
        predictions, actuals, n_permutations=500, seed=_SEED, predict_fn=lambda _s: predictions
    )
    assert cert.underpowered is False
    assert cert.passed is True


# ── Tie handling (sign(0), tied ranks) end to end ───────────────────────


def test_zero_effect_predictions_handled() -> None:
    # A predictor that emits some exact 0.0 (zero-effect) predictions: sign(0)
    # is its own class, average-ranks absorb the tied zeros, no crash, and a
    # certificate comes out.
    actuals = _linspace(-1.0, 1.0, _N)
    predictions = [0.0 if i % 3 == 0 else actuals[i] for i in range(_N)]
    cert = certify_null_integrity(predictions, actuals, n_permutations=300, seed=_SEED)
    assert isinstance(cert, NullIntegrityCertificate)
    assert cert.observed_direction_accuracy is not None
    assert -1.0 <= cert.observed_rank_rho <= 1.0


def test_all_same_direction_predictions() -> None:
    # Every prediction positive (one sign class). spearman over a constant-sign
    # but varied-magnitude pred is still defined via magnitudes; no crash.
    actuals = _linspace(-1.0, 1.0, _N)
    predictions = [abs(a) + 0.5 for a in actuals]
    cert = certify_null_integrity(predictions, actuals, n_permutations=200, seed=_SEED)
    assert isinstance(cert, NullIntegrityCertificate)
    assert 0.0 <= cert.observed_direction_accuracy <= 1.0


# ── Degenerate input ────────────────────────────────────────────────────


def test_empty_input_returns_void_cert() -> None:
    cert = certify_null_integrity([], [], n_permutations=100, seed=_SEED)
    assert cert.n_experiments == 0
    assert cert.passed is False
    assert cert.underpowered is True
    assert cert.void_reason is not None
    assert cert.observed_direction_accuracy is None
    assert cert.observed_rank_rho is None
    # Even the degenerate cert carries a hash (pre-registerable).
    assert len(cert.integrity_hash) == 64


def test_degenerate_all_identical_actuals_is_void() -> None:
    """CODEX P1: when every actual label is identical, scrambling is a no-op and
    the null has no power to detect leakage. A label-peeking predict_fn would
    otherwise look clean and PASS — so this MUST be VOID, not certified."""
    actuals = [0.0] * _N  # all-flat held-out outcomes.
    observed = list(actuals)

    cert = certify_null_integrity(
        observed,
        actuals,
        n_permutations=300,
        seed=_SEED,
        predict_fn=lambda shown: list(shown),  # the exact leaking closure codex named.
    )
    assert cert.passed is False
    assert cert.void_reason is not None
    assert "Uninformative null" in cert.void_reason


def test_length_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        certify_null_integrity([1.0, 2.0], [1.0], n_permutations=10, seed=_SEED)


def test_zero_permutations_rejected() -> None:
    with pytest.raises(ValueError):
        certify_null_integrity([1.0] * _N, [1.0] * _N, n_permutations=0, seed=_SEED)


def test_non_finite_inputs_rejected() -> None:
    """CODEX P2: NaN/inf must never be silently certified. A NaN would slip
    through _sign as the zero class and could certify garbage."""
    nan = float("nan")
    inf = float("inf")
    good = list(_linspace(-1.0, 1.0, _N))
    # NaN in predictions.
    with pytest.raises(ValueError):
        certify_null_integrity([nan] + good[1:], good, n_permutations=50, seed=_SEED)
    # inf in actuals.
    with pytest.raises(ValueError):
        certify_null_integrity(good, [inf] + good[1:], n_permutations=50, seed=_SEED)
    # The exact exploit codex named: all-NaN predictions, zero actuals.
    with pytest.raises(ValueError):
        certify_null_integrity([nan] * _N, [0.0] * _N, n_permutations=50, seed=_SEED)
    # A predict_fn that emits a NaN on the real labels is also rejected.
    with pytest.raises(ValueError):
        certify_null_integrity(
            good, good, n_permutations=50, seed=_SEED, predict_fn=lambda _s: [nan] * _N
        )


# ── p-value separation from the gate ────────────────────────────────────


def test_p_values_separate_from_gate() -> None:
    """The significance read is reported even when the cell PASSes, and it does
    not gate: a perfect predictor PASSes (clean null) AND has a tiny p-value."""
    actuals = _linspace(-1.0, 1.0, _N)
    predictions = list(actuals)
    cert = certify_null_integrity(
        predictions, actuals, n_permutations=500, seed=_SEED, predict_fn=lambda _s: predictions
    )
    assert cert.passed is True
    assert cert.direction_accuracy_p_value is not None
    assert cert.rank_rho_p_value is not None
    # add-one correction floors both p-values at 1/(B+1), never 0.
    assert cert.direction_accuracy_p_value >= 1 / 501
    assert cert.rank_rho_p_value >= 1 / 501
