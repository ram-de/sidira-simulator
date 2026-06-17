"""Feasibility-only producer-pack build for Cookie Cats (v1.1 plumbing check).

Run with the sidira-personas venv:
    /Users/ram/Projects/sidira-personas/.venv/bin/python build_pack.py

NOT a causal/baseline persona model: the only per-user features available are
sum_gamerounds (POST-treatment mediator) + retention_1 / retention_7 (flags).
This exercises the pipeline plumbing only — no accuracy/scoring is computed.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from sidira_personas import run_pipeline

HERE = Path(__file__).resolve().parent
FIXTURE = Path(
    "/Users/ram/Projects/sidira-simulator/.claude/worktrees/"
    "wizard-redesign-evaluate/backend/tests/data/cookiecats_sample.csv"
)

cfg = {
    "company_id": "cookiecats",
    "source": {"type": "local", "path": str(FIXTURE), "user_id_column": "userid"},
    "feature_groups": {
        # The ONLY per-user numeric features Cookie Cats provides.
        "engagement": [
            {"name": "sum_gamerounds", "type": "count"},
        ],
        "retention": [
            {"name": "retention_1", "type": "flag"},
            {"name": "retention_7", "type": "flag"},
        ],
    },
    "encoder": {"method": "pca", "embedding_dim_per_group": 2},
    "cluster": {
        "method": "gmm",
        "k_range": [3, 6],
        "selection": "bic",
        "random_state": 42,
        "bootstrap_iters": 8,
        "stability_threshold": 0.5,
        "holdout_frac": 0.2,
    },
    "weights": {"schemes": ["headcount"], "orders_column": None, "revenue_column": None},
    "sampling": {"n_synthetic_rows": 16, "random_state": 42},
    "prompt_compiler": {
        "top_n_distinctive_features_per_group": 4,
        "threshold_sigma": 0.3,
    },
}

df = pd.read_csv(FIXTURE)
print(f"loaded {len(df)} rows; columns={list(df.columns)}")

log_lines: list[str] = []
res = run_pipeline(
    df, cfg, run_id="cookiecats-feasibility", no_llm=True, log=log_lines.append
)
print("\n".join(log_lines))

pack = asdict(res.pack)
out = HERE / "producer_pack.json"
out.write_text(json.dumps(pack, indent=2, default=str))
print(f"\nwrote {out}")
print(f"schema_version={pack['schema_version']} k_selected={pack['k_selected']} "
      f"n_personas={len(pack['personas'])}")
for p in pack["personas"]:
    print(
        f"  {p['id']}: centroid_full={len(p.get('centroid_full') or {})} "
        f"feature_scale={len(p.get('feature_scale') or {})} "
        f"sample_rows={len(p.get('sample_rows') or [])}"
    )
