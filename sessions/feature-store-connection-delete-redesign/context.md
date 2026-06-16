---
type: session
domain: feature-store-connection-delete-redesign
status: complete
started: 2026-06-16
owner: ram-de
---

# Feature-store connection: disambiguate · delete · collapse-on-select (#327)

Redesign of the persona-builder "Saved connections" picker plus a backend
delete route and an app-level unique-name guard. Builds directly on #304
(reuse-saved-connections-by-id). Closes #327.

## Base-branch note (important)

The issue was authored assuming #304 had merged to `main`. It had NOT —
`#304` lived only on `origin/fix-304-reuse-saved-feature-store-connections`
(frontend-only, 6 commits, unmerged). To redesign the *actual* #304 picker
(rather than reinvent it), this branch — cut off `origin/main` — took the
`#304` version of `frontend/app/personas/new/page.tsx` via a path-scoped
`git checkout`. The rest of that branch's divergence (which pulled in
unrelated backend conflicts on a full merge) was deliberately left out. So
this PR carries BOTH the #304 frontend (reuse-by-id) AND the #327 redesign in
one page.tsx delta.

## The two-designer critique (Claude + codex, agreed)

The live picker rendered several cards all titled `prod-analytics`,
distinguishable only by a casing wobble in one mono subline, with no way to
delete a dead/duplicate row. It read like a gallery of near-identical
credential forms, not a register you can scan.

## The five fixes

1. **Disambiguate the picker.** Each row's primary line is now a CANONICAL
   identity: `name · DATABASE.SCHEMA · WAREHOUSE · ROLE` (schema omitted when
   empty), plus a mono subline `account · user · <id-8hex>`. Duplicate names
   get a stable `NN` designator (`01`, `02`, …) in the list's own order.
   Casing/trim is normalized for the DISPLAY comparison only — stored values
   are never mutated.
2. **Delete a connection.**
   - Backend: `DELETE /feature-stores/{id}`, customer-scoped — the repo
     `delete(customer_id, connection_id)` returns False for an unknown id OR
     another tenant's id alike, and the route maps both to 404 so existence
     never leaks across customers. 204 on a successful owned delete. Added to
     BOTH `InMemoryFeatureStoreConnectionRepo` and
     `PostgresFeatureStoreConnectionRepo` (kept in lockstep) + the Protocol.
   - Frontend: `deleteFeatureStore(id)` + a new `apiDelete` helper. A quiet
     per-row ink-hairline Delete text button (no red fill, no trash icon, no
     emoji — §10) opens an INLINE honest-text confirm stating exact scope
     ("Existing persona builds keep their records; future builds can't use
     this credential."). On success the row drops from the list, and if it was
     the selected connection the selection clears back to the blank form.
3. **Collapse-on-select.** A selected saved connection no longer renders the
   full prefilled credential form. It collapses to a compact "Using saved
   connection" record (canonical identity + account/user/db/warehouse/role +
   "Use different connection" and "Edit as new"). The full Snowflake form
   renders ONLY when creating new or editing-as-new. The #304 reuse-by-id /
   credential-fingerprint behavior is intact (selecting still pins
   `connFingerprint` so Test reuses `connection.id` with NO password).
4. **Register, not gallery.** Tall cards → dense paper rows (~2 lines),
   0.75px hairline rules top+between, mono metadata, radius ≤4, a single
   ink-hairline selected state (2px ink left edge + recessed paper) — no
   color-coded background.
5. **Unique connection names (per customer).** Backend POST `/feature-stores`
   rejects a name that already exists for the customer (case-insensitive,
   trimmed) with a clean 409 — APP-LEVEL via a `name_exists` repo query, NO DB
   unique constraint, so **NO Alembic migration**. The 409 surfaces in the
   form's existing test-error banner (the create call runs through `handleTest`
   → `apiErrorParts`), and the credentials hint now states names are unique
   per workspace.

## NO migration

Unique-name enforcement is app-level only. Health/status is the separate
ticket #328 — out of scope here.

## How verified

- Frontend: `cd frontend && npm ci && npm run build` (runs tsc) — GREEN, all
  13 routes generated, `/personas/new` 13.7 kB.
- Backend (shared `.venv` python; the worktree has no venv but the editable
  install resolves to the worktree tree):
  - `python -m pytest tests/test_feature_stores_api.py tests/test_repositories.py -q`
    → 37 passed.
  - New tests cover delete (own 204→gone, unknown 404, cross-customer 404 via
    `app.dependency_overrides`) + duplicate-name 409 (case-insensitive/trimmed)
    + distinct-names-both-succeed.
  - `ruff check` on the two touched backend files + the test → All checks
    passed.

## Touches backend → manual redeploy

This PR adds a route (`DELETE /feature-stores/{id}`) and a POST guard
(unique-name 409) under `backend/`. api.sidira.ai is manual-deploy, so after
merge the backend must be redeployed (no migration — `SIDIRA_AUTO_MIGRATE`
unaffected).
