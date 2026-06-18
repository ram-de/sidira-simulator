"""X5 RetailHero RICH-covariate follow-up — Step 1: build PRE-TREATMENT
behavioral (RFM-style) per-client features from purchases.csv.gz.

Single streaming pass over the ~670MB purchases file. Only transactions with
transaction_datetime STRICTLY BEFORE the campaign cutoff are aggregated, so the
features are pre-treatment (no leakage from the SMS-response window). Raw rows
are discarded immediately; only per-client aggregates are retained.

Campaign cutoff: 2019-02-19. The X5 RetailHero uplift dataset purchase history
spans 2018-11-25 .. 2019-03-18; the documented SMS communication window begins
2019-02-19. We therefore treat everything < 2019-02-19 as pre-treatment. This
cutoff is an assumption (the file has no explicit treatment-date column) and is
recorded as a limitation. REFERENCE date for recency = the cutoff itself.

Per-client features written to client_features.json:
  recency_days        days from last pre-cutoff transaction to the cutoff
  frequency_txns      # distinct pre-cutoff transactions
  active_days         # distinct calendar days with a purchase
  monetary_total      sum of purchase_sum across pre-cutoff transactions
  monetary_avg        mean purchase_sum per transaction
  basket_avg_lines    mean # product lines per transaction (basket size proxy)
  category_breadth    # distinct product_id bought (variety)
  redeem_txn_share    share of transactions where any points were spent
  earn_total          total regular+express points received

    PYTHONPATH=backend <venv>/bin/python build_features.py
"""
from __future__ import annotations

import csv
import gzip
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
CUTOFF = datetime(2019, 2, 19)  # campaign / SMS window start (pre-treatment boundary)


def _f(x: str) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def main() -> int:
    # Per-client accumulators. Keep memory bounded: scalar aggregates +
    # a set of product_ids (breadth) + a set of transaction dates (active days)
    # + a dict of per-transaction info (sum, lines, redeemed) keyed by txn id.
    last_dt: dict[str, datetime] = {}
    txn_sum: dict[str, dict[str, float]] = defaultdict(dict)   # client -> txn -> spend
    txn_lines: dict[str, dict[str, int]] = defaultdict(dict)   # client -> txn -> #lines
    txn_redeem: dict[str, dict[str, bool]] = defaultdict(dict)  # client -> txn -> redeemed?
    products: dict[str, set] = defaultdict(set)
    active_days: dict[str, set] = defaultdict(set)
    earn_total: dict[str, float] = defaultdict(float)

    n_rows = n_pre = n_post = n_bad = 0
    with gzip.open(DATA / "purchases.csv.gz", "rt") as f:
        rd = csv.DictReader(f)
        for r in rd:
            n_rows += 1
            ds = r["transaction_datetime"]
            try:
                dt = datetime.strptime(ds, "%Y-%m-%d %H:%M:%S")
            except (TypeError, ValueError):
                n_bad += 1
                continue
            if dt >= CUTOFF:
                n_post += 1
                continue
            n_pre += 1
            cid = r["client_id"]
            tid = r["transaction_id"]
            txn_sum[cid][tid] = _f(r["purchase_sum"])  # same per line; overwrite ok
            txn_lines[cid][tid] = txn_lines[cid].get(tid, 0) + 1
            redeemed = (_f(r["regular_points_spent"]) > 0) or (_f(r["express_points_spent"]) > 0)
            txn_redeem[cid][tid] = txn_redeem[cid].get(tid, False) or redeemed
            earn_total[cid] += _f(r["regular_points_received"]) + _f(r["express_points_received"])
            products[cid].add(r["product_id"])
            active_days[cid].add(ds[:10])
            if cid not in last_dt or dt > last_dt[cid]:
                last_dt[cid] = dt
            if n_rows % 5_000_000 == 0:
                print(f"  ...{n_rows:,} rows ({n_pre:,} pre-cutoff)")

    features: dict[str, dict] = {}
    for cid in txn_sum:
        sums = txn_sum[cid]
        n_txn = len(sums)
        total = sum(sums.values())
        lines = txn_lines[cid]
        n_redeem = sum(1 for v in txn_redeem[cid].values() if v)
        recency = (CUTOFF - last_dt[cid]).days
        features[cid] = {
            "recency_days": recency,
            "frequency_txns": n_txn,
            "active_days": len(active_days[cid]),
            "monetary_total": round(total, 2),
            "monetary_avg": round(total / n_txn, 2) if n_txn else 0.0,
            "basket_avg_lines": round(sum(lines.values()) / n_txn, 3) if n_txn else 0.0,
            "category_breadth": len(products[cid]),
            "redeem_txn_share": round(n_redeem / n_txn, 4) if n_txn else 0.0,
            "earn_total": round(earn_total[cid], 1),
        }

    out_path = DATA / "client_features.json"
    out_path.write_text(json.dumps(features))
    meta = {
        "n_purchase_rows": n_rows,
        "n_rows_pre_cutoff": n_pre,
        "n_rows_post_cutoff_dropped": n_post,
        "n_rows_bad_date": n_bad,
        "cutoff": CUTOFF.isoformat(),
        "n_clients_with_pre_features": len(features),
    }
    (DATA / "client_features_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"\nrows={n_rows:,} pre={n_pre:,} post={n_post:,} bad_date={n_bad}")
    print(f"clients with pre-cutoff features = {len(features):,}")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
