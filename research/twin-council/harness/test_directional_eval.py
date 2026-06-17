"""
Tests for directional_eval — the G0-G11 certification gate.

Runs with plain CPython (no pytest required):  python3 test_directional_eval.py
Also pytest-discoverable:                       pytest test_directional_eval.py

The integration tests encode the council's core claim: a simulator earns a GO
only by PASSING the gate, and the gate must REFUSE coin-flip simulators, A/A
signal fabrication, leakage, and thin data.
"""
from __future__ import annotations

import math
import random
from typing import List, Tuple

from directional_eval import (
    Experiment, GateConfig, certify,
    sign_with_deadband, wilson_interval, kendall_tau_b, mcc_multiclass,
    brier_multiclass, brier_climatology, expected_calibration_error,
    balanced_sign_match_rate, aa_false_signal_rate, label_permutation_smr,
    decision_utility, tail_winner_recall,
)

DELTA = 0.03


# --------------------------------------------------------------------------- #
# Synthetic backtest generators
# --------------------------------------------------------------------------- #
def _make_probs(pred_class: int, conf: float) -> Tuple[float, float, float]:
    other = (1 - conf) / 2
    if pred_class == 1:
        return (conf, other, other)
    if pred_class == 0:
        return (other, conf, other)
    return (other, other, conf)


def generate_backtest(n: int, base_acc: float, g_noise: float,
                      seed: int = 0) -> List[Experiment]:
    """A simulator with controllable directional accuracy and ranking noise."""
    rng = random.Random(seed)
    exps: List[Experiment] = []
    for i in range(n):
        u = rng.random()
        if u < 0.45:
            true_class = 1
            eff = rng.uniform(0.04, 0.30)
        elif u < 0.90:
            true_class = -1
            eff = -rng.uniform(0.04, 0.30)
        else:
            true_class = 0
            eff = rng.uniform(-0.02, 0.02)
        # easier (bigger) effects are called more confidently and more correctly
        # -> calibrated confidence separates strong winners from marginal ones,
        #    which is exactly what good tail-ranking requires.
        c = base_acc + 0.8 * (abs(eff) - 0.12) + rng.gauss(0, 0.03)
        c = min(0.98, max(0.40, c))
        if rng.random() < c:
            pred_class = true_class
        else:
            pred_class = rng.choice([k for k in (-1, 0, 1) if k != true_class])
        pp, pf, pn = _make_probs(pred_class, c)
        g = eff + rng.gauss(0, g_noise)
        exps.append(Experiment(f"e{i}", eff, g, pp, pf, pn))
    rng.shuffle(exps)  # input order = PM's arbitrary backlog order (baseline)
    return exps


def generate_aa(n: int, fabricate: bool, seed: int = 1) -> List[Experiment]:
    """A/A placebo records. Honest sim -> low-confidence flat. fabricate=True ->
    it invents actionable directional calls (should fail G1)."""
    rng = random.Random(seed)
    out: List[Experiment] = []
    for i in range(n):
        if fabricate:
            pred_class = rng.choice([-1, 1])
            pp, pf, pn = _make_probs(pred_class, rng.uniform(0.72, 0.9))
        else:
            pp, pf, pn = _make_probs(0, rng.uniform(0.45, 0.6))
        out.append(Experiment(f"aa{i}", 0.0, rng.gauss(0, 0.01), pp, pf, pn,
                              is_aa=True))
    return out


# --------------------------------------------------------------------------- #
# Unit tests — primitives
# --------------------------------------------------------------------------- #
def test_sign_deadband():
    assert sign_with_deadband(0.10, 0.03) == 1
    assert sign_with_deadband(-0.10, 0.03) == -1
    assert sign_with_deadband(0.01, 0.03) == 0
    assert sign_with_deadband(-0.02, 0.03) == 0


def test_wilson_interval_basic():
    lo, hi = wilson_interval(35, 50, 0.90)
    assert 0.0 <= lo < 0.70 < hi <= 1.0
    # wider n -> tighter interval
    lo2, hi2 = wilson_interval(140, 200, 0.90)
    assert (hi2 - lo2) < (hi - lo)
    # the paper's quoted numbers for SMR 0.70
    lo50, hi50 = wilson_interval(35, 50, 0.90)
    assert abs((hi50 - lo50) - 0.209) < 0.02
    lo200, hi200 = wilson_interval(140, 200, 0.90)
    assert abs((hi200 - lo200) - 0.106) < 0.02


def test_kendall_tau_b():
    assert abs(kendall_tau_b([1, 2, 3, 4], [1, 2, 3, 4]) - 1.0) < 1e-9
    assert abs(kendall_tau_b([1, 2, 3, 4], [4, 3, 2, 1]) + 1.0) < 1e-9
    assert abs(kendall_tau_b([1, 2, 3, 4], [1, 1, 1, 1])) < 1e-9  # all ties


def test_mcc_perfect_and_chance():
    # perfect predictions -> MCC = 1
    perfect = [Experiment("a", 0.2, 0.2, 0.9, 0.05, 0.05),
               Experiment("b", -0.2, -0.2, 0.05, 0.05, 0.9),
               Experiment("c", 0.0, 0.0, 0.05, 0.9, 0.05)]
    assert abs(mcc_multiclass(perfect, DELTA) - 1.0) < 1e-9


def test_brier_climatology_beats_uniform_nonsense():
    exps = generate_backtest(100, base_acc=0.8, g_noise=0.05, seed=3)
    assert brier_multiclass(exps, DELTA) < brier_climatology(exps, DELTA)


def test_ece_zero_for_calibrated():
    # by construction confidence == P(correct); ECE should be small on big n
    exps = generate_backtest(800, base_acc=0.78, g_noise=0.05, seed=4)
    assert expected_calibration_error(exps, DELTA) < 0.06


# --------------------------------------------------------------------------- #
# Integration tests — the gate
# --------------------------------------------------------------------------- #
def _clean_predict_fn(effect: float) -> Tuple[float, float, float]:
    # ignores the label entirely -> permutation collapses to ~0.5
    return (1 / 3, 1 / 3, 1 / 3)


def _leaking_predict_fn(effect: float) -> Tuple[float, float, float]:
    # peeks at the true effect -> stays accurate under permutation -> caught
    return _make_probs(sign_with_deadband(effect, DELTA), 0.9)


def test_good_simulator_gets_GO():
    exps = generate_backtest(200, base_acc=0.84, g_noise=0.04, seed=10)
    aa = generate_aa(60, fabricate=False, seed=11)
    cfg = GateConfig(delta=DELTA, budget=50, baseline_mcc=0.0,
                     sign_flip_rate=0.05, leakage_predict_fn=_clean_predict_fn,
                     bootstrap_trials=400, seed=10)
    res = certify(exps, aa, cfg)
    assert res.verdict == "GO", str(res)
    assert res.metrics["balanced_smr"] >= 0.70
    assert res.metrics["smr_wilson_lo90"] > 0.55
    assert res.metrics["delta_u_lo90"] > 0.0
    assert res.metrics["tail_winner_recall"] >= 0.80


def test_coin_flip_simulator_is_NOGO():
    exps = generate_backtest(200, base_acc=0.34, g_noise=5.0, seed=20)
    aa = generate_aa(60, fabricate=False, seed=21)
    cfg = GateConfig(delta=DELTA, budget=50, leakage_predict_fn=_clean_predict_fn,
                     bootstrap_trials=300, seed=20)
    res = certify(exps, aa, cfg)
    assert res.verdict == "NO-GO", str(res)


def test_thin_data_is_NOGO():
    exps = generate_backtest(30, base_acc=0.85, g_noise=0.04, seed=30)
    aa = generate_aa(20, fabricate=False, seed=31)
    cfg = GateConfig(delta=DELTA, budget=8, leakage_predict_fn=_clean_predict_fn,
                     bootstrap_trials=200, seed=30)
    res = certify(exps, aa, cfg)
    assert res.verdict == "NO-GO", str(res)
    assert res.gates["G0_floor"] is False


def test_aa_fabrication_is_NOGO():
    exps = generate_backtest(200, base_acc=0.84, g_noise=0.04, seed=40)
    aa = generate_aa(60, fabricate=True, seed=41)   # invents directional calls
    cfg = GateConfig(delta=DELTA, budget=50, leakage_predict_fn=_clean_predict_fn,
                     bootstrap_trials=300, seed=40)
    res = certify(exps, aa, cfg)
    assert res.verdict == "NO-GO", str(res)
    assert res.gates["G1_aa"] is False


def test_leakage_is_caught_and_NOGO():
    exps = generate_backtest(200, base_acc=0.84, g_noise=0.04, seed=50)
    aa = generate_aa(60, fabricate=False, seed=51)
    cfg = GateConfig(delta=DELTA, budget=50, leakage_predict_fn=_leaking_predict_fn,
                     bootstrap_trials=300, seed=50)
    res = certify(exps, aa, cfg)
    assert res.gates["G3_leakage"] is False, str(res)
    assert res.verdict == "NO-GO", str(res)


def test_clean_simulator_passes_leakage_probe():
    exps = generate_backtest(200, base_acc=0.84, g_noise=0.04, seed=60)
    perm = label_permutation_smr(exps, DELTA, predict_fn=_clean_predict_fn,
                                 trials=100, seed=60)
    assert 0.40 <= perm <= 0.60


def test_high_ece_blocks_GO():
    # take a good sim but corrupt confidences to be overconfident -> ECE up
    exps = generate_backtest(200, base_acc=0.70, g_noise=0.04, seed=70)
    bad = []
    for e in exps:
        ps = e.pred_sign()
        pp, pf, pn = _make_probs(ps, 0.98)  # claim 0.98 regardless of accuracy
        bad.append(Experiment(e.id, e.true_effect, e.g, pp, pf, pn))
    cfg = GateConfig(delta=DELTA, budget=50, leakage_predict_fn=_clean_predict_fn,
                     bootstrap_trials=200, seed=70)
    res = certify(bad, generate_aa(60, False, 71), cfg)
    assert res.metrics["ece"] > 0.08
    assert res.verdict != "GO", str(res)


# --------------------------------------------------------------------------- #
# Plain-CPython runner
# --------------------------------------------------------------------------- #
def _run_all() -> int:
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as ex:
            failures += 1
            print(f"FAIL  {t.__name__}: {ex}")
        except Exception as ex:  # noqa: BLE001
            failures += 1
            print(f"ERROR {t.__name__}: {type(ex).__name__}: {ex}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return failures


if __name__ == "__main__":
    import sys
    sys.exit(1 if _run_all() else 0)
