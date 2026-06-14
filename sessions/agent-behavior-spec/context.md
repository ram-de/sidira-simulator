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
- [ ] Scope the spec sections and decide drafting order (recommend: treatment-rendering layer first — it's shared infra built once in the harness)

## Completed
(nothing yet)

## Next Steps
1. **Treatment-rendering layer** (the newly named component, analysis §6.2): (existing state, proposed change) → exact text/image context an agent reads. Diff representation (what changed / what is explicitly held fixed), per-modality handling (copy vs UI screenshot vs pricing/mechanics). MUST be format-identical between Tier-0 benchmark inputs and customer PRDs — build once, in the harness (#222), first.
2. **Agent-context assembly spec**: feature pack + change PRD + persona narrative (gestalt) + individual row (specifics, deltas above |z|≈0.5 rendered in natural language) + per-cluster seed pools. The hierarchical conditioning prompt from analysis §3.2.
3. **Elicitation prompt templates** (tie to #221): design unblinding, distribution/verbalized sampling, delta-vs-control framing, paraphrase ensemble, no-persona control prompt.
4. **Ablation protocol**: archetype-only vs hierarchical vs persona-free row-sampling, scored on the Tier-0 harness (#222). Park 2024 predicts the ordering; measure it on Sidira's task.
5. **Multi-turn chat consistency + counterfactual interview**: same agent identity experienced both control and treatment (paired seeds) → ask what changed. Frame as hypothesis generator, never evidence (qa §5). Interview the panel not the agent; cluster answers; tie to weakness taxonomy.
6. Define OEC-aligned scoring input: simulate against the customer's OEC definition from the feature pack, not generic sentiment (analysis §4.4 Q11 — a real product gap today).

## Key Files
- `sessions/persona-classifier-research/analysis.md` — parent research (§3.2 conditioning, §3.3 elicitation, §6.2 treatment-rendering gap)
- `sessions/persona-classifier-research/qa-founder-clarifications.md` — §5 agent chat verdict, §7/§8 what's deliberately deferred to THIS spec
- Tickets this spec feeds: ram-de/sidira-personas#7 (A), ram-de/sidira-simulator#221 (B), ram-de/sidira-simulator#222 (C)

## Key Context
- This session is the deliberately-deferred implementation layer from persona-classifier-research (closed-out next). That research validated the *what*; this spec defines the *how* the code teams build against.
- **Scope expanded 2026-06-12** (recorded in parent session): this spec OWNS the treatment-rendering layer — (existing state + change PRD) → agent context — which must be format-identical between benchmarks and production. The parent analysis covered how the change description should be *used* (unblinding, paraphrase, linting, OEC scoring) but did NOT audit the ingestion/rendering path; that audit belongs here.
- Hard constraint from the research: agents get **persona narrative + individual row**, not archetype-only. Personas are scaffolding (sampling backbone, prompt gestalt, unit of insight, response-prior container, chat cast), not the accuracy engine.
- Positioning guardrail carries through: never "digital clones"; chat is hypothesis generator, never evidence.

## For my cofounder
New session, follow-on from persona-classifier-research (now closing). This is the spec the three adopted "Now" tickets build against. Start point: draft the treatment-rendering layer first since it's shared infra between the benchmark harness (#222) and production. Read the parent analysis §3.2, §3.3, §6.2 and qa §5/§7/§8 for what was deferred here on purpose.
