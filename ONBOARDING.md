# Sidira — Cofounder Onboarding

Welcome. This doc gets you from "just got the GitHub invite" to "shipped my first PR" in about 90 minutes. You can read it yourself, or paste it to your Claude Code instance and have it walk you through. It's written for both.

> **For Claude:** If the human pasted this and said "help me onboard," your job is to execute the steps below in order, asking the human for credentials and confirmations where noted. Don't skip steps. Don't run destructive commands without asking. After each major step, confirm it worked before moving on.

---

## What Sidira is, in 60 seconds

Sidira simulates how a customer's userbase would react to a proposed product change. A PM submits a hypothesis ("if we add one-tap reorder, weekly orders go up 8%"); Sidira samples agents from a calibrated persona pack, runs each agent's reaction through an LLM, scores the result, and the PM can then chat with each agent to ask why they reacted the way they did. The defining feature is **agent memory** — the agent you chat with is the same entity that simulated, not a re-instantiation.

Three repos:

The product is Sidira. The customer-facing simulator repo is `sidira-simulator`; producer repos are `sidira-personas` and `sidira-crawler`.

| Repo | What it does |
|---|---|
| `sidira-simulator` | Customer-facing app (FE + BE + agent memory + the only UI). This repo. |
| `sidira-personas` | Persona Pack producer (clusters real userbase data into archetypes with weights) |
| `sidira-crawler` | Feature Pack producer (weekly Playwright crawl of customer's product → reverse PRD) |

The simulator is the integration point — strategy, roadmap, and team docs live here.

---

## Step 1 — Accounts and access (5 min, ask the founder)

You need:

- [ ] GitHub `ram-de` access — invite to `sidira-simulator`, `sidira-personas`, `sidira-crawler`, plus the [Sidira GitHub Project](https://github.com/users/ram-de/projects/)
- [ ] Groq API key — for LLM calls. Founder has one at `~/mirofish-ui/.env` they can share, or sign up at https://groq.com (free tier works for now)
- [ ] (Optional, for Postgres work) Neon dev instance credentials — ask founder for the `DATABASE_URL`
- [ ] (Optional, for Anthropic fallback) Anthropic API key

If anything's missing, stop here and ping the founder before proceeding.

---

## Step 2 — Install Claude Code + gstack (10 min)

We use [gstack](https://github.com/garrytan/gstack) for the slash commands `/qa`, `/review`, `/retro`, `/plan-eng-review`, `/codex`. They are required to follow the team's workflow.

```bash
# 1. Install Claude Code (skip if you already have it)
#    https://claude.com/claude-code

# 2. Install bun (required by gstack setup)
curl -fsSL https://bun.sh/install | bash

# 3. Install gstack — one command, ~2 minutes
git clone https://github.com/garrytan/gstack ~/.claude/skills/gstack
PATH="$HOME/.bun/bin:$PATH" bash ~/.claude/skills/gstack/setup
```

Verify by opening Claude Code in any directory and typing `/qa` — you should see the skill load. If it doesn't, re-run `./setup` and check `~/.claude/skills/gstack/` exists.

---

## Step 3 — Clone the three repos (5 min)

```bash
mkdir -p ~/Projects && cd ~/Projects
git clone git@github.com:ram-de/sidira-simulator.git
git clone git@github.com:ram-de/sidira-personas.git
git clone git@github.com:ram-de/sidira-crawler.git
```

If your SSH key isn't set up with GitHub, use HTTPS URLs instead (`https://github.com/ram-de/...`).

---

## Step 4 — Set up the simulator backend (15 min)

The simulator is the main repo. You'll spend most of your time here.

```bash
cd ~/Projects/sidira-simulator/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run the tests — should be green; current baseline is 363 passed / 10 skipped
pytest tests/ -q
```

Expected output is roughly `363 passed, 10 skipped`. If anything fails, check Python version (need 3.11+) and try `pip install -e ".[dev]" --force-reinstall`.

### Environment variables

Create `backend/.env` (it's gitignored):

```bash
# Required
GROQ_API_KEY=gsk_...                                  # from founder or signup
SIDIRA_LOCAL_ARTIFACTS=/Users/<you>/Projects/sidira-simulator/local-artifacts

# Optional
ANTHROPIC_API_KEY=sk-ant-...                          # fallback when Groq 429s
DATABASE_URL=postgresql://...                         # only if doing Phase 5 work; InMemory works for everything else
SIDIRA_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000   # defaults are fine for dev
```

Load them before running the backend with `uvicorn --env-file .env`, or export
them in your shell. Legacy `PYTHIA_*` names still work during the rename, but
new setup should use `SIDIRA_*`.

---

## Step 5 — Set up the simulator frontend (5 min)

```bash
cd ~/Projects/sidira-simulator/frontend
npm install
npx tsc --noEmit            # should pass clean
```

For production deploys, leave `NEXT_PUBLIC_API_BASE` unset so browser traffic
uses the same-origin `/api` proxy. Set Amplify server-side
`SIDIRA_API_BASE_INTERNAL=https://api.sidira.ai/_sidira_web_proxy` and
`SIDIRA_WEB_PROXY_BASIC_AUTH=<base64 username:password>` for the EC2/Caddy web
proxy. Do not put the backend gateway token in Amplify; Caddy adds it
server-side after validating web-proxy Basic Auth. Local development can leave
the proxy default or use direct `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000`.

---

## Step 6 — Run the Magic Moment locally (10 min)

This is the smoke test: a hypothesis goes in, 6 agents react, score comes back. If this works, your setup is good.

**Terminal 1 — backend:**
```bash
cd ~/Projects/sidira-simulator/backend
source .venv/bin/activate
cp .env.example .env   # first run only; add GROQ_API_KEY to .env
uvicorn sidira_simulator.main:app --host 127.0.0.1 --port 8000 --reload --env-file .env
```

**Terminal 2 — frontend:**
```bash
cd ~/Projects/sidira-simulator/frontend
npm run dev
```

Then in a browser:
1. Open http://127.0.0.1:3000
2. Click **Simulations** → **+ New simulation**
3. Pick capability `reorder`
4. Paste a hypothesis: `Adding a one-tap reorder button on the home screen will lift weekly order frequency for engaged DashPass subscribers by 8%.`
5. Click **Run simulation**

Within ~10 seconds you should see a score (something between 20 and 70), three diagnosed weaknesses, three refinement suggestions, and six agent chips. If you see this, you're in.

**If it fails:** check the backend log for CORS errors (means env vars wrong), or `Failed to load capabilities` (means `SIDIRA_LOCAL_ARTIFACTS` is wrong — must point to the dir containing the fixture pack).

---

## Step 7 — Read the team context (15 min)

In this order, in the `sidira-simulator` repo:

1. **`CONTEXT.md`** (top-level) — what just shipped, what's next, what's not yet real. 2-minute read. This is the daily orientation file.
2. **`ROADMAP.md`** (top-level) — strategy, all phases, critical path, and locked decisions for the current phase. Read the "Where we are today" and "What's next" sections at minimum.
3. **`AGENTS.md`** (top-level) — conventions, tools, how the team works with AI agents. Read top-to-bottom.
4. **`sessions/persona-classifier/context.md`** — the full working state of the project from sprint 0 to today (~240 lines). Skim the top, then read "Magic Moment Sprint plan" and the most recent updates. This is the deeper history when you need design rationale or "what did we try and reject."

The `MILESTONES.md` in each of the three repos is a stub — ignore it. Planning consolidated into `ROADMAP.md` + the GitHub Project on 2026-05-21.

---

## Step 8 — Understand the session model (5 min)

We share working state through `git`, not Slack. There's a project-local skill called `/pythia-session` that writes session files into the repo at `sessions/<domain>/context.md`. When you commit + push a session file, the founder sees your state on their next `git pull`. Same the other way.

The skill is at `.claude/skills/pythia-session/` — Claude Code auto-discovers it when you're inside the `sidira-simulator` repo. No install required, it's just there.

Three commands you'll use:

| Command | What it does |
|---|---|
| `/pythia-session new <slug> — <description>` | Starts a new session, creates `sessions/<slug>/context.md` with a template |
| `/pythia-session save` | Stages + commits + pushes the session file. Founder sees it on next pull. |
| `/pythia-session resume <slug>` | Loads an existing session and continues from "Next Steps" |

Naming: `/pythia-session` (not `/session`) because some of us have a different `/session` skill at user level pointing to an employer work vault. The `pythia-` prefix prevents that collision from accidentally writing Sidira state to the wrong place.

---

## Step 9 — Pick up your first task (the actual work starts here)

**Open the GitHub Project:** https://github.com/users/ram-de/projects/

Read `CONTEXT.md` ("What's next") and `ROADMAP.md` ("Where we are today") to learn which phase is currently active — that's the phase your first ticket should come from. Then on the Project board:

1. **Filter by `Phase = <current phase>` AND `Status = Next` or `Backlog`.** Phase = Next means the founder has staged this as do-next-work; Backlog means it's locked but lower priority.
2. **Sort or scan by smallest scope first.** Good starter tickets share three traits:
   - Acceptance criteria are concrete and testable (the ticket says exactly what "done" looks like)
   - Surface area is one file or one route (low blast radius for a first PR)
   - No `Depends on:` block in the body, or the dependency is already merged
3. **Match your background.** Component field tells you `backend` / `frontend` / `schema` / `docs`. A frontend ticket in your first week is fine — Sidira's frontend is small and intentionally low-magic.
4. **Read the body in full.** Especially the "Out of scope" section. The fastest way to derail a first PR is to expand scope past what the ticket asked for.

If nothing in `Status = Next` looks right, ask the founder in the daily check-in which Backlog ticket they'd like pulled forward — that's the cheapest unblock.

To claim it: assign yourself on the issue and move it to `In progress` in the Project board. That's the signal to the founder that you've started.

### Doing the work

```bash
cd ~/Projects/sidira-simulator
git pull                                  # always start with this
git checkout -b feat/2.5-<short-desc>     # one branch per ticket

# Start a session so the founder can see what you're up to
# (Inside Claude Code:)
/pythia-session new <slug> — <one-line desc>

# ... do the work, run tests, commit normally ...
pytest tests/ -q                          # backend tests, must pass
npx tsc --noEmit                          # frontend, if you touched it

# Periodically push your session state so the founder sees progress
/pythia-session save

# When ready for review:
/qa                                       # if you touched frontend
/review                                   # always, before opening a PR
```

Then push the branch and open a PR (linked to the issue: `Closes #NNN` where `NNN` is the issue you claimed).

---

## Step 10 — Conventions cheat sheet

The full version is in `AGENTS.md`. The 90% version:

- **Conventional commits:** `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`
- **One commit per logical change.** Atomic, easy to revert.
- **One topic per PR.** Split if it grows past ~500 lines.
- **`/codex review` at PR boundary** for every PR.
- **`/qa` before merge** for any change that touches the frontend.
- **Never push to `main` directly.** Always PR.
- **AI-assisted commits get `Co-Authored-By: Claude <noreply@anthropic.com>`** trailer — not a value judgment, just a record.
- **Customer-scoped reads/writes:** every repo method takes `customer_id` and filters by it. No exceptions; Phase 5 multi-tenancy depends on this discipline.
- **No business logic in API routes.** Routes call orchestrators / services. Services are unit-testable without the HTTP layer.
- **Inline styles on the frontend for now.** When 5+ pages share patterns, we'll lift to a styling lib. Premature abstraction worse than duplication today.

---

## Step 11 — When you get stuck

| Stuck on | Do this |
|---|---|
| "What was the design decision for X?" | Search `sessions/persona-classifier/context.md` and `ROADMAP.md` first |
| "Why is the code shaped this way?" | `git log -- <file>` + read commit messages. We write detailed commit bodies for a reason. |
| Tests fail and you don't know why | `pytest tests/ -v -x` to stop at first failure with full trace; check it's not an env-var issue |
| Frontend won't connect to backend | CORS — check backend log; verify `SIDIRA_CORS_ORIGINS` matches your frontend origin |
| LLM calls fail with 429 | Groq rate limit — wait 60s, or fall back to Anthropic (set `ANTHROPIC_API_KEY`) |
| Genuinely blocked | Drop a one-line note in your session file's "Next Steps" with `[BLOCKED]` prefix, `/pythia-session save`, then ping founder. They'll see the block context on pull. |

---

## Step 12 — First-week expectations

Don't try to be productive in the first 48 hours. Spend the first day on:
- Running the Magic Moment loop end-to-end and submitting at least three different hypotheses to see how the scoring behaves
- Reading the full `sessions/persona-classifier/context.md` (it's the project's brain)
- Picking the smallest Status = Next ticket on the Project board and shipping it (see Step 9 for how to pick)

By end of week one you should have:
- One PR merged
- A second PR in flight
- A session file in `sessions/<your-slug>/` with active work
- Read `ROADMAP.md` enough to know the current phase, what is shipped, and what is next

---

## Appendix — Quick reference

| File | Purpose | Read frequency |
|---|---|---|
| `ONBOARDING.md` (this file) | One-time setup | Once |
| `CONTEXT.md` | What just shipped, what's next | Every session start |
| `ROADMAP.md` | Strategy, phases, locked decisions | Weekly or before starting a phase |
| `AGENTS.md` | Conventions, skill usage | Once during onboarding, then reference |
| `sessions/<active>/context.md` | Current working state | When picking up someone else's work |
| GitHub Project | Open tickets | Daily |
| `sidira-personas/MILESTONES.md` | Stub — ignore | Never |
| `sidira-crawler/MILESTONES.md` | Stub — ignore | Never |
| `sidira-simulator/MILESTONES.md` | Stub — ignore | Never |
| `sidira-simulator/docs/SEED_ISSUES.md` | One-time Project seed list | Never (historical) |

---

## Welcome aboard

Once you've shipped your first PR, drop a `/pythia-session close` on your session and update `CONTEXT.md` with what you shipped. That marks the end of onboarding. From there, it's just CONTEXT → Project → session → ship, in a loop, forever.
