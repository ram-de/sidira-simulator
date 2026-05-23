---
type: session
domain: commit_author
status: active
started: 2026-05-22
owner: ram-de
---

# Session: commit_author — scrub @doordash.com email + rmkmar identity from Pythia git history

## Goal
Move all Pythia repo commits to a clean `ram-de` identity using GitHub's privacy-preserving noreply email, so a future public repo flip (or external collaborator) doesn't expose the founder's work email in commit metadata. Cover both future commits (per-repo git config) and past commits (history rewrite).

## In Progress
- [ ] Force-push rewritten main on `pythia-simulator` to origin (authorized; about to execute).
- [ ] Repeat the rewrite on `pythia-personas` and `pythia-crawler` if their history also contains `@doordash.com` author entries.

## Completed
- [x] **Surveyed the identity split.** GitHub PR author = ram-de (the `github_ramde` MCP server's PAT). Local git commit author = rmkmar (from `git config user.name/email`). The split caused PR #67's commit list to show "rmkmar committed" under a ram-de-merged PR, with `ramkumar.karunanidhi@doordash.com` baked into every commit object on github.com.
- [x] **(A) Per-repo git config on all 3 Pythia repos.** Set `user.name = ram-de` and `user.email = 208066893+ram-de@users.noreply.github.com` in each of `pythia-simulator`, `pythia-personas`, `pythia-crawler`. Global config (`rmkmar / @doordash.com`) is unchanged — work repos and any other personal repos continue to use the global identity. Verified via `git config --global user.name` afterwards.
- [x] **(B) Wrote mailmap + ran git filter-repo on pythia-simulator.** Mailmap at `/tmp/pythia-mailmap.txt` rewrites:
  - `rmkmar <ramkumar.karunanidhi@doordash.com>` → `ram-de <208066893+ram-de@users.noreply.github.com>`
  - `ram-de <karunanidhi.ramkumar@gmail.com>` (GitHub UI merge commits) → same noreply target
  Filter-repo parsed all 78 commits in 0.19s. Local main HEAD moved from `fa14329` → `77186df`. Origin remote was stripped by filter-repo's safety default; re-added pointing at `git@github.com-personal:ram-de/pythia-simulator.git`.
- [x] **Backup tag created.** `pre-history-rewrite-backup` points at the pre-rewrite HEAD (`fa14329`). Recovery is `git reset --hard pre-history-rewrite-backup` IF the force-push hasn't happened yet; once force-push lands, recovery is `git fetch && git reset --hard origin/main`.

## Next Steps
1. **Force-push to origin/main on pythia-simulator.** `git push --force-with-lease origin main`. `--force-with-lease` refuses the push if anyone else (cofounder) pushed to main while we were rewriting — that's the right safety for this workflow.
2. **Tell cofounder before they next pull.** `git fetch && git reset --hard origin/main`. If they have unpushed local commits on main, stash first or cherry-pick onto the new history.
3. **Run the same rewrite on pythia-personas and pythia-crawler** if `git log --format="%ae" | sort -u` on those repos shows @doordash.com entries. Same mailmap, same procedure, same force-push.
4. **After verification (a few days), delete the local backup tag:** `git tag -d pre-history-rewrite-backup`. No rush.

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
