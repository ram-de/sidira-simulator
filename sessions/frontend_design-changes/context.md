---
type: session
domain: frontend_design-changes
status: closed
started: 2026-06-02
closed: 2026-06-02
owner: ram-de
---

# Session: frontend_design-changes — apply DESIGN.md to the public site

## Goal
Restyle the public homepage (rendered on the `sidira.ai` host) to the locked design system in `DESIGN.md`. Scope is the public site ONLY. Not in scope: `app.sidira.ai` shell (deferred), `/about` page (part of #135), in-product simulation-run animation (#136), legacy brand cleanup (#137).

## In Progress
— session complete —

## Completed
- [x] Audited current public-site rendering — no Tailwind (inline styles throughout), `system-ui` was the body font (DESIGN.md §10 violation), three multi-column grids on the public page, locked regression-test strings noted.
- [x] Wired four production fonts via `next/font/google` in `app/layout.tsx`: Hanken Grotesk (Söhne stand-in — Next 14.2 predates Geist), Archivo Narrow, Instrument Serif, JetBrains Mono. Exposed as CSS variables `--font-sans` / `--font-narrow` / `--font-serif` / `--font-mono`. Body font flipped from `system-ui` to `var(--font-sans)`. Body bg/color flipped to ink-on-paper.
- [x] Rewrote `PublicCompanyHome` in `app/page.tsx`: inline `SidiraLockup` SVG component, editorial italic hero ("Validate product bets before you build."), Hanken Grotesk body, ink/paper CTAs (4px radius, no gradients), hairline-separated 3-step section with monumental mono numerals (no colored icon circles), mono footer. `ProductHome` untouched.
- [x] Updated DESIGN.md §5.1 preview-fallback font: `Geist 600` → `Hanken Grotesk 600` to reflect actual shipped stand-in.
- [x] Stripped `Helvetica Neue Condensed` from FONT_NARROW chain and from `sidira-lockup.svg` / `sidira-lockup-duo.svg` per DESIGN.md §10 refuse list (codex P2 fix).
- [x] Added scoped `<style>` block + classNames on multi-column grids so phone-width viewports collapse to a single column (codex P2 fix). `flexWrap: 'wrap'` added to the top header.
- [x] All regression tests passing: `pytest backend/tests/test_deploy_config.py` 12 passed (PR #133 host-split + public-copy + temp-Basic-Auth invariants preserved). `npm run typecheck` + `npm run build` clean.
- [x] Codex review: 2 rounds, 2 P2s flagged + fixed, R2 clean.
- [x] PR #138 squash-merged to `main` as commit `24eb992`.

## Key Files
- `frontend/lib/site-hosts.ts` — host detection (public vs app)
- `frontend/middleware.ts` — host routing + temp Basic Auth
- `frontend/app/page.tsx` — homepage (renders public OR product content based on host)
- `frontend/components/TopNav.tsx` — nav (lockup goes here)
- `frontend/app/layout.tsx` — root layout, fonts wire in here
- `frontend/tailwind.config.ts` (or `.js`) — design tokens land here
- `frontend/public/brand/sidira-lockup.svg` — primary horizontal lockup (already shipped in #134)
- `DESIGN.md` — source of truth, do not violate §10 refuse list

## Key Context

### Locked design system to apply
See `DESIGN.md` at repo root (merged in PR #134). Quick reference for this session:

**Palette tokens to wire (DESIGN.md §4):**
- `--ink: #0E1A2B` · `--ink-muted: #4A5668`
- `--paper: #F4EFE6` · `--paper-elevated: #FAF6EE` · `--paper-recessed: #EBE5D8`
- `--rule: #D6CFC0` (0.75pt hairline)
- `--signal: #C8FF3D` (lime — ≤8% surface, never as fill)
- `--avira: #D696C8` (scoped — NOT on public homepage at this time; reserved for /about page)
- `--alert: #E84A2C` · `--warn: #D9A300`

**Typography stack (DESIGN.md §5):**
- Wordmark/narrow display: Archivo Narrow SemiBold (Söhne Schmal stand-in), uppercase, +60 tracking
- Display + body: Geist (Söhne stand-in)
- Data/numerals: JetBrains Mono (Berkeley Mono stand-in)
- Marketing hero editorial: Instrument Serif Italic (GT Sectra Fine stand-in) — 1–2 lines per page max

**Spacing (§6):** 2/4/8/12/16/24/32/48/64 — the 12 step is load-bearing.
**Radius (§7.1):** 2px inputs, 4px cards, 6px modals max. No pills.
**Rules (§7.2):** 0.75pt hairlines, color `--rule`, at zone boundaries only.

**Refuse list (§10) — must not ship:**
- Purple/violet gradients
- 3-col "Built for X / Designed for Y / Trusted by Z" feature grids with icon circles
- Centered marketing-style hero blocks (no — wait, this only applies INSIDE the app; the public hero CAN be the editorial moment)
- Gradient CTA buttons
- `border-radius: 9999px` pills
- Lowercase wordmark
- `system-ui`/Inter/Roboto/Helvetica/Open Sans/Lato/Montserrat/Poppins as production fonts
- "Made by humans" / "Powered by AI" footer badges
- Stock photo / abstract blobs / mesh patterns / AI shimmer

### Out of scope (deferred, see linked issues)
- `app.sidira.ai` shell restyle — issue #135 phase 2
- `/about` page with founder-mode dual-color lockup — issue #135 phase 3
- In-product aperture-close animation on the result page — issue #136
- Legacy brand-file cleanup — issue #137

### Production constraints
- The `sidira.ai` host currently sits behind Amplify global access control (temporary) until that's flipped off per the phase-5-company-site session. This redesign work can land on `main` without that flip; the visual change shows up once Amplify access control is disabled.
- Same-origin proxy auth (`SIDIRA_WEB_PROXY_BASIC_AUTH`) still gates internal API calls per the phase-5-auth-hardening work — should not affect the static public homepage.

## For my cofounder
Public homepage redesign shipped via PR #138 (squash `24eb992`). DESIGN.md system applied to the `sidira.ai`-host page: lockup, ink/paper palette, Hanken Grotesk + Instrument Serif + JetBrains Mono via `next/font/google`, hairline-separated workflow rows, no colored circles, no gradients, no pills. Responsive collapse below 768px. App shell, /about, and the in-product aperture-close animation remain on issues #135 / #136. Once the Amplify global access control flip on the `phase-5-company-site` session lands, the new public homepage is what visitors to `https://sidira.ai` will see.
