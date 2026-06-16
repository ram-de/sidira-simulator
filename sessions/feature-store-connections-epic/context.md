---
type: session
domain: feature-store-connections-epic
status: complete
started: 2026-06-16
owner: ram-de
---

# Saved feature-store connections — full epic (reuse → delete → health → combobox)

What began as a one-line bug ("why can't we save database connections? I re-enter
everything every time") became a four-PR redesign of the persona-build wizard's
Connect step, driven by a two-designer review (Claude + codex) of the live UI.
All four shipped, merged, deployed, and verified live in one autonomous session.

## The arc

1. **#304 — reuse-by-id** (PR #305, `4a74587`, frontend-only, live).
   Root cause of the original complaint: connections WERE persisted server-side
   (prod Postgres, migration 011, encrypted `password_enc`), but the wizard never
   surfaced them — `listFeatureStores()` was defined and never called, so the form
   started blank every visit. Fix: list saved connections on mount and reuse one
   **by id** — because the build references `connection_id` and test/preview/build
   all run off the server-stored credential, selecting a saved connection reaches
   BUILD with **zero password re-entry**. Fingerprint split (cred vs source) makes
   it robust.

2. **Two-designer review** of the live picker. Claude + codex (independent senior-
   designer critiques) agreed on five issues, the headline being an **identity
   collision**: multiple cards all titled `prod-analytics`, distinguishable only by
   a subtle role/casing detail in a mono subline, with no way to delete dead/dupe
   connections. "It isn't a picker yet" (codex).

3. **#327 — delete + disambiguation + register + unique names** (PR #330,
   `6328f2b4a`, BACKEND+frontend, redeployed + verified).
   - Canonical-identity title (`name · DB.SCHEMA · WAREHOUSE · ROLE`) + `account ·
     user · id8` subline + duplicate designators (`name 01/02`).
   - New `DELETE /feature-stores/{id}` (customer-scoped: foreign/unknown id → 404,
     non-leak) + repo `delete` on both repos + frontend inline-confirm delete.
   - Collapse-on-select (compact "Using saved connection" summary, not the full
     form). Register density (rows, not cards).
   - App-level **unique connection names** per customer (409, no migration).

4. **#328 — per-connection health / last-tested status** (PR #333, `de75a06`,
   BACKEND+migration 014, redeployed WITH `SIDIRA_AUTO_MIGRATE=1` then reset to 0,
   verified). Migration 014 adds `last_tested_at/last_test_status/last_error_kind/
   last_error_message` (nullable → existing rows read UNTESTED). `POST /{id}/test`
   records the outcome (customer-scoped, best-effort so a DB hiccup can't mask the
   connectivity verdict); GET returns the fields; rows show `OK · TESTED JUN 15` /
   `FAILED · AUTH` / `UNTESTED` in honest text (no color/dots). Per-row TEST
   refreshes status in place. This is what finally distinguishes two otherwise-
   identical `ACCOUNTADMIN` rows — by whether they actually work.

5. **#332 — collapse into a custom searchable combobox** (PR #335, `aa1e79b38`,
   frontend-only, Amplify). User pushed: even 6 rows inline clutter the step. So
   the list no longer renders at rest — one trigger (`Choose a saved connection
   (N) ▾`) opens a CUSTOM popover (not a native `<select>`, which couldn't carry
   the two-line identity / status / delete / on-paper styling). Popover is a
   labelled listbox: height-capped + internal scroll, filter/search, MRU sort
   (`last_tested_at` desc), full keyboard a11y (Esc/arrows/outside-click). Zero
   rows at rest whether you have 4 or 40; selecting collapses to the #327 summary.

## Deploy / verification (prod, api.sidira.ai)

- Backend redeployed manually via SSM `ec2-api-deploy.sh` (instance
  `i-04b155fafcc90042b`) TWICE: #327 (no migration) and #328 (migration 014).
  Both succeeded with **no OOM** — the 2GB swap added 2026-06-16 let the full
  `docker compose build` fit on the 916MB box (each run reclaimed ~904MB cache).
- Migration verified: container log `Running upgrade 013 -> 014`; all four
  `last_*` fields live in the prod `ConnectionSummary` schema; `SIDIRA_AUTO_MIGRATE`
  reset to `0` after. Prod backend SHA `de75a06`, health ok.
- #304 and #332 are frontend-only → Amplify auto-deploys on merge.

## Out of scope / follow-ups

- **In-memory-repo data-loss** (the `InMemoryFeatureStoreConnectionRepo` loses
  rows on restart) only bites if prod ever runs without Postgres — prod IS on
  Postgres, so not active. Left unhardened.
- Connector remains Snowflake-only (#255).
- Unique-name enforcement is app-level (no DB constraint) — pre-existing duplicate
  rows from before the guard still exist and are now deletable by the user.

## Status

COMPLETE. Original bug fixed and the Connect step redesigned end-to-end: reuse
without re-entry, a disambiguated + deletable + health-aware register, collapsed
behind a scalable searchable combobox. All four PRs merged; backend live and
verified; frontend riding Amplify. See memory
[[project-feature-store-connections-epic]].
