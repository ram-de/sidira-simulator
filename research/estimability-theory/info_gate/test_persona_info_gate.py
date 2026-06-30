"""
Self-validating test for the persona information-sufficiency gate.

Builds synthetic persona packs where the right answer is KNOWN by construction,
and asserts the gate's PASS/FAIL partition matches ground truth. This is how we
prove the gate works BEFORE any design-partner data exists.

Run: /opt/homebrew/bin/python3.11 test_persona_info_gate.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from persona_info_gate import GateConfig, HypothesisSpec, evaluate

N = 2000
SEED = 7


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def _base_demographics(rng):
    return pd.DataFrame({
        "age": rng.integers(18, 70, N),
        "region": rng.choice(["north", "south", "east", "west"], N),
    })


def make_sufficient(rng):
    """overload_sensitivity varies AND drives the pre-test proxy -> PASS."""
    df = _base_demographics(rng)
    df["overload_sensitivity"] = rng.normal(0, 1, N)
    p = _sigmoid(2.0 * df["overload_sensitivity"] + rng.normal(0, 0.3, N))
    df["browse_abandon"] = (rng.random(N) < p).astype(int)  # pre-test proxy, binary
    return df


def make_absent(rng):
    """Mechanism feature simply not in the pack -> L0 FAIL."""
    df = _base_demographics(rng)
    df["browse_abandon"] = rng.integers(0, 2, N)             # proxy present, signal absent
    return df  # no 'overload_sensitivity' column


def make_degenerate(rng):
    """Feature present but constant -> L1 FAIL."""
    df = _base_demographics(rng)
    df["overload_sensitivity"] = 0.5                          # no variance
    df["browse_abandon"] = rng.integers(0, 2, N)
    return df


def make_noise(rng):
    """Feature present & varying but unrelated to the proxy -> L2 FAIL."""
    df = _base_demographics(rng)
    df["overload_sensitivity"] = rng.normal(0, 1, N)
    df["browse_abandon"] = rng.integers(0, 2, N)             # independent of the feature
    return df


def make_partial(rng):
    """Two mechanism features: one absent, one present-and-discriminative.
    The gate should still PASS via the usable one (graceful coverage)."""
    df = _base_demographics(rng)
    df["price_sensitivity"] = rng.normal(0, 1, N)
    p = _sigmoid(1.8 * df["price_sensitivity"] + rng.normal(0, 0.3, N))
    df["cart_abandon"] = (rng.random(N) < p).astype(int)
    return df  # 'discount_affinity' (also requested) is absent


HYP_OVERLOAD = HypothesisSpec(
    id="themes_vs_products",
    change="show themed collections instead of individual products",
    mechanism="reduces choice overload",
    mechanism_features=["overload_sensitivity"],
    proxy="browse_abandon",
    proxy_kind="binary",
)
HYP_PARTIAL = HypothesisSpec(
    id="discount_banner",
    change="surface a discount banner",
    mechanism="price sensitivity",
    mechanism_features=["discount_affinity", "price_sensitivity"],  # first is absent
    proxy="cart_abandon",
    proxy_kind="binary",
)

CASES = [
    ("sufficient",  make_sufficient,  HYP_OVERLOAD, True,  None),
    ("absent",      make_absent,      HYP_OVERLOAD, False, "L0"),
    ("degenerate",  make_degenerate,  HYP_OVERLOAD, False, "L1"),
    ("noise",       make_noise,       HYP_OVERLOAD, False, "L2"),
    ("partial_cov", make_partial,     HYP_PARTIAL,  True,  None),
]


def main():
    cfg = GateConfig()
    rows, failures = [], []
    for name, maker, hyp, want_pass, want_tier in CASES:
        rng = np.random.default_rng(SEED)
        pack = maker(rng)
        res = evaluate(pack, hyp, cfg)
        ok = (res.passed == want_pass) and (res.tier_failed == want_tier)
        rows.append({
            "case": name, "expect_pass": want_pass, "got_pass": res.passed,
            "expect_tier": want_tier, "got_tier": res.tier_failed,
            "usable": res.usable_features, "reason": res.reason,
            "l2": {k: round(v, 4) for k, v in res.l2.items() if isinstance(v, float)},
            "correct": ok,
        })
        if not ok:
            failures.append(name)

    print(f"\n{'case':<13} {'want':<6} {'got':<6} {'tier':<6} {'ok':<4} reason")
    print("-" * 100)
    for r in rows:
        print(f"{r['case']:<13} {str(r['expect_pass']):<6} {str(r['got_pass']):<6} "
              f"{str(r['got_tier'] or '-'):<6} {'✓' if r['correct'] else '✗':<4} {r['reason']}")

    out = Path(__file__).parent / "test_result.json"
    out.write_text(json.dumps({"all_correct": not failures, "failures": failures,
                               "cases": rows, "config": cfg.__dict__}, indent=2))
    print(f"\nwrote {out.name}")

    assert not failures, f"GATE MISCLASSIFIED: {failures}"
    print("ALL CASES CORRECT — gate partitions known ground truth as designed.")


if __name__ == "__main__":
    main()
