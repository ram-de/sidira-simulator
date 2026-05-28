---
type: session
domain: arm-scoped-persona-chat
status: closed
started: 2026-05-27
closed: 2026-05-27
owner: ram-de
---

# Session: arm-scoped-persona-chat -- A/B persona-group chat with split rooms (#98)

## Goal
Ship #98. In A/B-mode sims, the persona-group chat route (`/simulations/<id>/personas/<persona_id>`) is currently disabled with a tooltip because it fans out to ALL agents in the persona regardless of arm -- mixing treatment + control reactions in one chat room. Replace the disabled tooltip with TWO chat links per persona row in A/B mode (💬 T / 💬 C), each opening an arm-scoped chat room with arm-isolated transcripts.

First question from #92 dogfood was literally "why can't I chat with the persona group?" Confirmed the followup is wanted, not theoretical.

## Locked design decisions (carried from ticket)

1. **Approach (a) split rooms.** Each persona row in A/B mode renders TWO chat links: 💬 T (treatment) and 💬 C (control). Each opens an independent chat page with its own transcript. Rejected (b) arm-selector dropdown on a shared route -- transcript continuity gets muddled, and split rooms map naturally to how PMs think about A/B comparison.
2. **Backend: arm tag in the route + log path.** `?arm=treatment|control` query param on both POST and GET handlers. PersonaGroupLog path extends with the arm so transcripts are physically isolated.
3. **Feedback target_id extends with arm suffix.** Without this, T-turn-0 thumbs and C-turn-0 thumbs collide on the same `(sim_id, persona_id, turn_index)` key.
4. **Single-arm path UNCHANGED.** Pre-#98 sims use the existing `?arm=` omitted path; log file lives at the existing key; feedback target_id stays `{sim_id}/{persona_id}`. Zero regression.

## In Progress
(none)

## Completed
- [x] Backend: `PersonaGroupLog` now supports optional `arm` and stores A/B persona-group transcripts under `.../<persona_id>/treatment/turns.jsonl` or `.../<persona_id>/control/turns.jsonl`.
- [x] Backend: persona-group POST/GET handlers accept `?arm=treatment|control`, filter fan-out/replay to that arm, and preserve the pre-#98 no-arm path for single-arm sims.
- [x] Backend: persona-group feedback accepts `?arm=...`, reads the arm-scoped transcript, and writes feedback to `{sim_id}/{persona_id}/{arm}` so T/C turn indexes do not collide.
- [x] Frontend: A/B persona rows now show two chat links (`💬 T`, `💬 C`) instead of the disabled "1:1 only" tooltip.
- [x] Frontend: persona-group chat page reads `?arm=...`, filters the displayed cohort count to that arm, scopes load/send/feedback calls, and keeps draft state separate by arm.
- [x] Tests: added A/B fan-out/log isolation coverage and arm-scoped feedback isolation coverage.
- [x] Codex review round 1 found two P2s: require `arm` for A/B persona-group APIs, and avoid broken empty-arm chat entry points.
- [x] Backend: A/B persona-group chat/turns/feedback now 400 when `?arm=` is omitted, preventing old/bookmarked unscoped URLs from recreating mixed rooms.
- [x] Frontend: A/B persona-group chat pills are disabled for an arm when that persona has no surviving agents in the completed run.
- [x] Verification: `backend/.venv/bin/pytest tests/` passed (331 passed, 10 skipped); touched-file `ruff` + `black --check` passed; `frontend` `npx tsc --noEmit` and `npm run build` passed; `git diff --check` passed.
- [x] Final Codex review passed with no correctness regressions.
- [x] PR #104 (`feat: add arm-scoped persona group chat`) merged via squash to `main` as `bdac59b`, closing #98.
- [x] GitHub issue #98 is closed and the Pythia Project item is verified as `Status: Done`.

## Next Steps
— session complete

## Key Files
- `backend/pythia_simulator/memory/persona_group_log.py` -- _key + append + read get optional arm
- `backend/pythia_simulator/api/persona_groups.py` -- POST + GET handlers + arm query param
- `backend/pythia_simulator/api/feedback.py` -- target_id arm suffix
- `frontend/app/simulations/[id]/page.tsx` -- replace disabled tooltip with TWO arm links, disabled when an arm has no surviving agents
- `frontend/app/simulations/[id]/personas/[persona_id]/page.tsx` -- arm search param + arm-scoped chat
- `frontend/lib/api.ts` -- thread arm through getPersonaGroupTurns + sendPersonaGroupMessage signatures

## Key Context

**Why split rooms not a single dropdown:** transcript continuity is the killer. If a PM asks "what did you think of the change?" then switches arms and asks "would that change your weekly usage?", with a dropdown the transcripts intermingle and the second question lacks the context of the first answer. Split rooms = two independent conversations, each with its own history. PMs already think this way ("I want to ask treatment X and control Y").

**Why feedback target_id needs arm suffix:** the feedback log keys flags by `(target_kind=PERSONA_GROUP, target_id=f"{sim_id}/{persona_id}", turn_index)`. With split rooms, T-turn-0 and C-turn-0 are different turns about different (PM-question, agent-answer) pairs -- they MUST get separate feedback. Without the arm suffix in target_id, a thumbs-up on T-turn-0 would also paint thumbs-up on C-turn-0 because both turns share the key. Pre-#98 single-arm sims keep the existing 2-segment target_id for backwards-compat.

**Why log path not turn-level arm tag:** the alternative would be a single log file with arm tagged on each turn, filtered on read. That works but means every read of the log fetches turns from the OTHER arm and discards them -- wasteful at scale. Per-arm path means each chat page reads only the relevant turns. Trade-off: more log files at high persona/sim counts, but Pythia's volumes are low enough this doesn't bite.

**1:1 agent chat is unaffected.** Each AgentInstance.arm is pinned at materialization (#89 identity-continuity invariant), so 1:1 chat already has a known arm context and doesn't need any changes. Only the persona-GROUP chat needed the fix.

## For my cofounder
#98 shipped in PR #104 and is merged to `main` (`bdac59b`). The trickiest invariant is the feedback target_id arm suffix: if you touch persona-group feedback, the join in `list_persona_group_turns` against `latest_flags(target_id=...)` must also pass arm. Tests now pin both transcript isolation and feedback isolation.

#103 (model selection) remains teed up next.
