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

**Auto-save on compaction:** The repo's `PreCompact` hook (`.claude/hooks/pre-compact-save-session.sh`) automatically saves the active session before any context compaction (auto or manual). This fires at ~80% context usage (20% remaining). You don't need to call `/pythia-session save` before `/compact` — it happens automatically. The hook is a no-op if no session is active or the session file has no uncommitted changes.

- **Worktree sessions** (the normal case for feature work): the session file is committed directly to the feature branch. It lands on `main` when the PR merges. No branch-hop needed, no conflict risk.
- **Main-checkout sessions** (rare): the branch-hop dance commits the session file to `main` immediately so the cofounder sees it on `git pull`.

## Why "pythia-session" and not just "session"

Other skills named `/session` may exist at user level (e.g., an employer's work-vault skill that writes to `~/vaults/work/sessions/`). Project-local skill resolution depends on cwd, and we never want Sidira work to accidentally land in an employer vault. The unambiguous name eliminates that risk.

## Cross-repo note

This skill lives in the `sidira-simulator` repo but applies to all Sidira work. Run it from the `sidira-simulator` checkout. Session files always go in `sidira-simulator/sessions/`, even when the work touches `sidira-personas` or `sidira-crawler`.

## GitHub context

The Pythia repos use `git@github.com-personal:ram-de/<repo>.git` remotes (in the founder's local dev environment) or `git@github.com:ram-de/<repo>.git` (default). All sessions assume this context — no need to re-confirm.

### GitHub identity (HARD RULE)

When this skill is active, every GitHub write operation against `ram-de/*` repos MUST act as the `ram-de` identity (the repo owner). Do NOT use the founder's personal `rmkmar` identity: it is NOT a collaborator on `ram-de/*` and cannot create PRs there — write calls return `422 "must be a collaborator"`.

Use the `gh` CLI, which is authenticated as `ram-de`. Confirm before any write with `gh auth status` (expect `Active account: true` for `ram-de`). Apply this rule to all writes: `gh pr create`, `gh issue create`, `gh issue comment`, `gh pr merge`, `gh pr comment`, branch pushes, and any other write operation. Read operations are unaffected.

**Outside of `/pythia-session` (e.g. operating on the founder's personal projects):** the `ram-de` identity is scoped exclusively to the three Sidira repos and should not be used elsewhere.

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

Commit and push the current session state so the other founder sees it. **Where the commit lands depends on whether you're in a worktree** — worktree sessions commit to the feature branch, main-checkout sessions branch-hop to `main`. See "Where session updates land" below for the full rationale.

**Steps:**
1. If `<domain>` given: use it as the commit message context
2. If no domain given: resolve active session (same as resume) to get domain; if none found, use "context update"
3. Detect whether you're in a worktree (the `PreCompact` hook uses the same check):
   ```bash
   [ "$(git rev-parse --git-common-dir)" != "$(git rev-parse --git-dir)" ] && echo worktree || echo main-checkout
   ```

**Worktree session (normal case for feature work) — commit directly to the feature branch, NO branch-hop:**
```bash
git add sessions/ && git commit -m "session: <domain> — save" && git push origin "$(git branch --show-current)"
```
The session file rides the PR and lands on `main` when it merges. Tell the user: "Session committed to the feature branch — it'll land on `main` when the PR merges." Done — skip the dance below.

**Main-checkout session (rare) — branch-hop so the file lands on `main` immediately:**
1. Capture the current branch: `CURRENT=$(git branch --show-current)`
2. If `CURRENT != main`: do the branch-hop dance:
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
3. On `main`, commit + push:
   ```bash
   git add sessions/ && git commit -m "session: <domain> — save" && git push origin main
   ```
4. If push fails due to diverged history: `git pull --rebase && git push origin main`
5. If we hopped from a feature branch: `git checkout "$CURRENT"`. The session file on the feature branch is now a stale duplicate of what's on main — discard any leftover diff on that branch so the next merge doesn't conflict:
   ```bash
   git checkout origin/main -- sessions/<domain>/context.md
   ```
6. Tell the user: "Session pushed to main. Cofounder will see this on next `git pull`."

**Why two paths:** the PR #64 conflict happens only when the session file lives on BOTH `main` (via save) AND a feature branch (via in-flight edits) and both sides move. The fix is a single source of truth per session type: branch-only for worktree sessions (lands on main at merge), main-only for main-checkout sessions (the branch-hop dance).

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

## Where session updates land

**Worktree sessions (normal case):** commit the session file directly to the feature branch. The file lands on `main` when the PR merges. This avoids the PR #64 conflict class entirely — `main` never has a diverged copy mid-session. The `/pythia-session save` branch-hop is skipped automatically when running inside a worktree.

**Main-checkout sessions (rare):** the branch-hop dance from `/pythia-session save` still applies — commit on `main` immediately so the cofounder sees it on `git pull`. Don't commit the session file on the feature branch AND on main; that's the PR #64 conflict pattern.

**The PR #64 lesson:** conflicts happen when the session file is committed on BOTH `main` (via save) AND a feature branch (via in-flight edits). The fix is a single source of truth per session type: branch-only for worktree sessions, main-only for main-checkout sessions.

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
