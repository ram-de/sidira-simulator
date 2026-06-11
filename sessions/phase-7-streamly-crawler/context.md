---
type: session
domain: phase-7-streamly-crawler
status: active
started: 2026-06-11
owner: ram-de
---

# Session: phase-7-streamly-crawler — walk the Streamly sandbox, synthesize the Feature Pack

## Goal
First-customer (mock) pipeline in ram-de/sidira-crawler: generic Playwright walker (#1, done) → CI acceptance gate against the streamly-sandbox image (#2, PR #7) → Phase 3 synthesizer over the raw walk → Streamly Feature Pack (#3, ready to start).

## In Progress
- [ ] Crawler #2: PR #7 (`feat/sandbox-walk-ci`) — sandbox-walk gate re-running in CI after the GHCR read grant was fixed; **user approved squash-merge once green** (being handled in the original session; if you're picking this up and the gate is green, merge it)
- [ ] Crawler #3: synthesize Streamly Feature Pack via Phase 3 synthesizer — **can start NOW, no merge dependency** (see Key Context)

## Completed
- Crawler #1 (walker MVP) — PR #6 merged. Generic BFS walker: replayable action paths, fresh context per node, screen_id = route + flag tokens + structural digest.
- Crawler #2 build: acceptance harness (`scripts/sandbox_acceptance.py`), judge config (`acceptance/streamly-sandbox.json`), CI workflow (`.github/workflows/sandbox-walk.yml`), hermetic tests (94 passed). Local gate PASS: guest 8/8, member 19/20, premium 20/20, all 6 mustDiscover FOUND, determinism PASS, 16.5 min with --jobs 3.
- Codex review of PR #7: 6 findings (1 P1 evidence-free matchers, 3 P2, 2 P3) — all fixed (`1130a7a`, `79c3edb`), verdict re-judged unchanged.
- GHCR pull failure on PR #7 root-caused (read grant not in effect; `manifest unknown` on digest pulls = GHCR masking denial) and fixed by user in package UI (sidira-crawler: Read under Manage Actions access).
- Issue #8 filed: replay steps not idempotent (the one honest miss, member plan-upgrade-done 19/20).
- All crawler issues backfilled to GitHub project 1 (gh token now has `project` scope; pass `--project` on future ticket creation).

## Next Steps
1. **Start crawler #3** (`gh issue view 3 -R ram-de/sidira-crawler`): run the Phase 3 synthesizer over the raw sandbox walk → reverse PRD + reverse Figma per capability → Feature Pack to R2 `customers/streamly-sandbox/featurepacks/<weekly-bucket>/`, schema-validated.
2. Input data: on Ram's Mac a full passing walk is at `/tmp/raw3.jsonl`; elsewhere, download the `raw-jsonl` artifact from PR #7's sandbox-walk run, or regenerate locally: `python scripts/sandbox_acceptance.py --server-cmd 'cd <streamly-sandbox checkout> && npm run dev' --config acceptance/streamly-sandbox.json --manifest <sandbox>/ground-truth/manifest.json --run-date <date> --out raw.jsonl --jobs 3`.
3. If PR #7 is green and unmerged: squash-merge it (user pre-approved), then branch #3 work off updated `main`. If not yet green, branch off `feat/sandbox-walk-ci` so the raw.jsonl schema-2 producer is in-tree.
4. After #3: file remaining gaps; sandbox backlog parked (#4 public deploy, #5 hostility traits); crawler #8 (replay idempotency) is an open engine follow-up.

## Key Files
- crawler `scripts/sandbox_acceptance.py` — harness + importable judge functions; `--help` documents local-server mode
- crawler `acceptance/streamly-sandbox.json` — judge config; ALL sandbox knowledge lives here + workflow, never in the engine
- crawler `sidira_crawler/walker.py` — generic engine; `sidira_crawler/storage.py` — R2ArtifactStore conventions (env R2_BUCKET/R2_ENDPOINT_URL/R2_ACCESS_KEY_ID/R2_SECRET_ACCESS_KEY)
- crawler `docs/sandbox-acceptance.md` — gate description + raw.jsonl schema 2 (meta header line, then observation/transition lines tagged `<role>@<entry_path>`)
- sandbox image pin: `ghcr.io/ram-de/streamly-sandbox@sha256:abdeb699118e99271363c0ea705a8142cbd1e55debb80211e7e0830892b9aaff # v0.1.0` (port 3000, `/healthz`, manifest at `/app/ground-truth/manifest.json`; seeded creds member@streamly.test/watchmore, premium@streamly.test/watchmore4k)

## Key Context
- **#3 has a data dependency on #2, not a merge dependency** — the synthesizer consumes raw walk output, which already exists. Treat raw.jsonl schema as pinned to PR #7's branch.
- **Anti-circularity (hard rule for #3):** build and run the synthesizer WITHOUT reading sidira-simulator `streamly_sample` fixture content. The honest-test gate compares synthesized pack vs streamly_sample on normalized graph shape + screen categories ONLY — never route names, labels, titles, fixture IDs. Comparison happens after synthesis, as evaluation.
- **Engine purity (hard rule, CI-greppable):** `grep -ri streamly sidira_crawler/` must stay empty. Judge/config may know the sandbox; the engine never does.
- R2 secrets are NOT configured on ram-de/sidira-crawler (CI R2 upload skips with a notice; artifact upload still works). #3's R2 write needs them or a local store.
- Known honest miss: member `plan-upgrade-done` (replay non-idempotency, issue #8) — doesn't gate.
- Docker is not installed on Ram's Mac — use `--server-cmd` mode locally; ports 4180-4199 free, 3000 taken.
- Codex review discipline: run codex review before declaring any PR done (`~/.npm-global/bin/codex`, off PATH; `-s read-only`, prefix prompts with the skill-files exclusion warning).

## For my cofounder
Ticket #2 is functionally done — PR #7 just needs the CI gate to finish (it passed locally end-to-end; the only CI failure so far was the GHCR grant, now fixed). Merge on green is pre-approved. Ticket #3 is unblocked: real walk data exists, contract documented above. Watch the anti-circularity rule — it's the whole point of the sandbox being independently built.
