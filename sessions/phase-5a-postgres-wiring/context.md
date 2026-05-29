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
- [ ] Start #68 on a feature branch and audit the current FastAPI dependency, repository, and background-task session boundaries.

## Completed
- Created this Phase 5a session after closing the Phase 4.7 Sidira rename/deployment session.
- Read #68 and confirmed scope: wire existing Postgres repositories through FastAPI async sessions; no Clerk/auth, signup, or route-level multi-tenant auth in this ticket.

## Next Steps
1. Create the #68 branch from `main` and mark the GitHub issue active.
2. Audit `backend/sidira_simulator/api/deps.py`, `api/simulations.py`, repository implementations, and `SimulationOrchestrator` for session lifecycle boundaries.
3. Add focused tests that lock the InMemory fallback and the Postgres session/repo factory behavior before implementation.
4. Implement request-scoped `AsyncSession` dependencies plus a separate short-lived background-task session path.
5. Run backend tests and frontend typecheck before PR.

## Key Files
- `backend/sidira_simulator/api/deps.py` -- currently stubs Postgres repo wiring when `DATABASE_URL` is set.
- `backend/sidira_simulator/adapters/postgres.py` -- existing lazy async engine/session helpers.
- `backend/sidira_simulator/adapters/repositories.py` -- existing Postgres and InMemory repository implementations.
- `backend/sidira_simulator/api/simulations.py` -- route dependency wiring and background task scheduling.
- `backend/sidira_simulator/services/simulation_orchestrator.py` -- background simulation lifecycle.
- `backend/alembic/` -- existing migrations; optional auto-migration/warn path may touch this.

## Key Context
- #68 is the next pre-customer hardening ticket after Phase 4.7.
- Current production intentionally leaves `DATABASE_URL` unset because the API raises if it is present. Do not add production DB env vars until #68 is implemented, reviewed, and deployed.
- Acceptance requires both paths: with `DATABASE_URL` unset, behavior remains unchanged; with Postgres enabled and migrations applied, simulation list/detail/agents survive process restart.
- Background simulations run outside the original request lifecycle, so they must not reuse a request-scoped session.
- User asked not to use local AWS CLI because it is configured for work. Any production AWS work should stay browser/SSM-console based unless the user explicitly changes that.

## For my cofounder
Phase 4.7 is closed. This session starts #68. The likely risk is session lifetime, not schema design: the adapter classes and migrations already exist, but FastAPI request dependencies and background tasks need separate session scopes.
