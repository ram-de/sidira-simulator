"""X5 RetailHero generalization test — Step 2: build REAL ground-truth uplift ranking.

Mirrors the Hillstrom heterogeneity method (forecaster_powered.py build_cases):
pre-treatment-covariate segments, per-segment REAL uplift = mean(target|T=1) -
mean(target|T=0), ordered into a ground-truth "who responds more" vector.

Segments = gender(F/M) x age-bucket(under35/35to54/55plus) x tenure(by first_issue
year: 2017=long, 2018=mid, 2019=new). Gender 'U' (unknown) is DROPPED because it
yields no interpretable audience description for the blinded forecaster. Implausible
ages (<14 or >90) dropped. Floor: n>=200 PER ARM, no silent truncation.

    PYTHONPATH=backend <venv>/bin/python build_ground_truth.py
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
FLOOR = 200  # n per arm

AGE_LABEL = {"under35": "under 35", "35to54": "35 to 54", "55plus": "55 or older"}
TEN_LABEL = {
    "longtenure": "joined the loyalty program in 2017 (long-standing members)",
    "midtenure": "joined the loyalty program in 2018",
    "newtenure": "joined the loyalty program in 2019 (recently joined)",
}
GENDER_LABEL = {"F": "women", "M": "men"}


def age_bucket(a: int) -> str:
    if a < 35:
        return "under35"
    if a < 55:
        return "35to54"
    return "55plus"


def tenure_bucket(first_issue_date: str) -> str | None:
    y = first_issue_date[:4]
    return {"2017": "longtenure", "2018": "midtenure", "2019": "newtenure"}.get(y)


def main() -> int:
    # Load treatment + target.
    tr: dict[str, tuple[int, int]] = {}
    with gzip.open(DATA / "uplift_train.csv.gz", "rt") as f:
        for r in csv.DictReader(f):
            tr[r["client_id"]] = (int(r["treatment_flg"]), int(r["target"]))

    cells: dict[tuple, dict[int, list[int]]] = defaultdict(
        lambda: {0: [0, 0], 1: [0, 0]}  # arm -> [target_sum, n]
    )
    n_total = n_no_gender = n_bad_age = n_bad_tenure = 0
    with gzip.open(DATA / "clients.csv.gz", "rt") as f:
        for r in csv.DictReader(f):
            cid = r["client_id"]
            if cid not in tr:
                continue
            n_total += 1
            g = r["gender"]
            if g not in ("F", "M"):
                n_no_gender += 1
                continue
            try:
                a = int(float(r["age"]))
            except (TypeError, ValueError):
                n_bad_age += 1
                continue
            if a < 14 or a > 90:
                n_bad_age += 1
                continue
            tb = tenure_bucket(r["first_issue_date"])
            if tb is None:
                n_bad_tenure += 1
                continue
            key = (g, age_bucket(a), tb)
            t, y = tr[cid]
            cells[key][t][0] += y
            cells[key][t][1] += 1

    segments = []
    dropped = []
    for key in sorted(cells):
        c = cells[key]
        nT, nC = c[1][1], c[0][1]
        g, ab, tb = key
        seg_id = f"{g}/{ab}/{tb}"
        if nT < FLOOR or nC < FLOOR:
            dropped.append({"segment": seg_id, "n_treatment": nT, "n_control": nC,
                            "reason": f"below floor n>={FLOOR}/arm"})
            continue
        rate_t = c[1][0] / nT
        rate_c = c[0][0] / nC
        segments.append({
            "segment": seg_id,
            "gender": g, "age_bucket": ab, "tenure_bucket": tb,
            "n_treatment": nT, "n_control": nC,
            "target_rate_treatment": rate_t,
            "target_rate_control": rate_c,
            "uplift": rate_t - rate_c,
        })

    # Canonical ground-truth uplift vector: ordered by segment id (stable, sorted).
    seg_ids = [s["segment"] for s in segments]
    uplift_vector = [s["uplift"] for s in segments]
    canonical = json.dumps(
        [{"segment": s, "uplift": round(u, 10)} for s, u in zip(seg_ids, uplift_vector)],
        sort_keys=False,
    )
    sha = hashlib.sha256(canonical.encode()).hexdigest()

    out = {
        "dataset": "X5 RetailHero uplift (scikit-uplift S3 mirror)",
        "source_files": ["clients.csv.gz", "uplift_train.csv.gz"],
        "treatment": "retailer SMS promotion (treatment_flg=1) vs no-SMS holdout (=0)",
        "target": "binary purchase/redeem outcome (target)",
        "covariates_used": ["gender (F/M)", "age bucket", "tenure bucket (first_issue year)"],
        "floor_per_arm": FLOOR,
        "n_matched_clients": n_total,
        "n_dropped_unknown_gender": n_no_gender,
        "n_dropped_bad_age": n_bad_age,
        "n_dropped_bad_tenure": n_bad_tenure,
        "n_segments": len(segments),
        "n_segments_dropped": len(dropped),
        "uplift_min": min(uplift_vector),
        "uplift_max": max(uplift_vector),
        "canonical_uplift_vector_order": "by segment id, lexicographic sort",
        "ground_truth_sha256": sha,
        "segments": segments,
        "dropped_segments": dropped,
    }
    (HERE / "x5_ground_truth.json").write_text(json.dumps(out, indent=2))
    print(f"segments={len(segments)} dropped={len(dropped)}")
    print(f"uplift range [{min(uplift_vector):+.4f}, {max(uplift_vector):+.4f}]")
    print(f"ground_truth_sha256={sha}")
    print(f"dropped unknown-gender clients={n_no_gender} bad-age={n_bad_age}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
