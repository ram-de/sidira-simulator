"""Null-integrity certificate — the Tier-0 engine-validation gate (§4).

ablation-protocol §4, "Null-integrity certificate (mandatory)": scramble the
experiment outcome labels and a CLEAN ablation cell must score at chance on
direction and ρ≈0 on rank. A cell that "predicts" scrambled outcomes is leaking
signal from the label into the prediction; the whole run is VOID until it
doesn't. Ship the certificate with results.

This module is JUST that statistical primitive — a pure, deterministic function
over a cell's paired ``(predicted_effect, actual_effect)`` arrays. It does not
depend on any (not-yet-built) eval runner; it is the gate that harness cells
will later ship results through.

What the certificate carries (see `NullIntegrityCertificate`):

1. Observed direction-accuracy + rank-ρ over the REAL labels.
2. A NULL distribution of both, built by permuting the `actuals` labels
   `n_permutations` times under a seeded `random.Random` (the same run-seed
   XOR-mix reproducibility discipline as `aggregate_conversion_lift`), each with
   a percentile CI.
3. The PASS/VOID gate — per §4: `passed=True` iff the null direction-accuracy
   CI brackets this cell's MARGINAL chance baseline AND the null rank-ρ CI
   brackets 0. Otherwise VOID + a `void_reason` (leakage → run void until
   fixed). The direction baseline is the cell's marginal-expected accuracy
   under random relabeling, NOT a fixed 0.5, so an honest-but-skewed sign
   distribution (e.g. all-positive actuals) is not falsely voided.
4. A SEPARATE significance read: permutation p-values comparing the OBSERVED
   scores to the null distribution. This is the honest "is the real result
   better than chance" number; it never relaxes the gate.
5. A `hashlib` SHA-256 hash-commit (§5) over canonical-serialized inputs +
   config, so a certificate can be pre-registered and not retrofitted.
6. Honesty guards: a small-N floor (never silently certify a 2-experiment run),
   explicit tie handling (`sign(0)`, average ranks), and an honest degenerate
   path.

Pure-Python and dependency-free (no scipy/numpy), matching `statistics.py`.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from typing import Callable, Sequence

from sidira_simulator.schemas.scoring import NullIntegrityCertificate
from sidira_simulator.services.statistics import spearman_rho

# Arbitrary integer XOR mask used to derive a permutation-specific RNG seed from
# the caller's seed, so the null-permutation stream cannot collide with the
# bootstrap resample stream in scoring.py (which mixes a DIFFERENT mask). Same
# defense-in-depth discipline as `_BOOTSTRAP_SEED_MIX` in scoring.py.
_PERMUTATION_SEED_MIX = 0x4E_55_4C_4C_5F_49_4E  # "NULL_IN" as hex bytes

# Certification floor (§4 honesty guard): below this many experiments the null
# distribution is too coarse to certify "centers at chance" — the direction-
# accuracy null can only take a handful of discrete values and the rank-ρ CI is
# enormous. We refuse to PASS such a cell and mark it underpowered rather than
# silently certifying a 2-experiment run.
_MIN_EXPERIMENTS = 8

# CI confidence for the null distributions (two-sided). 95% matches the
# bootstrap CI convention in statistics.py.
_NULL_CI_CONFIDENCE = 0.95


def _sign(x: float) -> int:
    """Sign of `x` with an explicit zero class: -1, 0, or +1.

    `sign(0) == 0` is a real third class (a zero-effect prediction or a
    genuinely flat outcome), NOT silently folded into +1. Direction accuracy
    then counts a pred/actual pair as correct only when BOTH share the same
    sign, including the 0==0 flat-agree case.
    """
    if x > 0.0:
        return 1
    if x < 0.0:
        return -1
    return 0


def _require_finite(values: Sequence[float], label: str) -> None:
    """Raise ValueError if any value is NaN or infinite (codex P2).

    The certificate certifies metric INTEGRITY, so non-finite data is never
    silently certified — a NaN would otherwise pass through `_sign` as the zero
    class and an inf would corrupt ranks/means.
    """
    for i, v in enumerate(values):
        if not math.isfinite(v):
            raise ValueError(f"{label}[{i}] is not finite ({v!r}); non-finite inputs are rejected")


def _direction_accuracy(predictions: Sequence[float], actuals: Sequence[float]) -> float:
    """Fraction of experiments where sign(pred) == sign(actual).

    Both endpoints use the explicit three-way `_sign` (so 0==0 agrees and 0 vs
    +1 disagrees). Assumes equal, non-empty lengths (the caller guarantees it).
    """
    n = len(predictions)
    matches = sum(1 for p, a in zip(predictions, actuals) if _sign(p) == _sign(a))
    return matches / n


def _marginal_chance_accuracy(predictions: Sequence[float], actuals: Sequence[float]) -> float:
    """Expected direction-accuracy under a random relabeling — the TRUE chance
    baseline for THIS cell's sign marginals (not a hard-coded 0.5).

    Permuting the `actuals` labels fixes the prediction signs and shuffles the
    actual signs, so a prediction with sign s matches a randomly-assigned actual
    with probability (count of actuals with sign s) / n. Averaging over all
    positions gives the closed-form expectation of the permutation null:

        E[acc] = Σ_{s ∈ {-1, 0, +1}}  (n_pred_s / n) · (n_actual_s / n)

    This is what `_direction_accuracy` averages to over many label permutations.
    Why it matters (codex P2): when the sign marginals are imbalanced — e.g. all
    held-out experiments have a positive effect (qa §1: flat/positive dominates
    67–92% of the time) — the permutation null centers WELL above 0.5 with ZERO
    leakage. Gating against a fixed 0.5 would falsely VOID such a clean cell. The
    direction gate brackets THIS marginal baseline instead, so it flags genuine
    label leakage (the null fails to center where a no-information predictor
    must) without penalizing a skewed-but-honest sign distribution. The rank-ρ
    gate keeps its fixed-0 target because permuting labels always centers ρ at 0
    regardless of marginals (ρ is mean-centered).
    """
    n = len(predictions)
    pred_counts: dict[int, int] = {-1: 0, 0: 0, 1: 0}
    actual_counts: dict[int, int] = {-1: 0, 0: 0, 1: 0}
    for p in predictions:
        pred_counts[_sign(p)] += 1
    for a in actuals:
        actual_counts[_sign(a)] += 1
    return sum((pred_counts[s] / n) * (actual_counts[s] / n) for s in (-1, 0, 1))


def _percentile_ci(
    sorted_samples: Sequence[float], *, confidence: float = _NULL_CI_CONFIDENCE
) -> tuple[float, float]:
    """Two-sided percentile CI over an already-sorted sample list.

    Uses the same nearest-rank convention as `bootstrap_percentile_ci`
    (index = ceil(p * B) - 1) so the null CIs and the bootstrap CIs elsewhere
    read identically. `sorted_samples` must be non-empty and ascending.
    """
    b = len(sorted_samples)
    alpha = (1.0 - confidence) / 2.0
    lo_idx = max(0, int(math.ceil(alpha * b)) - 1)
    hi_idx = min(b - 1, int(math.ceil((1.0 - alpha) * b)) - 1)
    return sorted_samples[lo_idx], sorted_samples[hi_idx]


def _canonical_payload(
    predictions: Sequence[float],
    actuals: Sequence[float],
    *,
    n_permutations: int,
    seed: int,
) -> str:
    """Canonical JSON over inputs + config for the hash-commit (§5).

    `sort_keys` + fixed separators make the serialization deterministic and
    order-stable; the float `repr` round-trips through json exactly on CPython,
    so the hash moves iff a prediction, an actual, n_permutations, seed, or the
    experiment count changes — nothing else. Pre-registration depends on this:
    the same inputs/config ALWAYS produce the same hash, and any retrofit moves
    it.
    """
    payload = {
        "predictions": [float(p) for p in predictions],
        "actuals": [float(a) for a in actuals],
        "n_permutations": int(n_permutations),
        "seed": int(seed),
        "n_experiments": len(predictions),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _integrity_hash(
    predictions: Sequence[float],
    actuals: Sequence[float],
    *,
    n_permutations: int,
    seed: int,
) -> str:
    """SHA-256 hex digest of the canonical payload (§5 hash-commit)."""
    canonical = _canonical_payload(predictions, actuals, n_permutations=n_permutations, seed=seed)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def certify_null_integrity(
    predictions: Sequence[float],
    actuals: Sequence[float],
    *,
    n_permutations: int = 1000,
    seed: int,
    predict_fn: Callable[[Sequence[float]], Sequence[float]] | None = None,
) -> NullIntegrityCertificate:
    """Build a `NullIntegrityCertificate` for one ablation cell (§4).

    `predictions[i]` is the cell's predicted effect for held-out experiment i
    (its SIGN is the predicted direction; its VALUE is the rank material).
    `actuals[i]` is the real realized outcome effect for the same experiment.
    The two arrays must be the same length and paired by index.

    The gate (`passed`) reads the NULL: a clean cell is one whose
    SCRAMBLED-label scores center at chance — null direction-accuracy CI
    brackets the cell's MARGINAL chance baseline AND null rank-ρ CI brackets 0.
    If they don't, the cell is leaking (predicting scrambled outcomes) and the
    certificate is VOID with a `void_reason`; per §4 the whole run is void until
    it doesn't leak. The direction target is the marginal-expected accuracy, not
    a fixed 0.5, so a skewed-but-honest sign distribution is not falsely voided.

    Certification REQUIRES `predict_fn` (codex P1). Two modes:

    * `predict_fn` supplied (the CERTIFYING path, faithful §4): the certificate
      RE-RUNS the cell on each scrambled label set (`predict_fn(scrambled)`). A
      leaking cell that peeks at labels at predict-time keeps scoring above
      chance on the scrambled labels, so its null does NOT center at the marginal
      baseline and the cell is correctly VOIDed. An honest cell ignores the
      labels and its null collapses to chance → PASS. The OBSERVED scores and the
      hash always use the passed-in `predictions` (the cell's real, unscrambled
      output), so the certificate stays reproducible and pre-registerable. To
      stop a caller certifying a clean closure's null while shipping a leaked
      observed vector, `predict_fn(actuals)` MUST reproduce the submitted
      `predictions` exactly — a mismatch VOIDs the certificate (codex P1).

      TRUST BOUNDARY (codex P1 #4 — by design): `predict_fn` MUST be the cell's
      REAL evaluation function — the one that re-derives predictions by running
      the model on the (scrambled) label set's experiments — NOT a closure that
      ignores its argument and returns a constant. This primitive cannot, even in
      principle, distinguish an honest feature-based predictor that happens to be
      label-independent from a leaking predictor disguised as a constant closure:
      both return a fixed vector regardless of the shuffle. Whoever holds the
      cell's evaluation code (the future #222 harness/runner) MUST own the
      construction of `predict_fn` and pass the genuine re-run; a `lambda _:
      frozen_vector` stub WILL be (wrongly) certified, exactly as `predict_fn=
      None` is refused. This function's job is the statistics of the gate; the
      authenticity of the re-run is the runner's job, and that contract is stated
      here so a caller can't certify by accident.
    * `predict_fn=None` (DIAGNOSTIC only, NON-CERTIFYING): the fixed `predictions`
      vector is scored against each label permutation. Because the prediction
      vector never changes, this path CANNOT rule out a cell that leaked the real
      labels while producing those very predictions — so it never PASSes
      (`passed=False`, `caveat` explains). It still reports the full diagnostic
      (observed scores, fixed-prediction null, p-values, hash) for inspection.

    The permutation p-values are the SEPARATE significance read — the honest
    "is the real result better than chance" number — and never relax the gate.

    Reproducibility: the permutation RNG is `random.Random(seed ^
    _PERMUTATION_SEED_MIX)`, the same XOR-mix discipline as
    `aggregate_conversion_lift`'s bootstrap, so the same (inputs, n_permutations,
    seed) ALWAYS yields a byte-identical certificate AND `integrity_hash`. (A
    `predict_fn` must itself be deterministic for this to hold.)

    Edge cases are handled honestly rather than silently:
      - empty input → an explicit VOID cert (never raises into the harness; the
        void_reason names the defect). Length mismatch is a programming error
        and DOES raise.
      - all `actuals` identical → uninformative null (scrambling is a no-op),
        certificate is VOID; a degenerate label set cannot certify integrity.
      - n_experiments below `_MIN_EXPERIMENTS` → `underpowered=True`,
        `passed=False`, a caveat; the observed scores + null are still computed
        and reported (the run sees the numbers, just can't certify on them).
      - all-same-direction / tied ranks → handled by `_sign` (explicit 0 class)
        and `spearman_rho` (average ranks; 0.0 when a side is all-ties).

    Raises ValueError on length mismatch, n_permutations < 1, non-finite inputs
    (NaN/inf in `predictions`, `actuals`, or any `predict_fn` output), or a
    `predict_fn` that returns the wrong length — all caller bugs. Every other
    degenerate input (empty, underpowered, ties) returns an honest certificate.
    """
    if len(predictions) != len(actuals):
        raise ValueError(
            f"certify_null_integrity requires equal-length inputs, "
            f"got {len(predictions)} predictions and {len(actuals)} actuals"
        )
    if n_permutations < 1:
        raise ValueError(f"n_permutations must be >= 1, got {n_permutations}")

    predictions = [float(p) for p in predictions]
    actuals = [float(a) for a in actuals]
    # CODEX P2: reject non-finite inputs. A NaN slips through `_sign` as the zero
    # class and inf corrupts ranks/means, so an all-NaN cell could certify
    # passed=True on garbage. The gate exists to certify metric integrity, so
    # non-finite data is a caller bug → raise (consistent with the length /
    # n_permutations guards above), never silently certified.
    _require_finite(predictions, "predictions")
    _require_finite(actuals, "actuals")
    n = len(predictions)
    integrity_hash = _integrity_hash(predictions, actuals, n_permutations=n_permutations, seed=seed)

    # ── Degenerate: empty input → honest VOID, no scores to report. ──
    if n == 0:
        return NullIntegrityCertificate(
            n_experiments=0,
            passed=False,
            void_reason="No experiments to certify (empty input).",
            underpowered=True,
            caveat="Empty input: nothing to score and no null to build.",
            n_permutations=n_permutations,
            seed=seed,
            integrity_hash=integrity_hash,
        )

    # ── Observed scores over the REAL labels. ──
    observed_dir_acc = _direction_accuracy(predictions, actuals)
    observed_rho = spearman_rho(predictions, actuals)

    # ── Bind the certifying predictor to the observed vector (codex P1). ──
    # The same `predict_fn` that drives the null MUST reproduce the submitted
    # `predictions` when run on the REAL labels — otherwise a caller could
    # certify the null with a clean closure while reporting observed scores/hash
    # for a different (leaked) vector, bypassing the gate. We run
    # `predict_fn(actuals)` and require an exact match; a mismatch is an honesty
    # failure → VOID (the certificate refuses to certify inconsistent inputs).
    predict_fn_mismatch = False
    if predict_fn is not None:
        on_real = [float(p) for p in predict_fn(actuals)]
        if len(on_real) != n:
            raise ValueError(
                f"predict_fn returned {len(on_real)} predictions on the real "
                f"labels, expected {n}"
            )
        _require_finite(on_real, "predict_fn(actuals)")
        predict_fn_mismatch = on_real != list(predictions)

    # ── Null distributions: permute the ACTUALS labels in place. ──
    # XOR-mix the seed so this stream is disjoint from the scoring bootstrap.
    # When `predict_fn` is supplied, RE-RUN the cell on each scrambled label set
    # (the faithful §4 protocol): a leaking cell that peeks at labels predicts
    # the scrambled labels too, so its null stays above chance and it VOIDs. An
    # honest cell ignores the labels and reproduces the fixed-prediction null.
    rng = random.Random(seed ^ _PERMUTATION_SEED_MIX)
    null_dir_accs: list[float] = []
    null_rhos: list[float] = []
    for _ in range(n_permutations):
        scrambled = actuals[:]
        rng.shuffle(scrambled)
        if predict_fn is None:
            perm_predictions: Sequence[float] = predictions
        else:
            perm_predictions = [float(p) for p in predict_fn(scrambled)]
            if len(perm_predictions) != n:
                raise ValueError(
                    f"predict_fn returned {len(perm_predictions)} predictions, " f"expected {n}"
                )
            _require_finite(perm_predictions, "predict_fn(scrambled)")
        null_dir_accs.append(_direction_accuracy(perm_predictions, scrambled))
        null_rhos.append(spearman_rho(perm_predictions, scrambled))

    null_dir_mean = sum(null_dir_accs) / n_permutations
    null_rho_mean = sum(null_rhos) / n_permutations
    null_dir_sorted = sorted(null_dir_accs)
    null_rho_sorted = sorted(null_rhos)
    null_dir_ci = _percentile_ci(null_dir_sorted)
    null_rho_ci = _percentile_ci(null_rho_sorted)

    # The TRUE chance baseline for the direction gate is this cell's marginal-
    # expected accuracy under random relabeling — NOT a fixed 0.5 (codex P2).
    # Imbalanced sign marginals (e.g. all-positive actuals) push a clean cell's
    # null well above 0.5; gating against 0.5 would falsely VOID it.
    chance_dir_acc = _marginal_chance_accuracy(predictions, actuals)

    # ── Significance read (SECONDARY): one-sided permutation p-values with the
    # standard +1/+1 add-one correction (Phipson & Smyth 2010), so a p-value is
    # never exactly 0 — the observed result itself counts as one permutation.
    dir_ge = sum(1 for v in null_dir_accs if v >= observed_dir_acc)
    rho_ge = sum(1 for v in null_rhos if v >= observed_rho)
    dir_p = (dir_ge + 1) / (n_permutations + 1)
    rho_p = (rho_ge + 1) / (n_permutations + 1)

    # ── Small-N honesty guard: refuse to certify an underpowered cell. ──
    underpowered = n < _MIN_EXPERIMENTS

    # ── Degenerate-null guard (codex P1): the permutation null only has power to
    # detect leakage if scrambling the labels actually CHANGES them. If every
    # actual is identical (e.g. all-0.0 lift), every permutation is a no-op, the
    # null collapses to a point, and a label-peeking predict_fn that reproduces
    # the labels gets a "clean" (1.0,1.0)/(0.0,0.0) null and would PASS — exactly
    # the case where the integrity test cannot distinguish leakage from a clean
    # model. We require at least 2 distinct actual values so the scramble carries
    # real information; otherwise the null is uninformative and we VOID.
    distinct_actuals = len(set(actuals))
    degenerate_null = distinct_actuals < 2

    # ── PASS/VOID gate (reads the NULL, per §4). ──
    # Direction: the null CI must bracket the cell's MARGINAL chance baseline
    # (`chance_dir_acc`), so an honest-but-skewed sign distribution doesn't void.
    # Rank: the null CI must bracket 0 — permuting labels always centers ρ at 0,
    # so a non-zero-centered rank null is genuine leakage. Either failure means
    # the scrambled-label scores didn't land where a no-information predictor
    # must, i.e. the cell is reading the labels → VOID.
    dir_brackets_chance = null_dir_ci[0] <= chance_dir_acc <= null_dir_ci[1]
    rho_brackets_zero = null_rho_ci[0] <= 0.0 <= null_rho_ci[1]

    void_reason: str | None = None
    caveat: str | None = None
    if predict_fn is None:
        # CODEX P1: the fixed-prediction path keeps the ORIGINAL prediction
        # vector across every permutation, so a cell that leaked the real labels
        # at predict-time (and produced these very predictions) still gets a
        # clean null and would PASS — exactly the failure §4 exists to catch.
        # Certification REQUIRES the faithful rerun (`predict_fn`) so the null
        # re-derives predictions from each scrambled label set. Without it we
        # still report the full diagnostic (observed scores, fixed-prediction
        # null, p-values, hash) but REFUSE to certify: `passed=False`, no
        # `void_reason` (this is "not certifiable here", not "leakage proven").
        passed = False
        caveat = (
            "Non-certifying: certification requires `predict_fn` so the null can "
            "re-run the cell on each scrambled label set (the faithful §4 "
            "protocol). The fixed-prediction path cannot rule out a cell that "
            "leaked labels at predict-time, so PASS is withheld; the reported "
            "scores and fixed-prediction null are diagnostic only."
        )
    elif predict_fn_mismatch:
        # CODEX P1: the certifying predictor must be the one that produced the
        # observed `predictions`. `predict_fn(actuals)` did NOT reproduce the
        # submitted vector, so the null is being built by a DIFFERENT predictor
        # than the one whose scores/hash we report — a caller could otherwise
        # certify a clean closure's null while shipping a leaked observed vector.
        # Inconsistent inputs cannot be certified → VOID.
        passed = False
        void_reason = (
            "Inconsistent inputs — predict_fn(actuals) did not reproduce the "
            "submitted predictions, so the certifying predictor is not the one "
            "whose observed scores and hash are reported. Certification is VOID "
            "until the same predictor produces both the observed vector and the "
            "permutation null."
        )
    elif degenerate_null:
        # CODEX P1: all actuals identical → scrambling is a no-op → the null has
        # no power to detect leakage, so a label-peeking predictor looks clean.
        # Refuse to certify rather than rubber-stamp an uninformative null.
        passed = False
        void_reason = (
            f"Uninformative null — all {n} actual labels are identical "
            f"({distinct_actuals} distinct value), so scrambling cannot change "
            f"them and the permutation null has no power to detect leakage. "
            f"Certification is VOID until the held-out outcomes carry variation."
        )
    elif underpowered:
        passed = False
        caveat = (
            f"Underpowered: {n} experiment(s) is below the certification floor "
            f"of {_MIN_EXPERIMENTS}; the null distribution is too coarse to "
            f"certify 'centers at chance'. Observed scores and the null are "
            f"reported, but this cell cannot PASS until it has more experiments."
        )
    elif dir_brackets_chance and rho_brackets_zero:
        passed = True
    else:
        passed = False
        leaks: list[str] = []
        if not dir_brackets_chance:
            leaks.append(
                f"null direction-accuracy CI {null_dir_ci} does not bracket the "
                f"marginal chance baseline ({chance_dir_acc:.4f})"
            )
        if not rho_brackets_zero:
            leaks.append(f"null rank-ρ CI {null_rho_ci} does not bracket 0")
        void_reason = (
            "Leakage detected — scrambled-label scores do not center at chance: "
            + "; ".join(leaks)
            + ". The run is VOID until the cell no longer predicts scrambled outcomes."
        )

    return NullIntegrityCertificate(
        n_experiments=n,
        observed_direction_accuracy=observed_dir_acc,
        observed_rank_rho=observed_rho,
        null_direction_accuracy_mean=null_dir_mean,
        null_direction_accuracy_ci=null_dir_ci,
        null_rank_rho_mean=null_rho_mean,
        null_rank_rho_ci=null_rho_ci,
        marginal_chance_accuracy=chance_dir_acc,
        certifying=predict_fn is not None,
        passed=passed,
        void_reason=void_reason,
        direction_accuracy_p_value=dir_p,
        rank_rho_p_value=rho_p,
        underpowered=underpowered,
        caveat=caveat,
        n_permutations=n_permutations,
        seed=seed,
        integrity_hash=integrity_hash,
    )
