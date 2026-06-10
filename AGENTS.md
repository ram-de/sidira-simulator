# AGENTS.md — How the Sidira team works with AI agents

This file is read by humans onboarding to the team AND by AI coding agents (Claude Code, Codex, Gemini CLI) before they touch the code. If a convention isn't written down here, it doesn't exist yet — propose it via PR.

---

## The 60-second orientation

1. **Read `CONTEXT.md`** — what just shipped, what's next, what's not yet real
2. **Read `ROADMAP.md`** — phases, critical path, where Phase 2.5 sits
3. **Open the [GitHub Project](https://github.com/users/ram-de/projects/)** — pick the next ticket with status = Next, assigned to you (or unassigned)
4. **Open the relevant repo's directory** — code conventions explained below

If you only have time for one file: it's `CONTEXT.md`.

---

## The three repos

The product name is Sidira. The customer-facing simulator repo is `sidira-simulator`; producer repos are `sidira-personas` and `sidira-crawler`.

| Repo | Run from | Tests |
|---|---|---|
| `sidira-simulator` | `backend/` (uvicorn) + `frontend/` (next dev) | `pytest tests/` in backend; `npx tsc --noEmit` in frontend |
| `sidira-personas` | Python library + CLI (`sidira-personas run`) | `pytest` |
| `sidira-crawler` | Python library + CLI (`sidira-crawler run`) | `pytest` |

The simulator imports personas and crawler as **libraries**, not over IPC. Artifact contract is filesystem-shaped under `local-artifacts/customers/{id}/...` in dev, R2 in prod.

---

## Skills (Claude Code + gstack)

We use [gstack](https://github.com/ram-de/gstack-public) for the slash commands. Both founders install it once: `cd ~/.claude/skills/gstack && ./setup`. After that the commands work in any directory:

| When | Skill | What it does |
|---|---|---|
| Starting any non-trivial chunk of work | `/plan-eng-review` | Locks architecture decisions before code. Single biggest leverage. |
| Per-session working state (shared across founders) | `/pythia-session` | Project-local. Lives in this repo at `.claude/skills/pythia-session/`. Writes to `sessions/<domain>/context.md`, committed to git so the other founder sees state on `git pull`. Named with the `pythia-` prefix to never collide with employer-vault `/session` skills. See full docs in the skill file. |
| At a PR boundary | `/codex` | Cross-model second opinion. Catches formula / type / boundary issues. |
| Before merging a frontend change | `/qa` | Live browser test of the running app. Catches what curl + tests miss. |
| Before declaring a feature done | `/review` | Independent diff review with adversarial pass. |
| At the end of a sprint | `/retro` | Captures lessons. Updates `CONTEXT.md`. |
| New phase or pipeline design | `/etl` (when it applies) | Lifecycle skill. Not Sidira-specific but useful when the work is data-pipeline-shaped. |

### `/pythia-session` — how the shared session model works

`/pythia-session` is the **only** skill of these that's project-local (checked into this repo at `.claude/skills/pythia-session/`). The command keeps the historical `pythia-` prefix to avoid collisions with user-level `/session` skills; do not rename it as part of the Sidira product rename. The others are user-level via gstack. Why project-local for sessions:

- Both founders see the same session state via `git pull`
- No dependency on either founder having an Obsidian vault
- Session content lives at `sessions/<domain>/context.md` in this repo and is committed
- The `pythia-` prefix ensures it never collides with employer-vault `/session` skills

Common flow:
```
/pythia-session new phase-2.5-sampler — implement population_sampler
(work, with continuous updates to sessions/phase-2.5-sampler/context.md)
/pythia-session save                       # commits + pushes the session file
(cofounder picks up next day:)
/pythia-session resume phase-2.5-sampler   # reads the file, continues from "Next Steps"
```

A live example session lives at `sessions/persona-classifier/context.md` — that's the full working state of the Sidira work from the Magic Moment Sprint forward. Read it for context before picking up Phase 2.5.

**Don't run a skill just because it exists.** Each one has a real cost (token + time). Pick by the trigger column above.

---

## Conventions

### Backend (Python)

- **FastAPI + Pydantic** for the schema. Types in `schemas/` are the source of truth; frontend TS types are generated via `npm run gen-types` (calls OpenAPI export).
- **Async everywhere** except for chat clients (sync, wrapped in `asyncio.to_thread`). The simulator's I/O is dominated by LLM calls.
- **Repository Protocol pattern** for data access. Every repo has Postgres + InMemory implementations (`adapters/repositories.py`). New repos follow this shape.
- **No business logic in API routes.** Routes call orchestrators / services. Services are unit-testable without a HTTP layer.
- **Customer-scoped reads/writes.** Every repo method takes `customer_id` and filters by it. No exceptions — Phase 5 multi-tenancy depends on this discipline.
- **`black` + `ruff`** for formatting and linting. Run before commit.

### Frontend (Next.js + TypeScript)

- **App Router** (Next 14+). Client components only when needed; default to server.
- **Inline styles for now.** When we add 5+ pages with shared patterns, we'll lift to CSS modules or a styling lib. Premature abstraction is worse than the duplication today.
- **`lib/api.ts`** is the only place that does `fetch`. Pages call typed wrappers from there.
- **`lib/api-types.ts`** is auto-generated. Don't hand-edit.

### Tests

- Backend: unit + integration via `pytest`; current baseline is hundreds of tests and should stay green. New code lands with tests.
- Frontend: typecheck via `npx tsc --noEmit`. Component tests are not gated yet but welcome.
- Eval tests (regression check on LLM scoring): live in `tests/eval/`. Run manually before any change to the scoring formula.

### Commits

- Conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`. Scope optional.
- One commit per logical change. Atomic. Easy to revert.
- AI-assisted commits get a `Co-Authored-By: Claude <noreply@anthropic.com>` trailer. Not a value judgment, just a record.

### PRs

- One topic per PR. If it grows past ~500 lines, consider splitting.
- **`/codex review` before merge. Every PR. No exceptions.** This is non-negotiable across all three Sidira repos (sidira-simulator, sidira-personas, sidira-crawler). Codex catches the class of bug self-review misses — silent failures, type/boundary issues, inconsistent error paths, off-by-one in stats code, drift between spec docstring and implementation. Previously this rule applied only to schema/scoring/agent-memory changes; the narrow version existed because Codex used to cost real money. It doesn't now. Run it everywhere.
  - If Codex flags `[P1]`: fix before merge. Re-run review until CLEAR.
  - If Codex flags `[P2]`: fix in the same PR if it's a 5-minute change; defer to a follow-up ticket otherwise, but call it out in the PR body.
  - If you're tempted to skip Codex on "trivial" changes (docs-only, one-line typo, tests-only): don't. The 30-second runtime is cheaper than the trust we lose when a "trivial" change breaks something.
- Squash on merge unless the commits are individually meaningful (rare).

### Deploys

- **Frontend:** AWS Amplify auto-builds on every push to `main`. Nothing to do.
- **Backend (api.sidira.ai): manual, and easy to forget.** A merged PR that touches `backend/` is NOT live until someone redeploys the EC2 API. Forgetting looks like a `404 {"detail":"Not Found"}` banner in the live app on the new routes while old ones still work.
- The agent-executable runbook is **`deploy/REDEPLOY.md`** — staleness check, the `SIDIRA_AUTO_MIGRATE` decision when the PR added an Alembic migration, the SSM deploy command, and verification. Point codex (or any agent) at it: `codex exec "Read deploy/REDEPLOY.md and execute the backend redeploy for api.sidira.ai."`
- **Agents: after a backend-touching PR merges, prompt the user to redeploy** with the command above as part of the wrap-up. Don't silently end the session with prod stale.

---

## How we plan and track

- **Strategy + phase specs:** `ROADMAP.md` (in this repo, since the simulator is the integration point)
- **Tickets:** [GitHub Project](https://github.com/users/ram-de/projects/), multi-repo, fields: Phase + Component + Status + Assignee
- **Sprint narrative:** `CONTEXT.md` — updated at the end of every sprint
- **Per-repo `MILESTONES.md`:** stubs pointing back here. Don't add detail to them; it'll get stale.

When you pick up a ticket:
1. Move it to Status = In progress, assign yourself
2. Branch off `main` (`feat/<phase>-<short-desc>` or `fix/<short-desc>`)
3. Land work; PR linked to issue (`Closes #N`)
4. After merge, the Project status auto-flips to Done

---

## How we work with each other

- **Default to async.** Decisions in PRs > decisions in Slack > decisions in DMs.
- **The other founder can pick up any branch / ticket without checking with you.** If something is locked-down personal-work-in-progress, it's on a branch and not in the Project board.
- **No surprises before a demo.** If a customer / investor demo is coming, ping the other founder so they know what to NOT push to `main` that day.
- **Sprint retros are mandatory.** Even when it's just two of us — the lesson capture compounds.

---

## How AI agents should behave on this codebase

- **Read `CONTEXT.md` first.** Don't infer the current state from code; the narrative is the source.
- **Don't update docs from memory of past sessions.** Re-read them. They change.
- **Skills > one-shot prompts.** When a skill applies (per the table above), invoke it.
- **Never push to `main` directly.** Always PR.
- **Always run tests before committing.** `pytest tests/` (<1s) + `npx tsc --noEmit` (~5s). No excuse.
- **Personal scratch notes (Obsidian, etc.) are NOT a source of truth.** If a fact matters to the team, it lives in `CONTEXT.md`, the GitHub Project, or a doc in the repo.

---

## Onboarding a new teammate (founder #2 or future #3)

1. Accept GitHub invite to all 3 repos + the GitHub Project
2. Clone `sidira-simulator`, `sidira-personas`, and `sidira-crawler` to `~/Projects/`
3. Install Claude Code + gstack: `cd ~/.claude/skills/gstack && ./setup`
4. Copy `~/mirofish-ui/.env` (or get Groq key from 1Password) → `sidira-simulator/backend/.env`
5. Set up Postgres (Neon dev instance) — DATABASE_URL in env
6. `backend/`: `python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"`
7. `frontend/`: `npm install`
8. Run the magic moment locally: start backend (`uvicorn ...`) + frontend (`npm run dev`), open `http://127.0.0.1:3000`, submit a hypothesis. If you see a score and 6 agents reacted, you're in.
9. Read `CONTEXT.md`. Then read `sessions/persona-classifier/context.md` for the deeper running state.
10. Pick a ticket from the GitHub Project. Run `/pythia-session new <slug> — <desc>` so I see what you're working on. Ship.

If anything in this file is wrong, fix it in a PR. The file outlives any single conversation.
