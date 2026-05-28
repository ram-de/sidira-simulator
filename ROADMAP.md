# Sidira — Overall Roadmap

**Last updated:** 2026-05-28 (Phase 4.7 Sidira rename in progress)

The Sidira product spans three repos. This document is the strategy map: phases, sequencing across repos, critical path, and what to focus on next. **Open tickets** live in the [Sidira GitHub Project](https://github.com/users/ram-de/projects/) (multi-repo board across sidira-simulator + pythia-personas + pythia-crawler), not in markdown — see "Where to find what" below.

| Repo | Role |
|---|---|
| [`pythia-personas`](https://github.com/ram-de/pythia-personas) | Persona Pack producer (clustering, weights, prompt compilation) |
| [`pythia-crawler`](https://github.com/ram-de/pythia-crawler) | Feature Pack producer (weekly Playwright crawl → reverse PRD + Figma) |
| [`sidira-simulator`](https://github.com/ram-de/sidira-simulator) | Customer-facing app (FE + BE + agent memory + single UI for all 3 producers) |

---

## Where to find what

| Want to know... | Look here |
|---|---|
| The big picture (why, order, critical path) | This file |
| What's the next chunk of work? | This file → "What's next" + GitHub Project filtered by Status = Next |
| What does "Phase N done" look like? | This file → "Phase specs" |
| What tickets are open right now? | GitHub Project (canonical), filtered by Status = Open / In progress |
| What did we just ship? | `CONTEXT.md` (current sprint narrative) + `git log` |
| Conventions, how the team works with AI agents | `AGENTS.md` |
| Architecture / system design | `docs/system-architecture.md` |

**The per-repo `MILESTONES.md` files are now stubs.** Anything that used to live there moved to either this ROADMAP (strategy) or the GitHub Project (tickets).

---

## Where we are today (2026-05-28)

✅ **Magic Moment Sprint complete** (Phases 2 + 3). A PM can submit a hypothesis through the UI, see agents react via real LLM calls, and get a confidence score + diagnosed weaknesses + refinement suggestions rendered live.
✅ **Phase 2.5 complete.** Population-size input, Hamilton allocation, identity seeds, score/weakness CIs, degradation guard, and population-aware frontend results are shipped.
✅ **Phase 4 agent chat foundations shipped.** PMs can chat with individual agents and persona groups, including arm-scoped group chat in A/B mode.
✅ **Phase 4.6 A/B experiment mode shipped.** Wizard toggle, paired treatment/control runner, paired-lift formula, and lift-first result UI are live.
🚧 **Phase 4.7 Sidira rename in progress.** Visible product surface, `SIDIRA_*` config namespace, `sidira_simulator`, and active Sidira docs/roadmap are merged. sidira.ai/domain metadata (#115) remains.

What's **not yet real**:
- **Real persona generation.** Demo uses a hand-built 6-persona fixture. pythia-personas can already generate packs; the simulator just hasn't consumed a real one yet.
- **Persistence across restarts.** `InMemorySimulationRepo` resets on backend restart. Phase 5a (#68) un-stubs the Postgres wiring (schema + adapters already exist) — small standalone ticket, carved out of Phase 5 so it can ship before auth.
- **Multi-tenancy.** Everything is hardcoded to `customer_id = "demo"`. Phase 5.
- **Crawler runs.** Feature Pack is still the hand-built Acme sample. crawler Phase 2 builds the Playwright walker.

---

## Cross-repo phase alignment

| Phase | `sidira-simulator` | `pythia-personas` | `pythia-crawler` | Status |
|---|---|---|---|---|
| 0 | Design | Architecture | Design | ✅ Done |
| 1 | Scaffold | Adapter/Encoder/Cluster/Calibrate | Scaffold | ✅ Done |
| 1.5 | MiroFish adaptation | — | — | ✅ Done |
| 2 | Persona + Feature Pack loaders + Postgres metadata | (Round 1 ✅; Round 2 pending) | Walker (Playwright) | ✅ Simulator done; crawler 🔲 |
| 3 | Simulation runner + scoring + refinement | — | Synthesis (PRD + Figma) | ✅ Simulator done; crawler 🔲 |
| **2.5** | Weighted population sampling | (per-cluster stats for v1.1 — optional) | — | ✅ Done |
| 4 | Agent chat UI (the differentiator) | — | R2 wiring + diff | ✅ Simulator done |
| 4.5 | Persona Builder UI (scaffolded) | — | — | 🚧 Scaffolded |
| 4.6 | A/B experiment mode | — | — | ✅ Done |
| **4.7** | **Sidira rename: product, config, package, docs, repo/domain metadata** | Repo/package names later | Repo/package names later | 🚧 In progress |
| **5a** | **Postgres repo wiring (carve-out — #68)** | — | — | 🔲 Pending |
| 5 | Auth (Clerk) + multi-tenancy + per-customer R2 prefix isolation | R2 artifact integration | — | 🔲 Pending |
| 6 | Observability | Schema v1.1 + validation | — | 🔲 Pending |
| 7 | First customer (Lumen MVP) | First customer | First customer | 🔲 Pending |
| 8 | Refinement loop UX (Karpathy AutoResearch) | Layer-3 calibration prep | — | 🔲 Pending |
| 9 | Layer-3 calibration | Layer-3 loop | — | 🔲 Pending |
| 10 | Specialized 8B model | — | — | 🔲 Long-term |

---

## Critical path

```
✅ Magic Moment (Phase 2+3) ──> ✅ Phase 2.5 (calibrated mix) ──> ✅ Phase 4/4.6 (chat + A/B) ──> 🚧 Phase 4.7 (Sidira rename) ──> Phase 5a (Postgres wiring, #68) ──> Phase 5 (auth+multi-tenancy) ──> Phase 7 (first customer)
                                                                                                                       │
                                                                                                                       ▼
                                                                                                              Phase 8 → 9 → 10
```

**Parallel lanes** (can run alongside the critical path):
- Phase 4.5 Persona Builder UI completion
- Crawler Phase 2 (Playwright walker) — unblocks when a real customer has a product to crawl
- Phase 6 Observability — gets fast-tracked once a customer is live

---

## What's next

**Phase 4.7 — Sidira rename.** The product is still pre-public, so we are finishing the naming cleanup now instead of carrying the old placeholder into first-customer setup.

Current ticket order:
- **#114 done:** active simulator docs and roadmap now read as Sidira while preserving historical session logs and compatibility fallbacks.
- **#115 active next:** configure sidira.ai deployment/origins and GitHub metadata after docs are coherent. The simulator repo is now `sidira-simulator`; producer repos remain `pythia-*`.

Already merged in this phase:
- **#111:** visible product surface and FastAPI display metadata.
- **#113:** `SIDIRA_*` config namespace with `PYTHIA_*` fallbacks.
- **#112:** backend package/import/CLI rename to `sidira_simulator` / `sidira-simulator`.

Acceptance for the phase: a new teammate reads the active docs as Sidira end-to-end; local setup uses `SIDIRA_*` and `sidira_simulator`; sidira.ai/app/API origins are configured; any old-name references are explicitly historical, compatibility-only, or intentional producer repo/package names.

---

## Phase specs

Each phase spec below lives in this file (not per-repo MILESTONES) for cross-repo coordination. Tickets to execute each phase live in the GitHub Project.

### Phase 0 — Design ✅

- 3-repo architecture finalized; R2 as artifact contract
- Stack: Python/FastAPI backend, Next.js/TS frontend, Postgres on Neon, Clerk for auth, Cloudflare R2 for artifacts
- Agent memory + identity-continuity guarantee designed in
- Decided NOT to fork mirofish (`docs/mirofish-prior-art.md`)

### Phase 1 — Scaffold ✅

- All 3 repos scaffolded with passing smoke tests
- Backend: FastAPI app, schemas, agent memory, R2 adapter, Groq+Anthropic chat client, simulation runner skeleton
- Frontend: Next.js 14 + TypeScript, 3-tab UI (Personas / Product / Simulations), routes for `/simulations/new`, `/simulations/[id]`, `/agents/[id]`

### Phase 1.5 — MiroFish adaptation ✅

Four patterns ported: `SimulationRunState` + JSONL event log; parallel agent execution via `asyncio.gather` + semaphore; `_CHAT_GUARD_PREFIX`; JSON repair helper. Rejection rationale in `docs/mirofish-prior-art.md`.

### Phase 2 — Persona + Feature Pack loaders + Postgres metadata ✅

- Postgres schema + Alembic migration 001 (4 tables: simulations, agent_instances, agent_feedback, customers)
- Repository Protocol pattern (Postgres + InMemory impls), both customer-scoped
- `feature_pack_loader.py` reads the sample Acme Feature Pack
- `persona_loader.py` reads from `local-artifacts/customers/{id}/personas/v_N/persona_pack.json`
- 6-persona fixture pack (Maya, Dom, Priya, Lex, Jordan, Sam) with head_count + order + revenue weight schemes summing to 1.0

### Phase 3 — Simulation runner + scoring + refinement ✅

- `SimulationRunner.run()` orchestrates one sim end-to-end with `asyncio.gather` + semaphore + 60s per-agent timeout
- Scoring formula (locked): `0.6 × sentiment_score + 0.4 × (1 − weakness_concentration)`, with Bayesian shrinkage toward neutral on small N
- Weakness categories: 6 closed-set values (wrong_metric / wrong_cohort / broken_mechanism / untestable_hypothesis / hidden_guardrail_risk / underpowered_design)
- Refinement service: separate LLM call after scoring, returns 1–3 actionable suggestions
- Backed by 60 backend tests; codex cross-model review applied at PR boundary

### Phase 2.5 — Weighted population sampling ✅

**Goal:** make the calibration thesis true in code. Population-size input + stratified sample + per-agent variance + confidence intervals.

**Tasks** (tickets in the Project):
- `services/population_sampler.py` — largest-remainder allocation over persona weight scheme
- `services/identity_seed.py` — per-agent personal context (age band, locale band, tenure, current state, recent gripe). Hybrid: deterministic fields + optional LLM prose.
- Schema changes: `SimulationRequest.population_size`, `Simulation.sampled_agent_count`, `Weakness.frequency`+`ci_low`+`ci_high`, `AgentInstance.identity_seed`
- Scoring: bootstrap or Wilson CI on weakness frequencies; CI on aggregate score
- Groq rate-limit backoff in `adapters/llm.py`
- Scoring degradation guard (failure-rate threshold)
- Frontend wizard: `Sample size` → `Population` with helper text explaining stratification
- Frontend detail view: CI rendering on score + weakness bars, "Population: 1000 (sampled: 50)" banner, virtualized agent table or grouped-by-persona

**Acceptance:** 1000-population sim runs in <60s, produces score with 95% CI, weaknesses with CIs, 50 agents allocated in correct persona proportions (within ±1 rounding).

**Dependencies:** none on other repos (per-cluster stats from pythia-personas v1.1 would improve variance but is optional).

**Risks:** Groq rate limits at higher sample sizes; UX of 50-agent agent list; CI method choice.

### Phase 4 — Agent chat UI ✅

**Goal:** PM can chat with each agent that participated in a simulation. The defining feature.

Shipped across the Phase 4 tickets: individual-agent chat, persona-group fan-out chat, one-line synthesis, calibration thumbs, and A/B arm-scoped persona-group rooms so treatment/control conversations remain isolated.

### Phase 4.5 — Persona Builder UI 🔲 (scaffolded)

7-step wizard scaffolded with stub bodies (`/personas/new`). Goal: PM connects Snowflake → maps columns to 7 feature groups → triggers a pythia-personas build → resulting pack appears in the simulator. Snowflake-only MVP; single-source builds; LLM-assisted column mapping.

### Phase 4.6 — A/B experiment mode ✅

Treatment/control simulation mode shipped 2026-05-27. Wizard A/B toggle runs paired treatment and control arms, computes predicted lift from matched agents, and renders a lift-first result card. Calibration writeup lives in `docs/4.6-ab-experiment-mode.md`.

Followups carved out of the dogfood:
- #99 de-asymmetric A/B result-page UX.
- #100 wizard cost preview vs backend cap.
- Plumbing cleanup: delete `AB_MODE_DISABLED_UNTIL_LIFT` after soak.

### Phase 4.7 — Sidira rename 🚧

Pre-public rename from the old placeholder to Sidira.

Done:
- #111 visible product surface.
- #113 `SIDIRA_*` config namespace with `PYTHIA_*` fallback compatibility.
- #112 `sidira_simulator` backend package and `sidira-simulator` CLI.

Remaining:
- #115 sidira.ai deployment/origins and GitHub metadata/repo-name decision.

Dependencies: #115 should run after #112/#113/#114 are merged so domain/repo metadata is not racing active code/docs. Repo names remain `pythia-*` until #115 explicitly changes them.

### Phase 5a — Postgres repo wiring 🔲 (carve-out — #68)

Small standalone ticket carved out of Phase 5 so persistence can ship before auth lands. The schema (Alembic 001+002+003) and adapter classes (`PostgresSimulationRepo`, `PostgresAgentInstanceRepo`, `PostgresCustomerRepo`) already exist; only the FastAPI `AsyncSession` dependency wiring in `api/deps.py` is stubbed.

- Un-stubs `_repos()` to return Postgres-backed repos when `DATABASE_URL` is set.
- `InMemorySimulationRepo` stays as the local-dev fallback when `DATABASE_URL` is unset.
- Background-task session lifecycle (orchestrator runs outside request scope).
- Optional `SIDIRA_AUTO_MIGRATE=1` flag for app-startup migration. Legacy
  `PYTHIA_AUTO_MIGRATE` remains the compatibility fallback during the rename.
- ~1 day. Blocks Phase 7 (first customer requires a backend that survives restarts).

### Phase 5 — Auth + multi-tenancy 🔲

- Clerk auth on every API route
- Customer scoping enforced at the repo layer (the Postgres repos already accept `customer_id` — this phase ENFORCES it on every route)
- CORS allowlist per-customer subdomain
- Per-customer R2 prefix isolation (#33)
- Customer signup flow + initial customer record (#31)
- The Phase 5a InMemory fallback is retired; production runs Postgres only

### Phase 6 — Observability 🔲

Sentry (errors) + Langfuse (LLM traces) + Grafana (basic counts). Per-customer cost tracking on LLM spend.

### Phase 7 — First customer (Lumen MVP) 🔲

The entire 3-repo system run against one real customer's data. Crawler walks their product; personas builds from their userbase; simulator runs hypotheses from their PMs. Validates the artifact contract under production conditions.

### Phase 8 — Refinement loop UX 🔲

PM reads refinement, refines hypothesis, resubmits → simulator compares old/new scores → "did the change actually move the needle?" view. Karpathy AutoResearch pattern: one specialized agent per loop role.

### Phase 9 — Layer-3 calibration 🔲

PM "realistic / not realistic" flags on agent reactions become training signal. This is the moat — every customer makes Sidira smarter on their userbase over time. First useful signal expected ~6 months after first customer.

### Phase 10 — Specialized 8B model 🔲

When per-customer feedback volume justifies it (~6–12 months after first customer), fine-tune an 8B model for agent reactions. Off-the-shelf LLMs become the cold-start, the 8B becomes the warm-start moat.

---

## Deferred ideas

**A/B experimentation mode — Phase 4.6 (SHIPPED 2026-05-27).** Part (a) of the original two-part proposal — extend the simulator to model both treatment and control arms with a predicted-lift output — landed on main across PRs #93 / #95 / #96 / #97 (tickets #87 design / #88 schema + wizard input / #89 dual-arm runner + control-arm prompt / #90 paired-lift formula + CI / #91 result-page lift card + arm-split table / #92 e2e calibration dogfood). Wizard A/B toggle is live end-to-end as of 2026-05-27. Calibration writeup in `docs/4.6-ab-experiment-mode.md` § "#92 e2e dogfood calibration": 3/3 cleanly-predicted hypotheses directionally confirmed; one PM-prediction override (autoplay-next-episode) correctly caught the well-known autoplay-is-divisive dynamic. Followups carved out as separate tickets: arm-scoped persona-group chat (route currently disabled in A/B mode), de-asymmetric per-arm result-page scoring (control arm skips weakness classifier so side-by-side display is misleading), delete the `AB_MODE_DISABLED_UNTIL_LIFT` plumbing after soak.

Part (b) of the original proposal (accept real A/B test data as input to the same Analysis tab) was rejected outright: no PM has asked for it, the analyzer market is crowded (Eppo, GrowthBook, Statsig), and it dilutes the agent-simulation moat. If we ever build (b), the natural home is **Phase 9 Layer-3 calibration** — "what we predicted vs what actually happened" using real A/B data as the ground-truth tuning signal, not as a standalone analyzer.

**Historic design context (locked 2026-05-26):** docs at `docs/4.6-ab-experiment-mode.md`, session at `sessions/phase-4.6-ab-experiment-mode/`. Three CEO-level decisions: (1) control-arm artifact reuses `Capability.reverse_prd` (drop proposed-change section in composer); (2) paired sampling (same `identity_seed` in both arms); (3) wizard cost preview + 200-per-arm cap + confirm-if-large (pricing deferred to Phase 7). Score-formula decision (#90) routed through `/plan-eng-review` before #90 code started.

---

## Links

- [GitHub Project](https://github.com/users/ram-de/projects/) — open tickets (canonical)
- [System architecture](docs/system-architecture.md)
- [Feature Pack Crawler spec](docs/feature-pack-crawler-spec.md)
- [MiroFish prior-art](docs/mirofish-prior-art.md)
- [CONTEXT.md](CONTEXT.md) — current sprint narrative
- [AGENTS.md](AGENTS.md) — how the team works with AI agents
