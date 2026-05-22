# Phase 4 — ticket drafts (agent-chat UI)

Source: `docs/agent-chat-ui-spec.md`. Ready to create as GitHub issues in the [Pythia Project](https://github.com/users/ram-de/projects/) once approved.

All issues:
- **Repo:** `ram-de/pythia-simulator` (unless noted)
- **Phase:** 4
- **Status on create:** Backlog (move to Next manually as we pick them up)

Ordering follows the "Implementation order (locked)" section of the spec.

---

## T01 — Result table refactor on `/simulations/[id]`

**Title:** `feat(frontend): result table grouped by persona on simulation detail page`
**Component:** frontend
**Depends on:** none (existing data is sufficient)

### What
Replace the bare "Agents that participated" list on `/simulations/[id]` with a persona-grouped result table per the design in `docs/agent-chat-ui-spec.md` ("Surface 1 — Result table").

Columns: Persona name · N (agent count) · Sentiment chip · Top quote · 💬 (chat affordance).
Row hierarchy: one group row per persona; click-to-expand reveals one row per agent in that persona.

### Why
The current list is debug output (8-char UUIDs) — not a result a PM can act on. The table is the landing page for the chat feature; without it, the chat surfaces have no plausible entry point.

### Out of scope
- Chat surfaces themselves (T03, T05). The 💬 button can route to placeholder URLs for now.
- Live (mid-sim) progressive row reveal — wait until single-agent chat lands.

### Acceptance
- Table renders for `sim` `89d01a19-…` (the existing streamly_sample run) showing 6 personas, sentiment + top quote per row.
- Top quote uses `agent.initial_reaction` (frozen). Truncated to ~80 chars with click-to-expand inline.
- Failed agents render as `failed — <error>` row with no chat button.
- Existing failure card still renders when the whole sim failed (no regression).
- Frontend typecheck clean.

---

## T02 — Wire `GET /agents/{id}` + `POST /agents/{id}/messages`

**Title:** `feat(api): implement get_agent and send_message routes`
**Component:** backend
**Depends on:** none

### What
Both routes in `backend/pythia_simulator/api/agents.py` currently raise `HTTPException(501)`. Wire them up.

- `GET /agents/{id}` — load via `AgentMemory.load(metadata)` and return the `AgentInstance` (identity + initial_reaction + conversation log). Look up the agent's metadata from the simulation it belonged to.
- `POST /agents/{id}/messages` — delegate to `AgentChatService.send_message(...)`; append the PM turn and the agent turn via `AgentMemory.append_turn`; return `AgentChatResponse`.

### Why
The agent chat service already exists (`services/agent_chat.py`) and the memory substrate exists (`memory/agent_memory.py`). What's missing is the HTTP edge. T03 and T05 both need this.

### Out of scope
- Postgres lookup of agent → sim. For now, accept a `?sim_id=` query param on `GET /agents/{id}` and look up the agent in the in-memory repo by that scoping. Phase 5's Postgres handover removes the query param.
- Streaming responses (Phase 4.6 or later).

### Acceptance
- `curl -X POST /agents/{aid}/messages -d '{"content":"why?"}'` returns a non-empty agent reply.
- Conversation log persists across requests (re-GET returns the appended turn).
- 50-turn conversation does not exceed the model's context window (truncation policy: keep identity + initial reaction + last N turns, where N is computed from token budget — copy pattern from `AgentChatService.send_message`).
- Backend tests cover one happy path + one not-found path.

---

## T03 — Individual-agent chat surface on `/agents/[id]`

**Title:** `feat(frontend): individual-agent chat with pinned identity + initial reaction`
**Component:** frontend
**Depends on:** T02

### What
Build the `/agents/[id]` page per the design's "Surface 3 — Individual-agent chat":
1. Pinned identity card at the top (persona name, persona description, 3-4 behavioral_snapshot fields, lifestage). Reusable component — also rendered on the persona-group page in T05.
2. Pinned "Initial reaction" block, with the hypothesis prose immediately above the reaction for context.
3. Scrollable chat — newest at the bottom, auto-scroll on new turn. Optimistic UI on send; disable composer while in-flight; error toast on failure.

Reusable primitives (build as standalone components so T05 reuses them): `<IdentityCard>`, `<ChatComposer>`, `<MessageBubble>`.

### Why
The agent chat is Pythia's defining feature. Surfacing it on a real route, anchored to a frozen identity, is the first PM-visible payoff of all the AgentMemory work.

### Out of scope
- Calibration flags (T06).
- Streaming token-by-token rendering — single full-reply response is fine for v1.

### Acceptance
- From the result table (T01) click on any agent row → land on `/agents/[id]` populated.
- Send a follow-up; agent replies in <10s; new turn appears in conversation log on refresh.
- Identity card and initial reaction never change across turns (visual confirmation of the identity-continuity guarantee).
- `npx tsc --noEmit` clean; `/qa` smoke pass.

---

## T04 — `POST /simulations/{id}/personas/{persona_id}/messages` (fan-out + synthesis)

**Title:** `feat(api): persona-group chat with per-agent fan-out and one-line synthesis`
**Component:** backend
**Depends on:** T02

### What
New route + service for persona-group chat. Per the spec, this is **fan-out**, not synthesis-only.

Service flow:
1. Resolve the agents in `(sim_id, persona_id)` from the in-memory repo.
2. For each agent, call the existing single-agent `send_message` path (`AgentChatService.send_message`) — this appends the PM turn + agent turn to *each individual agent's* conversation log. Identity continuity preserved.
3. Once all per-agent replies are in, make one synthesis LLM call summarizing the replies in 1-2 sentences.
4. Persist the persona-group turn (PM message + synthesis line + the list of per-agent reply IDs) at `customers/<id>/simulations/<sim_id>/persona_groups/<persona_id>/turns.jsonl`.
5. Return `{synthesis: str, per_agent: [{agent_id, content}]}`.

### Why
PMs reason about user *segments*, not individual users. Without the group surface, every drill-down requires walking through N agent pages — that's a research tool, not a PM tool. Spec rationale in `docs/agent-chat-ui-spec.md` § "Surface 2".

### Cost / rate-limit consideration
At Phase 2.5's N=8-10 agents per persona, fan-out = 8-10 concurrent LLM calls. Coordinate with Phase 2.5's Groq rate-limit backoff ticket (already in the project). For now, gate this ticket on Groq rate-limit infrastructure landing first OR add a `max_fan_out=6` cap in this service.

### Out of scope
- A "compose then send" UX optimization (deferred to T05's UX polish).
- Reading the synthesis from a cache when the same PM question recurs across agents (cute, not needed yet).

### Acceptance
- POST against the streamly_sample run with `persona_id=rivka_weekend_movie_night` returns 1 synthesis line + 1 agent reply (N=1 today).
- Each agent's conversation log contains the appended turn (verify by GET /agents/{id} on each).
- Persona-group log file exists with one JSONL line per PM turn.
- Backend tests: happy path + zero-agents-in-group → 422.

---

## T05 — Persona-group chat surface on `/simulations/[id]/personas/[persona_id]`

**Title:** `feat(frontend): persona-group chat page with side-by-side per-agent replies + synthesis`
**Component:** frontend
**Depends on:** T03 (for IdentityCard / ChatComposer / MessageBubble), T04

### What
New route `/simulations/[id]/personas/[persona_id]` per the design's "Surface 2".

Layout:
- Pinned: persona identity card (aggregate — name, description, N, initial group sentiment).
- Chat: each PM turn is followed by a synthesis-line bubble at the top, then a stack of per-agent reply bubbles below it, labeled with the agent's short id (clickable → `/agents/[id]`).
- Composer: same `<ChatComposer>` component from T03.
- "← Result table" back-link to `/simulations/[id]`.

### Why
This is the surface the cofounder specifically asked for. It's also the highest-leverage chat surface once Phase 2.5's N>1 per persona lands — a single PM question becomes 10 agents' answers in one screen.

### Out of scope
- Diff highlighting between agent replies (interesting, not v1).
- Filtering / sorting replies (interesting, not v1).

### Acceptance
- Send a PM message → see one synthesis line + N agent reply bubbles within ~10-15s.
- Click on `[rivka_001]` label in a reply → navigate to `/agents/rivka_001` and see the same turn appended to that agent's individual conversation log (identity-continuity sanity check).
- Composer disabled while in-flight; error toast on failure of any leg of the fan-out (partial-success policy: show what succeeded, flag what failed).

---

## T06 — Calibration flags on agent replies ("realistic / not realistic")

**Title:** `feat(frontend+api): per-turn calibration thumbs on agent replies`
**Component:** frontend, backend
**Depends on:** T03

### What
Add a small inline calibration affordance to each agent reply (and each per-agent reply on the persona-group page): a 👍 / 👎 with optional one-line reason. Writes to `AgentFeedbackRepo`.

### Why
Layer-3 calibration on the roadmap depends on a stream of "realistic / not realistic" signal. The hook is already in place at the repo layer; the UI is the late add. Capture starts producing training signal the moment this ships, even before Layer-3 model training begins.

### Out of scope
- A separate review queue / dashboard for the feedback. Just capture.
- Calibration on initial reactions (only follow-up turns for v1).

### Acceptance
- Each agent reply has 👍/👎 buttons; clicking writes to the backend; refresh persists.
- `GET /agents/{id}` includes any feedback turns in its response (or a sidecar field).

---

## Updates to existing docs (no new ticket — bundle with whichever PR ships the spec)

- `ROADMAP.md` — Phase 4 entry expanded to reference `docs/agent-chat-ui-spec.md` and add the persona-group surface bullet (today it only mentions individual chat).
- `CONTEXT.md` — "What's next" section already names Phase 2.5 as next; no change until Phase 4 actually starts.

---

## Notes on creating these as GitHub issues

Use `mcp__github__create_issue` with `owner: "ram-de", repo: "pythia-simulator"`. Body = the body of each ticket above (everything from `### What` onward), title = the title line. After creation, set the Phase field to `4` and Component as listed.

Don't create them all in one shot — create T01 first, link the spec doc in the issue body, then sanity-check the formatting and labels before batching the rest.
