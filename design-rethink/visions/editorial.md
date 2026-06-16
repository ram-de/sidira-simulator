# Sidira — Design Language: "THE READING ROOM"

> A clean-sheet, original design language for Sidira. Channels the *spirit* of
> Stripe / editorial-trust (generous whitespace, warm authoritative voice,
> beautiful typographic hierarchy, diagrammatic illustration, the feeling of a
> premium financial product you trust) — but is its own thing: an instrument
> that reads human behavior, set down as a typeset record.

---

## 1. Design thesis (one line)

**Set the simulation down like a financial statement and let the live reading breathe like an instrument — every screen is a typeset record of a measurement that respects the reader's intelligence.**

---

## 2. Mood / emotional target

The feeling of opening a beautifully typeset quarterly report from a firm you
already trust — and finding, embedded in the margins, a live oscilloscope still
warm from the bench. Calm, exact, expensive-quiet. Authority without volume.
The reader should feel: *these people measure carefully, they tell me what they
don't know, and I would put a sprint of engineering on their word.* The
opposite of a SaaS splash: no hype, no confetti, no spinner-and-glow. Spectacle
is permitted only where it reads as **intelligence** — the moment a population
of synthetic minds resolves into a verdict.

Three emotional beats the system must always hit:
- **Trust through restraint** — the page is mostly quiet so the one live thing means something.
- **Candor as luxury** — disclosure of limits (uncalibrated, raw, X-of-N) is rendered as confidence, never as a warning the user must dismiss.
- **Earned spectacle** — the signature graphics fire once, at the decision moment, and never loop.

---

## 3. COLOR system

A clean-sheet palette. It deliberately **departs** from the saturated 2026 AI
cream-and-terracotta default and from the prior `#F4EFE6` warm-paper reflex.
The base is a **cool archival oat** — a near-neutral with a whisper of cool
green-grey, not warmth-by-default — so the one warm-cool tension on screen is
carried by *type and ink*, and the one chromatic event is carried by the live
**phosphor** reading. Two accents only: a single instrument **phosphor** (the
live reading) and a single **vital ochre** (human, the persona/agent layer).
Everything else is ink on oat.

### 3.1 Light mode — "the bench in daylight" (default for records & marketing)

| Role | Token | HEX | OKLCH | Use |
|---|---|---|---|---|
| Base surface | `oat` | `#F1EFE8` | `oklch(0.945 0.008 110)` | page background — cool archival oat, chroma toward green-grey not warm |
| Sheet | `sheet` | `#FBFAF6` | `oklch(0.982 0.005 110)` | record cards, panels, modals (raised paper) |
| Sunk | `sunk` | `#E7E4DA` | `oklch(0.905 0.010 108)` | inputs, code wells, recessed rows |
| Ink | `ink` | `#15211C` | `oklch(0.235 0.018 168)` | primary text, rules, the mark — a deep ink-spruce, not pure black |
| Ink-2 | `ink-muted` | `#4C574F` | `oklch(0.470 0.016 165)` | secondary text, axis labels, captions (≥4.6:1 on oat) |
| Ink-3 | `ink-faint` | `#7C857C` | `oklch(0.610 0.012 160)` | designator chips, timestamps, the quietest layer (use ≥14px) |
| Hairline | `rule` | `rgba(21,33,28,0.14)` | — | 0.75px true hairlines between records |
| **Phosphor** | `signal` | `#5BE08C` | `oklch(0.835 0.165 156)` | THE live reading — traces, running pulse, computed verdict glyph. Budget: ≤2 carriers/screen. |
| Phosphor-deep | `signal-ink` | `#1E5C3A` | `oklch(0.430 0.110 158)` | phosphor's ink companion on light surfaces (labels/strokes that must hit AA) |
| **Vital ochre** | `vital` | `#C8761E` | `oklch(0.660 0.135 62)` | the human layer — persona/agent identity accent, sparing |
| Vital-deep | `vital-ink` | `#7A430E` | `oklch(0.440 0.095 56)` | vital's AA-safe ink companion |

Semantic (rendered as *ink + hairline border*, never as fills — candor not alarm):
| Role | HEX | Note |
|---|---|---|
| `caution` | `#9A5B12` | low-stability / placeholder / uncalibrated — reads as a margin note, not a red light |
| `affirm` | `#1E5C3A` | reuses phosphor-deep; "validated", "real data" |
| `alert` | `#A23A22` | true error only (failed crawl, broken connection); border + ink, never a banner fill |

### 3.2 Dark mode — "the instrument display" (default for live readings, simulations in flight, agent transcripts at night)

This is **not** an inverted marketing theme. Dark mode is the *display glass* —
the one surface where the bench goes dark so the phosphor reads. Same palette,
re-grounded.

| Role | Token | HEX | OKLCH |
|---|---|---|---|
| Base glass | `glass` | `#0C1714` | `oklch(0.205 0.016 168)` — ink-spruce gone to glass, not generic slate |
| Glass sheet | `glass-sheet` | `#13201B` | `oklch(0.258 0.018 166)` |
| Glass sunk | `glass-sunk` | `#091310` | `oklch(0.170 0.014 168)` |
| Glass ink | `glass-text` | `#EAF0EA` | `oklch(0.945 0.008 160)` |
| Glass ink-2 | `glass-muted` | `rgba(234,240,234,0.58)` | — |
| Glass hairline | `glass-rule` | `rgba(234,240,234,0.10)` | — |
| **Phosphor (glass)** | `signal` | `#62F39A` | `oklch(0.875 0.185 156)` — reaches ~14:1 on glass, the true oscilloscope green |
| Vital (glass) | `vital` | `#E5933A` | `oklch(0.745 0.130 64)` |

**Phosphor persistence rule (load-bearing):** phosphor lines never use CSS
`glow`/`blur`/`drop-shadow`. Persistence is faked the way a real CRT does it —
a 4px, 16%-opacity **underdraw** of the same SVG path beneath the 1.5px live
stroke. This is the single most important detail keeping the brand from
collapsing into "dark dashboard with a neon accent."

### 3.3 The one hard law

Two accents, total. **Phosphor = the machine is reading. Vital = a human is
in the frame.** If a color appears that is neither ink, oat, phosphor, nor
vital, it is a bug. No gradients-as-decoration, no second blue, no status
rainbow.

---

## 4. TYPOGRAPHY

The type IS the instrument's authority. Three families on a deliberate contrast
axis — a transitional **serif** for record prose (the financial-statement
voice), a **grotesque sans** for interface and headlines (the engineered
voice), and a **mono** strictly for designators and live numerals (the
measured voice). All Google-Fonts-available.

### 4.1 Families

| Role | Family | Why this one (not the reflex) |
|---|---|---|
| **Record serif** (PRD prose, About narrative, persona descriptions, long-form) | **Newsreader** (Google) | A screen-tuned transitional serif with real editorial gravity and an italic with genuine character. NOT Fraunces/Instrument Serif (the banned LLM display serifs) — Newsreader reads like a respected periodical, not a "creative brief." |
| **Interface grotesque** (all UI, headlines, labels, nav, buttons, data tables) | **Geist** (Google / Vercel) | Neutral, engineered, tabular-friendly; the "made by serious people" sans. Carries headlines via weight, not a second face. |
| **Measured mono** (designators, IDs, role chips, live numerals, provenance, timestamps, manifest) | **Geist Mono** (Google) | Pairs natively with Geist; tabular by construction. Mono is *reserved* — it marks the things a machine wrote or measured. |

Pairing logic: serif↔sans is a true contrast axis (not two grotesques). Mono
shares Geist's skeleton so the "machine voice" feels like the same hand. The
wordmark **SIDIRA** stays narrow-grotesque uppercase (Geist at weight 600,
`letter-spacing 0.06em`) — no glyph trickery, ever.

### 4.2 Type scale (1.250 major-third, fluid via clamp)

| Token | Size (clamp) | Line-height | Tracking | Weight | Family | Use |
|---|---|---|---|---|---|---|
| `display` | `clamp(2.8rem, 1.6rem + 4vw, 4.5rem)` | 1.02 | -0.035em | 600 | Geist | marketing hero (ceiling ≤72px; never shouting) |
| `h1` | `clamp(2rem, 1.4rem + 2vw, 2.75rem)` | 1.08 | -0.03em | 600 | Geist | page titles |
| `h2` | `1.75rem` | 1.12 | -0.025em | 600 | Geist | section heads |
| `h3` | `1.3rem` | 1.2 | -0.015em | 550 | Geist | sub-heads |
| `lede` | `1.375rem` | 1.5 | -0.005em | 400 *italic optional* | Newsreader | the one editorial sentence under a hero / dossier opener |
| `prose` | `1.0625rem` | 1.65 | 0 | 400 | Newsreader | PRD body, About, persona descriptions — max 68ch |
| `body` | `0.9375rem` | 1.55 | 0 | 400 | Geist | UI body, form help, table cells |
| `label` | `0.75rem` | 1.2 | 0.08em | 500 *uppercase* | Geist Mono | designators, provenance, eyebrows (rationed — see §6) |
| `micro` | `0.6875rem` | 1.3 | 0.06em | 500 | Geist Mono | timestamps, seed, model id, X-of-N |
| `numeral` | contextual | 1 | 0 | 500 *tabular* | Geist Mono | every score, CI, lift, %, cohort count — `tnum` always on |

**Hard rules:** body prose uses serif and caps at 68ch. Mono is never used for
sentences — only designators and numbers. Emphasis inside a headline is
weight/italic of the *same* family, never a dropped-in serif word. Display
ceiling 72px. Display tracking floor -0.04em.

---

## 5. SPATIAL system

### 5.1 Grid

- **Marketing**: 12-column, `max-width: 1180px`, gutter 24px, generous outer margins. Hero and editorial sections break to an **asymmetric 7/5 or 8/4** split (text-left, diagram-right) — never a centered hero except the About manifesto opener.
- **App**: a **records ledger** grid — full-width content column `max-width: 1100px`, left-rail designators (mono IDs, provenance) in a fixed 180px margin column on wide screens, collapsing under the content on narrow. The left margin is the "binder edge" of the dossier.
- **Reading column** for any long-form record: 68ch hard cap, centered within its sheet.

### 5.2 Spacing scale (4px base, geometric)

`2 · 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 · 96 · 128` (px). Section rhythm on
marketing uses **96–128**; record-internal rhythm uses **16–24**. Whitespace is
the primary luxury signal — when in doubt, add a step.

### 5.3 Radius — "filed paper"

One scale, committed: **2px** on chips/inputs/code-wells, **4px** on
sheets/cards/modals, **0px** on full-bleed rules and table edges. Phosphor
glass wells take 4px. No pills, no 16px blobs — filed records have crisp
corners. (Buttons are the one exception: 4px, never full-pill.)

### 5.4 Density philosophy

**Airy for records, dense only for live instruments.** A persona dossier or
PRD breathes (density ~3/10). A live simulation manifest, a results panel, an
agent fan-out runs denser (~6/10) because the operator wants the whole reading
in one viewport. The density *shift itself* is meaningful: airy = "read this,"
dense = "watch this." Never a uniform cockpit, never a uniform gallery.

### 5.5 Hairlines over cards

Group with `border-top` hairlines (`rule`, 0.75px) and negative space before
reaching for a card. A card earns its sheet only when it is a discrete record
(one persona, one capability, one simulation). Never nest cards.

---

## 6. MOTION + EFFECTS — the signature graphics layer

### 6.1 Name: **THE APERTURE FIELD**

The signature graphics/effects layer is a **WebGL/canvas phosphor field** named
the **Aperture Field**: a generative particle system of N points (one per agent
in the cohort) that behaves like an instrument resolving a measurement. It is
the visual proof of the product's core truth — *a rigorous instrument that
simulates a population of human minds.*

- **Where it lives:** (1) the marketing hero, as an ambient resolved field behind the value prop; (2) the simulation *running* state, where points scatter then converge; (3) the **decision-commit beat** on the results page, where the field collapses through a six-blade aperture into the verdict glyph. It lives *nowhere else* — it is rationed to the three moments that are genuinely about a population resolving.
- **Tech:** WebGL via a single fragment+point shader (regl or raw GL); ~2,000–8,000 GPU points, never DOM nodes. Phosphor color only. Mouse parallax is a sub-1° drift, not a toy. CPU fallback = a static SVG of the resolved field (pre-rendered), so headless/reduced-motion/old-GPU users still see the artifact, just frozen.
- **How it stays tasteful (the discipline):** it is *monochrome phosphor on glass/oat*, never rainbow. It moves on **arrival** and on **commit** only — it does not idle-loop in the user's face (a barely-perceptible 0.5% brownian shimmer is the ceiling at rest). It always encodes real structure: each point is an agent, cluster centroids are persona means, convergence speed maps to agreement score. Spectacle = data. If it ever reads as decoration, it's wrong.

### 6.2 Motion principles

- **Easing:** ease-out only, exponential (`cubic-bezier(0.22, 1, 0.36, 1)` standard; `cubic-bezier(0.16, 1, 0.3, 1)` for the long settle). No bounce, no elastic, no spring overshoot on UI chrome.
- **Durations:** UI micro 120–180ms (Emil frequency gate — this is productivity UI, keyboard actions never animate). Record reveals 300–400ms. The decision-commit beat is the one luxury: **800ms**, fired once, non-looping.
- **Frequency gate:** the app is used daily → app motion is near-instant and quiet. Marketing is visited once → marketing motion is allowed to be cinematic (the Aperture Field, scroll-reveals).
- **Reveal honesty:** content is visible by default; reveals enhance, never gate. Reduced-motion swaps every animation for an instant crossfade and freezes the Aperture Field to its SVG still.
- **The phosphor underdraw** (§3.2) is the one non-transform material: live traces draw on with a `stroke-dashoffset` wipe (`EASE_MECH`), leaving the 16% persistence path behind — exactly like a scope sweep.

---

## 7. THREE SIGNATURE MOVES (unique to Sidira)

### 7.1 The Aperture Field → Verdict collapse *(graphics showpiece)*
On the results page, when a verdict commits, the live phosphor population field
(N points = N agents) **collapses through a six-blade camera aperture** that
irises shut around the cohort, and the points fuse into a single verdict glyph
(ship / hold) with the agreement score resolving in tabular phosphor numerals.
800ms, once, never loops. This is the product's entire thesis in one motion: a
population of synthetic minds, measured, irised down to a decision. No
competitor has an aperture-resolve because no competitor's product *is* an
aperture closing on a measurement. WebGL with SVG-still fallback.

### 7.2 The Provenance Spine
Every record (persona pack, capability PRD, simulation result, agent
transcript) carries a fixed **left binder-margin** — a mono "spine" running the
height of the sheet that states, vertically or in a stacked stack, exactly
*where this reading came from*: crawl snapshot id, capture date, seed, model,
sample size, calibration state. It is always present, always quiet, never
dismissible. Trust isn't a badge you earn once; it's a spine that runs down
every page. Editorial-trust made structural — like the running folio and
source-line of a financial statement. No SaaS product carries provenance as a
permanent architectural element; here it's load-bearing because every number is
an uncalibrated reading and candor is the brand.

### 7.3 Read-vs-Watch density inversion
The system has exactly two physical postures and the transition between them is
a signature: **paper-read** (oat, serif prose, airy, static — a record you
absorb) and **glass-watch** (dark display, mono numerals, dense, the phosphor
field live — an instrument you watch resolve). Moving from "configure a
hypothesis" (paper) to "begin reading" (the manifest dims to glass and the
field ignites) is a deliberate, choreographed surface-state change — the bench
lights going down for a measurement. The verdict, once committed, is *set back
down onto paper* as a record. Read → Watch → Read. This breathing between two
honest materials, with the live phosphor as the only chromatic event, is
something no dashboard-first competitor can do because they only have one
surface (chrome) and call everything "live."

---

## 8. Why this is top-0.1% for THIS product specifically

1. **The aesthetic is the argument.** A financial-statement record voice +
   one live instrument reading is the literal shape of Sidira's value prop:
   *de-risk a decision before you build it.* The editorial-trust spirit isn't
   skin — a quarterly-report calm is exactly the register that makes a
   sophisticated buyer believe an uncalibrated number. The design persuades on
   the same axis the product sells on.

2. **Candor rendered as luxury solves the product's hardest problem.** Every
   number is raw and uncalibrated; the "ledger is empty." A lesser design hides
   that or alarms about it. This one renders disclosure (uncalibrated, X-of-N,
   placeholder, low-stability) as margin notes in a respected document — the
   Provenance Spine — so honesty *increases* trust instead of denting it. That
   inversion is the whole game and no competitor's chrome can express it.

3. **The two-accent law makes the phosphor mean something.** Because the entire
   system is ink-on-oat with exactly one machine-color and one human-color, the
   moment phosphor appears it reads as *the instrument is alive* and vital reads
   as *a person is in the frame*. Color carries meaning, not mood — which is
   precisely how a precision instrument communicates.

4. **The Aperture Field earns "NO HOLDS BARRED" without gimmickry.** It is
   ambitious WebGL spectacle that is *literally the data* (one point per agent,
   convergence = agreement, iris-collapse = decision). It makes a designer stop
   scrolling, and it makes a buyer trust the math — because the spectacle is the
   measurement, not a gradient blob. Restraint (fires three times, never loops,
   monochrome) is what keeps it reading as intelligence.

5. **It refuses every 2026 AI tell.** Cool archival oat instead of warm
   cream/terracotta; Newsreader instead of Fraunces/Instrument Serif; serif↔sans
   contrast instead of two grotesques; provenance-as-architecture instead of
   eyebrow-on-every-section; one phosphor event instead of a status rainbow;
   hairlines instead of identical card grids. The result could not be mistaken
   for a template, and could not have been made for any product but this one.
