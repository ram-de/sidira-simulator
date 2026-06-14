---
type: session
domain: agent-behavior-spec
status: active
started: 2026-06-13
owner: ram-de
---

# Session: agent-behavior-spec — the implementation layer between persona/benchmark research and shipping

## Goal
Specify how an agent's full context is assembled and how it behaves — prompt templates, the feature-pack + persona-pack + individual-row merge, the treatment-rendering layer, the ablation protocol, per-modality handling, and multi-turn chat consistency — so the adopted "Now" tickets (#7/#221/#222) have a concrete spec to build against, format-identical between benchmark harness and production.

## In Progress
- [ ] §1 treatment-rendering layer + §3a conversion question — draft v1 of both written; 3 open Qs each, recommendations attached, none blocking (defaults chosen). Founder review when convenient.

## Completed
- [x] **§1 treatment-rendering layer, draft v1** (2026-06-13) → `treatment-rendering-layer.md`: audited `prompt_composer.py` in code → 3 confirmed gaps (`proposed_figma` dropped entirely; no explicit diff/"held-fixed"; control vs treatment differ in representation density, not just content). Spec = typed structural state-diff (ADDED/REMOVED/CHANGED/MOVED + mandatory "NOT changing" block) rendered symmetrically across arms, per-modality table tied to reliability regimes, format-identical via an archive→`Hypothesis` adapter at the edge. Resolves §3a Q3 (choice-set = transitions reachable from `decision_point`).
- [x] **§3a conversion question, draft v1** (2026-06-13) → `elicitation-conversion.md`: agent-side in-character elicitation (turn 2 after the free-text reaction), forced 10-trial allocation across realistic alternatives (verbalized sampling, counters acquiescence/hyper-rationality/mode-collapse), `p_conv` derived per arm, scored as paired delta (reuses #90 bootstrap, cancels uncalibrated absolute level), reported in pp but directional/relative until #222. 3 open Qs resolved to reversible v1 defaults.

## Next Steps
1. **Treatment-rendering layer** (the newly named component, analysis §6.2): (existing state, proposed change) → exact text/image context an agent reads. Diff representation (what changed / what is explicitly held fixed), per-modality handling (copy vs UI screenshot vs pricing/mechanics). MUST be format-identical between Tier-0 benchmark inputs and customer PRDs — build once, in the harness (#222), first.
2. **Agent-context assembly spec**: feature pack + change PRD + persona narrative (gestalt) + individual row (specifics, deltas above |z|≈0.5 rendered in natural language) + per-cluster seed pools. The hierarchical conditioning prompt from analysis §3.2.
3. **Elicitation prompt templates** (tie to #221): design unblinding, distribution/verbalized sampling, delta-vs-control framing, paraphrase ensemble, no-persona control prompt.
   - **3a. Per-metric outcome elicitation (NEW, 2026-06-13 discussion).** Today the agent is only asked to "react" → classified to 3-way sentiment; the metric the PM actually cares about ("conversion +5%") is never elicited, and even A/B `lift` is in sentiment-score units. This spec must define, **per metric type**, the exact behavioral decision the agent is asked (conversion → "would you complete checkout?"; retention → "would you come back next week?"; CTR → "would you click this?"), elicited as a distribution not a point. The aggregation (rate per arm → paired-bootstrap lift in native units) lives in #221; the *question design* lives here. Decision rule: the question must encode the metric's actual user action, framed in-character, never "rate your sentiment." Magnitude is direction-credible but inflated → output stays directional/relative until #222's shrinkage layer calibrates absolute lift (Upworthy = first CTR calibration target).
4. **Ablation protocol**: archetype-only vs hierarchical vs persona-free row-sampling, scored on the Tier-0 harness (#222). Park 2024 predicts the ordering; measure it on Sidira's task.
5. **Multi-turn chat consistency + counterfactual interview**: same agent identity experienced both control and treatment (paired seeds) → ask what changed. Frame as hypothesis generator, never evidence (qa §5). Interview the panel not the agent; cluster answers; tie to weakness taxonomy.
6. Define OEC-aligned scoring input: simulate against the customer's OEC definition from the feature pack, not generic sentiment (analysis §4.4 Q11 — a real product gap today).

## Key Files
- `sessions/agent-behavior-spec/treatment-rendering-layer.md` — §1 deliverable: code audit of `prompt_composer.py`, the 3 gaps, the typed state-diff representation, per-modality handling, benchmark↔prod format contract, build order
- `sessions/agent-behavior-spec/elicitation-conversion.md` — §3a deliverable: the conversion question (prompt text, output schema, aggregation contract, design rationale, open Qs)
- `sessions/persona-classifier-research/analysis.md` — parent research (§3.2 conditioning, §3.3 elicitation, §6.2 treatment-rendering gap)
- `sessions/persona-classifier-research/qa-founder-clarifications.md` — §5 agent chat verdict, §7/§8 what's deliberately deferred to THIS spec
- Tickets this spec feeds: ram-de/sidira-personas#7 (A), ram-de/sidira-simulator#221 (B), ram-de/sidira-simulator#222 (C)

## Key Context
- This session is the deliberately-deferred implementation layer from persona-classifier-research (closed-out next). That research validated the *what*; this spec defines the *how* the code teams build against.
- **Scope expanded 2026-06-12** (recorded in parent session): this spec OWNS the treatment-rendering layer — (existing state + change PRD) → agent context — which must be format-identical between benchmarks and production. The parent analysis covered how the change description should be *used* (unblinding, paraphrase, linting, OEC scoring) but did NOT audit the ingestion/rendering path; that audit belongs here.
- Hard constraint from the research: agents get **persona narrative + individual row**, not archetype-only. Personas are scaffolding (sampling backbone, prompt gestalt, unit of insight, response-prior container, chat cast), not the accuracy engine.
- Positioning guardrail carries through: never "digital clones"; chat is hypothesis generator, never evidence.
- **Metric-prediction gap (2026-06-13, code-confirmed):** current output is generic — `confidence_score = 0.6·sentiment + 0.4·(1−weakness_share)`; A/B `lift` is in confidence-score units (sentiment delta), not the hypothesis's metric. `prompt_composer.py` asks "react to the change"; `scoring.py` classifies sentiment + weakness. Predicting a named metric (conversion lift) needs: (1) target-metric field on `Hypothesis` [#221], (2) per-metric behavioral elicitation [this spec §3a], (3) rate-per-arm aggregation reusing the #90 paired bootstrap [#221]. Directional/relative lift is near-term; trustworthy absolute % is gated on #222's calibration.

## For my cofounder
New session, follow-on from persona-classifier-research (now closing). This is the spec the three adopted "Now" tickets build against. Start point: draft the treatment-rendering layer first since it's shared infra between the benchmark harness (#222) and production. Read the parent analysis §3.2, §3.3, §6.2 and qa §5/§7/§8 for what was deferred here on purpose.
