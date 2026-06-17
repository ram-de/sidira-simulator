"""Supervised lever (#342): the white paper's thesis — LLM signal + structural
features fed to a CROSS-FIT calibrator trained on REAL CTR. Zero new LLM spend:
reuses the 300 cached comparative/popshare Sonnet signals (two disjoint slices)
and adds rule-based headline features. Tests whether learning the mapping from
outcomes pushes the confirmed zero-shot signal past the GO bars.

Pre-registered feature list + model + CV (no feature selection, no tuning) to
avoid fishing. Out-of-fold predictions only; scored through the G0-G11 gate.

    PYTHONPATH=backend <venv>/bin/python <thisfile>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import model_comparison_probe as MCP
from sidira_simulator.services.directional_gate import ExperimentRecord, GateConfig, certify

CURIOSITY = {"this", "what", "why", "how", "secret", "never", "actually", "will",
             "when", "reason", "these", "before", "after", "real", "truth", "happens",
             "you", "your", "one", "thing", "everything", "nobody", "everyone"}


def feats(h: str) -> dict:
    words = re.findall(r"\w+", h.lower())
    return {
        "len": len(h),
        "nwords": len(words),
        "num": 1.0 if re.search(r"\d", h) else 0.0,
        "q": 1.0 if "?" in h else 0.0,
        "excl": 1.0 if "!" in h else 0.0,
        "colon": 1.0 if ":" in h else 0.0,
        "caps": sum(1 for w in re.findall(r"[A-Za-z]+", h) if w.isupper() and len(w) > 1),
        "you": 1.0 if ("you" in words or "your" in words) else 0.0,
        "curio": sum(1 for w in words if w in CURIOSITY),
    }


def structural_diff(ctl: str, trt: str) -> list[float]:
    fc, ft = feats(ctl), feats(trt)
    return [ft[k] - fc[k] for k in ("len", "nwords", "num", "q", "excl", "colon", "caps", "you", "curio")]


def load_300():
    orig = MCP.original_test_ids()
    s1 = MCP.load_fresh_cases(150, orig)
    s1_tids = {c["case_id"].split(":")[0] for c in s1}
    s2 = MCP.load_fresh_cases(150, orig | s1_tids)
    sig = {}
    for mode in ("comparative", "popshare"):
        sig[mode] = {}
        for suff, cs in (("", s1), ("_confirm", s2)):
            d = json.loads((HERE / f"levers_ckpt_{mode}_sonnet{suff}.json").read_text())["sig"]
            sig[mode].update(d)
    rows = []
    for cs in (s1, s2):
        for c in cs:
            cid = c["case_id"]
            if cid not in sig["comparative"] or cid not in sig["popshare"]:
                continue
            rows.append({
                "case_id": cid,
                "y": 1 if c["observed_lift"] > 0 else 0,
                "observed_lift": c["observed_lift"],
                "struct": structural_diff(c["control_hl"], c["treatment_hl"]),
                "elicited": [sig["comparative"][cid], sig["popshare"][cid]],
            })
    return rows


def score_feature_set(rows, name, get_X, seed=42):
    X = np.array([get_X(r) for r in rows], dtype=float)
    y = np.array([r["y"] for r in rows])
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    p = cross_val_predict(clf, X, y, cv=cv, method="predict_proba")[:, 1]  # out-of-fold P(T wins)
    recs = [ExperimentRecord(r["case_id"], r["observed_lift"], float(p[i]) - 0.5)
            for i, r in enumerate(rows)]
    cfg = GateConfig(delta=0.0, budget=max(1, len(recs) // 4), bootstrap_trials=4000,
                     seed=seed, conf=0.90)
    res = certify(recs, cfg)
    m = res.metrics
    print(f"\n=== {name} (cross-fit, n={len(recs)}) ===")
    print(f"  SMR {m['balanced_smr']:.3f} (LB {m['smr_wilson_lo']:.3f}) | "
          f"Kendall tau_b {m['kendall_tau_b']:+.3f} (LB {m['kendall_tau_b_lo']:+.3f}) | "
          f"MCC {m['mcc']:+.3f} (LB {m['mcc_lo']:+.3f})")
    print(f"  ECE {m['ece']:.3f} | Brier-skill {m['brier_skill']:+.3f} | "
          f"dU {m['delta_u']:+.1f} (LB {m['delta_u_lo']:+.1f}) | tail {m['tail_winner_recall']:.2f}")
    print(f"  VERDICT: {res.verdict}  | passing: {sorted(g for g,v in res.gates.items() if v)}")
    return {"name": name, "verdict": res.verdict, "metrics": m, "gates": res.gates, "n": len(recs)}


def main() -> int:
    rows = load_300()
    print(f"loaded {len(rows)} cases with both signals; "
          f"{sum(r['y'] for r in rows)} pos / {len(rows)-sum(r['y'] for r in rows)} neg")
    out = {}
    out["structural_only"] = score_feature_set(rows, "structural features only", lambda r: r["struct"])
    out["elicited_only"] = score_feature_set(rows, "elicited signals only (comparative+popshare)", lambda r: r["elicited"])
    out["combined"] = score_feature_set(rows, "structural + elicited (combined)", lambda r: r["struct"] + r["elicited"])
    (HERE / "supervised_calibration_result.json").write_text(json.dumps(out, indent=2, default=float))
    print("\nwrote supervised_calibration_result.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
