# Sidira — Design Vision: "PRECISION"

> A clean-sheet design language. Ignores the prior paper-and-ink system by mandate.
> Channels the *spirit* of Linear-grade precision-minimalism — not a clone — and
> bends it toward the one truth this product owns: **it simulates human behavior
> under measurement.** Every effect amplifies that truth or it does not ship.

---

## 1. Design thesis (one line)

**A measurement instrument for human reaction — where a confident dark console frames live, computed populations, and every reading wears its own uncertainty on its sleeve.**

---

## 2. Mood / emotional target

The feeling is **mission-control calm meeting laboratory candor.** Not a SaaS
dashboard, not a hype splash, not a warm-paper "editorial" record either. The
visitor — a founder pitching a Kohavi-class buyer — should feel they have walked
up to a *calibrated instrument*: the kind of dark, matte console where a
spectrum analyzer or an oscilloscope lives. It is dense but never busy; the
density reads as *information*, not clutter. The dominant emotion is **earned
confidence**: decisive enough to act on, honest enough to trust. Spectacle, when
it appears, reads as *intelligence* — a population of synthetic minds visibly
computing — never as decoration. The north star sentence: *"these people measure
human reaction the way an instrument measures voltage, and I want that pointed at
my roadmap."*

Three adjectives that govern every decision: **exact · alive · candid.**

---

## 3. Color system

A single committed instrument palette. **One dark console family** carries the
app and the marketing hero; **one warm-neutral "sheet"** carries long-form
records; **one signal accent** (phosphor lime-cyan) is the only saturated color
and it means exactly one thing: *a live, computed reading.* Uncertainty has its
own dedicated muted band so the product can render doubt as a first-class color,
not an afterthought.

### 3.1 Core ramp — "Console" (the instrument body)

Dark is not chosen "because tools look cool dark." Physical scene: a founder, at
night before a board meeting, leaning into a screen to read whether a bet lands —
the screen is the only light in the room, and it must not glare. That forces dark.

| Token | OKLCH | Hex | Role |
|---|---|---|---|
| `console-900` | `oklch(0.17 0.022 248)` | `#0B1220` | deepest well — the display glass, behind live readings |
| `console-850` | `oklch(0.205 0.021 248)` | `#10192A` | app canvas / hero background |
| `console-800` | `oklch(0.245 0.020 248)` | `#161F32` | raised panels, nav, cards |
| `console-750` | `oklch(0.29 0.019 248)` | `#1D2740` | hover / pressed panel |
| `console-700` | `oklch(0.34 0.018 249)` | `#26314C` | input wells, recessed |
| `console-line` | `oklch(0.40 0.016 250)` | `#33405C` | hairline rules (rendered at 1px, alpha 0.5) |

### 3.2 Ink on console

| Token | OKLCH | Hex | Role |
|---|---|---|---|
| `text-hi` | `oklch(0.97 0.006 250)` | `#F2F4F8` | primary text, headlines |
| `text` | `oklch(0.84 0.008 250)` | `#C6CCD8` | body |
| `text-mut` | `oklch(0.66 0.010 250)` | `#8A93A6` | captions, axis labels, provenance |
| `text-faint`| `oklch(0.52 0.012 251)` | `#646E84` | disabled, watermark designators |

### 3.3 Signal — the one accent (live reading only)

A phosphor **lime-cyan** — cooler and more clinical than a pure lime, so it reads
as *measurement* (oscilloscope trace, spectrum peak) not "eco-startup green."
Budget is law: **at most one signal carrier per primary viewport region.**

| Token | OKLCH | Hex | Role |
|---|---|---|---|
| `signal` | `oklch(0.90 0.19 158)` | `#5CF2B0` → tuned to `#48EFCA` | live traces, the running pulse, active control |
| `signal-dim`| `oklch(0.72 0.13 162)` | `#39B894` | signal on hover-rest / secondary trace |
| `signal-wash`| `oklch(0.90 0.19 158 / 0.12)` | — | trace underdraw / fill (never CSS blur) |

> Exact signal hex: **`#48EFCA`** (a cyan-leaning phosphor). On `console-900` it
> hits ~13:1 contrast and behaves like emitted light, which is the whole point.

### 3.4 Uncertainty band — doubt as a color (the product's signature honesty)

Because every Sidira number is *uncalibrated*, the system needs a color that says
"this is an estimate, here is its spread." A desaturated **amber-sand**, used
ONLY for confidence intervals, error bars, and "ungraded / placeholder" marks.
It never competes with signal; it is deliberately low-chroma.

| Token | OKLCH | Hex | Role |
|---|---|---|---|
| `spread` | `oklch(0.78 0.06 78)` | `#C8B68A` | CI bands, error-bar caps, "estimate" hatching |
| `spread-dim`| `oklch(0.62 0.05 78)` | `#90815F` | ungraded/placeholder designator text |

### 3.5 Semantic (used as 1px borders + word, NEVER as fill)

Following the product's anti-alarm rule: a negative reaction is information, not
red. Semantic color appears only on a hairline + the word reads in `text`.

| Token | Hex | Role |
|---|---|---|
| `verdict-ship` | `#48EFCA` (= signal) | a positive verdict reuses signal — ship == live |
| `verdict-hold` | `#C8B68A` (= spread) | "don't ship / inconclusive" reuses spread — hold == uncertain |
| `alert` | `#F0683C` | hard failures only (crawl error, run failed) — border + word |

### 3.6 Light mode — "Sheet" (records & long-form only)

Long-form reading (Capability detail, Persona pack detail, About prose) inverts
to a **warm low-chroma sheet** — but pointedly NOT the banned cream. It is a cool
*blueprint* off-white that belongs to the same console hue family (hue 250), so
the two modes feel like one instrument with two faces, not two websites.

| Token | OKLCH | Hex | Role |
|---|---|---|---|
| `sheet` | `oklch(0.965 0.004 250)` | `#F3F4F7` | reading surface (cool, not cream) |
| `sheet-raised`| `oklch(0.99 0.003 250)` | `#FBFBFD` | sheet cards |
| `sheet-line` | `oklch(0.86 0.006 250)` | `#D4D8E0` | hairlines on sheet |
| `sheet-ink` | `oklch(0.24 0.020 250)` | `#1A2336` | body ink on sheet |
| `sheet-mut` | `oklch(0.50 0.014 250)` | `#5E6678` | muted on sheet |

Mode rule: **app shell + every "reading" surface = Console (dark). Long-form
"record" surfaces = Sheet (light).** This is the one sanctioned theme split, and
it is *meaningful*: dark = live instrument, light = printed record. It maps 1:1
onto the product's own reading-vs-record distinction, so a user learns the
grammar without being told.

---

## 4. Typography

Type is the hero. Three families, each with a job, paired on real contrast axes
(not two similar sans). All Google-Fonts-available.

### 4.1 Families

| Role | Family | Why this, not the default |
|---|---|---|
| **Display / Headlines** | **Geist** (700/600/500) | Geometric-grotesque with true mechanical precision; reads as engineered, not editorial. Chosen over Inter (too neutral) and over any serif (a serif here would lie — this product is not a manuscript). |
| **Body / UI** | **Geist** (400/450) | Same family at text weights for a unified instrument voice; the contrast axis is carried by the mono + numeric face, not by a second sans. |
| **Data / Numerals / Designators** | **Geist Mono** (500/400) | Every score, CI, seed, snapshot id, role chip, and axis tick is set in Geist Mono with **tabular numerals locked on**. Numbers are the evidence; they get the typewriter. |
| **Optional accent (reading mode only)** | **Newsreader** (text, italic) | In Sheet/long-form ONLY, the PRD/About prose may use Newsreader at body for genuine document warmth. Articulated reason: a reverse-PRD is literally a *document of record*; a reading serif earns its place there and nowhere else. Strictly absent from all Console surfaces. |

> Pairing logic: Geist (geometric sans) × Geist Mono (its monospace sibling) is a
> *designed* pair on the proportional-vs-monospaced axis — the cleanest possible
> instrument voice. Newsreader appears only where the surface is genuinely a
> document, never as decoration.

### 4.2 Type scale (modular, ratio ≈ 1.25, tabular numerals everywhere numeric)

| Step | Size / line-height | Tracking | Use |
|---|---|---|---|
| Display-XL | `clamp(2.6rem, 6vw, 5.5rem)` / 0.98 | `-0.035em` | marketing hero headline |
| Display-L | `3.25rem` / 1.02 | `-0.03em` | About / Product section heads |
| H1 | `2.0rem` / 1.08 | `-0.025em` | page titles |
| H2 | `1.5rem` / 1.12 | `-0.02em` | section titles |
| H3 | `1.125rem` / 1.2 | `-0.01em` | card titles |
| Body-L | `1.0625rem` / 1.6 | `0` | reading prose (max 68ch) |
| Body | `0.9375rem` / 1.55 | `0` | UI default |
| Caption | `0.8125rem` / 1.4 | `0` | helper, captions |
| Mono-data | `0.875rem` / 1.3 | `0` (tnum on) | scores, CIs, tables |
| Designator | `0.6875rem` / 1.2 | `+0.08em` UPPER | mono id/role/snapshot chips |

> **Eyebrow discipline:** the small mono UPPERCASE "designator" is reserved for
> genuine *machine identifiers* (snapshot `2026-W25`, role `ANALYST`, seed
> `0x4f`, persona id) — it is provenance, never a decorative section kicker. There
> is at most one decorative eyebrow per marketing page; in-app, the designator is
> data, so its frequency is governed by the data, not by section rhythm.

### 4.3 Numeric law

Every figure that is a *reading* — score, agreement %, A/B lift, CI bound,
cohort `n`, sentiment, timestamp — is **Geist Mono, `font-variant-numeric:
tabular-nums`, and rendered with its uncertainty adjacent** (e.g. `0.62
±0.08`). A bare number with no spread is forbidden on any results surface.

---

## 5. Spatial system

### 5.1 Grid
- **App shell:** fixed 56px left rail (icon nav) + fluid content, max content
  `1320px`, gutter `32px`.
- **Marketing:** 12-col, `max-w-[1240px]`, 24px gutter; hero breaks to full-bleed
  for the graphics showpiece.
- **Reading (Sheet):** single 720px measure column + a 240px right margin rail
  for provenance/designators (the "lab-notebook margin").

### 5.2 Spacing scale (4px base, geometric)
`2 · 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 · 96 · 128`. Density philosophy:
**dense-but-calm** — tight vertical rhythm inside a region (8/12), generous
silence *between* regions (48/64). Tables and manifests run at 8px row padding;
they are meant to be scanned like a logbook.

### 5.3 Radius
**One scale, used everywhere:** `4px` for wells/inputs/chips, `8px` for panels/cards,
`10px` for the hero console frame. No pills, no full-round except the live status
dot. Sharp-ish corners read as *instrument*, not consumer-app.

### 5.4 Borders & elevation
- Hairlines are **1px `console-line` at 0.5 alpha** (dark) / `sheet-line` (light).
- Elevation is carried by **lightness step + a 1px top inner highlight**
  (`inset 0 1px 0 rgba(255,255,255,0.04)`), never by drop shadow. The console has
  no "floating cards"; panels sit *in* the surface like cut metal.

### 5.5 Density philosophy
VISUAL_DENSITY ≈ 5 — a cockpit you can read. The product is data-rich; the design
earns calm by *ranking* (one hero number, everything else recedes to `text-mut`)
rather than by removing information.

---

## 6. Motion + effects — the signature graphics layer

### 6.1 The named showpiece: **"THE POPULATION FIELD"**

A live, generative **particle/agent field** rendered on **WebGL (regl or raw
GLSL via a single full-bleed canvas)**, with a 2D-canvas fallback and a static
SVG poster for reduced-motion / SSR / headless.

**What it is:** a dark instrument field seeded with **N points = the cohort size**
(e.g. 1,200 agents). Each point is one synthetic person. At rest they drift in a
slow, low-amplitude flow-field (curl noise) — a calm, breathing population. When
a "bet" is applied (hero auto-loop, or a real run on the results page), a
**wavefront of signal-lime sweeps across the field** and each particle *reacts*:
it shifts along a 1-D reaction axis (left = rejects, right = adopts), and the
field visibly **re-sorts into a distribution**. The emergent histogram IS the
verdict. The CI band materializes as a `spread`-amber ribbon around the mean line.

**Why it is the product, literally:** Sidira computes how a *population* reacts to
a change. The showpiece is not a metaphor for that — it is a live, honest
visualization of exactly that computation. Spectacle = intelligence.

**Where it lives:**
- **Landing hero** — full-bleed, auto-running a canned bet on a loop (8s cycle:
  drift → wavefront → re-sort → settle → CI ribbon → dissolve back to drift).
- **Simulation results** — driven by *real* run data: real N, real distribution,
  real CI. The same shader, now telling the truth.
- **Agent transcript / persona pages** — a *single* particle pulled out of the
  field and isolated, threading the macro showpiece to the micro 1:1 chat.

**How it stays tasteful (the discipline):**
- Monochrome console body; **lime appears only on the reaction wavefront and the
  settled mean** — never a rainbow particle system.
- Particles are 1.5px points, additive-blended at low alpha; the field reads as
  *graphite dust catching light*, not a fireworks demo.
- It runs at a capped 30fps, `prefers-reduced-motion` swaps to a static settled
  poster (the distribution + CI, frozen — which is arguably the more honest frame
  anyway), and it never animates while a tab is hidden.
- Off the hero and results, the field is *quiet ambient* (drift only) or absent.

### 6.2 Supporting motion principles

Governed by the frequency gate (Emil for the dense app, Jakub for marketing polish):

- **Curves:** ease-out only — `cubic-bezier(0.22, 1, 0.36, 1)` (out-quint) for
  reveals; `cubic-bezier(0.32, 0.72, 0, 1)` (mechanical) for telemetry wipes,
  tab underlines, and progress. **No bounce, no elastic, no spring overshoot** —
  an instrument does not wobble.
- **Durations:** app interactions ≤180ms; keyboard-initiated = 0ms (instant).
  Marketing reveals 400–600ms. The Population Field is the only long-running motion.
- **The "trace draw":** any line chart, CI axis, or confidence curve *draws itself*
  left-to-right on first paint via `stroke-dashoffset` over 700ms mechanical —
  the universal "instrument is taking a reading" gesture. Underdraw is a 5px /
  18%-alpha echo of the same path (phosphor persistence), never CSS glow.
- **Status pulse:** a running simulation shows one 8px signal dot with a 2s
  opacity breath — the *only* sanctioned infinite loop in the product.
- **Verdict commit:** when a run resolves, the hero number counts up (tabular,
  300ms mechanical) and the field settles in one non-looping beat. Decisive, once.

---

## 7. Three signature moves unique to Sidira

### 7.1 The Population Field (graphics showpiece — see §6.1)
A WebGL agent field where particle count = real cohort size and the emergent
histogram is the verdict. No competitor in product-research tooling renders the
*actual population* reacting in real time. It is simultaneously the marketing
hero and the live results instrument — the same shader, fed canned data on the
landing page and true data in-app, so the marketing promise and the product are
provably identical.

### 7.2 The Spread Stamp (candor as a visual primitive)
Every reading renders with its uncertainty *physically attached*: the number in
Geist Mono, a `spread`-amber CI bar beneath it, and a one-glyph **"uncalibrated"
provenance stamp** (a hollow diamond ◇ = no ground truth yet) that the user
learns to read instantly. A *graded* reading swaps to a filled diamond ◆. This
turns the product's most important honesty — "this is a sim, not a measurement" —
into a repeatable, scannable mark instead of a paragraph of disclaimer. No
analytics tool wears its own epistemic limits this proudly.

### 7.3 The Console↔Sheet inversion (meaningful theming)
The app is a dark console (live instrument); records invert to a light blueprint
sheet. Crossing from a *reading* surface to a *record* surface performs a single
120ms cross-tone transition — the screen visibly "prints" the reading onto paper.
The theme split is not decoration; it encodes the product's own
reading-vs-record ontology, so a user feels the difference between a live
estimate and an archival fact in their retina before they read a word.

---

## 8. Why this is top-0.1% for THIS product specifically

1. **The spectacle is the substance.** Most "ambitious" landing pages bolt a
   WebGL toy onto an unrelated value prop. Here the showpiece *is* the product's
   core computation — a population reacting to a change — so a sophisticated buyer
   reads it as a live demo of the instrument, not as eye candy. Credibility and
   spectacle are the same gesture.

2. **It renders honesty as a feature, not fine print.** A Kohavi-class buyer's
   first objection is "your numbers are uncalibrated." This system answers that
   *in the visual grammar*: the Spread Stamp and the dedicated uncertainty color
   mean the product never overstates. Disarming the strongest skeptic at the
   pixel level is exactly what wins a rigorous audience — and almost no tool dares
   to design its own limits this prominently.

3. **The theme split teaches the product's ontology for free.** Reading = dark
   live console; record = light blueprint sheet. The user internalizes "estimate
   vs. fact" through color temperature, which is precisely the distinction this
   product must protect. Meaning-bearing theming is rare; here it is load-bearing.

4. **Instrument typography over editorial reflex.** Geist × Geist Mono with a
   tabular-numeral law gives every number the authority of an oscilloscope readout
   — resisting the AI-default reach for warm paper + display serif, which would
   have made a measurement tool look like a magazine and quietly destroyed its
   credibility.

The result: a founder demoing this to a buyer isn't showing software. They're
showing an instrument that visibly computes human reaction and refuses to lie
about what it knows. That is the only thing that converts this audience — and no
competitor is building it.
