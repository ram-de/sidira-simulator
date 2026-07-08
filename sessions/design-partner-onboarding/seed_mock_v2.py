"""White-glove seeding of rich Netflix-like mock data into STREAMLY.SYNTHETIC.

All data deterministic (hash-seeded, no RNG state). Designed ground truth:

  lever (all in FEATURE_ROLLOUTS_V2)      assignment            TRUE effects
  ------------------------------------    -------------------   --------------------------------
  new_recs_algorithm          (t3)        randomized 50%        watch_minutes +45, completion +0.05
  mobile_preview_clips        (t4)        randomized 50%        watch_minutes +40, sessions +1.2
  profile_onboarding_quiz     (t5)        randomized 30%        sessions +1.5
  password_sharing_crackdown  (t6)        randomized 40%        watch_minutes -50, churned_90d ~ +9pp
  kids_profile_nudge          (t7)        randomized 25%        kids_hours +1.5
  ui_dark_mode_default        (t8)        randomized 50%        ZERO everywhere (true null)
  premium_upsell_banner       (t9)        CONFOUNDED (high-u)   ZERO (pure selection on taste)
  dormant_winback_email       (t10)       CONFOUNDED (low-u)    sessions +1.0 (real, sign-masked)

Latent taste u = 0.6*z(weekly_viewing_hours) + 0.8*hash-noise — shared by every
outcome and by the confounded assignments; pre-period metrics share u, levers
cannot cause them (the vouched-NC argument).
"""
import asyncio
import json
import os

import asyncpg

from sidira_simulator.adapters import credentials
from sidira_simulator.adapters.feature_stores.snowflake import SnowflakeCreds, SnowflakeStore

CID = "org_3F9pXzqFStz5NyPkazXW1o47NzE"
CONN_ID = "fs-e1c58d6a5d28"
SCHEMA = "STREAMLY.SYNTHETIC"


def uni(tag: str) -> str:
    return f"(MOD(ABS(HASH(\"user_id\" || '{tag}')), 1000000) / 1000000.0)"


def nrm(tag: str) -> str:
    return f"(({uni(tag + 'a')} + {uni(tag + 'b')} + {uni(tag + 'c')} - 1.5) * 2.0)"


BASE = f"""
base AS (
  SELECT "user_id",
         ("weekly_viewing_hours" - AVG("weekly_viewing_hours") OVER ())
           / NULLIF(STDDEV("weekly_viewing_hours") OVER (), 0) AS "z_wvh"
  FROM {SCHEMA}.USERS_FEATURE_STORE
),
lat AS (
  SELECT "user_id", (0.6 * "z_wvh" + 0.8 * {nrm('-lat2')}) AS "u" FROM base
),
lev AS (
  SELECT "user_id", "u",
         MOD(ABS(HASH("user_id" || '-t3')), 2)                            AS "new_recs_algorithm",
         MOD(ABS(HASH("user_id" || '-t4')), 2)                            AS "mobile_preview_clips",
         IFF({uni('-t5')} < 0.30, 1, 0)                                   AS "profile_onboarding_quiz",
         IFF({uni('-t6')} < 0.40, 1, 0)                                   AS "password_sharing_crackdown",
         IFF({uni('-t7')} < 0.25, 1, 0)                                   AS "kids_profile_nudge",
         MOD(ABS(HASH("user_id" || '-t8')), 2)                            AS "ui_dark_mode_default",
         IFF("u" + 0.4 * {nrm('-t9')} > 0.30, 1, 0)                       AS "premium_upsell_banner",
         IFF(-"u" + 0.4 * {nrm('-t10')} > 0.60, 1, 0)                     AS "dormant_winback_email"
  FROM lat
)"""

ROLLOUTS_V2 = f"""
CREATE OR REPLACE TABLE {SCHEMA}.FEATURE_ROLLOUTS_V2 AS
WITH {BASE}
SELECT "user_id",
       "new_recs_algorithm", "mobile_preview_clips", "profile_onboarding_quiz",
       "password_sharing_crackdown", "kids_profile_nudge", "ui_dark_mode_default",
       "premium_upsell_banner", "dormant_winback_email"
FROM lev
"""

ENGAGEMENT = f"""
CREATE OR REPLACE TABLE {SCHEMA}.ENGAGEMENT_OUTCOMES AS
WITH {BASE}
SELECT "user_id",
       GREATEST(0, ROUND(12.0 + 6.0 * "u" + 1.5 * {nrm('-pre_s')}, 1))    AS "pre_sessions_30d",
       LEAST(0.98, GREATEST(0.02,
             ROUND(0.55 + 0.15 * "u" + 0.05 * {nrm('-pre_c')}, 4)))       AS "pre_completion_rate_30d",
       GREATEST(0, ROUND(
             610.0 + 300.0 * "u"
             + 45.0 * "new_recs_algorithm"
             + 40.0 * "mobile_preview_clips"
             - 50.0 * "password_sharing_crackdown"
             + 80.0 * {nrm('-y_min')}, 1))                                AS "watch_minutes_next_30d",
       GREATEST(0, ROUND(
             12.5 + 6.0 * "u"
             + 1.2 * "mobile_preview_clips"
             + 1.5 * "profile_onboarding_quiz"
             + 1.0 * "dormant_winback_email"
             + 1.5 * {nrm('-y_ses')}, 1))                                 AS "sessions_next_30d",
       LEAST(0.98, GREATEST(0.02, ROUND(
             0.56 + 0.15 * "u"
             + 0.05 * "new_recs_algorithm"
             + 0.05 * {nrm('-y_cmp')}, 4)))                               AS "completion_rate_next_30d",
       GREATEST(0, ROUND(
             3.0 + 0.5 * "u"
             + 1.5 * "kids_profile_nudge"
             + 2.0 * {nrm('-y_kid')}, 1))                                 AS "kids_hours_next_30d"
FROM lev
"""

SUBSCRIPTION = f"""
CREATE OR REPLACE TABLE {SCHEMA}.SUBSCRIPTION_SNAPSHOT AS
WITH {BASE}
SELECT "user_id",
       CASE MOD(ABS(HASH("user_id" || '-plan')), 10)
            WHEN 0 THEN 'basic' WHEN 1 THEN 'basic' WHEN 2 THEN 'basic'
            WHEN 3 THEN 'standard' WHEN 4 THEN 'standard' WHEN 5 THEN 'standard' WHEN 6 THEN 'standard'
            ELSE 'premium' END                                            AS "plan_tier",
       CASE MOD(ABS(HASH("user_id" || '-plan')), 10)
            WHEN 0 THEN 8.99 WHEN 1 THEN 8.99 WHEN 2 THEN 8.99
            WHEN 3 THEN 13.99 WHEN 4 THEN 13.99 WHEN 5 THEN 13.99 WHEN 6 THEN 13.99
            ELSE 19.99 END                                                AS "monthly_price",
       IFF({uni('-payf')} < 0.06, 1, 0) + IFF({uni('-payf2')} < 0.02, 1, 0) AS "payment_failures_90d",
       IFF(-0.8 * "u" + 0.6 * {nrm('-churn')} + 0.5 * "password_sharing_crackdown" > 1.25, 1, 0)
                                                                          AS "churned_90d",
       IFF(0.5 * "u" + {nrm('-upg')} > 1.60, 1, 0)                        AS "upgraded_plan_90d"
FROM lev
"""

EXPERIMENTS_DDL = f"""
CREATE OR REPLACE TABLE {SCHEMA}.EXPERIMENT_HISTORY (
  "experiment_id"    VARCHAR,
  "experiment_name"  VARCHAR,
  "feature_flag"     VARCHAR,
  "hypothesis"       VARCHAR,
  "primary_metric"   VARCHAR,
  "start_date"       DATE,
  "end_date"         DATE,
  "treatment_users"  INTEGER,
  "control_users"    INTEGER,
  "control_mean"     FLOAT,
  "treatment_mean"   FLOAT,
  "lift_abs"         FLOAT,
  "p_value"          FLOAT,
  "decision"         VARCHAR,
  "notes"            VARCHAR
)
"""

# Past A/B tests: numbers consistent with the designed ground truth where flags overlap.
EXPERIMENTS = [
    ("EXP-2025-031", "Skip intro default-on", "skip_intro_default_on",
     "Defaulting skip-intro on increases watch time", "watch_minutes_30d",
     "2025-11-03", "2025-12-01", 24880, 24730, 601.2, 659.4, 58.2, 0.0004,
     "shipped", "Rolled to 100% Jan 2026; strongest engagement win of H2."),
    ("EXP-2026-004", "New recommendations algorithm v9", "new_recs_algorithm",
     "Two-tower recs lift completion and minutes", "watch_minutes_30d",
     "2026-02-10", "2026-03-10", 49510, 49770, 604.8, 648.9, 44.1, 0.0021,
     "shipped", "Completion rate +4.8pp in secondary read."),
    ("EXP-2026-011", "Mobile preview clips", "mobile_preview_clips",
     "Autoplaying 15s previews on mobile lift session starts", "sessions_30d",
     "2026-03-02", "2026-03-30", 30110, 30240, 12.4, 13.5, 1.1, 0.0100,
     "shipped", "Minutes +38 secondary; no cannibalization of TV starts."),
    ("EXP-2026-014", "Profile onboarding quiz", "profile_onboarding_quiz",
     "Taste quiz at profile creation lifts early engagement", "sessions_30d",
     "2026-03-16", "2026-04-13", 15080, 35120, 12.3, 13.9, 1.6, 0.0300,
     "shipped", "New-profile cohort only; existing profiles untested."),
    ("EXP-2026-017", "Password sharing crackdown", "password_sharing_crackdown",
     "Paid-sharing enforcement is minutes-negative but revenue-positive", "watch_minutes_30d",
     "2026-04-01", "2026-04-29", 40050, 60110, 612.0, 560.3, -51.7, 0.0100,
     "shipped", "Shipped for ARPU despite engagement cost; churn +3.8pp in treated."),
    ("EXP-2026-019", "Kids profile nudge", "kids_profile_nudge",
     "Prompting kids-profile setup lifts kids watch hours", "kids_hours_30d",
     "2026-04-13", "2026-05-11", 12490, 37600, 3.1, 4.5, 1.4, 0.0200,
     "shipped", "Household-level consent flow added post-launch."),
    ("EXP-2026-021", "Dark mode default", "ui_dark_mode_default",
     "Dark-first UI increases evening viewing", "watch_minutes_30d",
     "2026-04-27", "2026-05-25", 25010, 25140, 608.8, 610.0, 1.2, 0.7100,
     "inconclusive", "No detectable effect; shipped as a preference, not a default."),
    ("EXP-2026-023", "Dormant winback email", "dormant_winback_email",
     "Winback email lifts sessions among 30d-dormant users", "sessions_30d",
     "2026-05-04", "2026-06-01", 8040, 8110, 4.1, 5.0, 0.9, 0.0400,
     "shipped", "RCT on dormant segment; later ROLLOUT targeted low-engagement (selection!)."),
    ("EXP-2025-044", "Thumbnail art personalization", "thumb_art_personalization",
     "Personalized key art lifts title starts", "title_starts_7d",
     "2025-12-08", "2026-01-05", 45210, 45360, 8.9, 9.4, 0.5, 0.0080,
     "shipped", "Flag retired after 100% rollout; not in current warehouse."),
    ("EXP-2026-002", "Autoplay preview volume default", "autoplay_preview_muted",
     "Muted autoplay previews reduce browse abandonment", "browse_abandon_rate",
     "2026-01-19", "2026-02-16", 22020, 22150, 0.31, 0.29, -0.02, 0.0600,
     "rolled_back", "Directionally right but accessibility complaints; reverted."),
    ("EXP-2026-007", "Top-10 row placement", "top10_row_position",
     "Moving Top-10 above the fold lifts starts", "title_starts_7d",
     "2026-02-17", "2026-03-17", 18110, 18090, 9.0, 9.1, 0.1, 0.5400,
     "inconclusive", "Underpowered; queued for re-run at 4x sample."),
    ("EXP-2026-025", "Premium upsell banner", "premium_upsell_banner",
     "Upsell banner lifts premium upgrades", "upgrade_rate_90d",
     "2026-05-18", "2026-05-25", 5010, 5040, 0.081, 0.083, 0.002, 0.6200,
     "rolled_back", "RCT was flat; PMM later re-launched TARGETED at high-engagement users (never re-tested)."),
]

CATALOG_DDL = f"""
CREATE OR REPLACE TABLE {SCHEMA}.CONTENT_CATALOG (
  "title_id" VARCHAR, "title" VARCHAR, "content_type" VARCHAR, "genre" VARCHAR,
  "seasons" INTEGER, "maturity_rating" VARCHAR, "launch_date" DATE, "is_original" BOOLEAN
)
"""

CATALOG = [
    ("TT-1001", "Crown of Ashes", "series", "drama", 4, "TV-MA", "2023-02-10", True),
    ("TT-1002", "Byte Club", "series", "comedy", 2, "TV-14", "2024-06-21", True),
    ("TT-1003", "The Last Habitat", "documentary", "nature", 1, "TV-G", "2025-04-22", True),
    ("TT-1004", "Midnight Ledger", "film", "thriller", 0, "R", "2025-10-31", True),
    ("TT-1005", "Paws & Effect", "series", "kids", 3, "TV-Y", "2022-08-15", True),
    ("TT-1006", "Solaris Divide", "series", "scifi", 3, "TV-14", "2023-11-03", True),
    ("TT-1007", "Kitchen Empires", "series", "reality", 5, "TV-PG", "2021-09-12", False),
    ("TT-1008", "The Quiet Cartographer", "film", "drama", 0, "PG-13", "2026-01-16", True),
    ("TT-1009", "Rift Valley", "series", "action", 1, "TV-MA", "2026-03-07", True),
    ("TT-1010", "Numbers Never Lie", "documentary", "true-crime", 2, "TV-14", "2024-01-26", False),
    ("TT-1011", "Starlight Academy", "series", "kids", 4, "TV-Y7", "2023-05-19", True),
    ("TT-1012", "Grand Slam Diaries", "documentary", "sports", 1, "TV-PG", "2025-07-08", True),
    ("TT-1013", "Vermilion", "film", "romance", 0, "PG-13", "2026-02-13", True),
    ("TT-1014", "Backyard Universe", "series", "family", 2, "TV-G", "2024-11-22", True),
    ("TT-1015", "The Debt Machine", "series", "thriller", 2, "TV-MA", "2025-09-04", True),
]

VIEW = f"""
CREATE OR REPLACE VIEW {SCHEMA}.PERSONA_SOURCE_V2 AS
SELECT f.*,
       r1."offline_downloads_enabled", r1."skip_intro_default_on",
       r1."pre_minutes_30d", r1."minutes_watched_next_30d",
       r2."new_recs_algorithm", r2."mobile_preview_clips", r2."profile_onboarding_quiz",
       r2."password_sharing_crackdown", r2."kids_profile_nudge", r2."ui_dark_mode_default",
       r2."premium_upsell_banner", r2."dormant_winback_email",
       e."pre_sessions_30d", e."pre_completion_rate_30d",
       e."watch_minutes_next_30d", e."sessions_next_30d",
       e."completion_rate_next_30d", e."kids_hours_next_30d",
       s."payment_failures_90d", s."churned_90d", s."upgraded_plan_90d"
FROM {SCHEMA}.USERS_FEATURE_STORE f
JOIN {SCHEMA}.FEATURE_ROLLOUTS r1 ON f."user_id" = r1."user_id"
JOIN {SCHEMA}.FEATURE_ROLLOUTS_V2 r2 ON f."user_id" = r2."user_id"
JOIN {SCHEMA}.ENGAGEMENT_OUTCOMES e ON f."user_id" = e."user_id"
JOIN {SCHEMA}.SUBSCRIPTION_SNAPSHOT s ON f."user_id" = s."user_id"
"""


async def get_store() -> SnowflakeStore:
    url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    db = await asyncpg.connect(url)
    row = dict(await db.fetchrow(
        "SELECT * FROM feature_store_connections WHERE id=$1 AND customer_id=$2", CONN_ID, CID))
    await db.close()
    if isinstance(row["password_enc"], str):
        row["password_enc"] = json.loads(row["password_enc"])
    aad = f"{CID}:{row['id']}".encode()
    secrets = credentials.decrypt(credentials.deserialize_blob(row["password_enc"]),
                                  customer_id=CID, aad=aad)
    return SnowflakeStore(SnowflakeCreds(
        account=row["account"], user=row["user"], password=secrets["password"],
        warehouse=row["warehouse"], role=row["role"],
        database=row["database"], schema=row["schema"]))


def execute(conn, sql: str, label: str) -> None:
    cur = conn.cursor()
    try:
        cur.execute(sql)
        print(f"OK  {label}")
    finally:
        cur.close()


async def main() -> None:
    store = await get_store()
    conn = store._connect()  # white-glove seeding uses the saved connection's raw cursor
    try:
        execute(conn, ROLLOUTS_V2, "FEATURE_ROLLOUTS_V2")
        execute(conn, ENGAGEMENT, "ENGAGEMENT_OUTCOMES")
        execute(conn, SUBSCRIPTION, "SUBSCRIPTION_SNAPSHOT")
        execute(conn, EXPERIMENTS_DDL, "EXPERIMENT_HISTORY (ddl)")
        cur = conn.cursor()
        cur.executemany(
            f"""INSERT INTO {SCHEMA}.EXPERIMENT_HISTORY VALUES
                (%s,%s,%s,%s,%s,TO_DATE(%s),TO_DATE(%s),%s,%s,%s,%s,%s,%s,%s,%s)""",
            EXPERIMENTS)
        cur.close()
        print(f"OK  EXPERIMENT_HISTORY ({len(EXPERIMENTS)} rows)")
        execute(conn, CATALOG_DDL, "CONTENT_CATALOG (ddl)")
        cur = conn.cursor()
        cur.executemany(
            f"""INSERT INTO {SCHEMA}.CONTENT_CATALOG VALUES
                (%s,%s,%s,%s,%s,%s,TO_DATE(%s),%s)""",
            CATALOG)
        cur.close()
        print(f"OK  CONTENT_CATALOG ({len(CATALOG)} rows)")
        execute(conn, VIEW, "PERSONA_SOURCE_V2 view")
    finally:
        conn.close()

    # Verification through the product read path.
    rows = store.run_query(f'''SELECT COUNT(*) AS "n", COUNT(DISTINCT "user_id") AS "d" FROM {SCHEMA}.PERSONA_SOURCE_V2''')
    print("VIEW:", rows)
    rows = store.run_query(f'''SELECT AVG("new_recs_algorithm") AS "t3", AVG("mobile_preview_clips") AS "t4",
        AVG("profile_onboarding_quiz") AS "t5", AVG("password_sharing_crackdown") AS "t6",
        AVG("kids_profile_nudge") AS "t7", AVG("ui_dark_mode_default") AS "t8",
        AVG("premium_upsell_banner") AS "t9", AVG("dormant_winback_email") AS "t10",
        AVG("churned_90d") AS "churn", AVG("upgraded_plan_90d") AS "upg" FROM {SCHEMA}.PERSONA_SOURCE_V2''')
    print("ADOPTION:", rows)
    # Designed-effect sanity: naive diffs on randomized levers ~= truth; confounded spurious.
    for t, y, expect in (
        ("new_recs_algorithm", "watch_minutes_next_30d", "+45"),
        ("mobile_preview_clips", "sessions_next_30d", "+1.2"),
        ("password_sharing_crackdown", "watch_minutes_next_30d", "-50"),
        ("ui_dark_mode_default", "watch_minutes_next_30d", "0"),
        ("premium_upsell_banner", "watch_minutes_next_30d", "SPURIOUS+"),
        ("dormant_winback_email", "sessions_next_30d", "true +1.0 masked by -u selection"),
    ):
        r = store.run_query(f'''SELECT AVG(IFF("{t}"=1,"{y}",NULL)) - AVG(IFF("{t}"=0,"{y}",NULL)) AS "naive" FROM {SCHEMA}.PERSONA_SOURCE_V2''')
        print(f"NAIVE {t} -> {y}: {r[0]['naive']:+.2f}  (design: {expect})")

asyncio.run(main())
