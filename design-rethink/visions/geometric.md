# Sidira — Design Vision: **GRAPHITE**

> A clean-sheet design language. Channels the spirit of Vercel/geometric monochrome —
> stark high-contrast, geometric precision, dramatic dark mode, developer-grade
> capability — bent toward Sidira's one truth: *a rigorous instrument that
> simulates human behavior, and reports it honestly.*

---

## 1. Design thesis (one line)

**Pure black, pure white, one wavelength of green — a measurement instrument rendered as code: every pixel is either signal or silence, and the only color is the reading.**

---

## 2. Mood / emotional target

The feeling is the cold, exhilarating confidence of opening an oscilloscope that
just locked onto a clean trace. Not warm. Not friendly. **Capable.** The visitor —
a founder pitching Kohavi-class buyers — should feel they've found the tool the
serious people use: monochrome to the point of severity, geometric to the point of
machined, and so honest about its own limits that the honesty itself reads as
authority. Where the old paper-and-ink language whispered *"archival record,"*
GRAPHITE states *"live instrument, powered on, under load."* The emotional arc per
surface:

- **Marketing** → *awe at precision.* A designer stops scrolling because the hero is a living simulation, not a screenshot.
- **App** → *earned, sober trust.* The instrument never lies, never spins a fake loader, never paints a verdict it can't back.
- **The shared signature** → *intelligence as restraint.* Spectacle is rationed; when the green fires, it means something.

---

## 3. Color system (exact values, light + dark)

GRAPHITE is **dark-primary**. The app and all instrument surfaces live in the dark.
Marketing offers a light "spec-sheet" inverse for cold-visitor legibility, but the
brand's resting state is near-black. One accent only: **Reticle Green** — a single
narrow-band wavelength, never gradient, never a second hue.

### 3.1 Core ramp (oklch + hex)

| Token | oklch | hex | Role |
|---|---|---|---|
| `--void` | `oklch(0.145 0 0)` | `#0A0A0A` | App background. Pure neutral black, chroma 0. |
| `--surface` | `oklch(0.185 0 0)` | `#161616` | Raised panels, cards, the instrument bench. |
| `--surface-2` | `oklch(0.225 0 0)` | `#1F1F1F` | Wells, inputs, recessed code/data fields. |
| `--line` | `oklch(0.30 0 0)` | `#333333` | Hairline rules, 1px borders (the grid). |
| `--line-bright` | `oklch(0.42 0 0)` | `#4D4D4D` | Hover borders, active dividers. |
| `--ink-3` | `oklch(0.58 0 0)` | `#7A7A7A` | Muted labels, mono designators, captions. |
| `--ink-2` | `oklch(0.78 0 0)` | `#BFBFBF` | Body text, secondary prose. |
| `--ink-1` | `oklch(0.985 0 0)` | `#FAFAFA` | Headlines, primary numerals, max contrast. |

Pure neutral grayscale on purpose — chroma is **0** across the entire structural
ramp. Any color you see is a *reading*, never chrome. This is the discipline that
separates GRAPHITE from "dark SaaS": the gray is dead-neutral machined aluminum,
not blue-black "tech" tint.

### 3.2 The one accent — Reticle Green

| Token | oklch | hex | Role |
|---|---|---|---|
| `--signal` | `oklch(0.87 0.21 145)` | `#3DF07A`→ tuned to `#34E26F` | The reading. Live traces, verdict-positive, active pulse, focus ring. |
| `--signal-dim` | `oklch(0.72 0.15 145)` | `#28B459` | Signal on light surfaces, AA-safe on void. |
| `--signal-trace` | `signal @ 0.14 alpha` | — | Grid glow, trace afterimage, hover wash. |

**Saturation discipline:** one hue (145°, true green, not teal not lime-yellow),
appearing on < 6% of any screen's pixels. It is the oscilloscope phosphor. It is
*the measurement*. It never decorates a button just to be lively.

### 3.3 Honest-disclosure tones (NOT semantic color)

Sidira's product truth: *every reading is uncalibrated; a negative reaction is
neutral information, not a red alarm.* So GRAPHITE refuses the green-good/red-bad
reflex. State rides **wording, weight, and hairline**, not hue.

| Token | hex | Strict rule |
|---|---|---|
| `--caution` | `#E0A030` (amber) | Border + label only. Used for "placeholder / ungraded / uncalibrated" provenance flags. NEVER fills a region. |
| `--negative` | `--ink-2` (gray) | A "don't-ship" verdict or negative reaction renders in **neutral gray**, never red. The word carries it. |
| `--critical` | `#E5484D` | Reserved for true system failure (crawl error, run crashed) — never for a simulation *result*. |

### 3.4 Light "spec-sheet" inverse (marketing legibility only)

For cold visitors on `/`, `/about`, `/product` a light mode exists so the value
prop reads in daylight. It is a *plotter on white paper*, not warm paper.

| Token | hex | Role |
|---|---|---|
| `--paper` | `#FCFCFC` | Off-white, chroma 0. Not cream. Not beige. |
| `--paper-line` | `#E4E4E4` | Hairline grid. |
| `--paper-ink` | `#0A0A0A` | Text — full black on near-white, max contrast. |
| `--signal` (light) | `#1FA64E` (`--signal-dim`) | Same green, darkened to hold AA on white. |

Marketing pages may switch void↔paper **once**, as a deliberate composition
(see Signature #2). The app never goes light.

---

## 4. Typography

A two-axis pairing on a true contrast axis (grotesque + mono), plus a numeric
discipline. No serif anywhere — this is an instrument, not a manuscript.

### 4.1 Families (all Google-Fonts-available)

| Role | Family | Why |
|---|---|---|
| **Display / Headlines** | **Space Grotesk** (700 / 500) | Mechanical, slightly engineered grotesque with the squared terminals of measuring equipment. Reads "calibrated," not "friendly Inter." |
| **Body / UI** | **Inter Tight** (400 / 500 / 600) | Tight, neutral, ruthless legibility at small sizes. The workhorse for prose and labels. |
| **Mono / Designators / Data** | **JetBrains Mono** (400 / 500) | All numerals, IDs, provenance lines, code, the live-manifest. Tabular by default. This is where the "developer-grade" credibility lives. |

The pairing contrast: Space Grotesk (geometric display) vs Inter Tight (humanist-leaning
neutral body) vs JetBrains Mono (the machine voice). Three clearly distinct registers,
each with a job: *Grotesk states, Inter explains, Mono measures.*

### 4.2 Type scale (1.250 major-third, clamped fluid)

| Step | clamp() | weight / tracking | Use |
|---|---|---|---|
| Display | `clamp(2.75rem, 6vw, 5.5rem)` | 700 / `-0.03em` | Marketing hero only (ceiling 88px, never shouts) |
| H1 | `clamp(2rem, 4vw, 3rem)` | 700 / `-0.025em` | Page titles |
| H2 | `1.75rem` | 600 / `-0.02em` | Section heads |
| H3 | `1.25rem` | 600 / `-0.015em` | Sub-sections, card titles |
| Body-L | `1.125rem` | 400 / `0` · 1.6 leading | Long-form PRD prose, About narrative |
| Body | `0.9375rem` (15px) | 400 / `0` · 1.55 leading | Default UI / app body |
| Mono-data | `0.875rem` | 500 / `0` · tnum | Numerals, scores, CIs, deltas |
| Designator | `0.6875rem` (11px) | 500 / `0.12em` UPPERCASE | Mono micro-labels, role/screen IDs, provenance eyebrows |

**Eyebrow discipline:** the mono uppercase designator is a *real brand system element*
(provenance lines, persona IDs, arm tags, snapshot stamps) — but it is rationed:
max one per ~3 sections on marketing, and in-app it appears only where it labels a
true identifier (`SNAPSHOT 2026-W25`, `arm=treatment`, `cr-924718699c21`). Never a
decorative kicker over every heading.

**Numerals are sacred.** Every score, confidence interval, agreement %, lift, cohort
size, timestamp, and seed is JetBrains Mono with `font-variant-numeric: tabular-nums`.
Numbers in this product are evidence; they align in columns like a lab readout.

---

## 5. Spatial system

### 5.1 The grid — *the reticle*

GRAPHITE's structure is a literal **measurement grid**. An 8px base unit, and the
signature device: a faint 1px graticule (`--line` at very low alpha) optionally
underlying instrument surfaces, like graph paper behind a plotted trace. Content
columns: 12-col, `max-width: 1280px` for app, `1120px` for reading-heavy marketing
prose (65–75ch caps on body).

### 5.2 Spacing scale (8px base, geometric)

`4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 · 96 · 128`

Density philosophy: **two densities, hard-separated.**
- **Instrument density (app):** tight, technical, cockpit-adjacent. 12–16px rhythm, hairline-divided rows over cards, data breathing in plain `divide-y` tables, not boxes. `VISUAL_DENSITY ≈ 6`.
- **Statement density (marketing):** airy, gallery, one idea per viewport. 64–128px section rhythm. `VISUAL_DENSITY ≈ 3`.

### 5.3 Radius — *machined, not rounded*

| Token | value | Use |
|---|---|---|
| `--r-sharp` | `0px` | Hairline rules, dividers, the grid, tables. |
| `--r` | `2px` | Default — cards, inputs, panels. Barely-there bevel of a machined edge. |
| `--r-chip` | `3px` | Chips, tags, designator pills. |
| `--r-pill` | `9999px` | The live-status dot/pulse ONLY. Nothing else is pill. |

Radius lock: the system is **all-sharp-to-2px**. Soft 12–16px "friendly SaaS"
corners are banned. A 2px radius reads as a precision-cut panel; a 16px radius reads
as a consumer app. We are not a consumer app.

### 5.4 Borders over shadows

Elevation is communicated by **hairline borders and surface-value steps**, almost
never by drop shadow (shadows are invisible on `#0A0A0A` anyway and read as fake
depth). The one sanctioned glow: `--signal` at low alpha around a *live* element.

---

## 6. Motion + Effects — the signature graphics layer

### 6.1 Name: **THE TRACE LAYER**

The signature effects system is **The Trace** — a real-time oscilloscope/phosphor
metaphor rendered in WebGL (with a hard CSS/SVG fallback). It is the visual
embodiment of "we simulate human behavior and plot the result." It lives in exactly
three places and nowhere else:

1. **Marketing hero** (`/`) — full Trace, the showpiece (see Signature #1).
2. **Live computing states** (app) — a contained Trace strip while a run/crawl/persona-build is in flight.
3. **The verdict-settle beat** — a single non-looping trace lock when a reading commits.

**The tech:** a GPU particle/line field (`regl` or raw WebGL2, ~8k points) where
each particle is a synthetic agent. At rest they drift on a faint lattice (the
population). Under "load," they organize into a plotted waveform — a confidence
trace settling toward a value — phosphor-green on void, with a subtle bloom and a
1–2 frame afterimage decay so it reads like a real CRT, not a chart animation. The
trace *settles* (damped, never bounces) onto its final reading and holds.

**How it stays tasteful (the rules that make spectacle read as intelligence):**
- **Monochrome substrate.** The field is gray; only the *active trace* is green. Spectacle never becomes a rainbow.
- **Motivated, always.** Every Trace instance maps to a real product event: agents reacting, confidence converging, a verdict locking. It never animates "to look alive." If there's no computation, the Trace is still.
- **Rationed.** Max one Trace showpiece per page. The app uses a *reduced* Trace (a single settling line, not the full field).
- **Honest.** When data is uncalibrated/placeholder, the Trace renders **dim and unlocked** (drifting, never settling) — the motion itself tells the truth about trust.
- **`prefers-reduced-motion`:** the Trace freezes to a single static plotted frame (the final settled trace as an SVG), fully legible, zero motion. Never blank.
- **Performance:** WebGL on its own layer, `will-change` isolated, paused when offscreen / tab hidden, capped at the device refresh. Mobile gets the static SVG frame by default.

### 6.2 Motion principles (Emil-weighted: this is a productivity instrument)

- **Durations:** UI micro-interactions 120–180ms; reveals 400–600ms; the verdict-settle beat 800ms (the one indulgence). Keyboard-initiated transitions: instant, never animated.
- **Easing:** `--ease-mech: cubic-bezier(0.32, 0.72, 0, 1)` for wipes, underlines, panel slides (a mechanical decel). `--ease-settle: cubic-bezier(0.16, 1, 0.3, 1)` for the trace lock. **No bounce, no elastic, ever** — an instrument does not spring.
- **The frequency gate is law.** The simulations table, the composer, the agent chat — all frequent surfaces — get near-zero motion. Delight is spent on the rare moments: first crawl publishing, a verdict committing, the hero. 
- **No fake loaders.** Honest mono text (`READING · 0.6s` / `WALKING capability 3 of 6`) and the live Trace strip — never a generic spinner. This is both a DESIGN.md product law and a brand differentiator.
- **Tactile feedback:** buttons `:active` translate-y -1px; focus rings are `--signal` 2px, always visible.

### 6.3 Hover / interaction texture

- **The graticule wake.** On instrument surfaces, hovering a row lights the underlying grid cell faintly (`--signal-trace` wash + `--line-bright` border) — as if the cursor is a probe touching the bench. Subtle, 120ms, no layout shift.
- **Mono link hover:** dotted-underline → solid, in `--ease-mech`.
- **Designator chips** get a 1px border brighten on hover; never scale.

---

## 7. Three signature moves (unique to Sidira)

### Signature #1 — **The Living Population Hero** *(graphics showpiece)*

The marketing hero is a WebGL field of ~8,000 points: the synthetic population at
rest, drifting on a dark lattice in neutral gray. As the page loads, a headline
hypothesis types in mono (*"Will removing the paywall lift retention?"*) and the
field **reacts in real time** — points migrate, cluster into treatment/control arms,
and a phosphor-green confidence trace draws itself across the field and **settles**
onto a verdict readout (`AGREEMENT 0.78 · LIFT +3.6pp`). The whole thing is a
30-second loop of *the actual product running*, not a screenshot, not a gradient
blob. Scroll-scrubbing lets the visitor drag the simulation forward/back. This is
the "designer stops scrolling" moment, and it is *literally the product's core
truth* rendered as art — simulation made visible. No competitor (UserTesting,
Sprig, dscout, Maze) has anything like a live agent-field; they show dashboards.

### Signature #2 — **The Inversion (spec-sheet flip)**

A single, deliberate void→paper inversion as a scroll composition on marketing. The
dark "instrument powered on" hero gives way — *once* — to a stark white **spec sheet**:
the product's claims set in mono on white like a datasheet / lab exhibit (provenance,
method, what-it-is, what-it-isn't). The inversion dramatizes Sidira's two modes —
*reading* (dark, live, green) and *record* (light, static, exact) — which is the
literal architecture of the product. The flip is choreographed with a clip-path wipe
on `--ease-mech`, so it reads as an instrument switching display modes, not a theme
glitch. One flip per page, never random alternation.

### Signature #3 — **The Aperture Reticle** *(brand geometry as system primitive)*

Sidira's six-blade camera-diaphragm mark becomes the system's structural primitive,
not just a logo. (a) **The verdict-commit beat:** when a simulation verdict locks,
the aperture *closes* once — six green blades sweeping to the hexagonal center — a
non-looping 800ms settle that says "measurement captured." (b) **Loading states**
use a single rotating aperture blade as the honest progress indicator (replacing
any spinner). (c) **The graticule** behind instrument surfaces echoes the mark's
hexagonal geometry at low alpha — a faint reticle, so even the empty bench feels
calibrated. The aperture is the through-line: it appears as identity, as the moment
of commitment, and as the ambient grid — one geometric idea, three scales.

---

## 8. Why this is top-0.1% for *this* product specifically

Sidira's job is to make a founder *believe an uncalibrated simulation enough to act
on it, while never being lied to.* That is a razor's-edge trust problem, and GRAPHITE
is engineered for exactly it:

1. **The aesthetic IS the argument.** "Developer-grade monochrome instrument" is not
   a borrowed Vercel look — it's the most credible possible costume for a measurement
   tool sold to Kohavi-class buyers who distrust hype. Stripping all color except one
   green wavelength *is* the message: we measure, we don't decorate.

2. **The honesty engine is built into the visual grammar.** Negative verdicts in
   gray (never red), placeholder data as a dim *unlocked* trace, no fake spinners,
   provenance in unmissable mono — the design refuses to overstate, which is the one
   thing that would kill trust in an uncalibrated instrument. Competitors paint
   confident green checkmarks; GRAPHITE's restraint is the credibility.

3. **The showpiece is the product, not a metaphor for it.** The Trace Layer renders
   the *actual mechanism* — a population of agents reacting and a confidence interval
   settling. Spectacle and substance are the same object. A designer stops scrolling;
   a buyer simultaneously understands what the thing does. That collapse of "wow" and
   "I get it" into one frame is the rare top-0.1% move — and it's only possible
   because Sidira's core truth is, itself, visually extraordinary: *simulated humans,
   plotted live.*

4. **One language, two densities, honestly partitioned.** Marketing gets the
   gallery-airy statement mode and the showpiece; the app gets cockpit-tight
   instrument density with near-zero motion on frequent surfaces. Same tokens, same
   green, same geometry — so the cold visitor and the daily power-user feel one
   coherent instrument, calibrated to two jobs.

---

## 9. Token quick-reference (implementation seed)

```css
:root {
  /* structure — chroma 0, machined gray */
  --void:#0A0A0A; --surface:#161616; --surface-2:#1F1F1F;
  --line:#333; --line-bright:#4D4D4D;
  --ink-3:#7A7A7A; --ink-2:#BFBFBF; --ink-1:#FAFAFA;
  /* the one reading */
  --signal:#34E26F; --signal-dim:#28B459; --signal-trace:rgba(52,226,111,.14);
  /* honest disclosure — not semantic */
  --caution:#E0A030; --critical:#E5484D;
  /* geometry */
  --r:2px; --r-chip:3px; --r-pill:9999px;
  /* motion */
  --ease-mech:cubic-bezier(.32,.72,0,1);
  --ease-settle:cubic-bezier(.16,1,.3,1);
  /* type */
  --font-display:"Space Grotesk",sans-serif;
  --font-body:"Inter Tight",sans-serif;
  --font-mono:"JetBrains Mono",ui-monospace,monospace;
}
.light { --void:#FCFCFC; --line:#E4E4E4; --ink-1:#0A0A0A; --signal:#1FA64E; }
```

**The one rule for everyone who builds in GRAPHITE:** the gray is structure, the
green is the reading. If you're reaching for a second color, you're decorating —
stop, and let the measurement be the only thing that glows.
