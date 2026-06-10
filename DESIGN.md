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
| **Signal** = brand-functional | `signal` | `#C8FF3D` | live state · the instrument is reading · oscilloscope-phosphor accent. No personal meaning. Used at ≤ 8% of any rendered surface, only on live traces and the active state of one control. Never as fill, never as background. |
| **Vital** = Avira | `avira` | `#D696C8` | secondary accent for narrowly-scoped narrative surfaces — see §4.4. |

**Lime's primary home is glass.** On glass (`#0A1421`) signal lime reaches
~14:1 contrast and reads as phosphor — that is where it lives. On paper, lime
requires an ink companion stroke at ≥3:1 contrast (this codifies the existing
underdraw practice as law; bare lime on cream fails at ~1.1:1).

**Phosphor persistence:** lime traces on glass get a 5 px / 18%-opacity
underdraw of the same path. Never CSS glow, blur, or `drop-shadow`.

### 4.2 Surface and text tokens

| Token | Hex / value | Use |
| --- | --- | --- |
| `paper` | `#F4EFE6` | primary surface — archival-tungsten warm off-white |
| `paper-elevated` | `#FAF6EE` | cards · modals · elevated panels |
| `paper-recessed` | `#EBE5D8` | inputs · code blocks · receded panels |
| `rule` | `rgba(14,26,43,0.16)` | hairline dividers, **0.75pt** — a true hairline (replaces solid `#D6CFC0`) |
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

`sid-blue` `#2C5577` is **only** used in the duo mark (founder-mode surfaces,
the brand-mode favicon, and the §9.2 animation keyframes). It is not a
system-wide token. Outside the duo mark, structure is `ink`.

### 4.5 Dark mode

Dark mode inverts paper and ink:

| Token | Light | Dark |
| --- | --- | --- |
| `paper` | `#F4EFE6` | `#0E1A2B` |
| `ink` | `#0E1A2B` | `#F4EFE6` |
| `paper-elevated` | `#FAF6EE` | `#16243A` |
| `paper-recessed` | `#EBE5D8` | `#0A1421` |
| `rule` | `rgba(14,26,43,0.16)` | `#1F2F47` |
| `signal` | `#C8FF3D` | `#C8FF3D` (unchanged — lime works on both) |
| `avira` | `#D696C8` | `#D696C8` (unchanged) |
| `glass` | `#0A1421` | `#0A1421` (unchanged — the display is always dark) |

Saturation drops 15% on all non-signal, non-avira colors in dark mode. Dark
mode remains a follow-on; glass is a component surface today, not a theme.

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
or numerals. The hypothesis statement is body-weight scaffolding (16 px / 600)
— **the reading numeral is the hero** (84–96 px mono on glass).

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

---

## 7. Layout posture

Dense, left-aligned, instrument-panel composition. Three persistent zones on
every primary product screen:

1. **Hypothesis header** — what is being tested (top strip)
2. **Evidence** — the readings and register (main center; glass wells live here)
3. **Inspector** — provenance, manifest, or per-persona detail (right rail)

No marketing symmetry inside the app. No centered hero blocks. No
three-column-icon feature grids. Hairline rules (`0.75pt`, `--rule`) at zone
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

Hairline dividers at `0.75pt` color `--rule` (`rgba(14,26,43,0.16)` light,
`#1F2F47` dark; `glass-rule` on glass). Heavier weight only at zone
boundaries, never inside a zone.

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
| **MVP (calibration ledger empty)** | `HIGH SIM AGREEMENT · SHIP CANDIDATE` | `HIGH SIM AGREEMENT · DO NOT SHIP` | `DIRECTIONAL` · `UNDERPOWERED` |
| **Calibrated (ledger has grades)** | `DECISIVE · SHIP` | `DECISIVE · DO NOT SHIP` | `DIRECTIONAL` · `UNDERPOWERED` |

**`DECISIVE` is reserved for the calibrated state.** Until the calibration
ledger has graded predictions, the product claims agreement among simulated
agents — nothing more.

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
- CI axis: SVG with real ticks, 10 px mono scale numerals, **and the decision
  threshold marked on the axis**.
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

When a new asset is needed, add it to `frontend/public/brand/` with a name that
matches the convention (`sidira-<thing>[-<variant>].svg`) and add a row to the
table above.

---

## 12. Changelog

| Date | Version | Change |
| --- | --- | --- |
| 2026-06-02 | 0.1 | Initial DESIGN.md. Locked: six-blade diaphragm mark · narrow uppercase SIDIRA wordmark · hybrid color C (monochrome default, dual-color during animation, dual-color founder-mode lockup) · Sid + Avira architecture · settle-trace motion bet · Söhne / Berkeley Mono / GT Sectra Fine type stack. Replaces the legacy teal/blue split-test mark. |
| 2026-06-10 | 0.2 | **R2 "Paper bench, glass display"** (founder-signed; epic #156, this PR = #163). Adds: glass surface + tokens (§4.2) · lime-on-glass law + phosphor persistence (§4.1) · `success` token (§4.3) · true-hairline `rule` · data-furniture section (§8): decision-rule primitive, MVP verdict lexicon (`HIGH SIM AGREEMENT` stem, `DECISIVE` calibrated-only), honest-numbers rules, data-bound marks, paired-difference lift · surface restraint "same system, different pressure" (§7.4) · mobile = stacked instrument readout (§7.5) · Library IA (§7.6) · motion §9.3 mech ease + §9.4 reading choreography + §9.5 live carrier + §9.6 marketing motion + §9.7 live plotting · refuse-list additions. Drops GT Sectra Fine; fallback family unified on Archivo; MVP ships fallbacks (founder, 2026-06-10). Resolves: duo commit-beat carve-out (§1.3/§9.2) · favicon duo-on-paper confirmed (§1.3/§4.4/§11 reconciled) · verdict stem. Grid folded into §7.3. |

---

When in doubt: re-read §1, §4.1, §8.1, and §9. The mark, the color
architecture, the decision-rule primitive, and the settle-trace motion
together carry the whole brand thesis.
