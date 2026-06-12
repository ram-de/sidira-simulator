---
type: session
domain: phase-7-streamly-crawler
status: active
started: 2026-06-11
owner: ram-de
---

# Session: phase-7-streamly-crawler — walk the Streamly sandbox, synthesize the Feature Pack

## Goal
First-customer (mock) pipeline: crawler MVP chain (#1–#3, done) → import the generated pack into the simulator as the first real customer (#190, done). Next: trigger crawls from the product (#193).

## In Progress
- (nothing — #190 closed with acceptance evidence; #193 is the next pickup)

## Completed
- **Simulator #190 DONE 2026-06-12**: streamly-sandbox 2026-W24 imported as the first crawler-GENERATED customer pack; `latest` pointer written in R2 by the crawler workflow itself.
  - PR #191 (`d7b62c3`): initial import + layered `.gitignore` allowlist + `backend/tests/test_streamly_sandbox_pack.py` (round-trips every capability through `FeaturePackLoader`; structural assertions only — GENERATED, NEVER AUTHORED).
  - Crawler PR #12 (`4245c7b`): `publish_latest` — pointer written only after pack AND diff, no-regress guard for backfills (zero-padded ISO weeks compare as strings). Verified live in synthesize-pack runs 27398818409 + 27400430296.
  - The verification re-dispatch re-synthesized 2026-W24 in R2 (clustering is nondeterministic even at temp 0.0), so PR #192 (`1298bee`) re-imported: final pack is **12 capabilities** (`account_plan` split out of `account`; `help` folded away), `crawl_metadata` consistent (`unassigned_screens: 0`, 48/48 assigned). Honest gate PASS on the exact imported pack (leakage 0/0/0, recall 0.75).
  - Codex review on #192 caught a real crawler bug → crawler PR #13 (`bf9f625`): clustering validation never checked `unassigned ∩ assigned`; repair drops double-listed screens (assignment wins, `cluster.double_listed_repaired` log).
  - R2 snapshot keys are not cleaned on overwrite: re-running the same snapshot leaves stale capability dirs (the run-27400430296 artifact still had `help/`). Import takes manifest + diff + manifest-named capability dirs — **the manifest is the source of truth for pack membership**.
- **Crawler #3 DONE 2026-06-12**: Phase-3 synthesizer (PRs #10, #11). Pack in R2 at `customers/streamly-sandbox/featurepacks/2026-W24/`; honest gate PASS; engine purity (`grep -ri streamly sidira_crawler/` empty) holds.
- Crawler #2 (CI acceptance gate, PR #7) and #1 (generic BFS walker, PR #6) — see git history.

## Next Steps
1. **#193 (ready)**: wire Start crawl — `POST /crawls` dispatches the crawler CI workflow (R2/Groq secrets stay in crawler CI), `GET /crawls/{id}` maps run → status, fire-and-watch UI (no spinners, DESIGN.md §8.6; browser never load-bearing). Open decisions in the ticket: single `crawl.yml` walk→synthesize entry point, GitHub token for dispatch, dispatch→run-id correlation.
2. **#194 (parked behind #193)**: local walker execution — full loop on the dev Mac, `--server-cmd` sandbox, LocalArtifactStore, no CI/cloud creds. Guardrail: a local crawl must not silently overwrite the imported streamly-sandbox fixture.
3. **Crawler #14 (open)**: figma synthesis drops cross-capability transitions — the observed `Manage plan` path from `account` into `account_plan` is absent from the published pack. Generator design change (boundary transitions with external-target marker); needs consumer-schema thought. Re-import the pack wholesale once it lands.
4. Crawler #8 open: replay steps not idempotent (member 19/20).
5. Sandbox backlog parked: #4 public deploy, #5 hostility traits.

## Key Files
- simulator `backend/tests/test_streamly_sandbox_pack.py` — round-trip tests on the generated fixture (pins 2026-W24 × 12 caps)
- simulator `local-artifacts/customers/streamly-sandbox/featurepacks/` — GENERATED, NEVER AUTHORED; re-import from R2, never hand-edit
- simulator `backend/sidira_simulator/api/crawls.py` — `POST /crawls` / `GET /crawls/{id}` 501 stubs (#193 wires them)
- crawler `sidira_crawler/storage.py` — `publish_latest` / `_read_latest`
- crawler `sidira_crawler/synthesis/cluster.py` — validation + coverage repair + `_drop_double_listed`
- crawler `scripts/pack_structure_compare.py` — honest-test judge (sample scope: recall ≥0.75 + zero leakage)

## Key Context
- **GENERATED, NEVER AUTHORED**: pack content is never hand-edited in the simulator repo; codex findings about pack *content* route to crawler tickets (e.g. #14), then re-import.
- Anti-circularity & engine purity remain standing rules; the honest gate re-runs locally fine (judge may read fixtures; synthesis may not).
- **No R2 creds on Ram's Mac** — R2 via crawler CI only; the synthesize-pack artifact is an R2 mirror of the snapshot prefix (may contain stale dirs from earlier writes at the same key).
- Clustering is nondeterministic run-to-run (Groq, temp 0.0): capability count/shape can shift on every re-synthesis; the round-trip test pins whatever the imported manifest says.
- CI date gotcha: pass `crawl_date` explicitly when dispatching after 00:00Z (used 2026-06-12 throughout).
- Codex review discipline: `~/.npm-global/bin/codex review --base main` (off PATH) before declaring any PR done — it caught both crawler #13 and #14.
- gh quirks: GraphQL 401 with ram-de token → use REST (`gh api -X PUT .../merge`).
- Backend api.sidira.ai is manual-deploy; #190/#191/#192 were fixture+test only — no redeploy needed. #193 WILL touch backend routes → redeploy reminder applies.

## For my cofounder
The first real customer is live in the repo: the simulator now serves a Feature Pack that no human wrote — crawled from the Streamly sandbox, synthesized by the crawler, published to R2 with a `latest` pointer the workflow flips itself, imported verbatim, and round-tripped by tests through the same loader the product uses. The review loop earned its keep twice: codex caught a metadata contradiction that turned out to be a real clustering-validation gap (fixed, crawler #13) and a dropped cross-capability path that's now crawler #14. Next: #193 makes the Start crawl button real (fire-and-watch via CI dispatch), then #194 gives us the local dev loop.
