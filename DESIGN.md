# Sidira — Design System

**This file is the source of truth.** Read it before making any visual, UI, or
brand decision. If something here is wrong or out of date, update this file
*and* the assets it references in the same change.

The memorable thing Sidira is trying to be: *"This looks like an instrument, not
software."*

**R2 completes the metaphor: paper bench, glass display.** A real instrument is
a matte bench with a dark glass display. Paper is the product surface — the
decision record. Glass (`#0A1421`) is the one new surface where live readings
render. Everything on screen is either **a reading** (glass, lime, settles) or
**a record** (paper, ink, static). There is no third thing.

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
and app-icon use case (the duo-color mark on a paper-filled rounded-square
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
| **Animated (transient)** | inside the product while a simulation is being computed, while a confidence trace is settling, during persona-group fan-out, and the **decision-commit beat** (one non-looping aperture cycle when a verdict commits — §9.2) | cycles monochrome → dual-color → monochrome via the aperture-close animation (§9) |
| **Brand-mode (frozen)** | favicon · app icon · public site (`sidira.ai`) · `/about` · press kit · social avatar · company anniversary hero · investor decks page-one only | dual-color (3 Sid-blue blades + 3 Avira-rose blades) on paper ground (`#F4EFE6`), static |

The default is monochrome inside the product. The dual-color brand-mode is
used on all public/brand surfaces and the favicon. The in-product prohibition
applies to **resting** color: the nav mark may pass through dual-color
mid-animation (it always does — see the §9.2 keyframes), but it never *rests*
dual-color. The dashboard, product nav, and product shell rest monochrome,
always. Buyer-facing product UI stays monochrome.
*(Resting-vs-transient clarification + decision-commit beat carve-out:
founder decision, 2026-06-10.)*

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

| Property | Production target | MVP / fallback (shipping now) |
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
| **Signal** = brand-functional | `signal` | `#C8FF3D` | live state · the instrument is reading · oscilloscope-phosphor accent. No personal meaning. Countable budget: lime lives on **at most three carriers per screen** — a glass well's live traces (the well counts as one carrier; §9.1 sanctions two traces inside it), the §9.5 live carrier, and the active state of one control. Never on two adjacent elements, never as fill, never as background. |
| **Vital** = Avira | `avira` | `#D696C8` | secondary accent for narrowly-scoped narrative surfaces — see §4.4. |

**Lime's primary home is glass.** On glass (`#0A1421`) signal lime reaches
~15.7:1 contrast and reads as phosphor — that is where it lives. On paper, lime
requires an ink companion stroke at ≥3:1 contrast (this codifies the existing
underdraw practice as law; bare lime on cream fails at ~1:1).

**Phosphor persistence:** lime traces on glass get a 5 px / 18%-opacity
underdraw of the same path. Never CSS glow, blur, or `drop-shadow`.

### 4.2 Surface and text tokens

| Token | Hex / value | Use |
| --- | --- | --- |
| `paper` | `#F4EFE6` | primary surface — archival-tungsten warm off-white |
| `paper-elevated` | `#FAF6EE` | cards · modals · elevated panels |
| `paper-recessed` | `#EBE5D8` | inputs · code blocks · receded panels |
| `rule` | `rgba(14,26,43,0.16)` | hairline dividers, **`0.75px` CSS** — a true hairline (replaces solid `#D6CFC0`; unit law in §7.2 — never `pt`) |
| `ink` | `#0E1A2B` | primary text · mark · lines |
| `ink-muted` | `#4A5668` | secondary text · axis labels · captions |

#### Glass — the instrument display

| Token | Value | Use |
| --- | --- | --- |
| `glass` | `#0A1421` | the dark display surface — **live computed readings only** |
| `glass-rule` | `rgba(244,239,230,0.08)` | hairlines on glass |
| `glass-text` | `#F4EFE6` | primary text on glass |
| `glass-muted` | `rgba(244,239,230,0.55)` | secondary text on glass |

Glass is a **component surface, not a theme**. It is sanctioned ONLY for live
instrument readings: confidence traces, CI axes, running states, live
telemetry readouts. Never for chrome, navigation, tables, text content, cards,
or marketing. If glass spreads, the brand bet dissolves into a generic dark
dashboard — this rule is load-bearing. Glass wells take radius 4 and a 1 px
`glass-rule` border.

#### Layering

- Recessed: `inset 0 1px 2px rgba(14,26,43,0.07)`
- Elevated: hairline border + `inset 0 1px 0 rgba(255,255,255,0.55)` top highlight
- Drop shadows remain banned.
- Maximum **3 paper levels + glass** on any screen.

### 4.3 Semantic tokens

| Token | Hex | Use |
| --- | --- | --- |
| `alert` | `#E84A2C` | error · weakness-flagged |
| `warn` | `#D9A300` | underpowered · caution |
| `success` | `#2F6B3F` | confirmed · ship-candidate affordances · positive deltas |
| `signal` | `#C8FF3D` | live · settled · evidence (see §4.1) |

`success` exists so that no surface ever invents its own green — it closes the
root-cause gap behind the off-token green/blue/red hexes that accumulated in
production. Token sweep happens in the rollout's PR 2.

**Semantic colors are chip and accent colors, not prose colors.** Prose and
body text are always `ink` or `ink-muted`. What each token may touch:

| Token | Text? | Accent (borders · bands · markers)? |
| --- | --- | --- |
| `warn` | **never** — ≈2.0:1 on paper, fails WCAG at any size (Codex catch, PR #174 — now law). Mid-range score text falls back to `ink-muted` | yes — this is its only job |
| `alert` | short mono designators and chips only, always co-signaled by a border or the wording itself (≈3.4:1 — below AA for small text; see §7.8). Never body text | yes |
| `success` | short mono designators and chips (≈5.6:1 — AA) | yes |
| `signal` | never text on paper (§4.1 — needs the ink companion); on glass per §4.1 | per §4.1 only |

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
- on the dashboard / result page / wizard / agent chat (transient §1.3
  animation states excepted)
- as a standalone accent in the favicon / app icon / nav lockup — its only
  sanctioned appearance there is as half of the duo mark (§1.3 brand-mode
  favicon, §9.2 animation keyframes)
- anywhere a buyer's first impression is being formed

The duo-color favicon is a sanctioned exception to the first-impression rule,
not a contradiction of it: the favicon is a §1.3 **brand-mode** surface
(browser chrome), not product UI. This line exists so the question stops
being re-litigated.

`sid-blue` `#2C5577` is **only** used in the duo mark (founder-mode surfaces,
the brand-mode favicon, and the §9.2 animation keyframes). It is not a
system-wide token. Outside the duo mark, structure is `ink`. In code the duo
hexes exist as **scoped constants** — `DUO_SID` / `DUO_AVIRA` in
`frontend/lib/design.ts` — and the §9.2 keyframes and duo lockup components
consume those, never hardcoded hexes (the scoped constant is what keeps
sid-blue out of the system palette without inviting drift into animation
CSS). Standalone SVG *assets* keep literal hexes; they can't import.

### 4.5 Dark mode

Dark mode inverts paper and ink; glass is unchanged — the display is always
dark. That sentence is the entire spec today. The computed token table lands
in this section when dark mode is actually scheduled — **do not implement
dark mode from this section, and do not invent values** (a half-spec invites
premature implementation; this one is deliberately cut to nothing). Glass is
a component surface today, not a theme.

---

## 5. Typography

### 5.1 Stack

| Role | Production target | MVP / fallback (shipping now) |
| --- | --- | --- |
| Wordmark | Söhne Schmal Halbfett (Klim) | Archivo Narrow SemiBold |
| Display (in-app) | Söhne Halbfett (Klim) | Archivo 600 |
| Body | Söhne Buch | Archivo 400 |
| UI labels (small caps) | Söhne Kräftig | Archivo 500, `letter-spacing: 0.16em`, uppercase |
| Data · numerals · timestamps · cohort IDs | Berkeley Mono Regular (Berkeley Graphics) | JetBrains Mono 500 |
| Marketing display | Söhne Schmal Halbfett, 64–96 px, uppercase | Archivo Narrow SemiBold, 64–96 px, uppercase |
| Code blocks (docs, runbooks) | Berkeley Mono | JetBrains Mono |

**The MVP ships the fallback column as its production stack** (founder
decision, 2026-06-10 — no font purchases now). The fallback family is
**Archivo** throughout — same superfamily as the Archivo Narrow wordmark
fallback, one voice. The Söhne / Berkeley Mono column stays in this table as
the purchase target so the swap is a token change at the marketing push or
first paying customer. Alternates if Klim stalls: ABC Diatype / Untitled Sans.

**GT Sectra Fine is dropped entirely** (R2). There is no serif anywhere — the
marketing display voice is the narrow grotesk at hero sizes. The app is
sans-only.

### 5.2 Scale (px)

`11 · 13 · 14 · 16 · 20 · 24 · 32 · 48 · 64`

Line height: **1.4** for body, **1.1** for display.

Floors: no text below **10 px**; below **12 px** only as uppercase mono labels
or numerals. 10 px is the floor *deliberately* — §8.4's axis numerals sit
exactly on it. The hypothesis statement is body-weight scaffolding (16 px /
600) — **the reading numeral is the hero** (84–96 px mono on glass).

**Two sanctioned off-scale ranges** — the only sizes above 64:
the reading numeral (**84–96 px**, mono on glass) and marketing display
(**64–96 px**, §5.1; a fluid `clamp()` may pass below 64 on narrow
viewports — the shipped hero clamps 48 → 96). Nothing else renders above 64;
a new hero size gets added to this paragraph before it ships.

### 5.3 Numerals

All numerals — anywhere they appear — use `font-feature-settings: "tnum" on`
(tabular figures). Data, timestamps, scores, deltas, cohort sizes. The
exception is when a number is animated as a trace (see §9.1), in which case it
is rendered as SVG / Canvas rather than text.

### 5.4 Mono is instrumentation, not atmosphere

The mono face marks **machine-derived designators and measurements**: run IDs,
versions, timestamps, counts, verdict chips, axis labels. Hints, helper text,
empty states, and conversational copy stay in the body font at sentence case.
A wall of uppercase mono is shouting, not precision — if everything is
instrumentation, nothing is.

---

## 6. Spacing

Base scale (px): `2 · 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64`.

The **12-step is load-bearing**. It is the difference between Sidira's
instrument-panel density and the typical SaaS-default `4 · 8 · 16 · 24` ladder.
Use it for tight inline gaps where 8 is too tight and 16 is too airy.

Marketing extension: `96 · 112` for section rhythm on the 1280 px marketing
grid (codified from the shipped homepage, `frontend/app/page.tsx`) —
**marketing surfaces only, never inside the app**. Without these two steps,
marketing pages invent their own.

---

## 7. Layout & interaction posture

Dense, left-aligned, instrument-panel composition. Three persistent zones on
every primary product screen:

1. **Hypothesis header** — what is being tested (top strip)
2. **Evidence** — the readings and register (main center; glass wells live here)
3. **Inspector** — provenance, manifest, or per-persona detail (right rail)

No marketing symmetry inside the app. No centered hero blocks. No
three-column-icon feature grids. Hairline rules (`0.75px`, `--rule`) at zone
boundaries.

**MVP navigation is `Hypotheses · Library`** — the nav names only pages that
exist. Future surfaces (Objectives, Rollouts, Calibration) appear in the nav
only when they ship; a nav that names pages that don't exist isn't an
expansion slot, it's a broken promise. *(Target spec: the shipped app still
exposes the pre-R2 routes; the nav lands on this shape in the rollout's
TopNav PR, #164.)*

Standard components:

- **Lineage rail** — every hypothesis screen carries its pipeline position.
  MVP: `SIMULATED → DECISION`. The full rail
  (`SIMULATED → VALIDATED → PRD → ROLLOUT → GRADED` + `STAGE n/5` chip)
  renders only when those stages exist in the backend.
- **Telemetry key/value grid** — replaces middle-dot–separated strips.
- **Provenance grid** — two-column `dt`/`dd`, replaces dot-separated footers
  (contents specced in §8.7).

Eyebrow rationing: mono-caps zone labels only where position doesn't already
name the zone.

### 7.1 Border radius

| Surface | Radius |
| --- | --- |
| Inputs (text, select, search) | **2 px** |
| Cards · panels · glass wells | **4 px** |
| Modals | **6 px** |
| Pills · capsules · "rounded everything" | **never** |

No `border-radius: 9999px`. No fully-rounded controls. Anywhere.

### 7.2 Rules

Hairline dividers at **`0.75px` CSS**, color `--rule` (`rgba(14,26,43,0.16)`;
`glass-rule` on glass). The unit is `px`, never `pt` — `pt` is a print unit
that CSS resolves to ~1px anyway, so a `pt` value in code is a rounding
accident waiting to ship. `0.75px` is intentional: 1× displays round it to a
1 px hairline; hi-DPI displays render a true sub-pixel hairline. Heavier
weight only at zone boundaries, never inside a zone.

### 7.3 Grid

| Surface | Columns | Max content width |
| --- | --- | --- |
| Marketing | 12 | 1280 px |
| App | 16 | full-bleed |

Inner app columns are 64 px wide with 16 px gutters, giving a stable readable
column for forms and a 4-column-wide block for charts.

### 7.4 Surface restraint — same system, different pressure

One system, applied at different pressures per surface. Severity is a dial,
not a default:

| Surface | Pressure |
| --- | --- |
| Hypothesis detail / instrument panel | maximum severity — dense readings, glass wells, mono designators |
| New-hypothesis wizard | **configuring a run** — two-zone layout with a live manifest rail; the run card prints as you configure. Sentence-case body-font hints; paper-elevated inputs without inset shadow; numbered sections |
| Agent chat | **evidentiary but human** — provenance pinned on every message, but conversational text is body font at body volume; mono only for designators |
| Marketing | editorial — the instrument voice at editorial scale, no glass |

A form is not a results panel. A chat is not a telemetry feed. When a surface
feels wrong, the first suspect is composition breaking these rules — not the
theme.

### 7.5 Mobile posture

Mobile is a **stacked instrument readout**, not a squeezed desktop panel.
Zones stack vertically in reading order (header → reading → register →
inspector); glass wells go full-width; the inspector rail becomes a section,
not a sidebar. Density comes from the type and spacing scale, never from
horizontal compression.

### 7.6 Library IA — three entity types

The Library hosts the product's evidence inputs:

| Entity | What it is | Authoring |
| --- | --- | --- |
| **Feature pack** | the as-built product — one versioned snapshot per product, multiple capabilities each carrying its own reverse PRD + reverse Figma (maps 1:1 to `FeaturePackManifest`/`Capability` in `backend/sidira_simulator/schemas/feature_pack.py`) | **GENERATED — NEVER AUTHORED.** Produced by sidira-crawler; the crawl-setup window configures and triggers the crawler, it never edits pack content. The as-built pack is the control arm — hand-editing it would corrupt every reading |
| **Persona packs** | who reacts | persona builder |
| **Stimuli** | the change under test, with arms | MVP: authored inline on the hypothesis (wizard 02 · Subject — `Hypothesis.prose` + `proposed_prd` + `proposed_figma`). First-class Library entity is a future migration |

Reverse PRDs render in **PRD-document typography on paper** — they are
records, not readings, so no glass. Run provenance pins all three: persona
pack version · stimulus · feature-pack snapshot (the slice frozen into
`identity.md` at run time).

**PRD-document typography — the record voice.** A reverse PRD or decision
record renders as a paper document, not a panel: a `paper-elevated` sheet
(radius 4, hairline border) with a mono provenance header on top (designator
· snapshot version · capture timestamp), then sans-only document text —
16 px body at line-height **1.6** (the one sanctioned exception to §5.2's
1.4 body line-height — long-form documents breathe) in a **≤ 68ch** measure,
headings from the §5.2 scale (20 / 24 / 32) in display weight, sentence
case. Mono never appears in the document body itself; it stops at the
provenance header. No glass, no semantic color, no motion — a record is
static ink on paper by definition (§8). *(Forward spec — the only one in
v0.3: the Library's REVERSE PRD views are not yet shipped; this spec gates
them when they land.)*

### 7.7 Controls

§10 bans what a button can't be; this is what controls **are** (codified from
the shipped wizard — `frontend/app/simulations/new/page.tsx`):

| Control | Spec |
| --- | --- |
| **Primary action** | ink fill on paper: `ink` background, `paper` text, `0.75px` `ink` border, radius 2, padding `7px 14px`, 13 px / 500 body font, sentence case (`Begin reading →`). **One per zone** — the wizard's lives in the manifest rail. |
| **Secondary action** | same geometry, transparent background, `ink` text, `rule` border. Hover: `paper-recessed` fill (80 ms, §9.3). |
| **Quiet / row action** | mono designator button: mono 10–11 px uppercase, `rule` border, radius 2, transparent. For row-level operations (expand · pin · view). Hover may invert — `paper` text on `ink` fill — but never ink-on-ink (Codex catch, PR #179). |
| **Links** | prose links are `ink` with a 1 px underline; designator links (run IDs, artifact files) are mono, underlined. Never blue — `#1d4ed8` died in the token sweep. |
| **Disabled** | `opacity: 0.5` + `cursor: not-allowed` on the same control. Never a recolor, never hidden — a disabled control is honest about existing. |
| **Press** | `translateY(1px)` at 0 ms, release 80 ms (§9.3). |
| **The signal-active control** (§4.1) | lime is a state *carrier*, not a fill: the active segment gets a 2 px lime edge with its ink companion (§4.1) — the control surface itself stays paper/ink. |

Form validation is honest text, not decoration: a `paper-recessed` note with
a `0.75px` `alert` border, message in sentence-case body font, `ink` — never
`alert` body text (§4.3). Cautionary notes use the same anatomy with a
`warn` border and `ink-muted` text — the border carries severity, the words
carry meaning. Field-level errors print the message below the field and
never rely on color alone.

Forbidden: gradient fills (§10) · pills (§10) · `avira` fills (§4.4) · lime
fills (§4.1) · more than one primary action per zone.

### 7.8 Accessibility

- **Focus**: every interactive element gets a visible `:focus-visible`
  treatment — `outline: 1px solid` `ink`, `outline-offset: 2px` on paper;
  `glass-text` on glass. The offset hairline ring is the instrument
  language's focus state. Never `outline: none` without a replacement; never
  a glow or shadow ring. Ships as the app's one global element-selector
  rule — a scoped `<style>` block in the app shell
  (`frontend/app/layout.tsx`); a surface that needs a different ring color
  (glass) sets `--focus-ring` inline.
- **Keyboard**: everything clickable is a real `<button>` / `<a>` (never
  `div + onClick`), reachable in DOM order; `Escape` closes disclosures;
  keyboard shortcuts never bind while an input has focus. A row-level
  `onClick` (the register's `tr`) is permitted only as progressive
  enhancement around a real link in the row (the register puts it in the
  hypothesis cell) — the link is the keyboard path; the row click is a
  convenience on top.
- **Contrast floors** (against `paper` / `glass`; verdicts per WCAG AA):

| Pair | Ratio | Standing |
| --- | --- | --- |
| `ink` / paper | ≈ 15:1 | body text |
| `ink-muted` / paper | ≈ 6.5:1 | secondary text — AA |
| `success` / paper | ≈ 5.6:1 | chip / designator text — AA |
| `alert` / paper | ≈ 3.4:1 | **below AA for small text** — chips co-signal with border + wording; body text never; a text-grade darker alert is an open follow-up |
| `warn` / paper | ≈ 2.0:1 | **never text** — accent only (§4.3) |
| `glass-text` / glass | ≈ 16:1 | text on the display |
| `signal` / glass | ≈ 15.7:1 | lime's home (§4.1) |
| `signal` / paper | ≈ 1:1 | illegible — requires the ink companion stroke (§4.1) |

- **Color never carries state alone**: every semantic color is co-signaled
  by wording, a glyph, or a border (§4.3, §8.5).
- **Reduced motion** is already law per-entry: every §9 spec declares its
  settled frame.

### 7.9 Breakpoints

Desktop-first, `max-width` queries. The shipped thresholds, now law:

| Threshold | What changes |
| --- | --- |
| ≤ 1023 px | the instrument grid (evidence + 340 px inspector rail) collapses to one column — the inspector rail becomes a stacked section (§7.5) |
| ≤ 859 px | glass wells go single-column; the telemetry grid drops 6 → 2 columns |
| ≤ 768 px | marketing multi-column rows stack |

New responsive behavior picks from these three thresholds before inventing a
fourth.

### 7.10 Iconography

No icon library, ever — imported icon sets are the fastest route to visual
drift. Two sanctioned registers:

- **Text glyphs** (preferred for furniture): `+ ~ −` sentiment · `▾ ▸`
  disclosure · `×` dismiss · `→` action direction · `i` info. Set in mono at
  ink weight; a glyph takes its context's text color, and §4.3 governs when
  that may be a semantic tone.
- **Drawn icons** (rare; must earn their place over a mono label): inline
  SVG in the mark's own language — `currentColor` stroke, no fill,
  `linejoin: round`, stroke weight matched to the §1.2 ladder at the render
  size.

Icons are `ink` / `ink-muted` / `currentColor`. A semantic color on an icon
requires the adjacent text to carry the same state. No emoji anywhere in
product UI (the 👍/👎 purge: PR #177).

---

## 8. Data furniture

How numbers, verdicts, and charts render. The governing split: **a reading
renders on glass and may move; a record renders on paper and is static.**

### 8.1 The decision-rule primitive

**A verdict without its policy never renders.** Every verdict carries its
decision policy beside it — threshold, margin, and rule, e.g.:

```
THRESHOLD 0.70 · POLICY DR-1 · MARGIN +0.08
SHIP IF P ≥ 0.70 AND EVERY HIGH RISK HAS A NAMED MITIGATION
```

plus a one-line "why this verdict" under the hypothesis statement tying the
verdict to the threshold, the expected lift, and the gating mitigations. The
threshold shown must be a real, persisted policy — never copy. This is what
separates decision intelligence from a prettier simulation report.

### 8.2 Verdict lexicon

The stem names the measurement; the second clause carries the polarity
(founder decision, 2026-06-10 — one lexicon, mapped 1:1 to the measurement):

| State | Decisive-positive | Decisive-negative | Other |
| --- | --- | --- | --- |
| **MVP (calibration ledger empty)** | `HIGH SIM AGREEMENT · SHIP CANDIDATE` | `HIGH SIM AGREEMENT · DO NOT SHIP` | `DIRECTIONAL` · `UNDERPOWERED` · `NOT ANSWERABLE BY THIS INSTRUMENT` |
| **Calibrated (ledger has grades)** | `DECISIVE · SHIP` | `DECISIVE · DO NOT SHIP` | `DIRECTIONAL` · `UNDERPOWERED` · `NOT ANSWERABLE BY THIS INSTRUMENT` |

**`DECISIVE` is reserved for the calibrated state.** Until the calibration
ledger has graded predictions, the product claims agreement among simulated
agents — nothing more.

**`NOT ANSWERABLE BY THIS INSTRUMENT` is the abstention verdict** (epic #309 T2,
`#311`). When the pre-flight answerability gate
(`services/answerability.py`) classifies the OEC as `out_of_scope` — a
long-horizon / network / novelty-decay outcome a first-exposure single-session
panel cannot resolve — the run still proceeds and the score is still computed,
but the ship/no-ship verdict is **categorically WITHHELD**. It is not a discount
on the number (the panel hard constraint: never multiply `confidence_score`);
it is a refusal to render a verdict the instrument cannot support. It composes
with the `underpowered_design` flip as the **outermost** branch of `verdictFor()`
(abstention precedes the numeric verdict). The withheld verdict always carries
its inspectable named reasons (the §8.1 "a verdict carries its policy" law,
applied to a *withheld* verdict: it carries *why* it was withheld).

**Verdict → token mapping.** The lexicon maps 1:1 onto §4.3 tokens —
implementers never choose a verdict color (codified from the shipped
instrument panel, `verdictFor()` in `frontend/app/simulations/[id]/page.tsx`):

| Verdict | Tone |
| --- | --- |
| `HIGH SIM AGREEMENT · SHIP CANDIDATE` / `DECISIVE · SHIP` | `success` |
| `DIRECTIONAL — BELOW SHIP THRESHOLD` | `ink-muted` |
| `UNDERPOWERED — TREAT AS DIRECTIONAL` | `ink-muted` — **not `warn`**: warn is accent-only (§4.3), and underpowered is a data condition, not an alarm |
| `NOT ANSWERABLE BY THIS INSTRUMENT` | `ink-muted` — **not `warn` / not `alert`**: the run did not fail and the OEC is not "do not ship"; it is a measurement-scope condition (the instrument abstains), so it reads in the same neutral register as `UNDERPOWERED`. The named reasons render in a hairline-`rule` note (§7.7 anatomy, message in `ink`, no semantic fill). |
| `LOW SIM AGREEMENT · DO NOT SHIP` / `DECISIVE · DO NOT SHIP` | `alert` |
| `READING IN PROGRESS` | `ink-muted` + the §9.5 live carrier |
| `RUN FAILED — NO VERDICT` | `alert` |

**Chip anatomy.** Two shipped registers, one law:

- **Register chip** (hypotheses register — `CHIP_BASE` in
  `frontend/app/simulations/page.tsx`): mono 10.5 px, letter-spacing 0.06em,
  tabular numerals, 1 px border (`rule`; the tone color borders `alert`
  states), radius 2, padding `2px 7px`, transparent background.
- **Panel verdict chip** (instrument panel, next to the §8.1 policy
  designator): mono 11 px / 600, padding `3px 8px`, radius 2, `0.75px`
  `rule` border, `paper-recessed` fill — a paper surface tone, not a
  semantic fill.

The law: a chip is **never filled with a semantic tone** — the tone lives in
the text (and, on the register's `alert` states, the border); the polarity
lives in the words (§4.3: color never carries state alone).

**Disclosure notes (degrade-and-disclose).** A run may carry a non-verdict
disclosure alongside its reading — a disclosed limitation of the *input*, not a
judgment of the change. The shipped case is the T3 pre-flight input lint (epic
#309, `#312`): when the hypothesis prose is vague / leading, or the pre-flight
verdict was paraphrase-unstable, the run still produces its normal verdict and an
**input-lint note** sits beside it (`input_flags` on `SimulationResult`). It uses
the same §7.7 note anatomy as the §8.2 instrument-scope note — `0.75px` `rule`
border, `paper-recessed` fill, message in `ink`, no semantic fill, no pill/icon —
because it is a data caution, not an alarm. Unlike the `out_of_scope` abstention,
it does **not** change the verdict label (the verdict is computed and shown
normally); for the `abstain` state the note header reads "indeterminate — please
clarify." Disclosure notes never recolor the verdict chip and never discount
`confidence_score` (panel hard constraint: the lint routes, it does not score).

**Completeness checklist (glanceable, display-only).** The `simulations/new`
wizard's manifest rail carries a `Completeness` block above the primary action:
an `N OF M ESSENTIALS` count rendered as a §8.2 **panel-verdict-chip** (mono 11
px / 600, `paper-recessed` fill, `0.75px` `rule` border — a paper tone, never a
semantic fill) over a per-item present/absent list. Each row uses the §7.10
**text-glyph** register (no icon library): present = a `✓` glyph in `success`
with an `ink` label; absent = a `·` glyph with an `ink-muted` label. **Color
never carries state alone** (§4.3 / §7.8): every row prefixes its label with a
mono `PRESENT` / `MISSING` word, so the glyph + the wording — not the tone — are
the signal. The count is a **human-glance number only**: it is deterministic and
zero-LLM (derived from form state + the existing pre-flight `reason_codes`),
never fed to `confidence_score` / the verdict / persistence, and it never gates
submit (the authoritative block/override lives in the needs_input/`422` path).
The lone advisory item (mechanism) is excluded from the count and tagged
`· advisory` in mono — purely presentational. No new colors/pills/icons.

### 8.3 Honest numbers

- The headline number is labeled for what it is. MVP:
  **"simulation agreement — raw, UNCALIBRATED (ledger empty)"**. It becomes a
  calibrated probability (e.g., `0.78`) only when the backend computes one —
  never unitless "78/100".
- **No calibrated / Brier / isotonic UI ships before the backend computes and
  exposes it**, with a visible calibration ledger the user can open. Anything
  else is credibility theater — the worst failure mode for a DS audience.
- Every aggregate carries unit-explicit n: `240 READINGS · 48 PERSONAS · 5 SEEDS`.
- Seed variance is always labeled (`SEED VARIANCE σ = 0.021`), never a bare
  glyph strip.
- Every statistic has a "how computed" methodology affordance.
- Grading internals (REALISM scores) never appear on buyer-facing surfaces.

### 8.4 Charts

- **Data-bound marks only.** Every trace, tick, and band on glass renders from
  real run data, or it doesn't render. The confidence trace is the literal
  running estimate over readings, axis-labeled — never a decorative waveform.
- Frequency bars: bare 2 px ink bars, no gray tracks.
- CI axis: SVG with real ticks, 10 px mono scale numerals (the §5.2 floor,
  deliberately), **and the decision threshold marked on the axis**.
- **Lift is a paired difference, not a second waveform**: control tick →
  treatment tick on a labeled rate axis with the delta CI band — matching the
  paired A/B semantics in `frontend/app/simulations/[id]/page.tsx`.

### 8.5 Sentiment and severity

Negative sentiment counts are data, not alarms: `ink-muted`, never
`alert`-red. Red stays reserved for risk and error severity.

### 8.6 Pending states

Pending states are honest text, never skeletons: verdict chip reads
`READING IN PROGRESS`, numerals show `—.——`, register shows
`REGISTER PENDING`. The trace is the progress indicator (§9.7) — spinners and
progress bars are banned.

### 8.7 Provenance grid

Every reading screen carries a two-column provenance grid: persona pack
version · stimulus · feature-pack snapshot · run ID · timestamp · seed ·
model — plus artifact links (`readings.csv`, transcripts, API) for the
engineer audience.

### 8.8 Registers and tables

The register is a core zone; this is its density spec (codified from the
shipped hypotheses register, `frontend/app/simulations/page.tsx`):

| Property | Spec |
| --- | --- |
| Header | mono 11 px / 400, uppercase, letter-spacing 0.1em, `ink-muted`, padding `10px 16px 6px 0`. Left-aligned; right-aligned above numeral columns |
| Cells | padding `9px 16px 9px 0`, `vertical-align: baseline`, `0.75px` `rule` bottom border |
| Numerals | right-aligned, mono, tabular (§5.3) — always |
| Designators | first column, mono, 8-hex (4-hex collides on one page — Codex, PR #175) |
| Row hover | `paper-recessed` fill, 80 ms (§9.3) |
| Stripes / zebra | never — the hairline is the row separator |
| Empty / truncated | honest text per §8.6: `REGISTER PENDING`; a display limit is labeled as one (`LATEST 50 HYPOTHESES`), never presented as a total (Codex, PR #175) |

Key/value grids (telemetry, provenance §8.7) follow the same treatment:
mono `ink-muted` keys, `ink` values, hairline separations, gaps from the §6
scale (12 / 16).

---

## 9. Motion

Motion is constrained. There is **one** brand-level motion vocabulary, and
everything else follows it. Every §9 entry must declare its
`prefers-reduced-motion` end state (the settled frame).

### 9.1 The settle trace

**Numbers are traces, not spans.** Confidence score and paired-lift settle as
an 800 ms `signal` trace — thin line draws across, oscillates briefly, settles.

| Property | Value |
| --- | --- |
| Duration | **800 ms** |
| Easing | `cubic-bezier(.34, 1.1, .64, 1)` (slight overshoot + resolve) |
| Color | `signal` (`#C8FF3D`) on glass |
| Render | SVG `<path>` or Canvas — never a `<span>` text node |
| Settled state | the final value remains visible as a static numeral in mono tabular |
| Reduced motion | skip the trace; render the settled frame (static path + final numeral) immediately |

Other numerics in the app stay static and tabular. The settle trace is reserved
for the two values that earn it: confidence score and paired-lift. Numerals
fade in over the trace's final 120 ms — they never tick or count up.

### 9.2 Aperture close

The mark focuses while the instrument is computing. Same easing physics as the
settle trace.

| Property | Value |
| --- | --- |
| Trigger (loop) | simulation kicked off · result loading · the 800 ms before a settle trace · persona-group fan-out |
| Trigger (single cycle) | **decision commit** — when §9.4 commits a reading, the nav mark plays ONE aperture cycle, then rests monochrome (§1.3 carve-out) |
| Loop | `3.4 s ease-in-out infinite` (single cycle: one 3.4 s pass, no loop) |
| Keyframes | `0%, 100%`: `rotate(0) scale(1)`, monochrome ink; `40%, 60%`: `rotate(-8deg) scale(0.86)`, dual-color (Sid-blue + Avira-rose) |
| Implementation | CSS only — no JS, no bundle weight |
| Reduced motion | static monochrome mark |

### 9.3 Other motion

| Trigger | Duration | Easing |
| --- | --- | --- |
| Hover · focus (color · weight) | **80 ms** | `ease-out` |
| State change (panel expand · tab swap) | **220 ms** | `ease-out` |
| Telemetry wipe | **240 ms** | `--ease-mech` |
| Tab underline | **160 ms** | `--ease-mech` |
| Content crossfade (page swap) | **120 ms** | `ease-out` |
| Button press | translateY(1px) at **0 ms**, release **80 ms** | — |
| Settle trace (only) | **800 ms** | `cubic-bezier(.34, 1.1, .64, 1)` |
| Aperture close (only) | **3.4 s loop** | `ease-in-out` |

`--ease-mech: cubic-bezier(.32, .72, 0, 1)` — the mechanical ease for
instrument furniture.

Reduced motion: every transition in this table jumps to its end state
instantly (durations drop to 0). The button press keeps its instant
translateY — it is positional feedback, not animation.

No parallax. No scroll-jacking. No "AI shimmer." No floating UI elements.

### 9.4 Reading choreography

Fires **once per data arrival**, never on revisit. Total ≤ 1300 ms:

| t | Event |
| --- | --- |
| 0 | static text renders |
| 0–240 ms | telemetry wipe |
| 120–920 ms | confidence trace + CI marker sweep (transform-only) |
| 280–1080 ms | lift trace |
| 800 ms | numeral fade-in |
| 940 ms | CI band `scaleX` |
| 960 ms+ | register stagger (30 ms steps, one staggered list per view) + inspector fade |

Reduced motion: the choreography lands on its settled frame.

### 9.5 Live carrier

The single sanctioned pulse: a 2 px lime underline under `STATUS RUNNING`,
3.4 s ease-in-out, opacity 0.45 ↔ 1.0, phase-locked to the aperture loop.
**Nothing else ever pulses.** Reduced motion: static underline at full opacity.

### 9.6 Marketing motion

Signal-path draw (OKR → … → ROLLOUT, 1600 ms, once) + calibration convergence
(1200 ms, once) + hero settle. Nothing else. Reduced motion: settled frames.

### 9.7 Live plotting

While `STATUS = RUNNING`, the confidence trace extends point-by-point as
reading batches land — **event-driven** (batch graded → point plots), never
time-based. The trace IS the progress indicator. Each new point appears
instantly (no per-point tween — it's a measurement, not an animation); the
only continuous motion during a run is the §9.5 carrier + aperture loop.
Pending states per §8.6. On the final batch, hold ~400 ms, then fire §9.4 once
to commit the reading — and the nav mark plays its single decision-commit
cycle (§9.2). Reduced motion: the trace still extends (it's data); §9.4 lands
on its settled frame.

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
- **Glass surfaces anywhere except live computed readings** (no glass chrome,
  nav, tables, cards, text content, or marketing).
- **Decorative instrument marks** — any trace, tick, or band not bound to
  backend data ("instrument cosplay — worse than no trace").
- **A verdict chip without its decision policy** (§8.1).
- **Spinners, progress bars, and skeleton loaders** — the trace is the
  progress indicator; pending states are honest text (§8.6).
- **Calibrated / Brier / isotonic UI before the backend computes it** (§8.3).
- **Count-up / odometer numerals** — numerals fade in over the trace's final
  120 ms (§9.1).

---

## 11. File reference

| Path | Contents |
| --- | --- |
| `DESIGN.md` (this file) | canonical source of truth |
| `frontend/lib/design.ts` | the token values in code — update together with §4 |
| `frontend/app/icon.svg` | favicon + app-icon (duo-color mark on paper ground — §1.3 brand-mode) |
| `frontend/public/brand/sidira-mark.svg` | canonical monochrome mark |
| `frontend/public/brand/sidira-mark-duo.svg` | founder-mode dual-color mark |
| `frontend/public/brand/sidira-lockup.svg` | primary horizontal lockup |
| `frontend/public/brand/sidira-lockup-duo.svg` | founder-mode horizontal lockup |
| `frontend/public/brand/merch/sidira-sticker-mark.svg` | merch · hex die-cut sticker, ink mark on paper (38 mm) |
| `frontend/public/brand/merch/sidira-sticker-duo.svg` | merch · hex die-cut sticker, duo mark — ships only if merch is sanctioned as a §1.3 brand-mode surface (open founder decision) |
| `frontend/public/brand/merch/sidira-sticker-reading.svg` | merch · settle-trace reading sticker, signal + paper on glass (84 × 30 mm) |
| `frontend/public/brand/merch/sidira-sticker-verdict.svg` | merch · verdict-with-policy sticker, ink on paper (84 × 31 mm) |
| `frontend/public/brand/merch/sidira-sticker-wordmark.svg` | merch · lockup strip sticker, ink on paper (80 × 21 mm) |
| `frontend/public/brand/merch/sidira-print-decision-rule.svg` | merch · apparel back print, §8.1 decision rule, single color via `currentColor` |
| `frontend/public/brand/merch/sidira-print-reading.svg` | merch · apparel print, settle-trace record, signal + paper — dark garments only (§4.1) |
| `frontend/public/brand/merch/lookbook.html` | merch · tech pack 01: full line, specs, production notes, open decisions |

When a new asset is needed, add it to `frontend/public/brand/` with a name that
matches the convention (`sidira-<thing>[-<variant>].svg`) and add a row to the
table above.

---

## 12. Changelog

| Date | Version | Change |
| --- | --- | --- |
| 2026-06-02 | 0.1 | Initial DESIGN.md. Locked: six-blade diaphragm mark · narrow uppercase SIDIRA wordmark · hybrid color C (monochrome default, dual-color during animation, dual-color founder-mode lockup) · Sid + Avira architecture · settle-trace motion bet · Söhne / Berkeley Mono / GT Sectra Fine type stack. Replaces the legacy teal/blue split-test mark. |
| 2026-06-10 | 0.2 | **R2 "Paper bench, glass display"** (founder-signed; epic #156, this PR = #163). Adds: glass surface + tokens (§4.2) · lime-on-glass law + phosphor persistence (§4.1) · `success` token (§4.3) · true-hairline `rule` · data-furniture section (§8): decision-rule primitive, MVP verdict lexicon (`HIGH SIM AGREEMENT` stem, `DECISIVE` calibrated-only), honest-numbers rules, data-bound marks, paired-difference lift · surface restraint "same system, different pressure" (§7.4) · mobile = stacked instrument readout (§7.5) · Library IA (§7.6) · motion §9.3 mech ease + §9.4 reading choreography + §9.5 live carrier + §9.6 marketing motion + §9.7 live plotting · refuse-list additions. Drops GT Sectra Fine; fallback family unified on Archivo; MVP ships fallbacks (founder, 2026-06-10). Resolves: duo commit-beat carve-out (§1.3/§9.2) · favicon duo-on-paper confirmed (§1.3/§4.4/§11 reconciled) · verdict stem. Grid folded into §7.3. |
| 2026-06-12 | 0.3 | **Spec-gap close** (#195; external design review, triaged in `sessions/phase-5-design-system/external-design-review-2026-06-12.md`). Codifies what the shipped R2 surfaces already render — no new product surfaces (R2.4-compatible); the one forward spec is §7.6's record voice, gating the unshipped Library REVERSE PRD views. Adds: §7.7 controls (primary/secondary/quiet/links/disabled/signal-active/validation) · §7.8 accessibility (focus ring, keyboard, contrast floors, color-never-alone) · §7.9 breakpoints · §7.10 iconography (no icon libraries) · §8.2 verdict→token mapping + chip anatomy (register + panel registers) · §8.8 registers and tables · §7.6 PRD-document "record voice" typography. Promotes the R2.14 Codex catch into law: `warn` is accent-only, never text (§4.3 token-role table). Resolves inconsistencies: unit law `px` never `pt`, `0.75px` intentional (§7.2 rewrite; §4.2) · sanctioned off-scale type ranges 84–96 reading numeral / 64–96 marketing display (§5.2) · marketing spacing extension 96·112 (§6) · lime budget restated as countable (§4.1) · scoped duo constants `DUO_SID`/`DUO_AVIRA` in `lib/design.ts` (§4.4) · dark-mode half-spec cut to one line (§4.5) · favicon brand-mode exception acknowledged (§4.4). |
| 2026-06-12 | 0.3.1 | **Deviation close** (#197). The three v0.3 known-deviation notes resolved in lockstep with the code: §7.8 focus ring shipped as the app's one global element-selector rule (scoped `<style>` in `frontend/app/layout.tsx`; `--focus-ring` is the override mechanism for glass — no glass surface has a focusable element yet) · §7.7 wizard validation now matches the law (banner message in `ink`; field-level persona error gets the full note anatomy; both carry `role="alert"`) — note removed · §7.8 keyboard deviation note **corrected, not fixed**: the register row's hypothesis cell already carried a real `<Link>` (`simulations/page.tsx`), so the `tr onClick` was always progressive enhancement; the spec now states that pattern as law. |
| 2026-06-12 | 0.3.2 | **§4.3 compliance sweep** (#199; no spec change — the law already stood). Every `alert`-as-body-text site outside the wizard converted to the §7.7 note anatomy: message in `ink`, severity on a `0.75px` `alert` border, `role="alert"` on dynamically-injected errors (18 sites across the agent chat, persona library, crawl setup, register, simulation detail, persona-group chat, and sample-workspace card). ThumbsControl's `(failed)` label — sans, so not a sanctioned mono designator — reads in `ink-muted` (visual-only; the #170 flag/onSet freeze untouched). Inline error notes unified on radius 2; full-page error cards stay radius 4 (they are cards). Chips, verdict designators, score numerals, status dots, and alert borders verified legitimate and unchanged. |
| 2026-06-16 | 0.3.3 | **Abstention verdict** (epic #309 T2, `#311`). §8.2 adds the fourth verdict state `NOT ANSWERABLE BY THIS INSTRUMENT` to the MVP + calibrated lexicons and the verdict→token map (`ink-muted` — a measurement-scope condition, not `warn`/`alert`). When the deterministic answerability gate classifies the OEC as `out_of_scope` (long-horizon / network / novelty-decay), `verdictFor()` WITHHOLDS the ship/no-ship verdict as its outermost branch (precedes the `underpowered_design` flip and the numeric path); the score is still computed and `confidence_score` is never discounted (panel hard constraint). The withheld verdict carries its inspectable named reasons in a hairline-`rule` §7.7 note (message in `ink`, no semantic fill). No new colors/pills/icons. |
| 2026-06-16 | 0.3.4 | **Input-lint disclosure surface** (epic #309 T3, `#312`). §8.2 codifies the degrade-and-disclose **disclosure note** as a sanctioned pattern: a non-verdict caution about the *input* (vague / leading prose, or a paraphrase-unstable pre-flight verdict) carried on `input_flags` and rendered beside the normal reading on the simulation detail page. It REUSES the §7.7 note anatomy verbatim — `0.75px` `rule` border, `paper-recessed` fill, message in `ink`, no semantic fill, no pill/icon — because it is a data caution, not an alarm. Unlike the 0.3.3 `out_of_scope` abstention it does **not** change the verdict label (the verdict is computed and shown normally); for the `abstain` state the note header reads "indeterminate — please clarify." No new colors/pills/icons; the lint routes and never discounts `confidence_score` (panel hard constraint). |
| 2026-06-16 | 0.3.5 | **Answerable hypothesis authoring** (epic #309 T4, `#313`; the deploy-unblocker). The `simulations/new` wizard's `01 · Claim` section now defaults to four structured fields following the falsifiable template "If [change] for [cohort], then [OEC metric] [direction]," composed into the prose the API expects and shown verbatim in a `paper-recessed` mono preview; a quiet `Free-text instead →` toggle (§7.7 quiet control) keeps the escape hatch so terse expert claims are never over-constrained. The OEC metric picker (`05 · Outcome metric`) is **decoupled from A/B mode** — declaring a metric clears the answerability gate's `oec_undeclared` block in either mode (the paired lift delta stays A/B-only; single-arm reports the metric rate). Two new authoring surfaces REUSE the §8.2 / §7.7 disclosure-note anatomy verbatim — `0.75px` `rule` border, `paper-recessed` fill, mono label, body in `ink` (fixes in `ink-muted`), no semantic fill / pill / icon / alert-red: (1) a **live inline lint** rendering the deterministic zero-LLM `POST /simulations/preflight` answerability + leading-framing reasons/fixes as the user authors, and (2) the **needs_input surface** that catches the create path's `422` and renders the named reasons + fixes as guidance (never a dead-end), offering an explicit `Run anyway as generic reception` quiet affordance when `allow_override` (resubmits with `run_as_generic_reception`). No new colors/pills/icons; no migration; `confidence_score` arithmetic untouched (panel hard constraints). |
| 2026-06-16 | 0.3.6 | **Glanceable completeness checklist** (epic #309 T6, `#337`). §8.2 codifies a display-only `Completeness` block in the `simulations/new` manifest rail: an `N OF M ESSENTIALS` count rendered as a §8.2 panel-verdict-chip (mono, `paper-recessed` fill, `rule` border) over a per-item present/absent list in the §7.10 text-glyph register — present `✓` (`success`) + `ink` label, absent `·` + `ink-muted` label, each row prefixed with a mono `PRESENT`/`MISSING` word so color never carries state alone (§4.3 / §7.8). The six essentials (change · cohort · OEC metric · direction · conditional design attached · advisory mechanism) are derived **deterministically, zero-LLM** from the wizard's form state + the EXISTING live `POST /simulations/preflight` `reason_codes` (the "conditional design attached" item reuses the gate's own `structurally_invisible_change` signal rather than re-deriving the regime classifier client-side); the count is a human-glance number **never fed to `confidence_score` / the verdict / persistence** and **never gates submit** (the authoritative block/override stays in the T4 needs_input/`422` path). The lone advisory item (mechanism) is excluded from the count and mono-tagged `· advisory`. Frontend-only — no backend / no route / no migration. No new colors/pills/icons; `confidence_score` arithmetic untouched (panel hard constraint). |

---

When in doubt: re-read §1, §4.1, §8.1, and §9. The mark, the color
architecture, the decision-rule primitive, and the settle-trace motion
together carry the whole brand thesis.
