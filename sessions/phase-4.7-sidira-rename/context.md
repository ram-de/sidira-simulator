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
- [ ] #115 -- Configure sidira.ai deployment, origins, and project metadata. Project status: In Progress.

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
- Implemented #114 on `codex/114-sidira-active-docs`.
- Updated active simulator docs, onboarding, roadmap, context, architecture/design docs, and agent instructions to read as Sidira while preserving intentional historical, compatibility, and current `pythia-*` repo/package references.
- Verification for #114 passed: backend full suite (`363 passed, 10 skipped`), frontend `npm run typecheck`, `git diff --check main...HEAD`, and `codex review --base main`.
- PR #119 opened and squash-merged to `main` as `7e07922` (`docs: update active Sidira roadmap and onboarding (#119)`).
- #114 closed as completed and issue body tracking updated to `Status: Done`.
- Moved #115 to In Progress in issue tracking.
- Created #115 feature branch `codex/115-sidira-domain-metadata`.
- Updated GitHub metadata outside the repo: Project #1 title is now Sidira; `pythia-simulator`, `pythia-personas`, and `pythia-crawler` repo descriptions/homepages now use Sidira and `https://sidira.ai`.
- Chose not to rename repos yet. Repo/package names remain `pythia-*` until producer-package alignment is explicitly scheduled.
- Added first #115 local commit on the feature branch (`aba778c docs: add Sidira domain deployment runbook`) with frontend/backend deploy env examples and `docs/sidira-domain-runbook.md`.
- DNS audit: `sidira.ai` resolves to `162.255.119.57` but HTTPS does not answer; `app.sidira.ai` and `api.sidira.ai` do not resolve yet.
- Verification for first #115 local slice passed: `git diff --check`, frontend `npm run typecheck`, and focused backend config tests (`14 passed`).
- Added AWS deployment scaffold in commit `4303653`: Amplify monorepo build spec, backend Dockerfile, Docker ignore, and browser-console-friendly Docker Compose/Caddy API host for a small Lightsail/EC2 VM.
- Verification for #115 deployment scaffold passed: `git diff --check`, frontend `npm run typecheck`, frontend `npm run build`, focused backend tests (`18 passed`), `docker compose ... config`, `docker build -t sidira-api:local backend`, and image import smoke.
- Opened AWS Console via browser only. Route 53 currently shows zero hosted zones; paused before creating `sidira.ai` hosted zone because it is billable.

## Next Steps
1. If approved, create a Route 53 public hosted zone for `sidira.ai` in the personal AWS account, then copy the assigned NS values into Namecheap Custom DNS.
2. Create an Amplify Hosting app for `ram-de/pythia-simulator` with monorepo root `frontend`, `AMPLIFY_MONOREPO_APP_ROOT=frontend`, and `NEXT_PUBLIC_API_BASE=https://api.sidira.ai`.
3. Create a small Lightsail/EC2 API VM, attach static IP, point `api.sidira.ai` at it, and run `docker compose -f deploy/docker-compose.api.yml up -d --build` from browser SSH.
4. Open PR for `codex/115-sidira-domain-metadata`, run Codex review, and merge after the external DNS/hosting state is recorded or explicitly deferred.

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
- `AGENTS.md`, `MILESTONES.md`, `docs/system-architecture.md`, `docs/feature-pack-crawler-spec.md`, `docs/mirofish-prior-art.md` -- active Sidira docs updates from #114.
- `frontend/.env.example` -- frontend API base example for local and Sidira production.
- `docs/sidira-domain-runbook.md` -- canonical hostnames, deploy env, DNS/HTTPS checklist, GitHub metadata checklist, rollback notes.
- `amplify.yml` -- AWS Amplify monorepo build spec for `frontend/`.
- `backend/Dockerfile`, `backend/.dockerignore` -- FastAPI production image scaffold.
- `deploy/docker-compose.api.yml`, `deploy/Caddyfile.api`, `deploy/README.md` -- browser-console-friendly API VM deployment path.

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
- Project board has only Todo / In Progress / Done. #114 is Done; #115 is now In Progress.
- #114 shipped the active team/developer docs cleanup. Historical session logs and old PR references were preserved unless they needed active current-state notes.
- #115 is the final Phase 4.7 ticket currently tracked in the roadmap: sidira.ai deployment/origins and GitHub metadata/repo-name decision.
- #115 is partially complete: GitHub metadata and local deploy docs/env examples are done; DNS/hosting is not complete because `app.sidira.ai` and `api.sidira.ai` do not resolve yet.
- App Runner is not the right first backend choice for a new personal AWS account because AWS docs now say App Runner is no longer open to new customers.
- User asked not to use local AWS CLI because it is configured for work; all AWS actions for this task should use the browser console / browser SSH unless the user explicitly says otherwise.
- For a browser-only backend bootstrap, prefer Amplify for frontend plus a small Lightsail/EC2 API VM running Docker Compose and Caddy. Lightsail Containers can be revisited after a clean image-publishing path exists.

## For my cofounder
Session opened 2026-05-28. #111, #113, #112, and #114 are merged. #115 is active on `codex/115-sidira-domain-metadata`: GitHub Project/repo descriptions are Sidira, local deployment scaffold is pushed, AWS Console is open in the browser, and Route 53 hosted-zone creation is waiting on explicit approval because it is billable. Remaining blocker is external DNS/hosting: root `sidira.ai` resolves but does not serve HTTPS, and `app.sidira.ai` / `api.sidira.ai` do not resolve yet.
