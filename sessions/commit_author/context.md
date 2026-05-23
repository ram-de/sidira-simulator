---
type: session
domain: commit_author
status: closed
started: 2026-05-22
closed: 2026-05-22
owner: ram-de
---

# Session: commit_author — scrub @doordash.com email + rmkmar identity from Pythia git history

## Goal
Move all Pythia repo commits to a clean `ram-de` identity using GitHub's privacy-preserving noreply email, so a future public repo flip (or external collaborator) doesn't expose the founder's work email in commit metadata. Cover both future commits (per-repo git config) and past commits (history rewrite).

## In Progress
— session complete. All 3 Pythia repos now have ram-de/noreply identity across full history. Cofounder still needs a `git fetch && git reset --hard origin/main` on their next pull (see "For my cofounder" below).

## Completed
- [x] **Surveyed the identity split.** GitHub PR author = ram-de (the `github_ramde` MCP server's PAT). Local git commit author = rmkmar (from `git config user.name/email`). The split caused PR #67's commit list to show "rmkmar committed" under a ram-de-merged PR, with `ramkumar.karunanidhi@doordash.com` baked into every commit object on github.com.
- [x] **(A) Per-repo git config on all 3 Pythia repos.** Set `user.name = ram-de` and `user.email = 208066893+ram-de@users.noreply.github.com` in each of `pythia-simulator`, `pythia-personas`, `pythia-crawler`. Global config (`rmkmar / @doordash.com`) is unchanged — work repos and any other personal repos continue to use the global identity. Verified via `git config --global user.name` afterwards.
- [x] **(B) Wrote mailmap + ran git filter-repo on pythia-simulator.** Mailmap at `/tmp/pythia-mailmap.txt` rewrites:
  - `rmkmar <ramkumar.karunanidhi@doordash.com>` → `ram-de <208066893+ram-de@users.noreply.github.com>`
  - `ram-de <karunanidhi.ramkumar@gmail.com>` (GitHub UI merge commits) → same noreply target
  Filter-repo parsed all 78 commits in 0.19s. Local main HEAD moved from `fa14329` → `77186df`. Origin remote was stripped by filter-repo's safety default; re-added pointing at `git@github.com-personal:ram-de/pythia-simulator.git`.
- [x] **Backup tag created.** `pre-history-rewrite-backup` points at the pre-rewrite HEAD on each repo. Recovery is `git reset --hard pre-history-rewrite-backup` IF the force-push hasn't happened yet; once force-push lands, recovery is `git fetch && git reset --hard origin/main`.
- [x] **Force-push to origin succeeded on all 3 Pythia repos.**
  - `pythia-simulator`: `fa14329` → `4319d60` (78 commits + session commit)
  - `pythia-personas`: `31db543` → `befdcf1` (13 commits)
  - `pythia-crawler`: `facfe4e` → `7fff2f9` (4 commits)
  All three used `--force-with-lease` (refuses if origin moved during the rewrite — none had moved). `filter-repo` strips origin by default; re-added pointing at the `git@github.com-personal:ram-de/<repo>.git` SSH URL on each.
- [x] **Session lessons captured for future history rewrites:**
  1. `filter-repo` strips the origin remote by default — re-add it before pushing.
  2. `--force-with-lease` fails immediately after a fresh `filter-repo` because the lease check has no fetched view of the new-remote-vs-old-remote. `git fetch origin main` first, THEN `git push --force-with-lease`.
  3. Claude Code's auto-mode classifier blocks force-push to main without explicit in-chat authorization, even when the broader operation was authorized earlier. Get explicit "execute the push" before running.
  4. `--global` git config vs `--local` matters here — per-repo scope is the difference between leaking your new identity into work commits or not. Always verify with `git config --global user.email` after a per-repo identity setup.

## Next Steps
— session complete.

**Carryover housekeeping (not blocking, do whenever):**
1. **Tell cofounder before their next pull on any Pythia repo.** Recovery is `git fetch && git reset --hard origin/main` per repo. If they have unpushed local commits on main, stash first.
2. **After a few days of verifying GitHub is happy with the rewritten history, delete the local backup tags** on each of the 3 repos: `git tag -d pre-history-rewrite-backup`. Doesn't block anything; just cleanup.
3. **Delete the mailmap + origin-backup scratch files** when convenient: `rm /tmp/pythia-mailmap.txt /tmp/pythia-origin-backup.txt`.

## Key Files
- `/tmp/pythia-mailmap.txt` — the rewrite mapping. Safe to delete after all 3 repos are processed.
- `/tmp/pythia-origin-backup.txt` — backed-up origin URL since filter-repo strips it. Safe to delete.

## Key Context
- **Why noreply email:** `208066893+ram-de@users.noreply.github.com` is GitHub's privacy-preserving format. The leading number is ram-de's GitHub user id (208066893), so the commit is still attributable to that GitHub account (shows up in the contributions graph, links to the profile), but the email itself is a github.com-owned address that doesn't leak anything personal. Two birds: identity stays correct, real email stays hidden.
- **Why per-repo config (not --global):** the founder's primary identity on this machine is `rmkmar @ doordash.com` (the work account). A global change would have leaked ram-de into work commits. Per-repo config is the precise scope: it only applies inside `.git/config` of each Pythia checkout, and git's config precedence is `local > global > system` — so anywhere outside the 3 Pythia repos, the global config still wins.
- **What history rewrite preserves:** all 78 commits remain, with the same messages, same diffs, same merge structure, same timestamps, same DAG. ONLY the author email + the resulting SHAs changed. `git diff pre-history-rewrite-backup..HEAD` should print zero file differences (only commit metadata).
- **What's "lost":** old commit SHAs become unreachable from any live branch after the force-push. They still exist in GitHub's cache (typically 90+ days) and in the local objects database until `git gc` runs, but no ref points at them. PR review threads on github.com that anchor comments to specific commit SHAs still load via GitHub's cache, but their "this commit" links may show as detached.
- **PRs themselves stay intact** — GitHub keeps PR objects (titles, descriptions, review comments, merge metadata) forever. Only the commit-anchor URLs go stale.
- **Why I (the AI agent) didn't do the force-push directly:** Claude Code's auto-mode classifier blocks force-push to main even when the user has authorized the rewrite. "Authorize the rewrite" is not the same as "authorize the destructive remote operation that propagates it." The user has to type the push command themselves OR explicitly authorize it in chat (which they did this turn).

## For my cofounder

I rewrote all the git history on `pythia-simulator` (and shortly on the other two Pythia repos) to remove my work email (@doordash.com) from the commit metadata and consolidate all commits under the `ram-de` identity with GitHub's privacy-preserving noreply email. The repo content (files, code, README, docs) is unchanged — only commit SHAs and author emails moved.

**Before you next pull, do this:**
```bash
cd ~/Projects/pythia-simulator   # or wherever you cloned
# If you have any uncommitted local changes, stash first:
git stash push -u -m "pre-rewrite-stash"
# Then reset to the new history:
git fetch origin
git reset --hard origin/main
# If you stashed, recover your changes (may need to re-apply manually if conflicts):
git stash pop
```

If you had any local branches (other than `main`), they'll point at the OLD pre-rewrite commits. You'll either need to rebase them onto the new main (`git rebase --onto origin/main <old-base> <branch>`) or just discard them if they were stale.

Sorry for the friction — one-time cost to keep my work email out of a (potentially-future-public) git log.
