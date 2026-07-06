# Separate-table onboarding — treatment data outside the persona feature store

**Ticket:** #568 (M1 of epic #572). White-glove / API-driven for now.

When a design partner's treatment/exposure signal lives in a *different* table
from the persona feature store (a reminder-email log, an experiment-exposure
table, a billing/outcome table), we still onboard it through the existing
feature-store build path — no connector change. Two moving parts:

1. a Snowflake **VIEW** that joins the tables into one row-per-user source, and
2. an **`estimability`** block on the build request that names the treatment and
   outcome columns so the producer pipeline emits the estimability manifest.

## 1. Author a joined VIEW

Create a Snowflake view that joins the persona-feature table to the separate
treatment/exposure table (and any outcome column) on the persona `user_id` key,
yielding **one row per user** — the same shape the build already expects:

```sql
CREATE OR REPLACE VIEW ANALYTICS.SIDIRA.PERSONA_SOURCE_V1 AS
SELECT
    f.user_id,
    f.total_orders_lifetime,
    f.convenience_ratio,
    f.region,
    f.signup_date,
    -- treatment / exposure, joined from a separate table:
    COALESCE(t.reminder_email_sent, 0)          AS reminder_email_sent,
    -- outcome, joined from a separate table:
    COALESCE(o.reactivated_within_30d, 0)       AS reactivated_30d
FROM ANALYTICS.SIDIRA.USER_FEATURE_STORE f
LEFT JOIN ANALYTICS.SIDIRA.EMAIL_LOG      t USING (user_id)
LEFT JOIN ANALYTICS.SIDIRA.OUTCOMES       o USING (user_id);
```

Onboard the view either way:

- **SQL mode:** set the build `source_query` to `SELECT * FROM
  ANALYTICS.SIDIRA.PERSONA_SOURCE_V1`.
- **Table mode:** point the table-mode FQN at the view.

**Views are query-transparent** — `SnowflakeStore.run_query(config.source_query)`
runs a free-form `SELECT`, so a view reads exactly like a base table. No
connector, loader, or schema change is required.

## 2. Declare estimability on the build request

Add an `estimability` block to the build payload naming the treatment column(s)
(`treatments`) and outcome column(s) (`outcomes`) that now live in the view.
The *presence* of the block is the intent to enable — it is threaded verbatim
into the producer pipeline's `cfg["estimability"]` contract, which builds the
manifest when `enabled is True`. Optional: `neg_control_map` (explicit negative
controls per treatment) and `nc_diagnostics: true` (the reviewable per-lever
diagnostics that back the lever-card surface, #565).

```json
{
  "connection_id": "conn_abc123",
  "source_query": "SELECT * FROM ANALYTICS.SIDIRA.PERSONA_SOURCE_V1",
  "column_mapping": {
    "total_orders_lifetime": "behavioral_patterns",
    "convenience_ratio": "value_sensitivity",
    "region": "demographic_identity",
    "signup_date": "loyalty_lifecycle",
    "user_id": null,
    "reminder_email_sent": null,
    "reactivated_30d": null
  },
  "k": "auto",
  "stability_threshold": 0.65,
  "weight_schemes": ["head_count"],
  "estimability": {
    "enabled": true,
    "treatments": ["reminder_email_sent"],
    "outcomes": ["reactivated_30d"],
    "neg_control_map": { "reminder_email_sent": ["region", "signup_date"] },
    "nc_diagnostics": true
  }
}
```

Notes:

- Leave the treatment/outcome columns **unmapped** (`null`) in
  `column_mapping` — they are causal signals, not persona-clustering features,
  and estimability reads them by name from the source rows, not from the
  feature groups.
- Every field but `enabled` is optional. Unset knobs (`auto_neg_controls`,
  `max_treatments`, `max_outcomes`, `max_rows`, ...) fall through to the
  pipeline's own documented defaults — the backend serializes the block with
  `exclude_none`, so only what you set is sent.
- Omit the whole `estimability` block and the build behaves exactly as before:
  no manifest, the grounded-decision chain stays dormant.
- **Spell the top-level key exactly `estimability`.** It is an optional field and
  unknown top-level keys on the build request are silently dropped (the parent
  `BuildConfig` is intentionally permissive for wire forward-compat), so a typo
  like `estimablity` produces **no error and no manifest**. After a white-glove
  build, confirm the manifest was actually written
  (`.../estimability_manifest.json` beside the pack, or the `[estimability] N
  candidate effect(s)` build log line) rather than assuming the block took. Keys
  *inside* the block are typo-protected (`extra="forbid"` → a bad nested key
  raises).

## 3. The organic-variation constraint

Observational grounding needs a **contrast**: the treatment must vary across
users — some exposed, some not. If the lever was shown to **everyone** (or no
one), there is no comparison group and the effect is not estimable from
observational data. In that case route the partner to the **experiment path**
(a real A/B holdout), not this observational one. Confirm the treatment column
has both values present in the view before onboarding.

## 4. Scope

This flow is **white-glove / API-driven** for now: the joined view is authored
by us during onboarding and the `estimability` block is passed on the build
request directly. The wizard UI field for declaring treatment/outcome roles is
**deferred** — it belongs to #565's lever-card surface and is founder-gated.
