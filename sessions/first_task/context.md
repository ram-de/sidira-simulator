---
type: session
domain: first_task
status: active
started: 2026-05-22
owner: rmkmar
---

# Session: first_task — onboarding to Pythia

## Goal
Walk through the Pythia onboarding flow (ONBOARDING.md) and pick up enough context to take on a first real ticket.

## In Progress
- [ ] Pick a starter ticket and spin up a dedicated session for it

## Completed
- Steps 1–5: env already provisioned (gstack installed, 3 repos cloned, backend venv + .env present, frontend node_modules present, Python 3.11.5, Node 23)
- Verified backend tests: 60/60 passing
- Verified frontend typecheck: clean (`npx tsc --noEmit`)
- Step 7: Read CONTEXT.md, ROADMAP.md, AGENTS.md
- Step 8: session model understood (this skill, committed to git)
- Step 9 (scout): pulled all 30 open issues on `ram-de/pythia-simulator`

## Next Steps
1. Decide between recommended starter tickets (see Key Context)
2. Once chosen: assign self on the issue, move Project board → In progress, `git checkout -b <branch>`, open a new `/pythia-session new <slug>`
3. (Optional but recommended for muscle memory) Run the Magic Moment locally (Step 6) — submit a hypothesis end-to-end before writing any code

## Key Files
- `ONBOARDING.md`, `CONTEXT.md`, `ROADMAP.md`, `AGENTS.md` — read
- `sessions/persona-classifier/context.md` — deeper running history (skim if blocked on rationale)
- `backend/pythia_simulator/api/agents.py` — target file for #52 if we pick it

## Key Context
- **No Phase 2.5 tickets are open on the board.** CONTEXT/ROADMAP call Phase 2.5 (weighted population sampling) "next", but issues #27–#56 cover Phase 4–10 only. Worth flagging to founder: either Phase 2.5 work hasn't been seeded as tickets yet, or the active phase to pull from is Phase 4 (agent chat UI — the differentiator).
- **Recommended starter: issue #52 — `feat(api): implement get_agent and send_message routes`.** Phase 4 backend. Single file (`backend/pythia_simulator/api/agents.py`). Service + memory layers already exist; just wiring the HTTP edge. No `Depends on:` blockers. Clear acceptance criteria and an explicit Out of scope. Unblocks #53 + #54.
- **Alternative (frontend-flavored): #51 — `feat(frontend): result table grouped by persona on simulation detail page`.** Single page, low blast radius. Good if you want a frontend-first first PR.

## For my cofounder
Onboarding done. Sitting on Step 9 (ticket pick). Leaning toward #52 (Phase 4 API wiring) as the first PR. Heads-up that the Project has no open Phase 2.5 tickets despite ROADMAP saying that's the next phase — want to align on whether 2.5 still gates 4 before I claim #52.
