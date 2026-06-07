#!/usr/bin/env bash
# Auto-save active pythia-session(s) before context compaction.
# Fires via PreCompact hook; always exits 0 (non-blocking).
# Reads JSON event payload from stdin but does not need its contents.
#
# Worktree sessions: commit session file(s) directly to the feature branch.
# The session file lands on main when the PR merges — no branch-hop needed.
#
# Main-checkout sessions (no worktree): use the branch-hop dance to commit
# on main immediately so the cofounder sees it on next git pull.
#
# Multiple active sessions: EVERY active session with uncommitted changes is
# saved. A PreCompact hook runs non-interactively (no TTY), so it cannot ask
# which session to keep — saving them all is the only loss-free policy. (The
# old hook resolved exactly one active session and silently no-op'd whenever
# zero or many were active, so autosave never ran with >1 session open.)

REPO=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
SCRIPT="$REPO/.claude/skills/pythia-session/scripts/session_state.py"
[[ -f "$SCRIPT" ]] || exit 0

# Detect a linked worktree by comparing the two git dirs (same test the
# /pythia-session save flow uses). In a linked worktree, --git-dir is the
# per-worktree .git/worktrees/<name>, while --git-common-dir is always the main
# repo's .git — so they differ only in a worktree. (Checking --git-common-dir
# for "/.git/worktrees/" never matches, because the common dir is by definition
# the shared .git, not the per-worktree dir.)
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null) || exit 0
GIT_DIR=$(cd "$REPO" && cd "$GIT_DIR" && pwd -P)
GIT_COMMON=$(git rev-parse --git-common-dir 2>/dev/null) || exit 0
GIT_COMMON=$(cd "$REPO" && cd "$GIT_COMMON" && pwd -P)

if [[ "$GIT_DIR" != "$GIT_COMMON" ]]; then
  # Linked worktree: --git-common-dir is <main-repo>/.git.
  MAIN_REPO="${GIT_COMMON%/.git}"
  IN_WORKTREE=1
else
  MAIN_REPO="$REPO"
  IN_WORKTREE=0
fi

# Collect ALL active sessions. session_state.py prints one domain per line and
# exits 0 (exactly one active), 1 (none), or 2 (multiple active). Treat 0 and 2
# the same: save every active session that has uncommitted changes. Exit 1 (or
# any other non-zero) means there is nothing to save.
ACTIVE_OUT=$(python3 "$SCRIPT" active 2>/dev/null)
ACTIVE_RC=$?
if [[ "$ACTIVE_RC" -ne 0 && "$ACTIVE_RC" -ne 2 ]]; then
  exit 0
fi

# Of the active sessions, keep only those whose file has uncommitted changes
# (working-tree or staged) relative to REPO — whose working tree reflects the
# branch we would commit on in either mode.
DIRTY_FILES=()
DIRTY_DOMAINS=()
while IFS= read -r DOMAIN; do
  [[ -n "$DOMAIN" ]] || continue
  SESSION_FILE="sessions/$DOMAIN/context.md"
  [[ -f "$REPO/$SESSION_FILE" ]] || continue
  if git -C "$REPO" diff --quiet HEAD -- "$SESSION_FILE" 2>/dev/null && \
     git -C "$REPO" diff --cached --quiet -- "$SESSION_FILE" 2>/dev/null; then
    continue  # no changes for this session
  fi
  DIRTY_FILES+=("$SESSION_FILE")
  DIRTY_DOMAINS+=("$DOMAIN")
done <<< "$ACTIVE_OUT"

# Nothing changed across any active session → no-op.
[[ "${#DIRTY_FILES[@]}" -gt 0 ]] || exit 0

# Commit message lists the saved domains (comma-separated).
DOMAIN_LIST=$(IFS=,; echo "${DIRTY_DOMAINS[*]}")
COMMIT_MSG="session: $DOMAIN_LIST — auto-save (pre-compact)"

# ── WORKTREE PATH ─────────────────────────────────────────────────────────────
# Commit session file(s) directly to the feature branch in the worktree.
# No branch-hop: the file lands on main when the PR merges.
#
# Commit with an explicit pathspec (a partial commit) so the autosave captures
# ONLY the session files — never any unrelated code the user happened to have
# staged when compaction fired. Other staged/unstaged work is left untouched.
if [[ "$IN_WORKTREE" -eq 1 ]]; then
  git -C "$REPO" commit -m "$COMMIT_MSG" -- "${DIRTY_FILES[@]}" 2>/dev/null || true
  # Push to the remote feature branch so the cofounder can see it.
  git -C "$REPO" push origin HEAD 2>/dev/null || true
  exit 0
fi

# ── MAIN-CHECKOUT PATH ────────────────────────────────────────────────────────
# Branch-hop dance: commit session file(s) on main so the cofounder sees them
# immediately on git pull. Only needed when working in the main checkout.
CURRENT_BRANCH=$(git -C "$MAIN_REPO" branch --show-current 2>/dev/null)

if [[ -n "$CURRENT_BRANCH" && "$CURRENT_BRANCH" != "main" ]]; then
  git -C "$MAIN_REPO" stash push -m "pre-compact-session-save" -- "sessions/" 2>/dev/null || exit 0
  git -C "$MAIN_REPO" checkout main 2>/dev/null || { git -C "$MAIN_REPO" stash pop 2>/dev/null; exit 0; }
  git -C "$MAIN_REPO" pull --rebase origin main 2>/dev/null || true
  git -C "$MAIN_REPO" stash pop 2>/dev/null || exit 0
fi

# Partial commit (explicit pathspec) so only the session files are committed,
# never unrelated staged work.
git -C "$MAIN_REPO" commit -m "$COMMIT_MSG" -- "${DIRTY_FILES[@]}" 2>/dev/null && \
  git -C "$MAIN_REPO" push origin main 2>/dev/null || true

if [[ -n "$CURRENT_BRANCH" && "$CURRENT_BRANCH" != "main" ]]; then
  git -C "$MAIN_REPO" checkout "$CURRENT_BRANCH" 2>/dev/null || true
  git -C "$MAIN_REPO" checkout origin/main -- "${DIRTY_FILES[@]}" 2>/dev/null || true
fi

exit 0
