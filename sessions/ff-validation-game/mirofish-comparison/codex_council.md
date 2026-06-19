# Council Review: What Sidira Should Borrow From MiroFish

## Executive Consensus

MiroFish is useful as prior art for **visualization, graph ingestion plumbing, and optional social-network dynamics**. It is not useful as an accuracy system. The established findings are accurate: I found no meaningful benchmark/backtest/calibration path, persona generation includes random demographic/social fields, and graph memory is shared at the graph level without Sidira-grade customer/entity leakage boundaries.

Sidira should borrow **interfaces and substrates**, not claims or scoring logic.

---

## Borrowable Items

| Priority | Borrow | MiroFish Evidence | Fit For Sidira | Effort |
|---|---|---|---|---|
| 1 | Knowledge graph visualization | `/tmp/MiroFish/frontend/src/components/GraphPanel.vue` | High fit as a **persona/product evidence graph viewer**, not as-is | M |
| 2 | Zep `graph.add_batch` ingestion | `/tmp/MiroFish/backend/app/services/graph_builder.py` | Good fit as optional feeder into `sidira-personas` clustering inputs | M |
| 3 | Ontology generation/editing flow | `/tmp/MiroFish/backend/app/services/ontology_generator.py`, `/tmp/MiroFish/backend/app/api/graph.py` | Useful as a draft schema suggestion layer, with human/schema gates | M |
| 4 | OASIS/network-effects substrate | `/tmp/MiroFish/backend/scripts/run_parallel_simulation.py` | Narrow fit for future “network effects / virality” mode only | L |
| 5 | Time-of-day/activity modulation | `/tmp/MiroFish/backend/app/services/simulation_config_generator.py` | Useful as metadata on agent activation, not core scoring | S/M |
| 6 | Graph-memory update pattern | `/tmp/MiroFish/backend/app/services/zep_graph_memory_updater.py` | Useful only as append-only evidence ingestion, not agent memory replacement | M |
| 7 | Graph detail UX | `/tmp/MiroFish/frontend/src/components/GraphPanel.vue` | Strong fit for auditability: node/edge details, provenance, episodes | S/M |

---

## 1. Frontend Graph Visualization

**What it is**

MiroFish has a substantial D3 force graph in:

`/tmp/MiroFish/frontend/src/components/GraphPanel.vue`

Concrete implementation:

- D3 force layout over `graphData.nodes` / `graphData.edges`
- node colors by entity type
- zoom/pan
- draggable nodes
- edge labels toggle
- selected node/edge detail panel
- self-loop grouping
- multiple-edge curvature handling
- live “graph updating” hints during simulation

This is real implementation, not marketing copy.

**Fit for Sidira**

Best Sidira targets:

- `frontend/app/personas/[id]/page.tsx`
- `frontend/app/personas/feature-pack/[version]/page.tsx`
- `frontend/app/simulations/[id]/page.tsx`
- `frontend/lib/api.ts`
- backend presentation endpoints near `backend/sidira_simulator/api/persona_packs.py` and `backend/sidira_simulator/api/simulations.py`

Do not port Vue. Rebuild as a small React/D3 component with a Sidira-native graph DTO:

```ts
type EvidenceGraph = {
  nodes: {
    id: string;
    label: string;
    kind: "persona" | "behavior" | "feature" | "metric" | "segment" | "source";
    summary?: string;
    provenance?: string[];
  }[];
  edges: {
    id: string;
    source: string;
    target: string;
    kind: string;
    evidence?: string;
    confidence?: number;
    source_ids?: string[];
  }[];
};
```

Use it first on the **persona pack detail page** to show how personas, behavioral traits, source rows/features, and product capabilities relate. Then add a simulation result graph showing which evidence supports or contradicts a result.

**Effort: M**

The force layout and detail-panel logic are proven, but Sidira needs React, design-system styling, API DTOs, and browser QA.

**Prior-echo impact**

Helpful indirectly. A graph can expose when a positive prediction is resting on generic “users like more” edges instead of concrete counter-evidence. Add explicit edge classes for:

- `supports_change`
- `contradicts_change`
- `metric_risk`
- `guardrail_risk`
- `weak_evidence`

That would make prior echo visible.

---

## 2. Zep `graph.add_batch` As A Feeder Into Clustering

**What it is**

MiroFish builds a Zep standalone graph from uploaded seed documents:

`/tmp/MiroFish/backend/app/services/graph_builder.py`

Key pattern:

- create graph
- set ontology
- chunk text
- send chunks via `client.graph.add_batch(...)`
- poll episode processing
- fetch nodes/edges

This is implemented in `GraphBuilderService.add_text_batches()` and the `/api/graph/build` route.

**Fit for Sidira**

This should not live inside `sidira-simulator` as prediction memory. It fits better upstream as a **feature/behavior enrichment feeder** for `sidira-personas`:

- source docs / crawl docs / product analytics docs → Zep graph
- graph nodes/edges → structured features
- structured graph features → GMM clustering / persona-pack generation

Sidira-side integration points:

- `backend/sidira_simulator/services/persona_builder.py`
- `backend/sidira_simulator/api/persona_builds.py`
- `backend/sidira_simulator/services/persona_pack_translator.py`
- sibling producer seam that emits `persona_pack.json`

Important constraint: keep Sidira’s existing customer-scoped artifact boundary:

`customers/{customer_id}/personas/{version}/...`

Graph IDs must be customer/build scoped, never global.

**Effort: M**

The API pattern is straightforward, but mapping graph entities into validated clustering features is nontrivial.

**Prior-echo impact**

Potentially helpful if the graph contributes **observed behavioral facts** rather than LLM-invented persona prose. Dangerous if used to generate richer fictional profiles. The value is “more grounded inputs,” not “more colorful personas.”

---

## 3. Ontology Handling

**What it is**

MiroFish generates an ontology from documents and simulation requirements:

`/tmp/MiroFish/backend/app/services/ontology_generator.py`

Then applies it to Zep:

`/tmp/MiroFish/backend/app/services/graph_builder.py`

The implementation asks the LLM for entity types, edge types, attributes, and validates/post-processes the result.

**Fit for Sidira**

Useful as a **draft mapping assistant**, especially for self-serve persona building and crawler output. Sidira already has canonical feature groups and LLM-assisted column mapping:

- `backend/sidira_simulator/services/column_mapper.py`
- `frontend/app/personas/new/wizard-ui.tsx`
- `backend/sidira_simulator/services/persona_builder.py`

Recommended use:

- propose ontology from Snowflake columns, crawl docs, and feature-pack text
- map ontology fields into Sidira’s canonical persona feature groups
- require schema validation and human confirmation before build
- version the ontology with the persona build

Do not let the ontology decide persona truth by itself.

**Effort: M**

Sidira already has the wizard and mapping posture. The missing piece is ontology DTOs, validation, and display/edit UI.

**Prior-echo impact**

Moderate. A good ontology can force the system to distinguish “desired business outcome” from “observed user mechanism,” which helps counter the more-is-better bias.

---

## 4. OASIS As Optional Network-Effects Substrate

**What it is**

MiroFish runs OASIS/CAMEL social simulations through:

`/tmp/MiroFish/backend/scripts/run_parallel_simulation.py`

It supports Twitter/Reddit environments, action logs, agent interviews, and IPC-style control.

**Fit for Sidira**

Do not use this for Sidira’s normal A/B prediction. Sidira’s current runner is intentionally independent-agent, paired, and benchmarkable:

- `backend/sidira_simulator/services/simulation_runner.py`
- `backend/sidira_simulator/services/scoring.py`
- `backend/sidira_simulator/schemas/simulation.py`

OASIS only fits a future optional mode like:

- “Will this referral mechanic spread?”
- “Will this social feature create visible network effects?”
- “Will creator/community behavior amplify or suppress adoption?”

It should be a separate substrate with separate metrics, not mixed into the existing confidence score.

**Effort: L**

Operationally heavier: subprocess lifecycle, dependency footprint, action schema, calibration harness, and a new result UI.

**Prior-echo impact**

Potentially useful for counter-intuitive cases where “more feature” causes negative network dynamics: spam, social pressure, status dilution, feed pollution. But only if evaluated against network-effect benchmarks. Otherwise it becomes another prior amplifier.

---

## 5. Time-Of-Day / Activity Modulation

**What it is**

MiroFish has time and activity configuration in:

`/tmp/MiroFish/backend/app/services/simulation_config_generator.py`

Examples include:

- `dead_hours`
- `morning_hours`
- `work_hours`
- `peak_hours`
- per-agent `activity_level`
- `posts_per_hour`
- `comments_per_hour`
- `active_hours`
- response delay ranges

**Fit for Sidira**

Useful as low-stakes behavioral metadata, especially once Sidira predicts metrics like conversion, retention, or engagement. Targets:

- `backend/sidira_simulator/services/identity_seed.py`
- `backend/sidira_simulator/schemas/identity.py`
- `backend/sidira_simulator/services/prompt_composer.py`
- `backend/sidira_simulator/services/simulation_runner.py`

Sidira already has identity seeds with `current_state`, tenure, locale, recent gripe. Add optional activity fields only when present in real data:

- active window
- session frequency band
- weekday/weekend tendency
- lifecycle timing
- recency of last use

Do not hardcode “China time” style defaults.

**Effort: S/M**

Schema + prompt changes are small. Making it data-grounded is the real work.

**Prior-echo impact**

Minor but useful. Some counter-intuitive outcomes are timing-sensitive: a feature can look good abstractly but fail in rushed, late-night, mobile, or work-context sessions.

---

## 6. Graph Memory Update Pattern

**What it is**

MiroFish streams simulation actions back into Zep:

`/tmp/MiroFish/backend/app/services/zep_graph_memory_updater.py`

It batches actions, converts them to natural-language episodes, and writes them into the graph.

**Fit for Sidira**

Do not replace Sidira’s memory architecture. Sidira’s current memory model is much safer:

- `backend/sidira_simulator/memory/agent_memory.py`
- `backend/sidira_simulator/schemas/agent.py`

It freezes:

- `identity.md`
- `initial_reaction.md`
- `conversation.jsonl`
- `identity_seed.json`
- `reaction_distribution.json`

That identity-continuity guarantee is superior to MiroFish’s graph-memory pattern for chat.

Borrow only the **append-only event-to-evidence pipeline** idea:

- simulation reactions → evidence graph artifacts
- PM feedback → calibration/evidence graph
- persona-group themes → graph view
- no graph writes are read back into the same prediction run

**Effort: M**

Need a graph artifact schema and write path, but no need to change core memory.

**Prior-echo impact**

Helpful if the graph records contradictions and failed predictions. Dangerous if the graph feeds prior generated claims back into future agents without a leakage firewall.

---

## 7. Graph Detail UX And Provenance Panels

**What it is**

MiroFish’s `GraphPanel.vue` detail panel exposes:

- node labels
- UUIDs
- attributes
- summaries
- edge facts
- fact types
- episodes
- timestamps

**Fit for Sidira**

This is highly aligned with Sidira’s “validated directional accuracy” thesis. Sidira should show evidence provenance, not just pretty graph topology.

Targets:

- persona-pack detail: `frontend/app/personas/[id]/page.tsx`
- simulation result: `frontend/app/simulations/[id]/page.tsx`
- API types: `frontend/lib/api.ts`
- backend rendered views: `backend/sidira_simulator/services/persona_pack_view.py`

Recommended Sidira panel fields:

- source table / crawl artifact / benchmark dataset
- persona pack version
- feature group
- holdout/Jaccard/stability flags
- whether edge is observed, inferred, or LLM-summarized
- whether it supports or contradicts the predicted direction

**Effort: S/M**

The UX idea is easy. The backend provenance quality determines whether it is meaningful.

---

# Do Not Copy

## Do not copy MiroFish’s accuracy posture

I found no meaningful benchmark, backtest, holdout, calibration, or directional-accuracy harness in the inspected MiroFish backend. Sidira’s thesis depends on this exact missing layer.

Sidira should keep investing in:

- sealed pre-registered backtests
- leakage firewall
- role-separated validation
- benchmark harness
- paired lift
- null integrity
- calibration

## Do not copy random persona generation

MiroFish profile generation uses random fields like MBTI, country, social counts, usernames, karma/follower counts in:

`/tmp/MiroFish/backend/app/services/oasis_profile_generator.py`

This conflicts with Sidira’s persona packs built from clustered real data.

## Do not copy shared graph memory as prediction memory

MiroFish writes natural-language actions into a graph and can reuse graph context. That is a leakage risk unless carefully scoped.

Sidira should keep:

`backend/sidira_simulator/memory/agent_memory.py`

as the source of truth for agent continuity.

## Do not copy the single-LLM Markdown report as the result surface

MiroFish’s report agent is elaborate:

`/tmp/MiroFish/backend/app/services/report_agent.py`

But Sidira’s value is structured directional prediction, weaknesses, lift, CI, and inspectable agent evidence. A narrative report would make the product easier to overclaim.

## Do not copy OASIS into the default simulation runner

It changes the estimand. Sidira’s normal A/B score should remain paired and independent unless explicitly running a network-effects mode.

## Do not copy the Vue component wholesale

The graph component is useful prior art, but its styling, framework, colors, and component architecture do not match Sidira’s Next/design system.

## Do not copy LLM-invented ontology as ground truth

Use ontology as draft structure. Ground final fields in source data, human confirmation, and schema validation.

---

# What Helps Sidira’s Prior-Echo Weak Spot

The strongest borrow is **not** another simulation method. It is an **evidence graph that makes priors inspectable**.

Recommended additions:

1. Add evidence graph edges for `supports`, `contradicts`, `guardrail_risk`, and `weak_or_inferred`.
2. Show counter-evidence next to every positive A/B prediction.
3. Feed Zep/graph extraction into clustering only as source-grounded features, not persona prose.
4. Use OASIS only for benchmarked network-effect cases where social feedback loops are the mechanism.
5. Add ontology checks that force the hypothesis to name mechanism and metric separately.

Council verdict: **Borrow MiroFish’s graph instrumentation and ingestion scaffolding. Do not borrow its prediction stack.**
