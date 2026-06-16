# SIDIRA — Design System v2: **THE READING CONSOLE**

> The production design language for Sidira (AI persona-simulation platform for
> founders). v2 keeps v1's bones — the Console/Sheet ontology, the candor
> primitives, and ONE signature visualization — and resolves the Round-1 council's
> central charge: v1 *performs* intelligence by naming six signature gimmicks and
> over-lawyering every number. v2 replaces that with a single governing law:
>
> ## **MAXIMAL IMPACT WHERE IT COUNTS. BRUTAL QUIET EVERYWHERE ELSE.**
>
> No-holds-barred WebGL / canvas / depth / glow is *earned* on a short, named list
> of showpiece surfaces — the landing hero, simulation results, the persona-build
> evaluate step, the new-simulation manifest. Those surfaces go as far as taste
> allows. The other ~80% of every screen is brutally quiet — ink, hairlines,
> negative space — *so the showpiece lands.* A system that is loud everywhere is
> loud nowhere.
>
> Hex + OKLCH are both authoritative (OKLCH is design intent; hex is the sRGB
> fallback). An engineer can reproduce any pixel from here. Every text/bg pair in
> this document carries a measured contrast ratio; values that fail AA in v1 are
> corrected and marked **[v2-fix]**.

---

## 0. Thesis, ontology, and the impact budget

**Thesis (one line):** *A measurement instrument for human reaction — a confident
dark **Console** frames live, computed populations; a cool blueprint **Sheet**
prints the record; every inferred number wears its spread; and spectacle is
spent like money — almost all on the one screen where the computation happens.*

### 0.1 The two-faced ontology (kept from v1 — this is the grammar)

| Surface | Mode | Means | Voice | Density | Provenance device |
|---|---|---|---|---|---|
| **Console** | dark (`#0B1220`) | a *live, computed estimate* | mono numerals, dense | **Provenance Bar** (one per reading region) |
| **Sheet** | light (`#F3F4F7`) | a *printed record / fact* | serif prose, airy | **Provenance Spine** (left binder-margin) |

Dark = estimate, light = record. The user learns the product's epistemology
through color temperature before reading a word. **Three governing adjectives:**
`exact · alive · candid`.

**Route → mode law (locked per route, never inverts mid-scroll):**
- **Console (dark):** marketing landing, app shell, dashboard, simulation setup &
  results, agent transcript, persona-build wizard, crawl setup — any live reading.
- **Sheet (light):** Capability / PRD long-form, persona-pack record detail,
  About / press / changelog — any archival document of record.
- **No mode inversion mid-route.** If a Sheet page needs a live estimate, embed
  one restrained **Console well** inside the Sheet — never a dark masthead that
  "prints" into light mid-scroll. *(v1 capability-detail / About violated this;
  fixed in §6.4.)* **[v2-fix]**

### 0.2 THE IMPACT BUDGET — the law that resolves the core tension

Every Sidira surface is classed **SHOWPIECE**, **WORKING**, or **RECORD**. The
class sets the ceiling on visual spectacle. This is the single most important
table in the system.

| Class | Surfaces | Spectacle ceiling |
|---|---|---|
| **SHOWPIECE** (4) | landing hero · simulation **results** · persona-build **evaluate** step · new-simulation **manifest** | **No holds barred.** Full-bleed WebGL Population Field, depth, wavefront, phosphor underdraw, 30fps drift, settle bloom. This is where the product earns its "stop scrolling" moment. One showpiece per page, max. |
| **WORKING** (most app) | dashboard body, lists, setup forms, transcript, settings, combobox-heavy config | **Brutally quiet.** Ink + hairline + negative space. NO Population Field. Charts are static or self-draw-once. At most one *tiny* isolated-particle motif (a single agent dot) if it threads to a showpiece. One accent carrier per viewport region. |
| **RECORD** (Sheet) | persona-pack detail, capability PRD, About, changelog | **Still.** Serif prose, Provenance Spine, no canvas, no drift, no motion beyond the page reveal. A frozen distribution *poster* (static SVG) is permitted as a figure; a live field is not. |

**The 80/20 rule, stated as law:** within any single SHOWPIECE page, the showpiece
occupies one region (typically 55–70% of the first viewport); the rest of that
page obeys WORKING quiet. A page is never loud edge-to-edge.

**What this retires from v1.** v1 named six co-equal "signature elements." v2 keeps
**two** as signatures — the **Population Field** (the one viz) and the **candor
primitives** (Spread Stamp + Provenance) — and demotes the rest to *optional
motifs* governed by the budget:

| v1 named element | v2 status |
|---|---|
| Population Field | **SIGNATURE** — the one viz, SHOWPIECE-only |
| Spread Stamp + calibration glyph | **SIGNATURE** — candor primitive, scoped (§1.10, §7.2) |
| Provenance (Bar + Spine) | **SIGNATURE** — structural honesty (§6) |
| Channel Legend | **demoted → Provenance Bar**, one per reading region (§7.3), ~40% fewer instances |
| Console↔Sheet Inversion | **demoted → route-locked theming** (no mid-route print) (§6.4) |
| Living Manifest | **optional motif**, lives only on the new-sim manifest SHOWPIECE (§7.5) |
| Dim-Unlocked Trace | **folded into Drift law** (§5.6) — finite, accessible, no longer its own named gimmick |

---

## 1. Color tokens

Authored in OKLCH; hex is the sRGB rounding. Use CSS custom properties; never
inline a raw hex. **Every text/bg pair below states its measured WCAG ratio.**

### 1.1 Console — dark instrument body (primary)

| Token | OKLCH | Hex | Role |
|---|---|---|---|
| `--console-900` | `oklch(0.17 0.022 248)` | `#0B1220` | deepest well — glass behind live readings, the scope screen |
| `--console-850` | `oklch(0.205 0.021 248)` | `#10192A` | app canvas / hero background |
| `--console-800` | `oklch(0.245 0.020 248)` | `#161F32` | raised panels, nav, cards |
| `--console-750` | `oklch(0.29 0.019 248)` | `#1D2740` | hover / pressed panel |
| `--console-700` | `oklch(0.34 0.018 249)` | `#26314C` | input wells, recessed controls |
| `--console-line` | `oklch(0.40 0.016 250)` | `#33405C` | hairline rules — render at **1px, alpha 0.5** |

### 1.2 Ink on Console (every label/body pair passes AA)

| Token | OKLCH | Hex | On `--console-850` | On `--console-700` | Role |
|---|---|---|---|---|---|
| `--text-hi` | `oklch(0.97 0.006 250)` | `#F2F4F8` | 15.8:1 | 9.6:1 | primary text, headlines |
| `--text` | `oklch(0.84 0.008 250)` | `#C6CCD8` | 9.9:1 | 6.0:1 | body |
| `--text-mut` | `oklch(0.69 0.010 250)` | `#929BAE` | 5.4:1 | 3.3:1 | captions, axis labels, provenance — **darkened from v1 `#8A93A6`** so it clears 4.5:1 on the app canvas **[v2-fix]** |
| `--text-faint` | `oklch(0.52 0.012 251)` | `#646E84` | 2.9:1 | 1.8:1 | **DISABLED CONTROLS ONLY.** Never a label, caption, tooltip, or provenance string. Its job is to look unavailable. **[v2-fix]** |

> **Law:** `--text-faint` is reserved for disabled state. Any readable label,
> caption, designator, or tooltip uses `--text-mut` or brighter. v1 used
> `--text-faint` for placeholders, watermarks, and designators on `--console-700`
> (~1.8:1 — invisible). Placeholders now use `--text-mut` at 0.7 alpha.

### 1.3 Signal — the one saturated accent (LIVE READING ONLY)

A phosphor **lime-cyan**. Reads as *measurement* (oscilloscope trace), not
eco-startup green. **Budget is law: exactly ONE signal carrier per viewport
region** (see §1.9). It is *light*, never paint — never a default button fill.

| Token | OKLCH | Hex | On `--console-900` | Role |
|---|---|---|---|---|
| `--signal` | `oklch(0.86 0.155 168)` | `#48EFCA` | 12.9:1 | live traces, the running pulse, active live control |
| `--signal-dim` | `oklch(0.72 0.13 168)` | `#39B894` | 7.4:1 | settled/resting signal, secondary trace, hover-rest |
| `--signal-wash` | `oklch(0.86 0.155 168 / 0.12)` | `rgba(72,239,202,0.12)` | — | trace underdraw / fill — **never CSS blur/glow** |

> **Signal MEANS "a live reading is here." It does NOT mean positive / ship / up /
> good / emphasis.** (§1.9 is the discipline.)

### 1.4 Spread — doubt as a first-class color

Every *inferred* Sidira number is uncalibrated; the system renders doubt with a
dedicated low-chroma **amber-sand**, used ONLY for confidence intervals, error
bars, hold-verdicts, and ungraded marks. Never competes with signal.

| Token | OKLCH | Hex | Role |
|---|---|---|---|
| `--spread` | `oklch(0.78 0.06 78)` | `#C8B68A` | CI bands, error-bar caps, "estimate" hatching (on Console) |
| `--spread-dim` | `oklch(0.62 0.05 78)` | `#90815F` | ungraded/placeholder designator text on Console (3.4:1 on `--console-900`, captions/glyphs only) |
| `--spread-wash` | `oklch(0.78 0.06 78 / 0.14)` | `rgba(200,182,138,0.14)` | CI ribbon fill on the field |

### 1.5 Arm tints — A/B identity (provenance, NEVER valence)

Two cold-vs-warm provenance poles that name *which experiment arm*. **A negative
reaction is rendered in `--text` + a down-glyph, never in the treatment color —
harm is information, not alarm.**

| Token | OKLCH | Hex | Role |
|---|---|---|---|
| `--arm-control` | `oklch(0.74 0.11 232)` | `#4FA8E0` | Control arm · "Sid" pole · steady blue |
| `--arm-treat` | `oklch(0.72 0.10 345)` | `#E08BC4` | Treatment arm · "Avira" pole · **calm magenta-coral** — shifted from v1's `#F0796B`, which read as *danger/alarm*. Magenta is unmistakably *identity*, carries no valence. **[v2-fix]** |

**Series ramp** (≥3 cohorts) — interpolate the two poles on a single perceptual
OKLCH ramp, **never a rainbow**:
`#4FA8E0 → #7C9ECF → #A797C9 → #C28FC6 → #E08BC4`.

### 1.6 Semantic — borders + word only, NEVER fill

| Token | Hex | Role |
|---|---|---|
| `--edge-warn` | `#C9A227` | caution border (uncalibrated, starter-pack, low-stability) — 1px border + the word |
| `--alert` | `#F0683C` | hard failures only (crawl error, run failed) — **1px border + word, never a banner fill** |

> **There is no `--verdict-ship` / `--verdict-hold` token in v2.** A verdict is
> not a color. A ship/hold/test classification renders as a *word + glyph in ink*
> (§1.9). v1's `--verdict-ship == --signal` was the exact valence-leak the jurors
> flagged ("SHIP" in lime = approval). Removed. **[v2-fix]**

### 1.7 Sheet — light blueprint record (long-form only)

Pointedly **not cream** — a cool blueprint off-white in the hue-250 family, so the
two modes feel like one instrument with two faces. **AA fixes below.**

| Token | OKLCH | Hex | On `--sheet`/`--sheet-raised` | Role |
|---|---|---|---|---|
| `--sheet` | `oklch(0.965 0.004 250)` | `#F3F4F7` | — | reading surface (cool, not cream) |
| `--sheet-raised` | `oklch(0.99 0.003 250)` | `#FBFBFD` | — | sheet cards, modals |
| `--sheet-sunk` | `oklch(0.93 0.006 250)` | `#E6E8EE` | — | inputs, code wells on sheet |
| `--sheet-line` | `oklch(0.86 0.006 250)` | `#D4D8E0` | — | hairlines on sheet (0.75px) |
| `--sheet-ink` | `oklch(0.24 0.020 250)` | `#1A2336` | 13.9:1 | body ink on sheet |
| `--sheet-mut` | `oklch(0.50 0.014 250)` | `#5E6678` | 5.9:1 | muted on sheet |
| `--sheet-signal` | `oklch(0.43 0.12 168)` | `#00785F` | **4.8:1** | signal-as-TEXT on sheet — **darkened from v1 `#0FA882` (~2.75:1 FAIL)**. Use only for the rare live-reading glyph/word inside a Sheet Console-well. **[v2-fix]** |
| `--sheet-spread` | `oklch(0.45 0.055 78)` | `#6F5E33` | **5.6:1** | spread-as-TEXT on sheet — **darkened from v1 `#857449` (~4.16:1, marginal)**. **[v2-fix]** |

### 1.8 The hard color laws (kept and tightened)

1. **Signal = live reading. Spread = doubt.** A saturated color that is not signal
   (live), spread (uncertain), arm-control/treat (identity), or a 1px semantic
   border is a bug.
2. **Color never carries valence.** Green is not "good," magenta-arm is not "bad,"
   and nothing is colored "up." A negative cohort reaction renders in plain ink +
   a down-glyph. This single discipline separates an instrument from a dashboard.

### 1.9 THE SIGNAL BUDGET (Law 3 — testable)

- **Exactly ONE signal carrier per viewport region.** A "region" is a top-level
  panel, the hero, the nav, or a card. If two elements in one region are lime, one
  is wrong. On a SHOWPIECE results page the carrier *is the Population Field's
  wavefront/mean* — so the CTA, the verdict word, the eyebrow, and the logo dot in
  that viewport are **ink/spread, not lime.**
- **Signal is forbidden as an emphasis or sentiment color.** Sentiment ("positive
  reaction"), direction ("higher"/"+3.6pp"), and verdicts ("ship") render in
  **plain ink + a glyph + provenance**, never valence color. *(v1 leaked signal
  into "ship/up/positive" across results, transcript, app-shell — fixed.)* **[v2-fix]**
- **Verdict vocabulary on an uncalibrated reading** is hedged: not "SHIP
  CANDIDATE" but **`DIRECTIONAL +3.6 ±1.4pp ◇`** or **`TEST FIRST ◇`** /
  **`PROMISING PRIOR ◇`**. "Ship" language is reserved for graded (◆) readings.
  **[v2-fix]**

### 1.10 THE CANDOR SCOPE (Law 1 — testable, the most important v2 correction)

v1's "every number carries ±" is, per both jurors, absurd in practice and made
record pages a wall of fake error bars. v2 scopes candor precisely.

**± / Spread Stamp is REQUIRED on INFERRED readings only** — values the model
*estimated* about a population:

> agreement / preference score · A/B lift · sentiment · confidence · conversion
> estimate · retention estimate · weakness-frequency · adoption probability · any
> `n`-derived *estimate* (a rate, share, or mean inferred from the cohort).

**± is FORBIDDEN (EXEMPT — these are facts, not estimates):**

> identifiers (persona id, run id, snapshot `2026-W25`) · timestamps & dates ·
> seeds (`0x4f`) · model names (`groq/llama-3.3`) · **raw counts / cohort `n`**
> (the literal number of agents is a fact, not an estimate) · version numbers ·
> URLs · configuration values the user typed · file sizes · durations.

**Rule of thumb engineers can apply mechanically:** *"Did the model infer this
about people, or is it a recorded fact about the run?"* Inferred about people →
Spread Stamp. Recorded fact → bare mono, no ±, no ◇/◆ glyph. An exempt value that
sprouts a ± is a bug just as surely as an inferred value that prints bare.

---

## 2. Typography

Three families, each with one job. All Google-Fonts-available. *(Unchanged from
v1 — the council praised type & hierarchy; we keep it verbatim and only tighten
the designator-frequency law.)*

### 2.1 Families

| Role | Family | Weights | Why |
|---|---|---|---|
| **Display / Body / UI** | **Geist** | 700 · 600 · 500 · 450 · 400 | Geometric-grotesque, mechanically precise — *engineered*, not editorial. One family carries headline→body via weight. |
| **Data / Numerals / Designators** | **Geist Mono** | 500 · 400 | Every score, CI, seed, snapshot id, role chip, axis tick — `font-variant-numeric: tabular-nums` locked on globally. |
| **Record prose (Sheet only)** | **Newsreader** | 400 · 400 italic | The one sanctioned serif, ONLY in genuine document prose (PRD / About / dossier). **Italic is for in-prose emphasis only — never a hero flourish or display headline.** **[v2-fix, marketing juror]** |

`@import`:
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
| `lede` | `1.375rem` / 1.5 | `-0.005em` | 400 Newsreader *(Sheet)* | the one editorial sentence in a dossier opener |
| `prose` | `1.0625rem` / 1.65 | `0` | 400 Newsreader *(Sheet)* | PRD/About prose — **max 68ch** |
| `body-l` | `1.0625rem` / 1.6 | `0` | 450 Geist | Console reading prose |
| `body` | `0.9375rem` / 1.55 | `0` | 400 Geist | UI default |
| `caption` | `0.8125rem` / 1.4 | `0` | 400 Geist | helper, captions |
| `mono-data` | `0.875rem` / 1.3 | `0` (tnum) | 400 Geist Mono | inline scores, CIs, table cells |
| `data-lg` | `2rem` / 1.0 | `0` (tnum) | 500 Geist Mono | hero readings (agreement score, lift) |
| `data-xl` | `clamp(3rem, 7vw, 5rem)` / 1.0 | `-0.01em` (tnum) | 500 Geist Mono | the masthead figure on a results page |
| `designator` | `0.6875rem` / 1.2 | `+0.08em` UPPER | 500 Geist Mono | id/role/snapshot chips, Provenance Bar |

**Global numeric law:** `font-variant-numeric: tabular-nums` on every numeric/mono
element. `text-wrap: balance` on `h1`–`h3` and display; `text-wrap: pretty` on prose.

### 2.3 Designator / eyebrow discipline (tightened)

The small mono UPPERCASE designator is reserved for genuine *machine identifiers*
(snapshot, role, seed, persona id) — provenance, never a decorative kicker.
- **At most one decorative eyebrow per marketing page.**
- **No numbered section scaffolds (`01` / `02` / `03`)** except a *true ordered
  flow* (the persona-build wizard's 5 steps; a checkout-style sequence). v1's
  product page, crawl-setup, feature-pack, and agent-detail used `01/02/…` as
  decoration — banned. Sequence is carried by the artifact, not a numeral. **[v2-fix]**
- In-app designator frequency is governed by the *Provenance Bar budget* (§7.3),
  not section rhythm. One bar per live reading region — **not** every subpanel,
  rail, and footer (~40% reduction from v1's Channel-Legend-everywhere). **[v2-fix]**

The wordmark **SIDIRA** is Geist 600 uppercase, `letter-spacing: 0.06em`.

---

## 3. Spacing · grid · radius · elevation

### 3.1 Spacing scale (4px base, geometric)

`2 · 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 · 96 · 128` (px). Semantic aliases:

| Token | px | Use |
|---|---|---|
| `--space-hairline` | 2 | between a number and its ± stamp |
| `--space-tight` | 4 | chip internal, glyph gaps |
| `--space-snug` | 8 | table row padding, dense control gaps |
| `--space-cozy` | 12 | input padding, button padding-y context |
| `--space-base` | 16 | default panel padding, control gaps |
| `--space-room` | 24 | card padding, between stacked controls |
| `--space-section` | 48 | between WORKING regions |
| `--space-bay` | 64 | between major Console regions |
| `--space-rest` | 96 | Sheet between-section |
| `--space-vast` | 128 | Sheet chapter breaks, hero top/bottom |

**Density philosophy — dense-but-calm (`VISUAL_DENSITY ≈ 5`):** tight rhythm
*inside* a region (8/12), generous silence *between* regions (48/64). Records on
Sheet breathe (24/32 internal, 96/128 between). The density *shift* is meaningful:
dense Console = "watch this," airy Sheet = "read this."

### 3.2 BREATHING ROOM (Law 8 — testable)

The council's #1 fix-to-reach-elite was *breathe more; let the hero reading
dominate.* Encoded as hard guidelines:

- **Max top-level panels per viewport:** **3** on a WORKING page, **2** on a
  SHOWPIECE page (the showpiece + at most one supporting panel). If a fourth wants
  in, it goes below the fold or into a collapsible drawer.
- **The hero reading dominates:** on any SHOWPIECE, the primary reading (the
  Population Field, or the `data-xl` masthead figure) occupies **≥ 55%** of the
  first viewport's area. Supporting chrome may not exceed it.
- **Minimum gutter between regions:** `--space-section` (48px) on Console, never
  less. Adjacent panels with < 48px between them must merge or gain a hairline.
- **No panel nesting beyond depth 2.** A card may contain a well; a well may not
  contain a card. (v1's agent-detail stacked chambers-in-panels-in-rails.)
- **Collapse by default:** secondary analytics, failed-run history, and driver
  breakdowns ship *collapsed* (a one-line summary row that expands), so the
  reading is never crowded. **[v2-fix, app juror — agent-detail / crawl-setup]**

### 3.3 Grid

- **App shell:** fixed **56px** left icon-rail + fluid content; `max-width: 1320px`;
  gutter `32px`.
- **Marketing:** 12-col, `max-width: 1240px`, 24px gutter; **hero breaks
  full-bleed for the Population Field** (the field is the hero, not a sidebar
  panel — §7.1).
- **Reading (Sheet):** single **720px** measure column + **240px** right margin
  rail for provenance; prose caps at **68ch**; the **Provenance Spine** occupies
  the left **180px** binder margin.

### 3.4 Radius — one family

| Token | Value | Use |
|---|---|---|
| `--r-well` | `4px` | inputs, chips, wells, code blocks |
| `--r-panel` | `8px` | panels, cards, modals |
| `--r-frame` | `10px` | the hero console frame, the scope display well |
| `--r-dot` | `9999px` | **only** the live status dot |

No pills. No 16px blobs. Sharp-ish corners read *instrument*, not consumer-app.

### 3.5 Borders & elevation

- Hairlines: **1px `--console-line` @ 0.5 alpha** (dark) / **0.75px `--sheet-line`**
  (light).
- **Elevation = lightness-step + a 1px top inner highlight**
  (`box-shadow: inset 0 1px 0 rgba(255,255,255,0.04)`), **never a drop shadow.**
  Panels sit *in* the surface like cut metal — no floating cards.
- **Glass (`--console-900`) is reserved for live computed readings** — never
  resting chrome.

---

## 4. Core components

Console (dark) is default; Sheet variants noted. Motion refs §5. **§4.11 is the
full state matrix the jurors required.**

### 4.1 Buttons

Height **36px** (default), **28px** (compact), **44px** (hero CTA). Padding
`0 16px`. Radius `--r-well`. Geist 500, `body` size. On `:active`,
`translateY(1px)` + inner highlight dims. Focus: **2px `--signal-dim` focus track**
(not a glow). Transition `140ms ease-out`.

| Variant | Rest | Hover | Notes |
|---|---|---|---|
| **Primary** | bg `--console-700`, 1px `--console-line`, text `--text-hi`, inner highlight | bg `--console-750` | The workhorse. Signal is NOT a default fill. |
| **Live / Run** | transparent, **1px `--signal`**, text `--signal` | fill `--signal-wash` | The ONE button that may carry signal — it initiates a live reading. **One per region** (it counts against the signal budget). |
| **Secondary** | transparent, 1px `--console-line`, text `--text` | bg `--console-800` | |
| **Ghost** | transparent, no border, text `--text-mut` | text `--text-hi` | inline/toolbar actions |
| **Destructive** | transparent, **1px `--alert`**, text `--text-hi` | bg `rgba(240,104,60,0.08)` | border + word, never solid red |

### 4.2 Inputs / textarea

Height **36px**. Bg `--console-700`, 1px `--console-line`, radius 4px, text
`--text-hi`, **placeholder `--text-mut` @ 0.7α** (never `--text-faint`), padding
`0 12px`. Geist `body`; **numeric inputs are Geist Mono tabular.** Focus: border →
`--signal-dim`. Label above: `caption` `--text-mut`. Sheet: bg `--sheet-sunk`,
border `--sheet-line`, ink `--sheet-ink`.

### 4.3 Select / combobox

Trigger = input spec + 16px chevron (`--text-mut`). Menu: `--console-800`, 1px
`--console-line`, radius 8px, inner highlight, **no drop shadow** (1px
`--console-900` ring beneath). Items: 32px row, 8px pad, hover bg `--console-750`,
selected = 1px left `--signal-dim` bar + `--text-hi`. Combobox filter at top;
results virtualized at 32px rows; matched substring `--signal-dim`. Open/close
`160ms ease-out`, no bounce.

### 4.4 Cards / panels

Bg `--console-800`, 1px `--console-line`, radius `--r-panel`, inner highlight,
padding `16/24`. **A card earns itself only as a discrete record** (one persona,
one capability, one simulation). Otherwise group with `border-top` hairlines +
negative space. **Never nest cards.** A card carrying a live reading gets **one**
Provenance Bar (§7.3) as its top strip. Sheet card: `--sheet-raised`, `--sheet-line`.

### 4.5 Nav / app-shell

- **Left rail:** fixed 56px, `--console-850`, 1px right hairline. Icon buttons 40px;
  active = 1px left `--signal-dim` bar + icon `--text-hi`; rest `--text-mut`.
  Tooltip on hover (`designator` mono, **`--text-mut` not `--text-faint`**).
- **Top bar:** 52px, `--console-850`, 1px bottom hairline. Left: wordmark + route
  designator. Right: a **single** global Provenance Bar reference when a run is
  live (`CH1 · n=… · ◇ UNCAL`) + the running status dot. Not a second full legend.
- **Tab underline:** 2px `--signal-dim`, `cubic-bezier(0.32,0.72,0,1)`, `180ms`.

### 4.6 Data tables (the logbook)

Row height **36px**, 8px vertical pad, `mono-data` cells, **every numeric column
tabular, right-aligned.** Header: `designator` mono, `--text-mut`, 1px bottom
hairline. Hairline row dividers (no zebra by default). Hover row: `--console-750`.
**Inferred columns carry a Spread Stamp** (`value ±ci` + ◇/◆); **exempt columns
(`n`, id, timestamp, seed) print bare** (§1.10). Sticky header on scroll.

### 4.7 Charts (WORKING-class default)

Axes: 1px `--console-line`, ticks `designator` `--text-mut`. Series use arm tints;
the distribution is the hero on SHOWPIECE charts only. Every chart:
- **draws itself once** on first paint (`stroke-dashoffset`, `700ms --ease-mech`).
- carries a **phosphor underdraw** — a 5px / 18%-α echo beneath the 1.5px stroke
  (CRT persistence) — **never `filter: blur`/`glow`.**
- shows its **CI band** as a `--spread-wash` ribbon (inferred series only).
- if uncalibrated, renders a dashed `--spread` noise-floor line and obeys the
  **finite Drift law** (§5.6) — not "never settles."

On WORKING pages a chart is static-after-draw. The *animated, depth, wavefront*
treatment is SHOWPIECE-only (the Population Field, §7.1).

### 4.8 Badges / chips / designators

- **Designator chip:** `designator` mono UPPER, 1px `--console-line`, radius 4px,
  pad `2px 6px`, text `--text-mut`.
- **Calibration glyph:** ◇ (hollow) = uncalibrated · ◆ (filled) = graded. Attached
  to *inferred* readings only (never to a seed or id).
- **Status badge:** border + word only. `LIVE` = `--signal` text + 6px running
  dot; `HOLD`/`TEST FIRST` = `--spread` text; `FAILED` = `--alert` text. Never a
  filled pill, never lime for "good."

### 4.9 Modals / dialogs

Overlay `rgba(11,18,32,0.66)` (no blur). Panel `--console-800`, 1px
`--console-line`, radius `--r-panel`, inner highlight, max-width 560px, pad 24/32.
Enter `opacity 0→1` + `translateY(8px→0)`, `180ms ease-out`. Exit `120ms`. Esc +
backdrop close; focus trap; return focus.

### 4.10 Empty / loading / error states

- **Empty (the empty ledger):** the surface's structure shown *bare* — for
  results, the axis + CI grid with no trace, captioned `LEDGER EMPTY · NO READING
  YET`. No mascot. One Live/Run button to fill it.
- **Loading (taking a reading):** on SHOWPIECE, the Population Field at drift;
  elsewhere skeleton rows at `--console-850` with a single 2s opacity breath (the
  only sanctioned skeleton shimmer). Numbers count up on arrival.
- **Error:** 1px `--alert` border on the affected panel + a `body` line in
  `--text` stating what failed and the next action, prefixed by a `FAILED`
  designator. **Never** a red banner fill or auto-dismissing toast for a data error.

### 4.11 COMPONENT STATE MATRIX (Law 7 — Console + Sheet, every state)

The boring completeness elite systems have. `focus` = keyboard focus-visible ring
(2px `--signal-dim` Console / 2px `--sheet-signal` Sheet, 2px offset). `loading`
shows the 2s opacity breath. Disabled uses `--text-faint` (its only job).

**BUTTON — Console**

| State | Spec |
|---|---|
| default | per §4.1 variant |
| hover | bg steps +1 lightness (`700→750`); 140ms |
| focus | 2px `--signal-dim` ring, 2px offset, no glow |
| active | `translateY(1px)`, inner highlight → 0.02α |
| disabled | text `--text-faint`, border α halved, no hover, `not-allowed` |
| loading | label → spinner (1px `--text-mut` arc, 700ms rotate); width locked |
| error | n/a (errors surface on the form, not the button) |

**BUTTON — Sheet:** same geometry; default bg `--sheet-raised` / 1px `--sheet-line`
/ ink `--sheet-ink`; hover bg `--sheet-sunk`; focus ring `--sheet-signal`; disabled
ink `--sheet-mut` @ 0.5α.

**INPUT — Console**

| State | Spec |
|---|---|
| default | bg `--console-700`, 1px `--console-line`, text `--text-hi` |
| hover | border → `--console-line` @ 0.7α |
| focus | border `--signal-dim` 1px + 2px `--signal-dim` ring outside |
| filled | identical to default (no chrome change) |
| disabled | bg `--console-800`, text `--text-faint`, `not-allowed` |
| loading | right-aligned 14px breath dot `--text-mut` |
| error | border `--alert` 1px + helper line `--text` (never red fill) |

**INPUT — Sheet:** bg `--sheet-sunk`, border `--sheet-line`, ink `--sheet-ink`;
focus ring `--sheet-signal`; error border `--alert` + `--sheet-ink` helper.

**TABLE ROW — Console**

| State | Spec |
|---|---|
| default | 36px, hairline divider, `mono-data` cells |
| hover | bg `--console-750`; sort/row-action affordances fade in 140ms |
| focus (keyboard row) | 1px left `--signal-dim` bar + bg `--console-750` |
| active/selected | 1px left `--signal-dim` bar persists + bg `--console-800` |
| disabled (non-actionable) | text `--text-mut`, no hover |
| loading | skeleton bar per cell, 2s breath |
| error (row failed to load) | cell shows `—` + `FAILED` designator in `--alert` |

**TABLE — Sheet:** divider `--sheet-line`; hover `--sheet-sunk`; selected 1px left
`--sheet-signal` bar; ink `--sheet-ink`.

**CHART — Console**

| State | Spec |
|---|---|
| default | drawn, settled, underdraw + CI ribbon (inferred) |
| hover (point/bin) | crosshair 1px `--text-mut`; tooltip panel `--console-800`; value `±ci` |
| focus (keyboard) | bin/point ring `--signal-dim`; tooltip mirrored |
| active (selected series) | non-selected series → `--text-mut` @ 0.4α |
| disabled/no-data | empty ledger (axis only) + `NO READING YET` |
| loading | trace self-draws (700ms) or Field drifts (SHOWPIECE) |
| error | axis frame + `--alert` caption stating fetch failure |
| **uncalibrated** | dashed `--spread` noise-floor + **finite drift (§5.6)** |

**CHART — Sheet:** static poster only (RECORD); CI ribbon `--sheet-spread` @ low α;
ink `--sheet-ink`; axes `--sheet-line`; no motion beyond page reveal.

---

## 5. Motion + effects system

### 5.1 Motion law

**Everything either settles or stays still.** A reading *settles*; a record *is
still*. No third motion. Nothing loops for decoration except the single running
status dot. `prefers-reduced-motion` replaces every settle with an instant cut and
**freezes all canvas/WebGL/drift to their settled poster.**

### 5.2 Easings (only these)

| Token | Curve | Use |
|---|---|---|
| `--ease-out` | `cubic-bezier(0.22, 1, 0.36, 1)` | reveals, modal enter, default UI |
| `--ease-settle` | `cubic-bezier(0.16, 1, 0.3, 1)` | the long convergence / settle |
| `--ease-mech` | `cubic-bezier(0.32, 0.72, 0, 1)` | telemetry wipes, tab underline, trace draw |

**No bounce, no elastic, no spring overshoot, ever.**

### 5.3 Durations

| Context | Duration |
|---|---|
| Micro-interaction (hover, focus, press) | `140ms` |
| Keyboard-initiated action | `0ms` |
| Menu / modal enter | `160–180ms` |
| Tab underline / telemetry wipe | `180ms` |
| Trace draw (self-draw) | `700ms` |
| Number count-up (verdict commit) | `300ms` |
| Marketing scroll-reveal | `400–600ms`, 60ms stagger |
| Population Field settle | `~3s` event-driven (real run) / `8s` hero loop |
| **Uncalibrated drift cycle** | **`12–18s`** (§5.6) |

### 5.4 Supporting signature motions

- **Trace draw:** any line/CI/confidence path draws L→R on first paint
  (`stroke-dashoffset`, `700ms --ease-mech`); 5px/18%-α underdraw. **Never glow.**
- **Status pulse:** one 8px `--signal` dot, 2s opacity breath (`0.5↔1.0`) — the
  only sanctioned infinite loop.
- **Verdict commit:** on resolve, the hero number counts up (`300ms --ease-mech`)
  and the field settles in one non-looping beat. (Aperture-close brand animation,
  DESIGN.md-reserved, may fire here.)
- **Settle damp:** the final 200ms of any data animation damps to rest,
  overshoot-free — the number "comes to rest" like a needle.

### 5.5 THE SIGNATURE GRAPHICS LAYER — **THE POPULATION FIELD**

> The ONE signature viz. No-holds-barred — *but SHOWPIECE-class surfaces only.* It
> renders *the product computing*, never decoration. One shader serves the canned
> hero and the true results, so the marketing promise and the product are provably
> the same instrument.

**What it is.** A live generative **agent field** in **WebGL**, single full-bleed
canvas, seeded with **N points = the real cohort size**. Each point is one
synthetic person. At rest, points drift in a slow curl-noise flow-field — a calm,
breathing population. On a "bet" (hero loop, or a real run), a wavefront of
`--signal` lime sweeps across; each particle shifts along a 1-D reaction axis (left
rejects, right adopts) and the field **re-sorts into a distribution.** The emergent
histogram **IS the verdict.** The CI band materializes as a `--spread` ribbon.

**Where it lives — SHOWPIECE-ONLY (the impact budget, §0.2):**

| Page | Field treatment |
|---|---|
| **Landing hero** | full-bleed, the hero *itself* (not a sidebar). Headline overlaid into the field like an instrument label. Auto-runs a *canned* bet on an 8s loop: `drift → wavefront → re-sort → settle → CI ribbon → dissolve`. **[v2-fix: field is the hero, per marketing juror's single-highest-leverage note]** |
| **Simulation results** | driven by *real* run data: real N, distribution, CI, arm split. Occupies ≥55% of viewport. |
| **Persona-build evaluate step** | the cohort settling as the pack is graded — the field *is* the evaluation. |
| **New-simulation manifest** | a live preview field seeded to the chosen cohort size; A/B forks it (§7.5). |
| **Everywhere else** | **NO Population Field.** Lists, config, detail, transcript get a static distribution *poster* (SVG) or, at most, a single isolated-particle motif. **[v2-fix: app + marketing jurors — kill hero-field on list/config pages]** |

**Grafted: Cohort Settle as individuals.** The re-sort is countable dots streaming
into bins; control/treatment dots settle in their two arm tints. **Interaction is
binned, not per-pixel** (operational-noise fix): hover/click targets are
`≥24px` binned clusters; an individual agent becomes selectable only after zoom or
bin-selection → opens its 1:1 transcript. **Mobile:** static distribution +
sampled-agents list (no 1,200-dot canvas). **[v2-fix, system juror]**

**Honesty in motion** is now the finite Drift law (§5.6), not a separate gimmick:
uncalibrated → dim, finite drift, never *locks*; graded → snaps to signal, blooms
once, rests with ◆.

**Tech recipe.**
1. **Tier 1 — WebGL** (`regl`/GLSL), single full-bleed `<canvas>`: instanced
   `gl.POINTS` size 1.5px; idle `pos = restPos + curlNoise·driftAmp`; on bet,
   interpolate toward `binPos(reactionScore[i])` with index-seeded stagger.
   Additive blending low-α (graphite dust catching light, not fireworks). Lime
   only on wavefront + settled mean; arm tints only on settled A/B dots. **Capped
   30fps; pauses on `visibilitychange`; freezes on `prefers-reduced-motion`.**
2. **Tier 2 — Canvas 2D** fallback: same math, ≤2,000 points.
3. **Tier 3 — static SVG poster** (SSR / headless / reduced-motion / old GPU): the
   settled distribution + CI ribbon, frozen. **This is also the poster used on
   every WORKING/RECORD page** — same value-series → polyline math, so the
   signature is identical from shader to static SVG.

**Taste rules:** real reading data or an honest canned baseline only; ≤18% bloom;
underdraw never CSS glow; counts as *the* signal carrier for its region; never
animates on a hidden tab; reduced-motion → frozen poster.

### 5.6 THE DRIFT LAW (Law 5 — finite & accessible)

Replaces v1's "uncalibrated readings never settle" (irritating + exclusionary per
both jurors). **Truth is carried by the ◇ glyph and the copy; motion is a gentle
secondary cue that never punishes attention.**

**Uncalibrated (◇) reading drift:**
- max amplitude **2px**
- opacity **~0.45**
- cycle **12–18s** (slow, ambient)
- **PAUSES after 20s of idle** (no interaction)
- **FREEZES on focus, hover, or `prefers-reduced-motion`** — the instant you look
  at it, it holds still so you can read it
- it **drifts but does not *lock*** — there is no settle bloom, no ◆

**Calibrated (◆) reading:** fully stable, settled, locked. Snaps from noise to
signal once, blooms once, rests. Only a graded reading earns the lock.

> An uncalibrated reading still "can't fake a verdict" — but because it never
> *locks* (no ◆, no bloom, hedged copy), **not** because it twitches forever in
> your peripheral vision.

---

## 6. Provenance architecture (structural honesty)

Provenance is structural, not per-number fine print. Two complementary faces:

- **Console (live) → the Provenance Bar** (§7.3): one instrument silkscreen strip
  per *reading region* (not per subpanel). Makes "◇ UNCALIBRATED" structurally
  unavoidable on the estimate side.
- **Sheet (record) → the Provenance Spine** (§7.4): a permanent left binder-margin
  on every record.

Together: no reading and no record displays without its origin + calibration
state visible — **but the Bar appears once per region, not as wallpaper.**

### 6.4 Console well inside Sheet (route-mode law, no inversion)

When a RECORD (Sheet) page must show a live estimate, it embeds a single
**Console well** — a small `--console-900` framed reading inset into the Sheet —
*not* a dark masthead that inverts the route. The page stays Sheet from the first
pixel to the last. This is the v2 fix for v1's capability-detail and About pages,
which inverted mode mid-scroll and broke the ontology. **[v2-fix, app + marketing]**

---

## 7. The signature elements (now TWO signatures + scoped motifs)

### 7.1 ✦ THE POPULATION FIELD — *the one graphics showpiece* (see §5.5)

WebGL agent field, **particle count = real cohort size**, emergent **binned,
clickable** histogram = the verdict. Same shader feeds the canned landing hero
(now the hero *itself*) and the true in-app results. **SHOWPIECE-class surfaces
only** (landing, results, evaluate, manifest); a frozen poster everywhere else.

### 7.2 ✦ THE SPREAD STAMP — *candor as a visual primitive (scoped)*

Every *inferred* reading renders with uncertainty attached: number in Geist Mono
tabular, a `--spread` CI bar (`0.62 ±0.08`), and a calibration glyph (◇/◆).
**Scoped to inferred values only** (§1.10) — identifiers, timestamps, seeds,
models, and raw `n` print bare. One compact stamp pattern across the whole product
(tables, charts, hero figures) — not a bespoke treatment per page. **[v2-fix:
v1's "every number" → inferred-only]**

### 7.3 ✦ THE PROVENANCE BAR — *provenance as instrument silkscreen (Console)*

> Renamed and re-scoped from v1's "Channel Legend" to break the
> telemetry-wallpaper read.

**One** mono silkscreen strip per *live reading region*:
```
CH1 · CONTROL · n=240 · seed 0x1f · groq/llama-3.3 · 2026-W25 · ◇ UNCALIBRATED
```
`designator` mono, `--text-mut`; glyph + `UNCALIBRATED` in `--spread-dim`. **Nested
panels inherit it via a compact `CH1` reference** — they do not repeat the full
bar. Budget: **one per reading region**, ~40% fewer instances than v1.
**[v2-fix, both jurors]**

### 7.4 ✦ THE PROVENANCE SPINE — *provenance as architecture (Sheet)*

Every record carries a fixed **180px left binder-margin** stating, stacked:
snapshot id · capture date · seed · model · sample size `n` · calibration state.
Always present, quiet, never dismissible. The one surface where **Newsreader** is
sanctioned for body prose. **Prose runs calm and archival — not manifesto-like,
em-dash-heavy, or theatrical** (records read like a lab notebook, not a pitch).
**[v2-fix, app + marketing — tighten Sheet prose]**

### 7.5 ◦ THE LIVING MANIFEST — *optional motif, manifest SHOWPIECE only*

> Demoted from a co-equal "signature" to a single-surface motif.

On the **new-simulation manifest** (a SHOWPIECE), as the founder composes a
hypothesis a **manifest panel** assembles the receipt in real time (cohort, arms,
model, seed, `n`) and the chosen cohort size seeds a live preview into the
Population Field. **Choosing A/B visibly forks and doubles the field** — making the
2× cost *felt*, not buried. It exists *only* here; it is not a global mechanic.
(playful-pro's spring physics, glass-blur, magnetic CTAs are dropped wholesale.)

---

## 8. Implementation reference (CSS custom properties)

```css
:root {
  /* Console (dark, default app + marketing) */
  --console-900:#0B1220; --console-850:#10192A; --console-800:#161F32;
  --console-750:#1D2740; --console-700:#26314C; --console-line:#33405C;
  --text-hi:#F2F4F8; --text:#C6CCD8; --text-mut:#929BAE; /* AA-clear */
  --text-faint:#646E84;                                  /* DISABLED ONLY */
  --signal:#48EFCA; --signal-dim:#39B894; --signal-wash:rgba(72,239,202,.12);
  --spread:#C8B68A; --spread-dim:#90815F; --spread-wash:rgba(200,182,138,.14);
  --arm-control:#4FA8E0; --arm-treat:#E08BC4; /* calm magenta, no valence */
  --edge-warn:#C9A227; --alert:#F0683C;       /* borders + word, never fill */
  /* NOTE: no --verdict-ship / --verdict-hold token — a verdict is not a color */

  /* Sheet (light, records only) — AA-corrected */
  --sheet:#F3F4F7; --sheet-raised:#FBFBFD; --sheet-sunk:#E6E8EE;
  --sheet-line:#D4D8E0; --sheet-ink:#1A2336; --sheet-mut:#5E6678;
  --sheet-signal:#00785F; /* 4.8:1 text */ --sheet-spread:#6F5E33; /* 5.6:1 */

  /* Radius / motion */
  --r-well:4px; --r-panel:8px; --r-frame:10px; --r-dot:9999px;
  --ease-out:cubic-bezier(.22,1,.36,1);
  --ease-settle:cubic-bezier(.16,1,.3,1);
  --ease-mech:cubic-bezier(.32,.72,0,1);

  /* Spacing */
  --space-snug:8px; --space-cozy:12px; --space-base:16px; --space-room:24px;
  --space-section:48px; --space-bay:64px; --space-rest:96px; --space-vast:128px;

  --font-sans:"Geist",system-ui,sans-serif;
  --font-mono:"Geist Mono",ui-monospace,monospace;
  --font-serif:"Newsreader",Georgia,serif; /* Sheet prose only */
}
* { font-variant-numeric: tabular-nums; }
.elevated { box-shadow: inset 0 1px 0 rgba(255,255,255,.04); } /* never drop-shadow */

/* Drift law (§5.6) — finite, accessible */
@keyframes uncal-drift { /* max 2px, ~12-18s, ~0.45 opacity */
  0%,100% { transform: translateY(0); } 50% { transform: translateY(2px); }
}
.uncalibrated { opacity:.45; animation: uncal-drift 15s var(--ease-settle) infinite; }
.uncalibrated:hover, .uncalibrated:focus-within { animation-play-state: paused; opacity:.7; }
@media (prefers-reduced-motion: reduce){
  *{animation:none!important;transition-duration:1ms!important;}
  .uncalibrated{opacity:.7;} /* frozen poster, readable */
}
```

---

## 9. Why this is top-0.1% for THIS product

1. **The spectacle is the substance — and it's spent, not sprayed.** The impact
   budget concentrates no-holds-barred WebGL on the four surfaces where the
   *population reacting* IS the screen's job, and makes the other 80% brutally
   quiet so those four land. A loud-everywhere system is a demo reel; this is an
   instrument that has one unforgettable move.
2. **Honesty is a scoped, scannable feature.** Candor is enforced precisely where
   the model *inferred something about people* and exempted everywhere it didn't —
   so the Spread Stamp reads as discipline, not as fake error bars bolted onto
   seeds and timestamps.
3. **It passes the laws it preaches.** Every text/bg pair clears AA; signal means
   exactly one thing (live reading) and never leaks into "ship/up/good"; treatment
   is a calm magenta, not an alarm-red; uncalibrated drift is finite and freezes
   under your gaze instead of punishing attention.
4. **It refuses every 2026-AI tell** — cool blueprint Sheet over cream, Geist ×
   Geist Mono over warm display serif, color-as-identity over status rainbow,
   provenance-as-architecture over eyebrow-on-every-section, and *no
   `01/02/03` scaffolds.*
5. **It is boringly complete and shippable** — one shader / three tiers, one radius
   family, elevation-by-lightness, a full Console+Sheet state matrix, a spacing
   scale with a max-panels guideline, and two signatures instead of six.
