# pythia-simulator — Milestones

**Last updated:** 2026-05-20

## Phase tracker

| Phase | Status | Completion |
|---|---|---|
| **0. Design** | ✅ Done | 2026-05-20 |
| **1. Scaffold** | ✅ Done | 2026-05-20 |
| **2. Persona + Feature Pack loaders + Postgres metadata** | 🔲 Pending | ~1 week |
| **3. Simulation runner (real LLM fan-out) + scoring + refinement** | 🔲 Pending | ~2 weeks |
| **4. Agent chat API wired + frontend chat UI** | 🔲 Pending | ~2 weeks |
| **4.5. Persona Builder UI (Snowflake → pack)** | 🔲 Pending | ~2 weeks |
| **5. Auth (Clerk) + multi-tenancy** | 🔲 Pending | ~1.5 weeks |
| **6. Observability (Sentry + Langfuse)** | 🔲 Pending | ~1 week |
| **7. First customer (Lumen MVP)** | 🔲 Pending | ~3 weeks |
| **8. Refinement loop UX (Karpathy AutoResearch)** | 🔲 Pending | ~2 weeks |
| **9. Layer-3 calibration (the moat)** | 🔲 Pending | ongoing, 6+ months first signal |
| **10. Specialized 8B model** | 🔲 Pending | 6–12 months after data threshold |

## Completed

### Phase 0 — Design (2026-05-20)
- Architecture finalized: 3-repo system (`pythia-personas` / `pythia-crawler` / `pythia-simulator`) with R2 as the artifact contract
- Backend stack: Python/FastAPI; producers import as packages (no IPC)
- Frontend: Next.js + TypeScript with types generated from FastAPI OpenAPI export
- Storage: R2 for artifacts (zero egress) + Postgres on Neon for metadata
- Auth: Clerk; multi-tenant via `customer_id` scope on every read/write
- Decided **not** to fork mirofish — wrong target audience, wrong input/output shape, wrong tenancy model
- **Agent memory** designed in: identity prompt + initial reaction (both frozen) + append-only conversation
- **Identity-continuity guarantee** explicitly defined: chat-time agent is the SAME entity that simulated, not a re-instantiation from the persona template

### Phase 1.5 — MiroFish prior-art adaptation (2026-05-20)

After scaffolding, surveyed mirofish for transferable patterns and adapted four into the codebase. Full record at `docs/mirofish-prior-art.md`.

- **`SimulationRunState` + JSONL event log** (`services/run_state.py`) — two-tier state model; live progress + audit trail + replay surface. Adapted from `simulation_runner.py:101-193` and `:482-554`.
- **Parallel agent execution** — `SimulationRunner.run()` uses `asyncio.gather` with a semaphore-bounded concurrency limit instead of a serial loop. Adapted from `oasis_profile_generator.py:851-1014` (ThreadPoolExecutor → asyncio-native equivalent).
- **`_CHAT_GUARD_PREFIX`** (`services/agent_chat.py`) — pinned as a system supplement on every chat call to prevent LLM drift while preserving identity continuity. Adapted from `simulation_runner.py:25` INTERVIEW_PROMPT_PREFIX.
- **JSON repair helper** (`adapters/llm.py:repair_json` + `parse_llm_json` + new `chat_json` method) — forgiving parser for structured LLM outputs. Adapted from `oasis_profile_generator.py:606-670`.

Explicitly rejected: inter-agent socialization, Zep graph memory, subprocess-based agent IPC, simulation config auto-gen, multi-platform abstractions, narrative report output, zh-CN localization. Rationale captured in `docs/mirofish-prior-art.md`.

Tests: 10 passing (4 new) — including JSON-repair round-trip, event-log append, and chat-guard sanity.

### Phase 1 — Scaffold (2026-05-20)

**Backend (`backend/`):**
- `pythia_simulator/main.py` — FastAPI app with `/health`, `/simulations`, `/agents`, `/capabilities`
- `pythia_simulator/schemas/` — Pydantic models for Persona, FeaturePack, Simulation, Agent (source-of-truth; TS types codegen from OpenAPI)
- `pythia_simulator/memory/agent_memory.py` — frozen identity + frozen initial reaction + appendable conversation log; enforces identity continuity
- `pythia_simulator/adapters/r2.py` — `LocalArtifactStore` + `R2ArtifactStore` (both working)
- `pythia_simulator/adapters/llm.py` — Groq primary + Anthropic fallback chat client
- `pythia_simulator/services/prompt_composer.py` — builds the FROZEN identity prompt at simulation time
- `pythia_simulator/services/simulation_runner.py` — orchestrates a simulation; materializes AgentInstances with frozen identity + reaction
- `pythia_simulator/services/agent_chat.py` — post-simulation PM ↔ agent chat using replay-from-frozen-state
- `pythia_simulator/jobs/runner.py` — `InProcessJobRunner` for MVP (swap to Cloud Tasks / SQS later)
- `pythia_simulator/cli.py` — `pythia-simulator serve` for local dev
- Tests: 5 smoke tests passing; includes explicit identity-continuity assertion

**Frontend (`frontend/`):**
- Next.js 14 + TypeScript skeleton
- Routes: `/`, `/simulations/new`, `/simulations/[id]`, `/agents/[id]`
- `lib/api.ts` typed fetch helpers; OpenAPI codegen wired via `npm run gen-types`

**Docs:**
- `docs/system-architecture.md` — mirror of personal wiki spec
- `docs/feature-pack-crawler-spec.md` — for cross-reference

---

## Future phases — detailed spec

Each phase has: **goal** (one sentence), **tasks**, **acceptance criteria** (what "done" looks like), **dependencies**, **risks**. Update statuses as work lands.

---

### Phase 2 — Persona + Feature Pack loaders + Postgres metadata

**Goal:** Replace stub responses with real reads from R2 (artifacts) and Postgres (metadata) so the API can return live data, even if simulation scoring is still stubbed.

**Tasks:**
- `adapters/persona_loader.py` — read latest Persona Pack from `customers/<id>/personas/latest/persona_pack.json`; cache per-request
- `adapters/feature_pack_loader.py` — read latest Feature Pack manifest + per-capability artifacts (reverse-PRD + reverse-Figma); resolve "latest" via a pointer file or list-and-sort
- `adapters/postgres.py` — async SQLAlchemy + asyncpg session factory; connection pool
- Postgres schema (Alembic migration 001):
  - `customers` (id, clerk_org_id, name, created_at) — placeholder until Phase 5 wires Clerk
  - `simulations` (id, customer_id, status, persona_pack_version, feature_pack_version, hypothesis_json, result_json, created_at, completed_at)
  - `agent_instances` (id, customer_id, simulation_id, persona_id, persona_pack_version, persona_name, created_at, last_active_at, message_count)
  - `agent_feedback` (agent_id, turn_index, realistic_flag, created_at) — Layer-3 calibration signal
- Repository pattern: one repo class per table, all queries scoped by `customer_id` via SQLAlchemy session-level filter (foundation for Phase 5 multi-tenancy)
- Wire `GET /capabilities` → reads latest Feature Pack manifest for customer
- Wire `GET /simulations/{id}` → joins Postgres row + R2 result.json
- Wire `GET /agents/{id}` → AgentMemory.load() via stored metadata row
- Integration test rig: local Postgres via Docker Compose; seed scripts populate sample data from `samples/`

**Acceptance:**
- `POST /simulations` accepts a request, persists a row in `simulations` with status=PENDING, returns 202 + simulation_id
- `GET /simulations/{id}` returns the full simulation including agent_instance_ids
- `GET /agents/{id}` returns the agent's identity + initial reaction + (empty) conversation
- All routes respect `customer_id` scoping (even if customer_id is hardcoded until Phase 5)
- Integration tests pass against the local Postgres rig

**Dependencies:** Phase 1 ✅

**Risks:**
- **R2 "latest" pointer ambiguity** — producers must write a `latest/` symlink or a manifest-of-manifests so the simulator doesn't list-and-sort on every request
- **Schema drift** — every artifact will need a `schema_version` field; backend must tolerate one minor version back
- **Local dev parity** — local Postgres + LocalArtifactStore needs to match prod R2 + Neon behavior closely enough that "works locally" predicts prod

**Estimated effort:** ~1 week

---

### Phase 3 — Simulation runner (real LLM fan-out) + scoring + refinement

**Goal:** A submitted hypothesis runs end-to-end against real LLM calls, returns a meaningful confidence score with diagnosed weaknesses, and proposes refinements when score is below threshold.

**Tasks:**
- Wire `SimulationRunner.run()` into the `POST /simulations` route (background task via `InProcessJobRunner`)
- **Scoring algorithm v1:**
  - Per-agent: second LLM call classifies the reaction against the 6 weakness categories (`wrong_metric`, `wrong_cohort`, `broken_mechanism`, `untestable_hypothesis`, `hidden_guardrail_risk`, `underpowered_design`) → returns JSON via `chat_json()` (uses the repair helper)
  - Per-agent: sentiment classification (positive / neutral / negative reception toward the proposed change)
  - Aggregate: confidence score = weighted blend of (% positive reactions) + (1 − weakness concentration) on a 0–100 scale
  - Aggregate: top 3 weaknesses by frequency, with supporting agent_ids
- **Refinement agent (Karpathy AutoResearch pattern):**
  - Given hypothesis + top weaknesses + N agent reactions, suggest 1–3 hypothesis refinements
  - Pure-text agent — no multi-agent debate; single specialized prompt
  - Persisted as `result.refinement_suggestions`
- **Iteration loop:**
  - PM-driven: PM accepts a refinement → submits a new simulation linked to the previous one (`parent_simulation_id`)
  - Track plateau detection: if 3 successive simulations move the score by <5 points, return EXIT 2 (Invalid)
  - If a simulation hits ≥80, return EXIT 1 (Validated) + experiment spec export
- **Live progress endpoint:**
  - `GET /simulations/{id}/state` returns the latest `SimulationRunState` (cheap poll; SSE upgrade in Phase 4)
- End-to-end integration test: real Groq call against `samples/example_acme_2026-W21/` Feature Pack and a fixture Persona Pack

**Acceptance:**
- PM submits a hypothesis via curl → receives a simulation_id → polls /state every 2s and sees agents progressing → final result has a meaningful 0–100 score, top weaknesses, and 1–3 refinements
- Total simulation time (10 personas, parallel) under 30 seconds against Groq
- Score reproducibility: same hypothesis + same packs + same seed → score within ±3 points across runs (LLM variance is real)
- One end-to-end integration test runs in CI against a mock LLM that returns canned reactions

**Dependencies:** Phase 2

**Risks:**
- **Scoring calibration** — initial weights between sentiment and weakness-concentration will be guesses; need real PM feedback to tune
- **LLM rate limits** — Groq free tier may not handle parallel-10. Anthropic fallback adds latency. Token-bucket throttle at the chat client layer.
- **Refinement quality** — refinement agent could hallucinate non-actionable suggestions. Add a critic-style validation pass before returning.
- **Cost forecast** — 10 personas × 3 LLM calls (reaction + weakness + sentiment) per simulation = 30 calls/simulation. At Groq rates that's negligible; on Anthropic it's $0.10–$0.30 per simulation.

**Estimated effort:** ~2 weeks

---

### Phase 4 — Agent chat wired + frontend chat UI

**Goal:** PMs interrogate the agents that participated. The defining differentiator from every other experimentation tool.

**Tasks:**
- Wire `AgentChatService.send_message()` into `POST /agents/{id}/messages`
- Update `agent_instances.last_active_at` + `message_count` in Postgres on each turn
- `POST /agents/{id}/messages/{turn_index}/feedback` — PM submits realistic/not-realistic flag → writes to `agent_feedback` table
- **Streaming responses:**
  - SSE endpoint `POST /agents/{id}/messages/stream` returns token-by-token
  - Backend uses LLM streaming APIs for both Groq and Anthropic
  - Persist on completion (only after the full response is received)
- **Frontend (Next.js + TypeScript):**
  - Simulation detail page: confidence score card, weakness summary, agent list (table: persona name, sentiment, weakness category, last_active)
  - Agent chat page: identity card pinned at top (persona name + behavioral snapshot), initial reaction pinned below identity, chat bubbles for follow-up turns, message input
  - Realistic / not-realistic thumbs on every agent message
  - Conversation persists across page reloads (loaded from `GET /agents/{id}`)
  - "What changed since last time?" — surfaces new turns since last visit
  - Soft empty states: "No reactions yet — try asking…" suggestions
- Run OpenAPI codegen in CI to keep TS types fresh

**Acceptance:**
- PM completes a simulation, clicks an agent, sees that agent's identity + initial reaction
- PM types a question, watches the response stream in token-by-token
- Refresh the page → conversation history is intact
- Click thumbs-down on a response → flag persists; visible on next load
- Same agent maintains coherent voice across 20+ turn conversations (manual QA)

**Dependencies:** Phase 3

**Risks:**
- **SSE reliability** — connection drops mid-stream. Backend must persist the partial response on disconnect; frontend must handle reconnect gracefully.
- **Long-conversation token budget** — at 30+ turns, replay history approaches LLM context limits. Phase 4 adds soft warnings; Phase 8 adds summarization compression.
- **Mobile UX** — enterprise PMs increasingly review from phones. Chat UI must work below 640px.

**Estimated effort:** ~2 weeks

---

### Phase 2+3 — Magic Moment Sprint (in flight)

**Goal:** end-to-end simulation against fixture data — submit hypothesis → 10 agents react → confidence score + weaknesses + refinements rendered.

**Locked-in decisions** (post-`/plan-eng-review`, 2026-05-21):

| Decision | Choice | Rationale |
|---|---|---|
| Reproducibility | `temperature=0` + fixed `seed` + cache `(identity_prompt_hash, persona_id) → reaction` | Eliminates score swing across reruns. ~50 lines. |
| Score formula | `0.6 × sentiment_score + 0.4 × (1 − weakness_concentration)` | Captures "will users like this?" first; weaknesses are the diagnostic. Tunable. |
| Per-agent timeout | `asyncio.wait_for(60s)` + emit `agent.reaction.failed` events; render N-of-M on the frontend | Robust to a hung LLM call. No whole-run aborts. |
| Postgres scope | Full migration 001: `simulations` + `agent_instances` + `agent_feedback` | Phase 5 unblocked, Layer-3 hook in place from day 1. |
| Fixture pack path | `local-artifacts/customers/demo/personas/v_1/persona_pack.json` | Matches prod R2 layout; `persona_loader.load_latest("demo")` works unchanged. |
| Request pattern | `POST /simulations` returns 202 + `simulation_id`; background task runs the work | 30s LLM-bound work would blow HTTP timeouts. |
| Refinement | Separate LLM call after scoring | Independent service, independently swappable. |
| Live progress | 5s poll on `/simulations/{id}/state` | Simple MVP; SSE in Phase 4. |

**NOT in scope** (deferred, explicit):
- Clerk auth / multi-tenancy (`customer_id="demo"` hardcoded) — Phase 5
- Persona Builder UI completion (the 7-step wizard stays as stubs) — Phase 4.5 finishing
- Chat UI for agent follow-up — Phase 4
- Crawler runs (we use the existing Acme sample) — crawler Phase 2
- SOC 2 prep / encryption / audit logs — Phase 6+
- Real customer data ingestion — first customer phase

**What already exists** (do not rebuild):
- `SimulationRunner.run()` skeleton with identity-continuity + parallel `asyncio.gather` + semaphore
- `SimulationRunState` + `RunStateStore` (JSONL event log, state.json)
- `AgentMemory` with frozen identity + initial reaction
- `chat_json()` + `repair_json()` for structured LLM output
- `_CHAT_GUARD_PREFIX` (reusable in refinement agent if needed)
- Sample Feature Pack at `pythia-crawler/samples/example_acme_2026-W21/`
- API route shells for `/simulations`, `/agents`, `/capabilities`
- Frontend route shells for `/simulations/new`, `/simulations/[id]`, `/agents/[id]`

**Critical test gaps to land alongside code** (from the test review):
- **TEST-1** Integration: `tests/integration/test_simulation_e2e.py` — mock LLM with canned reactions, assert result shape + score in range
- **TEST-2** Unit: `tests/unit/test_scoring.py` — `aggregate()` over hand-built reactions covering each weakness category
- **TEST-3** Eval: 10 (hypothesis, expected-score-band) pairs as regression guard
- **TEST-4** Unit: `persona_loader` handles missing pointer + schema_version mismatch

### Parallelization plan (lanes)

```
Wave 1  [Lane A — parallel, independent files]
  ├── T1  Postgres schema + Alembic 001 (3 tables)
  ├── T4  adapters/feature_pack_loader.py
  └── T5  fixture persona_pack_demo.json  ← write last; validates against schema

Wave 2  [Lane B — parallel, independent]
  ├── T2  adapters/postgres.py + repositories
  └── T3  adapters/persona_loader.py

Wave 3  [Lane C — sequential, integration]
  └── T6  Wire POST /simulations + 202+poll + background asyncio task
          + timeout + N-of-M failure handling

Wave 4  [Lane D — sequential, intelligence]
  ├── T7a services/scoring.py: weakness classification (chat_json)
  ├── T7b services/scoring.py: sentiment classification (chat_json)
  ├── T7c services/scoring.py: aggregate() with 0.6/0.4 blend
  ├── T7t TEST-1 + TEST-2 + TEST-3
  ├── /codex consult on the aggregation formula  ← cross-model second opinion
  └── T8  services/refinement.py (independent LLM call)

Wave 5  [Lane E — PARALLEL via 2 sub-agents, different page files]
  ├── Agent α: /simulations/new form (capability dropdown + hypothesis textarea)
  └── Agent β: /simulations/[id] result view + 5s state polling

Wave 6  [Lane F — sequential, validation]
  ├── T12 End-to-end manual demo
  ├── /qa against running :3000 / :8000
  ├── /review the full diff
  └── /retro
```

**Conflict flags:** Lane A's T1 (Postgres) and Lane B's T2 (postgres adapter) touch related code but different files; no merge conflict expected. Lane E sub-agents touch **different page files** — fully independent.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | not run (no significant product change in this sprint) |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR | 6 architecture findings → 4 critical decisions locked; 4 test gaps → land alongside code |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | not run (Wave 5 frontend is stubs-to-real, no new visual design) |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | n/a (internal sprint) |
| Outside Voice | `/codex` | Independent challenge | 0 | — | deferred to Wave 4 for the scoring formula specifically |

- **UNRESOLVED:** 0
- **VERDICT:** ENG CLEARED — ready to implement.



**Goal:** A customer connects their Snowflake, maps columns to Pythia's 7 feature groups (LLM-assisted), previews their population, configures the build, runs it, reviews the resulting personas, and promotes the pack to `latest` — all from a self-serve wizard. Equivalent for `pythia-crawler` and `pythia-simulator` UIs land in their own phases; this one is the proof of concept.

**Tasks:**

*Backend (`backend/`):*
- `adapters/feature_stores/__init__.py` — `FeatureStore` Protocol (test_connection, list_schemas, list_tables, run_query, sample)
- `adapters/feature_stores/snowflake.py` — Snowflake-specific implementation (snowflake-connector-python)
- `adapters/credentials.py` — encrypt/decrypt customer creds with a KMS-managed per-customer key; envelope encryption pattern
- `services/persona_builder.py` — orchestrator: load creds → query Snowflake → call `pythia_personas` library → emit pack to R2 + Postgres metadata
- `services/column_mapper.py` — LLM call that reads column names + sample values, suggests group assignments for the 7 feature groups
- `services/job_run.py` — generalize `SimulationRunState` to a `JobRun` abstraction shared by simulations + persona builds + (future) crawls
- API routes:
  - `POST /feature-stores` — create a saved connection
  - `GET /feature-stores` — list connections for customer
  - `POST /feature-stores/{id}/test` — round-trip connectivity check
  - `POST /feature-stores/{id}/preview` — run a query, return row count + column profile (NULL coverage, distribution skews)
  - `POST /feature-stores/{id}/suggest-mapping` — LLM column-to-group suggestions
  - `POST /persona-builds` — kick off a build (returns build_id; status streams via `/jobs/{id}/state`)
  - `GET /persona-builds/{id}` — fetch build status + result
  - `GET /persona-packs` — list packs (all versions, drafts + promoted, with stability scores)
  - `POST /persona-packs/{id}/promote` — atomically update `customers/<id>/personas/latest` pointer
- Postgres tables (Alembic migration 002):
  - `feature_store_connections` (id, customer_id, name, kind, encrypted_creds, created_at)
  - `persona_build_runs` (id, customer_id, connection_id, status, config_json, result_pack_version, created_at, completed_at)
  - `persona_pack_versions` (id, customer_id, version, status [DRAFT|PROMOTED|RETIRED], stability_score, created_at, promoted_at)

*Frontend (`frontend/`):*
- Top-level navigation: 3 tabs (Personas / Product / Simulations). Shared layout.
- `/personas/` — pack list view (current `latest` highlighted, all past versions browsable)
- `/personas/new/` — the 7-step wizard:
  - Step 1 — Connect Snowflake
  - Step 2 — Pick source (table picker OR SQL textarea)
  - Step 3 — Map columns to 7 groups (LLM suggestions pre-filled)
  - Step 4 — Population preview (row count, NULL coverage, distribution skews)
  - Step 5 — Configure (k or auto, stability threshold, LLM provider, weight schemes)
  - Step 6 — Live build progress (streams `JobRun` events)
  - Step 7 — Review + promote
- `/personas/[id]/` — pack detail (personas with names, descriptions, JTBD, behavioral snapshots, stability score, "Promote to latest" CTA)
- `/product/` placeholder (Phase TBD)
- `/simulations/` — existing pages move under this path

**Acceptance:**
- A customer connects their Snowflake from the UI, walks the 7-step wizard, and lands a draft pack in under 15 minutes
- The pack appears in `/personas/` and can be promoted to `latest`
- After promotion, a simulation submitted via `/simulations/new` uses the new pack
- Snowflake credentials are never visible in API responses, never in logs, never in plaintext after the initial connect call
- The wizard can be paused and resumed (in-progress builds persist; user can come back to Step 5 later)
- LLM mapping suggestions correctly classify ≥70% of columns on a realistic schema (manual QA against the DoorDash 146-col table)

**Dependencies:** Phases 2 + 4 (needs Postgres + multi-tenant scoping; needs the chat-UI shared navigation work; Phase 5 Clerk integration locks in security boundary).

**Risks:**
- **Snowflake connectivity from Fly.io** — customer firewalls may not allow our IPs. Document the egress IP allowlist requirement up front.
- **Long-running builds blocking the API** — must run on a worker (not the API process). `InProcessJobRunner` MVP works for ≤30-min builds; bigger packs require Phase 2 of `JobRunner` (Cloud Tasks / SQS).
- **LLM mapping wrong on edge schemas** — column-name heuristics fail on poorly-named tables. Mitigate with sample-value inspection and "I don't know — please assign manually" as an acceptable suggestion.
- **Credential key rotation** — KMS key rotation can break decryption of historical creds. Re-encrypt-on-rotation policy documented.

**Estimated effort:** ~2 weeks



**Goal:** Multiple customers can use the same backend without seeing each other's data. SAML/SSO ready for enterprise sales.

**Tasks:**
- Clerk integration in backend:
  - JWT verification middleware on every protected route
  - Extract `customer_id` (mapped from Clerk `org_id`) → attach to request context
  - 401 on missing/invalid JWT; 403 on customer_id mismatch with resource owner
- Clerk integration in frontend:
  - Sign-in / sign-up / forgot-password flows
  - Organization switcher (a PM may belong to multiple customers)
  - Session refresh handled by Clerk SDK
- Customer model wired:
  - Postgres `customers.clerk_org_id` populated on first request from a new org
  - First-user-of-org becomes the default admin
- **Tenancy enforcement audit:**
  - SQLAlchemy session-level filter rejects any query missing `customer_id`
  - R2 paths always prefixed with `customers/<customer_id>/` — assertions in adapter layer
  - Cross-tenant access test: customer A's PM cannot fetch customer B's simulation_id
- Admin endpoints: `POST /admin/customers/{id}/refresh` to trigger persona + crawler runs (gated to platform admins)
- SAML/SSO documentation for enterprise customers

**Acceptance:**
- Two customers register, each sees only their own simulations
- A PM hitting another customer's simulation_id by URL gets 403
- The R2 adapter's path-assertion middleware refuses writes to a path that doesn't match the request's customer_id
- SAML/SSO sign-in tested with one mock IdP
- Penetration test: a malicious JWT (forged customer_id) is rejected at the middleware

**Dependencies:** Phase 4

**Risks:**
- **R2 path-scoping bugs** — any code path that constructs an R2 key by hand instead of through a helper is a tenancy leak. Add a lint rule.
- **Clerk org model mismatch** — some enterprise customers want a single Clerk org with multiple "workspace" sub-units. Phase 5 supports flat orgs only; defer workspaces to Phase 7+ if requested.
- **Admin endpoint surface** — must not be exposed to customer JWTs. Use a separate Clerk role (`platform_admin`) and a different middleware stack.

**Estimated effort:** ~1.5 weeks

---

### Phase 6 — Observability

**Goal:** When something breaks in prod, we know within minutes; when an LLM bill spikes, we know which customer drove it.

**Tasks:**
- **Sentry:**
  - Backend Python SDK with FastAPI integration; attach customer_id + simulation_id to every event
  - Frontend Next.js SDK with source maps
  - Performance traces enabled (sample rate 10%)
- **Langfuse:**
  - Wrap Groq + Anthropic clients with `@observe()` decorators
  - Capture: prompt, response, model, latency, token usage, cost-estimate
  - Tag every trace with `customer_id`, `simulation_id`, `agent_id` (when applicable)
  - Dashboard: cost-per-customer-per-day; latency p50/p95 per phase
- **Structured logging:**
  - `structlog` configured to emit JSON to stdout
  - Request context middleware attaches customer_id + request_id to every log line
  - Ship to Fly.io aggregation; defer Datadog/BetterStack until scale demands
- **Healthchecks:**
  - `GET /health` extended: DB connectivity, R2 connectivity, LLM key validity
  - External uptime monitor (BetterUptime) probing /health every 1m
- **Admin dashboard (in-app):**
  - Cost per customer per day; flag any customer exceeding $X/day
  - Failed simulations and agent reactions with error breakdown
  - Crawl freshness per customer (when did the last Feature Pack land?)
  - Persona pack freshness per customer

**Acceptance:**
- A live Sentry trace surfaces a real exception within 30 seconds of it firing
- Langfuse dashboard shows top customers by LLM cost yesterday
- Admin dashboard alerts when a customer hits >$50 LLM spend in a day
- BetterUptime page exists; backend downtime triggers a page (off-hours) or email (business hours)

**Dependencies:** Phase 5

**Risks:**
- **Logging cardinality** — too many tags per log line balloons storage. Cap context fields.
- **Langfuse cost-estimate accuracy** — depends on per-model pricing being current; build a small price table updated quarterly.
- **PII in logs** — agent reactions may reference real customer data. Redact `pm_message` content from logs (keep token counts, not text).

**Estimated effort:** ~1 week

---

### Phase 7 — First customer (Lumen MVP)

**Goal:** One enterprise design partner runs real simulations on their own data, end-to-end, in production.

**Tasks:**
- **Customer onboarding playbook:**
  - Sales / discovery → contract → kickoff doc → sandbox creds exchange → first crawl → first persona pack → first simulation
  - Time-to-first-simulation target: ≤14 calendar days from contract sign
- **Production deployment:**
  - Vercel frontend with custom domain (`app.pythia.<your-brand>.com`)
  - Fly.io backend with autoscaling
  - Neon production Postgres in customer-preferred region
  - Cloudflare R2 bucket with per-customer prefix encryption
  - Clerk production tenant + SAML config for the design partner
- **SOC 2 prep:**
  - Bucket-level encryption-at-rest enabled
  - DB-level encryption-at-rest enabled
  - Audit log table: every read/write to `simulations` and `agent_instances` rows
  - Access controls: only platform admins can read any customer's data; PMs only their own
- **Pricing model decision:**
  - Per-simulation (~$X per run)
  - Per-seat (~$X per PM per month)
  - Annual contract (preferred for enterprise; locks revenue)
  - Decide before kickoff; reflect in Clerk billing webhooks (Stripe later)
- **Data Processing Addendum (DPA) signed**
- **Internal runbook:**
  - "Simulation stuck in RUNNING" → check Fly worker logs, check Groq rate limit, check R2 write
  - "Agent chat returning gibberish" → check identity_prompt frozen artifact, replay messages, escalate
  - "Crawler can't authenticate" → coordinate with customer's IT for fresh creds

**Acceptance:**
- Design partner has run ≥5 simulations on their real product
- ≥3 weakness categories surfaced in those simulations were validated as "real" by the partner's PMs in retro
- Partner's PMs are chatting with ≥10 agents per week
- Crawler runs weekly on their schedule, no manual intervention
- Quarterly persona refresh runs without incident
- Partner publicly references using Pythia (case study or quote)

**Dependencies:** Phases 2–6

**Risks:**
- **Sandbox parity** — partner's sandbox may lack feature flags or recent data; manage expectations up front
- **First-customer dependency** — feature requests will be tempting to fulfill; maintain product discipline, road-map every ask
- **Simulation accuracy not yet calibrated** — without Layer-3 calibration (Phase 9), accuracy will be ~70%; communicate this clearly so the partner doesn't expect 90%

**Estimated effort:** ~3 weeks (after Phase 6 lands)

---

### Phase 8 — Refinement loop UX (Karpathy AutoResearch pattern)

**Goal:** The full validation flow — submit → refine → re-simulate → exit at threshold or plateau — is one cohesive experience, not a series of disconnected runs.

**Tasks:**
- Frontend: simulation chain view (parent → child via `parent_simulation_id`)
- Frontend: "Accept refinement" CTA on each suggestion → pre-fills new simulation form with the refined hypothesis
- Backend: chain-aware scoring — if a simulation is part of a chain, surface the score trajectory in the chain view
- Backend: plateau detection — surface EXIT 2 (Invalid, Rethink Recommended) when scores plateau below 80 across 3+ iterations
- Backend: validated-hypothesis export — generate an experiment spec (primary metric, MDE estimate, recommended cohort, suggested duration) when a chain hits EXIT 1
- Statsig / Eppo / LaunchDarkly export adapters (one-click → "send this validated hypothesis to your experiment platform")
- Long-conversation memory compression for agents whose chat history exceeds context limits
- Worked example onboarding flow (the Late Night Munchers case from the project page)

**Acceptance:**
- A PM walks the 5-iteration Late Night Munchers example from 52 → 83 in under 30 minutes
- Validated hypothesis exports cleanly to a Statsig experiment template
- Plateau detection fires on a fixture chain where the score never crosses 75

**Dependencies:** Phase 7

**Risks:**
- **Iteration fatigue** — PMs may give up before plateau is reached; track abandonment per iteration count
- **Statsig API churn** — third-party experimentation platforms change schemas; design exports to be extensible

**Estimated effort:** ~2 weeks

---

### Phase 9 — Layer-3 calibration (the moat)

**Goal:** Per-customer simulation accuracy compounds with experiment history. After 100 simulations, accuracy is verifiably higher than at simulation 1. This is what makes Pythia defensible.

**Tasks:**
- **Outcome capture pipeline:**
  - Webhook from Statsig / Eppo / LaunchDarkly when an experiment completes → ingests actual lift
  - Match outcome back to the validated hypothesis chain
  - Compute accuracy metric: predicted lift sign vs actual lift sign; predicted MDE vs observed effect size
- **Calibration table:**
  - `customer_calibration` table per customer: weights on weakness categories, persona mix tuning, sentiment-to-score mapping
  - Updated on every completed outcome
- **Per-customer accuracy dashboard:**
  - "Pythia predicted this customer's outcomes correctly N% of the time over the last 6 months"
  - Trend line; per-PM accuracy
- **Realistic / not-realistic flag aggregation:**
  - All chat-time flags from Phase 4 feed a per-persona, per-customer "agent realism score"
  - Low-realism agents get re-clustered out of the persona pack on the next quarterly refresh
- **Model fine-tuning pipeline (prep for Phase 10):**
  - Curate "realistic" agent reactions + flagged outcomes into a training set
  - 10K+ examples per customer required before Phase 10 fine-tuning can fire

**Acceptance:**
- Layer-3 accuracy chart shows compounding improvement on at least one design partner after 50 simulations
- Realism flags drive measurable change in agent selection over time (visible in retros)
- Training set sized ≥5K examples for at least one customer

**Dependencies:** Phase 8 + ≥6 months of customer use

**Risks:**
- **Outcome capture latency** — experiments take 2–6 weeks to complete; calibration loop is slow by physics
- **Sparse signal** — most customers run <50 experiments per quarter; need multi-tenant pooling for early signal
- **Privacy** — pooled calibration risks leaking patterns across customers. Strictly per-customer until SOC 2 + customer consent for pooled training data.

**Estimated effort:** ~ ongoing; first measurable result in 6+ months

---

### Phase 10 — Specialized 8B model

**Goal:** Replace Groq/Anthropic in the inference path with a Pythia-owned 8B model trained on consumer behavior + per-customer outcome data. Cost drops 8–10×; inference moves on-device; the model becomes the moat.

**Tasks:**
- Pretraining corpus (Qwen3-8B base) — coordinated with `pythia-de-spec` (the data engineering spec already drafted)
- Supervised fine-tuning on persona reactions + curated Layer-3 examples
- RL on outcome accuracy (RLHF → Augur outcomes → Lumen outcomes)
- Deployment: vLLM serving on Fly.io GPU pods (or Modal / Replicate as bridge)
- A/B Pythia 8B vs Groq Llama-3.3 on the same prompts; require ≥parity before cutover
- Cutover plan: per-customer opt-in, monitor accuracy + cost for a quarter before defaulting

**Acceptance:**
- Pythia 8B beats Llama-3.3 70B in 80%+ of held-out evaluation cases (the M1 gate from the original Pythia roadmap)
- Inference cost per simulation drops by 8×+ on customers using the Pythia model
- One customer is running 100% on Pythia 8B in production for ≥30 days with no quality regression

**Dependencies:** Phases 7 + 9 + sufficient training data (≥10K outcomes across the customer base)

**Risks:**
- **Time-to-collect** — outcomes accrue at experimentation cadence (quarters, not weeks); can't compress
- **Model accuracy plateau** — 8B may not match frontier models on edge personas; keep frontier as fallback path indefinitely
- **GPU cost** — vLLM serving is cheaper at scale but expensive at low utilization; only cut over when load justifies it

**Estimated effort:** ~6–12 months once the data threshold is hit (per the original Pythia roadmap)

---

## Open questions (rolling)

| Item | Phase | Notes |
|---|---|---|
| Where to host Postgres in dev | 2 | Neon free tier; local Docker fallback for offline dev |
| Streaming PM ↔ agent chat | 4 | SSE upgrade path detailed in Phase 4 |
| LLM concurrency limits | 3 | Groq has tight per-key rate limits; semaphore at chat client layer |
| Agent listing & search UX | 4 | Index by persona name, last_active_at, weakness category |
| Realistic-flag UI placement | 4 | Per-turn thumbs vs end-of-conversation roll-up — needs PM user testing |
| Pricing model | 7 | Per-simulation vs per-seat vs annual — decision before first customer kickoff |
| Outcome capture authority | 9 | Webhook from experiment platforms vs PM-self-reported — both, with PM as ground truth tiebreaker |
| Pythia-8B inference host | 10 | Fly GPU vs Modal vs Replicate vs cloud-of-record AWS Bedrock

## Related artifacts

- Persona-pack producer: [`pythia-personas`](https://github.com/ram-de/pythia-personas)
- Feature-pack producer: [`pythia-crawler`](https://github.com/ram-de/pythia-crawler)
- Personal wiki project page: `~/vaults/personal/wiki/projects/pythia.md`
- Active working notes: `~/vaults/personal/sessions/persona-classifier/context.md`
