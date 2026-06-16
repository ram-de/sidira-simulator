# Design System v2.1 — LAW-ENFORCEMENT PATCH (Round 3)

This patch sits ON TOP of `design-system-v2.md`. It does not change the system —
it codifies, as mechanical pass/fail checks, the cross-cutting law-breaks the
Round-2 jury found in almost every mock. Every page must pass ALL of these.
Where this patch and a page conflict, this patch wins.

## P1 — The resting logo mark is ALWAYS ink. Never lime.
The wordmark / logo dot in the persistent nav or rail is brand chrome, not a
live reading. It must render in `--text-hi` / `--text-mut` / `--console-line`
— NEVER `--signal` (#48EFCA). Lime in a viewport means exactly one thing: a live
reading is happening there. A resting brand mark is not a reading.
(Brand-mode dual/lime mark is reserved for public brand surfaces per DESIGN.md
— and even there, not when a live signal carrier shares the viewport.)

## P2 — One signal carrier per viewport region. Count them.
For each region, count elements rendered in `--signal`/`--signal-dim`. The count
must be **1** (or 0 on RECORD pages). When the Population Field carries the
signal, the CTA in that region is **ink** (`.btn-primary` ink), not a lime
`.btn-live`. Demote to `--text-mut`/`--spread`/ink, in priority order:
- channel/CH legend labels (a designator is not a carrier),
- sort arrows and other affordances (decorative emphasis),
- secondary status dots, second eyebrow dots,
- "create/new/primary" buttons that do NOT initiate a live reading
  (e.g. "New hypothesis", "New bet" → `.btn-secondary` ink).
A lime button is permitted ONLY when it initiates a live reading (Run / Read now).

## P3 — Exactly ONE infinite loop on a page: the status dot.
Per §5.1/§5.4 only the 2s status-dot breath may loop forever. Forbidden:
- perpetual lime "wavefront" sweeps (make them ONE-SHOT: fire on
  seed/focus/chip-change, then rest to pure curl-drift),
- "composing" equalizer bars (replace with the single breathing dot + static
  label),
- any count-up/re-sort/dissolve loop that re-runs (run ONCE on entry, then hold
  the settled poster).

## P4 — Drift is a HARD ≤2px ceiling.
Uncalibrated drift: amplitude **≤2px**, opacity ~0.45, cycle 12–18s, PAUSE after
20s idle, FREEZE on hover/focus/`prefers-reduced-motion`. Any `driftAmp` or
equivalent above 2px is a hard fail (R2 `simulations-new` shipped 16px — 8× over).
The idle-population "breathing" baseline is NOT exempt: keep it ≤2px too, so the
field reads as breathing, not churning.

## P5 — Static posters use `--signal-dim`, never bright `--signal`.
A frozen/settled distribution poster is not a live reading. Its trace/mean line
uses `--signal-dim` (or dimmer ink), never the bright live `--signal`. A figure
stamped "STATIC · NO READING RUNNING" with a bright lime trace is a hard fail.

## P6 — Verdict vocabulary is gated on calibration state.
On an uncalibrated reading (◇ / "LEDGER EMPTY" / "RAW · UNCALIBRATED") the verdict
may NOT say "SHIP" / "SHIP CANDIDATE" / "HIGH … · SHIP". Use the hedged register:
`DIRECTIONAL +X ±Y ◇`, `TEST FIRST ◇`, `PROMISING PRIOR ◇`. "Ship" language is
reserved for a graded ◆ reading with a populated ledger. The verdict renders in
ink + glyph; spread-amber at most for a HOLD; never lime for approval.

## P7 — `--text-faint` (#646E84) is DISABLED-ONLY.
Never on ids, separators, axis labels, captions, placeholders, or provenance.
Those go `--text-mut` (#929BAE) or brighter. Provenance/honesty text especially
must clear AA — bump uncalibrated WORDS to `--text-mut`; reserve `--spread-dim`
strictly for the ◇ glyph and the ± value, not running words.

## P8 — Candor scope is mechanical, both directions.
- Every INFERRED reading wears ± + ◇/◆: a rate/share/mean/lift/sentiment/
  confidence/percentile inferred from the cohort — INCLUDING ones buried in
  build logs ("STABILITY 0.71" → "0.71 ±0.04 ◇") and cohort-mean deltas
  ("↑ +0.33 above" → "+0.33 ±0.NN ◇").
- EXEMPT facts must print BARE — no ±, no ◇: ids, timestamps, seeds, model
  names, raw counts/n, versions, URLs, config, durations, snapshot weeks.
  A ◇ trailing an id ("cr-924718 ◇", "2026-W26 ◇") is a hard fail; carry
  uncalibrated state ONCE via the region's provenance marker.
- A k-means centroid coordinate / per-segment rate IS inferred — do NOT caption
  it "RECORDED FACT". (R2 `persona-detail` mislabeled inferred snapshot means.)

## P9 — Impact budget: the live Population Field is SHOWPIECE-ONLY.
The live WebGL/Canvas field is earned on EXACTLY four archetypes:
**landing hero · simulation-results · personas-new (evaluate) · simulations-new
(manifest)**. Everywhere else — including **app-shell / dashboard** — replaces it
with a static Tier-3 SVG distribution poster or a single isolated-agent motif.
(R2 `app-shell` shipped a live field — hard fail; reclassify WORKING, use poster,
let the reading + bets list dominate.) And no page may run the field TWICE
(R2 `landing` ran hero + closer fields — the closer becomes a quiet ink/hairline
CTA band).

## P10 — One reading dominates; resting hero reading is legible.
The page's marquee inferred figure must be the visual focus on first paint, NOT
the faintest thing. A hero reading drifting at opacity 0.45 while exempt facts
sit at full ink is an inverted hierarchy (R2 `capability-detail`). Lift the
resting hero figure to ~0.7+ (stamp/glyph full), keep ONLY the ≤2px drift as the
uncalibrated cue. Static posters must be interrogable (arm opacity ≥0.6, a
baseline + mean label), not 0.42α glyph-soup.
