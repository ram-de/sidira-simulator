---
type: session
domain: snowflake-feature-store-load
status: active
started: 2026-06-15
owner: ram-de
---

# Session: snowflake-feature-store-load — load synthetic feature-store data into Snowflake via Snowflake MCP

## Goal
Stand up a Snowflake MCP connection and load the synthetic consumer feature-store
dataset into Snowflake so the product's `SnowflakeStore` feature-store adapter
path can be exercised against realistic data.

## In Progress
- [ ] Phase 1 of #268 — binding code complete; **PR #272 open** (awaiting merge). After merge: manual backend redeploy (NO migration; does NOT fully unblock prod Build — needs Phase 2 worker image for the ML wheel).
- [ ] Phase 2 of #268 (later) — worker image + deploy wiring (poll Postgres, API enqueues).

## Persona-pipeline binding (#268) — NEW WORK after decrypt fix
- [x] Diagnosed the post-decrypt "sidira-personas not installed" failure as an UNBUILT feature (intentional phase-4.5 stub), not a bug. No existing ticket covered it.
- [x] Deliberated architecture (assistant + codex): chose **worker model** (not R2-read #208, not BackgroundTasks). Verified prod is Postgres-backed (`/sidira/prod/DATABASE_URL` exists) → worker prerequisite satisfied. Operational driver: sidira-personas pulls sklearn/numpy/scipy → keep ML deps in a SEPARATE worker image (8GB EC2 root already fills with docker build cache).
- [x] Filed **issue #268** (worker model + A/B/C analysis + Postgres/disk findings + 2-phase plan).
- [x] **Phase 1a DONE:** extracted pure `run_pipeline(df, cfg, *, run_id, no_llm, log) -> PipelineResult` in sidira-personas (was buried in `cli.run`). PR #14 → squash-merged to sidira-personas main (7da118b). 45 tests pass, ruff clean, codex no-blocking. CLI is now a thin wrapper; smoke test guarantees behaviour preservation.
- [x] **Phase 1b (binding) DONE — "infer now, override later" (option C, user-approved).** Replaced the `run_personas_pipeline` stub in `persona_builder.py` with the real binding + pure-Python (pandas-free) helpers: `_infer_adapter_type(values)` infers each column's adapter type (json_ratios/json_counts w/ union keys → tenure_days → flag → ratio → count → score → categorical fallback) and `_build_pipeline_config(rows, mapping, config, customer_id)` assembles the full pipeline cfg (feature_groups w/ inferred types grouped by FeatureGroup, snapshot/user-id/orders/revenue detected by name, weight schemes translated head_count→headcount etc. w/ headcount always forced, k "auto"→[3,8] / int→[k,k]). New sig `run_personas_pipeline(rows, column_mapping, config, customer_id, run_id)` lazy-imports pandas + `sidira_personas.run_pipeline` (ModuleNotFoundError → clear RuntimeError) so the module still imports in the API image. Dropped `_apply_column_mapping`; `run()` now passes raw rows + customer_id + build_id. Verified: module imports with NO pandas loaded; ruff clean; 8 build-API tests + 18 new binding unit tests (`tests/test_persona_builder_binding.py`) pass; full suite 920 pass / 1 known-unrelated fail (`test_deploy_config` frontend-content). Worktree `persona-pipeline-binding`.
- [x] **Phase 1c (Task #17) DONE — wheel + end-to-end validation.** Built pinned private wheel `sidira_personas-0.1.0-py3-none-any.whl` (`pip wheel . --no-deps`, off main@7da118b) and installed it + deps into the backend dev venv (pandas 3.0.3 / numpy 2.4 / sklearn 1.9 — no compat issues). Validated `run_personas_pipeline` end-to-end TWICE: (1) synthetic fixture as dict-rows, (2) **live SIDIRA.SYNTHETIC.USERS_FEATURE_STORE (1500 rows)** via the key-pair `sidira` connection. Both → 6 personas (P01–P06), stability 0.6124, one prompt/persona, JSON-serializable pack. **Zero-config inference reproduced the hand-curated `config/synthetic.yaml` types EXACTLY** incl. JSON keys (day_of_week_profile→json_counts[weekday,weekend], category_motivation→json_ratios[grocery,restaurant,retail]); snapshot_date auto-detected, consumer_id as user_id, signup_date as tenure. Live table stores dates as VARCHAR (strings) so the string path handled them — but that surfaced a latent gap: native DATE/TIMESTAMP cols return `datetime.date` (NOT a `datetime` subclass) → **hardened `_looks_like_date` to `isinstance(value, date)`** + added a native-date unit test. Final: ruff clean, 19 binding unit tests + 8 build-API tests pass.
- [x] **Follow-up FILED → issue #271:** wizard adapter-type override (the "later" half of infer-now-override-later) — surface each inferred adapter type in the wizard Map step with a user override.
- [x] **Phase 1d (codex review fixes) DONE — two material findings resolved, binding PR opened.**
  - **Finding 1 (provider ignored):** `run_personas_pipeline` ignored `BuildConfig.llm_provider`; the producer picked an LLM by env order (Groq first), so the wizard's "Naming model" control was a no-op + builds non-reproducible. Fixed in **sidira-personas**: added a `provider` param threaded `run_pipeline → llm_name / llm_provider_in_use`; a forced provider routes only to that backend (key absent → None generic fallback, never silent cross-fallback); an *unknown* provider raises `ValueError` (never auto-selects). **PR #15 squash-merged to sidira-personas main (a57e855)**, 53 tests pass (was 45), ruff clean. Binding now calls `run_pipeline(..., provider=config.llm_provider)`. **Wheel rebuilt from a57e855** (`sidira_personas-0.1.0-py3-none-any.whl`, 26548 B) + reinstalled into backend dev venv.
  - **Finding 2 (schema mismatch, P1):** `_write_pack` persisted the raw *producer* wire dict (`asdict(pack)`: company_id/created_at/overall_stability + per-persona weights), but `PersonaPackLoader.load_at_version` validates `persona_pack.json` as the *consumer* `PersonaPack` — a completed build would write an artifact `/persona-packs`/promote/evaluate/sims can't load. Fixed: `_write_pack` now runs the wire dict through the existing tested `translate_producer_pack(output.persona_pack, version=pack_version)` (version pinned to the R2 path segment v_N, not run_id) and writes `pack.model_dump_json()`. Verified the **real** `run_pipeline` output translates + round-trips through the consumer schema; added a regression test (persisted pack validates as `PersonaPack` + loader reads it back); updated the build-API fake to producer-wire shape. Full backend suite **922 pass** / 1 known-unrelated fail; ruff clean; **codex re-review: no material findings.**
  - Binding branch `worktree-persona-pipeline-binding` (3 commits) → **PR #272** (ram-de).

## Completed
- [x] Located the synthetic dataset and confirmed its shape
- [x] Decisions: existing account, key-pair auth, load BOTH datasets
- [x] Generated RSA key-pair (~/.snowflake/sidira_snowflake_key.p8 chmod 600, .pub registered on user)
- [x] Installed tooling in ~/.snowflake/venv: snow CLI 3.20, connector 4.6, snowflake-labs-mcp 1.3.3, pandas+pyarrow
- [x] Account HWATYVV-XD01132, user SIDIRA, role ACCOUNTADMIN; public key registered (fp SHA256:T7duc...D3TM=); JWT connection ✔
- [x] Created warehouse COMPUTE_WH (pre-existing) + DB SIDIRA + schema SYNTHETIC
- [x] Loaded SIDIRA.SYNTHETIC.USERS_FEATURE_STORE (1500 rows × 24 cols) via write_pandas
- [x] Loaded SIDIRA.SYNTHETIC.SIMULATION_EVENTS (2841 rows, 229 sims, PAYLOAD VARIANT) via write_pandas + PARSE_JSON
- [x] Registered `snowflake` MCP server (local scope, ~/.claude.json) → `claude mcp list` shows ✔ Connected
- [x] Loader script saved at /tmp/sf_load.py; MCP service config at ~/.snowflake/mcp_service_config.yaml
- [x] Diagnosed wizard Step-03 "cannot decrypt credentials" Build failure → code bug: `persona_builder._snowflake_store` decrypted the connection password WITHOUT the AAD (`f"{customer_id}:{connection_id}"`) that `create_connection` seals it with; only `_snowflake_store` was missed when AAD binding was added (preview path `_store_from_row` had it). Affected EVERY feature-store persona build, not just ours. The error's "rotate key / re-save" hint is a red herring.
- [x] Fixed in worktree fix-snowflake-build-decrypt-aad → PR #265 (ram-de). One-line decrypt fix + test seed now AAD-bound (it had masked the bug) + explicit regression test. ruff clean; 8/8 build tests pass; full suite 878 pass (only known unrelated test_deploy_config fail); codex review no blocking findings.
- [x] PR #265 squash-merged to main (59a9ad9) + backend redeployed to api.sidira.ai via SSM (cmd de20b479, instance i-04b155fafcc90042b). Verified: deployed SHA 8b3cd30 (descendant of fix, no revert), container has aad at persona_builder.py:246, sidira-api healthy. NO migration. Wizard Build step is now unblocked.

## Next Steps
1. Collect Snowflake connection details (account / user / warehouse / role / db / schema) — secrets go in a config file, never chat
2. Choose auth method (key-pair preferred for MCP)
3. Install + configure the Snowflake MCP server
4. Create target table + load 1,500 rows (PUT to stage + COPY, or `write_pandas`)
5. Verify row count + a sample SELECT through the MCP
6. Optionally wire the loaded table into the `SnowflakeStore` adapter for an end-to-end test

## Key Files
- `sidira-personas/fixtures/synthetic/users.parquet` — the dataset (1500 rows × 24 cols)
- `backend/sidira_simulator/adapters/feature_stores/snowflake.py` — product's Snowflake adapter (SnowflakeStore; needs `snowflake-connector-python`)
- `backend/sidira_simulator/adapters/feature_stores/__init__.py` — FeatureStore Protocol + TablePreview/ColumnProfile

## Key Context
- **Dataset = consumer feature store.** 24 cols: consumer_id, snapshot_date, signup_date, region,
  device_count, total_orders_lifetime, order_frequency_28d, avg_days_between_orders,
  day_of_week_profile (JSON str), deal_seeker_flag, convenience_ratio, category_motivation (JSON str),
  high_fee_rate, unsubscribe_rate, promo_redeemer_flag, out_of_pocket_per_order, discount_share,
  notification_channel, open_within_24h, click_within_24h, notifications_weekly,
  cx_lifestage_detailed_status, active_28d, hv_segment.
- Two JSON-string columns (day_of_week_profile, category_motivation) — load as VARCHAR or VARIANT (PARSE_JSON).
- No Snowflake CLI/MCP installed yet; no `~/.snowflake/connections.toml` present.
- The product's `SnowflakeStore` already targets this exact use case (customer feature store → persona builder), so loading here doubles as adapter test data.
- Alternative dataset (not chosen unless user says): 229 simulation runs / 2841 events in `local-artifacts/.../events.jsonl`.

## For my cofounder
Standing up Snowflake MCP + loading the synthetic feature-store parquet (1500 consumer rows)
so we can test the SnowflakeStore adapter against real-ish data. Blocked on Snowflake account
details from Ram. Secrets go in `~/.snowflake/connections.toml`, never in chat or git.
