"""
predict_streamly_challenge.py — BLIND predictions for the Synthetic Streamly Challenge.

Runs the FROZEN causal_estimator on each dataset using only the public index (schema). The
author does not know which file is which regime (secret-shuffled), so these predictions are
not tunable to the answers. Writes synthetic_streamly_predictions.json; this is committed
BEFORE the sealed key is read by the scorer.

Pre-registered prediction procedure (fixed here, before scoring):
  treatment=got_feature, outcome=outcome, covariates=index covariate_cols; estimator=t-learner
  (primary) + IPW; null band = 0.005 (binary) / 0.05 (continuous); confidence=low if not
  supportable or overlap<0.5.

  /opt/homebrew/bin/python3.11 research/empirical-uplift-spike/predict_streamly_challenge.py
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from causal_estimator import support_check, estimate  # noqa: E402

INDEX = HERE / "synthetic_streamly_index.json"
DATA = HERE / ".data" / "synthetic_streamly"
OUT = HERE / "synthetic_streamly_predictions.json"
NULL_BAND = {"binary": 0.005, "continuous": 0.05}


def winner(ate, otype):
    band = NULL_BAND[otype]
    return "treatment" if ate > band else "control" if ate < -band else "null/uncertain"


def main():
    idx = json.loads(INDEX.read_text())["datasets"]
    preds = []
    for d in idx:
        df = pd.read_csv(DATA / d["filename"])
        T, Y, X = d["treatment_col"], d["outcome_col"], d["covariate_cols"]
        sup = support_check(df, T, Y, X)
        est = estimate(df, T, Y, X)
        otype = d["outcome_type"]
        conf = "low" if (not sup.supportable or est.overlap_fraction < 0.5) else "high"
        preds.append(dict(
            filename=d["filename"], outcome_type=otype, supportable=sup.supportable,
            overlap_fraction=round(est.overlap_fraction, 3),
            naive_ate=round(est.naive_ate, 4), naive_sign="positive" if est.naive_ate > 0 else "negative",
            t_learner_ate=round(est.t_learner_ate, 4), t_learner_sign=est.sign_adjusted,
            ipw_ate=round(est.ipw_ate, 4), ipw_sign="positive" if est.ipw_ate > 0 else "negative",
            naive_winner=winner(est.naive_ate, otype),
            predicted_winner=winner(est.t_learner_ate, otype),  # causal is the prediction
            confidence=conf))
    OUT.write_text(json.dumps({"procedure": "t-learner primary; IPW secondary; blind",
                               "predictions": preds}, indent=2))
    print(f"wrote {OUT.name} — {len(preds)} blind predictions")
    for p in preds:
        print(f"  {p['filename']}: naive={p['naive_winner']:13} causal={p['predicted_winner']:13} "
              f"(t_learner={p['t_learner_ate']:+.4f}, overlap={p['overlap_fraction']}, conf={p['confidence']})")


if __name__ == "__main__":
    main()
