---
type: session
domain: sidira-dojo-living-content-pwa
status: closed
started: 2026-06-15
closed: 2026-06-16
owner: ram-de
---

# Session: sidira-dojo-living-content-pwa — persistence, living content, exam-bank versioning, installable iPhone PWA

> ⚠️ Cross-repo session. All code for this work lives in the SEPARATE repo
> `~/Projects/sidira-dojo` (private GitHub `ram-de/sidira-dojo`, HEAD `1df25eb`),
> NOT in `sidira-simulator`. This session file is stored here only to keep the
> session log in one place; the durable KB is [[project-sidira-dojo]] in memory
> plus the dojo repo itself. The dojo is NOT in sidira-simulator's GitNexus index.

## Goal
Harden the Sidira Dojo (founder training app vs Kohavi-class buyers) and make it
usable day-to-day: prove progress survives restarts, make lesson + exam content
"living" (edits invalidate prior completion/mastery and prompt a redo), and make
it installable on the founder's iPhone with no App Store.

## In Progress
(none)

## Completed
- [x] **Persistence verified.** Two-boot test on an isolated DB proved all state
      (lessons, exam attempts, mastery, seen-items) survives a full server
      stop/start — it's on-disk SQLite (`dojo.db`); user re-logs in and continues.
- [x] **Living lesson content.** Each lesson carries a content hash
      (`content.js:lessonHash`, sha256 of stable-stringified content), stored in
      `lesson_progress.content_hash` at completion. A completion is valid only
      while the hash matches; editing a lesson's JSON flips it to "not done" with
      an "updated · redo" prompt across lesson/module/dashboard/overview.
      `reconcileLessonHashes()` backfills NULL legacy rows at boot so rollout
      doesn't reset existing users. Verified end-to-end (edit m1.json → reload →
      invalidated → re-complete clears it → git restore).
- [x] **Exam-bank versioning.** Each module's bank gets a content hash
      (`computeBankHash` over item id/conceptId/difficulty + `generate.toString()`),
      stamped per attempt in `exam_attempts.bank_hash`. Editing questions stops
      old attempts counting toward aced/best (`evaluateModuleExam`), flips
      `examUpdated`, zeros module mastery for display, and hard-resets mastery
      (`resetModuleMastery`) on the next retake-start. Verified end-to-end (bank
      hash provably changes `11ad3607`→`3e5a8bde`; best→null, examUpdated→true,
      retake clears it). Free-text DEFENSE bank not yet folded into the hash.
- [x] **Installable iPhone PWA (no App Store).** `public/manifest.webmanifest`,
      apple-touch-icon PNG (generated from `favicon.svg` via `qlmanage`+`sips`),
      apple-mobile-web-app meta tags in `index.html`, `.topbar` safe-area padding.
      Server binds `0.0.0.0` and prints the LAN URL on boot; `npm run phone`
      builds + serves the single-process app on :3001. Dev server also LAN-exposed
      (`vite.config.ts` host:true). Install: iPhone Safari → `http://<mac-ip>:5174`
      (or :3001) → Share → Add to Home Screen. Cookie is sameSite:lax, no Secure
      flag, so plain-http LAN works.
- [x] **Decided AGAINST native.** Capacitor would still need the backend running
      (Node/SQLite/Groq can't run in-app); free Apple ID = 7-day expiry; Mac has no
      full Xcode/CocoaPods. PWA gives ~the same feel with none of the friction.
- [x] **Backed up off-machine.** Pushed dojo to private GitHub
      `ram-de/sidira-dojo` (one commit `1df25eb`). Verified `.env` (live Groq key)
      and `dojo.db` are gitignored / not tracked; no `gsk_` in any tracked file.
- [x] Memory [[project-sidira-dojo]] + MEMORY.md index updated to current state.

## Next Steps
— session complete. Open follow-ups (not started):
- Fold the curated free-text DEFENSE bank (`content/freetext/m*.js`) into the
  bank hash so editing scenarios also invalidates.
- Optional: tunnel (cloudflared) or cloud deploy so the PWA works off home Wi-Fi.
- Optional: run `npx gitnexus analyze` inside `~/Projects/sidira-dojo` to give the
  dojo its own code-intelligence index.
- Rotate the Groq key (exposed in chat transcript) in the Groq console; update both
  `~/Projects/sidira-dojo/.env` and product `backend/.env`.

## Key Files (all in ~/Projects/sidira-dojo)
- `server/content.js` — lessonHash / computeBankHash / evaluateModuleCompletion /
  evaluateModuleExam / reconcileLessonHashes / resetModuleMastery
- `server/db.js` — addColumnIfMissing migrations (content_hash, bank_hash)
- `server/schema.sql` — content_hash on lesson_progress, bank_hash on exam_attempts
- `server/exam/sampler.js` — stamps bank_hash per attempt
- `server/routes/{content,progress,exam}.js` — staleLessons / examUpdated / mastery reset
- `server/index.js` — 0.0.0.0 bind + LAN URL banner
- `index.html`, `vite.config.ts`, `public/manifest.webmanifest`, `public/*.png`,
  `src/index.css` (safe-area), `src/pages/{Dashboard,Module}.tsx`, `src/lib/api.ts`
- `package.json` — `npm run phone`

## Key Context
**Why content-hash invalidation, not a manual "mark stale" flag:** the founder
wants to edit content via Claude Code and have completion/mastery reset
automatically. Hashing the actual content means any real edit invalidates with
zero extra bookkeeping; the boot-time backfill is the one-time guard so shipping
the feature doesn't punish prior completions.

**Why read-time comparison for lessons + exams:** completion/aced is derived by
comparing stored-hash vs current-hash at request time (no mutation), so the
dashboard shows "redo/retake" the instant content changes. Mastery is the one
stored EWMA that can't be recomputed at read time, so it's shown as 0 when stale
and physically reset on retake-start for a clean slate.

**Why PWA over native:** the backend (auth, SQLite, exam engine, Groq grader) is
Node and can't run inside an iOS app, so native (Capacitor) wouldn't make it
self-contained — it'd still phone home to the Mac. PWA "Add to Home Screen" gives
the full-screen icon/standalone experience with no Xcode/Apple-ID/expiry cost.

**Persistence was an original hard requirement** ("progress saved even when
starting/stopping the server locally; I log in and continue") — already satisfied
by on-disk SQLite; this session just proved it.

## For my cofounder
The Dojo is a SEPARATE repo (`~/Projects/sidira-dojo`, private GitHub
`ram-de/sidira-dojo`). To run it on your phone: `npm run phone`, then on an iPhone
on the same Wi-Fi open the printed `http://<mac-ip>:3001` in Safari → Add to Home
Screen. Content is "living": edit a lesson's JSON or a module's exam bank and the
matching completion/mastery resets and prompts a redo on next login — the magic is
content hashing (`content.js`), with a boot-time backfill so existing progress
isn't wiped on deploy. Full design + gotchas are in memory [[project-sidira-dojo]].
