# Session: brand-dualcolor (ticket #35)

## Goal
Founder-authorized brand-system override: make the dual-color "founder-mode"
aperture mark the STANDARD mark EVERYWHERE — in-product nav and dashboard
included — deliberately superseding DESIGN.md §1.3's prior "monotone
in-product / dual-color brand-surfaces-only / never resting in nav-or-dashboard"
rule. ONE lockstep PR (doc + code together). Do NOT merge / deploy.

## Status: DONE — PR opened vs main (ram-de). Awaiting codex review + merge.

## Changes

### DESIGN.md (v0.3.x → v0.4, 2026-06-26 changelog row)
- §1.3 rewritten: three color states → TWO (static dual-color default +
  transient animation). Dual-color is the everywhere-standard; "never resting
  in nav/dashboard" lifted. Added RATIONALE (visual consistency over the
  brand-vs-product split). Aperture-close animation note kept valid.
- §3 lockup table: primary horizontal now duo (`sidira-lockup-duo.svg`),
  everywhere; mono lockup/mark demoted to fallback-only.
- §1.5 + §11 asset tables: duo = standard, mono = legacy fallback.
- §4.4: forbidden-`avira` list scoped to STANDALONE accents only — the
  resting duo MARK is now sanctioned in nav/dashboard.
- §9.2 keyframes: resting endpoints retfrom "monochrome ink" to "resting
  dual-color"; aperture now focuses (rotate+scale) on the always-dual mark,
  no mono↔duo color crossing. Reduced-motion = static dual-color.

### CLAUDE.md (Design System section)
- Replaced the "dual-color reserved for brand-mode surfaces … never resting
  in the nav or dashboard" paragraph with "dual-color is the standard mark on
  every surface, in-product nav + dashboard included." Matches §1.3.

### Code (in-product nav/dashboard logos → dual-color, REUSE existing assets)
- frontend/components/TopNav.tsx: SidiraLockup → SidiraLockupDuo (height 28,
  light/paper ground — ink wordmark correct there).
- frontend/components/v2/AppShellV2.tsx (console rail brand): ConsoleMarkMono →
  SheetMarkDuo (size 28, dark console ground — fixed DUO_SID/DUO_AVIRA strokes,
  no currentColor dependency, renders on dark).
- frontend/components/v2/Marks.tsx: updated doc-comments (SheetMarkDuo = the
  everywhere-standard; ConsoleMarkMono = legacy fallback).

### Deliberately UNCHANGED (out of "nav/dashboard" scope)
- Public site logos: PublicTopBar (SidiraLockupDuo), PublicConsoleTopBar +
  Sheet (SheetMarkDuo), ConsoleShell marketing TopBar — already/legitimately
  duo or marketing-surface; not touched.
- AppFrame.tsx (the /v2/* MOCK shell) — left on ConsoleMarkMono per its own
  contract (mocks must not be mutated).
- Auth screens (sign-in/up, sso-callback, v2/auth) still ConsoleMarkMono —
  not "nav/dashboard"; left for a later migration, noted in Marks.tsx comment.
- DUO_SID/DUO_AVIRA tokens + brand SVGs: REUSED, not recreated.

## Verification
- `tsc --noEmit`: green (exit 0).
- `next build`: green (exit 0, "Compiled successfully").

## Constraints honored
- No emoji / icon-lib; tokens only; reused existing duo geometry.
- GitHub = ram-de. Committed + PR vs main. NOT merged, NOT deployed.
