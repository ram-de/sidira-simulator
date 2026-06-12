---
type: session
domain: persona-classifier-research
status: active
started: 2026-06-11
owner: ram-de
---

# Session: persona-classifier-research — validate persona plan, design classifier algorithm + benchmark strategy

## Goal
Research-grade validation of the current persona classifier/building plan, plus a concrete classifier algorithm design and a benchmark strategy credible to experimentation-mature buyers (Meta, Google, Amazon).

## In Progress
- [ ] Founder review of analysis.md → decide which roadmap items to adopt

## Completed
- [x] Inventoried current plan (closed session sessions/persona-classifier/, sidira-personas code audit, simulator consumption path)
- [x] 4 parallel research streams: pipeline code audit (12 defects), LLM-simulation literature (~40 sources), buyer-grade benchmark research (Kohavi-proof), segmentation/clustering SOTA
- [x] Wrote the deliverable: `analysis.md` (validation verdict + classifier algorithm v2 + benchmark strategy)

## Next Steps
1. Founder reads analysis.md; pick Phase-Now items (§5): pipeline hygiene + tests, simulator elicitation fixes (temp/distributions/delta-mode/no-persona control), Tier-0 benchmarks (Upworthy + Hewitt archive + null-integrity suite)
2. If adopted: open tickets in sidira-personas (per-cluster Jaccard, soft posteriors in pack schema v1.1, holdout) and sidira-simulator (elicitation + calibration layer)
3. Close session once roadmap decisions are made

## Key Files
- `sessions/persona-classifier-research/analysis.md` — THE deliverable (validation, classifier v2, benchmark strategy, sources)
- `sessions/persona-classifier/context.md` — the original (closed) persona plan that was validated

## Key Context
- Premise (from founder): simulation quality = f(hypothesis description, feature pack, personas, model). Feature pack extraction is ~deterministic; hypothesis quality is user-dependent. Persona extraction/construction is the highest-leverage controllable component.
- **Premise revised by evidence**: aggregate effect prediction works (r=0.85 Hewitt), individual twins don't (r≈0.20 Funhouse Mirrors); persona *conditioning depth* matters (interviews 86% vs demographics 74%, Park 2024), persona *cluster quality* is weakly coupled to accuracy. Highest-leverage stack = individual-level conditioning + calibration on historical experiments + the eval harness itself.
- Top 5 upgrades (ranked): hierarchical conditioning (persona + sampled-row deltas), end-to-end backtest as model-selection criterion, GATES/causal-forest response grounding, soft GMM posteriors end-to-end, distribution elicitation + shrinkage calibration. Planned XGBoost assignment classifier mostly killed (GMM posterior is the classifier; XGBoost only for cold-start with soft targets).
- Benchmark headline: Kohavi publicly attacked this category (Nov 2025) — positioning must be "calibrated prior / triage / bandit warm-start," never "replaces experiments" or "digital clones." Evidence ladder: Tier 0 (Upworthy confirmatory + Hewitt archive + null-integrity certificate + stratified honesty table, no customer needed) → Tier 1 (buyer-archive blind backtest, 150–200 experiments, hash-committed) → Tier 2 (prospective escrow registry).

## For my cofounder
Research deliverable done: read `analysis.md` in this directory (~20 min). TL;DR: our pipeline scaffolding is good (weights, Hamilton sampling, paired seeds), but accuracy will come from individual-level agent conditioning + a backtest harness, not from better clustering; ARI-chasing is deprioritized. The benchmark plan is the sales motion for Meta/Google/Amazon — Tier 0 needs no customer and ~4–8 weeks. Biggest immediate code asks: soft posteriors in the pack, simulator temperature/distribution elicitation, no-persona control arm.
