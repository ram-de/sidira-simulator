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
- [ ] **`/plan-ceo-review` on #54's synthesis quality bar** — locked design question per `docs/agent-chat-ui-spec.md` and the original `weighted_population` session notes. A bad one-line persona-group synthesis is worse than no synthesis. Lock prompt strategy + eval rubric before any code on #54.

## Completed
- [x] **#52 merged via [PR #75](https://github.com/ram-de/pythia-simulator/pull/75)** as `f1b9d2d`. `GET /agents/{id}` + `POST /agents/{id}/messages` un-stubbed. Routes call `AgentMemory.load` (wrapped in `asyncio.to_thread` for the sync R2 read) + `AgentChatService.send_message`. Customer scoping enforced at the repo layer; cross-customer agent reads return 404. LLM-side exceptions surface as 502 (distinguishable from a "service broken" 500). Best-effort `repo.touch()` for `last_active_at`/`message_count` after the turn lands; failures logged via structlog (`agents.touch_failed` with agent_id + customer_id + exc_type), not silently swallowed. 7 new tests in `test_agents_api.py` (GET/POST happy paths, 404 cases, customer scoping, empty-body rejection, multi-turn identity-continuity). **Codex P1 fix mid-PR**: PM-turn-before-LLM-call ordering was a retry-duplication footgun; moved to PM-turn-after-LLM-success-only in `AgentChatService.send_message`. Suite 156 → 164.
- [x] **#53 merged via [PR #76](https://github.com/ram-de/pythia-simulator/pull/76)** as `a8c4eb7`. Individual-agent chat at `/agents/[id]`. Sticky identity card (persona name + persona_id + 5 identity_seed fields), hypothesis + initial reaction in view together, bounded-scroll conversation (`maxHeight: 50vh` so the sticky card stays in place when new turns arrive), composer with Enter-to-send + Shift+Enter newline + IME composition guard. Optimistic PM turn rendering with refetch-on-success to canonical state. Codex P1 fix mid-PR: split POST-success from refetch-failure so a refetch error doesn't roll back a successfully-persisted turn (which would prompt a duplicating retry). 4 codex rounds, 0 P1 outstanding, 0 P2 outstanding.
- [x] **#77 + #78 merged via [PR #79](https://github.com/ram-de/pythia-simulator/pull/79)** as `980439c`. Two PM-trust papercuts the live chat surface immediately surfaced:
  - **#77 templated opener** — all agents opened with "Honestly, I'm not [too] thrilled... As someone who [persona summary]..." regardless of actual persona. Fix lives in `prompt_composer` with a new `### How to open` sub-section requiring identity_seed grounding + an explicit list of polite-hedge templates to avoid + soft framing ("Open like a real person reacting in the moment").
  - **#78 identity_seed × persona contradiction** — a `lex_new_explorer` agent (persona: "first 60 days") was drawn with `tenure_band: "veteran (3y+)"`. Fix: `_PERSONA_OVERRIDES` table in `services/identity_seed.py` constraining the 6 demo personas to coherent draws. Stopgap with sunset note — pack-supplied `behavioral_seeds` (v1.1 packs, eventually) bypass it entirely. Codex P1 fix mid-PR: Dom's tenure was over-permissive (allowed `early (3-12mo)` even though prose says "14 months" = established only); narrowed. Sam + Priya were over-narrow (excluded `veteran` and `early` respectively without textual justification); widened. Suite 164 → 170.

## Next Steps
**Remaining Phase 4 implementation order (revised after #52/#53/#77/#78 shipped):**

1. **`/plan-ceo-review` on #54's synthesis quality bar.** Load-bearing design question. Cost of a bad one-line synthesis = "templated AI slop, lost trust" stacked across N agent replies — same failure mode #77 was about, but worse because the synthesis is what the PM reads FIRST. Decisions to lock: (a) prompt strategy — what makes a "good" synthesis ("3 of 5 said X because Y"); (b) eval rubric — how do we measure synthesis quality before shipping; (c) failure mode — what if the N agent replies are themselves contradictory? Synthesis says "mixed" or refuses?
2. **#54 backend — persona-group fan-out** at `POST /simulations/{sim_id}/personas/{persona_id}/messages`. Fans out to each agent in the persona, awaits all via `AgentChatService.send_message` (which now has the correct PM-turn-after-LLM ordering from #52's codex fix). Computes the synthesis as a SEPARATE LLM call against the just-completed answers. Persists the synthesis to a per-persona-group log (`customers/<id>/simulations/<sim_id>/persona_groups/<persona_id>/turns.jsonl`) — NOT on individual agents (per spec: drilling into a group answer must land on the same individual agent's chat, so synthesis is meta, not turn-level).
3. **#55 frontend — persona-group chat UI** at `/simulations/[id]/personas/[persona_id]`. Side-by-side per-agent replies (uses the same composer + message-bubble primitives as #53) + synthesis pinned at top. 💬 button on persona-row in result table (currently the persona-grouped collapsible) links here. Optimistic UI + the same PM-after-LLM rollback semantics from #53.
4. **Result-table refinements (#51 follow-up).** Spec-mandated additions: sentiment chip column, top-quote column, 💬 button per row. These need #54 + #55 to exist before the 💬 button has anywhere to navigate to.
5. **#56 — calibration thumbs.** Per-turn 👍/👎 on agent replies (both individual and group surfaces). Hook into existing `AgentFeedbackRepo`. The Layer-3 signal Phase 9 will consume. Last per spec order.

## Carryover questions / follow-ups surfaced during testing

- **Opener-quality observability.** #77 ships the *prompt instruction*; whether the LLM actually obeys it across thousands of agent-runs is observable only via #56 calibration thumbs + Phase 9. No way to assert "the opener is good" in unit tests; the prompt content is pinned, the behavior is empirical.
- **Persona overrides are a stopgap.** `_PERSONA_OVERRIDES` in `services/identity_seed.py` covers the 6 demo personas. Real long-term answer is pythia-personas v1.1 packs emitting per-persona `behavioral_seeds`. The override table has a `**This is a stopgap. Delete when v1.1 packs ship.**` comment baked in. When the v1.1 persona work lands in the sibling repo, this file shrinks.
- **streamly_sample customer not covered by overrides.** The override table is keyed by `persona_id` of the 6 demo personas (maya/dom/priya/lex/jordan/sam). If a sim runs against the `streamly_sample` customer (its 6 video-streaming personas), it falls through to `_DEFAULT_BEHAVIORAL_SEEDS` and the contradiction class returns. Not blocking — `streamly_sample` is a fixture for proving the simulator isn't shaped only for food-delivery, not a demo we're showing externally yet. If we ever do, populate overrides for those personas too.

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
- **Identity-continuity invariant** (verified empirically 2026-05-26): chat-time agent IS simulation-time agent. Every chat turn is generated from the frozen `identity_prompt` + frozen `initial_reaction` + the full conversation log + the `_CHAT_GUARD_PREFIX`. Re-instantiating an agent for chat is forbidden. **The full identity prompt is what the LLM sees on every turn — NOT just the initial reaction.** The UI on `/agents/[id]` shows the PM a summary card (persona name + 5 identity_seed fields), but the LLM gets: persona description prose, JTBD, behavioral snapshot (orders_per_week / dashpass_active / promo_redemption_rate / fee_sensitivity_index / etc), identity_seed fields, current product PRD + structural spec, the proposed change, and the `### How to open` instructions from #77. This is the architecture answer to "is the follow-up reply really staying in persona?" — pinned by `test_send_message_multi_turn_preserves_identity_continuity` in `test_agents_api.py`.
- **#51 result table is partially done.** PR #67 shipped the persona-grouped expandable table; the spec calls for additional columns (sentiment chip, top quote) + a 💬 button. Those land AFTER #54+#55 ship — they need chat surfaces to exist before the 💬 button has anywhere to navigate to.
- **No new architectural decisions in scope for this session.** Implement the spec; revisit design only if something breaks irreparably.
- **Ship-then-dogfood pattern is working.** #53 shipped, user clicked through, two real PM-trust papercuts surfaced (#77 templated openers, #78 identity contradictions). Both fixed within hours via #79. This is the calibration loop working — the chat surface IS the eval surface for #77/#78-class bugs.

## For my cofounder
**Phase 4 status as of 2026-05-26: 2-of-5 tickets shipped + 2 PM-trust papercut fixes** (#52, #53, #77, #78). Individual-agent chat is live: a PM can click any agent from a simulation result table, land on `/agents/[id]`, see the agent's identity card + initial reaction + conversation, and ask follow-ups. Follow-ups are guaranteed to stay in persona — the LLM receives the full identity_prompt (persona description, behavioral snapshot, identity_seed, product PRD, hypothesis, opener guidance) on every turn, not just the initial reaction. Pinned by tests.

**What's next:** `/plan-ceo-review` on #54's synthesis quality bar BEFORE writing any persona-group fan-out code. After that: #54 backend → #55 frontend → #51 result-table polish → #56 calibration thumbs. The two papercut fixes (#77 + #78) bought us trust before #54 stacks N agents side-by-side and amplifies any templating.

To pick this up: `/pythia-session resume phase-4-agent-chat`, read the spec at `docs/agent-chat-ui-spec.md`, then run `/plan-ceo-review` on the synthesis question with `docs/agent-chat-ui-spec.md` as input.
