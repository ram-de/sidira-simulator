"""X5 RetailHero RICH-covariate follow-up — Step 2: REAL ground-truth uplift
ranking over BEHAVIORAL (RFM) segments.

Mirrors x5-benchmark/build_ground_truth.py but segments on PRE-TREATMENT
purchase-history features (recency / frequency / monetary tertiles) instead of
demographics. Per-segment REAL uplift = mean(target|T=1) - mean(target|T=0).

Segmentation: independent tertiles (low / mid / high) of Recency, Frequency,
Monetary over the eligible population (clients in uplift_train that ALSO have
pre-cutoff behavioral features). 3x3x3 = up to 27 cells; cells with < FLOOR per
arm are dropped (listed). Tertile cutpoints are computed from FEATURES ONLY,
never from uplift -> no leakage into the ground-truth definition.

Recency tier semantics: LOW recency_days = shopped most RECENTLY (best). We
label tiers by behavior, not raw quantile direction, in describe()/forecaster.

    PYTHONPATH=backend <venv>/bin/python build_ground_truth.py
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
FLOOR = 200  # n per arm


def tier(value: float, lo: float, hi: float) -> str:
    """3-way split by the two tertile cutpoints (lo=33rd, hi=66th pct)."""
    if value <= lo:
        return "low"
    if value <= hi:
        return "mid"
    return "high"


def main() -> int:
    feats = json.loads((DATA / "client_features.json").read_text())

    # Treatment + target, restricted to clients that have behavioral features.
    tr: dict[str, tuple[int, int]] = {}
    n_uplift = n_match = 0
    with gzip.open(DATA / "uplift_train.csv.gz", "rt") as f:
        for r in csv.DictReader(f):
            n_uplift += 1
            cid = r["client_id"]
            if cid in feats:
                tr[cid] = (int(r["treatment_flg"]), int(r["target"]))
                n_match += 1

    elig = list(tr.keys())
    rec = np.array([feats[c]["recency_days"] for c in elig], dtype=float)
    freq = np.array([feats[c]["frequency_txns"] for c in elig], dtype=float)
    mon = np.array([feats[c]["monetary_total"] for c in elig], dtype=float)

    cut = {
        "recency": (float(np.quantile(rec, 1 / 3)), float(np.quantile(rec, 2 / 3))),
        "frequency": (float(np.quantile(freq, 1 / 3)), float(np.quantile(freq, 2 / 3))),
        "monetary": (float(np.quantile(mon, 1 / 3)), float(np.quantile(mon, 2 / 3))),
    }

    cells: dict[tuple, dict[int, list]] = defaultdict(
        lambda: {0: [0, 0], 1: [0, 0]}  # arm -> [target_sum, n]
    )
    # Per-segment feature accumulators (means) for the blinded description.
    feat_acc: dict[tuple, dict] = defaultdict(
        lambda: {"recency": [], "frequency": [], "monetary": [],
                 "basket": [], "breadth": [], "redeem": []}
    )
    for cid in elig:
        fdat = feats[cid]
        rt = tier(fdat["recency_days"], *cut["recency"])
        ft = tier(fdat["frequency_txns"], *cut["frequency"])
        mt = tier(fdat["monetary_total"], *cut["monetary"])
        key = (rt, ft, mt)
        t, y = tr[cid]
        cells[key][t][0] += y
        cells[key][t][1] += 1
        fa = feat_acc[key]
        fa["recency"].append(fdat["recency_days"])
        fa["frequency"].append(fdat["frequency_txns"])
        fa["monetary"].append(fdat["monetary_total"])
        fa["basket"].append(fdat["basket_avg_lines"])
        fa["breadth"].append(fdat["category_breadth"])
        fa["redeem"].append(fdat["redeem_txn_share"])

    segments, dropped = [], []
    for key in sorted(cells):
        c = cells[key]
        nT, nC = c[1][1], c[0][1]
        rt, ft, mt = key
        seg_id = f"R-{rt}/F-{ft}/M-{mt}"
        if nT < FLOOR or nC < FLOOR:
            dropped.append({"segment": seg_id, "n_treatment": nT, "n_control": nC,
                            "reason": f"below floor n>={FLOOR}/arm"})
            continue
        rate_t = c[1][0] / nT
        rate_c = c[0][0] / nC
        fa = feat_acc[key]
        segments.append({
            "segment": seg_id,
            "recency_tier": rt, "frequency_tier": ft, "monetary_tier": mt,
            "n_treatment": nT, "n_control": nC,
            "target_rate_treatment": rate_t,
            "target_rate_control": rate_c,
            "uplift": rate_t - rate_c,
            "mean_recency_days": round(float(np.mean(fa["recency"])), 1),
            "mean_frequency_txns": round(float(np.mean(fa["frequency"])), 2),
            "mean_monetary_total": round(float(np.mean(fa["monetary"])), 1),
            "mean_basket_lines": round(float(np.mean(fa["basket"])), 2),
            "mean_category_breadth": round(float(np.mean(fa["breadth"])), 1),
            "mean_redeem_share": round(float(np.mean(fa["redeem"])), 3),
        })

    seg_ids = [s["segment"] for s in segments]
    uplift_vector = [s["uplift"] for s in segments]
    canonical = json.dumps(
        [{"segment": s, "uplift": round(u, 10)} for s, u in zip(seg_ids, uplift_vector)],
        sort_keys=False,
    )
    sha = hashlib.sha256(canonical.encode()).hexdigest()

    out = {
        "dataset": "X5 RetailHero uplift (scikit-uplift S3 mirror) — RICH behavioral covariates",
        "source_files": ["clients.csv.gz (unused here)", "uplift_train.csv.gz", "purchases.csv.gz"],
        "treatment": "retailer SMS promotion (treatment_flg=1) vs no-SMS holdout (=0)",
        "target": "binary purchase/redeem outcome (target)",
        "covariates_used": ["pre-treatment recency tertile", "frequency tertile", "monetary tertile",
                            "(+ basket size, category breadth, redeem share in descriptions)"],
        "pre_treatment_cutoff": "2019-02-19 (purchases strictly before)",
        "tertile_cutpoints": cut,
        "floor_per_arm": FLOOR,
        "n_uplift_train_rows": n_uplift,
        "n_matched_with_features": n_match,
        "n_segments": len(segments),
        "n_segments_dropped": len(dropped),
        "uplift_min": min(uplift_vector),
        "uplift_max": max(uplift_vector),
        "canonical_uplift_vector_order": "by segment id, lexicographic sort",
        "ground_truth_sha256": sha,
        "segments": segments,
        "dropped_segments": dropped,
    }
    (HERE / "x5_rich_ground_truth.json").write_text(json.dumps(out, indent=2))
    print(f"matched clients with features = {n_match:,} / {n_uplift:,} uplift_train rows")
    print(f"tertile cutpoints: {cut}")
    print(f"segments={len(segments)} dropped={len(dropped)}")
    print(f"uplift range [{min(uplift_vector):+.4f}, {max(uplift_vector):+.4f}]")
    print(f"ground_truth_sha256={sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
