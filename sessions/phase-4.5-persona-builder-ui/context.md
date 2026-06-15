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
- [ ] #21 — envelope encryption for feature-store credentials (starting)

## Completed
(nothing yet)

## Next Steps
1. Read `adapters/credentials.py` scaffold; run impact analysis on the credential symbols.
2. Implement #21 KMS/local modes + audit log + unit tests.
3. build/typecheck → codex review → PR → advance to #22.

## Key Files
- `backend/sidira_simulator/adapters/credentials.py` — credential adapter scaffold (#21 target)
- `backend/sidira_simulator/adapters/feature_stores/` — pluggable store Protocol (#22 target)
- `frontend/app/personas/` — wizard route (#27/#28 target)

## Key Context
- Scope confirmed by user: Bucket A (this repo), NOT the sidira-personas pipeline tickets (#1–#7).
- `pythia-personas` is already importable as a library (per #24).
- Acceptance criteria captured per-issue in the GitHub issues (#21–#28).

## For my cofounder
Starting the Phase 4.5 Persona Builder wizard epic as a self-paced autonomy loop over
#21→#22→#23→#24→#25→#27→#28. Each issue gets its own worktree + PR (not auto-merged).
This session file is the coordination point — maintained on `main` from the main checkout.
