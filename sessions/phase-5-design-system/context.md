---
type: session
domain: phase-5-design-system
status: active
started: 2026-06-02
owner: ram-de
---

# Session: phase-5-design-system — Sidira brand & design system consultation

## Goal
Lock a complete design system for Sidira (DESIGN.md as source of truth) covering aesthetic, typography, color, spacing, motion, the wordmark, and the logomark — before sidira.ai's public homepage and `app.sidira.ai` get any more visual layer added. Output: production-ready `DESIGN.md` at repo root + canonical SVG assets in `frontend/public/brand/` + `frontend/app/icon.svg` favicon.

## In Progress
- [ ] Write `DESIGN.md` to repo root, replace `frontend/app/icon.svg` + `frontend/public/brand/sidira-mark.svg`, add dual-color + lockup SVGs, update `CLAUDE.md` with design routing block, branch + PR via `github_ramde` MCP, /codex review.

## Completed
- [x] Drafted full design brief and locked memorable-thing: **"This looks like an instrument, not software."**
- [x] Ran /design-consultation through Phase 5 preview; consulted Codex + Claude subagent in parallel for outside-voice design directions.
- [x] Synthesized into a coherent system with explicit SAFE vs RISK breakdown — user approved palette, type stack, spacing, motion bet.
- [x] First-pass logo + wordmark rejected ("logo not good", wordmark "average").
- [x] Ran shotgun grid: 6 logomarks × 6 wordmarks × 5 paired lockups.
- [x] **LOCKED L2: M2 diaphragm + W4 narrow uppercase SIDIRA.**
- [x] Refined L2 lockup — true 6-blade diaphragm geometry (overlapping triangular blades around hexagonal aperture, NOT spokes-from-center), construction notes, reproduction sizes 16/32/48/96/240px, real-world contexts (favicon / nav / app icon / social avatar / business card / in-product header), animation moment (aperture-close on simulation run), clear-space rule, refuse list.
- [x] Personal-meaning exploration after user shared name etymology (Sid + Avira → Sidira; daughter loves pink/purple, son is "typical boy").
- [x] **LOCKED color architecture (option C — hybrid):** Structure = Sid (the entire ink layer, navy-leaning #0E1A2B is already "boy-coded"). Vital = Avira (rose/pink-violet, used in narrowly-scoped narrative moments). Signal = lime (brand-functional, instrument-reading state, no personal meaning).
- [x] **LOCKED:** drop the lime/rose square dots in the wordmark. SIDIRA is plain narrow uppercase, no special-glyph trickery.
- [x] **LOCKED color states for the mark:**
   1. Default everywhere (nav, favicon, app icon, social avatar, business card, screenshots): monochrome ink mark.
   2. During simulation/settle animation (in-product, live): the close cycle transitions monochrome → dual-color (3 Sid blades + 3 Avira blades) → monochrome.
   3. Founder-mode lockup (cofounder page / about-Sidira / press kit / company-anniversary hero): dual-color version as the official frozen image.

## Next Steps
1. (in progress) Branch `feat/phase-5-design-system`, write DESIGN.md, replace icon.svg, add dual-color + lockup SVGs, update CLAUDE.md, PR via github_ramde MCP.
2. /codex review the PR.
3. Address codex findings, merge.
4. After merge: bake the locked mark into the public homepage at sidira.ai and the app.sidira.ai shell so PR #133's host split picks it up.
5. Update the previously-rejected `/tmp/sidira-design-preview.html` showcase to use the new diaphragm + clean wordmark + dual-color animation (optional — DESIGN.md is the canonical source; preview is illustration only).

## Key Files
- `DESIGN.md` — TO BE CREATED at repo root (canonical source of truth)
- `CLAUDE.md` — TO BE UPDATED with "## Design System" routing block at end
- `frontend/app/icon.svg` — TO BE REPLACED (currently the legacy teal/blue split-test mark; becomes the new diaphragm favicon, 32×32 viewBox with thick stroke)
- `frontend/public/brand/sidira-mark.svg` — TO BE REPLACED with canonical monochrome diaphragm (100×100 normalized viewBox)
- `frontend/public/brand/sidira-mark-duo.svg` — TO BE CREATED (founder-mode 3+3 Sid-blue/Avira-rose blades)
- `frontend/public/brand/sidira-lockup.svg` — TO BE CREATED (horizontal: mark + SIDIRA in Söhne Schmal / Archivo Narrow fallback)
- `frontend/public/brand/sidira-lockup-duo.svg` — TO BE CREATED (horizontal dual-color)
- Legacy versioned files (`sidira-logo-v2-*`, `sidira-logo-v3-*`, etc.) — LEAVE in place as history
- `/tmp/sidira-lockup-L2.html` — refinement showcase (decision support, ephemeral)
- `/tmp/sidira-palette-personal.html` — palette exploration with Sid+Avira (decision support, ephemeral)
- `/tmp/sidira-design-preview.html` — original full design-system preview (ephemeral; aspirational target for committed showcase later)

## Key Context

### Final locked design system

**Memorable-thing:** *"This looks like an instrument, not software."*

**Aesthetic:** Industrial/Utilitarian × Editorial. 1960s research instrument rebuilt in software. Archival-paper surfaces under tungsten light.

**Palette (with personal-meaning architecture):**
- `ink` `#0E1A2B` — Structure = **Sid**. The entire ink layer (mark, wordmark, body text, rules). Already navy-leaning, no change needed.
- `paper` `#F4EFE6` — primary surface, archival-tungsten warm off-white (4% yellow shift)
- `paper-elevated` `#FAF6EE` — cards, modals
- `paper-recessed` `#EBE5D8` — inputs, code blocks
- `rule` `#D6CFC0` — hairline dividers (0.75pt)
- `signal` `#C8FF3D` (lime) — brand-functional accent. Used only on live traces, active state of one control. ≤8% of any rendered surface. Never as fill, never as background.
- `avira` `#D696C8` (pink-violet) — Vital = **Avira**. Documented secondary accent. Used in: (1) the 3 right-side blades of the founder-mode duo mark, (2) the cofounder/about page rose hairline rule, (3) the "first-ever simulation" one-time easter-egg pulse, (4) one persona color in the chart series (the "warm" archetype), (5) anniversary/launch hero brand moments. NEVER as a button fill, never as a primary CTA, never on the main app dashboard.
- `sid-blue` `#2C5577` — used ONLY in the founder-mode duo mark (the 3 left-side blades). Not a system-wide token.
- `alert` `#E84A2C`, `warn` `#D9A300` — semantic colors, unchanged.

**Typography production stack:** Söhne family (display + body + labels), Söhne Schmal Halbfett (wordmark — narrow uppercase, +60 tracking), Berkeley Mono (data + numerals + timestamps + cohort IDs), GT Sectra Fine (marketing hero ONLY — never in the app).
Preview substitutes: Geist / Archivo Narrow / JetBrains Mono / Instrument Serif.

**Spacing scale:** 2/4/8/12/16/24/32/48/64. The 12-step is load-bearing — tighter than the SaaS default, instrument-panel density.

**Radius:** 2px inputs, 4px cards, 6px modals max. No pills. No `border-radius: 9999px` anywhere.

**Motion bet:** Numbers are traces, not spans. Confidence score and paired-lift settle as 800ms lime traces with `cubic-bezier(.34, 1.1, .64, 1)`. Every other numeric stays static + tabular.

**Layout posture:** Dense, left-aligned, instrument-panel. Three persistent zones on every result page.

### The mark — L2 spec

**Geometry:** 100×100 normalized viewBox, center 50,50. Outer pivot radius 40 (6 points at angles 30/90/150/210/270/330). Inner hexagonal aperture radius 13 (6 vertices at angles 0/60/120/180/240/300 — offset 30° from outer pivots). Six identical quadrilateral blades, each defined by (outer pivot i → outer pivot i+1 → inner vertex i+1 → inner vertex i). Hairline stroke, no fill, linejoin round, stroke scales with size (6.0 at 16px viewBox → 0.7 at 240px+).

**Wordmark:** SIDIRA in Söhne Schmal Halbfett (production) or Archivo Narrow SemiBold (preview), uppercase, +60 tracking at 24px+, +80 at small sizes. Mark height = wordmark cap-height × 1.25. Mark-to-wordmark gap = mark width × 0.28. No dot embellishments.

**Color states for the mark** (the C-hybrid lockdown):
1. **Static default** (nav, favicon, app icon, social avatar, business card, screenshots): monochrome ink mark.
2. **During simulation/settle** (in-product, live): aperture-close animation transitions monochrome → dual-color (3 Sid-blue + 3 Avira-rose blades) → monochrome. CSS-only via `@keyframes`.
3. **Founder-mode frozen lockup** (cofounder page / about-Sidira / press kit / company-anniversary hero): dual-color version as static image.

**Animation principle:** 3.4s ease-in-out infinite. At 40% the mark has rotated -8° and scaled 0.86; at 60% same; bookend frames are upright + 1.0 scale. During the held frame is when the dual-color is visible. Same easing physics as the 800ms settle-trace on confidence-score.

**Reproduction floor:** 16px digital, 8mm print. Clear-space minimum = 1× blade-length on every side.

**Refuse list:** no gradient fills, no arbitrary rotation, no lowercase wordmark, no AI-shimmer effects, no purple-violet gradients anywhere, no 3-col SaaS feature grids, no pill buttons, no `border-radius: 9999px`.

### Why we landed here (1-paragraph summary for future contributors)

The mark proves the brand thesis ("this is an instrument") with iconic camera-iris geometry that has heritage in JPL/Hubble/Leica/oscilloscope reticles. The narrow uppercase wordmark is the only typographic register in the Linear/Vercel/Statsig peer lineup that doesn't sit in the "Y Combinator lowercase sans" template — it gives Sidira authority instead of approachability. The animation moment (aperture closing, dual-color appearing) enacts the design thesis literally: ink at rest, color when the instrument is reading evidence. The dual-color carries Sid + Avira meaning, scoped to two specific surfaces (in-motion + founder-mode), so the family-name story lives without ever appearing on a buyer-facing dashboard. Lime signal-accent stays the brand-functional color for live state — instrument-correct, oscilloscope-phosphor-coded, escape velocity from the cyan/violet lane every peer occupies.

## For my cofounder
Phase 5 design-system consultation closing out. **Final locked:** L2 lockup (true 6-blade diaphragm + narrow uppercase SIDIRA, no dots), hybrid color C (monochrome static default; dual-color Sid-blue + Avira-rose during simulation animation and on founder-mode lockup), all earlier-locked decisions intact (lime signal, ink/paper, Söhne+Berkeley+Sectra type stack, 4-12-16-24 spacing, 800ms settle-trace). Currently writing DESIGN.md + replacing canonical SVG assets + updating CLAUDE.md, then PR via github_ramde MCP + /codex review. The name "Sidira" comes from our kids — Sid (the ink/structure foundation) + Avira (the rose-violet vital spark) — encoded into the architecture so it's structurally there but buyer-invisible except in cofounder/about contexts. Visual proof: `/tmp/sidira-lockup-L2.html` (the locked mark + lockup) and `/tmp/sidira-palette-personal.html` (the color decision).
