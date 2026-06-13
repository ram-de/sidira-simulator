---
type: session
domain: phase-7-streamly-crawler
status: active
started: 2026-06-11
owner: ram-de
---

# Session: phase-7-streamly-crawler — walk the Streamly sandbox, synthesize the Feature Pack

## Goal
First-customer (mock) pipeline: crawler MVP chain (#1–#3, done) → import the generated pack (#190, done) → trigger crawls from the product (#193, done) → prove a real UI-driven crawl end-to-end (done). MVP crawler epic (#171) now closed; remaining work is self-serve (#206) + browsability (#207).

## In Progress
- **Option-1 import (org W24 pack → Library) — repo half DONE, deploy half PENDING.** PR #209 merged to main (squash `5d31542`): imported the live Clerk org's first UI-driven crawl pack into `local-artifacts/customers/org_3EvPfxHZberTPA4ATgw2PITnmHo/featurepacks/2026-W24/` (13 caps, verbatim from R2/feature-pack artifact), `latest` pointer, `.gitignore` negation, round-trip test (`backend/tests/test_org_prod_pack.py`, 3 pass). Codex review: no actionable issues. **Deploy half (codex/SSM) still needed to surface it in prod** — see Next Steps #1.

## Completed
- **#171 CLOSED 2026-06-12 (MVP crawl-setup+trigger window — proven end-to-end)**: all four scoped parts map to shipped code (setup form, trigger+progress watch view, re-crawl link; review/promote partial — promote-gate deferred as a product decision, never a blocker). GENERATED-NEVER-AUTHORED invariant held. Remaining gaps carried out to **#206** (self-serve) + **#207** (browsability), filed + cross-linked this session.
- **#193 DONE + PROD REDEPLOYED 2026-06-12 (fire-and-watch crawl trigger)**: `POST /crawls` dispatches `crawl.yml`; `GET /crawls/{id}` maps run→status; fire-and-watch UI. Shipped as PR #201 (backend crawl_runs + dispatch + migration 010) + PR #202 (frontend) + crawler `crawl.yml`. Prod backend redeployed via codex/SSM (account 897729137726, instance i-04b155fafcc90042b): deployed SHA dc8a57c, migration 010 applied, `dispatch_configured: True`, AUTO_MIGRATE reset to 0. Charset widened to `[A-Za-z0-9][A-Za-z0-9_-]{0,63}` (#203 / crawler #16) because prod tenant key is the raw Clerk org id. Two redeploy gotchas documented in `deploy/REDEPLOY.md` (PR #205): run deploy TWICE when it edits `ec2-api-deploy.sh` itself; `/health` version is a hand-bumped constant, NOT a freshness signal.
- **Real UI-driven crawl PROVEN 2026-06-12**: Start crawl on app.sidira.ai for the live Clerk org `org_3EvPfxHZberTPA4ATgw2PITnmHo` → run 27458728409 walk→synthesize green in ~14 min → published 28 objects to `customers/org_3EvPfxHZberTPA4ATgw2PITnmHo/featurepacks/2026-W24/` (13 capabilities). Needed crawler PR #17 (`add33c01`): hand-authored `acceptance/org_3EvPfxHZberTPA4ATgw2PITnmHo.json` (byte-for-byte copy of streamly-sandbox.json) — THIS manual step is exactly the #206 self-serve gap. Pack readable without R2 creds via the run's `feature-pack` artifact (`gh run download 27458728409 --repo ram-de/sidira-crawler --name feature-pack`); reverse-PRD lives at `capabilities/<name>/reverse-prd.md` (per `storage.py`).
- **Simulator #190 DONE 2026-06-12**: streamly-sandbox 2026-W24 imported as the first crawler-GENERATED customer pack; `latest` pointer written in R2 by the crawler workflow itself.
  - PR #191 (`d7b62c3`): initial import + layered `.gitignore` allowlist + `backend/tests/test_streamly_sandbox_pack.py` (round-trips every capability through `FeaturePackLoader`; structural assertions only — GENERATED, NEVER AUTHORED).
  - Crawler PR #12 (`4245c7b`): `publish_latest` — pointer written only after pack AND diff, no-regress guard for backfills (zero-padded ISO weeks compare as strings). Verified live in synthesize-pack runs 27398818409 + 27400430296.
  - The verification re-dispatch re-synthesized 2026-W24 in R2 (clustering is nondeterministic even at temp 0.0), so PR #192 (`1298bee`) re-imported: final pack is **12 capabilities** (`account_plan` split out of `account`; `help` folded away), `crawl_metadata` consistent (`unassigned_screens: 0`, 48/48 assigned). Honest gate PASS on the exact imported pack (leakage 0/0/0, recall 0.75).
  - Codex review on #192 caught a real crawler bug → crawler PR #13 (`bf9f625`): clustering validation never checked `unassigned ∩ assigned`; repair drops double-listed screens (assignment wins, `cluster.double_listed_repaired` log).
  - R2 snapshot keys are not cleaned on overwrite: re-running the same snapshot leaves stale capability dirs (the run-27400430296 artifact still had `help/`). Import takes manifest + diff + manifest-named capability dirs — **the manifest is the source of truth for pack membership**.
- **Crawler #3 DONE 2026-06-12**: Phase-3 synthesizer (PRs #10, #11). Pack in R2 at `customers/streamly-sandbox/featurepacks/2026-W24/`; honest gate PASS; engine purity (`grep -ri streamly sidira_crawler/` empty) holds.
- Crawler #2 (CI acceptance gate, PR #7) and #1 (generic BFS walker, PR #6) — see git history.

## Next Steps
0. **Option-1 deploy half (codex/SSM) — surface the org pack in the prod Library.** Two facts settle what's needed: (a) prod serves `local-artifacts` via a **bind mount** from the instance repo dir (`ec2-api-deploy.sh:198`), NOT baked into the image — so the deploy's `git fetch origin main` brings PR #209's pack onto the box; a redeploy is sufficient to land the fixture. (b) IDENTITY WALL (#208): the live Library showed `streamly_sample` (the `SIDIRA_CUSTOMER_ID` default), which means the Clerk `org_id` claim is NOT reaching `request.state.customer_id` in prod — if it were, `current_customer_id` would resolve to `org_3Ev…` and the API would 404 (no pack) rather than serve the sample. So to make the pack visible, EITHER set SSM `/sidira/prod/SIDIRA_CUSTOMER_ID=org_3EvPfxHZberTPA4ATgw2PITnmHo` (global default flip — fine while the app is single-org) OR fix the Clerk claim extraction (multi-tenant-correct, more work). Decision pending with user. Codex prompt: redeploy from main (no migration this PR), set the tenant default, verify `GET /capabilities` serves 13 caps for the org.
1. **#206 (strategic next epic — real-customer self-serve)**: the saved `CrawlSetup` form is NOT wired to the dispatch; Start crawl ignores form input and a crawl only works if `acceptance/<org-id>.json` exists in the crawler repo (hand-authored). Four sub-slices: (a) thread CrawlSetup → dispatch inputs; (b) crawler consumes that config instead of `acceptance/<customer>.json` + hardcoded sandbox image; (c) per-customer secret handling (form collects role+username but NO password today); (d) honesty-gate strategy with no ground-truth manifest for a customer's real app. Slice (a) alone is groundwork — no visible value until (b).
2. **#207 (self-contained feature — Library browsability)**: capability/persona cards in `/personas` are static `<Card>` (link nowhere); reverse-PRD/Figma only readable from R2 or the run artifact. Build: backend endpoint to serve one capability from a pack + `/personas/capability/[name]` route + swap `<Card>`→`<CardLink>`, remove the two "aren't browsable from the Library yet" placeholders. NOTE: the org's W24 pack is NOT yet visible in the app Library (earlier screenshot showed an old 2026-W21/2-cap pack) — a #190-style import + `latest`-pointer check would surface it; this is the small bounded option we deferred in favor of housekeeping.
3. **#194 (parked)**: local walker execution — full loop on the dev Mac, `--server-cmd` sandbox, LocalArtifactStore, no CI/cloud creds. Guardrail: a local crawl must not silently overwrite the imported streamly-sandbox fixture.
4. **Crawler #14 (open)**: figma synthesis drops cross-capability transitions — observed `Manage plan` path from `account` into `account_plan` absent from the published pack. Re-import the pack wholesale once it lands.
5. Crawler #8 open: replay steps not idempotent (member 19/20). Sandbox backlog parked: #4 public deploy, #5 hostility traits.

## Key Files
- simulator `backend/tests/test_streamly_sandbox_pack.py` — round-trip tests on the generated fixture (pins 2026-W24 × 12 caps)
- simulator `local-artifacts/customers/streamly-sandbox/featurepacks/` — GENERATED, NEVER AUTHORED; re-import from R2, never hand-edit
- simulator `backend/sidira_simulator/api/crawls.py` — `POST /crawls` (dispatches, 202) / `GET /crawls/{id}` (status) — WIRED by #193; does NOT read saved CrawlSetup (that's the #206 gap)
- simulator `deploy/REDEPLOY.md` — agent-executable backend redeploy runbook; two gotchas added this session (run-twice on self-edit; /health version not a freshness signal)
- crawler `acceptance/org_3EvPfxHZberTPA4ATgw2PITnmHo.json` — hand-authored prod-tenant config (copy of streamly-sandbox.json); the manual step #206 removes
- crawler `sidira_crawler/storage.py` — R2 layout: `customers/<id>/featurepacks/<ver>/{manifest.json, capabilities/<name>/reverse-prd.md + reverse-figma.json, diff-vs-prior.json}` + `latest` pointer
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
The MVP crawler loop is complete and **proven from the live product**: clicking Start crawl on app.sidira.ai dispatched a real CI crawl of our Clerk org, walked the Streamly sandbox, synthesized a 13-capability pack, and published it to R2 under `customers/org_3EvPfxHZberTPA4ATgw2PITnmHo/featurepacks/2026-W24/` — no human touched the pack. #193 (the trigger), the prod backend redeploy (POST /crawls is live, dispatch token in SSM), and #171 (the whole crawl-setup window epic) are all closed. Two honest caveats remain, now filed: (1) **#206** — this is NOT real self-serve yet; the form input is dropped on dispatch and a crawl only works because I hand-authored `acceptance/org_…json` in the crawler repo and the walker hits a hardcoded sandbox image. A real customer can't onboard themselves. (2) **#207** — the produced pack isn't browsable in the app; capability cards link nowhere (read it from R2 or `gh run download … --name feature-pack`). The org's W24 pack also isn't imported into the Library yet (app still shows an old W21 pack). Next epic is #206 (self-serve, large) or #207 (browsability, medium). This session ended on housekeeping — board now reflects reality.
