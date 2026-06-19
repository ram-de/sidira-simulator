# Sidira vs MiroFish — Two-Council Borrow Analysis

**Date:** 2026-06-19 · **Method:** two independent councils, synthesized.
**Council A (Claude):** 4 parallel expert subagents — simulation-mechanics, data-science/personas, frontend/graph-viz, product/architecture-fit.
**Council B (Codex / gpt-5.5):** independent read-only panel (raw output: [`codex_council.md`](./codex_council.md)).
**Repos on disk:** Sidira = `/Users/ram/Projects/sidira-simulator` · MiroFish = `/tmp/MiroFish` (cloned from github.com/666ghj/MiroFish, depth 1).
This is a **report, not an implementation.** No Sidira code was changed. All MiroFish findings were verified against the real clone, not marketing copy.

---

## (a) Verdict

> **Borrow MiroFish's *interfaces and substrates* — never its *prediction stack*.** Both councils converged on this independently.

MiroFish is a polished **orchestration wrapper** around two third-party systems: CAMEL's **OASIS** (the social-sim engine) and **Zep Cloud** (the knowledge-graph memory). Almost none of its "engine" is its own IP — the simulation loop is `oasis.make()` / `env.step()`, and the memory is `zep.graph.*`. What MiroFish *authored* is the glue: a graph UI, a doc→graph ingestion path, an LLM ontology generator, time/activity config, and a single-LLM Markdown "report."

Its fatal gap — confirmed by both councils with repo-wide search — is **zero accuracy validation**: no benchmark, backtest, holdout, calibration, or directional-accuracy harness anywhere. Its "prediction" is one LLM's prose summary of unvalidated agent logs. **That gap is exactly Sidira's moat.** Sidira's backtests are *cryptographically sealed* (SHA-256 hash-commit over canonical inputs, `backend/sidira_simulator/services/null_integrity.py`) — a thing MiroFish structurally **cannot** have, because it invents its ontology, personas, and config fresh per run, so there is nothing stable to pre-register or seal.

Two important framings that emerged:

1. **Sidira already harvested the obvious wins.** Sidira's own code credits MiroFish in two places — `backend/sidira_simulator/services/simulation_runner.py:13` (the `asyncio` fan-out, "from mirofish oasis_profile_generator.py:851-1014") and `backend/sidira_simulator/services/agent_chat.py:16` (the chat anti-drift guard, "Adapted from mirofish … INTERVIEW_PROMPT_PREFIX"). Parallel orchestration, the chat guard, **and** the post-hoc persona interview (`agent_chat.py` + `PersonaGroupChatV2.tsx`) are *done* — and Sidira's versions are stronger. Excluded from the borrow list.

2. **The realistic borrowable surface is small and mostly *upstream* of the predictor.** The defensible borrows feed cleaner *inputs* (seed-doc enrichment) or expose *evidence* (a provenance/evidence graph), or add an optional *substrate* for a future network-effects mode. Nothing touches the scorer.

### Comparison table

| Dimension | **Sidira** | **MiroFish** |
|---|---|---|
| **Architecture** | FastAPI + Next.js; independent-agent, **paired** (treatment vs control shadow), one-shot static elicitation; out-of-process persona worker | Vue + Python wrapper around CAMEL **OASIS** + **Zep Cloud**; multi-round social `env.step` loop; IPC/file-poll control plane |
| **Personas** | Built from **clustered REAL data** (GMM pipeline, sibling `sidira-personas`); LLM enrichment fenced twice (feature-grounded prompt + `_PERSONA_OVERRIDES` clamp in `identity_seed.py`) | **`random.choice`** over hardcoded MBTI/country/age/karma arrays (`oasis_profile_generator.py:156+`), then LLM-written 2000-char persona prose off a Zep summary; regex JSON-repair gauntlet |
| **Validation / accuracy** | **The whole thesis.** Sealed pre-registered backtests (SHA-256 commit), two-table leakage firewall, role-separated blinded validation, permutation null-integrity gate (`null_integrity.py`), paired lift, calibration/shrinkage seam (`conversion_calibrator.py`, no-op until #222) | **None.** Repo-wide search for benchmark/backtest/calibration/ground-truth = 0 hits. "Prediction" = one LLM's Markdown summary of agent logs (`report_agent.py`) |
| **Frontend** | Next.js/React, instrument-panel aesthetic (DESIGN.md), live confidence trace as event-driven progress; **no graph/viz library at all** (verified) | Vue 3, **D3 v7 the only viz dep**; 1423-line raw-SVG force-directed knowledge graph (`GraphPanel.vue`) with node/edge detail panel, zoom/pan, drag, multi-edge bundling |
| **Memory** | **Frozen, write-once** identity-continuity guarantee — `identity.md`/`initial_reaction.md`/`conversation.jsonl` replayed (`memory/agent_memory.py`); explicitly architected *against* the MiroFish failure mode | **Shared single Zep graph**, no per-entity/customer leakage boundary; simulation actions streamed *back* into the same graph that seeds the next run's personas (`zep_graph_memory_updater.py`) = closed model→memory→persona loop |
| **Predictor** | Statistical instrument: scorer → paired-lift aggregator → null-integrity certificate | Single LLM writing prose ("predict-by-vibes") |

---

## (b) Borrowable items — ranked

Effort: **S** = days · **M** = 1–2 weeks · **L** = multi-week / new dependency. Each item carries the **council agreement** state.

### #1 — Evidence/provenance graph (NOT a generic entity graph) — **M backend + S–M frontend**
*Both councils raised a graph; they DISAGREED on framing. This synthesis resolves it.*

- **What it is:** MiroFish's `GraphPanel.vue` is a competent raw-SVG D3 force graph — `d3.forceSimulation` with link/charge/collide forces (`:472-486`), zoom/pan (`:492-494`), click-vs-drag detection (`:662-697`), curved multi-edge bundling + self-loop arcs (`:435-464`), color-by-type legend, and a **right-rail detail panel exposing provenance** (node summary/labels/attributes; edge `fact`/`fact_type`/`episodes`/`valid_at` — `:52-200`, `:285-299`).
- **The disagreement:** Codex ranked "build the graph viewer" as its **#1 borrow** (effort M), as a *persona/product evidence graph*. The Claude frontend lens **rejected the graph as a feature**: Sidira has **no graph-shaped data** — personas carry aggregate shares + feature vectors, agents carry a scalar sentiment + quote, agent→persona is strictly one-to-many, capabilities have no inter-edges. A persona-similarity graph would have to *invent* edges (e.g. centroid cosine distance) — which lands on DESIGN.md §10's forbidden "decorative instrument marks… not bound to backend data," plus §4.1 color-budget and §7 "no floating UI" violations.
- **Resolution (the real cost is the backend, not the D3):** Both are right about different layers. The graph is only legitimate **if you first build an evidence-graph DATA MODEL** — edges with explicit semantics: `supports_change` / `contradicts_change` / `guardrail_risk` / `weak_or_inferred`, each carrying `provenance` (source table / crawl artifact / benchmark dataset), `confidence`, and `observed | inferred | llm_summarized`. *That* is data Sidira's directional-accuracy thesis genuinely owns, and a graph of it is honest. A graph of *manufactured* persona similarity is theater. So: **the borrow is the provenance-panel + evidence-edge concept; the cost is the backend that produces real edges, not the renderer.**
- **Fit:** Backend — new DTO + write path near `backend/sidira_simulator/api/simulations.py` / `persona_packs.py` and `services/persona_pack_view.py`. Frontend — `frontend/app/simulations/[id]/page.tsx` and `frontend/app/personas/[id]/page.tsx`, consuming a Sidira-native `EvidenceGraph` DTO in `frontend/lib/api.ts`.
- **Library (if/when rendered):** **`visx`** (`@visx/network`), *not* raw D3-in-React (imperative DOM mutation fights React's reconciler — MiroFish's port path is wrong) and *not* `react-force-graph` (canvas/WebGL, opaque to design tokens). visx renders SVG through React, so every node/edge respects Sidira's `TOKENS`, focus rings, and `<button>` requirements — and matches the existing hand-rolled `GlassTrace`/`GlassCiAxis` idiom.
- **Effort:** Frontend rendering **S–M**; the load-bearing cost is the **backend evidence-graph model (M)**. Don't build the renderer first.

### #2 — Click-select → synced detail rail with **cross-highlight** (interaction polish) — **S, no library**
*Claude frontend lens. Codex's "graph detail UX" (its #7) overlaps.*

- **What it is:** MiroFish's selection model — click a node/edge → set `selectedItem`, **highlight the selection plus its neighbors**, drive a typed detail panel; click empty space to deselect (`GraphPanel.vue:698-716`, `:777-783`).
- **Fit:** Sidira already has the InspectorRail (`frontend/app/simulations/[id]/page.tsx:1943-2159`, sticky 340px paper-elevated rail). The borrowable refinement is the **bidirectional highlight**: selecting a persona group in the rail highlights its row in the PERSONA READINGS register (~line 2040) and vice-versa. Pure interaction polish, fully DESIGN.md §7.2/§7.8 compliant (real `<button>`, focus-visible ring, existing `paper-recessed` active fill).
- **Effort:** **S** — wire existing `selectedPersona` state into a second consumer. No library, no new color/motion.

### #3 — Seed-doc → entity extraction as a **constrained feeder INTO clustering** — **L (pattern, not the Zep dep)**
*Data-science lens + Codex #2 agree this is real; both stress the same guardrails.*

- **What it is:** MiroFish builds a Zep graph from uploaded seed docs — create graph → set ontology → chunk text → `client.graph.add_batch(...)` → poll episodes → fetch nodes/edges (`backend/app/services/graph_builder.py`, `GraphBuilderService.add_text_batches()`, `/api/graph/build`).
- **Fit / why it's real:** It fills a **confirmed gap** — Sidira's `adapter.py` (`adapt_group()`) accepts only **structured** metric types (count/score/ratio/flag/categorical/json/tenure_days); there is **zero text/document ingest at build time.** A doc→feature extractor would let unstructured seed/crawl docs become structured features that then **re-enter the existing GMM pipeline** (`persona_builder.py` / `run_pipeline`) and **survive the existing `per_cluster_jaccard` / holdout / stability gates.**
- **Hard constraints (both councils):** (1) Borrow the *pattern*, **not the Zep Cloud dependency** — no hard external dep, no shared graph. (2) Output must be a **per-row feature table**, never persona prose. (3) Graph/build IDs must be **customer/build-scoped** (`customers/{customer_id}/personas/{version}/…`), never global — MiroFish's global graph is the leakage-shaped risk. (4) Pair it with a **fixed fallback schema** (#4) so extraction columns are bounded, never free LLM invention.
- **Effort:** **L** — the API pattern is easy; mapping graph entities into *validated* clustering features that pass the gates is the work.

### #4 — Fixed extraction-schema backbone (constraint on #3) — **S**
*Data-science lens.* Adopt fixed extraction columns + a bounded "other" bucket rather than free LLM schema invention. This is what makes #3 prior-echo-*neutral* instead of prior-echo-positive. Cheap; do it as part of #3.

### #5 — Time-of-day / activity modulation as a **per-persona sampling weight** — **S**
*Sim-mechanics lens + Codex #5 agree, with the same critical caveat.*

- **What it is:** MiroFish computes a per-round `simulated_hour`, applies peak/off-peak multipliers, and gates each agent on `active_hours` + a Bernoulli draw against `activity_level` (`run_parallel_simulation.py:1040-1090`; config in `simulation_config_generator.py`). This is the *only* non-trivial mechanic MiroFish authored itself.
- **Fit:** Borrow the **idea** as a per-persona **response-propensity/aggregation weight** (defaulting to 1.0 = byte-identical to today), threaded into `allocate()` / scoring. **Critical caveat — the weight MUST come from the clustered persona posterior (a measured population property), NEVER from an experimenter/LLM-authored config.** MiroFish's config-authored dials are a demand-characteristics leak straight into the outcome (DO-NOT-COPY). It must stay a *weight on the existing one-shot reaction* — never a temporal feedback loop (that inherits OASIS's prior-echo amplification).
- **Fit files:** `services/identity_seed.py`, `schemas/identity.py`, `services/prompt_composer.py`, aggregation in `simulation_runner.py`.
- **Effort:** **S** — a float weight; no new LLM calls, no firewall-schema change. (Making it genuinely *data-grounded* is the only real work.)

### #6 — LLM ontology generator as a **draft mapping assistant** (human/schema-gated) — **M**
*Codex #3.* MiroFish's `ontology_generator.py` asks an LLM for entity/edge types + attributes and validates the result. Sidira already has LLM-assisted column mapping (`column_mapper.py` + the `personas/new` wizard). Borrow ontology generation only as a **draft schema suggestion** over Snowflake columns / crawl docs, **requiring schema validation + human confirmation before build**, versioned with the persona build. **Never let the ontology decide persona truth.** Moderate prior-echo value (can force "business outcome" vs "observed mechanism" to be named separately). The sim-mechanics and data-science lenses are more skeptical here — LLM-invented ontology feeding personas is prior-echo-positive — so this is **conditional** on the human/schema gate being real.

### #7 — OASIS as an optional network-effects **substrate** (never the predictor) — **L, research bet**
*All lenses agree: substrate-only, and only with a real requirement.*

- **What it is:** The `oasis.make()` / `env.step()` loop over a social `agent_graph` (post/repost/follow/like/comment) — `run_parallel_simulation.py:1155-1254`. MiroFish *calls* the `oasis-ai` library; "borrowing OASIS" means adopting CAMEL/OASIS directly, not copying MiroFish.
- **Fit:** Conflicts with Sidira's core design in default form (OASIS agents are re-instantiated per run — **breaks the frozen identity-continuity guarantee**; the free-running loop is an uncontrolled, unblinded information channel — **breaks the leakage firewall**). Only defensible posture (the founder's framing, confirmed): use OASIS to generate **network-diffusion structure** (who-sees-what, reach, cascade size), then feed that as *context* into Sidira's existing frozen-agent elicitation, with the scorer + null-integrity certificate remaining the judge. Run it **blinded** and keep the no_persona shadow + null gate.
- **Effort:** **L** — heavy new deps (`oasis-ai`, `camel-ai`), separate worker process (mirrors the persona-worker split), a substrate→persona mapping layer, and validation proving no smuggled leakage. **Do not start without a network-effects product requirement.**

---

## (c) DO-NOT-COPY (explicit)

| Item | MiroFish evidence | Why it's poison for Sidira |
|---|---|---|
| **The accuracy posture (no validation)** | repo-wide: 0 benchmark/backtest/calibration | This *absence* is Sidira's entire moat. Copying the posture = deleting the product. |
| **Single-LLM Markdown "report" as the result surface** | `report_agent.py` | Replaces a statistical instrument (paired lift + CI + null cert) with prose that's trivially over-claimable. |
| **`random.choice` synthetic personas** (MBTI/karma/follower/country) | `oasis_profile_generator.py:156+`, `:792-845` | Direct regression vs GMM clustered real-data packs. "Personas from data" is marketing; it's LLM fan-fiction off a Zep summary. |
| **The Zep graph-memory write-back loop** | `zep_graph_memory_updater.py:340-418` | Closed simulation→memory→persona feedback loop: model output becomes next run's model input. Textbook two-table leakage-firewall violation; would void any sealed backtest. |
| **Shared graph memory with no per-entity scoping** | global Zep graph | Leakage-shaped risk; Sidira's frozen, write-once, customer-scoped `agent_memory.py` is deliberately the opposite and is correct. |
| **Config-authored behavioral dials** (`activity_level`, `active_hours` hand-set per agent) | `run_parallel_simulation.py:1066-1074` | Demand-characteristics leak: the experimenter who frames the hypothesis also sets who's loud. (This is the trap *inside* borrow #5 — take the mechanic, source the weight from the cluster posterior.) |
| **The IPC/file-poll interview substrate** | `run_parallel_simulation.py:217-601` (mtime polling, SQLite trace scrape) | Sidira's frozen-artifact replay chat (`agent_memory.py:build_replay_messages`) already does this with no live process/polling. The mechanism is inferior, not just the feature. |
| **Twin-regeneration agent memory** | OASIS re-instantiates agents per run | Sidira's frozen `identity.md`/`initial_reaction.md` continuity guarantee explicitly defends against this MiroFish failure mode. |
| **Porting the Vue `GraphPanel` wholesale** | `GraphPanel.vue` (rainbow 10-color palette, floating rounded cards, breathing-glow pills, edge-label pill toggles) | Violates DESIGN.md §4.1 (color budget), §7.1 (4px radius, no pills), §10 (no AI shimmer/pulsing, no decorative marks). Rebuild native if at all. |
| **LLM-invented ontology as ground truth** | `ontology_generator.py` | Fine as a *draft* (#6); fatal if it defines persona truth — prior-echo amplifier. |

---

## (d) Prior-echo weak spot — what helps, what hurts

Sidira's documented weakness is "more-is-better"/prior-echo bias on counter-intuitive product changes. The councils split the candidates cleanly:

**Would WORSEN it (avoid):**
- **OASIS-style interaction loops** *as predictor*. The single sharpest strategic finding (sim-mechanics lens): in `env.step`, every agent's LLM-generated post becomes another agent's input next round. LLMs already over-reproduce conventional sentiment; once they react to *each other's* conventional sentiment, the loop is a positive-feedback echo chamber that drives the population toward the intuitive prior and **buries the counter-intuitive signal** — with no blinding, control arm, or null check inside the rounds. This is the affirmative reason network interaction must be **substrate-only**. Sidira's static, one-shot, *paired* design is a *deliberate defense* against this echo — an architectural advantage, not a missing feature.
- **MiroFish's generative ontology→generative persona chain** (data-science lens): prior-echo-*positive*; would amplify the Hewitt-inflation weak spot. Safe only if the *data* (not the LLM) defines what's true and the Jaccard/holdout gates catch hallucinated structure.

**Would HELP (pursue):**
- **An evidence graph that makes priors inspectable** (Codex's strongest recommendation, and the best cross-council idea). Add edge classes `supports_change` / `contradicts_change` / `guardrail_risk` / `weak_or_inferred`, and **show counter-evidence next to every positive A/B prediction.** This makes prior echo *visible* — you can see when a positive verdict rests on generic "users like more" edges instead of concrete contradicting evidence. This is borrow #1's real payoff.
- **Ontology checks that force the hypothesis to name mechanism and metric separately** (Codex). A small gate that separates "desired business outcome" from "observed user mechanism" directly pressures the more-is-better reflex.
- **Constrained (extractive, fixed-schema) seed-doc feeder** (#3/#4): prior-echo-*neutral* — more grounded inputs, not more colorful personas.

---

## Council agreement map

| Topic | Council A (Claude) | Council B (Codex) | Synthesis |
|---|---|---|---|
| Borrow interfaces/substrates, not the predictor | ✅ | ✅ | **Agree** — headline verdict |
| Zero validation = Sidira's moat | ✅ | ✅ | **Agree** |
| DO-NOT-COPY synthetic personas / Zep write-back / single-LLM report | ✅ | ✅ | **Agree** |
| Seed-doc → clustering feeder (constrained, no Zep dep) | ✅ (L) | ✅ (M) | **Agree**; effort L once gates/validation included |
| Time/activity modulation as data-grounded weight | ✅ (S) | ✅ (S/M) | **Agree** |
| OASIS substrate-only, future network-effects mode | ✅ (L) | ✅ (L) | **Agree** |
| **Build a graph viewer** | ❌ **reject** (no edge data; DESIGN.md §10/§4.1/§7) | ✅ **#1 borrow** (M) | **Disagree → resolved:** legitimate *only* after building an **evidence-graph data model** with real provenance edges; the cost is backend, not D3. A persona-similarity graph is forbidden theater. |
| Evidence graph helps prior-echo | (frontend lens skeptical of graph) | ✅ strongest idea | **Adopt the concept**, gated on real edges |
| Library for any node-link view | `visx` (not raw D3 / not react-force-graph) | "small React/D3 component" | **Agree on native rebuild;** prefer `visx` |

---

## Bottom line for the founder

1. **Graph viz (your #1 priority):** the *pretty force graph* is the wrong borrow — Sidira has no relationship data to draw, and faking it violates DESIGN.md. The *right* borrow hiding inside it is the **evidence/provenance panel** — but its value comes from a **backend evidence-graph model** (supports/contradicts/guardrail edges with provenance) that you'd build new. Render it with `visx`, not ported Vue/D3. That same model is also your best **prior-echo defense** (show counter-evidence next to every positive verdict).
2. **Two free, immediate wins (S, no library, DESIGN.md-clean):** cross-highlight between the InspectorRail and the PERSONA READINGS register (#2), and collapse-N-agents-with-count disclosure on the persona drill-down.
3. **Best upstream bet (L):** a constrained, fixed-schema, customer-scoped **doc→feature extractor** that feeds Sidira's existing GMM clustering — it fills a real gap (`adapter.py` is tabular-only) and stays prior-echo-neutral because the data still defines truth.
4. **Keep on the shelf (L, research):** OASIS as a blinded network-effects *substrate*, never the predictor — and only when a network-effects product need is real.
5. **Everything in the DO-NOT-COPY table is load-bearing.** The single most dangerous import would be the Zep write-back loop; the single most strategically corrosive would be adopting their predict-by-vibes posture. Both councils are emphatic: Sidira's validation layer is the whole game, and MiroFish doesn't have one.

*Raw Codex panel: [`codex_council.md`](./codex_council.md). Council A lenses captured inline above.*
