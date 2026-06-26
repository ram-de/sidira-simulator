---
type: session
domain: experiment-onboarding
status: open
started: 2026-06-26
owner: ram-de
ticket: "#19"
---

# Session: experiment-onboarding — connect your experimentation platform and pull results

## Goal
Build the missing ONBOARDING flow for the experiment archive (`/memory`). Today the archive
is **synthetic seed data only** (`services/experiment_archive.py::seed_experiments`). This adds
a **connector framework** that ingests real external experiments into the existing `Experiment`
schema, plus a DESIGN.md-compliant onboarding page (`/memory/connect`):
pick a source → authenticate/upload → map fields → preview → import → archive populated.

## Hard constraints (from the ticket)
- **ADD an ingestion/write path. Do NOT refactor the existing read interface** —
  `experiment_archive.seed_experiments()` + `experiment_similarity`/`experiment_chat` are being
  extended by another builder in parallel. The read side is untouched.
- **DESIGN.md is law.** No emoji, no icon library (text glyphs only), tokens only, v2 console
  system (AppShellV2 / v2-theme.css), §8.8 register for the preview table, §8.6 honest
  pending/empty states, radius 2/4/6, §7.7 controls. New vocabulary → DESIGN.md update SAME PR.
- **Two-table firewall**: ingestion keeps the input side (`change_description`, `variants`,
  `primary_metric`, `category`) cleanly separate from the outcome side (`winner`, `result`,
  `effect_size_pct`, `n`, `date`). No leakage path invented — connectors only *map columns*,
  never derive outcome from input or vice versa.
- **HONEST**: CSV works fully NOW. Statsig + SQL are real connectors that work the moment the
  customer supplies credentials — they NEVER fabricate "imported" data. No creds → a clear
  "needs credentials" registered-but-inactive state.

## Architecture decisions
- **No Alembic migration.** Connectors are request-scoped (creds supplied at import time) and
  imports land in an **in-memory ingestion store** keyed by customer (`IngestionStore`). This
  keeps the PR migration-free (clean for the deploy runbook) and avoids touching the read
  interface. A future PR can persist via the existing `credentials.encrypt` + repo pattern
  (mirrors `feature_stores`) when a real customer arrives.
- **Connector registry** (`services/connectors/registry.py`): declarative descriptors —
  `csv` (active), `statsig` (needs key), `sql` (needs connection). The API lists these so the
  UI renders an honest picker (active vs needs-credentials), never a hardcoded CSV form.
- **Field mapping** is the firewall boundary: a `FieldMapping` maps source columns → the 9
  Experiment fields. Pure, deterministic, zero-LLM. `mapping.py` + `csv_connector.py` parse and
  build `Experiment` records; validation reports per-row errors honestly.

## Backend layout
- `schemas/connector.py` — connector descriptors, FieldMapping, import request/result models.
- `services/connectors/` — `base.py` (Connector protocol), `registry.py`, `mapping.py`,
  `csv_connector.py`, `statsig_connector.py`, `sql_connector.py`, `ingestion_store.py`.
- `services/experiment_ingest.py` — the ADD-only write path: validated Experiments → store.
- `api/connectors.py` — `GET /connectors`, `GET /connectors/csv/template`,
  `POST /connectors/csv/preview` (multipart), `POST /connectors/{kind}/validate`,
  `POST /connectors/{kind}/import`, `GET /connectors/imports`.

## Frontend
- `app/memory/connect/page.tsx` + `ConnectFlowV2.tsx` — 5-step flow under AppShellV2.
- `.v2-connect-*` classes in `styles/v2-theme.css` (mirrors `.v2-mem-*`).
- "Connect a source" entry point added to `MemoryConsoleV2`.

## DESIGN.md additions
- §8.9 (new) "Ingestion preview register + connector states" — the preview reuses the §8.8
  register; connector availability uses honest text states (active / needs credentials), no
  new colors/pills/icons. Changelog 0.3.7.

## Status / TODO
- [x] backend connectors + tests (28 tests, all green)
- [x] api routes + wiring in main.py (`/connectors/*`)
- [x] frontend connect flow (`/memory/connect`, 5 steps) + entry point on `/memory`
- [x] DESIGN.md §8.9 + changelog 0.3.7
- [x] tests green (backend connector + experiment-memory + feature-store suites) + `tsc --noEmit` green + `next build` compiles `/memory/connect`
- [x] PR opened (no merge, no deploy)

## What's live vs needs creds
- **CSV**: works end-to-end NOW (parse → map → preview → import populates the archive). Verified via curl.
- **Statsig**: structured; needs the customer's Statsig Console API key. No key → honest `needs_credentials` (0 rows). Network pull isolated in `statsig_connector._fetch_experiments` (stubbed in tests).
- **SQL**: needs the customer's connection string + read-only SELECT. **Postgres + SQLite only**
  (other dialects refused). Defense-in-depth: DB-level read-only transaction (`SET TRANSACTION
  READ ONLY` + `statement_timeout` on Postgres) is the real boundary; the keyword filter +
  function-call/no-FROM rejection is the second layer. Connect/exec errors are sanitized to generic
  messages (raw driver text logged server-side only). Round-trip isolated in `_run_query` (stubbed).

## Codex-review fixes (#488 follow-up, 2026-06-26)
Applied the BLOCKERS + quick MAJORS from the codex review:
- **BLOCKER 1 — SQL real read-only.** `sql_connector` now enforces DB-level read-only as the
  real boundary: Postgres opens with `default_transaction_read_only=on` + `statement_timeout`
  and runs `SET TRANSACTION READ ONLY` then rolls back; SQLite is the only other supported
  backend; any other dialect is **refused** (`SqlUnsupportedBackendError`) rather than trusting
  the keyword filter. `validate_query` now also rejects **function-call SELECTs** (nextval/setval/
  dblink/pg_sleep/proc-call) and **bare expression SELECTs with no FROM**, plus `SELECT … INTO`.
  Advertised support narrowed to Postgres + SQLite; needs-message tells customers to use a
  read-only role. Tests: function-call bypass, setval, SELECT INTO, unsupported backend.
- **BLOCKER 2 — credential redaction.** Joined `/connectors/{kind}/validate|preview|import` to the
  existing `_is_secret_body_path` redactor in `main.py` (the #206/#328 framework). A 422 on a
  credentialed body now redacts the input → secret never echoes. Tests assert the SQL conn-string /
  Statsig key do not appear in the 422 body.
- **MAJOR 3 — sanitize SQL errors.** `_run_query` raises distinct `SqlConnectError` /
  `SqlExecutionError` (raw driver text), logged server-side; the orchestrator returns generic
  "Could not connect with the supplied connection string." / "Query failed under the read-only
  import policy." The customer's own rejected query (guard-rail message) is still shown — it has
  no driver internals.
- **MAJOR 5 — credentialed preview.** Added a real dry-run `preview_import()` + `POST
  /connectors/{kind}/preview` (no store dependency → cannot persist). Frontend PREVIEW step now
  runs the dry-run for Statsig/SQL, shows the mapped rows, and only the explicit
  `Confirm & import to archive →` persists. DESIGN.md §8.9 + changelog 0.3.9 (UI copy lockstep).
- **MAJOR 6 — CSV duplicate/blank headers.** `parse_csv` rejects blank or duplicate (case-insensitive)
  headers up front with a clear "ambiguous mapping" error. Tests added.
- **MINOR 8 — removed the unused `get_descriptor` import** from `experiment_ingest.py`.
- **MAJOR 4 (left intentionally):** added a NOTE comment at the `seed_experiments()` read in
  `api/experiments.py` — the shared seed archive is read un-scoped on purpose until the persisted
  per-tenant archive lands; tracked separately. No memory-read behavior changed.
- **MINOR 7 — left** the conservative keyword filter as the second layer (now backed by the
  DB-level read-only transaction as the real boundary).

Tests: **41/41 connectors green**; full backend **1652 passed** (only the 2 pre-existing
`test_deploy_config` failures remain — see below). `tsc --noEmit` green.

## Pre-existing failures (re-verified against clean `origin/main` checkout)
- `test_deploy_config::test_public_api_is_gated_by_backend_internal_key` and
  `test_deploy_config::test_frontend_splits_public_site_from_product_app_hosts` — both read
  `deploy/` + `frontend/app/page.tsx`, which this PR does NOT touch; they fail on this worktree's
  base state and are unrelated.
- **CORRECTION:** `test_customer_isolation::test_every_route_resolves_the_tenant` was previously
  noted here as pre-existing `_IncludedRouter` drift — that was WRONG. It PASSES on clean main and
  failed only because the PR added connector routes without allowlisting the tenant-agnostic ones.
  **Fixed**: added `GET /connectors`, csv template/sample/preview, and `{kind}/validate` to
  `TENANT_AGNOSTIC_ROUTES` (with a comment). The tenant-scoped `{kind}/preview`, `{kind}/import`,
  and `GET /connectors/imports` correctly depend on `current_customer_id`. Now passes.
- `test_identity_seed::test_cross_process_determinism` did NOT fail in this run.

## Note for a future PR
Imports land in an in-memory `IngestionStore` (migration-free). To persist + connect the ingested
archive to the retrieval pipeline, add a Postgres repo (mirror `feature_stores`: `credentials.encrypt`
+ Alembic migration) once the parallel read-interface work lands — the connector/import API surface
stays the same.
