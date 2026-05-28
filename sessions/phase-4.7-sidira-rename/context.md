---
type: session
domain: phase-4.7-sidira-rename
status: active
started: 2026-05-28
owner: ram-de
---

# Session: phase-4.7-sidira-rename -- pre-launch product rename

## Goal
Rename Pythia to Sidira before public launch, starting with the user-visible simulator product surface and then progressing through config, package names, docs, cross-repo producers, and domain/project metadata.

## In Progress
- [ ] #114 -- Update active simulator docs and roadmap for Sidira. Project status: In Progress.

## Completed
- Created and pushed the Phase 4.7 session file on `main` (`85b8dcf`).
- Moved #111 to In Progress in the GitHub Project.
- Created feature branch `codex/111-sidira-product-surface`.
- Audited active product-surface references. #111 should touch visible frontend copy and FastAPI display metadata, not package/env/repo names.
- Added RED/GREEN backend smoke coverage for Sidira OpenAPI display metadata.
- Implemented #111 visible product-surface rename in frontend app metadata, nav, home page, simulations list copy, product placeholder copy, and FastAPI display metadata.
- Verification passed: backend full suite (`350 passed, 10 skipped`), frontend `npm run typecheck`, `git diff --check`, and live HTTP smoke for home/simulations/product/OpenAPI output.
- Code commit: `0c0f9b0 feat: rename product surface to Sidira`.
- Rebased code commit after session save: `0ce0b63 feat: rename product surface to Sidira`.
- Codex review clear: no discrete correctness issue introduced by the diff.
- PR opened: #116 (`https://github.com/ram-de/pythia-simulator/pull/116`).
- PR #116 squash-merged to `main` as `fb620a1` (`feat: rename product surface to Sidira (#116)`).
- #111 closed as completed and Project status verified as Done.
- Moved #113 to In Progress in the GitHub Project.
- Implemented #113 on `codex/113-sidira-config-env`.
- Added centralized `SIDIRA_*` primary / `PYTHIA_*` fallback resolver, including blank-value fallback handling so copied `.env` templates do not mask legacy values.
- Wired #113 config surfaces: customer scope, CORS, max agents, local artifacts, credential mode/key, and synthesis eval gate.
- Added `backend/.env.example` and updated active setup/docs for Sidira config naming.
- Verification for #113 passed: focused backend config/env tests (`55 passed`), backend full suite (`361 passed, 10 skipped`), frontend `npm run typecheck`, touched-file ruff, `git diff --check`, and `codex review --base main`.
- PR opened: #117 (`https://github.com/ram-de/pythia-simulator/pull/117`). Codex review clear after fixing the blank-env fallback P2.
- Moved #112 to In Progress in the GitHub Project.
- Implemented #112 on `codex/112-sidira-package-rename`.
- Renamed backend package/import surface from `pythia_simulator` to `sidira_simulator`, updated package metadata, canonical `sidira-simulator` CLI entry point, OpenAPI typegen path, and active setup references.
- Kept a temporary pre-launch `pythia-simulator` CLI compatibility alias, but did not keep a `pythia_simulator` import shim.
- Added package metadata/CLI tests and stabilized the pre-existing unseeded bootstrap CI test so full pytest no longer depends on probabilistic rounded-CI variation.
- Verification for #112 passed: backend full suite (`363 passed, 10 skipped`), ruff, black check, frontend `npm run typecheck`, OpenAPI typegen from `sidira_simulator.main:app`, import/CLI smoke, and Codex review.
- PR #117 squash-merged to `main` as `5eef0bb` (`feat: migrate config namespace to Sidira (#117)`).
- PR #118 opened, rebased onto `main` after #117, and squash-merged to `main` as `c141397` (`feat: rename simulator package to Sidira (#118)`).
- #112 and #113 closed as completed; issue body tracking updated to `Status: Done`.
- Moved #114 to In Progress in issue tracking.

## Next Steps
1. Create `codex/114-sidira-active-docs` from updated `main`.
2. Audit active docs: `README.md`, `ONBOARDING.md`, `ROADMAP.md`, `CONTEXT.md`, `AGENTS.md`, `MILESTONES.md`, and current `docs/**`.
3. Update only current team/developer docs for Sidira; do not rewrite closed historical session logs or old PR references.
4. Verify `rg Pythia README.md ONBOARDING.md ROADMAP.md CONTEXT.md AGENTS.md docs` returns only intentional historical/compatibility references.

## Key Files
- `frontend/app/layout.tsx` -- app metadata title/description.
- `frontend/components/TopNav.tsx` -- visible product brand in app chrome.
- `frontend/app/page.tsx` -- homepage hero and active product copy.
- `frontend/app/simulations/**` -- simulation wizard/list/result surfaces.
- `backend/sidira_simulator/main.py` -- FastAPI display metadata and canonical backend app module.
- `backend/sidira_simulator/services/runtime_config.py` -- Sidira env resolver with legacy fallback.
- `backend/pyproject.toml` -- `sidira-simulator` package metadata and CLI entry points.
- `backend/.env.example` -- Sidira-first local backend env template.
- `ONBOARDING.md`, `README.md`, `ROADMAP.md`, `CONTEXT.md`, `docs/**` -- active config/docs updates from #113.

## Key Context
- Phase 4.7 plan: #110.
- First execution ticket: #111.
- Product is pre-public, so deeper rename is appropriate for later tickets, but #111 stays scoped to active product surface and display metadata only.
- Historical session logs should not be bulk rewritten. Remaining `Pythia` references under `sessions/**` are archive context unless a specific active session file needs a note.
- Canonical brand: Sidira. Canonical domain: sidira.ai.
- Remaining #111-scope `rg "Pythia|pythia|PYTHIA" frontend/app frontend/components backend/pythia_simulator/main.py` hits are intentionally not changed in this ticket: `pythia_simulator` import path, `PYTHIA_CORS_ORIGINS`, and `pythia.*` browser draft-storage keys.
- PR #116 shipped the visible product surface only. Package/module/env/repo names remain intentionally tracked by #112/#113/#115.
- #113 did not rename Python package/import paths. It is config/env/docs only, with fallback compatibility.
- #112 completed the hard pre-public Python import/package rename. New code should use `sidira_simulator`; there is no `pythia_simulator` import shim.
- Project board has only Todo / In Progress / Done. #114 is now In Progress; #115 remains Todo and should follow after active docs are coherent.
- #114 is a docs cleanup pass over active team/developer docs only. Historical session logs and old PR references should remain unless the active Phase 4.7 session needs a current-state note.

## For my cofounder
Session opened 2026-05-28. #111, #113, and #112 are merged. Active code now uses Sidira product surface, `SIDIRA_*` config with `PYTHIA_*` fallback, and the `sidira_simulator` backend package. #114 is the active next ticket: update current team/developer docs and roadmap for Sidira without rewriting historical session logs.
