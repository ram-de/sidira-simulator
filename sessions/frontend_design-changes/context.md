---
type: session
domain: frontend_design-changes
status: active
started: 2026-06-02
owner: ram-de
---

# Session: frontend_design-changes — apply DESIGN.md to the public site

## Goal
Restyle the public homepage (rendered on the `sidira.ai` host) to the locked design system in `DESIGN.md`. Scope is the public site ONLY. Not in scope: `app.sidira.ai` shell (deferred), `/about` page (part of #135), in-product simulation-run animation (#136), legacy brand cleanup (#137).

## In Progress
- [ ] Audit the current public-site rendering path (frontend/middleware.ts, lib/site-hosts.ts, app/page.tsx, components/TopNav.tsx) to understand what renders on `sidira.ai`.

## Completed
(nothing yet)

## Next Steps
1. Read the current public-homepage code (components rendered when host = `sidira.ai` per `frontend/lib/site-hosts.ts`).
2. Add design tokens to Tailwind config — ink, paper(+elevated/recessed), rule, signal, avira, ink-muted, alert, warn, plus the 2/4/8/12/16/24/32/48/64 spacing scale.
3. Load fonts via `next/font` — Geist (sans, body+display stand-in for Söhne), Archivo Narrow (narrow uppercase stand-in for Söhne Schmal), JetBrains Mono (data stand-in for Berkeley Mono), Instrument Serif (one editorial line stand-in for GT Sectra Fine).
4. Replace any current TopNav lockup with `sidira-lockup.svg` (mark + SIDIRA narrow uppercase).
5. Restyle the public homepage hero with one editorial-serif headline + Söhne-body subheading + ink/paper palette + hairline-rule dividers. No gradient buttons, no pill radii, no icon-grid sections.
6. Verify the existing PR #133 regression tests for the public-site vs app-host content split still pass.
7. `cd frontend && npm run typecheck && npm run build` clean.
8. Branch `feat/frontend-design-public-site`, commit, PR via `github_ramde` MCP, /codex review, merge.

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
Working on applying the locked DESIGN.md system to the public homepage at `sidira.ai`. Scope is JUST the public site — not the app shell, not /about, not in-product animation. Those are issues #135/#136/#137. Building this on a feature branch `feat/frontend-design-public-site`, will PR via `github_ramde` MCP. After merge it'll be visible once Amplify global access control gets flipped per your phase-5-company-site session.
