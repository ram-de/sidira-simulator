---
type: session
domain: phase-5-company-site
status: closed
started: 2026-06-01
closed: 2026-06-06
owner: ram-de
---

# Session: phase-5-company-site -- public site and app host split

## Goal
Make `sidira.ai` / `www.sidira.ai` the public company site while keeping `app.sidira.ai` as the product app surface that Phase 5 auth will protect.

## In Progress
(nothing currently in progress)

## Completed
- [x] Created Phase 5 entry-slice session.
- [x] Classified the work as part of Phase 5, not a new roadmap phase.
- [x] Added regression tests for public-site/product-app host split and non-leaky public homepage copy.
- [x] Implemented minimal public company homepage for `sidira.ai`.
- [x] Kept the existing product home for `app.sidira.ai` and local development hosts.
- [x] Redirected product paths on `sidira.ai` to `app.sidira.ai`.
- [x] Added temporary app-host Basic Auth in Next middleware so Amplify access control can be disabled for the public apex before Clerk lands.
- [x] Verified the dummy Basic Auth value is not baked into `.next`; generated middleware keeps a runtime `process.env.SIDIRA_WEB_PROXY_BASIC_AUTH` reference.
- [x] Verification passed: new deploy/config tests, frontend typecheck, frontend production build, full backend suite, and `git diff --check`.
- [x] Fixed `/about` page: removed kids-naming backstory, removed founders section (Ram De card/bio), removed mark-architecture paragraph. New copy: "Precision before commitment." (Instrument Serif italic h1) + single paragraph explaining the product's purpose.
- [x] Extracted `SidiraLockupDuo` into shared component (`frontend/components/SidiraLockupDuo.tsx`) — dual-color mark (#2C5577 left, #D696C8 right) + SIDIRA wordmark. Used on all public/brand surfaces.
- [x] Updated public homepage nav to use `SidiraLockupDuo height={36}` (was mono at 28).
- [x] Added "About" link to public homepage nav (between Request access and Sign in).
- [x] Fixed public nav link font size: `fontSize: 16, fontWeight: 500` for About and Request access.
- [x] Fixed `ProductHome` h1 ("Sidira"): added `fontFamily: FONT_NARROW, fontSize: 40, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase"` — was rendering in browser default font.
- [x] Fixed product nav tab font size: bumped from 13→16px after iterative user feedback.
- [x] Fixed dev "Sign in" redirect: `APP_URL` in dev now uses `http://127.0.0.1:3000/simulations` (not `localhost`) so the `SIDIRA_PUBLIC_HOST=1` override doesn't intercept it.
- [x] Added `SIDIRA_PUBLIC_HOST=1` dev override to `frontend/lib/site-hosts.ts` so `localhost:3000` can render the public homepage in development. Documented in `frontend/.env.local`.
- [x] Updated DESIGN.md §1.3: renamed "Founder-mode" → "Brand-mode"; extended dual-color rule to cover favicon, app icon, and all public surfaces; clarified monochrome is product-shell only.
- [x] Changed favicon (`frontend/app/icon.svg`): was ink background + paper strokes; now paper background (#F4EFE6) + duo-color strokes (Sid-blue left, Avira-rose right).
- [x] Added `frontend/public/brand/sidira-mark-duo-social.svg` — social media avatar variant with paper background and 15-unit viewBox padding for safe circular crop on LinkedIn/Twitter.
- [x] Merged PRs: #142 (app shell + about page), #143 (squash-merge fix), #144 (duo lockup public surfaces), #145 (duo favicon + social SVG).

## Next Steps
— session complete. Remaining/handed-off items:
- #136 (aperture-close animation, PR #147) and #137 (prune legacy brand files, PR #148) shipped 2026-06-06.
- Phase 5 auth (Clerk middleware + tenant resolution) continues in the `phase-5-auth` session.
- Optional manual chore (not blocking): export `sidira-mark-duo-social.svg` to a 400×400 PNG for the Twitter/X avatar.

## Key Files
- `frontend/middleware.ts`
- `frontend/app/page.tsx` — public homepage + product home shell
- `frontend/app/about/page.tsx` — /about page
- `frontend/app/icon.svg` — favicon (duo-color on paper, rx=32)
- `frontend/components/TopNav.tsx` — product nav (mono lockup)
- `frontend/components/SidiraLockupDuo.tsx` — shared duo-color lockup component
- `frontend/lib/site-hosts.ts` — host-split logic + SIDIRA_PUBLIC_HOST dev override
- `frontend/public/brand/sidira-mark-duo-social.svg` — LinkedIn/Twitter avatar (SVG, needs PNG export)
- `docs/sidira-domain-runbook.md`
- `DESIGN.md` — canonical design spec (§1.3 updated for brand-mode rule)

## Key Context
- This is a Phase 5 entry slice, not a new roadmap phase. It creates the public/app boundary that Clerk auth will later enforce on `app.sidira.ai`.
- **Duo lockup rule**: duo-color (`SidiraLockupDuo`) on all public/brand surfaces (sidira.ai, /about, favicon, social avatar). Mono (`SidiraLockup`) in the product shell (app.sidira.ai TopNav, in-app UI).
- **Dev ergonomics**: `SIDIRA_PUBLIC_HOST=1` in `.env.local` makes `localhost:3000` render the public homepage. Use `http://127.0.0.1:3000/simulations` (not localhost) to access the product shell from the same dev server — `127.0.0.1` bypasses the public-host override.
- **Squash merge gotcha**: PR #142 squash only captured 2 of 13 commits. Fixed via PR #143 which cherry-picked the correct 4 files from the worktree branch.
- Public site copy should explain the problem and outcome, but not reveal the crawler/persona/simulator implementation recipe, scoring formula, artifact contract, prompts, roadmap, or customer details.
- "Access" means the temporary Basic Auth credential currently stored as `SIDIRA_WEB_PROXY_BASIC_AUTH`. Until Clerk lands, public `sidira.ai` bypasses that gate, while `app.sidira.ai` and product routes require it.

## For my cofounder
Host split is live: `sidira.ai` is the public company surface with duo-color branding (duo lockup in nav, duo favicon, /about page with product copy). Product routes remain on `app.sidira.ai` with mono branding. Temporary Basic Auth stays until Clerk replaces it. Issues #136 (animation) and #137 (brand file pruning) are next up.
