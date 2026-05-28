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
- [ ] #113 -- Migrate simulator config from `PYTHIA_*` to `SIDIRA_*` with fallbacks. PR #117 open, Project status: In Progress until merge.
- [ ] #112 -- Rename simulator package, imports, and CLI to Sidira. Project status: In Progress; next branch should stack on #113 until #117 merges.

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

## Next Steps
1. Create `codex/112-sidira-package-rename` as a stacked branch from `codex/113-sidira-config-env` unless #117 merges first.
2. Run an impact audit for package/import/CLI rename: backend package directory, imports, `pyproject.toml`, scripts, typegen, docs, and tests.
3. Plan #112 compatibility boundary: decide whether to keep a temporary `pythia_simulator` import/CLI shim or do a hard pre-public rename.

## Key Files
- `frontend/app/layout.tsx` -- app metadata title/description.
- `frontend/components/TopNav.tsx` -- visible product brand in app chrome.
- `frontend/app/page.tsx` -- homepage hero and active product copy.
- `frontend/app/simulations/**` -- simulation wizard/list/result surfaces.
- `backend/pythia_simulator/main.py` -- FastAPI display metadata only, if touched.
- `backend/pythia_simulator/services/runtime_config.py` -- Sidira env resolver with legacy fallback.
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
- #113 should not rename Python package/import paths. It is config/env/docs only, with fallback compatibility.
- #113 PR is open as #117 and should merge before or underneath #112 to avoid package-rename conflicts.
- Project board has only Todo / In Progress / Done. #113 remains In Progress while PR #117 is open; #112 is now also In Progress.
- #112 is the next logical code ticket. #114 is docs cleanup and may overlap with #112; #115 is later after code/domain deployment decisions.

## For my cofounder
Session opened 2026-05-28. #111 is merged. #113 has PR #117 open and passing review for `SIDIRA_*` config namespace migration with `PYTHIA_*` fallback. #112 is now the active next ticket; start it from #113 until #117 merges, then rebase onto `main`.
