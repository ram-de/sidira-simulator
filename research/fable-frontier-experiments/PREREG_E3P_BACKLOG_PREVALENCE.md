# PREREG — E3-P: Backlog-Prevalence Study (tier-1 realistic-coverage arm)

**Campaign:** fable-research data-efficiency frontier (PAPER.md §7; DEBATE_CONCLUSION.md joint priority #1 — codex's requested "additional evidence" for its standing dissent on tier-1 generalization).
**Date sealed:** 2026-07-01 — before any case assembly, any candidate search, any pipeline run.
**Discipline:** this prereg is fingerprinted and lands on `main` before the backlog exists. Case assembly is performed AFTER sealing, under the sourcing rules below, with a full candidate/exclusion audit log. Truths are sealed at assembly time; predictions are sealed before truths are unsealed.

## Question

E1 proved the tier-1 composition verdict rung *exists* (extraction from sufficient observed tables, zero error). E3-P measures what E1 deliberately did not: over a **realistic backlog** of product experiments — not a curated counter-intuitive set — what fraction can the tier-1 pipeline honestly CALL, what does it ABSTAIN on and why, and with what error on the called set? This is the number that decides whether tier 1 is a commercial wedge or a diagnostic + data-quote surface (the codex dissent, resolved empirically).

## Case sourcing (assembled after sealing)

- **Target N ≥ 40; minimum viable N = 25.** If <25 cases meet inclusion after exhausting the fixed source list, the study is declared UNDERPOWERED and reported descriptively with no verdict.
- **Fixed source list (no additions mid-assembly):** (1) GoodUI's public evidence/test database; (2) published industry experiments in Kohavi et al. publications and major company engineering-blog write-ups (Microsoft/Bing ExP, Booking, Airbnb, Netflix, LinkedIn, Pinterest, Etsy, Duolingo and similar); (3) Hillstrom (MineThatData challenge); (4) the 15-case portfolio `PORTFOLIO_CASES_V3.json` — included as a **separate CURATED stratum**, never pooled into the prevalence headline (it over-samples counter-intuitive outcomes by construction).
- **Inclusion criteria:** a real shipped A/B experiment; control and treatment described concretely enough to translate; a primary metric named; a directional outcome publicly reported. Cases are NOT selected for being interesting, counter-intuitive, or composition-shaped.
- **Anti-cherry-picking audit:** the assembler logs EVERY candidate encountered (source, one-line description) and the exclusion reason for every rejection. The log ships with the results.
- **Blinding:** the assembler writes two files — `e3p_backlog.json` (descriptions, metric names, declared data-availability, NO outcomes) and `e3p_truths.json` (sha256-sealed at assembly completion, before any pipeline run). Assembler is instructed to record a candidate's description fields before reading its results section; where a source states the outcome inline, this is imperfect — recorded as a limitation, and the assembler never writes outcome information into the backlog file.

## Pre-launch data-availability modeling (the codex scoping, honored)

E1's tables contained *pilot-observed* aggregates. A realistic pre-test call may not have them. For each case the assembler declares which tier-1 quantities would plausibly exist at decision time, and the pipeline runs in two arms:

- **Arm A — strict pre-launch:** only baseline tables (segment sizes, baseline rates, historical mediator/natural-variation aggregates). No arm outcomes, no pilot shift shares.
- **Arm B — post-pilot:** a bounded pilot's aggregate outcomes/shift shares are available (the E1 regime; the "run a cheap pilot, we call the full test" product mode).

## Pipeline (per case, per arm)

Translator (claude-opus-4-8; no sign output; temperature omitted — the model rejects the parameter) → estimand label (primary / guardrail / net-business / segment) + mechanism family + required-quantities list → availability check against the declared tables → **CALL** (deterministic composition calculator, E1's code) or **ABSTAIN** with a pre-registered reason code: `non_composition_mechanism` / `missing_shift_quantity` / `missing_response_quantity` / `ambiguous_binding` / `insufficient_description`. All predictions written and sha256-sealed before `e3p_truths.json` is opened.

## Pre-registered metrics

- **PREVALENCE:** fraction of the realistic backlog whose estimand is composition-decidable in principle (translator classification, blind to outcomes).
- **COVERAGE-A / COVERAGE-B:** fraction of the realistic backlog actually CALLED per arm.
- **Called-set quality (per arm):** directional accuracy; confident-wrong count; **false-ship** (called + when truth −) and **false-kill** (called − when truth +) separately.
- **Abstain-reason distribution** — this is a headline result, not a footnote: it is the data-quote demand curve.
- **Baselines on the called subset and on the full backlog:** always-treatment-wins (PM optimism), chance (0.50), and never-call.
- **Curated stratum (portfolio 15):** same pipeline, reported separately as a stress slice.

## Pre-registered outcomes

- **PASS (tier-1 is a commercial wedge):** COVERAGE-B ≥ 15% with **zero confident-wrong** on the called set (both arms), and called-set accuracy > always-treatment-wins baseline on the same cases.
- **MARGINAL:** COVERAGE-B in [5%, 15%) with zero confident-wrong → tier 1 ships as a minor rung; the sales motion leads tier-2-first.
- **KILL (tier-1-as-wedge):** COVERAGE-B < 5%, or ANY confident-wrong on a called case in either arm → tier 1 is demoted to diagnostic + EVOI data-quote surface only; the codex position on generalization wins; the frontier table is amended accordingly.
- **Expected and acceptable:** COVERAGE-A ≪ COVERAGE-B. A near-zero Arm-A coverage with a rich abstain-reason distribution is not a failure — it is the measured justification for the pilot-first product mode and the priced measurement quote.

## What this does not test

Mediator-driven flips with donor surfaces (E3 main battery), transport (E6), the conformal gate (E4). E3-P is only: *how much of a real backlog does the proven calculator slice cover, at what error, and what exactly blocks the rest.*
