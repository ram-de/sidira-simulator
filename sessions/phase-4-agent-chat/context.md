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
- [ ] **#51 result-table polish** — sentiment chip + top-quote column per row. Now unblocked: persona-row 💬 → `/simulations/[id]/personas/[persona_id]`, agent-row 💬 → `/agents/[id]`. Last spec-mandated piece of the result table.
- [ ] **#56 calibration thumbs** — per-turn 👍/👎 on individual replies AND on synthesis + collective lines. Collective quality is the failure mode the rubric can't catch; only PM signal can.

## Completed
- [x] **#52 merged via [PR #75](https://github.com/ram-de/pythia-simulator/pull/75)** as `f1b9d2d`. `GET /agents/{id}` + `POST /agents/{id}/messages` un-stubbed. Routes call `AgentMemory.load` (wrapped in `asyncio.to_thread` for the sync R2 read) + `AgentChatService.send_message`. Customer scoping enforced at the repo layer; cross-customer agent reads return 404. LLM-side exceptions surface as 502 (distinguishable from a "service broken" 500). Best-effort `repo.touch()` for `last_active_at`/`message_count` after the turn lands; failures logged via structlog (`agents.touch_failed` with agent_id + customer_id + exc_type), not silently swallowed. 7 new tests in `test_agents_api.py` (GET/POST happy paths, 404 cases, customer scoping, empty-body rejection, multi-turn identity-continuity). **Codex P1 fix mid-PR**: PM-turn-before-LLM-call ordering was a retry-duplication footgun; moved to PM-turn-after-LLM-success-only in `AgentChatService.send_message`. Suite 156 → 164.
- [x] **#53 merged via [PR #76](https://github.com/ram-de/pythia-simulator/pull/76)** as `a8c4eb7`. Individual-agent chat at `/agents/[id]`. Sticky identity card (persona name + persona_id + 5 identity_seed fields), hypothesis + initial reaction in view together, bounded-scroll conversation (`maxHeight: 50vh` so the sticky card stays in place when new turns arrive), composer with Enter-to-send + Shift+Enter newline + IME composition guard. Optimistic PM turn rendering with refetch-on-success to canonical state. Codex P1 fix mid-PR: split POST-success from refetch-failure so a refetch error doesn't roll back a successfully-persisted turn (which would prompt a duplicating retry). 4 codex rounds, 0 P1 outstanding, 0 P2 outstanding.
- [x] **#55 + collective-mode pivot merged via [PR #83](https://github.com/ram-de/pythia-simulator/pull/83)** as `826415f`. Frontend at `/simulations/[id]/personas/[persona_id]` with two modes (collective default + individual fan-out), `[label]` linkification to drill into individuals, `unavailable_agents` warning banner on partial load failures, `sessionStorage` draft persistence on both surfaces with single-effect restore+persist that survives StrictMode double-mount, and a "back to {persona_name} (group chat)" link on `/agents/[id]`. Native `<input type="radio">` for the mode toggle (proper keyboard semantics for free). 3 codex rounds, final CLEAR. Live PM smoke: real synthesis came back with `[dom_promo_driven_restaurant]` citation → renderer linkifies to `/agents/{id}`.
- [x] **Collective-mode backend pivot merged via [PR #82](https://github.com/ram-de/pythia-simulator/pull/82)** as `29e5f4f`. `mode="collective"` (default) added to `POST .../messages`: ONE LLM call answers in the voice of the persona group; cites individuals via `[agent_label]` tokens which the route resolves to canonical `agent_id`s. Driven by PM live-testing on PR #80 where meta questions ("who reacted negatively?") to fan-out produced N solipsistic guesses. `mode="individual"` preserves the original #54 fan-out. Service contract: `collective_reply()` NEVER raises (same #80 P1 lesson). Strict `_CITATION_RE = r"\[([\w\-]+)\]"`; hallucinated labels survive in content but NOT in references. `_pair_prior_turns` keeps multi-turn coherent across mode-mixing. `UnavailableAgent` surfaces partial load failures. 2 codex rounds, final CLEAR. Spec updated: `docs/agent-chat-ui-spec.md` Surface 2.
- [x] **#54 merged via [PR #80](https://github.com/ram-de/pythia-simulator/pull/80)** as `a31e872`. Persona-group chat backend: `POST /simulations/{sim_id}/personas/{persona_id}/messages` fans one PM message out to every agent in the persona via `AgentChatService.send_message` (identity-continuity preserved per-agent — every fan-out reply lands in each agent's individual `conversation.jsonl`), runs `PersonaGroupSynthesisService.synthesize` against the successful replies, persists both turns to `customers/<id>/simulations/<sid>/persona_groups/<pid>/turns.jsonl`. Companion `GET .../turns` for replay. **Synthesis quality bar (`docs/54-synthesis-quality-bar.md`):** counted shape only (`"N of M said X"`, `"N agents split: ..."`, or `"N agents gave non-substantive replies"` diagnostic), banned-hedge list mirrors #77, count-accuracy post-process with retry-once-then-deterministic-fallback. **Service contract: synthesize() NEVER raises** (codex round-1 [P1]) — LLM exception degrades to deterministic line so the route can't 500 after fan-out has persisted PM/agent turns to individual logs. Same swallow-and-degrade for `group_log.append` (codex round-2 [P2]) and a 5-wide semaphore cap on fan-out matching `SimulationRunner` (codex round-3 [P2]). 4 codex rounds, final CLEAR. 10 unit tests + 11 API tests + 10 LLM-rubric fixtures (gated behind `PYTHIA_RUN_LLM_EVALS=1`, ~$0.05/run). Suite 170 → 194.
- [x] **#77 + #78 merged via [PR #79](https://github.com/ram-de/pythia-simulator/pull/79)** as `980439c`. Two PM-trust papercuts the live chat surface immediately surfaced:
  - **#77 templated opener** — all agents opened with "Honestly, I'm not [too] thrilled... As someone who [persona summary]..." regardless of actual persona. Fix lives in `prompt_composer` with a new `### How to open` sub-section requiring identity_seed grounding + an explicit list of polite-hedge templates to avoid + soft framing ("Open like a real person reacting in the moment").
  - **#78 identity_seed × persona contradiction** — a `lex_new_explorer` agent (persona: "first 60 days") was drawn with `tenure_band: "veteran (3y+)"`. Fix: `_PERSONA_OVERRIDES` table in `services/identity_seed.py` constraining the 6 demo personas to coherent draws. Stopgap with sunset note — pack-supplied `behavioral_seeds` (v1.1 packs, eventually) bypass it entirely. Codex P1 fix mid-PR: Dom's tenure was over-permissive (allowed `early (3-12mo)` even though prose says "14 months" = established only); narrowed. Sam + Priya were over-narrow (excluded `veteran` and `early` respectively without textual justification); widened. Suite 164 → 170.

## Next Steps
**Phase 4 core complete (#52, #53, #54, #55, collective-mode pivot).** Remaining Phase-4-adjacent work:

1. **#51 result-table polish.** Sentiment chip column, top-quote column. Persona-row 💬 already wired to `/simulations/[id]/personas/[persona_id]` (PR #83); agent-row 💬 already wired to `/agents/[id]`. What's missing is the visual columns — the data is in the simulation result; the UI doesn't render it yet.
2. **#56 calibration thumbs.** Per-turn 👍/👎 on individual replies AND on synthesis + collective lines (collective quality is the failure mode the rubric can't catch; only PM signal can). Hook into existing `AgentFeedbackRepo`. The Layer-3 signal Phase 9 will consume.
3. **Phase 5a #68 (parallel track):** Postgres repo wiring. Lifts the in-memory persistence to actual durable storage so chat history survives uvicorn `--reload` and process restarts.

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
- `frontend/app/agents/[id]/page.tsx` — individual chat surface (#53). Reference for layout + optimistic semantics for #55.
- `frontend/app/simulations/[id]/page.tsx` — current result table from PR #67; later folds in 💬 buttons (#51 follow-up).
- `backend/pythia_simulator/api/persona_groups.py` — POST + GET routes for #55 to consume.
- `backend/pythia_simulator/schemas/persona_group.py` — request/response shapes for #55 client types.
- `backend/pythia_simulator/services/persona_group_synthesis.py` — service contract reference (synthesize never raises).
- `docs/54-synthesis-quality-bar.md` — locked synthesis decisions; explains the response shape #55 renders.

## Operational lessons (don't re-trip)
- **`npx next build` poisons the running `npm run dev` chunk cache.** Hit this on 2026-05-22 (PR #67) AND again on 2026-05-26 (PR #76). When verifying a frontend PR locally, EITHER kill the dev server before running `next build`, OR skip the build verification (`tsc --noEmit` alone catches almost everything) and rely on the codex round to surface anything else. The symptom is 404s on `main-app.js` / `layout.js` / `app-pages-internals.js` in the Network tab and pages stuck on their SSR'd loading state. Fix: kill :3000 process, `rm -rf frontend/.next`, restart `npm run dev`.

## Key Context
- **Spec is locked** (per `docs/agent-chat-ui-spec.md` "Design locked"). Don't re-litigate the persona-group fan-out vs. synthesis-only decision, the no-cross-persona-chat decision, or the identity-continuity append-only rule.
- **Identity-continuity invariant** (verified empirically 2026-05-26): chat-time agent IS simulation-time agent. Every chat turn is generated from the frozen `identity_prompt` + frozen `initial_reaction` + the full conversation log + the `_CHAT_GUARD_PREFIX`. Re-instantiating an agent for chat is forbidden. **The full identity prompt is what the LLM sees on every turn — NOT just the initial reaction.** The UI on `/agents/[id]` shows the PM a summary card (persona name + 5 identity_seed fields), but the LLM gets: persona description prose, JTBD, behavioral snapshot (orders_per_week / dashpass_active / promo_redemption_rate / fee_sensitivity_index / etc), identity_seed fields, current product PRD + structural spec, the proposed change, and the `### How to open` instructions from #77. This is the architecture answer to "is the follow-up reply really staying in persona?" — pinned by `test_send_message_multi_turn_preserves_identity_continuity` in `test_agents_api.py`.
- **#51 result table is partially done.** PR #67 shipped the persona-grouped expandable table; the spec calls for additional columns (sentiment chip, top quote) + a 💬 button. Those land AFTER #54+#55 ship — they need chat surfaces to exist before the 💬 button has anywhere to navigate to.
- **No new architectural decisions in scope for this session.** Implement the spec; revisit design only if something breaks irreparably.
- **Ship-then-dogfood pattern is working.** #53 shipped, user clicked through, two real PM-trust papercuts surfaced (#77 templated openers, #78 identity contradictions). Both fixed within hours via #79. This is the calibration loop working — the chat surface IS the eval surface for #77/#78-class bugs.
- **"Service never raises after fan-out" pattern (#54 codex P1).** When a route does irreversible work (per-agent persistence via `AgentChatService.send_message`) and then downstream work (synthesis, audit-log write), an exception in the downstream step that bubbles to the route 500s and invites a client retry — which re-runs the irreversible step and duplicates per-agent state. Fix: wrap downstream calls in try/except + structlog warn + deterministic fallback. The downstream work degrades; the upstream truth is preserved. Apply this to any future post-fan-out step.

## For my cofounder
**Phase 4 core is shipped as of 2026-05-26: all five chat tickets + 2 PM-trust papercut fixes + a major collective-mode pivot** (#52, #53, #54, #55, #77, #78, PR #82). A PM can now:
1. Open `/agents/[id]` to chat 1:1 with a frozen agent. Identity-continuity guaranteed.
2. Open `/simulations/[id]/personas/[persona_id]` to talk to a persona group with a mode toggle:
   - **collective** (default): one voice speaks for the persona, cites individuals via `[label]` tokens that linkify to `/agents/[id]`.
   - **individual fan-out**: N replies side-by-side with a counted synthesis on top.
3. Drill from any collective citation or fan-out reply into the individual agent's chat surface, then come back to the group via a "back to {persona_name} (group chat)" link. Drafts on both surfaces survive the round-trip via `sessionStorage`.

The collective pivot was the load-bearing design fix: real PM testing on PR #80 surfaced that meta questions ("what's the consensus?", "who reacted negatively?") to fan-out produced N solipsistic guesses. The two-mode design is mirofish-shaped (one orchestrator voice + opt-in fan-out) and matches how PMs actually think about user segments.

**What's next:** #51 result-table polish (sentiment chip + top quote — the 💬 buttons already work) → #56 calibration thumbs (on individual, synthesis, AND collective lines). Phase 5a #68 (Postgres repo wiring) is a parallel track.

To pick this up: `/pythia-session resume phase-4-agent-chat`, read `docs/agent-chat-ui-spec.md` Surface 2 for current design (collective default + mode toggle + `[label]` linkification), then start on either #51 or #56.
