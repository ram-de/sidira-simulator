---
type: session
domain: fable-research
status: active
started: 2026-07-01
owner: ram-de
---

# Session: fable-research — grounded-simulation accuracy research council

## Goal
Research-grade analysis of Sidira's core accuracy problem: grounded simulation + watchdog depends on customers providing rich behavioral data beyond persona data, while the "easy" path (persona-seeded LLM agents) is refuted by our own benchmarks (LLM prior bias — llama optimism, Opus pessimism, magnitude-blindness). Run a council of research-scientist-grade perspectives ("if Anthropic built this to save A/B-test cost, how would a Karpathy-level council solve it?") and draft a research paper.

## In Progress
- [ ] Founder review: PAPER.md v1.1 + DEBATE_CONCLUSION.md; next experiment = backlog-prevalence study (joint priority #1), then E5 proximal

## Completed
- [x] Grounded in evidence base: founder-readout/simulation-engine-where-we-landed.md + finetuned-simulator-readout.md (from origin/main; extracted to scratchpad)
- [x] Framed the research question: data-efficiency frontier — what trust/accuracy is deliverable at each data tier (0 persona-only / 1 aggregates / 2 A/B exhaust / 3 event-level) and what methods move value down the ladder
- [x] Research council workflow (wf_4385dd55-493, 16 agents ~1.04M tokens): 6 lens-proposers → per-proposal red team (6/6 "revise", 0 kills) → 3-judge panel (top-pick split 2–1 Backtest Ladder vs Abstention Ledger) → chair synthesis
- [x] PAPER.md drafted — "The Data-Efficiency Frontier for Trustworthy Pre-Test Prediction"
- [x] Provenance saved: council-synthesis.md (chair) + council-dossiers.md (full proposals/critiques/scores)
- [x] E1 RUN (worktree-fable-e1-e2, research/fable-frontier-experiments/): **PASS** — calc 12/12 flips + 12/12 one-sign; real Cookie Cats both signs from tier-1 moments alone (−0.8201/−0.5905pp = row-level truth); Opus-with-tables 23/24 (one silent arithmetic slip). Tier-1 verdict rung EXISTS on the composition slice; magnitude-blindness = information absence (words 0.00 → tables 1.00)
- [x] E2 RUN: **KILL** — 86.7% same-tag opposite-sign ambiguity on 17 real cases (threshold 30%); mechanism-tag retrieval permanently banned from picking signs; rule R2 is now a measured result
- [x] codex council round 1 (codex-council-r1.md): independent architecture converges on restructure-not-dissolve; 8 critiques adopted (validity-wording, estimand taxonomy, baselines, decision economics, certificate language, PFN deprioritized below tabular-supervised, in-span/novel labels, instrumentation preflight); Fable response with E1/E2 evidence in fable-response-r1.md
- [x] codex round 2 (codex-council-r2.md): hostile audit of E1/E2 artifacts PASSED (hashes, blinding, leakage verified; Wilson CI on E2); all 5 original disagreements resolved/synthesized; 3 standing codex dissents recorded
- [x] DEBATE_CONCLUSION.md: joint statement — proven engines = calculator + direct A/B estimate + g-formula, everything else an abstention test until it wins under seal on decision economics; audit is the wedge, selective pre-test prediction is the product
- [x] PAPER.md → v1.1 (changelog + inline amendments: validity wording retired, estimand+evidence-class labels, tier-1.5 experimental flag, E1/E2 RUN markers, §9 dissent 2 resolved)

## Next Steps
1. Founder reads PAPER.md (the deliverable) — §6 frontier table + §7 experiments are the decision surface
2. If endorsed: run E1 (arithmetic-sufficiency, 2 days ₹0) and E2 (same-tag opposite-sign audit, ₹0) as the next sealed experiments
3. Decide the §9.1 go-to-market dissent (audit-led vs guarantee-led) — evidence can't make this call

## Key Files
- sessions/fable-research/PAPER.md — the research paper (deliverable)
- sessions/fable-research/council-synthesis.md — chair synthesis (backbone)
- sessions/fable-research/council-dossiers.md — full 6 proposals + red-team critiques + judge scores
- sessions/fable-research/context.md (this file)

## Key Context
- Established evidence base (from memory, 2026-06-27→30): no LLM method beats chance on the 14-case set; LLM sims have model-specific structural direction bias (llama always-up, Opus always-down) but shared magnitude-blindness; grounded mediation sim wins 12/12 on magnitude-driven-flip cells vs LLM 0.00; negative-control guard validated; prod blind tests → durable product behavior = data-computed incrementality/unit-economics AUDIT + ABSTAIN, not persona-sim.
- Core tension this session must resolve: grounding requires customer data that is hard to get; persona-only is cheap but bias-broken. What's the principled middle path / data-efficiency frontier?
- Council's one-paragraph verdict: the data dependency CANNOT be dissolved (flip-deciding magnitudes are physically absent from words/personas/priors) but CAN be restructured — knowledge to our side (library), ask shrunk to afternoon-exportable artifacts (A/B exhaust + one frozen aggregate schema), missing magnitudes become PURCHASABLE Senu measurements (tier 1.5 SKU), every rung gated by computed abstention. Validity constant down the ladder; only COVERAGE varies.
- Three verdict-admission rules: R1 magnitudes data-derived-or-purchased never LLM-declared; R2 words never pick the sign; R3 full-product sign stability + flat-prior quarantine.
- Personas' one surviving role: P(z) transport weights — never LLM seeds.
- Tier 2 (A/B exhaust) is the recommended ENTRY rung: winner's-curse audit = day-one ROI + the data grant; tier 3 = premium rung, not entry toll.
- E1–E4 run at ₹0 on assets already in the repo; each carries a pre-registered kill.

## For my cofounder
Fable 5 research session, 2026-07-01. Deliverable = PAPER.md ("The Data-Efficiency Frontier for Trustworthy Pre-Test Prediction") — the council's answer to "grounded sim + watchdog needs data customers won't give; persona-seeded LLM agents are disproven; now what?" Read PAPER.md §6 (frontier table) + §7 (experiments) first; §9 records two dissents only a founder can resolve. Docs only — nothing deployed, no prod code touched.
