#!/usr/bin/env bash
# Auto-save active pythia-session before context compaction.
# Fires via PreCompact hook; always exits 0 (non-blocking).
# Reads JSON event payload from stdin but does not need its contents.

REPO=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
SCRIPT="$REPO/.claude/skills/pythia-session/scripts/session_state.py"
[[ -f "$SCRIPT" ]] || exit 0

# Find exactly one active session (exit 0 = found one, 1 = none, 2 = multiple)
DOMAIN=$(python3 "$SCRIPT" active 2>/dev/null) || exit 0

SESSION_FILE="sessions/$DOMAIN/context.md"
[[ -f "$REPO/$SESSION_FILE" ]] || exit 0

# Nothing to do if the session file has no uncommitted changes
if git -C "$REPO" diff --quiet HEAD -- "$SESSION_FILE" 2>/dev/null && \
   git -C "$REPO" diff --cached --quiet -- "$SESSION_FILE" 2>/dev/null; then
  exit 0
fi

CURRENT=$(git -C "$REPO" branch --show-current 2>/dev/null)

# Branch-hop dance: commit session file on main, not on a feature branch
if [[ -n "$CURRENT" && "$CURRENT" != "main" ]]; then
  git -C "$REPO" stash push -m "pre-compact-session-save" -- "sessions/" 2>/dev/null || exit 0
  git -C "$REPO" checkout main 2>/dev/null || { git -C "$REPO" stash pop 2>/dev/null; exit 0; }
  git -C "$REPO" pull --rebase origin main 2>/dev/null || true
  git -C "$REPO" stash pop 2>/dev/null || exit 0
fi

git -C "$REPO" add "$SESSION_FILE" 2>/dev/null || true
if ! git -C "$REPO" diff --cached --quiet -- "$SESSION_FILE" 2>/dev/null; then
  git -C "$REPO" commit -m "session: $DOMAIN — auto-save (pre-compact)" 2>/dev/null && \
    git -C "$REPO" push origin main 2>/dev/null || true
fi

# Return to the original branch and sync session file from main
if [[ -n "$CURRENT" && "$CURRENT" != "main" ]]; then
  git -C "$REPO" checkout "$CURRENT" 2>/dev/null || true
  git -C "$REPO" checkout origin/main -- "$SESSION_FILE" 2>/dev/null || true
fi

exit 0
