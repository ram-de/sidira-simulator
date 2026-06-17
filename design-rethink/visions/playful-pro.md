# Sidira — Design Vision: "Playful-Pro / The Living Instrument"

> Direction channeled (not cloned): **Raycast/Arc playful-pro** — delightful,
> characterful, soft depth, springy physics, alive-and-modern without toylike.
> The ONE rule honored throughout: every effect amplifies Sidira's core truth —
> *a rigorous instrument that simulates human behavior* — so spectacle reads as
> intelligence and credibility, never gimmick.

---

## 1. Design thesis (one line)

**A precision instrument that breathes — warm graphite glass with a living
aperture at its heart, where cold simulation rigor is made to feel intimately,
physically alive.**

The whole system is one idea: an oscilloscope that has a pulse. Raycast taught
us a pro tool can be *delightful*; Sidira's delight is that the instrument
behaves like the thing it measures — a population of minds — so the interface
itself feels populated, reactive, and warm-blooded under a cold chrome shell.

---

## 2. Mood / emotional target

| Axis | Target |
|---|---|
| First 400ms | *"This is alive."* The aperture breathes, agents stir, a soft graphite gradient settles. |
| First 3 seconds | *"This is serious."* Mono designators, tabular numerals, hairline precision, honest empty states. |
| The held feeling | **Earned, springy confidence.** A founder feels they are holding a warm, expensive measuring device — not a SaaS dashboard, not a toy. |
| The refusal | Never hype. Never confetti. Never a fake verdict. Delight comes from *physics and life*, never from decoration. |

The dial settings (from the taste skill): **DESIGN_VARIANCE 7 · MOTION_INTENSITY 7
· VISUAL_DENSITY 4** for marketing surfaces; **VARIANCE 5 · MOTION 4 · DENSITY 6**
for app records. The instrument is playful at the front door and disciplined at
the workbench — one personality, two postures.

---

## 3. COLOR system (exact values)

The palette is **graphite + bioluminescence**: a cold near-black instrument body
warmed by a single living accent. This deliberately rejects the paper-and-ink
default of the prior system AND the AI-cream trap — Sidira's *bench* becomes dark
glass, and "warmth" is carried by the accent's life, not by a beige background.

### 3.1 Core ramp — Graphite (the instrument body)

| Token | Hex | OKLCH | Role |
|---|---|---|---|
| `--void` | `#070B12` | `oklch(0.14 0.018 256)` | deepest bg, behind glass |
| `--graphite-900` | `#0B1018` | `oklch(0.17 0.020 256)` | app canvas (dark) |
| `--graphite-800` | `#10161F` | `oklch(0.21 0.021 255)` | raised surface |
| `--graphite-700` | `#18202B` | `oklch(0.26 0.022 254)` | card / panel |
| `--graphite-600` | `#222C39` | `oklch(0.32 0.024 253)` | hairline-lit edge |
| `--graphite-500` | `#37445400`→`#374454` | `oklch(0.42 0.025 252)` | muted stroke |
| `--mist-400` | `#7C8AA0` | `oklch(0.64 0.028 252)` | secondary text |
| `--mist-200` | `#B7C2D2` | `oklch(0.81 0.022 252)` | body text on dark |
| `--chalk` | `#EAEFF6` | `oklch(0.95 0.008 252)` | primary text on dark |

### 3.2 Signal — Aperture Lime (the one living accent, ≤8% of any surface)

The pulse of the diaphragm. Reserved for *live readings, the aperture motif, and
the single primary action per surface.* Never a decorative fill.

| Token | Hex | OKLCH |
|---|---|---|
| `--signal-core` | `#B6FF3C` | `oklch(0.91 0.214 128)` |
| `--signal` | `#9BE82A` | `oklch(0.85 0.205 130)` |
| `--signal-deep` | `#5FA60E` | `oklch(0.63 0.165 131)` |
| `--signal-glow` | `rgba(155,232,42,0.22)` | bloom / halo only |

### 3.3 Co-accent — Avira Violet (provenance, identity, "the person inside")

The Sid+Avira origin, encoded but quiet. Used *only* on persona/agent identity
surfaces — the human inside the machine — never on chrome. Cyan + violet are the
two phosphor colors of the readout; lime is the trace.

| Token | Hex | OKLCH | Role |
|---|---|---|---|
| `--avira` | `#9E7BFF` | `oklch(0.70 0.16 295)` | persona identity accent |
| `--phosphor-cyan` | `#54E6E0` | `oklch(0.83 0.12 192)` | A/B treatment trace, citations |

### 3.4 Honest-state tints (border-only, message reads in ink — never alarm-red fills)

| Token | Hex | Use |
|---|---|---|
| `--caution-edge` | `#E8B24A oklch(0.79 0.13 78)` | placeholder/ungraded — hairline + label only |
| `--affirm-edge` | `#5FA60E` | validated/real — hairline + label only |

A negative simulation reaction renders as **neutral `--mist-200` information**,
never red. This is load-bearing product truth (see DESIGN.md results rule).

### 3.5 Light mode — "Bench" (paper bench, glass display)

The record surfaces (persona detail, capability detail, simulations log) keep a
*paper* light theme so records read like archival documents. This is the
matte-bench / dark-glass duality made literal: **marketing + live-reading panels
are dark graphite glass; read-only records are warm paper.**

| Token | Hex | OKLCH |
|---|---|---|
| `--paper` | `#F5F1E8` | `oklch(0.95 0.012 92)` |
| `--paper-raised` | `#FBF8F1` | `oklch(0.97 0.010 92)` |
| `--ink` | `#0E1620` | `oklch(0.18 0.016 250)` |
| `--ink-soft` | `#43505F` | `oklch(0.42 0.022 250)` |
| `--rule` | `rgba(14,22,32,0.12)` | 0.75px hairlines |
| signal/avira | same as dark | accents are theme-invariant |

**Rule:** a single surface is one theme. Glass panels embedded in a paper record
(a live reading inside a record page) are the one sanctioned theme-island, and
they appear *only* when the data is genuinely live/computed.

---

## 4. TYPOGRAPHY (Google-Fonts-available, exact)

Three roles, paired on real contrast axes — no two-similar-sans amateur move.

| Role | Family | Source | Why |
|---|---|---|---|
| **Display / headline** | **Space Grotesk** | Google Fonts | Drafting-table geometric with quirk — instrument-coded but characterful (the Raycast-grade "pro with personality"). Not Inter, not a serif. |
| **Body / UI** | **Inter Tight** | Google Fonts | Compact humanist neutral; carries dense app UI and marketing prose without competing with the display. Pairs on a width/contrast axis vs. Space Grotesk. |
| **Designator / data / mono** | **Geist Mono** | Google Fonts | Tabular numerals, the "readout" voice: ids, role tags, snapshot stamps, metric values, agreement scores. The instrument's printed-tape voice. |

**Numerals:** `font-feature-settings: "tnum" 1, "ss01" 1;` on every metric, score,
weight, and timestamp. Numbers must lock into columns — non-negotiable for a
measurement tool.

### Type scale (1.250 major-third, rem)

| Token | Size | Line | Tracking | Weight | Use |
|---|---|---|---|---|---|
| `display-xl` | clamp(2.6rem, 6vw, 4.75rem) | 1.02 | -0.035em | 500 | hero only (ceiling ~76px) |
| `display-l` | 3.05rem | 1.05 | -0.03em | 500 | section heroes |
| `h1` | 2.0rem | 1.1 | -0.025em | 500 | page titles |
| `h2` | 1.5rem | 1.15 | -0.02em | 500 | section heads |
| `h3` | 1.2rem | 1.25 | -0.015em | 600 | card titles |
| `body-l` | 1.125rem | 1.6 | 0 | 400 | marketing lede (max 68ch) |
| `body` | 1.0rem | 1.6 | 0 | 400 | prose, records (max 72ch) |
| `ui` | 0.9375rem | 1.45 | 0 | 450 | app UI |
| `designator` | 0.75rem | 1.3 | 0.14em (mono, uppercase) | 500 | eyebrows, ids, role tags |
| `micro` | 0.6875rem | 1.3 | 0.10em (mono) | 500 | provenance stamps |

Eyebrow discipline: mono designators are a *brand system voice* (ids, snapshot
stamps, role tags) — legitimate because they encode real data — but the
templated "uppercase kicker above every section" is banned. Max one decorative
eyebrow per three sections; data designators don't count.

---

## 5. SPATIAL system

- **Grid:** 12-col, `max-w-[1280px]` marketing, `max-w-[1440px]` app shells,
  `gutter 24px`, content max-w 72ch for prose.
- **Spacing scale (4px base, geometric-ish):** `4 · 8 · 12 · 16 · 24 · 32 · 48 ·
  64 · 96 · 128`. Vary it for rhythm; never uniform.
- **Radius — the instrument curve:** `--r-chip 4px · --r-control 8px · --r-panel
  14px · --r-glass 18px`. Soft enough to read as warm-modern depth (Arc/Raycast),
  sharp enough to read as a machined panel. ONE scale, locked: chips 4, controls
  8, panels 14, glass readings 18.
- **Density philosophy:** *airy at the front door, instrument-dense at the
  bench.* Marketing breathes (DENSITY 4). App records and the reading panels run
  DENSITY 6 — close-set tabular data, hairline dividers instead of cards, numbers
  given room to be read but never wasted whitespace. Cards are used only where
  elevation is real (a live reading panel); records group with `divide-y`
  hairlines, not boxes.
- **Depth model — "soft graphite depth":** elevation is built from (a) a 1px
  top inner-highlight `inset 0 1px 0 rgba(255,255,255,0.06)`, (b) a hue-tinted
  ambient shadow `0 24px 60px -24px rgba(7,11,18,0.7)`, and (c) a hairline
  `--graphite-600` edge. No pure-black shadows. This is the Raycast "lifted
  pane" feel, tuned cold.

---

## 6. MOTION + EFFECTS — the signature graphics layer

### 6.1 Motion principles

- **Spring physics, not easing curves** for interactive feedback: `spring,
  stiffness 220, damping 26, mass 0.9`. For reveals/exits: `cubic-bezier(0.16, 1,
  0.3, 1)` (ease-out-expo), 180–420ms. No bounce, no elastic, no linear.
- **Frequency gate:** the hero aperture and scroll showpieces are rare-view →
  expressive. In-app, frequently-triggered actions (send message, rate, open
  row) are **instant or <140ms**. Keyboard-initiated = no animation.
- Every motion is motivated: reveal (sequence), feedback (a push, `scale 0.985`
  on `:active`), state-change (a reading *settling*), or life (the ambient
  population). `prefers-reduced-motion` swaps every effect for a crossfade and
  freezes the ambient field to a single static frame.

### 6.2 THE SIGNATURE GRAPHICS LAYER — **"The Cohort Field"**

> A live WebGL particle-and-field system that renders Sidira's literal subject:
> **a population of synthetic minds reacting to a change.** It is the one
> showpiece, and it is *the same engine* everywhere — scaled from hero spectacle
> to in-product readout, so the spectacle is never decorative; it always depicts
> real or representative data.

**What it is:** a few thousand GPU points (instanced, in a single draw call) on
a dark graphite plane, organized by a flow-field. Each point is one synthetic
agent. They drift with curl-noise (alive, breathing), cluster into persona
*basins* (gravity wells colored by `--avira`), and — when a "bet" is applied —
**split into a control river and a treatment river**, the treatment tinted
`--phosphor-cyan`, the divergence between them *being* the visual proof of lift.
At the optical center sits the **six-blade aperture** (the mark), rendered as a
soft additive bloom that **breathes** (scale 0.985→1.0, 5.5s) and whose blades
**close** on a committed decision (the in-product aperture-close moment).

**Tech, layered for taste and safety:**
1. **WebGL/GLSL** (regl or raw, ~2k–6k instanced points, additive blend, curl-
   noise in the vertex shader, depth-tinted alpha). This is the hero and the
   results-page field.
2. **Canvas 2D fallback** (~600 points) when WebGL is unavailable.
3. **SVG/CSS static frame** for `prefers-reduced-motion`, headless renderers,
   and first paint (the field fades in *over* a crisp static frame — content is
   never gated on the animation; the reveal enhances an already-visible default).

**How it stays tasteful (the discipline that makes it pro, not gimmick):**
- It lives behind/within content at **18–34% opacity**, color-keyed to graphite
  — a *substrate*, never a foreground toy.
- It is **data-bound, not random**: on the results page the cluster count = real
  persona count, the divergence = real agreement/lift, the agitation = real
  sentiment. On marketing it animates a representative (clearly-labeled mock)
  cohort. Spectacle = the data made physical.
- It **settles**. Like a real instrument needle, motion resolves to stillness
  when a reading completes. Idle ambient drift is sub-perceptual (≤2px/s).
- One field per view, ever. No second particle system, no marquee, no confetti.

### 6.3 Supporting effects

- **Glass readings:** live computed panels get `backdrop-filter: blur(16px)
  saturate(1.3)`, a `--graphite-600` hairline, and an inner top highlight —
  reserved strictly for live/computed readings (never on records or static
  marketing chrome), with a `prefers-reduced-transparency` solid fallback.
- **Signal trace:** numbers that just computed sweep in with a 1px lime
  underline that draws left→right (240ms) then fades — the "needle just landed"
  micro-moment.
- **Magnetic primary CTA:** the single per-surface primary action has a subtle
  magnetic pull (`useMotionValue`/`useTransform`, ±6px, off the render cycle)
  and a lime aperture-iris that irises open on hover.

---

## 7. THREE SIGNATURE MOVES (unique to Sidira)

### 7.1 ⟡ The Cohort Field → Decision (graphics showpiece)
The Cohort Field (§6.2) is the showpiece. Its unique, unownable move: **on
"Begin reading," the drifting population streams through the aperture and splits
into control/treatment rivers; on the verdict, the aperture blades *close* like a
shutter capturing the reading, and the lift-divergence freezes into the
agreement score.** No competitor visualizes synthetic-population simulation as a
literal, data-bound particle population passing through their own logo-aperture.
It is the product's thesis rendered as light.

### 7.2 ⟡ The Living Manifest (hypothesis builder)
As the founder composes a hypothesis, a **glass "manifest" panel** assembles in
real time — every choice (what's under test, cohort, sample size, A/B 2× cost)
springs into a tactile receipt with tabular numerals. The cohort size animates a
matching *seed count* of agent points into the embedded field; pick A/B and the
field visibly *doubles and forks*, making the 2× cost felt, not just stated.
"What you see is exactly what will run" becomes a physical, honest promise.

### 7.3 ⟡ Designator Tape (the printed-tape provenance voice)
Every record, agent, and snapshot carries a **mono "designator tape"** — a
single hairline-boxed strip of Geist Mono tabular data (`cr-924718699c21 ·
2026-W25 · seed 4471 · groq`) that reads like calibrated instrument label tape.
On hover, a citation token (`[a3]`) draws a 1px phosphor-cyan tether to its
source. Provenance is never buried in fine print; it's the instrument's
serial-number plate, always in frame — the move that makes a transcript read as
*evidence*, not chat.

---

## 8. Why this is top-0.1% for THIS product

1. **The effect IS the product.** Most "ambitious" landing graphics are
   decorative WebGL with no semantic link to the product. Sidira's Cohort Field
   *is* a synthetic population reacting to a change — the literal thing the
   instrument does. Spectacle and substance are the same object, so ambition
   reads as engineering credibility to the exact buyer (skeptical product
   leaders) who would otherwise distrust spectacle.
2. **It resolves the paper-vs-glass tension instead of ignoring it.** The prior
   system's best idea (record = paper, reading = glass) is *kept and amplified*:
   records stay archival paper, live readings become breathing graphite glass,
   and the duality becomes the brand's spatial grammar rather than a constraint
   to design around.
3. **Delight without toylike.** Raycast's lesson — a pro tool earns love through
   springy physics and soft depth — is applied through a cold graphite shell and
   a single bioluminescent accent that only ever marks *life and live data*. The
   warmth is the population breathing inside cold chrome. That is the precise
   emotional signature no competitor (paper-dry research tools, or hype-y SaaS)
   occupies.
4. **Honesty is designed in, not bolted on.** Negative reactions render neutral,
   placeholders wear a caution hairline (never a red fill), uncalibrated
   readings carry their own self-skeptical designator tape. The instrument is
   delightful *and* refuses to fake a verdict — which is exactly what earns a
   disciplined founder's trust, and exactly the 0.1% move: restraint and
   spectacle held in the same hand.
