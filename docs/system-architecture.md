---
type: docs
domain: pythia
status: draft
date: 2026-05-20
---

# Pythia — System Architecture

**Version:** 1.0 (Draft)
**Scope:** Lumen MVP through Phase 2
**Status:** Architecture finalized, awaiting review

## Overview

Pythia is a pre-experiment hypothesis validation product. PMs submit a feature hypothesis (PRD + Figma) against a customer's userbase; behavioral simulation agents react as that userbase; Pythia returns a confidence score with diagnosed weaknesses and refinement suggestions. This document defines how the three subsystems compose into one customer-facing product.

## Core principle

> **The artifact store is the integration contract.**

Producers (persona pack, feature pack) write versioned artifacts to a shared object store. The simulator (consumer) reads those artifacts. The simulator never calls a service named "personas" or "crawler" at runtime — it just reads files at known paths. This is what lets three independent repos compose into one product without runtime coupling, service mesh, or API versioning between them.

---

## Subsystem map

```
┌─────────────────────────────────────────────────────────────┐
│                    pythia-simulator/                        │
│  (the only thing the customer sees)                         │
│                                                             │
│  ┌──────────────┐   ┌────────────────────┐                  │
│  │   frontend   │←→│   backend (API)    │                  │
│  │  Next.js     │   │   Python/FastAPI   │                  │
│  └──────────────┘   └─────────┬──────────┘                  │
│                               │                             │
│                     ┌─────────┴──────────┐                  │
│                     │     workers        │                  │
│                     │  (in-process for   │                  │
│                     │  MVP; queue later) │                  │
│                     └─────────┬──────────┘                  │
└───────────────────────────────┼─────────────────────────────┘
                                │ reads + writes
                                ▼
                ┌─────────────────────────────┐
                │   Artifact Store (R2)       │  ← system of record
                │   /customers/<id>/...       │     versioned, immutable
                │                             │     per-customer scoped
                └────────────────▲────────────┘
                                 │ writes
                  ┌──────────────┴────────────────┐
                  │                               │
        ┌─────────┴─────────┐         ┌───────────┴───────────┐
        │  pythia-personas  │         │   pythia-crawler      │
        │  Python package   │         │   Python + Playwright │
        │  + CLI/Docker     │         │   package + CLI/Docker│
        └───────────────────┘         └───────────────────────┘

         Metadata DB: Postgres on Neon (customer config, sim history)
         Auth: Clerk         Errors: Sentry        LLM traces: Langfuse
```

---

## Repository layout

| Repo | Role | Stack |
|---|---|---|
| **`pythia-personas`** (exists) | Produces Persona Pack from a customer's user table | Python, scikit-learn, Snowflake/Datalake connector |
| **`pythia-crawler`** (new) | Produces Feature Pack via weekly Playwright crawl | Python, Playwright, LLM (Anthropic/Groq) |
| **`pythia-simulator`** (new) | Customer-facing app: frontend + backend + workers | Next.js + Python/FastAPI |
| **`pythia-schemas`** (new) | Shared Pydantic schemas (Persona Pack, Feature Pack, Simulation Result) | Python only; TS types generated from OpenAPI export |
| Artifact store | Cloudflare R2 bucket | S3-compatible API, zero egress |

### `pythia-simulator/` internal layout

```
pythia-simulator/
├── frontend/                Next.js + TypeScript, deployed to Vercel
├── backend/                 FastAPI service, deployed to Fly.io
│   ├── api/                 HTTP routes
│   ├── services/            simulation runner, prompt composition, scoring
│   ├── jobs/                JobRunner interface (direct call MVP → queue later)
│   └── adapters/            R2 client, LLM clients, Clerk, Sentry
├── workers/                 long-running tasks (heavy crawler runs, large LLM fan-outs)
└── README.md
```

Frontend and backend live in one repo for MVP — same team, shared schemas, single deploy unit. Split if/when they grow independent teams.

---

## Producer pattern: library first, service second

Each producer ships **two faces** from the same codebase:

1. **Installable Python package** (`pip install pythia-crawler`) — backend workers import and call: `from pythia_crawler import run_crawl; run_crawl(customer_id=..., snapshot=...)`. No HTTP between simulator and producers.
2. **Standalone CLI / Docker image** — for cron jobs, local dev, debugging. `pythia-crawler run --customer acme --snapshot 2026-W21`.

Both invocation paths converge on the same artifact contract: write versioned outputs to R2 at the canonical path. The simulator backend doesn't care which path produced the artifact.

---

## Artifact store: layout & contract

```
r2://pythia-artifacts/
└── customers/
    └── <customer_id>/
        ├── personas/
        │   ├── v_5/
        │   │   ├── manifest.json          # version, generated_at, persona_count
        │   │   ├── persona_pack.json      # full pack
        │   │   └── prompts/<persona>.md   # compiled prompts per persona
        │   └── v_6/...
        ├── featurepacks/
        │   ├── 2026-W21/
        │   │   ├── manifest.json
        │   │   ├── capabilities/
        │   │   │   ├── reorder/
        │   │   │   │   ├── reverse-prd.md
        │   │   │   │   └── reverse-figma.json
        │   │   │   └── checkout/...
        │   │   └── diff-vs-prior.json
        │   └── 2026-W22/...
        └── simulations/
            └── <simulation_id>/
                ├── inputs.json            # references personas v_N + featurepack version + hypothesis
                ├── agent_reactions.jsonl  # one line per agent run
                └── result.json            # score, weaknesses, refinement suggestions
```

**All artifacts are immutable once written.** Reproducibility: every simulation captures its input versions and can be re-run with the same packs forever.

---

## Data flow: a PM running a simulation

```
1. PM opens simulator → Clerk authenticates → frontend gets a session
2. Frontend asks backend: GET /capabilities
3. Backend reads customer's latest featurepack manifest from R2
   → returns list of capabilities (Reorder, Checkout, DashPass Signup, ...)
4. PM picks "Reorder" + pastes hypothesis prose + uploads proposed Figma
5. Frontend: POST /simulations  { capability, hypothesis, proposed_figma }
6. Backend service:
   a. Loads /customers/acme/personas/latest/persona_pack.json
   b. Loads /customers/acme/featurepacks/latest/capabilities/reorder/
   c. Composes prompts: persona system prompt + reverse-PRD + reverse-figma
      + proposed PRD/figma + hypothesis
   d. Fans out N agent simulations (one per persona) via LLM
   e. Aggregates reactions → confidence score + weakness diagnosis
   f. Writes result to R2 at simulations/<id>/
   g. Returns result_id to frontend
7. Frontend polls or streams progress; renders score, weaknesses, suggested
   refinements
8. PM iterates (refines hypothesis → re-submits) → loop terminates at
   score ≥ 80 (validated) or plateau below threshold (invalid)
```

The simulator backend is the only component that knows the **runtime composition**. Producers don't know about simulations. The frontend doesn't know about producers.

---

## Producer trigger model

| Event | Who triggers | Mechanism |
|---|---|---|
| New customer onboarding | Backend admin endpoint | Backend calls `pythia_personas.run(...)` + `pythia_crawler.run(...)` inline (MVP) or via queue (Phase 2) |
| Weekly feature pack refresh | Scheduled cron in producer | Producer runs standalone (no backend involvement) and writes to R2; backend picks up next read |
| PM hits "Refresh feature pack" in UI | Backend on user action | Backend submits job → worker invokes crawler library → emits artifact → backend gets job-complete notification (poll or webhook) |
| Quarterly persona recalibration | Scheduled cron in producer | Same as weekly — producer is autonomous |

For MVP, "submit job" is `asyncio.create_task` in the backend worker pool. Phase 2 replaces it with Cloud Tasks / SQS without changing the `JobRunner` interface seen by callers.

---

## Schema contracts (`pythia-schemas`)

Pydantic v2 models are the source of truth. Three canonical schemas:

```python
# pythia_schemas/persona_pack.py
class PersonaPack(BaseModel):
    version: str
    customer_id: str
    generated_at: datetime
    personas: list[Persona]
    weights: WeightSchemes  # head-count, order-weighted, revenue-weighted
    assignment_classifier: ClassifierArtifact
    stability_score: float

# pythia_schemas/feature_pack.py
class FeaturePack(BaseModel):
    version: str               # e.g. "2026-W21"
    customer_id: str
    generated_at: datetime
    capabilities: list[Capability]

class Capability(BaseModel):
    name: str
    surfaces: list[Surface]
    roles: list[Role]
    reverse_prd: str           # markdown
    reverse_figma: FigmaSpec   # structured

# pythia_schemas/simulation.py
class SimulationRequest(BaseModel):
    capability_name: str
    hypothesis: str
    proposed_prd: str | None
    proposed_figma: FigmaSpec | None

class SimulationResult(BaseModel):
    id: str
    persona_pack_version: str
    feature_pack_version: str
    confidence_score: float
    weaknesses: list[Weakness]
    refinement_suggestions: list[str]
```

**TypeScript types** are generated from FastAPI's OpenAPI export via `openapi-typescript` in the frontend build step. Single source of truth, two languages, no drift.

---

## Agent memory & post-simulation conversation

After a simulation completes, every agent that participated remains **conversable indefinitely**. PMs can click any agent in the UI and ask follow-up questions to understand *why* the agent reacted the way it did — like talking to the users who participated in an A/B test.

### Identity model

| Concept | Definition | Lifetime |
|---|---|---|
| **Persona** | Template from the Persona Pack | Stable per Persona Pack version |
| **AgentInstance** | A persona instantiated for a specific simulation run, with its own memory | Lives until customer purges |
| **Conversation** | Append-only chat thread with one AgentInstance | Tied to AgentInstance |

One simulation produces N AgentInstances (one per persona slot). Each is independently chat-able after the simulation finishes.

### Memory layers per AgentInstance

| Layer | Content | Mutability |
|---|---|---|
| Identity prompt | Persona description + Feature Pack slice + hypothesis context | Frozen at simulation time |
| Initial reaction | The agent's reply during the simulation | Frozen |
| Conversation log | Append-only (PM_message, agent_response) pairs | Appendable forever |

### MVP memory strategy

**Full transcript replay.** On every new PM message, the backend prepends identity + initial reaction + all prior turns into the LLM call. At ~10–30 turns per agent, token cost is manageable. Add summarization-based compression in Phase 2 when long-tail conversations exceed context windows.

### Identity-continuity guarantee

The agent a PM chats with after a simulation is **the same agent that participated** — not a freshly-instantiated twin built from the persona template. This distinguishes Pythia from mirofish-style engines where the chat-time agent is re-spun from a persona description and loses the simulation-time reasoning.

Enforced by two invariants:

1. **`identity.md` is written once at simulation time and is never recomputed.** It captures the persona description, the Feature Pack slice that was current, and the hypothesis context — exactly as they existed when the agent reacted.
2. **`initial_reaction.md` is replayed as the first assistant message on every subsequent chat call.** The LLM continues from the exact conversational state the agent produced during the simulation.

Chat never re-runs the prompt-composer. It loads these frozen artifacts and appends. PMs are therefore interrogating the same individual entity that reacted — not a new persona-of-the-same-name.

### Storage split

- **Postgres** — agent metadata (id, simulation_id, persona_id, persona_pack_version, created_at, last_active_at, message_count)
- **R2** — large blobs at `customers/<id>/simulations/<sim_id>/agents/<agent_id>/`:
  - `identity.md` — full system prompt (frozen)
  - `initial_reaction.md` — initial output (frozen)
  - `conversation.jsonl` — append-only chat turns

### Strategic value

- **Layer-3 calibration hook** — PM marking responses as "realistic" / "not realistic" during chat becomes training signal for the specialized 8B model (per the Pythia roadmap)
- **Moat surface** — accumulated agent memory per customer compounds with use; competitors can't replicate months of conversation history
- **Daily-engagement wedge** — PMs return to chat with agents even without a new hypothesis to test, drastically increasing DAU vs the one-shot "submit and forget" pattern of competing tools

---

## Feature store adapters & customer credential handling

Customers' user data lives in their own warehouses (Snowflake first; BigQuery, Databricks, Redshift, CSV upload later). The simulator backend exposes a self-serve flow where a customer connects their warehouse, maps columns to Pythia's 7 feature groups, previews their population, and builds a versioned persona pack — without engineering involvement on the Pythia side.

### Pluggable feature-store adapters

`pythia_simulator/adapters/feature_stores/` defines a `FeatureStore` Protocol satisfied by every warehouse implementation:

```python
class FeatureStore(Protocol):
    def test_connection(self) -> None: ...
    def list_schemas(self) -> list[str]: ...
    def list_tables(self, schema: str) -> list[str]: ...
    def preview(self, table_fqn: str, sample_size: int = 100) -> TablePreview: ...
    def run_query(self, sql: str) -> list[dict[str, Any]]: ...
```

MVP ships `SnowflakeStore`. New warehouse types are added by implementing the Protocol and registering the connection `kind`.

### LLM-assisted column mapping

`services/column_mapper.py` reads the customer's column list + sample values and proposes which Pythia feature group each column belongs in (one LLM call per schema). The user reviews suggestions in the UI before the mapping is persisted. Cheap (~one call per onboarding) but turns a 30-minute manual mapping task into a 30-second review.

### Credential storage — envelope encryption

Snowflake credentials enter via the Connect form and are immediately encrypted before persistence. They never appear in API responses, logs, or service-to-service calls beyond the brief in-memory decryption window during a build run.

| Mode | Use | Key location |
|---|---|---|
| **`local`** | Dev only | Symmetric AESGCM key from `PYTHIA_LOCAL_CRED_KEY` env var |
| **`kms`** | Production | Per-customer Data Encryption Key (DEK) wrapped by a Key Encryption Key (KEK) in KMS (AWS KMS / Cloudflare KMS). The wrapped DEK and ciphertext are persisted to Postgres; KMS access is audit-logged. |

Key rotation: KMS key rotation triggers a re-encrypt-on-read policy; old wrapped DEKs are unwrapped, rewrapped under the new KEK, and persisted on next access.

### Single UI surface across all three producers

The frontend has three top-level tabs:

| Tab | Producer | Wizard |
|---|---|---|
| **Personas** | `pythia-personas` (imported as library) | 7-step: Connect → Source → Map → Preview → Configure → Build → Review + Promote |
| **Product** | `pythia-crawler` (imported as library) | Future-phase wizard: Connect sandbox → Declare capabilities → Per-role test creds → Schedule → Crawl + Diff view |
| **Simulations** | The simulator itself | Hypothesis submit → live agent reactions → chat with each agent |

All three are backed by the same simulator backend; each producer remains a separate repo + Python package but is invoked via the simulator's `services/*_builder.py` orchestrators. Customers never see the producer boundary.

---

## Auth & tenancy

- **Identity provider:** Clerk. SAML/SSO supported out of the box for enterprise.
- **Multi-tenancy:** single backend, single R2 bucket. Isolation enforced by **`customer_id` scope on every read/write** — middleware extracts customer_id from session JWT, attaches it to the request context, all R2 keys and DB queries are scoped by it.
- **R2 key encryption:** at rest, per-prefix encryption keys per customer (Phase 2). MVP: bucket-level encryption is sufficient for SOC 2 type 1 prep.
- **Database row-level scoping:** every row in Postgres carries `customer_id`; all queries enforce it via SQLAlchemy session-level filters.

---

## Observability

| Concern | Tool |
|---|---|
| Application errors | **Sentry** — backend + frontend SDK |
| LLM traces (prompts, responses, latency, cost) | **Langfuse** — already used in the ETL skill |
| Structured logs | JSON to stdout → Fly.io log aggregation; ship to Datadog/BetterStack when scale demands |
| Pipeline metrics (crawler runs, persona runs) | Postgres tables + simple admin dashboard in `pythia-simulator/frontend/admin` |
| Uptime + healthchecks | Fly.io built-in + Better Uptime for external probes |

---

## Deployment topology

| Component | Host | Why |
|---|---|---|
| Frontend (Next.js) | **Vercel** | Edge, simplest Next.js DX, free tier covers MVP |
| Backend (FastAPI) | **Fly.io** | Container-based, autoscales, cheaper than Cloud Run for always-on |
| Crawler workers (Playwright) | **Fly.io workers, separate process group** | Heavy Chromium containers, isolated from API workload |
| Persona workers | **Fly.io workers** | Lightweight batch jobs |
| Postgres | **Neon** | Serverless, branchable, free tier |
| Artifact store | **Cloudflare R2** | Zero egress, S3-compatible |
| Auth | **Clerk** | Hosted |
| LLM | **Groq (default) + Anthropic (fallback)** | Already configured in `pythia-personas`; same pattern in crawler + backend |

---

## CI/CD

Each repo has its own GitHub Actions pipeline:

| Repo | Pipeline |
|---|---|
| `pythia-personas` | lint → unit tests → integration test (sample run) → publish package to private index |
| `pythia-crawler` | lint → unit tests → Playwright smoke test → build Docker image → push to registry |
| `pythia-simulator/backend` | lint → unit tests → typecheck → build Docker → deploy to Fly.io staging on `main` |
| `pythia-simulator/frontend` | lint → typecheck → Next.js build → Vercel preview on PR; promote to prod on tag |
| `pythia-schemas` | lint → tests → publish to private package index → triggers downstream rebuilds |

---

## MVP scope

| In scope | Out of scope (Phase 2) |
|---|---|
| Single backend monolith | Service split (when teams grow) |
| In-process workers (`asyncio.create_task`) | Real job queue (Cloud Tasks / SQS) |
| Customer-supplied capability list for crawler | LLM-driven capability auto-discovery |
| Manual customer onboarding (admin endpoint) | Self-serve onboarding |
| Single-region deployment | Multi-region, data residency options |
| One LLM family (Groq + Anthropic) | Specialized 8B model from Pythia roadmap |
| Sentry + Langfuse | Full observability stack (Datadog, etc.) |
| Bucket-level encryption | Per-customer KMS keys |
| Pythia infra + customer sandbox creds | Self-hosted crawler for regulated industries |

---

## Decision log (locked-in choices)

| Decision | Choice | Rationale |
|---|---|---|
| Three-repo split | `pythia-personas` / `pythia-crawler` / `pythia-simulator` | Different runtime profiles, security models, cadences; clean composition via artifact store |
| Artifact store | Cloudflare R2 | Zero egress for repeated reads by simulator, S3-compat for portability |
| Backend language | Python (FastAPI) | Same language as producers → direct package imports, no IPC |
| Frontend stack | Next.js + TypeScript | Dominant enterprise SaaS UI; types codegen'd from OpenAPI |
| Schema source | Pydantic in `pythia-schemas` | One source of truth; TS generated downstream |
| Job orchestration (MVP) | Direct invocation behind `JobRunner` interface | No queue infra; swappable later without caller changes |
| Auth | Clerk | Enterprise SSO ready, fastest UX path |
| Metadata DB | Postgres on Neon | Serverless, free tier, branchable |
| Observability | Sentry + Langfuse | Errors + LLM traces; standard stack |
| Hosting | Vercel (frontend) + Fly.io (backend + workers) | Edge UI + container backend |
| Producers ship as library + CLI | Both faces from same codebase | Backend imports directly; cron runs standalone |
| Immutable artifacts | Always write a new version, never edit | Reproducibility of past simulations + drift detection |

---

## Open questions / risks

| Item | Notes |
|---|---|
| Cost forecasting | LLM cost per simulation (N personas × ~10K tokens × Groq pricing) needs modeling before pricing commitments |
| Customer sandbox availability | Some enterprises lack functional sandboxes; need a fallback (PM-led recorded session?) |
| Schema versioning | Need a `schema_version` field on every artifact + backend tolerates one minor version back |
| Frontend ↔ Worker progress UX | For long crawls and large simulations, need streaming progress (SSE? WebSocket?). MVP: poll every 5s |
| Per-customer LLM quotas | Need rate-limiting per customer to prevent one client from starving others |
| Data residency for EU customers | R2 has EU regions, but Clerk + Neon EU options must be matched; deferred to Phase 2 |

---

## Related

- [[pythia]] — overall project page
- [[pythia-de-spec]] — pretraining corpus spec (orthogonal layer)
- [[pythia-feature-pack-crawler-spec]] — Feature Pack Crawler design (subsystem detail)
- `~/vaults/personal/sessions/persona-classifier/context.md` — persona pack work-in-progress
