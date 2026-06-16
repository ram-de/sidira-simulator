# SIDIRA — Design System v1: **THE READING CONSOLE**

> The forged, production-ready design language for Sidira (AI persona-simulation
> platform for founders). Spine: **precision**. Grafted: editorial's *Provenance
> Spine*, instrument/OSCILLA's *Channel Legend*, data-journalism's *individual-agent
> Cohort Settle*, GRAPHITE's *dim-unlocked trace*, playful-pro's *Living Manifest*.
> One law governs everything below: **the spectacle is the computation, and every
> reading wears its own uncertainty on its sleeve.**
>
> This document is the single source of truth. Hex + OKLCH are both authoritative
> (OKLCH is the design intent; hex is the sRGB fallback). An engineer can
> reproduce any pixel from here; a mock-builder can build any page — including its
> effects — from here.

---

## 0. Thesis & the two-faced ontology

**Thesis (one line):** *A measurement instrument for human reaction — a confident
dark **Console** frames live, computed populations; a cool blueprint **Sheet**
prints the record; and every number carries its spread, its provenance, and its
calibration state by law.*

**The ontology that the whole system encodes — memorize this, it is the grammar:**

| Surface | Mode | Means | Voice | Density | Provenance device |
|---|---|---|---|---|---|
| **Console** | dark (`#0B1220`) | a *live, computed estimate* | mono numerals, dense | **Channel Legend** (silkscreen, top of panel) |
| **Sheet** | light (`#F3F4F7`) | a *printed record / fact* | serif prose, airy | **Provenance Spine** (left binder-margin) |

Crossing from Console to Sheet is a *meaningful* transition: the screen "prints"
a live reading onto paper. Dark = estimate, light = record. The user learns the
product's epistemology through color temperature before reading a word.

**Three governing adjectives:** `exact · alive · candid`.

**Route → mode law (locked per route, never inverts mid-scroll):**
- **Console (dark):** marketing landing, app shell, dashboard, simulation setup &
  results, agent transcript, persona-build wizard, crawl setup, any live reading.
- **Sheet (light):** Capability / PRD long-form, Persona-pack record detail,
  About / press / changelog, any archival document of record.

---

## 1. Color tokens

All colors are authored in OKLCH. Hex is the sRGB rounding. Use CSS custom
properties; never inline a raw hex in a component.

### 1.1 Console — dark instrument body (primary)

| Token | OKLCH | Hex | Role |
|---|---|---|---|
| `--console-900` | `oklch(0.17 0.022 248)` | `#0B1220` | deepest well — display glass behind live readings, the scope screen |
| `--console-850` | `oklch(0.205 0.021 248)` | `#10192A` | app canvas / hero background |
| `--console-800` | `oklch(0.245 0.020 248)` | `#161F32` | raised panels, nav, cards |
| `--console-750` | `oklch(0.29 0.019 248)` | `#1D2740` | hover / pressed panel |
| `--console-700` | `oklch(0.34 0.018 249)` | `#26314C` | input wells, recessed controls |
| `--console-line` | `oklch(0.40 0.016 250)` | `#33405C` | hairline rules — render at **1px, alpha 0.5** |

### 1.2 Ink on Console

| Token | OKLCH | Hex | Role |
|---|---|---|---|
| `--text-hi` | `oklch(0.97 0.006 250)` | `#F2F4F8` | primary text, headlines |
| `--text` | `oklch(0.84 0.008 250)` | `#C6CCD8` | body |
| `--text-mut` | `oklch(0.66 0.010 250)` | `#8A93A6` | captions, axis labels, provenance |
| `--text-faint` | `oklch(0.52 0.012 251)` | `#646E84` | disabled, watermark designators |

### 1.3 Signal — the one saturated accent (LIVE READING ONLY)

A phosphor **lime-cyan**. Reads as *measurement* (oscilloscope trace), not
"eco-startup green." **Budget is law: at most one signal carrier per primary
viewport region.** It is *light*, never paint — never a default button fill.

| Token | OKLCH | Hex | Role |
|---|---|---|---|
| `--signal` | `oklch(0.86 0.155 168)` | `#48EFCA` | live traces, the running pulse, active live control, ship-verdict |
| `--signal-dim` | `oklch(0.72 0.13 168)` | `#39B894` | settled/resting signal, secondary trace, hover-rest |
| `--signal-wash` | `oklch(0.86 0.155 168 / 0.12)` | `rgba(72,239,202,0.12)` | trace underdraw / fill — **never CSS blur/glow** |

> On `--console-900`, `#48EFCA` hits ~13:1 contrast and behaves like emitted
> light. That emission is the whole point; do not desaturate it.

### 1.4 Spread — doubt as a first-class color (the honesty primitive)

Because every Sidira number is uncalibrated, the system renders *doubt* with its
own dedicated low-chroma **amber-sand**. Used ONLY for confidence intervals,
error bars, hold-verdicts, and ungraded/placeholder marks. It never competes
with signal.

| Token | OKLCH | Hex | Role |
|---|---|---|---|
| `--spread` | `oklch(0.78 0.06 78)` | `#C8B68A` | CI bands, error-bar caps, "estimate" hatching |
| `--spread-dim` | `oklch(0.62 0.05 78)` | `#90815F` | ungraded/placeholder designator text |
| `--spread-wash` | `oklch(0.78 0.06 78 / 0.14)` | `rgba(200,182,138,0.14)` | CI ribbon fill on the field |

### 1.5 Arm tints — A/B identity (provenance, NEVER valence)

Two cold provenance poles that name *which experiment arm*, used only in A/B
traces and per-persona fan-outs. **A negative reaction is rendered in `--text`,
never in the treatment color — harm is information, not alarm.**

| Token | OKLCH | Hex | Role |
|---|---|---|---|
| `--arm-control` | `oklch(0.74 0.11 232)` | `#4FA8E0` | Control arm · "Sid" pole · steady blue |
| `--arm-treat` | `oklch(0.72 0.13 22)` | `#F0796B` | Treatment arm · "Avira" pole · warm signal-red |

**Series ramp** (≥3 cohorts, e.g. per-persona): interpolate the two arm poles on
a single perceptual OKLCH ramp — **never a rainbow**:
`#4FA8E0 → #6E93B6 → #9389A0 → #C77E86 → #F0796B`.

### 1.6 Semantic — borders + word only, NEVER fill

| Token | Hex | Role |
|---|---|---|
| `--verdict-ship` | `#48EFCA` (= signal) | positive verdict reuses signal — *ship == live* |
| `--verdict-hold` | `#C8B68A` (= spread) | inconclusive / don't-ship reuses spread — *hold == uncertain* |
| `--edge-warn` | `#C9A227` | caution border (uncalibrated, starter-pack, low-stability) — border + word |
| `--alert` | `#F0683C` | hard failures only (crawl error, run failed) — **border + word, never a banner fill** |

### 1.7 Sheet — light blueprint record (long-form only)

Pointedly **not cream**. A cool blueprint off-white in the same hue-250 family,
so the two modes feel like one instrument with two faces.

| Token | OKLCH | Hex | Role |
|---|---|---|---|
| `--sheet` | `oklch(0.965 0.004 250)` | `#F3F4F7` | reading surface (cool, not cream) |
| `--sheet-raised` | `oklch(0.99 0.003 250)` | `#FBFBFD` | sheet cards, modals |
| `--sheet-sunk` | `oklch(0.93 0.006 250)` | `#E6E8EE` | inputs, code wells on sheet |
| `--sheet-line` | `oklch(0.86 0.006 250)` | `#D4D8E0` | hairlines on sheet (0.75px) |
| `--sheet-ink` | `oklch(0.24 0.020 250)` | `#1A2336` | body ink on sheet |
| `--sheet-mut` | `oklch(0.50 0.014 250)` | `#5E6678` | muted on sheet |
| `--sheet-signal` | `oklch(0.58 0.12 168)` | `#0FA882` | signal darkened for AA on sheet (≥4.5:1) |
| `--sheet-spread` | `oklch(0.56 0.06 78)` | `#857449` | spread darkened for AA on sheet |

### 1.8 The two hard color laws

1. **Signal is reserved for a live reading. Spread is reserved for doubt.** If a
   saturated color appears that is neither signal (live), spread (uncertain),
   arm-control/treat (identity), nor a 1px semantic border — it is a bug.
2. **Color never carries valence.** Green is not "good," red-arm is not "bad."
   A negative cohort reaction renders in plain ink. This is the single discipline
   that separates an instrument from a dashboard.

---

## 2. Typography

Type is the instrument's voice. Three families, each with one job, paired on
true contrast axes. All Google-Fonts-available.

### 2.1 Families

| Role | Family | Weights | Why |
|---|---|---|---|
| **Display / Body / UI** | **Geist** | 700 · 600 · 500 · 450 · 400 | Geometric-grotesque, mechanically precise — reads as *engineered*, not editorial. One family carries headline→body via weight. |
| **Data / Numerals / Designators** | **Geist Mono** | 500 · 400 | Every score, CI, seed, snapshot id, role chip, axis tick — `font-variant-numeric: tabular-nums` **locked on globally**. Numbers are the evidence; they get the typewriter. |
| **Record prose (Sheet only)** | **Newsreader** | 400 · 400 italic | The one sanctioned serif, and ONLY in genuine document prose (PRD/About/dossier). A reverse-PRD is a *document of record*; a reading serif earns its place there and **nowhere on Console**. |

Pairing logic: Geist (proportional) × Geist Mono (its monospace sibling) is a
designed pair on the proportional-vs-monospaced axis — the cleanest instrument
voice. Newsreader (serif) ↔ Geist (sans) is a true contrast axis, fired only on
the record surface.

`@import` (Google Fonts):
```
https://fonts.googleapis.com/css2?family=Geist:wght@400;450;500;600;700&family=Geist+Mono:wght@400;500&family=Newsreader:ital,opsz,wght@0,6..72,400;1,6..72,400&display=swap
```

### 2.2 Type scale (modular ≈ 1.25; tabular numerals on every numeric)

| Step | Size / line-height | Tracking | Weight / Family | Use |
|---|---|---|---|---|
| `display-xl` | `clamp(2.6rem, 6vw, 5.5rem)` / 0.98 | `-0.035em` | 700 Geist | marketing hero headline |
| `display-l` | `3.25rem` / 1.02 | `-0.03em` | 600 Geist | About / Product section heads |
| `h1` | `2.0rem` / 1.08 | `-0.025em` | 600 Geist | page titles |
| `h2` | `1.5rem` / 1.12 | `-0.02em` | 600 Geist | section titles |
| `h3` | `1.125rem` / 1.2 | `-0.01em` | 550 Geist | card titles |
| `lede` | `1.375rem` / 1.5 | `-0.005em` | 400 Newsreader *(Sheet)* | the one editorial sentence under a hero / dossier opener |
| `prose` | `1.0625rem` / 1.65 | `0` | 400 Newsreader *(Sheet)* | PRD/About/persona prose — **max 68ch** |
| `body-l` | `1.0625rem` / 1.6 | `0` | 450 Geist | Console reading prose |
| `body` | `0.9375rem` / 1.55 | `0` | 400 Geist | UI default |
| `caption` | `0.8125rem` / 1.4 | `0` | 400 Geist | helper, captions |
| `mono-data` | `0.875rem` / 1.3 | `0` (tnum) | 400 Geist Mono | inline scores, CIs, table cells |
| `data-lg` | `2rem` / 1.0 | `0` (tnum) | 500 Geist Mono | hero readings (agreement score, lift) |
| `data-xl` | `clamp(3rem, 7vw, 5rem)` / 1.0 | `-0.01em` (tnum) | 500 Geist Mono | the masthead figure on a results page |
| `designator` | `0.6875rem` / 1.2 | `+0.08em` UPPER | 500 Geist Mono | id/role/snapshot chips, Channel Legend |

**Global numeric law:** `font-variant-numeric: tabular-nums;` on every numeric
and mono element. `text-wrap: balance` on `h1`–`h3` and display; `text-wrap:
pretty` on prose.

### 2.3 The numeric law (the candor rule)

Every figure that is a *reading* — score, agreement %, A/B lift, CI bound, cohort
`n`, sentiment, timestamp — is **Geist Mono, tabular, and rendered with its
uncertainty adjacent** (e.g. `0.62 ±0.08`). **A bare number with no spread is
forbidden on any results surface.** This is enforced by the Spread Stamp (§7.2).

### 2.4 Eyebrow / designator discipline

The small mono UPPERCASE designator is reserved for genuine *machine identifiers*
(snapshot `2026-W25`, role `ANALYST`, seed `0x4f`, persona id) — it is
provenance, never a decorative kicker. **At most one decorative eyebrow per
marketing page.** In-app, designator frequency is governed by the *data*, not by
section rhythm (the Channel Legend is "data," so it is unlimited).

The wordmark **SIDIRA** is Geist 600 uppercase, `letter-spacing: 0.06em`. Never
glyph-tricked.

---

## 3. Spacing · grid · radius · elevation

### 3.1 Spacing scale (4px base, geometric)

`2 · 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 · 96 · 128` (px).

**Density philosophy — dense-but-calm (`VISUAL_DENSITY ≈ 5`):** tight vertical
rhythm *inside* a region (8/12), generous silence *between* regions (48/64).
Tables and manifests run 8px row padding — scanned like a logbook. Records on
Sheet breathe (24/32 internal, 96/128 between). The density *shift itself* is
meaningful: dense Console = "watch this," airy Sheet = "read this."

### 3.2 Grid

- **App shell:** fixed **56px** left icon-rail + fluid content; content
  `max-width: 1320px`; gutter `32px`.
- **Marketing:** 12-col, `max-width: 1240px`, 24px gutter; hero breaks to
  **full-bleed** for the Population Field.
- **Reading (Sheet):** single **720px** measure column + a **240px** right margin
  rail for provenance/designators — the lab-notebook margin. Long-form prose caps
  at **68ch**. The **Provenance Spine** (§7.4) occupies the left **180px** binder
  margin.

### 3.3 Radius — one family

| Token | Value | Use |
|---|---|---|
| `--r-well` | `4px` | inputs, chips, wells, code blocks |
| `--r-panel` | `8px` | panels, cards, modals |
| `--r-frame` | `10px` | the hero console frame, the scope display well |
| `--r-dot` | `9999px` | **only** the live status dot |

No pills. No 16px blobs. Sharp-ish corners read as *instrument*, not consumer-app.

### 3.4 Borders & elevation

- Hairlines: **1px `--console-line` @ 0.5 alpha** (dark) / **0.75px `--sheet-line`**
  (light).
- **Elevation = lightness-step + a 1px top inner highlight**
  (`box-shadow: inset 0 1px 0 rgba(255,255,255,0.04)`), **never a drop shadow.**
  Panels sit *in* the surface like cut metal — there are no floating cards.
- **Recession** conveys depth too: a well (`--console-700`/`--console-900`) is
  *darker* than the panel it sits in. Glass (`--console-900`) is reserved for
  live computed readings — never resting chrome.

---

## 4. Core components

All measurements concrete. Console (dark) is the default; Sheet (light) variants
noted where they differ. Motion values reference §5.

### 4.1 Buttons

Height **36px** (default), **28px** (compact), **44px** (hero CTA). Padding
`0 16px`. Radius `--r-well` (4px). Font: Geist 500, `body` size. Tactile: on
`:active`, `transform: translateY(1px)` + inner highlight dims. Focus: **2px
`--console-line`→`--signal-dim` track** (not a glow). Transition `140ms` ease-out.

| Variant | Rest | Hover | Notes |
|---|---|---|---|
| **Primary** | bg `--console-700`, 1px `--console-line`, text `--text-hi`, inner highlight | bg `--console-750` | The workhorse. Signal is NOT a default fill. |
| **Live / Run** | bg transparent, **1px `--signal`**, text `--signal`, `--signal-wash` on hover | fill `--signal-wash` | The ONE button that may carry signal — it initiates a live reading. One per region. |
| **Secondary** | transparent, 1px `--console-line`, text `--text` | bg `--console-800` | |
| **Ghost** | transparent, no border, text `--text-mut` | text `--text-hi` | inline/toolbar actions |
| **Destructive** | transparent, **1px `--alert`**, text `--text-hi` | bg `rgba(240,104,60,0.08)` | border + word, never solid red |

Disabled: text `--text-faint`, border alpha halved, no hover, `cursor: not-allowed`.

### 4.2 Inputs / textarea

Height **36px**. Bg `--console-700` (recessed well), 1px `--console-line`, radius
4px, text `--text-hi`, placeholder `--text-faint`, padding `0 12px`. Font Geist
`body`; **numeric inputs are Geist Mono tabular.** Focus: border →
`--signal-dim`, 1px. Label above: `caption` `--text-mut`. Error: border `--alert`
+ helper word in `--text` (never red fill). Sheet: bg `--sheet-sunk`, border
`--sheet-line`, ink `--sheet-ink`.

### 4.3 Select / combobox

Trigger = input spec + a 16px chevron (`--text-mut`). Menu: panel `--console-800`,
1px `--console-line`, radius 8px, inner highlight, **no drop shadow** (use a 1px
`--console-900` ring beneath for separation). Items: 32px row, 8px pad, hover bg
`--console-750`, selected = 1px left `--signal-dim` bar + `--text-hi`. Combobox:
filter input at top (input spec), results virtualized at 32px rows; matched
substring in `--signal-dim`. Open/close `160ms` ease-out, no slide-bounce.

### 4.4 Cards / panels

Bg `--console-800`, 1px `--console-line`, radius `--r-panel` (8px), inner
highlight, padding `16/24`. **A card earns itself only when it is a discrete
record** (one persona, one capability, one simulation). Otherwise group with
`border-top` hairlines + negative space. **Never nest cards.** A card carrying a
live reading gets a **Channel Legend** (§7.3) as its top strip. Sheet card: bg
`--sheet-raised`, border `--sheet-line`.

### 4.5 Nav / app-shell

- **Left rail:** fixed 56px, bg `--console-850`, 1px right `--console-line`. Icon
  buttons 40px, centered; active = 1px left `--signal-dim` bar + icon `--text-hi`;
  rest `--text-mut`. Tooltip on hover (`designator` mono).
- **Top bar:** 52px, bg `--console-850`, 1px bottom hairline. Left: wordmark +
  current route designator. Right: a **global Channel Legend** when a run is live
  (`CH1 · n=… · seed … · UNCALIBRATED`) and the running status dot.
- **Tab underline:** 2px `--signal-dim`, slides via `cubic-bezier(0.32,0.72,0,1)`
  (mechanical) over `180ms`.
- Mode boundary (Console→Sheet route change) performs the 120ms cross-tone print
  (§7.5).

### 4.6 Data tables (the logbook)

The most-used surface. Row height **36px**, 8px vertical pad, `mono-data` cells,
**every numeric column tabular and right-aligned**. Header: `designator` mono,
`--text-mut`, 1px bottom `--console-line`. Rows divided by hairlines (no zebra by
default; optional zebra = `--console-850` alt rows). Hover row: bg
`--console-750`. Numeric cells that are *readings* carry an inline Spread Stamp
glyph (◇/◆) in the calibration column. Sort affordance: a `designator` arrow in
the active header. Sticky header on scroll. **No bare reading numbers** — every
metric column shows `value ±ci`.

### 4.7 Charts

House chart system. Axes: 1px `--console-line`, ticks `designator` mono
`--text-mut`. Series use arm tints; the **distribution is the hero** (§7.1). Every
chart:
- **draws itself** on first paint (the "trace draw," §5.4) — 700ms mechanical
  `stroke-dashoffset`.
- carries a **phosphor underdraw**: a 5px / 18%-alpha echo of the same path
  beneath the 1.5px live stroke (CRT persistence) — **never `filter: blur`/`glow`.**
- shows its **CI band** as a `--spread-wash` ribbon around the mean line.
- if **uncalibrated**, renders a visible **dashed `--spread` noise-floor line**
  beneath the trace, and (per the dim-unlocked law, §7.6) drifts without locking.

Small inline sparklines in tables: static SVG, settled, with the underdraw.

### 4.8 Badges / chips / designators

- **Designator chip:** `designator` mono UPPER, 1px `--console-line`, radius 4px,
  padding `2px 6px`, text `--text-mut`. For ids/roles/snapshots.
- **Calibration glyph:** ◇ (hollow) = uncalibrated/no ground truth · ◆ (filled) =
  graded. Always attached to a reading. ◇ inherits `--spread-dim`.
- **Status badge:** border + word only. `LIVE` = `--signal` text + a 6px running
  dot; `HOLD` = `--spread` text; `FAILED` = `--alert` text. Never a filled pill.

### 4.9 Modals / dialogs

Overlay: `rgba(11,18,32,0.66)` (no blur). Panel: `--console-800`, 1px
`--console-line`, radius `--r-panel`, inner highlight, max-width 560px, padding
24/32. Enter: `opacity 0→1` + `translateY(8px→0)` over `180ms` ease-out (out-quint).
Exit: `120ms`. Title `h3`, body `body`. Footer actions right-aligned, 12px gap.
Esc + backdrop close; focus trap; return focus on close.

### 4.10 Empty / loading / error states

- **Empty (the empty ledger):** the honest frame. Show the surface's structure
  *bare* — for results, the axis + CI grid with no trace, captioned
  `designator`: `LEDGER EMPTY · NO READING YET`. Never an illustration mascot. A
  single Live/Run button to fill it.
- **Loading (taking a reading):** the Population Field at drift, or the trace
  drawing itself, or skeleton rows at `--console-850` with a single 2s opacity
  breath (the *only* sanctioned skeleton shimmer). Numbers count up on arrival
  rather than pop.
- **Error:** 1px `--alert` border on the affected panel + a `body` line in
  `--text` stating what failed and the next action, prefixed by a `FAILED`
  designator. **Never** a red banner fill, never a toast that auto-dismisses a
  data error.

---

## 5. Motion + effects system

### 5.1 Motion law

**Everything either settles or stays still.** A reading *settles* (a trace
converges, a number counts to rest). A record *is still*. There is no third
motion. Nothing loops for decoration. `prefers-reduced-motion` replaces every
settle with an instant cut to the rest state and freezes all canvas/WebGL to
their settled poster.

### 5.2 Easings (only these)

| Token | Curve | Use |
|---|---|---|
| `--ease-out` | `cubic-bezier(0.22, 1, 0.36, 1)` | reveals, modal enter, default UI |
| `--ease-settle` | `cubic-bezier(0.16, 1, 0.3, 1)` | the long convergence / settle |
| `--ease-mech` | `cubic-bezier(0.32, 0.72, 0, 1)` | telemetry wipes, tab underline, trace draw, progress |

**No bounce, no elastic, no spring overshoot, ever.** An instrument does not
wobble.

### 5.3 Durations

| Context | Duration |
|---|---|
| App micro-interaction (hover, focus, press) | `140ms` |
| Keyboard-initiated action | `0ms` (instant) |
| Menu / modal enter | `160–180ms` |
| Tab underline / telemetry wipe | `180ms` |
| Mode cross-tone print (Console↔Sheet) | `120ms` |
| Trace draw (chart self-draw) | `700ms` |
| Number count-up (verdict commit) | `300ms` |
| Marketing scroll-reveal | `400–600ms`, 60ms stagger |
| **The Population Field settle** | `8s` hero loop / event-driven in-app — the one long-running motion |

### 5.4 Supporting signature motions

- **Trace draw:** any line chart, CI axis, or confidence curve draws itself
  left-to-right on first paint via `stroke-dashoffset`, `700ms --ease-mech` —
  the universal "instrument is taking a reading" gesture. Underdraw is the 5px /
  18%-alpha echo (phosphor persistence), **never CSS glow.**
- **Status pulse:** a running simulation shows one 8px `--signal` dot with a 2s
  opacity breath (`0.5↔1.0`) — the *only* sanctioned infinite loop in the product.
- **Verdict commit:** when a run resolves, the hero number counts up (tabular,
  `300ms --ease-mech`) and the field settles in **one non-looping beat**. Decisive,
  once. (The aperture-close brand animation, DESIGN.md-reserved, may fire here.)
- **Settle damp:** the final 200ms of any data animation damps to rest
  (overshoot-free) so the number visibly "comes to rest" like a needle.

### 5.5 THE NAMED GRAPHICS / EFFECTS LAYER — **THE POPULATION FIELD**

> This is not optional polish. It is the signature layer, and it *is* the product
> computing. One shader serves the canned hero and the true results — the
> marketing promise and the product are provably the same instrument.

**What it is.** A live, generative **agent field** rendered in **WebGL** on a
single full-bleed canvas, seeded with **N points = the real cohort size** (e.g.
1,200 agents). Each point is one synthetic person. At rest the points drift in a
slow, low-amplitude **curl-noise flow-field** — a calm, breathing population. When
a "bet" is applied (hero auto-loop, or a real run on the results page), a
**wavefront of `--signal` lime sweeps across the field** and each particle
*reacts*: it shifts along a 1-D reaction axis (left = rejects, right = adopts),
and the field **re-sorts into a distribution**. The emergent histogram **IS the
verdict.** The CI band materializes as a `--spread`-amber ribbon around the mean.

**Why it is the product, literally.** Sidira computes how a *population* reacts
to a change. The showpiece is not a metaphor for that — it is a live, honest
visualization of exactly that computation. Spectacle = intelligence.

**Where it lives.**
- **Landing hero** — full-bleed, auto-running a *canned* bet on an 8s loop:
  `drift → wavefront → re-sort → settle → CI ribbon → dissolve back to drift`.
- **Simulation results** — driven by *real* run data: real N, real distribution,
  real CI, real arm split. The same shader, now telling the truth.
- **Agent transcript / persona pages** — a *single* particle pulled out of the
  field and isolated, threading the macro showpiece to the micro 1:1 chat.

**Grafted behavior — the Cohort Settle as individuals (from data-journalism).**
The re-sort is not an abstract cloud collapsing. Each agent **streams up and
finds its bin as a countable dot**; control-arm dots and treatment-arm dots
settle in their two arm tints. **Every dot is one clickable agent:**
`hover → one-line reaction` tooltip; `click → that agent's 1:1 transcript`. This
makes "we simulated 400 minds" viscerally, countably true and threads macro-field
→ micro-transcript.

**Grafted behavior — the dim-unlocked trace (from GRAPHITE).** Honesty rendered
in *motion*: a **placeholder / uncalibrated** reading renders **dim and drifting,
and never settles** — it visibly *won't resolve*. A **real, graded** reading
*locks*: the trace snaps from noise to signal, blooms once, and comes to rest with
the ◆ glyph. An ungraded reading can never fake a verdict, because it can never
stop moving. (See §7.6.)

**Tech / implementation recipe.**
1. **Tier 1 — WebGL** (`regl` or raw GLSL), single full-bleed `<canvas>`:
   - **Vertex shader:** instanced points (`gl.POINTS`, size 1.5px). Position =
     `restPos + curlNoise(restPos, time) * driftAmp` while idle; on a bet,
     interpolate each point toward `binPos(reactionScore[i])` with a per-point
     delay seeded by index (the "stream up and settle" stagger).
   - **Fragment shader:** additive blending at low alpha so the field reads as
     *graphite dust catching light*, not fireworks. The wavefront is a moving
     smoothstep band in `--signal`; everything behind it tints toward signal,
     ahead stays `--text-faint`.
   - **Color budget:** monochrome console body; **lime appears only on the
     wavefront and the settled mean**; arm tints only on the settled A/B dots.
     Never a rainbow particle system.
   - Capped at **30fps**; pauses entirely when the tab is hidden
     (`visibilitychange`).
2. **Tier 2 — Canvas 2D** fallback (no WebGL): same reaction math, dots drawn with
   `lineWidth` + a cheap `shadowBlur` glow, ≤2,000 points.
3. **Tier 3 — static SVG poster** (SSR / headless / `prefers-reduced-motion` /
   old GPU): the settled distribution + CI ribbon, **frozen** — arguably the more
   honest frame anyway. The same value-series → polyline math feeds all three
   tiers, so the signature is identical from shader to static SVG.

**Taste rules (what keeps it intelligent, not gimmicky).**
- It only ever renders **real reading data or an honest canned baseline** — never
  decorative noise pretending to be data.
- Off the hero and results, the field is *quiet ambient* (drift only) or absent.
- Bloom/wash held ≤18% opacity; underdraw, never CSS `glow`.
- One signal carrier per region (the field counts as the carrier on results).
- It never animates while a tab is hidden; reduced-motion freezes to the poster.

---

## 6. Provenance architecture (the two-faced honesty system)

Provenance is structural, not per-number fine print. It has two faces — one on
each mode — and they are complementary, not duplicative.

- **Console (live) side → the Channel Legend** (§7.3): an instrument silkscreen on
  every live reading panel. Makes "UNCALIBRATED" *structurally unavoidable* on the
  estimate side.
- **Sheet (record) side → the Provenance Spine** (§7.4): a permanent left
  binder-margin on every record. Makes candor *architectural* on the fact side.

Together they guarantee: **no reading and no record can be displayed without its
origin and calibration state visible.**

---

## 7. The signature elements (unique to Sidira)

### 7.1 ✦ THE POPULATION FIELD — *graphics showpiece* (see §5.5)

A WebGL agent field where **particle count = real cohort size** and the emergent,
**countable, clickable** histogram is the verdict. Same shader feeds the canned
landing hero and the true in-app results — so the marketing promise and the
product are provably identical. No competitor in product-research tooling renders
the *actual population reacting in real time, as individuals you can click into.*

### 7.2 ✦ THE SPREAD STAMP — *candor as a visual primitive*

Every reading renders with its uncertainty **physically attached**: the number in
Geist Mono tabular, a `--spread`-amber CI bar beneath it (`0.62 ±0.08`), and a
one-glyph **calibration stamp** — **◇** (hollow) = uncalibrated / no ground truth
yet, **◆** (filled) = graded. **A bare number with no spread is forbidden on any
results surface** (enforced in tables, charts, hero figures). This turns the
product's hardest objection — *"your numbers are uncalibrated"* — into a
scannable, repeatable mark instead of a paragraph of disclaimer.

### 7.3 ✦ THE CHANNEL LEGEND — *provenance as instrument silkscreen (Console side)*

Every live reading surface carries a real scope **channel legend** as a mono
silkscreen strip across the top of its panel:

```
CH1 · CONTROL · n=240 · seed 0x1f · groq/llama-3.3 · 2026-W25 · ◇ UNCALIBRATED
```

Set in `designator` mono, `--text-mut`, with the calibration glyph and the word
`UNCALIBRATED` in `--spread-dim`. It is the provenance line reimagined as a
scope's channel readout — always present, never dismissible — making "this is a
raw, uncalibrated reading" *structurally unavoidable* on the estimate side.

### 7.4 ✦ THE PROVENANCE SPINE — *provenance as architecture (Sheet side)*

Every record (persona pack, capability PRD, simulation archive, agent transcript
record) carries a fixed **left binder-margin** — a 180px mono "spine" running the
full height of the sheet — stating, stacked, exactly where the reading came from:
crawl snapshot id · capture date · seed · model · sample size `n` · calibration
state. Always present, always quiet, never dismissible. Trust isn't a badge you
earn once; it's a spine that runs down every page. This is the one surface where
**Newsreader** is sanctioned for the body prose beside it (the document voice).

### 7.5 ✦ THE CONSOLE↔SHEET INVERSION — *meaningful theming*

The app is a dark Console (live instrument); records invert to a light blueprint
Sheet. Crossing from a *reading* surface to a *record* surface performs a single
`120ms` cross-tone transition — the screen visibly **"prints" the reading onto
paper.** The split is not decoration: it encodes the product's own
reading-vs-record ontology, so a user feels the difference between a live estimate
and an archival fact in their retina before reading a word.

### 7.6 ✦ THE LIVING MANIFEST + DIM-UNLOCKED TRACE — *felt cost, honesty in motion*

As the founder composes a hypothesis, a **Living Manifest** panel assembles the
receipt in real time (cohort, arms, model, seed, sample size), and the chosen
**cohort size seeds a matching agent count into the Population Field as a live
preview**. Choosing **A/B visibly forks and doubles the field** — making the 2×
cost *felt*, not buried in a tooltip. (Grafted from playful-pro; its spring
physics, glass-blur, and magnetic CTAs are dropped wholesale — those hurt fit.)

Coupled to this: the **dim-unlocked trace** (graft from GRAPHITE) — while the
manifest is uncommitted or a reading is uncalibrated, the field/trace is **dim and
drifting and never settles**. Only a real, graded reading **locks** to rest with
the ◆ glyph. *An ungraded reading literally cannot fake a verdict, because it can
never stop moving.* Honesty rendered in motion, not just color and glyph.

---

## 8. Implementation reference (CSS custom properties)

```css
:root {
  /* Console (dark, default app + marketing) */
  --console-900:#0B1220; --console-850:#10192A; --console-800:#161F32;
  --console-750:#1D2740; --console-700:#26314C; --console-line:#33405C;
  --text-hi:#F2F4F8; --text:#C6CCD8; --text-mut:#8A93A6; --text-faint:#646E84;
  --signal:#48EFCA; --signal-dim:#39B894; --signal-wash:rgba(72,239,202,.12);
  --spread:#C8B68A; --spread-dim:#90815F; --spread-wash:rgba(200,182,138,.14);
  --arm-control:#4FA8E0; --arm-treat:#F0796B;
  --verdict-ship:#48EFCA; --verdict-hold:#C8B68A; --edge-warn:#C9A227; --alert:#F0683C;

  /* Sheet (light, records only) */
  --sheet:#F3F4F7; --sheet-raised:#FBFBFD; --sheet-sunk:#E6E8EE;
  --sheet-line:#D4D8E0; --sheet-ink:#1A2336; --sheet-mut:#5E6678;
  --sheet-signal:#0FA882; --sheet-spread:#857449;

  /* Radius / motion */
  --r-well:4px; --r-panel:8px; --r-frame:10px;
  --ease-out:cubic-bezier(.22,1,.36,1);
  --ease-settle:cubic-bezier(.16,1,.3,1);
  --ease-mech:cubic-bezier(.32,.72,0,1);

  --font-sans:"Geist",system-ui,sans-serif;
  --font-mono:"Geist Mono",ui-monospace,monospace;
  --font-serif:"Newsreader",Georgia,serif; /* Sheet prose only */
}
* { font-variant-numeric: tabular-nums; }       /* numbers never jitter */
.elevated { box-shadow: inset 0 1px 0 rgba(255,255,255,.04); } /* never drop-shadow */
@media (prefers-reduced-motion: reduce){ *{animation:none!important;transition-duration:1ms!important;} }
```

---

## 9. Why this is top-0.1% for THIS product

1. **The spectacle is the substance.** The Population Field *is* the product's
   core computation — a population reacting to a change, countable to the
   individual. A sophisticated buyer reads it as a live demo, not eye candy.
2. **Honesty is a visible feature, not fine print.** The Spread Stamp, the dual
   provenance architecture (Channel Legend + Provenance Spine), and the
   dim-unlocked trace disarm the strongest skeptic — "your numbers are
   uncalibrated" — at the pixel level. The instrument *cannot* show a reading
   without showing its limits.
3. **The theme split teaches the product's ontology for free.** Console (live
   estimate) ↔ Sheet (printed fact) is a 1:1 map onto Sidira's epistemology,
   learned through color temperature.
4. **It refuses every 2026-AI tell** — cool blueprint Sheet over cream, Geist ×
   Geist Mono over warm display serif, color-as-identity over status rainbow,
   provenance-as-architecture over eyebrow-on-every-section.
5. **It is the most shippable of the ambitious options** — one shader, three
   tiers, one radius family, elevation-by-lightness, no font sprawl.
