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
- [x] Founder Q&A walkthrough → captured in `qa-founder-clarifications.md` (positioning, sampling math, re-rank economics, agent chat, personas-stay verdict)

## Next Steps
1. Founder reads `analysis.md` (§1 premise revision, §4.1 Kohavi/positioning, §5 roadmap) — `qa-founder-clarifications.md` is the 5-min plain-language companion
2. Adoption decision on the three §5 "Now" items: simulator elicitation fixes · sidira-personas hygiene (soft posteriors, per-cluster Jaccard, holdout, tests) · Tier-0 benchmark harness (recommend green-lighting first — it's the model-selection criterion AND the sales artifact)
3. On "go": file tickets in sidira-personas + sidira-simulator (as ram-de), and start a new session for the **agent behavior spec** (prompt templates, feature-rendering rules, ablation protocol, chat-consistency + counterfactual-interview design) — identified as the missing implementation layer
4. Close session once roadmap decisions are made; roll lasting decisions into CONTEXT.md

## Key Files
- `sessions/persona-classifier-research/analysis.md` — THE deliverable (validation, classifier v2, benchmark strategy, sources)
- `sessions/persona-classifier-research/qa-founder-clarifications.md` — plain-language Q&A companion (read first)
- `sessions/persona-classifier/context.md` — the original (closed) persona plan that was validated

## Key Context
- Premise (from founder): simulation quality = f(hypothesis description, feature pack, personas, model). Feature pack extraction is ~deterministic; hypothesis quality is user-dependent. Persona extraction/construction is the highest-leverage controllable component.
- **Premise revised by evidence**: aggregate effect prediction works (r=0.85 Hewitt), individual twins don't (r≈0.20 Funhouse Mirrors); persona *conditioning depth* matters (interviews 86% vs demographics 74%, Park 2024), persona *cluster quality* is weakly coupled to accuracy. Highest-leverage stack = individual-level conditioning + calibration on historical experiments + the eval harness itself.
- Top 5 upgrades (ranked): hierarchical conditioning (persona + sampled-row deltas), end-to-end backtest as model-selection criterion, GATES/causal-forest response grounding, soft GMM posteriors end-to-end, distribution elicitation + shrinkage calibration. Planned XGBoost assignment classifier mostly killed (GMM posterior is the classifier; XGBoost only for cold-start with soft targets).
- Benchmark headline: Kohavi publicly attacked this category (Nov 2025) — positioning must be "calibrated prior / triage / bandit warm-start," never "replaces experiments" or "digital clones." Evidence ladder: Tier 0 (Upworthy confirmatory + Hewitt archive + null-integrity certificate + stratified honesty table, no customer needed) → Tier 1 (buyer-archive blind backtest, 150–200 experiments, hash-committed) → Tier 2 (prospective escrow registry).
- **Founder clarifications (2026-06-11, see qa-founder-clarifications.md)**: product intent is directional-only, never statistical significance — confirmed correct, but directional claims must be scored vs always-flat baseline (8–33% base win rates); value framing is "re-rank, never eliminate" (time-value of lift + arm pruning + bandit warm-start + pre-build iteration, NOT fewer tests); 1K-agent panels represent millions via GMM-as-compression + stratified sampling (pollster math); agent chat = strongest product feature + weakest scientific claim → counterfactual interview (paired seeds) is the unique centerpiece, frame as hypothesis generator never evidence; **personas STAY** — scaffolding not engine (sampling backbone, prompt gestalt, unit of insight, response-prior container, chat cast).
- Identified follow-up deliverable: **agent behavior spec** (prompt templates, feature-pack+persona-pack merge, ablation protocol, per-modality handling, chat consistency) — new session after Now-items adoption.

## For my cofounder
Research deliverable done. Start with `qa-founder-clarifications.md` (5 min, plain language), then `analysis.md` (~20 min, full detail). TL;DR: our pipeline scaffolding is good (weights, Hamilton sampling, paired seeds), but accuracy will come from individual-level agent conditioning + a backtest harness, not from better clustering; ARI-chasing is deprioritized; personas stay as the scaffolding/product layer. The benchmark plan is the sales motion for Meta/Google/Amazon — Tier 0 needs no customer and ~4–8 weeks. Biggest immediate code asks: soft posteriors in the pack, simulator temperature/distribution elicitation, no-persona control arm. Ram is reading now; next milestone is the adoption decision on the three §5 "Now" items.
