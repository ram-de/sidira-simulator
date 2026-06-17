"""Tests for directional_gate — the G0-G11 certification gate.

Pytest-discoverable; also runnable standalone:
    PYTHONPATH=. <venv>/bin/python tests/test_directional_gate.py
"""
from __future__ import annotations

import random

from sidira_simulator.services.directional_gate import (
    ExperimentRecord, GateConfig, certify, fit_calibration,
    balanced_sign_match_rate, kendall_tau_b, mcc_multiclass,
    label_permutation_smr, aa_false_signal_rate, _sign_dead,
)

DELTA = 0.03


def gen(n, signal_noise, scale=1.0, seed=0):
    rng = random.Random(seed)
    out = []
    for i in range(n):
        u = rng.random()
        if u < 0.45:
            eff = rng.uniform(0.04, 0.30)
        elif u < 0.90:
            eff = -rng.uniform(0.04, 0.30)
        else:
            eff = rng.uniform(-0.02, 0.02)
        sig = eff * scale + rng.gauss(0, signal_noise)
        out.append(ExperimentRecord(f"c{i}", eff, sig))
    rng.shuffle(out)
    return out


def gen_aa(n, fabricate, seed=1):
    rng = random.Random(seed)
    out = []
    for i in range(n):
        if fabricate:
            ps = rng.choice([-1, 1]); conf = rng.uniform(0.72, 0.9)
            pp, pf, pn = (conf, (1 - conf) / 2, (1 - conf) / 2) if ps == 1 \
                else ((1 - conf) / 2, (1 - conf) / 2, conf)
        else:
            conf = rng.uniform(0.45, 0.6)
            pp, pf, pn = (1 - conf) / 2, conf, (1 - conf) / 2
        r = ExperimentRecord(f"aa{i}", 0.0, rng.gauss(0, 0.005), pp, pf, pn, is_aa=True)
        out.append(r)
    return out


# ---- primitives ----
def test_sign_deadband():
    assert _sign_dead(0.1, 0.03) == 1
    assert _sign_dead(-0.1, 0.03) == -1
    assert _sign_dead(0.01, 0.03) == 0


def test_kendall_extremes():
    assert abs(kendall_tau_b([1, 2, 3], [1, 2, 3]) - 1.0) < 1e-9
    assert abs(kendall_tau_b([1, 2, 3], [3, 2, 1]) + 1.0) < 1e-9


def test_calibration_fills_probs_out_of_fold():
    recs = gen(120, signal_noise=0.04, seed=2)
    assert recs[0].p_pos is None
    fit_calibration(recs, DELTA, seed=2)
    assert all(r.p_pos is not None for r in recs)
    for r in recs:
        s = r.p_pos + r.p_flat + r.p_neg
        assert abs(s - 1.0) < 1e-6
        assert 0 <= r.p_pos <= 1


# ---- gate integration ----
def _clean_fn(eff):
    return (1 / 3, 1 / 3, 1 / 3)


def _leaking_fn(eff):
    s = _sign_dead(eff, DELTA)
    return (0.9, 0.05, 0.05) if s == 1 else ((0.05, 0.9, 0.05) if s == 0 else (0.05, 0.05, 0.9))


def test_good_simulator_GO():
    recs = gen(200, signal_noise=0.03, seed=10)
    cfg = GateConfig(delta=DELTA, budget=50, sign_flip_rate=0.05,
                     leakage_predict_fn=_clean_fn, bootstrap_trials=400, seed=10)
    res = certify(recs, cfg, aa=gen_aa(60, fabricate=False, seed=11))
    assert res.verdict == "GO", res.summary()
    assert res.metrics["balanced_smr"] >= 0.70
    assert res.metrics["delta_u_lo"] > 0
    assert res.metrics["tail_winner_recall"] >= 0.80


def test_coin_flip_NOGO():
    recs = gen(200, signal_noise=5.0, scale=0.0, seed=20)
    cfg = GateConfig(delta=DELTA, budget=50, leakage_predict_fn=_clean_fn,
                     bootstrap_trials=300, seed=20)
    res = certify(recs, cfg, aa=gen_aa(60, False, 21))
    assert res.verdict == "NO-GO", res.summary()


def test_thin_data_NOGO():
    recs = gen(30, signal_noise=0.03, seed=30)
    cfg = GateConfig(delta=DELTA, budget=8, leakage_predict_fn=_clean_fn,
                     bootstrap_trials=200, seed=30)
    res = certify(recs, cfg, aa=gen_aa(20, False, 31))
    assert res.verdict == "NO-GO"
    assert res.gates["G0_floor"] is False


def test_aa_fabrication_NOGO():
    recs = gen(200, signal_noise=0.03, seed=40)
    cfg = GateConfig(delta=DELTA, budget=50, leakage_predict_fn=_clean_fn,
                     bootstrap_trials=300, seed=40)
    res = certify(recs, cfg, aa=gen_aa(60, fabricate=True, seed=41))
    assert res.verdict == "NO-GO"
    assert res.gates["G1_aa"] is False


def test_leakage_caught_NOGO():
    recs = gen(200, signal_noise=0.03, seed=50)
    cfg = GateConfig(delta=DELTA, budget=50, leakage_predict_fn=_leaking_fn,
                     bootstrap_trials=300, seed=50)
    res = certify(recs, cfg, aa=gen_aa(60, False, 51))
    assert res.gates["G3_leakage"] is False, res.summary()
    assert res.verdict == "NO-GO"


def test_clean_passes_permutation():
    recs = gen(200, signal_noise=0.03, seed=60)
    perm = label_permutation_smr(recs, DELTA, predict_fn=_clean_fn, trials=100, seed=60)
    assert 0.40 <= perm <= 0.60


if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    fails = 0
    for f in fns:
        try:
            f(); print("PASS", f.__name__)
        except AssertionError as e:
            fails += 1; print("FAIL", f.__name__, str(e)[:200])
        except Exception as e:
            fails += 1; print("ERROR", f.__name__, type(e).__name__, str(e)[:200])
    print(f"\n{len(fns)-fails}/{len(fns)} passed")
    sys.exit(1 if fails else 0)
