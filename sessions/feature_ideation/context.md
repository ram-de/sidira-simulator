---
type: session
domain: feature_ideation
status: closed
started: 2026-05-22
closed: 2026-05-26
owner: rmkmar
---

# Session: feature_ideation — Phase 4 agent-chat UI design + tickets

## Goal
Lock the interaction-UI design for Pythia's defining feature (agent chat) by lifting the patterns we like from MiroFish — the per-agent result table, the persona-group chat surface, and the individual-agent chat surface — and seeding the GitHub Project with Phase-4 tickets that implement them.

## In Progress
— session complete. Design work done; implementation continues in a separate `phase-4-agent-chat` session opened 2026-05-26. The two "in progress" items below were never strictly blocking and have been resolved or absorbed:
- ~~Phase=4 / Component labels on issues~~ — accepted as a documentation gap; the GitHub Project filters work without them (per phase-prefix in title).
- ~~Cofounder review~~ — solo founder; spec is the founder's own design, no second pair of eyes needed before implementation.

## Completed
- [x] Surveyed the existing surface: result page bare-list at `/simulations/[id]`, agent stub at `/agents/[id]`, `AgentChatService` wired but `/agents/{id}` + `/agents/{id}/messages` routes still raise 501.
- [x] Wrote `docs/agent-chat-ui-spec.md` covering all three surfaces (result table, persona-group chat, individual chat), with explicit reusable-primitives + non-goals + open questions sections.
- [x] Added a "Net-new (NOT lifted from MiroFish)" section to `docs/mirofish-prior-art.md` flagging persona-group chat as a Pythia-original design, so future contributors don't grep MiroFish for a pattern that isn't there.
- [x] Drafted 6 tickets (T01-T06) in `sessions/feature_ideation/phase-4-tickets.md` with What / Why / Out-of-scope / Acceptance for each, plus dependency ordering.
- [x] Created all 6 issues on GitHub: [#51](https://github.com/ram-de/pythia-simulator/issues/51) result table, [#52](https://github.com/ram-de/pythia-simulator/issues/52) agent routes, [#53](https://github.com/ram-de/pythia-simulator/issues/53) individual chat UI, [#54](https://github.com/ram-de/pythia-simulator/issues/54) persona-group fan-out backend, [#55](https://github.com/ram-de/pythia-simulator/issues/55) persona-group UI, [#56](https://github.com/ram-de/pythia-simulator/issues/56) calibration thumbs. Labels not applied (the `phase-4` / `component-*` labels don't exist on the repo and MCP can't create them — manual step in browser).

## Next Steps
— session complete. Implementation tracked in `sessions/phase-4-agent-chat/context.md`.

**Status of the Phase 4 surfaces, as of close (2026-05-26):**
1. **Result table (#51)** — ✅ partial: persona-grouped collapsible table shipped via Phase 2.5 PR #67 (`12bea0f`). Remaining spec details (sentiment chip column, top-quote column, 💬 chat button per row) deferred until #52+#53 ship — the chat button is the entry point to chat, so it only adds value once chat exists.
2. **Individual chat (#52 backend + #53 frontend)** — 🔲 not started. Spec-locked: un-stub `POST /agents/{id}/messages`, build chat UI on `/agents/[id]` with pinned identity card + initial reaction.
3. **Persona-group chat (#54 backend + #55 frontend)** — 🔲 not started. Spec-locked, but `/plan-ceo-review` recommended on the synthesis quality bar before #54 lands. Defer until after #53 ships.
4. **Calibration thumbs (#56)** — 🔲 not started. Last per spec order; doesn't block others.

## Key Files
- `frontend/app/simulations/[id]/page.tsx` (current result page — to be extended)
- `frontend/app/agents/[id]/page.tsx` (stub — becomes individual chat surface)
- `backend/pythia_simulator/services/agent_chat.py` (one-agent chat already wired; `POST /agents/{id}/messages` exists)
- `backend/pythia_simulator/memory/agent_memory.py` (frozen identity + reaction + appendable conversation log)
- `docs/mirofish-prior-art.md` (what we already borrowed; the group-chat layer is new ground)
- `docs/agent-chat-ui-spec.md` (to be written)

## Key Context
- ROADMAP Phase 4 says "agent chat UI — the differentiator", scoped to one-agent-at-a-time. The persona-group chat surface the cofounder wants is a *new* idea — it changes Phase 4's surface area, and the prior-art doc explicitly rejected mirofish's inter-agent socialization. The group chat we're proposing is PM-to-group (broadcast Q&A), not agent-to-agent — different math, no influence effects. Worth flagging this distinction in the spec.
- MiroFish prior-art doc (`docs/mirofish-prior-art.md`) is the canonical place to record what we lifted vs. rejected. Any net-new borrow goes there too.
- Tickets land in the GitHub Project (board for `ram-de/pythia-simulator` + `pythia-personas` + `pythia-crawler`), Phase = 4, Component = frontend or backend or docs or schema.

## For my cofounder
Net-new design idea on the table: PM should be able to chat with a *persona group* (all binge marathoners, say) as well as individual agents. That's a v2-ish surface for Phase 4 that the current Phase 4 spec doesn't cover. We're drafting the design + tickets here; nothing implemented yet.
