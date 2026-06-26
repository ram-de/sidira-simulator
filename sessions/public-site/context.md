# Session — public marketing site (sidira.ai)

**Branch:** `feat/public-site-content` · worktree `agent-af681cba97c32b670`
**GitHub:** ram-de · PR vs `main`, do not merge / do not deploy.

## Two tasks

### Task 1 — dual-color logo on sanctioned brand surfaces only
**Finding: already correctly implemented on `main`. No change needed.**
- Public site headers (`/`, `/about`): `SheetMarkDuo` (`PublicConsoleTopBar`) /
  `SidiraLockupDuo` (`PublicTopBar`) → dual-color (DUO_SID + DUO_AVIRA). ✓
- Favicon / app icon (`frontend/app/icon.svg`): duo mark on paper ground. ✓
- Product nav stays monochrome: `TopNav` → `SidiraLockup` (currentColor),
  `AppShellV2` → `ConsoleMarkMono`. ✓ — correctly NOT touched.
- All duo components consume scoped `DUO_SID`/`DUO_AVIRA` from `lib/design.ts`
  (DESIGN.md §4.4), geometry lifted from the canonical brand SVGs. Reused, not
  recreated.

### Task 2 — fill the bare public marketing site with truthful content
Public host = `sidira.ai` / `www.sidira.ai` (`lib/site-hosts.ts`). `/` →
`PublicCompanyHome`; `/about`. (`/product` is a PRODUCT_PATH_PREFIX → redirects
to app host, so NOT a public marketing surface — left alone.)

Surface language: the shipped design-system-v2 "Reading Console" dark theme
(`styles/v2-theme.css`) the public pages already use. Tokens: `--text-hi/-mut`,
`--console-*`, `--signal` (#48efca), `--v2-font-mono`. Marketing rhythm 96/112
(§6). No glass component misuse, no icon library, no emoji.

## Hard content rules (brief)
Do NOT invent metrics/customers/testimonials/logos/team bios/features. Do NOT
overclaim — NOT proven on counter-intuitive A/B winners (at chance). Honesty IS
the brand. Minimal founder detail (one line max). Leave out anything ungrounded.

## Grounded sources
- `frontend/app/research/accuracy/page.tsx` — honest accuracy report (mixed
  standing, pre-registration, replication, nulls, "directional hypothesis
  generator + weakness surfacer, not a calibrated predictor").
- `README.md` — pre-experiment hypothesis validation via behavioral simulation;
  agent memory (conversable agents post-sim); 3-repo system.
- `ROADMAP.md` — private alpha; A/B mode shipped; not-yet-real items; calibration
  on roadmap not claimed.
- `research/twin-council/WHITE-PAPER.md` — "the live randomized experiment stays
  the ground truth"; rank candidate experiments; "uncalibrated" honesty gate.
- Outreach kit — canonical positioning: "AI audience simulation to pre-screen
  which experiment ideas are worth testing … upstream of A/B testing, not a
  replacement; validating honestly before claiming anything."

## Test constraints (must not break — backend/tests/test_deploy_config.py)
- `page.tsx` must keep: `isPublicSiteHost(host)`, `PublicCompanyHome`,
  literal `"Validate product bets before you build"`, `"Request access"`,
  `"Sign in"`. Must NOT contain: `reverse-Figma`, `reverse_prd`,
  `paired sampling`, `confidence interval`, `scoring formula`.
- (`ProductHome` assertion at line 201 is already red on main — pre-existing,
  page uses redirect("/simulations"); not my regression. Keep host-split block
  byte-stable.)

## DESIGN.md lockstep
New marketing vocabulary → same-PR DESIGN.md update. Watching for: any new copy
register or section pattern that needs codifying.

## Status
- [x] Read DESIGN.md, sources, host logic, tests
- [x] Task 1 audit: dual-color logo already correct on all sanctioned surfaces;
      product nav monochrome. No change needed (would be gold-plating).
- [x] Rewrite `/` content (screen-don't-replace positioning; kept required test
      strings; added "Where it stands" honest is/is-not/discipline section)
- [x] Fill `/about` (what it does · honest claim · how we measure · who's building)
- [x] DESIGN.md lockstep: no design vocabulary added — reused §7.4 marketing
      editorial register + existing section/token patterns. No DESIGN.md edit
      needed (copy is not design-system vocabulary). No glass, no raw hex.
- [x] tsc --noEmit green · next build green (/ and /about compile)
- [x] Files changed: only frontend/app/page.tsx + frontend/app/about/page.tsx
- [ ] PR opened (do not merge / do not deploy)
