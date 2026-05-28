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
- [ ] #111 -- Rename simulator product surface to Sidira.

## Completed
(nothing yet)

## Next Steps
1. Move #111 to In Progress in the GitHub Project.
2. Create branch `codex/111-sidira-product-surface`.
3. Audit active user-facing `Pythia` references in frontend and backend API display metadata.
4. Implement the #111 product-surface rename without touching package/env/repo names.
5. Verify frontend typecheck and backend tests if API display metadata changes.

## Key Files
- `frontend/app/layout.tsx` -- app metadata title/description.
- `frontend/components/TopNav.tsx` -- visible product brand in app chrome.
- `frontend/app/page.tsx` -- homepage hero and active product copy.
- `frontend/app/simulations/**` -- simulation wizard/list/result surfaces.
- `backend/pythia_simulator/main.py` -- FastAPI display metadata only, if touched.

## Key Context
- Phase 4.7 plan: #110.
- First execution ticket: #111.
- Product is pre-public, so deeper rename is appropriate for later tickets, but #111 stays scoped to active product surface and display metadata only.
- Historical session logs should not be bulk rewritten. Remaining `Pythia` references under `sessions/**` are archive context unless a specific active session file needs a note.
- Canonical brand: Sidira. Canonical domain: sidira.ai.

## For my cofounder
Session opened 2026-05-28. Starting with #111 because it gives immediate product consistency with low blast radius. Package/module/env/repo renames are tracked separately in #112/#113/#115 and should not leak into this first PR.
