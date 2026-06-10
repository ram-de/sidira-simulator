# Sidira Design Rework Proposal — "Paper bench, glass display"

**Date:** 2026-06-09 · **Status:** PROPOSED R2 (Codex-amended) — awaiting founder re-review before any DESIGN.md change
**Preview:** `/tmp/sidira-rework-proposal.html` (ephemeral, R2) · **Compare against:** `/tmp/sidira-paper-temperature-board.html`
**Inputs:** five parallel skill consultations — design-shotgun (gstack), design-taste-frontend + frontend-design, design-motion-principles, ui-ux-pro-max + impeccable, design-review + design-consultation (gstack) — plus an independent Codex review (see "Codex consult" below).
Agent IDs: shotgun ab023f30fd18f0502 · taste a61113f262708d418 · motion a4a0c6cd996b50bca · audience a8e74aa95e25263be · gatekeeper ae2b5ef2f3aa16b8c · codex session 019eaeb6-0c81-70a0-b94f-5454727b3a70 (`.context/codex-session-id`).

## Coherence argument (one paragraph)

The thesis stays "this looks like an instrument, not software" — but the metaphor gets completed. A real instrument is a matte bench with a dark glass display; today Sidira is all bench and no display, which is why signal lime (a phosphor color) fails at ~1.1:1 contrast on cream and has to be secretly underdrawn in ink. The rework keeps paper as the product surface (the decision record), adds one new surface — instrument glass `#0A1421` — where live readings render (where lime reaches ~14:1), and makes everything on screen either *a reading* (glass, lime, settles) or *a record* (paper, ink, static). That same split carries the moonshot: simulated readings on glass, graded decisions on paper, the lineage rail showing the OKR→rollout pipeline between them.

## SAFE choices (deliberately kept)

- The mark, wordmark, type scale, spacing scale, radius scale (2/4/6), refuse list — untouched.
- Paper-first product. Dark mode remains §4.5 follow-on; glass is a *component surface*, not a theme.
- §9.1 settle trace stays the signature motion, same 800ms bezier.

## RISKS (named, with cost)

1. **Glass wells could read as "dark mode creep."** If glass spreads beyond live readings (nav, cards, marketing), the brand bet dissolves into a generic dark dashboard. Cost if it goes wrong: rip-out across every results surface. Containment: hard rule — glass is sanctioned ONLY for live instrument readings (traces, CI axes, running states); never for chrome, tables, text content, or marketing.
2. **Credibility layer outruns the backend.** "Calibrated confidence 0.78", Brier 0.11, CAL ledger n=142 are designs for data the product must actually compute. Shipping the UI before the isotonic calibration exists = credibility theater, the worst failure mode for a DS audience. Containment (hardened per Codex): **no calibrated/Brier/isotonic UI ships until the backend computes and exposes it, with a visible calibration ledger the user can open.** Until then the UI shows the honest state ("UNCALIBRATED — 0 graded predictions") and the headline number is labeled as raw simulation agreement, not calibrated probability. Same gate applies to the decision-policy primitive: the threshold shown must be a real, persisted per-objective policy, not copy.
3. **Decorative instrument marks.** Any trace, tick, or band that is not bound to real run data is "instrument cosplay — worse than no trace" (Codex). Containment: codified as a refuse-list rule in the §8 delta — every mark on glass renders from backend data or it doesn't render.
4. *(deferred per founder decision, 2026-06-09)* Cooling paper to `#F5F2EB`. Codex flagged the cool-shift as possible overfitting to the swatch board; founder agreed. **Paper stays `#F4EFE6`** in this proposal and in the preview. The cooling question re-opens only via a side-by-side comparison on real product screens, not swatches.

## Proposed DESIGN.md delta (no edits made yet)

### §3 Surfaces
- Paper temperature **unchanged**: `paper #F4EFE6` · `paper-elevated #FAF6EE` · `paper-recessed #EBE5D8` stay as specced. (Cooling to `#F5F2EB` deferred — see Risk 4.) The only paper-side change: `rule → rgba(14,26,43,0.16)` (true hairline, replaces solid `#D6CFC0`).
- **NEW `glass #0A1421`** + `glass-rule rgba(244,239,230,0.08)` + `glass-text #F4EFE6` + `glass-muted rgba(244,239,230,0.55)`. Sanctioned only for live instrument readings. Radius 4, 1px glass-rule border.
- Layering spec: recessed = `inset 0 1px 2px rgba(14,26,43,0.07)`; elevated = hairline border + `inset 0 1px 0 rgba(255,255,255,0.55)` top highlight. Drop shadows remain banned. Max 3 paper levels + glass.

### §4 Color
- §4.1 amendment: lime's primary home is glass. On paper, lime requires an ink companion stroke ≥3:1 (codifies the existing underdraw hack as law).
- **NEW `success #2F6B3F`** — closes the root-cause gap behind the ~20 off-token green/blue/red hexes in production.
- Phosphor persistence: lime traces on glass get a 5px/18%-opacity underdraw of the same path. Never CSS glow/blur.

### §5 Type
- Purchase: Söhne (Buch/Kräftig/Halbfett + Schmal) ~$350–500, Berkeley Mono $75. Alternates if Klim stalls: ABC Diatype / Untitled Sans.
- Fallback stack change: Hanken Grotesk → **Archivo** (same superfamily as the Archivo Narrow wordmark fallback — one voice).
- **Drop GT Sectra Fine entirely.** Marketing display voice = Söhne Schmal Halbfett 64–96px uppercase. (Kills AI-slop tell #1.)
- Floors: no text <10px; <12px only as uppercase mono labels/numerals. Hypothesis statement demotes to 16/600; the reading numeral is the hero (84–96px mono).

### §7 Layout
- Three-zone panel confirmed. NEW components: **lineage rail** (SIMULATED→VALIDATED→PRD→ROLLOUT→GRADED + STAGE n/5 chip, every hypothesis screen), **telemetry key/value grid** (replaces middle-dot strips), **provenance grid** (two-column dt/dd, replaces dot-separated footers).
- Eyebrow rationing: mono-caps zone labels only where position doesn't already name the zone.

### §8 Data furniture
- Frequency bars: bare 2px ink bars, no gray tracks. CI axis: SVG with real ticks + 10px mono scale numerals **and the decision threshold marked on the axis**. Headline number = **calibrated probability** (e.g., 0.78), never unitless "78/100"; every aggregate carries unit-explicit n ("240 readings · 48 personas · 5 seeds"); seed-variance strip beside headline numbers, **always labeled** ("SEED VARIANCE σ = 0.021", never a bare glyph strip); "how computed" methodology affordance on every statistic; verdict lexicon fixed: DECISIVE / DIRECTIONAL / UNDERPOWERED.
- **NEW: decision-rule primitive (Codex's core addition).** Every verdict renders with its decision policy beside it — threshold, margin, and rule (e.g., `THRESHOLD 0.70 · POLICY DR-2 · MARGIN +0.08 · SHIP IF P ≥ 0.70 AND EVERY HIGH RISK HAS A NAMED MITIGATION`), plus a one-line "why this verdict" under the hypothesis statement tying the verdict to threshold, expected lift, and the gating mitigations. A verdict chip without its policy is banned. This is what separates decision intelligence from a prettier simulation report — and it serves the VP (cost-of-being-wrong) directly.
- **Data-bound marks only (refuse-list addition).** Every trace/tick/band on glass is rendered from real run data. The confidence trace is the literal running estimate over readings (axis-labeled); never a decorative waveform.
- **Lift is paired-difference, not a second waveform.** Control tick → digest tick on a labeled rate axis with the delta CI band — matching the repo's existing paired A/B lift semantics (`frontend/app/simulations/[id]/page.tsx`).
- Negative sentiment counts are data, not alarms: ink-muted, never alert-red. Red stays reserved for risk/error severity.
- Grading internals (REALISM scores) never shown on buyer-facing surfaces.
- Engineer surface: provenance grid includes run ID + timestamp and artifact links (readings.csv, transcripts, API) on every reading screen.

### §9 Motion (full spec from motion consultation)
- §9.3: add `--ease-mech: cubic-bezier(.32,.72,0,1)`; telemetry wipe 240ms; tab underline 160ms; content crossfade 120ms; press = translateY(1px) at 0ms, release 80ms.
- NEW §9.4 "Reading choreography": t=0 static text → 0–240ms telemetry wipe → 120–920ms confidence trace + CI marker sweep (transform-only) → 280–1080ms lift trace → 800ms numeral fade → 940ms CI band scaleX → 960ms+ register stagger (30ms steps, one staggered list per view) + inspector fade. Total ≤1300ms. Fires once per data arrival, never on revisit.
- NEW §9.5 "Live carrier": the single sanctioned pulse — 2px lime underline under STATUS RUNNING, 3.4s ease-in-out, opacity 0.45↔1.0, phase-locked to the aperture loop. Nothing else ever pulses.
- NEW §9.6 "Marketing motion": signal-path draw (OKR→…→ROLLOUT, 1600ms, once) + calibration convergence (1200ms, once). Hero settle. Nothing else.
- NEW §9.7 "Live plotting": while STATUS = RUNNING, the confidence trace extends point-by-point as reading batches land — event-driven (batch graded → point plots), never time-based. The trace IS the progress indicator; spinners and progress bars are banned. Each new point appears instantly (no per-point tween — it's a measurement, not an animation); the only continuous motion during a run is the §9.5 carrier + aperture loop. Verdict chip reads READING IN PROGRESS, numerals show `—.——`, register shows REGISTER PENDING — pending states are honest text, never skeletons. On the final batch, hold ~400ms, then fire §9.4 once to commit the reading. Reduced-motion: trace still extends (it's data), §9.4 lands on its settled frame.
- Every §9 entry must declare its `prefers-reduced-motion` end state (settled frame).

### §1.3 (separate decision)
- The duo-mark favicon contradiction (§1.3 vs §4.4) still needs resolution — independent of this proposal.

## Codex consult (2026-06-09)

Independent review by Codex (session `019eaeb6-0c81-70a0-b94f-5454727b3a70`, resumable via `codex exec resume`). Verdict: **"Approve with changes, not as-is."** All changes are folded into this R2 and the preview:

1. Glass sanctioned only for live computed readings (containment essential, or it's "another dark SaaS dashboard") → already Risk 1; language kept hard.
2. Lime traces must be data-bound, never decorative → Risk 3 + §8 refuse-list addition; preview trace now draws the actual running-estimate series with axis labels.
3. Lift as paired-difference visualization, matching the result page's existing paired A/B semantics → §8; preview rebuilt.
4. No calibrated/Brier/isotonic UI until the backend computes it, with a visible calibration ledger → Risk 2 hardened.
5. **Biggest gap: decision calibration, not statistical calibration** — a verdict chip with no decision policy. → NEW decision-rule primitive in §8; preview shows threshold/margin/rule beside 0.78 and a "why this verdict" line.
6. Seed variance strip too cryptic → labeled in §8 + preview.
7. Mute negative sentiment counts; fill the dead space right of the headline numeral with decision-threshold context → §8 + preview.
8. Keep warm paper `#F4EFE6` unless cooling is proven on real product screens → Risk 4, founder agreed 2026-06-09.

Audience read (Codex): PMs best served; VPs under-served without cost-of-being-wrong (addressed by the decision-rule primitive); DS conditionally served (claims must stay inspectable — methodology card + gating); Engineers under-served (addressed by the expanded provenance grid + artifact links).

## Adjudicated disagreements between consultations

- **Dark default (shotgun) vs paper-first (gatekeeper):** resolved via glass wells — paper keeps the brand, glass gets the demo-ability and the lime contrast. If glass wells underwhelm in review, fallback is "Reading Room" (current spec fully executed), not a dark theme.
- **Count-up numeral (taste) vs no-odometer rule (motion):** motion wins — numerals fade in over the trace's final 120ms, never tick.

## Acceptance bar (from review gate — checked against the preview)

lime ≤8% any viewport, ink companion on paper ✓ · radius ≤6, no pills ✓ · 100% tabular numerals ✓ · type floor ≥10px ✓ · every motion mapped to a §9 name, transform/opacity only (marker + digest-tick sweeps transform-based) ✓ · ≤3 paper levels + glass ✓ · paper temp: stays `#F4EFE6`, cooling deferred to in-product evidence ✓ · zero AI-slop tells ✓ · loading/empty/disabled states demonstrated (running-state toggle, incl. policy-aware pending verdict) ✓ · every glass mark data-bound ✓ · verdict carries its decision policy ✓ · SAFE/RISK + coherence in this doc ✓

## Rollout if approved

1. PR 1: DESIGN.md amendments + `lib/design.ts` token update (same diff), via worktree.
2. PR 2: globals.css + token sweep killing the ~20 off-token hexes (uses new `success`).
3. PR 3: result page → instrument panel (this preview's structure) with reading choreography.
4. Parallel: font purchase; marketing hero rework; calibration ledger page when backend supports it.
