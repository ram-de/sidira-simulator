#!/usr/bin/env bash
# Auto-save active pythia-session before context compaction.
# Fires via PreCompact hook; always exits 0 (non-blocking).
# Reads JSON event payload from stdin but does not need its contents.
#
# Worktree sessions: commit session file directly to the feature branch.
# The session file lands on main when the PR merges — no branch-hop needed.
#
# Main-checkout sessions (no worktree): use the branch-hop dance to commit
# on main immediately so the cofounder sees it on next git pull.

REPO=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
SCRIPT="$REPO/.claude/skills/pythia-session/scripts/session_state.py"
[[ -f "$SCRIPT" ]] || exit 0

# Detect worktree via git-common-dir.
# In a worktree: .git/worktrees/<name>  →  strip to get main repo root.
GIT_COMMON=$(git rev-parse --git-common-dir 2>/dev/null) || exit 0
GIT_COMMON=$(cd "$REPO" && cd "$GIT_COMMON" && pwd -P)

if [[ "$GIT_COMMON" == *"/.git/worktrees/"* ]]; then
  MAIN_REPO="${GIT_COMMON%%/.git/worktrees/*}"
  IN_WORKTREE=1
else
  MAIN_REPO="$REPO"
  IN_WORKTREE=0
fi

# Find exactly one active session (status: active in frontmatter).
DOMAIN=$(python3 "$SCRIPT" active 2>/dev/null) || exit 0

SESSION_FILE="sessions/$DOMAIN/context.md"
[[ -f "$REPO/$SESSION_FILE" ]] || exit 0

# ── WORKTREE PATH ─────────────────────────────────────────────────────────────
# Commit session file directly to the feature branch in the worktree.
# No branch-hop: the file lands on main when the PR merges.
if [[ "$IN_WORKTREE" -eq 1 ]]; then
  if git -C "$REPO" diff --quiet HEAD -- "$SESSION_FILE" 2>/dev/null && \
     git -C "$REPO" diff --cached --quiet -- "$SESSION_FILE" 2>/dev/null; then
    exit 0
  fi
  git -C "$REPO" add "$SESSION_FILE" 2>/dev/null || true
  if ! git -C "$REPO" diff --cached --quiet -- "$SESSION_FILE" 2>/dev/null; then
    git -C "$REPO" commit -m "session: $DOMAIN — auto-save (pre-compact)" 2>/dev/null || true
    # Push to the remote feature branch so the cofounder can see it.
    git -C "$REPO" push origin HEAD 2>/dev/null || true
  fi
  exit 0
fi

# ── MAIN-CHECKOUT PATH ────────────────────────────────────────────────────────
# Branch-hop dance: commit session file on main so the cofounder sees it
# immediately on git pull. Only needed when working in the main checkout.
if git -C "$MAIN_REPO" diff --quiet HEAD -- "$SESSION_FILE" 2>/dev/null && \
   git -C "$MAIN_REPO" diff --cached --quiet -- "$SESSION_FILE" 2>/dev/null; then
  exit 0
fi

CURRENT_BRANCH=$(git -C "$MAIN_REPO" branch --show-current 2>/dev/null)

if [[ -n "$CURRENT_BRANCH" && "$CURRENT_BRANCH" != "main" ]]; then
  git -C "$MAIN_REPO" stash push -m "pre-compact-session-save" -- "sessions/" 2>/dev/null || exit 0
  git -C "$MAIN_REPO" checkout main 2>/dev/null || { git -C "$MAIN_REPO" stash pop 2>/dev/null; exit 0; }
  git -C "$MAIN_REPO" pull --rebase origin main 2>/dev/null || true
  git -C "$MAIN_REPO" stash pop 2>/dev/null || exit 0
fi

git -C "$MAIN_REPO" add "$SESSION_FILE" 2>/dev/null || true
if ! git -C "$MAIN_REPO" diff --cached --quiet -- "$SESSION_FILE" 2>/dev/null; then
  git -C "$MAIN_REPO" commit -m "session: $DOMAIN — auto-save (pre-compact)" 2>/dev/null && \
    git -C "$MAIN_REPO" push origin main 2>/dev/null || true
fi

if [[ -n "$CURRENT_BRANCH" && "$CURRENT_BRANCH" != "main" ]]; then
  git -C "$MAIN_REPO" checkout "$CURRENT_BRANCH" 2>/dev/null || true
  git -C "$MAIN_REPO" checkout origin/main -- "$SESSION_FILE" 2>/dev/null || true
fi

exit 0
