#!/usr/bin/env python3
"""Generate + load the synthetic Streamly consumer feature store.

Streamly is the Netflix-style video-streaming product the sidira-crawler targets
as its first "customer". No real Streamly user-feature data exists, so this script
synthesizes a population as a **6-segment mixture keyed to the hand-authored
reference personas** in
  backend/local-artifacts/customers/streamly_sample/personas/v_1/persona_pack.json
  (Engaged Heavy, Engaged Light, Lapsing-At-Risk, New/Trial, Engaged Niche,
   Engaged Background)
so that when the real persona-Build pipeline clusters this table it should
*recover* segments resembling those archetypes — a genuine end-to-end validation,
not random noise. It is the acceptance fixture referenced by
ram-de/sidira-simulator#291 (Phase 3b of the persona-scaling epic #268).

Every feature is mapped to one of the 7 canonical feature groups
(`sidira_simulator` column_mapper): demographic_identity, behavioral_patterns,
motivations_jtbd, pain_points_friction, value_sensitivity, channel_tech_behavior,
loyalty_lifecycle. The latent segment label is deliberately NOT a column — the
pipeline must discover the structure, not read it off a leaked answer key.

Loads STREAMLY.SYNTHETIC.USERS_FEATURE_STORE via `write_pandas`. The CLI/this
script use **key-pair JWT** auth; note the product's `SnowflakeStore` adapter is
PASSWORD-auth only, so a wizard build against this table needs a Snowflake user
with a password set (see the reference notes / #291).

Usage
-----
  # generate + load (key-pair JWT; defaults match the `sidira` snow connection)
  python backend/scripts/gen_streamly_feature_store.py

  # regenerate identically (deterministic seed) without touching Snowflake
  python backend/scripts/gen_streamly_feature_store.py --dry-run

  # custom size / destination
  python backend/scripts/gen_streamly_feature_store.py --rows 5000 --table USERS_FEATURE_STORE_BIG

Connection is read from these env vars (CLI flags override), defaulting to the
values used to build the live fixture on 2026-06-15:
  SNOWFLAKE_ACCOUNT  (default HWATYVV-XD01132)
  SNOWFLAKE_USER     (default SIDIRA)
  SNOWFLAKE_PRIVATE_KEY_FILE (default ~/.snowflake/sidira_snowflake_key.p8)
  SNOWFLAKE_WAREHOUSE (default COMPUTE_WH)
  SNOWFLAKE_ROLE     (default ACCOUNTADMIN)

Requires numpy + pandas + snowflake-connector-python. NOTE these are *not* in
the base API image deps (the API image is deliberately ML-free, #268) — run this
from an env that has them: the persona-worker image, or the `~/.snowflake/venv`
used for Snowflake ops. `snowflake-connector-python` is a backend dep; numpy and
pandas ship with the worker / sidira-personas stack.
"""
import argparse
import os
import re
from datetime import date, timedelta

import numpy as np
import pandas as pd

DEFAULT_ROWS = 2500
DEFAULT_SEED = 20260615
# Fixed shuffle seed: with DEFAULT_ROWS + DEFAULT_SEED this reproduces the live
# STREAMLY.SYNTHETIC.USERS_FEATURE_STORE table (loaded 2026-06-15) byte-for-byte
# — same rows, same order, same user_id assignment.
SHUFFLE_SEED = 7
SNAPSHOT = date(2026, 6, 15)

# ----- segment mixture (weights sum to 1.0) -------------------------------
# Each segment: weight + per-feature (mean, std) for normals, p for bernoulli,
# and categorical distributions. Clipping applied after sampling.
SEGMENTS = {
    # Alex — serial binger, heavy mobile+TV, autoplay, churn-safe
    "engaged_heavy": dict(
        w=0.22, age=(28, 6), household=(2, 1),
        weekly_hours=(13.0, 3.0), sessions=(11, 3), session_min=(78, 18),
        serial=(0.88, 0.07), completion=(0.86, 0.08), rewatch=(0.22, 0.10),
        days_since=(1.2, 1.2), genre_conc=(0.55, 0.12), coview=(0.18, 0.10),
        aysw=(2.0, 1.2), stalled=(2, 2), rec_sat=(0.72, 0.12), cancel=(0, 1),
        price_sens=(0.28, 0.12), promo=(1, 1), upgrade=(0.40, 0.15),
        mobile=(0.50, 0.12), tv=(0.40, 0.12), subtitle=(0.30, 0.18),
        notif=(0.62, 0.15), email_open=(0.45, 0.15), churn=(0.12, 0.07),
        tenure=(620, 260), autoplay=0.92, ad=0.18,
        tier=[("premium", .55), ("member", .42), ("trial", .03)],
        genre=[("Drama Series", .35), ("Action", .25), ("Sci-Fi", .20),
               ("Comedy", .15), ("Documentary", .05)],
    ),
    # Rivka — household co-viewing, movies, decision fatigue
    "engaged_light": dict(
        w=0.20, age=(39, 8), household=(4, 1),
        weekly_hours=(4.5, 1.8), sessions=(4, 2), session_min=(95, 25),
        serial=(0.22, 0.10), completion=(0.78, 0.10), rewatch=(0.28, 0.12),
        days_since=(3.5, 2.5), genre_conc=(0.35, 0.12), coview=(0.72, 0.14),
        aysw=(1.0, 0.8), stalled=(1, 1), rec_sat=(0.55, 0.15), cancel=(0, 1),
        price_sens=(0.45, 0.15), promo=(2, 2), upgrade=(0.30, 0.15),
        mobile=(0.20, 0.10), tv=(0.70, 0.12), subtitle=(0.35, 0.18),
        notif=(0.45, 0.15), email_open=(0.50, 0.15), churn=(0.22, 0.10),
        tenure=(900, 320), autoplay=0.45, ad=0.30,
        tier=[("premium", .60), ("member", .38), ("trial", .02)],
        genre=[("Family", .30), ("Movies", .30), ("Comedy", .20),
               ("Drama Series", .12), ("Documentary", .08)],
    ),
    # Ken — price-sensitive lapser, cancel intent, low engagement
    "lapsing_at_risk": dict(
        w=0.16, age=(45, 10), household=(2, 1),
        weekly_hours=(1.2, 1.0), sessions=(1, 1), session_min=(42, 20),
        serial=(0.40, 0.20), completion=(0.50, 0.18), rewatch=(0.20, 0.12),
        days_since=(22, 8), genre_conc=(0.30, 0.15), coview=(0.30, 0.18),
        aysw=(0.4, 0.5), stalled=(3, 3), rec_sat=(0.35, 0.15), cancel=(4, 2),
        price_sens=(0.82, 0.12), promo=(1, 1), upgrade=(0.10, 0.08),
        mobile=(0.40, 0.18), tv=(0.40, 0.18), subtitle=(0.30, 0.18),
        notif=(0.20, 0.12), email_open=(0.18, 0.12), churn=(0.80, 0.12),
        tenure=(1100, 400), autoplay=0.40, ad=0.55,
        tier=[("member", .70), ("premium", .20), ("trial", .10)],
        genre=[("Movies", .30), ("News", .20), ("Comedy", .20),
               ("Drama Series", .18), ("Sports", .12)],
    ),
    # Tess — new trial, browse-heavy, conversion decision
    "new_trial": dict(
        w=0.14, age=(25, 5), household=(1, 1),
        weekly_hours=(5.5, 2.5), sessions=(7, 3), session_min=(38, 18),
        serial=(0.55, 0.18), completion=(0.42, 0.15), rewatch=(0.05, 0.05),
        days_since=(1.0, 1.0), genre_conc=(0.30, 0.15), coview=(0.20, 0.14),
        aysw=(0.6, 0.6), stalled=(2, 2), rec_sat=(0.50, 0.15), cancel=(1, 1),
        price_sens=(0.60, 0.18), promo=(0, 1), upgrade=(0.55, 0.18),
        mobile=(0.65, 0.15), tv=(0.20, 0.12), subtitle=(0.35, 0.20),
        notif=(0.55, 0.18), email_open=(0.48, 0.18), churn=(0.50, 0.18),
        tenure=(7, 4), autoplay=0.70, ad=0.40,
        tier=[("trial", .95), ("member", .05)],
        genre=[("Action", .25), ("Comedy", .22), ("Reality", .20),
               ("Drama Series", .18), ("Sci-Fi", .15)],
    ),
    # Noor — international/niche, subtitles, recommendation dissatisfaction
    "engaged_niche": dict(
        w=0.14, age=(34, 7), household=(2, 1),
        weekly_hours=(8.0, 3.0), sessions=(6, 2), session_min=(72, 20),
        serial=(0.70, 0.14), completion=(0.82, 0.10), rewatch=(0.25, 0.12),
        days_since=(2.5, 2.0), genre_conc=(0.82, 0.10), coview=(0.25, 0.15),
        aysw=(1.2, 0.9), stalled=(1, 1), rec_sat=(0.30, 0.14), cancel=(0, 1),
        price_sens=(0.35, 0.15), promo=(1, 1), upgrade=(0.35, 0.15),
        mobile=(0.45, 0.15), tv=(0.40, 0.15), subtitle=(0.95, 0.05),
        notif=(0.50, 0.15), email_open=(0.52, 0.15), churn=(0.20, 0.10),
        tenure=(700, 300), autoplay=0.55, ad=0.20,
        tier=[("premium", .65), ("member", .33), ("trial", .02)],
        genre=[("International", .45), ("World Drama", .25), ("Anime", .15),
               ("Documentary", .10), ("Drama Series", .05)],
    ),
    # Marco — comfort rewatcher, autoplay-on, background viewing
    "engaged_background": dict(
        w=0.14, age=(30, 6), household=(2, 1),
        weekly_hours=(9.5, 3.0), sessions=(9, 3), session_min=(64, 18),
        serial=(0.78, 0.12), completion=(0.62, 0.14), rewatch=(0.85, 0.10),
        days_since=(1.5, 1.3), genre_conc=(0.70, 0.12), coview=(0.22, 0.13),
        aysw=(6.5, 2.2), stalled=(1, 1), rec_sat=(0.58, 0.14), cancel=(0, 1),
        price_sens=(0.40, 0.15), promo=(1, 1), upgrade=(0.28, 0.14),
        mobile=(0.35, 0.15), tv=(0.50, 0.15), subtitle=(0.25, 0.16),
        notif=(0.40, 0.15), email_open=(0.42, 0.15), churn=(0.25, 0.12),
        tenure=(820, 320), autoplay=0.95, ad=0.28,
        tier=[("member", .55), ("premium", .43), ("trial", .02)],
        genre=[("Sitcom", .40), ("Comedy", .25), ("Reality", .18),
               ("Drama Series", .10), ("Sports", .07)],
    ),
}

COUNTRIES = [("US", .42), ("UK", .12), ("CA", .08), ("DE", .07), ("FR", .06),
             ("IN", .08), ("BR", .06), ("AU", .05), ("MX", .03), ("JP", .03)]


def _clip(a, lo, hi):
    return np.clip(a, lo, hi)


def _norm(rng, spec, n):
    m, s = spec
    return rng.normal(m, s, n)


def _cat(rng, choices, n):
    vals = [c[0] for c in choices]
    ps = np.array([c[1] for c in choices], dtype=float)
    ps = ps / ps.sum()
    return rng.choice(vals, size=n, p=ps)


def _gen_block(rng, name, n):
    p = SEGMENTS[name]
    df = pd.DataFrame()
    df["age"] = _clip(_norm(rng, p["age"], n), 16, 80).round().astype(int)
    df["household_size"] = _clip(_norm(rng, p["household"], n), 1, 6).round().astype(int)
    df["country"] = _cat(rng, COUNTRIES, n)
    df["subscription_tier"] = _cat(rng, p["tier"], n)

    df["weekly_viewing_hours"] = _clip(_norm(rng, p["weekly_hours"], n), 0, 50).round(2)
    df["weekly_sessions"] = _clip(_norm(rng, p["sessions"], n), 0, 35).round().astype(int)
    df["avg_session_minutes"] = _clip(_norm(rng, p["session_min"], n), 5, 200).round(1)
    df["serial_share"] = _clip(_norm(rng, p["serial"], n), 0, 1).round(3)
    df["completion_rate"] = _clip(_norm(rng, p["completion"], n), 0, 1).round(3)
    df["rewatch_share"] = _clip(_norm(rng, p["rewatch"], n), 0, 1).round(3)
    df["days_since_last_session"] = _clip(_norm(rng, p["days_since"], n), 0, 90).round().astype(int)

    df["top_genre"] = _cat(rng, p["genre"], n)
    df["genre_concentration"] = _clip(_norm(rng, p["genre_conc"], n), 0, 1).round(3)
    df["autoplay_enabled"] = (rng.random(n) < p["autoplay"]).astype(int)
    df["co_viewing_share"] = _clip(_norm(rng, p["coview"], n), 0, 1).round(3)

    df["aysw_dismissals_weekly"] = _clip(_norm(rng, p["aysw"], n), 0, 20).round(2)
    df["stalled_play_events_30d"] = _clip(_norm(rng, p["stalled"], n), 0, 40).round().astype(int)
    df["recommendation_satisfaction"] = _clip(_norm(rng, p["rec_sat"], n), 0, 1).round(3)
    df["cancel_page_views_30d"] = _clip(_norm(rng, p["cancel"], n), 0, 15).round().astype(int)

    df["price_sensitivity"] = _clip(_norm(rng, p["price_sens"], n), 0, 1).round(3)
    df["ad_supported_flag"] = (rng.random(n) < p["ad"]).astype(int)
    df["promo_redemptions_12mo"] = _clip(_norm(rng, p["promo"], n), 0, 12).round().astype(int)
    df["plan_upgrade_propensity"] = _clip(_norm(rng, p["upgrade"], n), 0, 1).round(3)

    mob = _clip(_norm(rng, p["mobile"], n), 0, 1)
    tv = _clip(_norm(rng, p["tv"], n), 0, 1)
    web = _clip(1 - mob - tv, 0, 1)
    tot = mob + tv + web
    mob, tv, web = mob / tot, tv / tot, web / tot
    df["mobile_share"] = mob.round(3)
    df["tv_share"] = tv.round(3)
    df["web_share"] = web.round(3)
    stack = np.vstack([mob, tv, web]).T
    df["device_primary"] = np.array(["mobile", "tv", "web"])[stack.argmax(axis=1)]
    df["subtitle_use_rate"] = _clip(_norm(rng, p["subtitle"], n), 0, 1).round(3)
    df["notification_response_rate"] = _clip(_norm(rng, p["notif"], n), 0, 1).round(3)

    df["email_open_rate"] = _clip(_norm(rng, p["email_open"], n), 0, 1).round(3)
    df["churn_risk"] = _clip(_norm(rng, p["churn"], n), 0, 1).round(3)
    tenure = _clip(_norm(rng, p["tenure"], n), 1, 2200).round().astype(int)
    df["signup_date"] = [(SNAPSHOT - timedelta(days=int(t))).isoformat() for t in tenure]
    trial_rem = _clip(rng.normal(5, 3, n), 1, 14).round().astype(int)
    df["trial_days_remaining"] = np.where(df["subscription_tier"].values == "trial",
                                          trial_rem, 0)
    return df


def generate(rows=DEFAULT_ROWS, seed=DEFAULT_SEED):
    """Build the synthetic Streamly population as a deterministic DataFrame."""
    rng = np.random.default_rng(seed)
    # largest-remainder allocation of `rows` across segment weights
    raw = {k: v["w"] * rows for k, v in SEGMENTS.items()}
    counts = {k: int(np.floor(v)) for k, v in raw.items()}
    rem = rows - sum(counts.values())
    for k in sorted(raw, key=lambda k: raw[k] - counts[k], reverse=True)[:rem]:
        counts[k] += 1

    blocks = [_gen_block(rng, name, n) for name, n in counts.items()]
    df = pd.concat(blocks, ignore_index=True)
    df = df.sample(frac=1.0, random_state=SHUFFLE_SEED).reset_index(drop=True)

    df.insert(0, "snapshot_date", SNAPSHOT.isoformat())
    df.insert(0, "user_id", [f"u_{i:06d}" for i in range(1, len(df) + 1)])
    return df, counts


def _ident(name):
    """Whitelist a SQL identifier (unquoted name) before interpolation."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"unsafe SQL identifier: {name!r}")
    return name


def _load(df, database, schema, table):
    from snowflake.connector import connect
    from snowflake.connector.pandas_tools import write_pandas

    database, schema, table = _ident(database), _ident(schema), _ident(table)
    pk_path = os.path.expanduser(
        os.environ.get("SNOWFLAKE_PRIVATE_KEY_FILE", "~/.snowflake/sidira_snowflake_key.p8")
    )
    # Connect WITHOUT database/schema session defaults: for a brand-new target,
    # the connector's USE-DATABASE session setup would fail before the CREATEs run.
    conn = connect(
        account=os.environ.get("SNOWFLAKE_ACCOUNT", "HWATYVV-XD01132"),
        user=os.environ.get("SNOWFLAKE_USER", "SIDIRA"),
        private_key_file=pk_path,
        authenticator="SNOWFLAKE_JWT",
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        role=os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
    )
    try:
        cur = conn.cursor()
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {database}.{schema}")
        cur.execute(f"USE SCHEMA {database}.{schema}")
        ok, nchunks, nrows, _ = write_pandas(
            conn, df, table, database=database, schema=schema,
            auto_create_table=True, overwrite=True, quote_identifiers=True,
        )
        print(f"write_pandas ok={ok} chunks={nchunks} rows={nrows} -> {database}.{schema}.{table}")
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rows", type=int, default=DEFAULT_ROWS)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--database", default="STREAMLY")
    ap.add_argument("--schema", default="SYNTHETIC")
    ap.add_argument("--table", default="USERS_FEATURE_STORE")
    ap.add_argument("--dry-run", action="store_true",
                    help="generate + summarize but do NOT connect to Snowflake")
    args = ap.parse_args()

    df, counts = generate(rows=args.rows, seed=args.seed)
    print(f"rows={len(df)} cols={len(df.columns)} seed={args.seed}")
    print("segment counts:", counts)
    print("columns:", list(df.columns))
    print(df.head(3).to_string())

    if args.dry_run:
        print("[dry-run] skipped Snowflake load.")
        return
    _load(df, args.database, args.schema, args.table)


if __name__ == "__main__":
    main()
