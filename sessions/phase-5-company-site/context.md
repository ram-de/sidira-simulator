---
type: session
domain: phase-5-company-site
status: active
started: 2026-06-01
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
- [x] PR #142: app shell + /about page (DESIGN.md system, SidiraLockup, design tokens, public homepage redesign). Codex gate: PASS.
- [x] Dev ergonomics: `SIDIRA_PUBLIC_HOST=1` in `.env.local` to see public homepage at localhost. `APP_URL` const routes Sign in to `localhost:3000/simulations` in dev. "About" nav link added.
- [x] `/about` page copy: replaced kids-naming story with product/instrument angle ("Precision before commitment."). Mark architecture paragraph kept, detached from naming origin.

## Next Steps
1. Merge PR #142 (codex gate passed).
2. Issue #136: aperture-close animation (separate PR).
3. Issue #137: prune legacy brand files (separate PR).
4. When browser tooling is available, visually QA `sidira.ai` public home and `/about` on a live deploy/preview.
5. Continue Phase 5 proper with Clerk middleware and tenant resolution.

## Key Files
- `frontend/middleware.ts`
- `frontend/app/page.tsx`
- `frontend/components/TopNav.tsx`
- `docs/sidira-domain-runbook.md`
- `frontend/lib/site-hosts.ts`

## Key Context
- This is a Phase 5 entry slice, not a new roadmap phase. It creates the public/app boundary that Clerk auth will later enforce on `app.sidira.ai`.
- Public site copy should explain the problem and outcome, but not reveal the crawler/persona/simulator implementation recipe, scoring formula, artifact contract, prompts, roadmap, or customer details.
- Local HTTP redirect checks passed for `sidira.ai/simulations/new` -> `app.sidira.ai/simulations/new` and `www.sidira.ai/simulations/new` -> `sidira.ai/simulations/new`. Full page body/browser verification was blocked by local socket instability after Next dev compilation and unavailable browser/Playwright tooling in this session.
- "Access" means the temporary Basic Auth credential currently stored as `SIDIRA_WEB_PROXY_BASIC_AUTH`. Until Clerk lands, public `sidira.ai` bypasses that gate, while `app.sidira.ai` and product routes require it.

## For my cofounder
Host split is implemented before Clerk: apex/www are the public company surface; product routes remain on `app.sidira.ai`; product links on the apex redirect to the app host. `app.sidira.ai` keeps temporary Basic Auth until Clerk replaces it. This should ship as a small Phase 5 PR before the larger auth/multi-tenancy work.
