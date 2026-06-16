---
type: session
domain: phase-2-persona-worker
status: active
started: 2026-06-15
owner: ram-de
---

# Session: phase-2-persona-worker — #268 Phase 2 (worker image + deploy wiring)

## Goal
Move the persona-build pipeline off the in-process FastAPI BackgroundTask onto a
separate **triggered worker** (polls Postgres for pending builds, runs
`run_personas_pipeline`, writes pack+manifest to R2, updates the build row) so the
ML stack (numpy/sklearn/scipy + the `sidira_personas` wheel) stays OUT of the API
image. The wizard's `202` + status-polling contract is unchanged. Per #268 decision (C).

## In Progress
- [ ] Open PR (ram-de) → merge → redeploy WITH migration 013 → verify worker container + real build.

## Built + verified (ready to PR)
- [x] Migration 013 (`config_json` JSONB on persona_build_runs); single alembic head 013.
- [x] Repo: `create(config_json=)`, atomic `claim_next_pending()` (FOR UPDATE SKIP LOCKED),
      `fail_orphaned_running()` startup reaper; Postgres + InMemory mirrors.
- [x] API dual-mode dispatch via `SIDIRA_PERSONA_BUILD_MODE` (inprocess code-default | worker);
      persists config_json on every create.
- [x] Worker (`sidira_simulator/worker/`): mode-gated (idles in inprocess so no double-claim),
      startup recovery of orphaned RUNNING rows, graceful FAILED on null/invalid config,
      `main()` checks mode before the Postgres requirement (no restart-loop in inprocess).
- [x] `Dockerfile.worker` (multi-stage, vendored wheel WITH ML deps) + compose `worker` service
      + `ec2-api-deploy.sh` (mode default = worker only when DB+compose; prune) + REDEPLOY.md.
- [x] 17 worker/repo tests; ML isolation confirmed (API imports no pandas/sklearn/numpy/scipy);
      ruff clean; full suite 979 pass (1 known-unrelated frontend fail).
- [x] **codex review CLEAN** after 4 rounds of P1/P2 fixes (compose env-mask, deploy default,
      worker mode-respect, orphaned-running reaper, invalid-config guard, main() mode-gate,
      and honest docs: inprocess is NOT a prod rollback — API image omits ML by design).

## Completed
- [x] Phase 1 (#268) shipped: binding + provider threading + producer→consumer pack
      translation. PR #272 squash-merged to main (22cda1c), backend redeployed
      (SSM 4363ab46, deployed SHA 22cda1c verified descendant, sidira-api healthy,
      `translate_producer_pack`/provider threading confirmed in the running container).
      NO migration. (Tracked in session `snowflake-feature-store-load`, now on main.)

## Survey findings (Explore, done)
- **Build row persists NONE of the BuildConfig** (only id/customer_id/connection_id/
  status/pack_version/stability_score/persona_count/error/created_at/completed_at).
  Config (source_query, column_mapping, stability_threshold, k, llm_provider,
  weight_schemes) lived only in the in-process BackgroundTask. → **migration 013 REQUIRED.**
- `PersonaBuilderService.run()` already drives the row RUNNING→COMPLETE/FAILED
  (persona_builder.py:357/407/450); it expects the row to pre-exist (created by route).
- `_run_build` (persona_builds.py:77) resolves its OWN session/repos (Postgres when
  configured, else in-memory) — the worker mirrors this exactly.
- Wheel installs full ML stack via declared deps (numpy/pandas/sklearn≥1.4/scipy≥1.11/
  hdbscan/anthropic/openai/snowflake-connector/pyarrow) → `pip install the.whl` (WITH
  deps) is sufficient; no need to enumerate. `wheels/` not git- nor docker-ignored.
- Tests monkeypatch `run_personas_pipeline` in the persona_builder module
  (test_persona_builds_api.py:129) — reuse for worker tests.

## Locked architecture (decisions)
1. **Config persistence = Option B: single `config_json` JSONB column** (migration 013,
   nullable). `create()` persists `BuildConfig.model_dump(mode="json")`; worker rebuilds
   via `BuildConfig.model_validate(row["config_json"])`. Self-documenting, no schema sprawl.
2. **Dual-mode dispatch via `SIDIRA_PERSONA_BUILD_MODE`** = `inprocess` (code default) |
   `worker`. create_build ALWAYS persists the row+config; then inprocess → schedule the
   BackgroundTask (current behavior, keeps dev + all existing tests green untouched),
   worker → enqueue only (worker claims). Prod/deploy default = `worker`.
3. **Atomic claim = `claim_next_pending()`** on the repo (NOT customer-scoped): Postgres
   `SELECT … ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED` → flip RUNNING → return
   row dict (incl. config_json); in-memory mirror. Claim pre-sets RUNNING; run() re-setting
   RUNNING is idempotent.
4. **Worker** = `sidira_simulator/worker/persona_worker.py` (+ `__main__.py`): per-job fresh
   session, claim → `BuildConfig.model_validate` → `PersonaBuilderService.run`; idle-sleep
   loop; requires Postgres (clear exit if not). `python -m sidira_simulator.worker`.
   config_json None (legacy/inprocess row) → mark FAILED gracefully, don't crash.
5. **Deploy** = vendored `backend/wheels/sidira_personas-0.1.0-…whl` (DONE) +
   `backend/Dockerfile.worker` (multi-stage: `pip install .` then `pip install wheels/*.whl`)
   + compose `worker` service (`restart: always`, same env_file + bind-mount, `depends_on:
   api`, `SIDIRA_PERSONA_BUILD_MODE=worker`). API image/Dockerfile UNCHANGED (no ML deps).
   ec2-api-deploy.sh: write `SIDIRA_PERSONA_BUILD_MODE` (default `worker`) + `docker builder
   prune -af` after build (8GB disk). REDEPLOY.md: note migration 013 + new service + prune.

## Next Steps
1. Commit to feature branch + open PR as ram-de.
2. After merge: **redeploy WITH migration 013** (AUTO_MIGRATE or manual `alembic upgrade head`).
   Flag explicitly — changes REDEPLOY step 2. inprocess is NOT a prod rollback (API image has
   no ML stack); rollback = revert + redeploy.
3. Verify post-deploy: `sidira-persona-worker` container Up + a real Build produces a pack.

## Key Files
- `backend/sidira_simulator/services/persona_builder.py` — the binding (Phase 1).
- (Phase 1 wheel) `/Users/ram/Projects/sidira-personas/dist/sidira_personas-0.1.0-py3-none-any.whl`
  built off sidira-personas main `a57e855`; NOT yet committed anywhere — worker image must vendor it.

## Key Context
- **Wheel not in repo.** Built into the backend dev venv only. Worker Dockerfile must
  install a vendored copy (commit it into the build context, e.g. `deploy/wheels/`).
- **Prod is Postgres-backed** (`/sidira/prod/DATABASE_URL` in SSM) → worker can claim
  build rows. Verified in #268.
- **8GB EC2 root fills with docker build cache** — multi-stage build + `docker builder
  prune -af` in deploy; keep worker image separate from API image.
- **Worker needs the same secrets as the API**: `SIDIRA_LOCAL_CRED_KEY`/`SIDIRA_CRED_MODE`
  (decrypt connection creds, AAD = `customer_id:connection_id`), DATABASE_URL, R2 creds,
  Snowflake reachability, optional LLM keys (GROQ/ANTHROPIC) for naming.
- Manual backend redeploy after merge; migration ONLY if a build-schema change lands.

## For my cofounder
Building the #268 Phase 2 worker so the prod Build step actually produces packs.
Phase 1 (binding) is live but the API image lacks the ML stack, so a real Build still
errors until this worker ships. Worktree `persona-worker-phase2`.
