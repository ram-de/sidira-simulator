---
type: session
domain: phase-4-agent-chat
status: active
started: 2026-05-26
owner: ram-de
---

# Session: phase-4-agent-chat — implement Phase 4 (the differentiator)

## Goal
Ship the three agent-chat surfaces per `docs/agent-chat-ui-spec.md`: individual-agent chat, persona-group chat, and the calibration-thumbs feedback layer. Result table foundation already shipped in Phase 2.5 PR #67; the spec-mandated additions to it (sentiment chip, top quote, 💬 chat button) come back into scope once chat exists to navigate into.

## In Progress
- [ ] **#52 — backend: un-stub `GET /agents/{id}` + `POST /agents/{id}/messages`**. The `AgentChatService` is fully wired; routes return 501. This is the first ticket — un-stubs the chat foundation that #53 will consume.

## Completed
(nothing yet — implementation session just opened)

## Next Steps
**Implementation order per spec (locked):**

1. **#52 backend — chat routes** (this session's first task). Load AgentInstance from R2 metadata + memory, return on GET. POST appends a PM turn, calls `AgentChatService` for the agent reply, appends that turn, returns the agent's response. Identity-continuity guarantee via the existing `AgentMemory.build_replay_messages` + `_CHAT_GUARD_PREFIX`.
2. **#53 frontend — individual chat UI** at `/agents/[id]`. Spec layout: identity card (pinned, top) → initial reaction (pinned) → scrollable chat. Reuse `AgentMemory` fields surfaced via #52.
3. **Result-table refinements** — fold the spec-mandated sentiment chip / top-quote / 💬 button additions into #51 follow-up work. 💬 button on agent rows links to `/agents/[id]` (the surface #53 builds).
4. **`/plan-ceo-review` on synthesis quality bar for #54** — captured open question. A bad one-line persona-group synthesis is worse than no synthesis. Lock the prompt strategy + eval rubric before the code lands.
5. **#54 backend — persona-group fan-out** at `POST /simulations/{sim_id}/personas/{persona_id}/messages`. Fans out to each agent in the persona, awaits all via `AgentChatService`, computes a synthesis as a separate LLM call against the just-completed answers, persists the synthesis to a per-persona-group log (NOT on individual agents).
6. **#55 frontend — persona-group chat UI** at `/simulations/[id]/personas/[persona_id]`. Side-by-side per-agent replies + synthesis at top. 💬 button on persona-row in result table links here.
7. **#56 — calibration thumbs.** Per-turn 👍/👎 on agent replies. Hook into existing `AgentFeedbackRepo`. Adds the Layer-3 calibration signal that Phase 9 will consume.

## Key Files
- `docs/agent-chat-ui-spec.md` — locked design (162 lines). Read first.
- `sessions/feature_ideation/phase-4-tickets.md` — drafted ticket bodies if GitHub issue copy is stale.
- `backend/pythia_simulator/api/agents.py` — the two stubbed routes (#52 targets this).
- `backend/pythia_simulator/services/agent_chat.py` — `AgentChatService` already wired; #52 just plumbs route → service.
- `backend/pythia_simulator/memory/agent_memory.py` — `AgentMemory.build_replay_messages`, `_CHAT_GUARD_PREFIX`, append_turn. The identity-continuity infrastructure.
- `backend/pythia_simulator/adapters/repositories.py` — `AgentInstanceRepo.get()` exists; needed for the GET route.
- `frontend/app/agents/[id]/page.tsx` — stub today; #53 builds this out.
- `frontend/app/simulations/[id]/page.tsx` — current result table from PR #67; later folds in 💬 buttons.

## Operational lessons (don't re-trip)
- **`npx next build` poisons the running `npm run dev` chunk cache.** Hit this on 2026-05-22 (PR #67) AND again on 2026-05-26 (PR #76). When verifying a frontend PR locally, EITHER kill the dev server before running `next build`, OR skip the build verification (`tsc --noEmit` alone catches almost everything) and rely on the codex round to surface anything else. The symptom is 404s on `main-app.js` / `layout.js` / `app-pages-internals.js` in the Network tab and pages stuck on their SSR'd loading state. Fix: kill :3000 process, `rm -rf frontend/.next`, restart `npm run dev`.

## Key Context
- **Spec is locked** (per `docs/agent-chat-ui-spec.md` "Design locked"). Don't re-litigate the persona-group fan-out vs. synthesis-only decision, the no-cross-persona-chat decision, or the identity-continuity append-only rule.
- **Identity-continuity invariant:** chat-time agent IS simulation-time agent. The Phase 2.5 identity_seed work (#5) baked this in — every chat turn is generated from the frozen `identity_prompt` + frozen `initial_reaction` + the full conversation log. Re-instantiating an agent for chat is forbidden.
- **#51 result table is partially done.** PR #67 shipped the persona-grouped expandable table; the spec calls for additional columns (sentiment chip, top quote) + a 💬 button. Those land later in this session — they need chat (#53) to exist before the 💬 button is useful.
- **Open design question parked for #54:** synthesis quality bar. The session memory from `weighted_population` says `/plan-ceo-review` before #54 code. Don't skip.
- **No new architectural decisions in scope for this session.** Implement the spec; revisit design only if something breaks irreparably.

## For my cofounder
Phase 4 implementation starts here. Spec is `docs/agent-chat-ui-spec.md` — locked, no re-litigation. First ticket: #52 (un-stub the two `/agents/{id}` routes). The chain after that is #53 → result-table polish → `/plan-ceo-review` → #54 → #55 → #56. Each step ships independently; the result table already in main is enough that an early-merged #52+#53 gives a real chat surface even before the persona-group work lands.
