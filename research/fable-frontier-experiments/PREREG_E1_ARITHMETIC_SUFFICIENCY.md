# PREREG — E1: Arithmetic-Sufficiency Test (tier-1 composition calculator)

**Campaign:** fable-research data-efficiency frontier (sessions/fable-research/PAPER.md §7-E1)
**Date sealed:** 2026-07-01, before any case generation, calculator code, or LLM call.
**Discipline:** self-blinding generator (answers written to a separate sealed file, sha256-fingerprinted, never read by any predictor path); scoring only after all predictions are recorded.

## Question

Is the tier-1 standardized aggregate schema (segment × mediator-bin × outcome cross-tabs + segment moments) **sufficient** for a small deterministic composition calculator to call the direction of composition-driven changes — the regime where the paper's data-efficiency frontier claims tier-1 verdicts are possible? And does a frontier LLM *given the same tables* match it?

## Case material

**Leg A — synthetic composition battery (self-blinded, fresh generation).**
`gen_composition_battery.py`, seeded RNG (seed=20260701). 24 cells across 3 composition families, 12 of them **flip cells** (constructed so the prose narrative reads opposite to or ambiguous about the arithmetic truth), 12 one-sign cells (narrative and arithmetic agree):

- **F1 mix-flip (Simpson):** change shifts traffic mix between segments with different per-segment rates; per-segment rates move one way (or not at all), the mix moves the aggregate the other way.
- **F2 gross-vs-net:** change raises a per-unit take (fee, price, upsell rate) while lowering volume (or vice versa); net revenue sign decided by the relative magnitudes in the tables.
- **F3 trade-down / cannibalization:** change adds a cheaper/easier option that draws from both non-buyers AND an existing premium option; net sign decided by source-mix magnitudes.

Each cell emits: (a) a prose hypothesis (PM-style, no numbers beyond what a PM would say); (b) the tier-1 export: baseline segment sizes + per-segment/per-bin outcome rates + the change's observed movement expressed ONLY as tier-1-visible aggregates (e.g., pilot/observed shift shares); (c) sealed truth = the sign of the aggregate effect computed from the generator's internal full specification. Truth values go to `e1_answers.json` (sha256 sealed in `e1_answers.sha256` at generation time).

**Leg B — real data (Cookie Cats).** Collapse the real 90,189-row Cookie Cats table to the tier-1 schema per arm (segment = engagement tercile computed from `sum_gamerounds` bins; mediator-bin = gamerounds bins; outcome = retention_7, retention_1). The calculator must recover the known counter-intuitive negative (gate_40 loses on retention_7 AND retention_1) **from the collapsed tables alone**. No row-level access in the calculator path.

## Predictors

1. **CALC** — deterministic composition calculator (~≤100 lines): translator output (mechanism family + which table fields constitute the shift) → arithmetic over the tier-1 tables → sign + ABSTAIN if the required cells are missing or the sign is not stable to ±20% perturbation of the shift-share inputs (pre-registered stability band).
2. **LLM-TABLES** — frontier LLM (claude-opus-4-8 via Anthropic API, temperature 0) given the SAME prose + SAME tier-1 tables, forced-choice direction + optional abstain. This is the fair baseline (not the words-only 0.00).
3. **CHANCE** — 0.50 reference.

The translator step for CALC uses the same LLM (claude-opus-4-8) but ONLY to map prose → (family, field bindings); it never outputs a sign. A mis-binding that the calculator detects (missing cells) → ABSTAIN, not a guess.

## Pre-registered outcomes

- **PASS (tier-1 wedge is real):** CALC ≥9/12 correct-and-confident on flip cells with **zero confident-wrong** (abstains don't count against, but >6/12 abstain on flips = FAIL-by-abstention); Cookie Cats sign recovered from collapsed tables on both retention metrics; zero confident-wrong on the 12 one-sign cells.
- **KILL:** any confident-wrong on flip cells, or <6/12 correct → the tier-1 verdict rung does not exist as designed; the ladder's middle rung is tier 1.5/2 (paper's dissent #2 resolves against tier 1).
- **Secondary (informational, not gating):** LLM-TABLES accuracy on the same cells — if LLM-TABLES ≈ CALC, the tier-1 information sufficiency claim is confirmed by two independent readers; the calculator still wins on determinism/auditability/cost. If LLM-TABLES ≪ CALC, tables alone don't rescue an LLM (magnitude-use failure survives table access — a NEW negative result worth recording).
- **Meta-rule (from the paper):** a synthetic pass is necessary-not-sufficient; only Leg B (real data) evidence is promotable language.

## What this does NOT test

Mediator-driven flips (deferred to E3's full battery with donor surfaces); transported surfaces; the conformal gate (E4). E1 is only the "is the arithmetic information present and extractable at tier 1" question.
