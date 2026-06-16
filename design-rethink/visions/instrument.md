# Sidira — Design Language: "OSCILLA"

> A clean-sheet design language. Ignores the prior paper-and-ink system entirely.
> Channels the *spirit* — not the look — of Teenage Engineering / pro-instrument:
> the app as a precise scientific instrument for reading human behavior.

---

## 0. The one-line thesis

**Sidira is an oscilloscope for human decisions** — a cold graphite instrument
whose every reading is a live phosphor trace settling toward truth, where
synthetic populations glow as measurable signal and the act of measurement is
the entire aesthetic.

---

## 1. Mood / emotional target

The feeling in the room is **a calibration lab at 2am** — quiet, exact,
slightly thrilling. Not the warm-paper bench of the old system (that read as a
notary's desk); this is the bench of someone who *measures things that move*.
The dominant emotion is **earned confidence under self-skepticism**: the
instrument is decisive enough to act on, honest enough to show its own noise
floor. Spectacle, when it appears, reads as *instrument intelligence* — the
machine is alive and watching the population react — never as decoration.

Three words: **measured · luminous · sober.**

What it must never feel like: a SaaS dashboard, a hype deck, a spinner-and-
confetti app, or warm-craft "artisan paper." It is a tool, switched on.

---

## 2. Color system

The base is **instrument graphite**, not paper. This deliberately rejects the
banned 2026 cream/sand/bone band. Warmth is forbidden in the substrate; all
life is carried by a single phosphor **Signal** accent and two cold provenance
tints. The system is **dark-primary** (instruments glow in the dark) with a
fully-specified light "datasheet" mode for long-form reading surfaces (About,
Capability detail, Persona record).

### 2.1 Core ramp — graphite (dark, primary)

| Token | oklch | hex | Role |
|---|---|---|---|
| `--bg-void` | `oklch(0.17 0.012 248)` | `#10141B` | Page substrate (the bench) |
| `--bg-panel` | `oklch(0.21 0.013 248)` | `#171C25` | Raised instrument panel |
| `--bg-well` | `oklch(0.145 0.010 248)` | `#0C0F15` | Recessed display well / scope screen |
| `--line-hair` | `oklch(0.30 0.012 248)` | `#272D38` | Hairline rules, panel seams (0.75px) |
| `--line-edge` | `oklch(0.40 0.014 248)` | `#3A424F` | Active edges, focus tracks |
| `--ink-1` | `oklch(0.93 0.008 248)` | `#E7EAEF` | Primary text |
| `--ink-2` | `oklch(0.72 0.010 248)` | `#A3AAB6` | Secondary / labels |
| `--ink-3` | `oklch(0.55 0.010 248)` | `#737B88` | Muted / provenance, ≥4.5:1 on void |

Hue 248 is a **cold blue-graphite**, not neutral grey and not warm — the tint
of anodized aluminum and CRT glass. Chroma is held ≤0.014 so it never reads
"blue," only "cold."

### 2.2 The Signal accent — phosphor

One accent. It is the live trace, the running pulse, the committed verdict.
Used on **≤6% of any view**. Never a button fill by default — it is *light*,
not paint.

| Token | oklch | hex | Role |
|---|---|---|---|
| `--signal` | `oklch(0.86 0.19 152)` | `#36E5A0` | Phosphor green — live traces, running, verdict-go |
| `--signal-dim` | `oklch(0.70 0.15 152)` | `#1FB682` | Settled / resting signal |
| `--signal-glow` | `oklch(0.86 0.19 152 / 0.18)` | — | Bloom halo behind live traces |

Phosphor green (152°) over the more obvious oscilloscope-cyan: green is the
classic P31 phosphor of lab scopes, reads unmistakably as "measurement," and
is maximally distinct from every SaaS-blue and AI-purple competitor.

### 2.3 Provenance tints — the two cold poles

These never compete with Signal. They carry **A/B arm identity** and the
encoded founder story (Sid / Avira) — invisible as story, functional as data.

| Token | oklch | hex | Role |
|---|---|---|---|
| `--arm-control` | `oklch(0.74 0.11 232)` | `#4FA8E0` | Control arm · "Sid" pole · steady blue |
| `--arm-treat` | `oklch(0.72 0.13 22)` | `#F0796B` | Treatment arm · "Avira" pole · warm signal-red |

Used only to label the two experiment arms in A/B traces and per-persona
fan-outs. Never as page chrome. A negative reaction is rendered in `--ink-2`
neutral, **never** in `--arm-treat` red — harm is information, not alarm.

### 2.4 Status — borders and words, never fills

Severity rides hairline borders + wording, echoing the old system's discipline
but in graphite. No semantic background fills.

| Token | hex | Role |
|---|---|---|
| `--edge-warn` | `#C9A227` | Caution border (uncalibrated, placeholder, starter-pack) |
| `--edge-ok` | `--signal-dim` | Validated / real-data border |

### 2.5 Light "datasheet" mode (long-form reading surfaces only)

For record-voice pages where reading prose for minutes matters (About, Product
PRD body, Capability detail, Persona pack record). Cold off-white, **chroma 0
toward the instrument hue**, never warm.

| Token | oklch | hex |
|---|---|---|
| `--ds-bg` | `oklch(0.975 0.003 248)` | `#F3F5F7` |
| `--ds-panel` | `oklch(1 0 0)` | `#FFFFFF` |
| `--ds-ink-1` | `oklch(0.22 0.012 248)` | `#1B2029` |
| `--ds-ink-2` | `oklch(0.46 0.012 248)` | `#5C6470` |
| `--ds-hair` | `oklch(0.90 0.006 248)` | `#DCE0E4` |
| `--signal` (on light) | `oklch(0.62 0.16 152)` | `#11A06E` (darkened for AA on white) |

Mode is **locked per route**, never inverts mid-scroll. Instrument routes
(simulations, results, transcript, builder, crawl setup) = graphite dark.
Record routes (about, capability, persona record, product PRD) = datasheet
light. Marketing landing = graphite dark (the scope, switched on).

---

## 3. Typography

Three roles, paired on a true contrast axis (grotesk + mono + a single tabular
data face), all Google-Fonts-available. No serif — serif on a measurement
instrument is a costume.

### 3.1 Families

| Role | Family | Why |
|---|---|---|
| Display / headline | **Space Grotesk** (500/700) | Engineered grotesk with the slightly-mechanical `a`/`g`; reads as instrument-panel silkscreen, not SaaS-Inter. Distinct, not Geist-default. |
| Body / prose | **Inter Tight** (400/500) | Tight, neutral, long-form legible for PRD/record bodies; the workhorse that disappears so the data speaks. |
| Mono / data / labels | **JetBrains Mono** (400/500/700) | Tabular numerals, the readout face. ALL numbers, all designators (run ids, seeds, snapshot ids, screen/component ids, role chips), all uppercase micro-labels. |

Pairing rationale: Space Grotesk (geometric-mechanical) × Inter Tight
(humanist-neutral) × JetBrains Mono (terminal) sit on three distinct axes —
the skill's anti-pattern (two-similar-sans) is avoided by construction.

### 3.2 Type scale (dark instrument; rem on 16px root)

| Token | size / line / tracking | Use |
|---|---|---|
| `display-xl` | `clamp(2.6rem, 5vw, 4.5rem)` / 0.98 / -0.03em | Landing hero only |
| `display` | `2.25rem` / 1.04 / -0.025em | Page heroes |
| `h1` | `1.625rem` / 1.12 / -0.02em | Section / record title |
| `h2` | `1.25rem` / 1.18 / -0.015em | Subsection |
| `h3` | `1.0rem` / 1.3 / -0.01em | Card / group head |
| `body` | `0.9375rem` / 1.6 / 0 | UI text |
| `prose` | `1.0625rem` / 1.72 / 0 | Long-form PRD / record (max 68ch) |
| `label` | `0.6875rem` / 1.2 / **+0.14em** uppercase mono | Micro-labels, eyebrows (rationed) |
| `data-lg` | `2rem` / 1 / 0 mono **tnum** | Hero readings (agreement score, lift) |
| `data` | `0.875rem` / 1.4 / 0 mono **tnum** | All inline numbers, table cells |

`font-variant-numeric: tabular-nums` is global on every numeric and mono
element — numbers must not jitter as a trace updates. `text-wrap: balance` on
h1–h3; `text-wrap: pretty` on prose.

**Eyebrow discipline:** the mono `label` is the *instrument silkscreen* — it is
allowed on panels as a functional designator (a real legend: `CH1 · TREATMENT`,
`n=240 · seed 0x1f`), NOT as a decorative kicker above every section. Max one
decorative eyebrow per three sections; functional panel legends are unlimited
because they label real channels.

---

## 4. Spatial system

Density philosophy: **two densities, one grid.** Instrument surfaces run dense
(a cockpit reads more, faster); record surfaces run airy (prose breathes). The
8px base unit and 12-col grid are shared so the two never feel like different
apps.

### 4.1 Grid & rhythm

- Base unit **8px**; half-step 4px allowed for instrument density only.
- Spacing scale: `4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 · 96 · 128`.
- 12-column grid, **88px max gutter**, content max-width `1320px` (instrument)
  / `720px` reading column (record prose).
- Instrument panels snap to an **even 8px module grid** with hairline seams —
  the "rack-unit" feel. Record sheets float on generous 64–96px vertical rhythm.

### 4.2 Radius — the instrument tell

A tight, two-value radius scale. Instruments have *milled* corners, not soft
SaaS pills.

| Token | value | Use |
|---|---|---|
| `--r-panel` | `3px` | Panels, cards, inputs, the screen well |
| `--r-control` | `2px` | Buttons, chips, toggles |
| `--r-screen` | `5px` | The scope display well only (the one "lens") |

No pills. No `border-radius: 9999`. The whole product reads at radius 2–3.

### 4.3 Borders, elevation, material

- Default separation is the **0.75px hairline** (`--line-hair`), not shadow.
- Elevation is conveyed by *recession* (the well is darker) and a single
  1px top inner-highlight (`inset 0 1px 0 oklch(1 0 0 / 0.04)`) that mimics a
  milled metal lip catching light. No tinted-black drop shadows.
- **Glass is reserved for live computed readings only** (the scope screen, a
  settling trace panel) — never resting chrome. This honors the deepest truth
  of the brief: glass = a live reading, paper/graphite = a record.

---

## 5. Motion + effects principles

> Motion law: **everything either settles or stays still.** A reading *settles*
> (a trace converges, a number counts to rest). A record *is still*. There is no
> third motion. Nothing loops for decoration. Reduced-motion replaces every
> settle with an instant cut to the rest state.

Easing: `--ease-settle: cubic-bezier(0.16, 1, 0.3, 1)` (ease-out-expo) for all
convergence. Durations: 180ms instrument feedback, 420ms trace settle, 900ms
the one hero showpiece. No bounce, no elastic, ever — an instrument that
overshoots is broken.

### 5.1 THE SIGNATURE GRAPHICS LAYER — "The Trace"

**What it is:** a live oscilloscope/spectrometer trace that *is* the data, not a
chart of it. Wherever a Sidira reading exists, it is drawn as a phosphor
waveform on the dark well: agreement scores, A/B lift, confidence convergence,
per-persona sentiment all render as glowing traces that **settle from noise to
signal** when a result resolves.

**Where it lives:**
- Landing hero (the showpiece) — a full-bleed background trace field.
- Simulation results — the verdict is a settling trace, not a gauge.
- Hypothesis builder live manifest — a faint "pre-trace" baseline that
  responds to config changes (cohort size widens the band, A/B splits it into
  two channels: blue control + red treatment).
- Persona pack / library — population shown as a stacked spectral histogram.

**The tech (tiered, degrades gracefully):**
1. **WebGL (`regl` / raw GLSL)** for the landing hero and the results well:
   a fragment shader draws the trace with real phosphor bloom (gaussian glow),
   a subtle scanline/grain, and a noise-to-signal "lock" animation on resolve.
   Population density renders as instanced points in a vertex shader — up to
   ~2,000 synthetic agents as a luminous swarm, each a real cohort member.
2. **Canvas 2D** fallback for mid surfaces (manifest, histograms): same trace
   math, no bloom, drawn with `lineWidth` + `shadowBlur` for a cheap glow.
3. **SVG `<path>` + CSS** for record/datasheet contexts and reduced-motion:
   a static, already-settled trace. Crisp, printable, no motion.

The same trace *math* (a value series → polyline with a noise envelope) feeds
all three tiers, so the instrument's signature is identical whether it's a
shader or a static SVG.

**How it stays tasteful (the one rule, enforced):** the trace only ever draws
**real reading data or an honest baseline** — never decorative noise pretending
to be data. Bloom is held at ≤18% opacity. The swarm is monochrome phosphor on
graphite (one color), so 2,000 points read as *one population's signal*, not a
rainbow particle toy. On record surfaces it freezes to a flat SVG. If a reading
is uncalibrated, the trace is drawn with a visible dashed **noise-floor** line
underneath it — the spectacle literally shows its own uncertainty.

### 5.2 The aperture lock (micro-signature)

Inherited *spirit* only: the camera-diaphragm mark performs a single
**non-looping aperture-close** the instant a verdict commits — blades sweep
shut over the verdict number, then snap open revealing it settled. 900ms, once,
on commit. This is the product's one "wow" beat and it is rationed to exactly
the moment a decision is made.

### 5.3 Tactile controls

Buttons/toggles depress `translate-y-[1px]` + the inner highlight dims on
`:active` (a physical key press). Range inputs (sample size, cohort) are styled
as **instrument sliders** with a tnum readout that settles. Focus is a 2px
`--line-edge` track, not a glow.

---

## 6. Three signature moves (unique to Sidira)

### Move 1 — The Settling Trace (graphics showpiece)
The verdict/score is never a static number dropped on screen. It **locks**: the
well shows phosphor noise, then the shader converges the trace to the measured
value while the number counts up through `tnum` digits, ending with a soft
bloom and a dashed noise-floor beneath it. You don't *read* the result, you
*watch the instrument resolve it.* No competitor renders a result as a live
measurement — they all show gauges, bars, and confetti.

### Move 2 — The Cohort Swarm
A persona pack / cohort is rendered as a **luminous point-field** in WebGL:
every synthetic agent is one phosphor point, positioned by its behavioral
embedding. On the results page the swarm visibly **splits and drifts** into
control (blue) and treatment (red) clusters as the A/B reads out — you watch the
population disagree. Hovering a region pulls those agents' transcripts. The
abstract "synthetic population" becomes a thing you can see reacting.

### Move 3 — The Channel Legend
Every reading surface carries a real **instrument legend** (mono silkscreen):
`CH1 CONTROL · n=240 · seed 0x1f · model groq/llama · UNCALIBRATED`. It is the
provenance line reimagined as a scope's channel readout — always present,
always honest, encoding seed/model/sample/calibration as functional silkscreen
rather than a buried footnote. It makes "this is a raw, uncalibrated reading"
structurally unavoidable, turning the brief's honesty mandate into a signature
visual element.

---

## 7. Why this is top-0.1% for *this* product

1. **The aesthetic IS the value prop.** Sidira's core truth is "we measure how
   humans will react before you build." An oscilloscope-graphite instrument with
   a live settling trace makes that truth *visible and visceral* — the
   spectacle reads as measurement intelligence, exactly the brief's one rule.
2. **It escapes both AI traps the skills flag.** It refuses warm cream/paper
   (first-order reflex) AND refuses the obvious "editorial-typographic" pivot
   (second-order reflex). Cold phosphor-on-graphite with a shader trace is a
   third thing — distinct from every SaaS-blue, AI-purple, and warm-craft
   competitor on the board.
3. **Honesty is built into the graphics, not bolted on.** The noise-floor line,
   the channel legend, and the "uncalibrated" silkscreen make self-skepticism a
   structural visual element — the page can't show a reading without showing its
   limits. That is the single hardest thing this product must do, solved in the
   design language itself.
4. **One trace-math engine, three render tiers** means the signature survives
   from a 2,000-point WebGL hero down to a printable static SVG on a record
   page — coherent, performant, accessible, reduced-motion-safe. Ambition with
   an engineering spine, which is exactly the disposition a founder pitching
   sophisticated buyers needs the instrument to project.
