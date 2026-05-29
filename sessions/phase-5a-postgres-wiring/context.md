---
type: session
domain: phase-5a-postgres-wiring
status: active
started: 2026-05-29
owner: ram-de
---

# Session: phase-5a-postgres-wiring -- durable simulation metadata

## Goal
Implement #68 so the backend uses Postgres-backed repositories when `DATABASE_URL` is set, while preserving the no-database InMemory fallback for local development and tests.

## In Progress
- [x] Start #68 on `codex/68-postgres-repo-wiring` and audit the current FastAPI dependency, repository, and background-task session boundaries.
- [x] Implement Postgres-backed repo selection when `DATABASE_URL` is set, with InMemory fallback preserved when unset.
- [x] Run focused and full verification, including Codex review/fix cycles.
- [ ] Commit, push, and open the #68 PR.

## Completed
- Created this Phase 5a session after closing the Phase 4.7 Sidira rename/deployment session.
- Read #68 and confirmed scope: wire existing Postgres repositories through FastAPI async sessions; no Clerk/auth, signup, or route-level multi-tenant auth in this ticket.
- Wired FastAPI dependencies so request handlers get a request-scoped `AsyncSession` when Postgres is configured; no-DB local dev still uses process-wide InMemory repos.
- Added a separate background-orchestrator factory so long-running simulations use their own DB session instead of reusing a request-scoped session after the POST returns.
- Hardened Postgres repository behavior: rollback on failed commits, release read-only transactions before LLM/artifact work, atomic customer upsert, deterministic agent listing via `materialization_index`.
- Added Alembic revision `008` for `agent_instances.materialization_index` plus migration/model/repository tests.
- Wired the EC2 deploy helper to pass `/sidira/prod/DATABASE_URL` and `/sidira/prod/SIDIRA_AUTO_MIGRATE` into `/opt/sidira/api.env` when present.
- Normalized provider-style Postgres URLs (`postgres://`, `postgresql://`, and `sslmode=` query params) to SQLAlchemy asyncpg-compatible URLs.
- Verification: backend suite `390 passed, 11 skipped`; focused Postgres/migration/deploy tests `31 passed`; Docker Postgres integration smoke `1 passed`; frontend typecheck passed; ruff/black/diff-check passed; Codex review clean after fixes.

## Next Steps
1. Commit and push the final #68 branch.
2. Open a PR for #68 and link it with `Closes #68`.
3. After merge/deploy, configure production Postgres through SSM Parameter Store rather than local AWS CLI.

## Key Files
- `backend/sidira_simulator/api/deps.py` -- repository/session dependency selection and background orchestrator factory.
- `backend/sidira_simulator/adapters/postgres.py` -- existing lazy async engine/session helpers.
- `backend/sidira_simulator/adapters/repositories.py` -- existing Postgres and InMemory repository implementations.
- `backend/sidira_simulator/api/simulations.py` -- route dependency wiring and background task scheduling.
- `backend/sidira_simulator/services/simulation_orchestrator.py` -- background simulation lifecycle.
- `backend/alembic/` -- existing migrations; optional auto-migration/warn path may touch this.

## Key Context
- #68 is the next pre-customer hardening ticket after Phase 4.7.
- Current production should keep `DATABASE_URL` unset until this branch is merged and deployed. After that, set `/sidira/prod/DATABASE_URL` through SSM Parameter Store and set `/sidira/prod/SIDIRA_AUTO_MIGRATE=1` only for the deployment intended to run Alembic.
- Acceptance requires both paths: with `DATABASE_URL` unset, behavior remains unchanged; with Postgres enabled and migrations applied, simulation list/detail/agents survive process restart.
- Background simulations run outside the original request lifecycle, so they must not reuse a request-scoped session.
- User asked not to use local AWS CLI because it is configured for work. Any production AWS work should stay browser/SSM-console based unless the user explicitly changes that.

## For my cofounder
Phase 4.7 is closed. #68 is implemented and verified on `codex/68-postgres-repo-wiring`; remaining work is PR creation/merge, then production database provisioning through the browser-based AWS flow.
