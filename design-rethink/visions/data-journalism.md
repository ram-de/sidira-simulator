# Sidira — Design Vision: "THE READING"

> Direction channeled (not cloned): FT / The Pudding data-journalism editorial.
> Charts and evidence ARE the design. Bold numbers, annotation, a narrative that
> makes complex behavioral data feel inevitable and clear.

---

## 1. Design thesis (one line)

**Every screen is a published broadsheet of an experiment-in-progress: the
distribution is the hero, the number is the headline, the annotation is the
journalism — Sidira doesn't show you a verdict, it shows you the reading and
lets the data argue its own case.**

---

## 2. Mood / emotional target

The feeling of opening the *Financial Times* on the morning a market moved, and
finding a single chart that explains everything before you've read a word — then
realizing a serious person annotated it for you, by hand, in the margin.

- **Authoritative, not loud.** The page has the calm of a printed page of
  record. It earns trust by being legible and exact, never by being slick.
- **Evidentiary.** Numbers feel weighed, sourced, and provenanced — every figure
  carries where-it-came-from the way a journalist carries a byline.
- **Inevitable.** Good data journalism makes a complex finding feel obvious in
  hindsight. The cohort's reaction should land as "of course" — the distribution
  was always going to say that; we just rendered it honestly.
- **Self-skeptical.** The instrument discloses its own limits in plain ink. An
  uncalibrated reading is labeled uncalibrated, in the margin, in the same voice
  that delivers the headline. Confidence through candor.

Target reaction from a founder pitching a Kohavi-class buyer: *"These people
report on customer behavior the way a great desk reports on markets. I want my
bets read this way before I build them."*

---

## 3. COLOR system

The world is **newsprint** — a warm, near-white press stock — overprinted with
**ink** and a **two-ink experiment palette** (control vs. treatment) plus one
**signal** ink that means "live / measured-now." Dark mode is the **photo-desk
proof**: a deep slate plate where the same charts glow as if backlit on a
lightbox.

### 3.1 Light ("Morning edition") — default

| Role | Hex | OKLCH | Use |
| --- | --- | --- | --- |
| `paper` | `#F5F0E6` | `oklch(0.953 0.018 86)` | page ground — warm press stock |
| `paper-2` | `#EFE8DA` | `oklch(0.922 0.022 86)` | recessed wells, table zebra, inline-code tint |
| `sheet` | `#FBF8F1` | `oklch(0.978 0.010 86)` | elevated record cards (hairline + 2–4px radius) |
| `ink` | `#16202E` | `oklch(0.255 0.028 248)` | primary type, rules, axes |
| `ink-2` | `#46505E` | `oklch(0.470 0.020 248)` | secondary type, captions (≥4.5:1 on paper) |
| `ink-3` | `#6B7480` | `oklch(0.585 0.016 248)` | annotation hands, axis ticks (large/UI only) |
| `rule` | `#D6CDBC` | `oklch(0.860 0.018 86)` | hairline rules (0.75px) |
| `control` | `#2C5E8C` | `oklch(0.480 0.090 248)` | the A arm / baseline series — "Sid-blue" lineage |
| `treatment` | `#B23A5E` | `oklch(0.520 0.140 5)` | the B arm / proposed change — "Avira-rose" lineage |
| `signal` | `#5BD37A` → ink `#1E7A3C` | fill `oklch(0.805 0.165 150)` / text `oklch(0.520 0.130 150)` | live/measured-now only; never for "good" |
| `flag` | `#C2541E` | `oklch(0.580 0.140 48)` | caution / uncalibrated stamp ink (border + word, never fill) |

**Iron rule (kept from the product's DNA, sharpened):** color encodes
**identity and provenance, not valence.** `control`/`treatment` name *which arm*.
`signal` means *this is a live reading right now*. A negative cohort reaction is
rendered in plain `ink` — it is information, not an alarm. Green never means
"good"; red never means "bad." This is the single discipline that separates an
instrument from a dashboard.

### 3.2 Dark ("Lightbox proof")

| Role | Hex | OKLCH |
| --- | --- | --- |
| `plate` | `#0C141E` | `oklch(0.190 0.022 248)` |
| `plate-2` | `#121C28` | `oklch(0.228 0.024 248)` |
| `sheet` | `#16212E` | `oklch(0.262 0.026 248)` |
| `ink` (inverts to light) | `#ECE4D6` | `oklch(0.918 0.020 86)` |
| `ink-2` | `#A7AEB8` | `oklch(0.745 0.014 248)` |
| `rule` | `#2A3644` | `oklch(0.330 0.022 248)` |
| `control` | `#69A8DE` | `oklch(0.720 0.090 248)` |
| `treatment` | `#E58AA6` | `oklch(0.760 0.110 5)` |
| `signal` | `#6FE08C` | `oklch(0.835 0.160 150)` |
| `flag` | `#E8916A` | `oklch(0.760 0.130 48)` |

Dark is reserved for the **live computed surfaces** (simulation results streaming,
agent transcript, the running-carrier glow) — the "glass display" of the
instrument. Marketing and record/library pages stay on paper. One theme per
surface; the app never inverts mid-scroll. The boundary between paper-record and
plate-reading is itself a designed seam (a hairline + a mono provenance strip),
not an accident.

### 3.3 Series scale (for distributions / multi-cohort charts)

When more than two series appear (per-persona reactions), extend from the two
arm-inks along a **single perceptual ramp**, never a rainbow:
`#2C5E8C → #4E7BA0 → #7E93A6 → #A87E86 → #B23A5E` (control→treatment bridge,
ΔE-even in OKLCH). Cohorts read as a spectrum between the two arms — visually
encoding "this persona leans toward the control / treatment reaction."

---

## 4. TYPOGRAPHY

Three voices, each doing one job — the data-journalism masthead trinity.

### 4.1 Families (all Google-Fonts-available)

| Role | Family | Why |
| --- | --- | --- |
| **Masthead / display** | **Fraunces** (opsz 9–144, wght 300–900, soft + "Wonky" axes off) | A contemporary "old-style" with optical-size; at display it has the engraved, newspaper-masthead authority of a Tiempos/Canela without the cliché. Carries the headline-number. |
| **Editorial body / prose** | **Newsreader** (Production Type, on Google Fonts) | Purpose-built screen text-serif for *reading* — the reverse-PRD, the persona dossiers, the About narrative. Newspaper warmth, screen-legible at 17px. |
| **Interface / labels / UI** | **Inter** (or **Geist** where shipped) | The neutral signage of the instrument: nav, buttons, form labels, chips. Quiet on purpose — the serifs carry personality, the sans carries the controls. |
| **Data / designators / provenance** | **IBM Plex Mono** | Tabular numerals, axis labels, snapshot ids, seed/model provenance, agent labels `[A3]`, mono micro-labels. The "lab-notebook" hand. |

Pairing logic is a true contrast axis (old-style serif display + screen-serif
body + grotesque sans UI + mono data) — four families, four jobs, zero overlap.
This is the masthead/byline/caption/dateline structure of a real newspaper page
mapped onto a product.

> Note on lineage: the product's prior system used Archivo Narrow for the
> `SIDIRA` wordmark. The wordmark itself is **preserved unchanged** (brand asset,
> §brand). Everything else is rebuilt from this clean sheet.

### 4.2 Type scale (fluid, 1.250 major-third base, display jumps to 1.333)

| Token | clamp() | Family / weight | Role |
| --- | --- | --- | --- |
| `headline-number` | `clamp(3.5rem, 9vw, 7rem)` | Fraunces 460, opsz 144, `-0.025em`, `tnum` | THE number — agreement score, lift, sample size. The masthead figure. |
| `display-1` | `clamp(2.75rem, 6vw, 5rem)` | Fraunces 420, `-0.02em` | hero / page headlines |
| `display-2` | `clamp(2rem, 4vw, 3.25rem)` | Fraunces 440, `-0.015em` | section heads, persona names |
| `title` | `1.5rem / 2rem` | Fraunces 500 | card titles, capability names |
| `lede` | `1.375rem`, lh `1.55` | Newsreader 400 | the standfirst paragraph under a headline |
| `body` | `1.0625rem (17px)`, lh `1.7`, `max-width: 68ch` | Newsreader 400 | long-form prose — reverse-PRD, dossiers, About |
| `body-ui` | `0.9375rem (15px)`, lh `1.55` | Inter 400 | app body, table cells |
| `label` | `0.75rem`, `+0.02em` | Inter 600 | form labels, buttons |
| `designator` | `0.6875rem (11px)`, `+0.09em`, uppercase | Plex Mono 500 | provenance, ids, axis labels, status words |
| `data-figure` | `tnum` everywhere numbers tabulate | Plex Mono 440 | every column of numbers, every metric |

**Numerals are sacred.** Every figure that sits in a column, a stat, an axis, or
a delta uses tabular-lining numerals (`font-feature-settings: "tnum" 1`). The
headline-number uses Fraunces oldstyle figures for warmth; data tables use Plex
Mono for alignment. This split — *warm numbers in headlines, exact numbers in
tables* — is the typographic signature of the whole system.

### 4.3 Editorial detail

- `text-wrap: balance` on all display/headlines; `pretty` on prose.
- Drop-cap option (Fraunces, 3-line) reserved for the About narrative and a
  capability's reverse-PRD opening — one per document, the journalism cue.
- Margin annotations are set in `designator` mono, hung in the left/right margin
  off a 0.75px leader rule — the hand-annotated-chart move (§7.2).

---

## 5. SPATIAL system

A **newspaper column grid** — the structure is literally the information.

### 5.1 Grid

- **12-column** base, `max-width: 1320px`, gutter `24px`, outer margin fluid.
- **Editorial overlay: a 4-column "broadsheet" measure** for long-form (prose
  lives in cols 2–3 of a 4-col field at ≤68ch; annotations hang in col 1 or 4).
  This is the FT article grid: a narrow reading column with a live margin.
- **Chart-bleed**: hero distributions may bleed to the full 12 cols or break the
  right margin entirely (the "full-bleed infographic") — the one place the grid
  is deliberately broken, and only for a chart, never for decoration.
- Baseline rhythm: **4px base unit**, body set on an 8px vertical baseline so
  prose, rules, and figures lock to the same horizontal grid lines you can
  *see* (faint baseline rules are a real visible motif on record pages — §7.3).

### 5.2 Spacing scale (4px base)

`2 · 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 · 96 · 128`. Section rhythm on
marketing varies deliberately (96 / 64 / 128) to avoid the metronome feel;
app density is tighter (16/24).

### 5.3 Radius

`2px` default (record cards, inputs), `4px` ceiling (elevated sheets, the live
plate panels), `0` for tables and rules. **Pill radius is banned** — nothing
here is a consumer chip. Corners are cut, not rounded — the instrument-panel cue.

### 5.4 Density philosophy

Two registers, explicitly:
- **Record / marketing** = airy (VISUAL_DENSITY 3). Whitespace is the luxury;
  one idea per field; the chart breathes.
- **Instrument / app tables** = considered-dense (DENSITY 5–6). A simulations
  logbook or feature-pack catalog packs rows like a stock table — legible
  density, hairline-divided, tabular numerals, scannable in one pass. Never a
  cockpit, never a toy.

Hairlines (0.75px `rule`) do the work cards usually do: `border-t` and `divide-y`
group; elevated `sheet` cards are used *only* when a record is a discrete object
(one persona, one capability). No nested cards, ever.

---

## 6. MOTION + EFFECTS — the signature layer

### 6.1 Name: **"THE DEVELOPING PRINT"**

The signature graphics layer is a **live distribution that draws itself** — a
density curve / dot-strip / sparkline that renders the way a journalist's chart
would animate into a published page, or the way a Polaroid develops: from
provenance-scaffold → settling samples → resolved distribution → annotated
finding. It is the literal visual of *a reading being taken*.

**Where it lives:** the simulation-results hero, the marketing hero, the
agent-cohort fan-out, and every metric that is a distribution rather than a
scalar. Small static sparkline versions live inline in the simulations logbook
and library cards.

**Tech, layered by fidelity:**
- **SVG + `<animate>` / stroke-dashoffset + Motion** for the everyday charts
  (distribution curves, deltas, axis draw-on). Crisp at any DPI, accessible,
  cheap. This is 90% of the system.
- **Canvas 2D** for dot-strip / unit-chart distributions where each synthetic
  agent is one dot (hundreds–thousands of dots settling into a histogram via a
  light force-layout). One reaction = one dot finding its bin. This is the
  showpiece (§7.1).
- **WebGL / GLSL fragment shader** for the marketing-hero ambient only: a
  **"phosphor field"** — a dark lightbox plate across which faint
  control-vs-treatment density isobands drift and a six-blade aperture reticle
  slowly breathes, sampling. GPU, `prefers-reduced-motion` → a single static
  rendered frame (a printed plate). Never on app surfaces.

### 6.2 Motion principles

- **Motion = a measurement happening, or nothing.** Curves draw on because data
  is arriving. Numbers count up because a tally is being struck. A reticle
  breathes because the instrument is sampling. If an animation can't be read as
  "the instrument is doing work," it's cut. No decorative drift on records.
- **Durations:** data draw-on 600–1100ms `ease-out-expo`; number tally 800ms
  with `tnum` so width never jitters; UI micro-interactions 140–200ms; page
  reveals stagger 60ms. Keyboard-initiated actions: instant.
- **Easing:** `cubic-bezier(0.16, 1, 0.3, 1)` (out-expo) house curve. No bounce,
  no elastic — instruments don't spring.
- **The settle.** Every reading *settles*: the final 200ms of any data animation
  damps to rest (slight overshoot-free deceleration) so the number visibly
  "comes to rest" like a needle. This is the emotional beat — the reading is now
  fixed, citable evidence.
- **Reduced motion:** every chart ships its resolved frame as the default; motion
  enhances an already-complete, already-visible render. A headless/reduced
  render shows the finished distribution, never a blank canvas.
- **Provenance never animates.** The byline/dateline/snapshot strip is always
  instantly present — trust elements never fade in.

### 6.3 Tasteful guardrails

The shader and dot-strip are *rare and load-bearing* — one phosphor field on the
marketing hero, one dot-strip per results page. Library, list, and record pages
get static charts with at most a draw-on reveal. The discipline: spectacle only
where a reading is genuinely live; paper records stay still.

---

## 7. THREE SIGNATURE MOVES (unique to Sidira)

### 7.1 ✦ THE COHORT SETTLE *(graphics showpiece)*

On a simulation result, the population's reaction renders as a **unit-distribution
that assembles itself from individual agents**: every synthetic agent is one
dot, the dots stream up from a baseline "ledger" and settle into a histogram /
beeswarm under the agreement axis, control-arm dots and treatment-arm dots in
their two inks, finding their bins via a damped force-layout (Canvas 2D). As the
last dots settle, the **headline-number tallies up** to the agreement score and
the curve's annotation hand writes itself in the margin ("treatment splits the
cohort: power-users lift, churned-risk recoil"). Then everything comes to rest —
the settle. You watched the reading be taken from N individual minds, and now
it's a fixed, annotated published chart. Hover any dot → that agent's one-line
reaction; click → their 1:1 transcript. No competitor renders the population as
*individuals resolving into a distribution* — it makes "we simulated 400 people"
viscerally, countably true.

### 7.2 ✦ THE MARGIN HAND (annotation-as-interface)

Borrowed straight from FT/Pudding: findings, caveats, and provenance are
**hand-annotations hung in the page margin**, tied to the exact point on the
chart or line of prose they concern by a 0.75px leader rule. A weakness finding
isn't a red card — it's a margin note pointing at the dip in the distribution,
in mono ink: `← n=37 churned-risk agents read this as a paywall`. The
uncalibrated-reading disclosure is a margin stamp next to the headline-number,
not a banner. This makes the instrument's *honesty* feel like editorial rigor —
the annotations ARE the credibility — and it's a structural device no SaaS
dashboard owns, because dashboards have no margin and no editor.

### 7.3 ✦ THE BASELINE LEDGER (the visible grid of record)

Record and results pages are set on a **faintly visible 8px baseline grid** — like
ledger paper or a chart's gridlines bleeding through the type — and the
provenance line (snapshot, capture date, seed, model) is printed as a
**masthead dateline** locked to that grid, the way a newspaper prints its volume
/ issue / date across the top rule. Numbers in every table snap to these lines;
distributions use the same lines as their axis. The "empty ledger" disclosure
(no live-outcome ground truth yet) is literally the baseline grid shown bare at
the bottom of a results page — *the ledger is empty, here it is, blank, by
design*. Provenance and self-skepticism become a coherent visual system instead
of fine print: the whole page admits it's a sheet of measured record, and shows
you the ruling.

---

## 8. Why this is top-0.1% for THIS product specifically

Sidira's core truth is a **rigorous instrument that simulates human behavior and
reports it honestly to people deciding what to build.** Generic instrument-design
goes cold and dead; generic SaaS goes hype and untrustworthy. Data-journalism is
the *exact* missing register: it is the one visual tradition built specifically
to make **complex behavioral data feel inevitable, sourced, and honest to a
skeptical reader** — which is verbatim Sidira's job for a founder pitching a
sophisticated buyer.

1. **The distribution-as-hero matches the product's substance.** Sidira's output
   isn't a verdict scalar — it's a *population's distribution of reactions* with
   an agreement score and provenance. FT/Pudding's whole craft is rendering a
   distribution so a non-expert reads it correctly. The Cohort Settle (§7.1)
   turns the literal data structure into the literal hero graphic. Form = truth.

2. **Annotation-as-interface solves the honesty mandate no one else solves.**
   Every surface in the brief screams the same tension: be decisive enough to act
   on, self-skeptical enough to never be mistaken for measured outcome. A red/green
   dashboard can't hold that. A margin-hand annotation system (§7.2) *is* how
   serious journalism holds exactly that tension — assertive headline, honest
   caveat in the same calm voice. It's a perfect, non-obvious fit.

3. **It preserves the instrument DNA while making it unforgettable.** Paper-and-ink,
   mono designators, hairline rules, color-encodes-identity-not-valence, the
   six-blade aperture, the paper-record-vs-glass-reading split — all of the
   product's hard-won discipline survives, because data-journalism shares those
   exact instincts (restraint, provenance, tabular numerals, no decorative color).
   But the broadsheet grid, the four-voice masthead typography, the Developing
   Print, and the Baseline Ledger push it from "tasteful B2B paper aesthetic" to
   "a published page of record that could only be Sidira." A designer stops
   scrolling because the population *assembles itself out of individual minds in
   front of them* — and then the data, annotated by a steady hand, makes the
   finding feel like it was always true.

This is the rare case where the most ambitious graphics move (thousands of
agent-dots settling into an annotated distribution) and the most disciplined
trust move (margin honesty, visible ledger, valence-free color) are *the same
design language*. That coherence — spectacle that reads as rigor — is what makes
it top-0.1% for Sidira and no one else.
