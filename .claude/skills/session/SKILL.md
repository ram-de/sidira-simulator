---
name: session
description: Project-scoped session state management for Pythia. Tracks in-progress work to <repo>/sessions/<domain>/context.md, committed alongside code so both founders see each other's state via git pull. Project-local variant of the personal /session-pr skill. Only invoked when explicitly called as /session.
---

# /session — Pythia Project Session Skill

## Overview

Every active chunk of Pythia work (sprint, feature, design spike) gets a session file at:

```
<repo>/sessions/<domain>/context.md
```

This file is the source of truth for what is being worked on, what is done, and what is next. **It is committed to git** — both founders see each other's working state on `git pull`. When context resets or a teammate picks up the work, `/session resume` reads this file and continues from exactly where you left off.

**This skill writes to the repo's `sessions/` directory** (not to any personal Obsidian vault). Sessions are shared, not private. Personal scratch belongs in your own notes app.

**Do NOT invoke this skill unless the user explicitly calls `/session`.** It does not auto-activate.

## Cross-repo note

This skill lives in the `pythia-simulator` repo but applies to all Pythia work. Run it from the `pythia-simulator` checkout. Session files always go in `pythia-simulator/sessions/`, even when the work touches `pythia-personas` or `pythia-crawler`.

## GitHub context

The Pythia repos use `git@github.com-personal:ram-de/<repo>.git` remotes. When creating PRs from a session, use `mcp__github__create_pull_request` (which is configured against `ram-de/*`). All sessions assume this context — no need to re-confirm.

---

## Subcommands

### `/session new <domain> — <description>`

Start a new session. `domain` is a short slug (e.g., `phase-2.5-sampler`, `agent-chat-ui`).

**Steps:**
1. Create directory `<repo>/sessions/<domain>/` if it doesn't exist
2. Write `context.md` using the template below
3. Tell the user: "Session started. I'll keep `sessions/<domain>/context.md` updated as we work."
4. Begin the work

### `/session resume [<domain>]`

Resume a session from a prior context.

**Steps:**
1. If `<domain>` given: read `<repo>/sessions/<domain>/context.md` directly
2. If no domain given: run `python3 <repo>/.claude/skills/session/scripts/session_state.py active`
   - Exit 0 (one active) → auto-resume that session without asking
   - Exit 1 (none active) → ask user which session or if they want to start new
   - Exit 2 (multiple active) → print the list and ask which to resume
3. Read the file, announce: "Resuming session `<domain>`. Last state: [In Progress items]. Next steps: [Next Steps items]."
4. Continue the work from Next Steps

### `/session save [<domain>]`

Commit and push the current session state (and any other in-flight changes) so the other founder sees them.

**Steps:**
1. If `<domain>` given: use it as the commit message context
2. If no domain given: resolve active session (same as resume) to get domain; if none found, use "context update"
3. Run:
   ```bash
   git add sessions/ && git commit -m "session: <domain> — save" && git push
   ```
4. If push fails due to diverged history: `git pull --rebase && git push`
5. Tell the user: "Session pushed. Cofounder will see this on next `git pull`."

### `/session list`

Run: `python3 <repo>/.claude/skills/session/scripts/session_state.py list`

Print the output. Offer to resume any active session.

### `/session close [<domain>]`

Mark the session as done. Roll lasting decisions / shipped artifacts into `CONTEXT.md` (team-shared sprint narrative).

**Steps:**
1. Resolve domain (same as resume)
2. Update `status: active` → `status: closed` in frontmatter
3. Set `closed: <today's date>` in frontmatter
4. Move all In Progress items to Completed
5. Clear Next Steps (or replace with "— session complete")
6. **Decide whether to update `CONTEXT.md`:**
   - **Significant** = session shipped to `main` AND has lasting impact on roadmap → update `CONTEXT.md`'s "What just shipped" and "Lessons" sections
   - **Pure exploration** with no shipped output → leave `CONTEXT.md` alone, just close the session
7. Commit and push (`session: <domain> — close`)

---

## Continuous Updates During Work

**After every significant action, update the session file immediately.** Do not batch updates.

### When to update:

| Event | What to update |
|-------|---------------|
| Task completed | Move item from In Progress → Completed |
| New task started | Add to In Progress |
| Decision made | Add to Key Context |
| File created/modified | Add to Key Files |
| Blocker found | Add to Next Steps with `[BLOCKED]` prefix |
| Next logical step identified | Add to Next Steps |

### How to update:

Use the **Edit tool** directly on `<repo>/sessions/<domain>/context.md`. Do not rewrite the whole file — make targeted edits to the relevant section.

---

## Session File Template

```markdown
---
type: session
domain: <domain>
status: active
started: <YYYY-MM-DD>
owner: <github-username or name>
---

# Session: <domain> — <description>

## Goal
<one sentence description of what this session is for>

## In Progress
- [ ] <current task>

## Completed
(nothing yet)

## Next Steps
1. <next action>

## Key Files
(none yet)

## Key Context
(none yet)

## For my cofounder
<short note: where I left off, anything you should know if you pick this up>
```

---

## Example: Starting a Phase 2.5 sub-session

User: `/session new phase-2.5-sampler — implement population_sampler with largest-remainder`

You:
1. Write `<repo>/sessions/phase-2.5-sampler/context.md` with the template
2. Set `owner` to whichever founder is starting the session
3. Say: "Session started. I'll keep `sessions/phase-2.5-sampler/context.md` updated as we work."
4. Begin the work
5. After completing each task: move to Completed, add next to In Progress, then `/session save` so cofounder can see progress

---

## Example: Cofounder picks up the session

Cofounder: `/session resume phase-2.5-sampler`

Claude (on cofounder's machine):
1. Read `<repo>/sessions/phase-2.5-sampler/context.md`
2. Say: "Resuming session `phase-2.5-sampler` (owned by Ram). In Progress: implement largest_remainder() math. Next: write the unit tests for the 6-persona × pop=1000 case."
3. Continue from Next Steps — no re-explanation needed

The cofounder may want to update `owner:` if they're taking over.

---

## Vault Structure

```
<repo>/
├── sessions/             ← live working scratch (this skill writes here, GIT-COMMITTED)
│   └── <domain>/
│       └── context.md
├── ROADMAP.md            ← strategy, phases (long-lived)
├── CONTEXT.md            ← cross-session sprint narrative (updated on session close)
└── AGENTS.md             ← team conventions
```

`sessions/` is intentionally COMMITTED to git. That's the whole point — both founders see the same state. If you have personal-scratch notes you don't want shared, those belong in your own notes app, NOT in `sessions/`.

---

## Separation from /session-pr (personal vault)

If you also use the user-level `/session-pr` skill at `~/.claude/skills/session-pr/`, it writes to your personal Obsidian vault and is private. The two don't collide:

```
/session    (this one)  → <repo>/sessions/     project-scoped, shared via git
/session-pr (your personal) → ~/vaults/personal/sessions/   personal, private
```

When working on Pythia, prefer `/session` so your cofounder can pick up.
