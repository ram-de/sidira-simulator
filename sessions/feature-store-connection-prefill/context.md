---
type: session
domain: feature-store-connection-prefill
status: complete
started: 2026-06-15
owner: ram-de
---

# Persona-build wizard — reuse saved feature-store connections (#304)

## The bug (#304)

The persona-build wizard (`frontend/app/personas/new/page.tsx`, Step 1 ·
Connect) made the user re-enter ALL warehouse/feature-store connection details
— including the password — every single time. Connections were already
persisted server-side (prod Postgres; migration 011 `feature_store_connections`;
password stored encrypted as `password_enc`, never returned by GET), but the
frontend never surfaced them. The wizard always started from `emptyConnForm()`.

## Root cause

`listFeatureStores()` (`frontend/lib/api.ts:577`) was defined but **never
called**. There was no UI affordance to pick a saved connection, so a returning
PM had no choice but to re-type credentials and password.

## The insight that makes the fix clean (reuse by id)

The build request sends `connection_id: connection.id` (page.tsx
`handleStartBuild`). `testFeatureStore(id)`, `previewFeatureStore(id, body)`,
and `suggestMapping(id, cols)` all operate on a **saved connection id** — the
server uses the stored encrypted password for each. They do NOT need plaintext.
`createFeatureStore(req)` is the ONLY call that needs the password, and it's
only needed to MINT a NEW connection.

Therefore: if the user SELECTS an existing saved connection, set the
`connection` state (a `ConnectionSummary`) DIRECTLY to that saved row — skip
`createFeatureStore` entirely — and test/preview/mapping/build all work off
`connection.id` with **zero password re-entry**.

## The fix (frontend only)

All in `frontend/app/personas/new/page.tsx`:

1. **Load on mount** — a `useEffect` calls `listFeatureStores()` once. New state
   `savedConns` + `connsPhase` ("loading" | "ready" | "error"). A failed fetch
   sets `connsPhase = "error"`, which simply hides the saved-list section and
   leaves the blank form usable — the wizard never blocks.

2. **Saved-connections section** — rendered in `StepConnect` ABOVE the
   credentials form (a "Saved connections" `section`), each row a selectable
   `<button>` showing name · account · warehouse · database(.schema) · role,
   plus a `kind` Chip and a SELECTED Chip on the active row. Selection emphasis
   is an ink hairline, no color state (DESIGN.md §4.3). Empty list / loading /
   error are honest text, no spinners (§8.6).

3. **`handleSelectSaved(c)`** — the load-bearing part. It:
   - sets `connection` to the saved `ConnectionSummary` directly (no
     `createFeatureStore`, no password),
   - prefills the visible form (`name/account/user/warehouse/role/database/
     schema`; password left blank — it's never returned),
   - sets `connFingerprint` to `credFingerprint` of THAT password-blank form
     against the current source mode/table/sql. Because the live `fingerprint`
     now MATCHES `connFingerprint`, `handleTest` reuses `connection.id` (runs
     `testFeatureStore(id)` against the stored credential) instead of
     re-minting. Continue still gates on a real 204 from Test, so the user
     confirms the saved row connects before proceeding.
   - resets any prior profiled mapping (columns/suggestion/mapping/mapPhase),
     mirroring what `handleTest` does after a fresh mint, since a different
     connection may have different columns.

4. **`handleNewConnection()`** — "+ Enter a different connection" returns to the
   blank `emptyConnForm()` path (clears `connection`, both fingerprints, mapping
   state), preserving the original enter-everything behavior.

If the user edits a credential field after selecting a saved row, the
fingerprint diverges and the existing mint-on-test path takes back over (a
password would then be required again — acceptable, matches existing behavior).

## Reuse path reaches BUILD with zero password re-entry

Yes. Select saved row → Test runs `testFeatureStore(connection.id)` (stored
credential, no mint) → Map previews/suggests off the id → Build sends
`connection_id` and the server uses `password_enc`. No plaintext password is
needed anywhere on the reuse path.

## Verification

- `npm ci` in `frontend/` (worktree had no node_modules).
- `npm run typecheck` (`tsc --noEmit`) → clean, no errors.
- `npm run build` (`next build`) → green; `/personas/new` compiles (12.4 kB).
- `npm run lint` is NOT a configured gate — it drops into Next.js's interactive
  ESLint setup prompt (no eslintrc in repo); typecheck + build are the gates.

## Scope / deploy

Frontend only — no `backend/` touched, no new API endpoints (`listFeatureStores`
already existed). Amplify auto-deploys the frontend on merge to `main`; **no
backend redeploy needed**.
