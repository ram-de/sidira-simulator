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
- [ ] Phase 2 of #268 — worker image + deploy wiring. Worktree `persona-worker-phase2`.

## Completed
- [x] Phase 1 (#268) shipped: binding + provider threading + producer→consumer pack
      translation. PR #272 squash-merged to main (22cda1c), backend redeployed
      (SSM 4363ab46, deployed SHA 22cda1c verified descendant, sidira-api healthy,
      `translate_producer_pack`/provider threading confirmed in the running container).
      NO migration. (Tracked in session `snowflake-feature-store-load`, now on main.)

## Next Steps
1. (await) Code survey of build flow / persistence schema / deploy setup (Explore agent).
2. Decide: does the build row already persist request params (source_query,
   column_mapping, stability_threshold, k, weight_schemes, connection_id)? If not →
   schema change + migration so the worker can reconstruct the job from the DB alone.
3. Implement worker poll loop + atomic claim (SELECT … FOR UPDATE SKIP LOCKED or
   UPDATE … WHERE status=pending RETURNING).
4. API: enqueue instead of running `_run_build` in-process.
5. Deploy: separate worker image (vendored wheel + ML deps), compose service
   restart=always, multi-stage build + `docker builder prune` (8GB disk pressure).

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
