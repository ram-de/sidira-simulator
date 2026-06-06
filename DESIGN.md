# Sidira — Design System

**This file is the source of truth.** Read it before making any visual, UI, or
brand decision. If something here is wrong or out of date, update this file
*and* the assets it references in the same change.

The memorable thing Sidira is trying to be: *"This looks like an instrument, not
software."*

The name comes from the founder's kids — **Sid + Avira → Sidira**. That story
is encoded into the color architecture (see §4) but kept invisible on
buyer-facing surfaces.

---

## 1. The mark

A six-blade camera diaphragm — six overlapping triangular blades arranged
around a hexagonal aperture. JPL / Hubble / Leica / oscilloscope-reticle
heritage. Calibrated, measured, instrument-coded.

### 1.1 Geometry

| Property | Value |
| --- | --- |
| viewBox | `0 0 100 100` |
| Center | `50, 50` |
| Outer pivot radius | `40` |
| Inner aperture radius | `13` |
| Angle convention | clockwise from `+x` in SVG viewBox coordinates (y-down). `angle 0°` is the right horizontal; `angle 90°` is straight down. |
| Outer pivot angles | `30°, 90°, 150°, 210°, 270°, 330°` |
| Inner vertex angles | `30°, 90°, 150°, 210°, 270°, 330°` (same as outer pivots — they share angular positions, not offset) |
| Blade count | `6` (identical quadrilaterals separated by 60°) |
| Blade construction | (outer pivot i) → (outer pivot i+1) → (inner vertex i+1) → (inner vertex i). With matched angles, each blade is a clean radial wedge; its inner edge is one side of the regular hexagonal aperture. |
| Inner hexagon | regular, edge length 13. The hexagon's flat edges face left and right; the points face top and bottom. |
| Stroke | `currentColor`, no fill, `linejoin: round`, `linecap: butt` |

### 1.2 Stroke weight by render size

`sidira-mark.svg` ships with a neutral default stroke (`1.1` in viewBox units,
sized for ~96 px output). When consuming it at other sizes, **override
`stroke-width` at the usage site** — SVG scales stroke linearly with output
size, so a fixed default would be too thin at 16 px and too heavy at 240 px+.

| Render size | `stroke-width` (in the `viewBox 0 0 100 100` of `sidira-mark.svg`) | Used for |
| --- | --- | --- |
| 16 px | `6.0` | small favicon · inline icon |
| 32 px | `3.5` | nav bar · in-app header |
| 48 px | `2.25` | marketing nav · doc header |
| 96 px | `1.1` (default — shipped value in `sidira-mark.svg`) | marketing hero |
| 240 px + | `0.7` | print · billboard · sign |

Reproduction floor: **16 px digital, 8 mm print**.

`frontend/app/icon.svg` is a **separate self-contained asset** for the favicon
and app-icon use case (a paper-stroke mark on an ink-filled rounded-square
ground, `viewBox 0 0 144 144`). Its stroke is fixed at `3.5` in viewBox units —
calibrated to read across the 32 → 144 px size range that Next.js generates
icons at. Browsers downscaling to 16 px will produce a thinner stroke; this is
acceptable for the favicon trade-off. Do not import `icon.svg` as a reusable
mark; use `sidira-mark.svg` with the stroke override above.

### 1.3 Color states

The mark has three sanctioned color states. Anything else is wrong.

| State | When it appears | Color |
| --- | --- | --- |
| **Static default** | product nav · in-app UI · business card · screenshots · everywhere not listed below | monochrome `ink` (`#0E1A2B`) |
| **Animated (running)** | inside the product while a simulation is being computed, while a confidence trace is settling, during persona-group fan-out | cycles monochrome → dual-color → monochrome via the aperture-close animation (§9) |
| **Brand-mode (frozen)** | favicon · app icon · public site (`sidira.ai`) · `/about` · press kit · social avatar · company anniversary hero · investor decks page-one only | dual-color (3 Sid-blue blades + 3 Avira-rose blades) on paper ground (`#F4EFE6`), static |

The default is monochrome inside the product. The dual-color brand-mode is used on all public/brand surfaces and the favicon. Do not use the
dual-color version on the in-app dashboard, in the product nav, or in the product shell. Buyer-facing product UI stays monochrome.

### 1.4 Clear space

Clear space minimum equals **one blade-length** (= mark width / 4) on every
side. In horizontal lockups, the wordmark sits inside this clear space — it is
the only thing allowed there.

### 1.5 Mark assets

| File | Use |
| --- | --- |
| `frontend/public/brand/sidira-mark.svg` | canonical monochrome mark, `currentColor` stroke |
| `frontend/public/brand/sidira-mark-duo.svg` | founder-mode dual-color (Sid-blue + Avira-rose) |
| `frontend/app/icon.svg` | favicon / app-icon (duo-color mark on paper ground, `rx: 32`) |

---

## 2. The wordmark

**`SIDIRA`** — narrow uppercase, no glyph trickery, no dots, no embellishments.

| Property | Production | Preview / fallback |
| --- | --- | --- |
| Typeface | **Söhne Schmal Halbfett** (Klim Type Foundry) | Archivo Narrow SemiBold (free, Google Fonts) |
| Weight | 600 | 600 |
| Case | uppercase always | uppercase always |
| Tracking | `+60` (= `letter-spacing: 0.06em`) at 24 px and above | same |
| Tracking (small) | `+80` (= `letter-spacing: 0.08em`) at ≤ 16 px | same |
| Color | `ink` (`#0E1A2B`) default · `paper` on dark surfaces | same |

The wordmark is never lowercase, never italic, never given a dot embellishment,
never paired with a tagline inside the lockup. The lockup is mark + `SIDIRA` —
nothing else.

---

## 3. Lockups

Four sanctioned lockups. The primary horizontal is the one used by default.

| Lockup | Composition | Use | Asset |
| --- | --- | --- | --- |
| Primary horizontal | mark + `SIDIRA` left-aligned | nav · email signature · press · default everywhere | `sidira-lockup.svg` |
| Founder-mode horizontal | dual-color mark + `SIDIRA` | cofounder page · about · press kit · anniversary | `sidira-lockup-duo.svg` |
| Stacked | mark above `SIDIRA` centered | marketing footer · business card · press kit | (compose at usage site — same proportions) |
| Mark only | mark, no wordmark | app icon · favicon · social avatar · loading state | `sidira-mark.svg` · `app/icon.svg` |

### 3.1 Lockup proportions

| Property | Value |
| --- | --- |
| Mark height | wordmark cap-height × **1.25** |
| Mark-to-wordmark gap | mark width × **0.28** |
| Mark vertical alignment | cap-height baseline matched to mark optical center |

The provided `sidira-lockup.svg` and `sidira-lockup-duo.svg` files already
encode these proportions. Use them directly rather than recomposing.

---

## 4. Color

### 4.1 Architecture — three layers, three meanings

| Layer | Token | Hex | Carries |
| --- | --- | --- | --- |
| **Structure** = Sid | `ink` | `#0E1A2B` | the entire ink layer — mark, wordmark, body text, rules, structural foundation. Already navy-leaning. Sid is the thing everything else stands on. |
| **Signal** = brand-functional | `signal` | `#C8FF3D` | live state · the instrument is reading · oscilloscope-phosphor accent. No personal meaning. Used at ≤ 8% of any rendered surface, only on live traces and the active state of one control. Never as fill, never as background. |
| **Vital** = Avira | `avira` | `#D696C8` | secondary accent for narrowly-scoped narrative surfaces — see §4.4. |

### 4.2 Surface and text tokens

| Token | Hex | Use |
| --- | --- | --- |
| `paper` | `#F4EFE6` | primary surface — archival-tungsten warm off-white |
| `paper-elevated` | `#FAF6EE` | cards · modals · elevated panels |
| `paper-recessed` | `#EBE5D8` | inputs · code blocks · receded panels |
| `rule` | `#D6CFC0` | hairline dividers, **0.75pt** |
| `ink` | `#0E1A2B` | primary text · mark · lines |
| `ink-muted` | `#4A5668` | secondary text · axis labels · captions |

### 4.3 Semantic tokens

| Token | Hex | Use |
| --- | --- | --- |
| `alert` | `#E84A2C` | error · weakness-flagged |
| `warn` | `#D9A300` | underpowered · caution |
| `signal` | `#C8FF3D` | live · settled · evidence (see §4.1) |

### 4.4 Sid + Avira — sanctioned use

The personal-meaning colors appear in two color states of the mark (§1.3) and
in five documented surfaces. Anywhere else is wrong.

| Surface | Sid (`#2C5577`) | Avira (`#D696C8`) |
| --- | --- | --- |
| Founder-mode mark (3-and-3 split) | 3 left-side blades | 3 right-side blades |
| Cofounder / about page | (ink is sid-coded; no extra token used) | one rose hairline rule above founder bios |
| First-ever simulation run | — | one-time rose pulse on the "begin" button |
| Persona chart series | — | the "warm" archetype gets rose as its series color |
| Anniversary / launch hero | — | a single rose word in a marketing headline |

Forbidden uses for `avira`:
- as a button fill
- as a primary CTA color
- on the dashboard / result page / wizard / agent chat
- in the favicon / app icon / nav lockup
- anywhere a buyer's first impression is being formed

`sid-blue` `#2C5577` is **only** used in the founder-mode duo mark. It is not a
system-wide token. Outside that single asset, structure is `ink`.

### 4.5 Dark mode

Dark mode inverts paper and ink:

| Token | Light | Dark |
| --- | --- | --- |
| `paper` | `#F4EFE6` | `#0E1A2B` |
| `ink` | `#0E1A2B` | `#F4EFE6` |
| `paper-elevated` | `#FAF6EE` | `#16243A` |
| `paper-recessed` | `#EBE5D8` | `#0A1421` |
| `rule` | `#D6CFC0` | `#1F2F47` |
| `signal` | `#C8FF3D` | `#C8FF3D` (unchanged — lime works on both) |
| `avira` | `#D696C8` | `#D696C8` (unchanged) |

Saturation drops 15% on all non-signal, non-avira colors in dark mode.

---

## 5. Typography

### 5.1 Stack

| Role | Production | Preview / fallback |
| --- | --- | --- |
| Wordmark | Söhne Schmal Halbfett (Klim) | Archivo Narrow SemiBold |
| Display (in-app) | Söhne Halbfett (Klim) | Hanken Grotesk 600 |
| Body | Söhne Buch | Hanken Grotesk 400 |
| UI labels (small caps) | Söhne Kräftig | Hanken Grotesk 500, `letter-spacing: 0.16em`, uppercase |
| Data · numerals · timestamps · cohort IDs | Berkeley Mono Regular (Berkeley Graphics) | JetBrains Mono 500 |
| Marketing hero only (1–2 lines/page max) | GT Sectra Fine Light Italic (Grilli Type) | Instrument Serif Italic |
| Code blocks (docs, runbooks) | Berkeley Mono | JetBrains Mono |

GT Sectra Fine is reserved for marketing hero lines only. It never appears
inside the application. The app is sans-only.

### 5.2 Scale (px)

`11 · 13 · 14 · 16 · 20 · 24 · 32 · 48 · 64`

Line height: **1.4** for body, **1.1** for display.

### 5.3 Numerals

All numerals — anywhere they appear — use `font-feature-settings: "tnum" on`
(tabular figures). Data, timestamps, scores, deltas, cohort sizes. The
exception is when a number is animated as a trace (see §9.1), in which case it
is rendered as SVG / Canvas rather than text.

---

## 6. Spacing

Base scale (px): `2 · 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64`.

The **12-step is load-bearing**. It is the difference between Sidira's
instrument-panel density and the typical SaaS-default `4 · 8 · 16 · 24` ladder.
Use it for tight inline gaps where 8 is too tight and 16 is too airy.

---

## 7. Layout posture

Dense, left-aligned, instrument-panel composition. Three persistent zones on
every primary product screen:

1. **Hypothesis header** — what is being tested (top strip)
2. **Cohort + score** — who was simulated and what came back (main center)
3. **Persona inspector** — per-persona reactions and waveforms (right panel)

No marketing symmetry inside the app. No centered hero blocks. No
three-column-icon feature grids. Hairline rules (`0.75pt`, `#D6CFC0`) at zone
boundaries.

### 7.1 Border radius

| Surface | Radius |
| --- | --- |
| Inputs (text, select, search) | **2 px** |
| Cards · panels | **4 px** |
| Modals | **6 px** |
| Pills · capsules · "rounded everything" | **never** |

No `border-radius: 9999px`. No fully-rounded controls. Anywhere.

### 7.2 Rules

Hairline dividers at `0.75pt` color `--rule` (`#D6CFC0` light, `#1F2F47`
dark). Heavier weight only at zone boundaries, never inside a zone.

---

## 8. Grid

| Surface | Columns | Max content width |
| --- | --- | --- |
| Marketing | 12 | 1280 px |
| App | 16 | full-bleed |

Inner app columns are 64 px wide with 16 px gutters, giving a stable readable
column for forms and a 4-column-wide block for charts.

---

## 9. Motion

Motion is constrained. There is **one** brand-level motion vocabulary, and
everything else follows it.

### 9.1 The settle trace

**Numbers are traces, not spans.** Confidence score and paired-lift settle as
an 800 ms `signal` trace — thin line draws across, oscillates briefly, settles.

| Property | Value |
| --- | --- |
| Duration | **800 ms** |
| Easing | `cubic-bezier(.34, 1.1, .64, 1)` (slight overshoot + resolve) |
| Color | `signal` (`#C8FF3D`) |
| Render | SVG `<path>` or Canvas — never a `<span>` text node |
| Settled state | the final value remains visible as a static numeral in **Berkeley Mono tabular** |

Other numerics in the app stay static and tabular. The settle trace is reserved
for the two values that earn it: confidence score and paired-lift.

### 9.2 Aperture close

The mark focuses while the instrument is computing. Same easing physics as the
settle trace.

| Property | Value |
| --- | --- |
| Trigger | simulation kicked off · result loading · the 800 ms before a settle trace · persona-group fan-out |
| Loop | `3.4 s ease-in-out infinite` |
| Keyframes | `0%, 100%`: `rotate(0) scale(1)`, monochrome ink; `40%, 60%`: `rotate(-8deg) scale(0.86)`, dual-color (Sid-blue + Avira-rose) |
| Implementation | CSS only — no JS, no bundle weight |

### 9.3 Other motion

| Trigger | Duration | Easing |
| --- | --- | --- |
| Hover · focus (color · weight) | **80 ms** | `ease-out` |
| State change (panel expand · tab swap) | **220 ms** | `ease-out` |
| Settle trace (only) | **800 ms** | `cubic-bezier(.34, 1.1, .64, 1)` |
| Aperture close (only) | **3.4 s loop** | `ease-in-out` |

No parallax. No scroll-jacking. No "AI shimmer." No floating UI elements.

---

## 10. Refuse list

These are never allowed to ship.

- Purple / violet gradients of any kind.
- Three-column "Built for X / Designed for Y / Trusted by Z" feature grids
  with iconified colored circles.
- Centered marketing-style hero blocks inside the application.
- Gradient CTA buttons.
- `border-radius: 9999px` pills, capsules, or fully-rounded controls.
- The wordmark in lowercase.
- The mark with gradient fills, drop shadows, bevels, or 3D effects.
- The mark with arbitrary rotation outside the §9.2 animation keyframes.
- The mark in any color other than `ink`, `paper`, or the sanctioned dual
  Sid-blue + Avira-rose split.
- Stock photography. Abstract blob backgrounds. Geometric mesh patterns.
- "AI-shimmer" / pulsing-gradient loading states.
- `system-ui`, `-apple-system`, `Inter`, `Roboto`, or `Helvetica` as a primary
  display or body font in production.
- "Made by humans" / "Powered by AI" footer badges.

---

## 11. File reference

| Path | Contents |
| --- | --- |
| `DESIGN.md` (this file) | canonical source of truth |
| `frontend/app/icon.svg` | favicon + app-icon (paper mark on ink) |
| `frontend/public/brand/sidira-mark.svg` | canonical monochrome mark |
| `frontend/public/brand/sidira-mark-duo.svg` | founder-mode dual-color mark |
| `frontend/public/brand/sidira-lockup.svg` | primary horizontal lockup |
| `frontend/public/brand/sidira-lockup-duo.svg` | founder-mode horizontal lockup |

When a new asset is needed, add it to `frontend/public/brand/` with a name that
matches the convention (`sidira-<thing>[-<variant>].svg`) and add a row to the
table above.

---

## 12. Changelog

| Date | Version | Change |
| --- | --- | --- |
| 2026-06-02 | 0.1 | Initial DESIGN.md. Locked: six-blade diaphragm mark · narrow uppercase SIDIRA wordmark · hybrid color C (monochrome default, dual-color during animation, dual-color founder-mode lockup) · Sid + Avira architecture · settle-trace motion bet · Söhne / Berkeley Mono / GT Sectra Fine type stack. Replaces the legacy teal/blue split-test mark. |

---

When in doubt: re-read §1, §4.1, and §9. The mark, the color architecture, and
the settle-trace motion together carry the whole brand thesis.
