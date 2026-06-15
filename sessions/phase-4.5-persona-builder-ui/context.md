---
type: session
domain: phase-4.5-persona-builder-ui
status: active
started: 2026-06-15
owner: ram-de
---

# Session: phase-4.5-persona-builder-ui — self-serve Persona Builder wizard (#21–#28)

## Goal
Ship the Phase 4.5 "Persona Builder UI" epic end-to-end: a self-serve wizard where a
customer connects a feature store (Snowflake) → maps columns → triggers a persona-pack
build (via `pythia-personas` as a library) → watches progress → promotes a pack as latest.

## Execution mode
`/loop` self-paced, **full autonomy** (user choice 2). One issue per iteration in the
dependency order below. Each iteration: `EnterWorktree` → impact analysis → implement →
build/typecheck → `/codex review` → PR → `ExitWorktree`, then advance. Do NOT auto-merge;
leave PRs open for review but keep moving to the next issue. Stop only on a real blocker or
a HIGH/CRITICAL impact warning.
**Session discipline (user instruction):** update this file frequently — capture every key
decision so none are missed. Run a `/pythia-session save` at ~290K tokens (auto-compact
fires at 300K). Session file is maintained from the MAIN checkout, committed to `main`
directly (single source of truth — avoids the PR #64 dual-source conflict across the 7
per-issue worktrees).

## Sequencing (dependency order)
1. **#21** backend: envelope encryption for feature-store creds — KMS prod / local dev + audit log + tests  (foundation)
2. **#22** backend: Snowflake adapter — connect / test / 100-row preview  (dep #21)
3. **#23** backend: column_mapper service — LLM suggests col → 7 feature groups, temp=0, confidence  (dep #22)
4. **#24** backend: persona-builds endpoint — POST trigger / GET status / JSONL events, BackgroundTask, R2 v_N bump  (dep #23)
5. **#25** backend: persona-packs endpoint — list / get / promote (latest pointer)  (dep #24)
6. **#27** frontend: wizard step 2 — column mapping UI w/ LLM suggestions  (dep #22,#23)
7. **#28** frontend: wizard steps 3–7 — review / trigger / watch / promote / done  (dep #24,#25)

Note: #26 (wizard step 1, Snowflake connect form) is already CLOSED. Scaffolding present:
`backend/sidira_simulator/adapters/credentials.py`, `adapters/feature_stores/`,
`frontend/app/personas/`. A prior worktree `persona-pack-v11-ui` exists — check it for reuse.

## In Progress
- [ ] #22 — Snowflake adapter (next)

## Completed
- [x] **#21 — envelope encryption for feature-store credentials** (commit on this branch).
  - Implemented KMS envelope path in `adapters/credentials.py`: per-blob DEK via
    `KMS:GenerateDataKey`, AESGCM-encrypt blob with DEK, persist only KMS-wrapped DEK;
    `KMS:Decrypt` unwraps on read. CMK via `SIDIRA_KMS_KEY_ID`; rotation transparent.
  - Local-key dev path retained unchanged.
  - Audit log on every write+read: `credential_access` structlog event with
    `action`/`key_id`/`customer_id`/`at` on channel `sidira.credentials.audit`.
  - Threaded optional `customer_id` kwarg into `encrypt`/`decrypt` (backward-compatible);
    updated 3 call sites (crawls.py save + dispatch preflight, internal.py pull).
    `_require_dispatchable_credentials` gained a `customer_id` param.
  - Tests: `tests/test_credentials_envelope.py` (12 tests, KMS faked). ruff clean.
  - **761 passed**, 11 skipped; the 1 failure `test_deploy_config::test_frontend_splits_
    public_site_from_product_app_hosts` is PRE-EXISTING on `main` (verified) — not ours.

## Next Steps
1. #22 Snowflake adapter in `adapters/feature_stores/` — read scaffold + existing Protocol.
2. Continue backend chain #22→#23→#24→#25 on this branch (per-issue commits).
3. Run `/codex review` ONCE on the full backend diff before opening the backend PR.

## Key Files
- `backend/sidira_simulator/adapters/credentials.py` — #21 DONE (KMS + audit)
- `backend/sidira_simulator/adapters/feature_stores/` — pluggable store Protocol (#22 target)
- `backend/tests/test_credentials_envelope.py` — #21 tests
- `frontend/app/personas/` — wizard route (#27/#28 target)

## Key Context
- Scope confirmed by user: Bucket A (this repo), NOT the sidira-personas pipeline tickets (#1–#7).
- Execution: full-autonomy loop (user choice 2). PACKAGING DECISION: backend chain #21–#25 →
  ONE branch `worktree-phase-4.5+persona-builder-backend`, one commit per issue, ONE PR
  (tightly-coupled additive work; avoids stacked-rebase churn, dependency-safe). Frontend
  #27–#28 → separate branch based off the backend branch → second PR.
- TEST RUNNER (worktrees have no .venv): `cd <worktree>/backend && PYTHONPATH=$(pwd) \
  /Users/ram/Projects/sidira-simulator/backend/.venv/bin/python -m pytest`. ruff via same venv.
- GitNexus MCP is OFFLINE this session → impact analysis is grep-based caller mapping.
- codex review deferred to ONCE-per-PR (token budget), not per-issue.
- `pythia-personas` is already importable as a library (per #24).
- Acceptance criteria captured per-issue in the GitHub issues (#21–#28).

## For my cofounder
Starting the Phase 4.5 Persona Builder wizard epic as a self-paced autonomy loop over
#21→#22→#23→#24→#25→#27→#28. Each issue gets its own worktree + PR (not auto-merged).
This session file is the coordination point — maintained on `main` from the main checkout.
