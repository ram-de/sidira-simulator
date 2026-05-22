# Prior Art: MiroFish — What We Borrowed, What We Didn't

[MiroFish](https://github.com/666ghj/MiroFish) is a multi-agent prediction engine for public-opinion / cultural-event simulation. Different product, but the agent-simulation substrate has good ideas worth borrowing. This document is the explicit record of what we lifted and what we rejected — so future contributors don't waste cycles re-deriving these choices.

## What we borrowed (adapted into pythia-simulator)

### 1. SimulationRunState + JSONL event log
**Source:** `simulation_runner.py:101-193` (SimulationRunState dataclass) + `:482-554` (`_monitor_simulation` polls action log).

**What it does in mirofish:** Two-tier state model — recent activity in RAM, full event log on disk as JSONL. Frontend polls a status endpoint for live updates; the JSONL is the source-of-truth for audit + replay.

**How we adapted it:** `pythia_simulator/services/run_state.py` defines `SimulationRunState` (status, started_at, agents_total, agents_complete, partial_score) and a `RunEventLog` that appends one line per event (`agent.materialized`, `agent.reacted`, `score.updated`). Lives in R2 next to the simulation artifacts. Frontend will poll `/simulations/{id}/state` until status is COMPLETE.

**Why it matters for Pythia:** Without this, simulations are black-box — PMs stare at a spinner for 30 seconds. With it, they watch agents react one-by-one. Same code path also gives us crash recovery (resume from last logged event) and a full audit trail per simulation.

---

### 2. Parallel agent execution
**Source:** `oasis_profile_generator.py:851-1014` (ThreadPoolExecutor with progress callbacks).

**What it does in mirofish:** Persona generation runs in parallel across N workers with incremental progress updates and locale capture before thread spawn.

**How we adapted it:** `SimulationRunner.run()` now uses `asyncio.gather` over agent reactions instead of a serial loop. Each agent's LLM call runs concurrently. We use async-native primitives (Python) rather than ThreadPoolExecutor because our LLM SDK is async and FastAPI already runs an event loop.

**Why it matters for Pythia:** 10 personas × 5 seconds serial = 50 seconds per simulation. Parallel = ~5 seconds (LLM-bound). Critical for UX.

---

### 3. INTERVIEW_PROMPT_PREFIX
**Source:** `simulation_runner.py:25` — prefix prepended to every interview prompt to coerce text-only reasoning and prevent tool-call drift.

**What it does in mirofish:** Solves the problem where agents trained on tool-using base models try to invoke tools during interview mode, producing garbage.

**How we adapted it:** `pythia_simulator/services/agent_chat.py` injects a `_CHAT_GUARD_PREFIX` system-supplement before every PM message. The prefix tells the agent to stay in-character, answer in first-person prose, and never request tools or structured outputs. Reinforces the identity-continuity guarantee at runtime.

**Why it matters for Pythia:** Even with frozen identity, base LLMs occasionally drift into "As an AI language model…" mode mid-chat. The guard prefix prevents that.

---

### 4. JSON-repair helper for LLM outputs
**Source:** `oasis_profile_generator.py:606-670` — `_try_fix_json` handles common LLM JSON failures (trailing commas, unescaped quotes, truncation).

**What it does in mirofish:** Wraps every LLM-as-JSON call with a forgiving parser that tries direct parse → repair → fallback before failing.

**How we adapted it:** `pythia_simulator/adapters/llm.py` exposes `chat_json(messages, schema)` — calls `chat()`, attempts `json.loads()`, attempts `_repair_json()` on failure (strips code fences, fixes trailing commas, balances braces), validates against the Pydantic schema, raises only on terminal failure.

**Why it matters for Pythia:** Score aggregation and weakness diagnosis return JSON. We need them to be robust to LLM quirks without bespoke retry logic at every call site.

---

## What we considered and rejected

### Inter-agent socialization
MiroFish has agents talk to each other and evolve emergently (`simulation_runner.py:_monitor_simulation` reads cross-agent actions). **Rejected for Pythia v1** — Pythia validates a *single* hypothesis against an independent persona sample, not group dynamics. Adding socialization would change the math (you'd need to control for influence effects to get a clean confidence score). Revisit only if we add a "viral spread" simulation mode later.

### Zep graph memory
MiroFish streams every action into a Zep knowledge graph (`zep_graph_memory_updater.py`) so agents can query their own history semantically. **Rejected for MVP** — our identity-continuity model (frozen prompt + frozen reaction + appended turns) covers the same need with no external dependency. If we ever want cross-simulation memory ("how did Maya feel about the *last* hypothesis?"), revisit with either Zep or a pgvector table — but only when there's a user request for it.

### Subprocess-based agent IPC
MiroFish keeps a live OASIS subprocess and routes interview prompts to it (`simulation_runner.py:1373-1608`). **Rejected for Pythia** — we don't need a long-lived agent process because our agents *are* their frozen artifacts. The replay model (load identity → load reaction → load history → LLM call) is stateless and avoids the operational complexity of subprocess lifecycle management.

### Simulation config auto-generation
MiroFish uses an LLM to auto-tune per-agent reactivity, posting frequency, sentiment biases (`simulation_config_generator.py`). **Deferred** — interesting idea for tuning persona aggressiveness from hypothesis context, but premature. Wait until a real PM tells us their simulation results feel off.

### Multi-platform abstractions (Twitter/Reddit/etc.)
MiroFish has platform-specific action types because public-opinion simulation requires it. **Rejected** — Pythia has one "platform" (the customer's product), captured in the Feature Pack. No abstraction needed.

### Narrative report output
MiroFish ends simulations with a multi-page text report. **Rejected** — Pythia returns a structured `SimulationResult` (confidence score + weaknesses + refinement suggestions). The PM-facing narrative happens in the chat with individual agents, not in a generated report.

### Hardcoded zh-CN strings + bilingual UI
**Rejected** — Pythia is English-only enterprise SaaS targeting US/EU PMs. We'd carry the i18n complexity for years if we forked.

---

## Net-new (NOT lifted from MiroFish)

### Persona-group chat surface
`docs/agent-chat-ui-spec.md` defines a `/simulations/[id]/personas/[persona_id]` chat surface — PM types one message, the system fans out to every agent in the persona group, and answers are returned side-by-side with a synthesis line summarizing the real replies. **This is a Pythia-original design, not a MiroFish borrow.** MiroFish has agent-to-agent socialization (rejected above); the Pythia surface is PM-to-group fan-out with no inter-agent influence. Flagged here so future contributors don't grep MiroFish looking for a pattern that doesn't exist there.

---

## Pattern map

| MiroFish file:line | Pythia adaptation |
|---|---|
| `simulation_runner.py:101-193` | `pythia_simulator/services/run_state.py` |
| `simulation_runner.py:482-554` | `RunEventLog` in `run_state.py` |
| `simulation_runner.py:25` (INTERVIEW_PROMPT_PREFIX) | `_CHAT_GUARD_PREFIX` in `services/agent_chat.py` |
| `oasis_profile_generator.py:497-581` | `services/prompt_composer.py` (already in place; mirofish patterns informed structure) |
| `oasis_profile_generator.py:606-670` | `_repair_json()` in `adapters/llm.py` |
| `oasis_profile_generator.py:851-1014` | `asyncio.gather` in `services/simulation_runner.py` |

---

## How to use this document

When tempted to copy more from mirofish: read this file first. The rejections aren't arbitrary — each one represents a deliberate boundary between *agent-simulation-as-research* (mirofish's domain) and *agent-simulation-as-enterprise-PM-tool* (Pythia's domain). When the boundary moves, update this doc rather than letting drift happen silently.
