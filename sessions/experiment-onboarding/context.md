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
- **SQL**: structured; needs the customer's connection string + read-only SELECT. Read-only guard rejects DML/DDL/multi-statement. DB round-trip isolated in `sql_connector._run_query` (stubbed in tests).

## Pre-existing failures (NOT mine, confirmed on clean main)
`test_customer_isolation::test_every_route_resolves_the_tenant` (FastAPI `_IncludedRouter` version drift),
`test_deploy_config` (2), `test_identity_seed::test_cross_process_determinism` — all fail identically on stock `origin/main` in this env.

## Note for a future PR
Imports land in an in-memory `IngestionStore` (migration-free). To persist + connect the ingested
archive to the retrieval pipeline, add a Postgres repo (mirror `feature_stores`: `credentials.encrypt`
+ Alembic migration) once the parallel read-interface work lands — the connector/import API surface
stays the same.
