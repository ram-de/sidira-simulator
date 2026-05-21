---
type: session
domain: persona-classifier
status: active
started: 2026-05-16
owner: rmkmar
---

> **For my cofounder:** This is the live working state of the Pythia persona-classifier
> + simulator stack. Skim "Goal" and "Magic Moment Sprint plan" to orient, then jump
> to the bottom for the most recent updates. Phase 2.5 (weighted population sampling)
> is the next big chunk — design is locked in `ROADMAP.md` and tickets are in the
> GitHub Project. Start there.

# Session: persona-classifier — Generic user persona discovery from feature-group metrics

## Goal
Build a company-agnostic ML pipeline that takes a user-level dataset organized into a FIXED set of feature groups (with VARIABLE metrics inside each group) and outputs (a) persona definitions, (b) persona **weights** (mixture proportions), and (c) a classifier that assigns new users. First instance: 10K DoorDash users across 7 feature groups from the source spreadsheet.

## Model Strategy (Updated 2026-05-16)
**No pretraining. No fine-tuning. Use off-the-shelf LLMs (Claude / GPT) for agent simulation.**
The specialized 8B model in the Pythia roadmap is a later-stage problem. For now:
- Each persona becomes a structured **system prompt** built from its centroid feature profile
- Simulation = LLM inference with persona prompt + hypothesis stimulus
- The persona pack is the prompt-generation input, not training data

This collapses scope dramatically — the persona-classifier work no longer feeds an ML training pipeline. It feeds a **prompt-templating layer** that drives off-the-shelf model inference.

## Why This Exists — Pythia Context
Pythia agents must faithfully represent a company's userbase to produce trustworthy simulation outcomes. That requires two outputs per company:
1. **Persona set** — what archetypes exist (used to define agent personalities)
2. **Persona weights** — what mix of those archetypes the population actually contains (used to sample agents in the correct proportions during simulation)

Without weights, an agent simulation is a uniform-sample fantasy. With weights, the simulation is a calibrated reflection of the real company.

This persona-calibration layer is distinct from:
- `pythia-scraper` (pretraining corpus — generic consumer behavior)
- `augur` (consumer product surface)

Proposed repo: `pythia-personas` (new) — runs per customer, ingests their user dataset, emits a persona pack consumed by the simulation engine.

## Source Spec
- Spreadsheet: https://docs.google.com/spreadsheets/d/1R_KuqOeUJT_5GfY4aUgaMYTNwB5JhI8aPyywJUmSrtY
- 7 feature groups (constant across companies):
  1. Demographic & Identity
  2. Behavioral Patterns
  3. Motivations & Jobs-to-be-Done
  4. Pain Points & Friction
  5. Value Sensitivity
  6. Channel & Tech Behavior
  7. Loyalty & Lifecycle Stage
- ~140 DoorDash-specific metrics mapped under these groups.

## Core Design Idea
Persona "extraction" is unsupervised clustering, not classification. The deliverable is a **Persona Pack** (JSON artifact) consumed by the Pythia simulation engine, containing:
- Persona definitions (centroid feature profile + LLM-generated name/description/JTBD)
- Persona weights — multiple schemes (head-count, order-weighted, revenue-weighted) so simulations can choose
- Per-user assignment table (consumer_id → persona_id + confidence)
- Stability score (bootstrap survival rate) — Pythia must know if personas are real or noise

Genericity comes from a 4-layer architecture:
- **Layer A — Adapter (company-specific)**: maps raw metrics → standardized feature schema per group (z-scores, share/ratio metrics, robust scaling, one-hot for categoricals). Only this layer changes per company.
- **Layer B — Group Encoder (generic)**: per-group dimensionality reduction → fixed-size embedding (e.g., 8-dim per group). Methods: PCA / denoising autoencoder / pooled stats. Outputs 7 × k = ~56-dim user vector.
- **Layer C — Persona Model (generic)**: clustering (HDBSCAN or GMM with BIC; k-means baseline) on concatenated embeddings → cluster IDs → LLM-labeled persona names from centroid profile.
- **Layer D — Calibration (generic)**: computes weight distributions, stability scores, and emits the Persona Pack JSON. Also trains the supervised assignment classifier on (features → cluster_id).

## In Progress
- [ ] **Magic Moment Sprint — Wave 6 (Validation)**: T12 e2e demo, `/qa` live browser test, `/review`, `/retro`. Waves 0-5 ✅ merged to main as of 2026-05-21.

## Magic Moment Sprint plan (started 2026-05-21)

**Goal:** PM submits a hypothesis → 10 agents react via real LLM calls → confidence score + diagnosed weaknesses + refinement suggestions returned and rendered in the UI. Hardcoded `customer_id="demo"`. No auth, no multi-tenancy. Fixture Persona Pack + existing Acme Feature Pack sample.

**Canonical roadmap:** https://github.com/ram-de/pythia-simulator/blob/main/ROADMAP.md

### Execution waves (parallelized where safe)

| Wave | Tasks | Status | Commit |
|---|---|---|---|
| **0. Plan review** | `/plan-eng-review`; 4 critical decisions locked through user; 4 more pre-recommended | ✅ Done | `6de33f8` |
| **1. Foundation** | T1 Postgres+Alembic 001; T4 feature_pack_loader; T5 6-persona fixture pack | ✅ Done | `69b34d8` |
| **2. Loaders** | T2 postgres adapter + repos (Postgres + InMemory); T3 persona_loader | ✅ Done | `69b34d8` + `cbabb2c` |
| **3. End-to-end wiring** | T6 POST /simulations 202+BackgroundTasks; GET /simulations/{id}; GET /state; GET /capabilities; 60s timeout + N-of-M | ✅ Done | `cbabb2c` |
| **4. Intelligence** | T7 scoring (weakness + sentiment + 0.6/0.4 aggregator); `/codex` formula review; T8 refinement | ✅ Done | `8c03641` + `71325b9` (PR #1 → `165a1e2`) |
| **5. Frontend** | T9 `/simulations/new` form; T10 result view; T11 `/state` polling — **parallel via 2 sub-agents** | ✅ Done | `808f689` (PR #2 → `3dce93a`) |
| **6. Validation** | T12 e2e demo; `/qa`; `/review`; `/retro` | 🔲 Next | — |

### gstack invocations planned

- ✅ now: `/plan-eng-review` — lock in architecture before touching code
- During Wave 4: `/codex` — second opinion on scoring formula
- Before each commit: `/review` — independent diff review
- After Wave 6: `/qa` — live browser testing of the wizard + simulation flow
- After demo: `/retro` — capture lessons for second sprint

### Architecture decisions locked (post-/plan-eng-review, 2026-05-21)

1. ✅ Fixture pack path: `local-artifacts/customers/demo/personas/v_1/persona_pack.json` (matches prod R2 layout exactly)
2. ✅ POST /simulations: 202 + simulation_id; background `asyncio.create_task`; frontend polls `/state` every 5s
3. ✅ Score formula: `0.6 × sentiment + 0.4 × (1 − weakness_concentration)`
4. ✅ Refinement: separate LLM call after scoring, independent service
5. ✅ Postgres: full migration 001 (simulations + agent_instances + agent_feedback)
6. ✅ Live progress: 5s poll, SSE deferred to Phase 4

### New decisions from the review

7. ✅ Reproducibility: `temperature=0` + fixed `seed` + cache `(identity_prompt_hash, persona_id) → reaction`
8. ✅ Per-agent timeout: `asyncio.wait_for(60s)` + emit `agent.reaction.failed`; frontend renders N-of-M

### Review findings flagged for during-implementation attention

- **3N LLM calls/simulation** (10 personas × 3 = 30) — semaphore-bounded; watch Groq rate limits — *handled via `max_concurrent_agents=5` semaphore (Wave 3)*
- **Refinement input contract** — define `RefinementInput` schema explicitly before writing the prompt composer — *Wave 4 task*
- **DRY for loaders** — extract `_load_json_artifact(path, schema)` helper in `adapters/base.py` — *done in Wave 1 (`base.py`)*
- **Fixture pack validation** — write fixture last; add import-time validation test — *done in Wave 1 (8 fixture validation tests)*

Full review report: `pythia-simulator/MILESTONES.md` § "GSTACK REVIEW REPORT"

### Execution log (live updates)

- **2026-05-21 Wave 1+T3** (commit `69b34d8`): Postgres schema + Alembic 001 (4 tables); feature_pack_loader + persona_loader with `ArtifactNotFound`/`ArtifactSchemaError` taxonomy; `adapters/base.py` DRY helper; 6-persona fixture (Maya/Dom/Priya/Lex/Jordan/Sam) with all 3 weight schemes summing to 1.0; `.gitignore` exception so `local-artifacts/customers/demo/` is checked in. +9 tests (32 total).
- **2026-05-21 Wave 2+3** (commit `cbabb2c`): postgres adapter + repository Protocol pattern (Postgres impl + InMemory impl, both customer-scoped); `SimulationOrchestrator` as HTTP-agnostic glue; `BackgroundTasks` scheduling (testable, no event-loop choreography); `AgentRecord` dataclass so persona_id/persona_name flow to repos; `sim_id` kwarg pinned across DB/R2; 60s `wait_for` + `return_exceptions=True` for N-of-M; `temperature=0`+`seed` plumbed through Groq+Anthropic; lazy chat client (no crash on missing key). +10 tests (42 total). Live HTTP demo verified.
- **2026-05-21 Wave 4** (commits `8c03641` + `71325b9`, merged via PR #1 → `165a1e2`): T7 scoring + T8 refinement services. `WeaknessClassification` + `SentimentClassification` Pydantic schemas; `services/scoring.py` with `classify_weakness`/`classify_sentiment`/`aggregate` using locked `0.6 sentiment + 0.4 (1 − weakness_concentration)` formula; `services/refinement.py` with explicit `RefinementInput` schema; `SimulationRunner._score()` stub replaced. `/codex` review applied — 5 P2/P3 fixes landed in `71325b9`.
- **2026-05-21 Wave 5** (commit `808f689`, merged via PR #2 → `3dce93a`): T9 `/simulations/new` submit form; T10 result view rendering score + agent reactions + refinement; T11 `/state` live polling for in-flight progress. Delivered in parallel via 2 sub-agents per the plan. Diff: +2,468/−31 across `simulations/new/page.tsx`, `simulations/[id]/page.tsx`, `lib/api-types.ts` (new — 1,458 lines of generated types), `lib/api.ts`, `next.config.js`.

### Wave 4 entry plan

1. Define `WeaknessClassification` + `SentimentClassification` Pydantic schemas (single LLM call per agent each, via `chat_json`)
2. `services/scoring.py`:
   - `classify_weakness(reaction) → WeaknessClassification`
   - `classify_sentiment(reaction) → SentimentClassification`
   - `aggregate(reactions) → SimulationResult` using the locked `0.6 sentiment + 0.4 (1 − weakness_concentration)` formula
3. Replace `SimulationRunner._score()` stub with real call
4. `/codex` consult on the aggregation formula before T8 starts (the cross-model check we pre-planned)
5. `services/refinement.py` with explicit `RefinementInput` schema (Hypothesis + top-K weaknesses + agent_reaction_summaries)
6. Persist `result_json` via the orchestrator (already wired)
7. Tests: unit test scoring with hand-built reactions; eval test with 10 (hypothesis, expected-score-band) fixtures (TEST-3)

## Completed
- [x] Pulled full feature-group schema from spreadsheet (7 groups, ~140 metrics)
- [x] Drafted 4-layer architecture + Layer E prompt compiler
- [x] Created repo `git@github.com-personal:ram-de/pythia-personas.git`
- [x] Scaffolded code: adapter, encoder, cluster, calibrate, compile_prompts, schema, cli, io
- [x] Inspected real Snowflake table `PRODDB.RAMKUMARKARUNANIDHI.CHANNEL_TECH_FEATURES_10K`
- [x] Identified populated vs NULL columns; calibrated config to reality
- [x] Run #1: full pipeline, k=12, stability 0.797 — demographics dominated
- [x] Run #2: prefilter Active + exclude demo/lifestage from embedding, k=7, stability 0.439 — niche personas clean, 53% mass remains
- [x] Committed sample Persona Pack to repo at `samples/run_2_active_only/`
- [x] Run #5 (2026-05-17): Added population baseline + persona feature snapshot to every prompt; auto-named all 10 personas from z-deltas; optional Claude polish via ANTHROPIC_API_KEY. Sample updated to `samples/run_5_with_baseline_and_names/`. Commit `cf28f94`.
- [x] Run #6 (2026-05-17): Explicit baseline scope label in every prompt (was ambiguous "this population"); per-persona behavioral snapshots for FIXED_* lifestage segments. Commit `5ef6866`.
- [x] Run #9 (2026-05-17): **Source data enriched** — 20+ previously-NULL columns now populated (DashPass status, app sessions, fee discounts, JSON profiles for dow/tod/channel/category, subscription health, goto-merchant score). Added `json_counts` adapter type. New naming rules covered Healthy DashPass Subscriber, DashPass Grocery Power, Discount-Driven Restaurant Regular, Unreachable Disengaged. **Stability 0.439 → 0.670 (passes 0.65 threshold for first time).** Residual 53% mass split into P03 (36% DashPass Healthy) + P06 (40% Discount-Driven Restaurant) + P07 (10.7% Unreachable). Commit `cdd1e13`.
- [x] **Removed all hard-coded DoorDash naming rules** (2026-05-17): caught design flaw — `_NAMING_RULES` referenced DoorDash-specific column names (dashpass_status, weekly_grocery_stockup_flag, etc.) breaking architecture genericity. Replaced with LLM-first naming + generic `Persona##` fallback. Commit `7767b95`.
- [x] Run #10 (2026-05-17): **End-to-end LLM naming via Groq** verified. Added Groq support to `_llm_name_groq()` using OpenAI-compatible API at `https://api.groq.com/openai/v1`. Provider preference: Groq → Anthropic → fallback. Default model `llama-3.3-70b-versatile`. All 10 personas got behavioral names + descriptions + JTBD from Groq in one pass. Sample at `samples/run_10_llm_named_groq/`. Commit `78f889a`.
- [x] **Feature Pack Crawler designed + scaffolded** (2026-05-20). Brainstormed the third Pythia simulation input (alongside personas + PM hypothesis): a weekly Playwright crawler producing reverse-PRD + reverse-Figma per capability, in the same shape PMs use to submit new features. Spec written to wiki + committed to both `pythia-personas/docs/` and the new `pythia-crawler` repo. System architecture finalized (3-repo composition: pythia-personas + pythia-crawler + pythia-simulator, R2 as artifact contract). New repo bootstrapped: https://github.com/ram-de/pythia-crawler — initial commit `23ffcc6` includes package skeleton, working storage adapters, schema, CLI, smoke tests (5 pass), and a complete fictional Feature Pack sample at `samples/example_acme_2026-W21/`.
- [x] **Milestone tracking added** (2026-05-20). `MILESTONES.md` written in both repos to track phase-by-phase progress through MVP.
- [x] **pythia-simulator scaffolded** (2026-05-20). https://github.com/ram-de/pythia-simulator — initial commit `6ec425d`. Monorepo: FastAPI backend + Next.js frontend + Pydantic schemas. Backend tests pass (6 smoke). **Agent memory baked in from day 1** with explicit identity-continuity guarantee: chat-time agent is the SAME entity that simulated, not a re-instantiation from the persona template (this is the mirofish failure mode we explicitly fix). Architecture spec updated to call out the guarantee + the two invariants that enforce it.
- [x] **MiroFish prior-art adapted** (2026-05-20). Commit `9261c8c`. Surveyed `~/mirofish-ui/`, extracted 4 transferable patterns into pythia-simulator: (1) `SimulationRunState` + JSONL event log, (2) parallel agent execution via `asyncio.gather` with semaphore, (3) `_CHAT_GUARD_PREFIX` for in-character chat, (4) JSON repair helper for LLM structured outputs. Tests: 10 passing. Rejection rationale committed to `docs/mirofish-prior-art.md` — explicit list of what we DIDN'T copy (inter-agent socialization, Zep memory, subprocess IPC, config auto-gen, multi-platform, narrative output, zh-CN).
- [x] **Future-phase milestones documented** (2026-05-20). All three repos. Simulator phases 2-10 (Postgres + loaders → real LLM scoring + refinement → chat UX → Clerk multi-tenancy → observability → first customer → Karpathy refinement loop → Layer-3 calibration → specialized 8B model). Each phase has goal, tasks, acceptance, dependencies, risks, effort estimate. Crawler phases 2-5 (Playwright walker → synthesis → R2 + diff → first customer). Personas phases 4-8 (Round 2 enrichment → R2 → schema v1.1 → first customer → Layer-3 loop). Phase numbers aligned across repos at shared milestones. Commits: simulator `09a3823`, crawler `91bbb93`, personas `5d645b0`.
- [x] **Phase 4.5 scaffolded: Persona Builder UI** (2026-05-21). https://github.com/ram-de/pythia-simulator commit `14b9ce8`. Decisions locked in: (1) Snowflake-only MVP, (2) single-source builds, (3) LLM-assisted column→7-feature-group mapping (cheap UX win for wide tables), (4) keep all pack history forever (data size negligible), (5) **single UI across all three producers** — `pythia-simulator` frontend now has 3 top-level tabs (Personas / Product / Simulations). Backend stubs: `adapters/feature_stores/` (pluggable Protocol + Snowflake adapter), `adapters/credentials.py` (envelope encryption, local-key dev → KMS in Phase 5), `services/column_mapper.py` (LLM mapping suggestions), `services/persona_builder.py` (orchestrator wrapping pythia-personas library), 3 new API route groups (`/feature-stores`, `/persona-builds`, `/persona-packs`). Frontend: shared `TopNav` component, landing page reworked, `/personas/new` 7-step wizard with stepper UI, placeholder bodies per step. All 6 new endpoints registered; all wizard routes serve 200. Tests: 10 passing.

## Next Steps (post-run #2)

### Round 1 enrichment — DONE (Run #9, 2026-05-17)
Source table re-populated with: DashPass status, device footprint, notification reachability profile/status, promo eligibility, app session freq, day-of-week / time-of-day / channel / category JSON profiles, health-of-subscription JTBD, goto-merchant score, out-of-pocket %, fee discounts (delivery/service/volume-share), consumer out-of-pocket per order, promo eligibility flag, avg notif per cx weekly. Stability 0.439 → 0.670.

### Round 2 enrichment — still NULL, highest-leverage next pull
- `PRICE_SENSITIVITY_SCORE_PSM`, `PROMO_SENSITIVITY_MODEL_SCORE`, `IS_LOW_ROI_CX` (Pricing & Affordability PSM v3)
- All loyalty fields: `HAS_REDEEMED_*`, `POINTS_*`, `ROAS`, `LOYALTY_MEMBER_AOV`, `TOTAL_REDEMPTIONS*`
- `UPSS_LIFESTAGE_ATTRIBUTE`, `UPSS_CHURN_ENGAGEMENT_SCORES`
- Notifications Hub: `HUB_NOTIFICATIONS_SENT`, `HUB_VIEW_TO_CLICK_RATE`, `HUB_REVISIT_RATE`
- `IS_EMPLOYEE`, `IS_INTERNAL_DD_CONSUMER` (filter, not feature)
- `HIGH_PRICE_VARIANCE_ITEMS_EXPOSED`, `ORDER_DROP_AT_FEE_CHANGE`
Adding these should push stability >0.75 and split the two big clusters (P03 DashPass Healthy, P06 Discount-Driven Restaurant) into 3–4 sub-personas each.

### Other follow-ups (logged in repo README)
1. **Stratified sample** — current 88% Active. Pull lifestage-stratified 10K so dormant/churned have ≥1K each.
2. **Sub-cluster the residual P04** with HDBSCAN as a diagnostic (10-min spike).
3. **LLM persona naming** — wire Anthropic call in `compile_prompts.py`.
4. **Per-cluster stability** (Jaccard) instead of single overall ARI.
5. **HTML diagnostic report** — BIC curve, weight distributions, t-SNE, baseline crosstab.
6. **High-leverage cluster alerts** — flag clusters where orders/revenue weight >> headcount weight.
7. **Persona Pack schema versioning** — bump to 1.1 when feature enrichment lands.

### Decisions made
- ✅ Unsupervised clustering, not classification — Pythia needs persona definitions, not labels.
- ✅ 5-layer architecture: Adapter / Encoder / Cluster / Calibrate / Compile Prompts.
- ✅ Persona Pack JSON as the deliverable contract.
- ✅ No pretraining — use off-the-shelf LLMs with structured prompts.
- ✅ Multiple weight schemes (headcount + orders) so simulations can choose.
- ✅ Prefilter known lifestage segments as fixed personas; cluster only the residual.
- ✅ LLM-first naming with generic Persona## fallback — keeps Layer E company-agnostic.
- ✅ Groq (`llama-3.3-70b-versatile`) as default LLM provider — fast and free-tier-friendly. Anthropic as fallback for higher quality.

### Provider config (current)
- Primary: `GROQ_API_KEY` → Groq via OpenAI-compatible endpoint (`llama-3.3-70b-versatile`)
- Fallback: `ANTHROPIC_API_KEY` → Claude (`claude-sonnet-4-6`)
- Force-fallback: `pythia-personas run --no-llm` → `Persona01`, `Persona02`, …
- Groq key is at `~/mirofish-ui/.env` (also used by mirofish). Permission rule granted: `Read(/Users/ramkumar.karunanidhi/mirofish-ui/.env)`.

### Repo state
- Branch: `main`
- Latest commit: `78f889a` (Run #10 with Groq LLM naming)
- Latest sample: `samples/run_10_llm_named_groq/`
- Local outputs: `outputs/dd-20260517T162638/` (gitignored)

## Real Data Findings (2026-05-16)
**Table:** `PRODDB.RAMKUMARKARUNANIDHI.CHANNEL_TECH_FEATURES_10K` — 146 cols, 10K users (deduped), snapshot 2026-05-14

### Population coverage by feature group
- ✅ **Behavioral Patterns** — well populated (total_orders, freq_28d/90d, lifestage_behavioral, avg_days_between, NV freq). Missing: DOW/TOD profile, app sessions, channel mix, category mix (those are NULL).
- ✅ **Motivations & JTBD** — populated (stockup_flag, conv_basket, speed_seeker, dp_value_seeker, category_motivation_profile JSON, promo_triggered_share, reminder_triggered_share). Missing: goto_merchant, deals_engine, loyalty_motiv, health_subscription.
- ⚠️ **Pain Points** — only 3 populated (high_fee_order_rate, notification_unsubscribe_rate, promo_dependency_score, mark_as_spam, app_uninstall). Everything else NULL.
- ❌ **Value Sensitivity** — almost entirely NULL. Only `promo_redeemer_flag` populated. PSM, promo sensitivity, fee discounts, price ratios all NULL.
- ✅ **Channel & Tech Behavior** — well populated (device_type, channel, source, message_type, num_notif_weekly, all *_within_24h rates).
- ✅ **Lifecycle** — populated (cx_lifestage_*, all *_28d_agg, *_90d_agg flags).
- ❌ **Loyalty** — ALL NULL. Every points/redemption/cumulative column is empty.
- ⚠️ **Demographic & Identity** — only basic IDs/geo/consumer_experience. DashPass, fraud, device_footprint, reach_profile NULL.

### Distribution skews
- `HV_MAU_SEGMENT`: 72% High Value MAU, 28% Intermittent (1057+676+470+343+267). **This is NOT a representative population sample — it's already filtered to engaged users.**
- `CX_LIFESTAGE_DETAILED_STATUS`: 88% Active, 8% Dormant Resurrected, 3% Churned Resurrected, 1% New. Almost no churned users in the sample.
- `HV_MAU_SEGMENT` is a useful **baseline label** to compare cluster output against (does GMM rediscover the HV vs Intermittent split? Does it produce finer structure inside HV?).

### Action items
- Drop the all-NULL columns from the config (saves processing, avoids false-zero embeddings).
- Parse `CATEGORY_MOTIVATION_PROFILE` JSON into 4 ratio columns (grocery/restaurant/retail/rx).
- Convert booleans (PROMO_REDEEMER_FLAG, etc.) to 0/1.
- Tell user about the skew — they may want a more representative sample at some point (include dormant + churned).

## Key Files
- `~/vaults/personal/wiki/projects/pythia.md` — Pythia project overview (consumed for context)
- `~/vaults/personal/wiki/docs/pythia-de-spec.md` — pretraining corpus spec (orthogonal layer)
- `~/vaults/personal/wiki/docs/pythia-feature-pack-crawler-spec.md` — **feature pack crawler design (2026-05-20)** — third simulation input alongside persona pack + PM hypothesis
- `~/vaults/personal/wiki/docs/pythia-system-architecture.md` — **system architecture (2026-05-20)** — full three-repo composition, artifact store contract, stack decisions, deployment topology
- `~/Projects/pythia-scraper/` — Stage A (corpus); NOT the home for this work
- `~/Projects/augur/` — consumer product (NOT the home either)
- Proposed new repo: `pythia-personas` at `git@github.com-personal:ram-de/pythia-personas.git`

## Key Context
- 10K users is small → favor algorithms robust at low N (GMM with BIC; avoid deep nets that need scale).
- 7 groups × variable metrics = good fit for **per-group encoders** (instead of one giant feature vector) — this is what makes the framework portable across companies.
- Persona model output = (cluster_id, persona_label, persona_description). Downstream supervised classifier (XGBoost/LogReg) trained on (features → cluster_id) handles new-user assignment + can be shipped as the production "classifier model" the user asked for.
- Likely persona archetypes from the DD metrics: Power Restaurant Loyalist, Weekly Grocery Stockup, Promo-Triggered Bargain Hunter, DashPass Convenience Seeker, Late-Night Snacker, Dormant At-Risk, New-and-Exploring, Speed-First Premium, etc. — let clusters speak rather than presupposing.
- Generic guarantee: any new company that fits its metrics into the same 7 groups can swap Layer A and reuse B + C unchanged.
