---
type: session
domain: feature-store-connection-health
status: complete
started: 2026-06-16
owner: ram-de
---

# Feature-store connection HEALTH / last-tested status (#328)

Fast-follow to **#327** (saved-connections register: dense identity rows, delete,
unique-name). #328 adds the missing piece: per-connection HEALTH so users can see
WHICH saved connection is dead before they hit the Test step.

## Scope shipped

### Backend
- **Alembic migration `014_feature_store_connection_health.py`** (`down_revision = "013"`).
  Adds four NULLABLE columns to `feature_store_connections`:
  `last_tested_at` (timestamptz), `last_test_status` (text 'ok' | 'failed'),
  `last_error_kind` (text), `last_error_message` (text). Nullable so every
  pre-existing row reads as UNTESTED — no backfill. `downgrade()` drops all four
  in reverse order. Verified up/down DDL via `alembic upgrade/downgrade --sql`.
- **ORM** (`db_models.py`): four nullable mapped columns added to
  `FeatureStoreConnection`. `_feature_store_connection_to_dict` returns them.
- **Repos** (`repositories.py`): new `record_test_result(connection_id, customer_id,
  *, status, tested_at, error_kind, error_message)` on the Protocol + BOTH
  `PostgresFeatureStoreConnectionRepo` and `InMemoryFeatureStoreConnectionRepo`.
  **Customer-scoped**: an unknown id OR another tenant's id returns False and
  writes nothing (security requirement). InMemory `insert` seeds the health keys
  as None so a fresh row reads UNTESTED, matching the nullable Postgres columns.
- **Route** (`api/feature_stores.py`): `POST /{id}/test` now persists its outcome —
  success → status='ok', tested_at=now, error fields cleared; failure → status='failed',
  tested_at=now, error_kind (from the classified `FeatureStoreConnectionError.kind`)
  + error_message. HTTP contract unchanged (204 on success / structured error on
  failure); persistence is best-effort metadata, ADDED only. `ConnectionSummary`
  schema + `_summary_from_row` extended to return the four fields. Password still
  never returned.

### Frontend
- `lib/api.ts`: `ConnectionSummary` extended with the four optional fields +
  `ConnectionTestStatus` type. `lib/api-types.ts` hand-edited to match (the
  checked-in file is intentionally stale for drifted routes).
- `app/personas/new/page.tsx`:
  - `connectionHealthLine()` derives the status IN WORDS — `OK · TESTED JUN 15`
    (`terseTestedDate` → TODAY/YESTERDAY/`MON DD`), `FAILED · AUTH`, `UNTESTED`.
    No dots, no color-coded fill (DESIGN.md §4.3/§10).
  - Each register row (`SavedConnectionRow`) shows the health line in the mono
    caption rail AND carries a quiet **TEST** affordance (hairline mono text
    button) that calls `testFeatureStore(id)` in place, then re-fetches the list
    so the row's status updates WITHOUT selecting the connection or leaving the
    picker. In-flight shows `TESTING…` (honest text, §8.6). A failed test flips
    the row to `FAILED · …`.
  - The collapse-on-select `SavedConnectionSummary` also shows a health Chip.

## #327 not regressed
Delete, unique-name, collapse-on-select, register density, reuse-by-id all
intact. The status line + TEST action only ADD to each row.

## Verification (all green)
- Frontend: `npm ci && npm run build` (tsc) — PASS.
- Backend (Python 3.11 venv `.venv-328`):
  `python -m pytest tests/test_feature_stores_api.py tests/test_repositories.py -q`
  → 44 passed. New tests: untested→null, test-success→ok+timestamp+cleared error,
  test-failure→failed+kind+message, failed-then-pass clears error; repo
  customer-scoping + null-seed.
  `ruff check` on touched files → clean.
  Migration: `alembic upgrade 013:014 --sql` and `downgrade 014:013 --sql`
  generate correct ALTER ADD/DROP COLUMN; single head `014`, chain valid.

## Deploy note
**Touches `backend/` AND adds Alembic migration `014`.** The redeploy MUST run
migrations: set `SIDIRA_AUTO_MIGRATE=1` per `deploy/REDEPLOY.md`, then reset to 0.
Depends on #327 (already merged to main).
