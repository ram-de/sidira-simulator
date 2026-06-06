---
name: pythia-session
description: Project-scoped session state management for Sidira. Tracks in-progress work to <repo>/sessions/<domain>/context.md, committed alongside code so both founders see each other's state via git pull. Named pythia-session (not session) to avoid collision with employer-vault /session skills. Only invoked when explicitly called as /pythia-session.
---

# /pythia-session — Sidira Project Session Skill

## Overview

Every active chunk of Sidira work (sprint, feature, design spike) gets a session file at:

```
<repo>/sessions/<domain>/context.md
```

This file is the source of truth for what is being worked on, what is done, and what is next. **It is committed to git** — both founders see each other's working state on `git pull`. When context resets or a teammate picks up the work, `/pythia-session resume` reads this file and continues from exactly where you left off.

**This skill writes to the repo's `sessions/` directory** (not to any personal Obsidian vault). Sessions are shared, not private. Personal scratch belongs in your own notes app or in `/session-pr`.

**Do NOT invoke this skill unless the user explicitly calls `/pythia-session`.** It does not auto-activate.

**Auto-save on compaction:** The repo's `PreCompact` hook (`.claude/hooks/pre-compact-save-session.sh`) automatically saves the active session to `main` before any context compaction (auto or manual). This fires at ~80% context usage (20% remaining). You don't need to call `/pythia-session save` before `/compact` — it happens automatically. The hook is a no-op if no session is active or the session file has no uncommitted changes.

## Why "pythia-session" and not just "session"

Other skills named `/session` may exist at user level (e.g., an employer's work-vault skill that writes to `~/vaults/work/sessions/`). Project-local skill resolution depends on cwd, and we never want Sidira work to accidentally land in an employer vault. The unambiguous name eliminates that risk.

## Cross-repo note

This skill lives in the `sidira-simulator` repo but applies to all Sidira work. Run it from the `sidira-simulator` checkout. Session files always go in `sidira-simulator/sessions/`, even when the work touches `sidira-personas` or `sidira-crawler`.

## GitHub context

The Pythia repos use `git@github.com-personal:ram-de/<repo>.git` remotes (in the founder's local dev environment) or `git@github.com:ram-de/<repo>.git` (default). All sessions assume this context — no need to re-confirm.

### MCP identity routing (HARD RULE)

When this skill is active, every GitHub MCP call against `ram-de/*` repos MUST go through the `github_ramde` MCP server (i.e. tools named `mcp__github_ramde__*`), NOT the default `github` server. The default `github` server is authenticated as the founder's personal `rmkmar` identity, which is NOT a collaborator on `ram-de/*` and cannot create PRs there — `mcp__github__create_pull_request` against `ram-de/*` returns `422 "must be a collaborator"`. The `github_ramde` server is authenticated as `ram-de` directly (the repo owner) and has full PR/issue/branch permissions.

Apply this rule to: `create_pull_request`, `create_issue`, `update_issue`, `add_issue_comment`, `merge_pull_request`, `create_branch`, `push_files`, and any other write operation. Read operations (`get_pull_request`, `list_issues`, etc.) work on either server, but prefer `github_ramde` while inside a `/pythia-session` for consistency.

**Outside of `/pythia-session` (e.g. operating on the founder's personal projects):** default back to the `github` server (rmkmar identity). The `github_ramde` server is scoped exclusively to the three Sidira repos by its PAT and should not be used elsewhere.

If `mcp__github_ramde__*` tools are NOT in the tool list, fall back to the default `github` server and tell the user: "The `github_ramde` MCP server isn't configured yet — PR creation will fail with 422. Add it per the instructions in `.claude/skills/pythia-session/SKILL.md` § MCP identity routing, then restart Claude Code."

---

## Subcommands

### `/pythia-session new <domain> — <description>`

Start a new session. `domain` is a short slug (e.g., `phase-2.5-sampler`, `agent-chat-ui`).

**Steps:**
1. Create directory `<repo>/sessions/<domain>/` if it doesn't exist
2. Write `context.md` using the template below
3. Tell the user: "Session started. I'll keep `sessions/<domain>/context.md` updated as we work."
4. Begin the work

### `/pythia-session resume [<domain>]`

Resume a session from a prior context.

**Steps:**
1. If `<domain>` given: read `<repo>/sessions/<domain>/context.md` directly
2. If no domain given: run `python3 <repo>/.claude/skills/pythia-session/scripts/session_state.py active`
   - Exit 0 (one active) → auto-resume that session without asking
   - Exit 1 (none active) → ask user which session or if they want to start new
   - Exit 2 (multiple active) → print the list and ask which to resume
3. Read the file, announce: "Resuming session `<domain>`. Last state: [In Progress items]. Next steps: [Next Steps items]."
4. Continue the work from Next Steps

### `/pythia-session save [<domain>]`

Commit and push the current session state so the other founder sees it. **Session commits always land on `main`, never on a feature branch** — see "Session updates land on main" below for why.

**Steps:**
1. If `<domain>` given: use it as the commit message context
2. If no domain given: resolve active session (same as resume) to get domain; if none found, use "context update"
3. Capture the current branch: `CURRENT=$(git branch --show-current)`
4. If `CURRENT != main`: do the branch-hop dance:
   ```bash
   # Stash only the session file (leave code changes alone on the feature branch)
   git stash push -m "pythia-session-save" sessions/
   git checkout main
   git pull --rebase origin main
   git stash pop
   # If pop produces a conflict on the session file, take ours (the just-edited state):
   git checkout --theirs sessions/<domain>/context.md
   git add sessions/<domain>/context.md
   ```
5. On `main`, commit + push:
   ```bash
   git add sessions/ && git commit -m "session: <domain> — save" && git push origin main
   ```
6. If push fails due to diverged history: `git pull --rebase && git push origin main`
7. If we hopped from a feature branch: `git checkout "$CURRENT"`. The session file on the feature branch is now a stale duplicate of what's on main — discard any leftover diff on that branch so the next merge doesn't conflict:
   ```bash
   git checkout origin/main -- sessions/<domain>/context.md
   ```
8. Tell the user: "Session pushed to main. Cofounder will see this on next `git pull`."

**Why the dance:** if the session file lives on both `main` (via `/pythia-session save`) and a feature branch (via in-flight edits), merging the PR creates a conflict every time both sides have moved. Keeping session commits exclusively on `main` removes that whole class of conflict. We learned this the hard way during PR #64.

### `/pythia-session list`

Run: `python3 <repo>/.claude/skills/pythia-session/scripts/session_state.py list`

Print the output. Offer to resume any active session.

### `/pythia-session close [<domain>]`

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

## Session updates land on main

**Session file commits always go on `main`, never on a feature branch.** The file itself is just a working-tree artifact — you can edit it on any branch during work — but every `/pythia-session save` (and the close commit) must hop to `main` first via the dance in `/pythia-session save` above.

The reason: code goes through PRs (audit trail, codex review, conflict isolation) but the session file is conversation state — both founders need to see it land immediately, and gating it behind a PR defeats the point. Committing it on a feature branch AND on main creates a guaranteed merge conflict every time the PR merges (we hit this on PR #64). Single-source-of-truth on main avoids that whole class of friction.

**If you're mid-edit on a feature branch and want to save:** the `save` subcommand handles the hop automatically. Don't `git add` the session file on the feature branch yourself.

**If a stray session-file diff is sitting on a feature branch at PR-merge time:** discard it before merging. The version on main is authoritative.

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

User: `/pythia-session new phase-2.5-sampler — implement population_sampler with largest-remainder`

You:
1. Write `<repo>/sessions/phase-2.5-sampler/context.md` with the template
2. Set `owner` to whichever founder is starting the session
3. Say: "Session started. I'll keep `sessions/phase-2.5-sampler/context.md` updated as we work."
4. Begin the work
5. After completing each task: move to Completed, add next to In Progress, then `/pythia-session save` so cofounder can see progress

---

## Example: Cofounder picks up the session

Cofounder: `/pythia-session resume phase-2.5-sampler`

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

`sessions/` is intentionally COMMITTED to git. That's the whole point — both founders see the same state. If you have personal-scratch notes you don't want shared, those belong in your own notes app or in your user-level `/session-pr`, NOT in `<repo>/sessions/`.

---

## Separation from other session skills

If you also use the user-level `/session-pr` skill at `~/.claude/skills/session-pr/`, it writes to your personal Obsidian vault and is private. Likewise, an employer-vault `/session` at `~/.claude/skills/session/` writes to work scratch. None of these collide with `/pythia-session`:

```
/pythia-session  (this one)  → <repo>/sessions/                  Pythia, shared via git
/session-pr      (personal)  → ~/vaults/personal/sessions/       personal, private
/session         (employer)  → ~/vaults/work/sessions/           employer, private
```

When working on Pythia, prefer `/pythia-session` so your cofounder can pick up.
