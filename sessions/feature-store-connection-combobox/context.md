---
type: session
domain: feature-store-connection-combobox
status: complete
started: 2026-06-16
owner: ram-de
---

# Saved-connection picker → custom searchable combobox (#332)

Final piece of the saved-feature-store-connections epic
(#304 → #327 → #328 → **#332**). Frontend only.

## Problem

The Persona Builder's Connect step (`frontend/app/personas/new/page.tsx`,
`StepConnect`) rendered the saved-connections **register inline at rest** —
every saved feature-store connection as a dense paper row. That reads fine at
3 rows; at 6, 20, or 40 it dominates the step. A connection picker is
*management surface*, not the step's primary content.

## What shipped

At REST the step now shows **ONE control**, not a list:

- A trigger `Choose a saved connection (N) ▾` (N = total saved count), or the
  selected connection's identity + count once one is pinned.
- **Zero** connection rows visible at rest, whether there are 4 or 40.
- The existing secondary path — `+ Enter a different connection` and the full
  credential form — is untouched.

Clicking the trigger opens a **custom popover** (`ConnectionPicker`) containing
the existing register rows, now with:

1. **Height cap + internal scroll** — `maxHeight: 268` + `overflow-y: auto` on
   the listbox (~4 rows), so it never grows unbounded.
2. **Sort** — `sortConnsForPicker`: `last_tested_at` desc, NULLs last, stable
   fallback by name then id. The most-recently-tested/used connection is on top.
3. **Filter** — a substring `<input>` at the top of the popover, narrowing by
   name / account / user / database / schema / warehouse / role
   (case-insensitive, `connMatchesFilter`). Always present.
4. Selecting a row → closes the popover and collapses to the **#327 "Using
   saved connection" summary** (reuse-by-id, no password). Unchanged behavior.
5. **DELETE** (inline honest-text confirm) and per-row **TEST** live INSIDE the
   open popover per row — the exact #327/#328 row, just relocated.

## Custom combobox, NOT a native `<select>` — the decision

A native `<select>`/`<option>` can carry **none** of what this list needs: the
two-line canonical identity (`name · DB.SCHEMA · WH · ROLE` + `account · user ·
id8`), the #328 health line (`OK · TESTED JUN 15` / `FAILED · AUTH` /
`UNTESTED`), the per-row TEST and DELETE affordances, or on-paper hairline
styling. DESIGN.md §10 also rules out the native-select chrome here. So the
trigger is a real `<button>` and the panel is a hand-built popover, styled on
paper with the existing `SavedConnectionRow` vocabulary.

## a11y model

Note: an early draft used `role="listbox"`/`role="option"`, but the rows carry
their own Test/Delete buttons and can morph into a confirm `alertdialog`, which
a strict listbox may not contain (codex flagged it). The shipped model is a
non-modal **dialog** instead:

- Trigger: `<button>` with `aria-haspopup="dialog"`, `aria-expanded`,
  `aria-controls` (when open). Enter / Space / ArrowDown open it.
- Panel: `role="dialog"` + `aria-label`; the row list is `role="group"`; the
  pinned row carries `aria-current`.
- On open, focus lands on the **filter input** (typing-first). ArrowDown steps
  into the first row.
- Rows: each row's select button takes a **roving tabindex** (active = 0, rest
  = -1). ArrowUp/ArrowDown move the active index; an effect pulls real DOM focus
  to match. ArrowUp from the first row returns to the filter input.
- **Enter** on a focused row selects it via the button's own `onClick`
  (`handleSelectSaved` → collapse) — not intercepted.
- **Esc** closes and returns focus to the trigger — handled at the **panel
  level** (`onPanelKeyDown`), so it fires from ANY focused control inside the
  popover (filter, a row, or a row's Test/Delete/confirm button). **Outside
  click** closes without yanking focus back (the user clicked elsewhere on
  purpose).
- **Focus after select**: selecting collapses the picker, unmounting the
  trigger — so we do NOT refocus it (that would drop focus to `<body>`). The
  parent passes a one-shot `justPickedRef` signal to the collapsed "Using saved
  connection" summary, which focuses its heading on mount only when the collapse
  followed a picker selection (never on a cold load with a pre-selected
  connection).
- The caret is a text `▾`/`▴` glyph (`aria-hidden`) — no imported icon set, no
  emoji. Focus-visible rides the browser default ink outline; no color-coded
  state (§4.3/§10). Empty-filter → honest `No connections match`; loading reuses
  the existing `LOADING SAVED CONNECTIONS…` line. Zero saved connections → the
  trigger isn't rendered; the step falls straight to the credentials form.

## Preserved, un-regressed

- **#304 reuse-by-id** — selecting still pins the credential fingerprint;
  `handleSelectSaved`/`handleTest` untouched, so Test reuses `connection.id`
  with no password.
- **#327** delete + inline confirm + unique names + collapse-on-select summary
  — same `SavedConnectionRow` / `SavedConnectionSummary`, only the *container*
  changed (inline list → triggered popover).
- **#328** per-row status line + per-row TEST refresh-in-place — same
  `handleTestRow`, `connectionHealthLine`, row props; relocated into the popover.

## Scope / deploy

Frontend only — no `backend/`, no migration, no new API calls (reuses
`listFeatureStores` / `deleteFeatureStore` / `testFeatureStore`). **Amplify
auto-deploys on merge to `main`; NO backend redeploy.**

Completes epic #304 → #327 → #328 → #332.
