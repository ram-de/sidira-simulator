"""
predict_streamly_v2.py — BLIND predictions + NEGATIVE-CONTROL guard (iter1).

Per the sealed PREREG_ITER1_NEGCONTROL.md: estimate the main treatment->outcome effect AND
the treatment->neg_control effect (adjusting for observed covariates). Guard: a main estimate
is downgraded to low/abstain when |neg_control effect| > NC_BAND (residual confounding the
negative control can see but overlap cannot).

  /opt/homebrew/bin/python3.11 research/empirical-uplift-spike/predict_streamly_v2.py
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from causal_estimator import support_check, estimate  # noqa: E402

INDEX = HERE / "synthetic_streamly_v2_index.json"
DATA = HERE / ".data" / "synthetic_streamly_v2"
OUT = HERE / "synthetic_streamly_v2_predictions.json"
NULL_BAND = {"binary": 0.005, "continuous": 0.05}
NC_BAND = 0.02


def winner(ate, otype):
    b = NULL_BAND[otype]
    return "treatment" if ate > b else "control" if ate < -b else "null/uncertain"


def main():
    idx = json.loads(INDEX.read_text())["datasets"]
    preds = []
    for d in idx:
        df = pd.read_csv(DATA / d["filename"])
        T, Y, NCc, X = d["treatment_col"], d["outcome_col"], d["neg_control_col"], d["covariate_cols"]
        est = estimate(df, T, Y, X)
        nc = estimate(df, T, NCc, X)                  # treatment -> negative control
        sup = support_check(df, T, Y, X)
        nc_tripped = bool(abs(nc.t_learner_ate) > NC_BAND)
        overlap_low = bool(est.overlap_fraction < 0.5)
        conf = "low/abstain" if (nc_tripped or not sup.supportable or overlap_low) else "high"
        preds.append(dict(
            filename=d["filename"], outcome_type=d["outcome_type"], supportable=sup.supportable,
            overlap_fraction=round(est.overlap_fraction, 3),
            naive_ate=round(est.naive_ate, 4), naive_winner=winner(est.naive_ate, d["outcome_type"]),
            t_learner_ate=round(est.t_learner_ate, 4),
            predicted_winner=winner(est.t_learner_ate, d["outcome_type"]),
            neg_control_ate=round(nc.t_learner_ate, 4), neg_control_tripped=nc_tripped,
            confidence=conf))
    OUT.write_text(json.dumps({"procedure": "t-learner + negative-control guard; blind",
                               "nc_band": NC_BAND, "predictions": preds}, indent=2))
    print(f"wrote {OUT.name} — {len(preds)} predictions")
    for p in preds:
        print(f"  {p['filename']}: causal={p['predicted_winner']:13} nc_ate={p['neg_control_ate']:+.4f} "
              f"{'TRIP' if p['neg_control_tripped'] else '   ·'} -> conf={p['confidence']}")


if __name__ == "__main__":
    main()
