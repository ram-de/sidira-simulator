#!/usr/bin/env bash
# Auto-save active pythia-session before context compaction.
# Fires via PreCompact hook; always exits 0 (non-blocking).
# Reads JSON event payload from stdin but does not need its contents.
#
# Works correctly whether Claude Code is running in the main checkout
# or in a git worktree (.claude/worktrees/*).

REPO=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
SCRIPT="$REPO/.claude/skills/pythia-session/scripts/session_state.py"
[[ -f "$SCRIPT" ]] || exit 0

# Detect worktree: resolve the main repo working tree so we can do
# branch operations there. git rev-parse --git-common-dir returns:
#   /main/.git                         (main checkout)
#   /main/.git/worktrees/<name>        (a worktree)
GIT_COMMON=$(git rev-parse --git-common-dir 2>/dev/null) || exit 0
GIT_COMMON=$(cd "$REPO" && cd "$GIT_COMMON" && pwd -P)  # canonicalise relative path

if [[ "$GIT_COMMON" == *"/.git/worktrees/"* ]]; then
  MAIN_REPO="${GIT_COMMON%%/.git/worktrees/*}"
  IN_WORKTREE=1
else
  MAIN_REPO="$REPO"
  IN_WORKTREE=0
fi

# Find exactly one active session. session_state.py uses git rev-parse
# internally, which resolves to $REPO (may be a worktree). That is fine —
# it reads the session files from $REPO/sessions/, which contains the
# edited (uncommitted) version we want to save.
DOMAIN=$(python3 "$SCRIPT" active 2>/dev/null) || exit 0

SESSION_FILE="sessions/$DOMAIN/context.md"

# The authoritative (possibly edited) copy is in $REPO (the worktree or
# main checkout where Claude is actually running).
SRC="$REPO/$SESSION_FILE"
DST="$MAIN_REPO/$SESSION_FILE"
[[ -f "$SRC" ]] || exit 0

# If we're in a worktree, propagate the worktree's edited session file to
# the main repo working tree before committing, so the commit goes on main.
if [[ "$IN_WORKTREE" -eq 1 ]]; then
  # Skip if the worktree's file matches main repo's committed version exactly.
  COMMITTED=$(git -C "$MAIN_REPO" show "HEAD:$SESSION_FILE" 2>/dev/null)
  CURRENT_CONTENT=$(cat "$SRC")
  if [[ "$COMMITTED" == "$CURRENT_CONTENT" ]]; then
    exit 0
  fi
  # Copy worktree's version into the main repo working tree.
  mkdir -p "$(dirname "$DST")"
  cp "$SRC" "$DST"
else
  # Running in main checkout: check for uncommitted changes the normal way.
  if git -C "$MAIN_REPO" diff --quiet HEAD -- "$SESSION_FILE" 2>/dev/null && \
     git -C "$MAIN_REPO" diff --cached --quiet -- "$SESSION_FILE" 2>/dev/null; then
    exit 0
  fi
fi

CURRENT_BRANCH=$(git -C "$MAIN_REPO" branch --show-current 2>/dev/null)

# Branch-hop dance on the MAIN repo (only needed when not in a worktree,
# since in a worktree $MAIN_REPO is always on main).
if [[ -n "$CURRENT_BRANCH" && "$CURRENT_BRANCH" != "main" && "$IN_WORKTREE" -eq 0 ]]; then
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

# Return to original branch in main repo (non-worktree branch-hop only).
if [[ -n "$CURRENT_BRANCH" && "$CURRENT_BRANCH" != "main" && "$IN_WORKTREE" -eq 0 ]]; then
  git -C "$MAIN_REPO" checkout "$CURRENT_BRANCH" 2>/dev/null || true
  git -C "$MAIN_REPO" checkout origin/main -- "$SESSION_FILE" 2>/dev/null || true
fi

exit 0
