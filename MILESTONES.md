# pythia-simulator — Milestones

**Last updated:** 2026-05-20

## Phase tracker

| Phase | Status | Completion |
|---|---|---|
| **0. Design** | ✅ Done | 2026-05-20 |
| **1. Scaffold** | ✅ Done | 2026-05-20 |
| **2. Persona + Feature Pack loaders + Postgres metadata** | 🔲 Pending | — |
| **3. Simulation runner (real LLM fan-out) + scoring** | 🔲 Pending | — |
| **4. Agent chat API wired + frontend chat UI** | 🔲 Pending | — |
| **5. Auth (Clerk) + multi-tenancy** | 🔲 Pending | — |
| **6. Observability (Sentry + Langfuse)** | 🔲 Pending | — |
| **7. First customer (Lumen MVP)** | 🔲 Pending | — |

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

## Next up (Phase 2 — Persona + Feature Pack loaders + Postgres metadata)

1. `adapters/persona_loader.py` — read latest Persona Pack from R2 (`customers/<id>/personas/latest/persona_pack.json`)
2. `adapters/feature_pack_loader.py` — same for latest Feature Pack manifest + per-capability artifacts
3. `adapters/postgres.py` — async SQLAlchemy session; `AgentInstanceMetadata` and `Simulation` tables
4. Alembic migrations bootstrapped
5. API routes wired: `GET /capabilities`, `POST /simulations`, `GET /simulations/{id}`, `GET /agents/{id}`, `POST /agents/{id}/messages`

## Open questions

| Item | Notes |
|---|---|
| Where to host Postgres in dev | Neon free tier; local Docker fallback for offline dev |
| Streaming PM ↔ agent chat | MVP: simple POST → response. Phase 2: SSE for token-streaming UX |
| LLM concurrency limits | Groq has tight per-key rate limits; need a token-bucket or queue at N >~ 10 |
| Agent listing & search UX | Phase 4 — index by persona name, last_active_at, weakness category |
| "Realistic / not realistic" flags | UI element on each agent turn; signal stored in Postgres for Layer-3 training data |

## Related artifacts

- Persona-pack producer: [`pythia-personas`](https://github.com/ram-de/pythia-personas)
- Feature-pack producer: [`pythia-crawler`](https://github.com/ram-de/pythia-crawler)
- Personal wiki project page: `~/vaults/personal/wiki/projects/pythia.md`
- Active working notes: `~/vaults/personal/sessions/persona-classifier/context.md`
