"""STEP A1 — build a v1.1 streamly producer pack from the Snowflake feature store.

Runs in the sidira-personas venv. Reads STREAMLY.SYNTHETIC.USERS_FEATURE_STORE via
key-pair JWT (the `sidira` connection; read_snowflake's password path is bypassed
because the table was loaded with JWT auth), then drives run_pipeline with
require_llm so personas get real LLM descriptions and the v1.1 quad
(centroid_full / feature_scale / sample_rows / posterior_mean).

Writes the raw PRODUCER pack JSON. A separate sim-venv step translates it into the
consumer PersonaPack the simulator's PersonaPackLoader reads.

FICTIONAL DATA — readiness exercise, not accuracy validation.
"""
from __future__ import annotations
import datetime as dt
import os
from pathlib import Path

import yaml

CFG = "/Users/ram/Projects/sidira-personas/config/streamly.yaml"
OUT = "/Users/ram/Projects/sidira-simulator/.claude/worktrees/benchmark-gate-validation/sessions/agent-behavior-spec/streamly-metric-validation/streamly_producer_pack_v11.json"


def read_via_jwt(database: str, schema: str, table: str):
    import pandas as pd  # noqa: F401
    from snowflake.connector import connect

    pk = os.path.expanduser(
        os.environ.get("SNOWFLAKE_PRIVATE_KEY_FILE", "~/.snowflake/sidira_snowflake_key.p8")
    )
    conn = connect(
        account=os.environ.get("SNOWFLAKE_ACCOUNT", "HWATYVV-XD01132"),
        user=os.environ.get("SNOWFLAKE_USER", "SIDIRA"),
        private_key_file=pk,
        authenticator="SNOWFLAKE_JWT",
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        role=os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        database=database,
        schema=schema,
        login_timeout=30,
    )
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {database}.{schema}.{table}")
        df = cur.fetch_pandas_all()
        df.columns = [c.lower() for c in df.columns]
        return df
    finally:
        conn.close()


def main():
    from sidira_personas.pipeline import run_pipeline

    cfg = yaml.safe_load(Path(CFG).read_text())
    src = cfg["source"]
    print(f"[read] {src['database']}.{src['schema']}.{src['table']} via JWT …")
    df = read_via_jwt(src["database"], src["schema"], src["table"])
    print(f"[read] {len(df):,} rows, {df.shape[1]} cols")

    run_id = f"{cfg.get('run_id_prefix','streamly')}-{dt.datetime.utcnow().strftime('%Y%m%dT%H%M%S')}"
    # require_llm=True → real descriptions, fail-fast if no provider; provider
    # forced to anthropic (ANTHROPIC_API_KEY present, claude-sonnet-4-6 default).
    result = run_pipeline(
        df, cfg, run_id=run_id, require_llm=True, provider="anthropic", log=print
    )
    result.pack.to_json(OUT)
    print(f"[write] producer pack -> {OUT}")

    # quad presence check on the producer pack
    import json
    pack = json.loads(Path(OUT).read_text())
    print(f"[pack] schema_version={pack.get('schema_version')} k={pack.get('k_selected')} "
          f"n_personas={len(pack.get('personas', []))}")
    for p in pack.get("personas", []):
        quad = all(
            p.get(k) not in (None, {}, [])
            for k in ("centroid_full", "feature_scale", "sample_rows")
        ) and ("posterior_mean" in p)
        print(f"  {p['id']:>5} | {p['name']!r:40} quad={'OK' if quad else 'MISSING'} "
              f"size={p.get('size')} stability={p.get('stability')}")


if __name__ == "__main__":
    main()
