---
type: session
domain: phase-7-streamly-crawler
status: active
started: 2026-06-11
owner: ram-de
---

# Session: phase-7-streamly-crawler — walk the Streamly sandbox, synthesize the Feature Pack

## Goal
First-customer (mock) pipeline in ram-de/sidira-crawler: generic Playwright walker (#1, done) → CI acceptance gate against the streamly-sandbox image (#2, done) → Phase 3 synthesizer over the raw walk → Streamly Feature Pack (#3, done). Core MVP chain COMPLETE.

## In Progress
- (nothing — tickets 1–3 all done; see Next Steps for follow-ups)

## Completed
- **Crawler #3 DONE 2026-06-12**: Phase-3 synthesizer merged (PR #10 `1667001`, robustness follow-up PR #11 `7ecf59a`, both on crawler main; issue #3 auto-closed). Pipeline: deterministic graph load/merge → LLM capability clustering (validated, retry-with-errors, coverage-only repair) → deterministic reverse-Figma + LLM reverse-PRD → FeaturePack (pydantic schema v1.0) → artifact store.
  - **Pack in R2**: `customers/streamly-sandbox/featurepacks/2026-W24/` (26 objects: manifest + 12 capabilities × reverse-prd.md + reverse-figma.json + cluster.json), written by `synthesize-pack.yml` run 27395394894 from `crawl/2026-06-12/raw.jsonl`. Also uploaded as workflow artifact `feature-pack`.
  - **Honest-test gate PASS** on the CI-produced pack vs streamly_sample (scope: sample): content leakage 0/0/0 (screen ids / screen names / capability names), category recall 0.75 (auth, detail, library found; `confirmation` legitimately absent — it sits behind a purchase the read-only walker never performs), info: similarity 0.4148, count ratio 6.0. Anti-circularity held: synthesizer built/run without reading fixture content.
  - Engine purity verified: `grep -ri streamly sidira_crawler/` empty.
  - New: `sidira_crawler/synthesis/` (graph, cluster, figma, prd, pack), `cli.py synthesize`, `scripts/pack_structure_compare.py` (judge with declared `--reference-scope full|sample`), `.github/workflows/synthesize-pack.yml` (workflow_dispatch; downloads raw from R2, synthesizes via Groq, writes pack to R2, mirrors as artifact), hermetic test suite (120 passed/1 skipped).
- Crawler #2 MERGED 2026-06-11: PR #7 squash-merged as `229de67`; CI gate PASSED on the real GHCR image (guest 8/8, member 19/20, premium 20/20, 6/6 mustDiscover, determinism PASS). Issue #2 closed.
- Crawler #1 (walker MVP) — PR #6 merged. Generic BFS walker: replayable action paths, fresh context per node, screen_id = route + flag tokens + structural digest.
- R2 crawl upload proven in CI: merge-triggered sandbox-walk (run 27387169611) uploaded `customers/streamly-sandbox/crawl/2026-06-12/raw.jsonl` (the 2026-06-11 walk predated the repo secrets, so its upload was skipped).
- Codex reviews: PR #10 (P2 MIN_CAPABILITIES floor → 1, fixed `8940750`) and PR #11 (clean).

## Next Steps
1. Sandbox backlog parked: #4 public deploy, #5 hostility traits.
2. Crawler #8 open: replay steps not idempotent (member plan-upgrade-done 19/20) — engine follow-up.
3. Possible next ticket: consume the Feature Pack in sidira-simulator (import `customers/streamly-sandbox/featurepacks/2026-W24/` as a real customer pack) — not yet filed.
4. CI date gotcha: synthesize-pack defaults `crawl_date` to *today UTC*; when dispatching after 00:00Z, pass the crawl date explicitly.

## Key Files
- crawler `sidira_crawler/synthesis/` — Phase-3 pipeline; `cluster.py` holds the LLM clustering + validation/repair (MIN 1 / MAX 16 capabilities, retries 2)
- crawler `scripts/pack_structure_compare.py` — honest-test judge; sample scope gates category recall ≥0.75 + zero leakage, full scope gates symmetric similarity + count ratio ≤3.0
- crawler `.github/workflows/synthesize-pack.yml` — dispatch with `customer`, `crawl_date`, optional `snapshot`
- crawler `scripts/sandbox_acceptance.py`, `acceptance/streamly-sandbox.json`, `.github/workflows/sandbox-walk.yml` — walk + gate (sandbox knowledge lives here, never in the engine)
- reference pack: sidira-simulator `local-artifacts/customers/streamly_sample/featurepacks/2026-W21/`
- sandbox image pin: `ghcr.io/ram-de/streamly-sandbox@sha256:abdeb699118e99271363c0ea705a8142cbd1e55debb80211e7e0830892b9aaff # v0.1.0`

## Key Context
- **Anti-circularity & engine purity remain standing rules** for any future synthesizer work: never read `streamly_sample` fixture content during build/run; `grep -ri streamly sidira_crawler/` must stay empty (judge/config/workflows may know the sandbox).
- R2 + LLM secrets live on ram-de/sidira-crawler (R2_BUCKET=`sidira-artifacts` + endpoint/keys, GROQ_API_KEY). **No R2 creds on Ram's Mac** — R2 reads/writes go through CI; local runs use LocalArtifactStore + GROQ_API_KEY from sidira-simulator `backend/.env`.
- LLM: Groq `llama-3.3-70b-versatile`, temperature 0.0; AnthropicClient fallback.
- Docker is not installed on Ram's Mac — use `--server-cmd` mode locally; ports 4180-4199 free, 3000 taken.
- Codex review discipline: run codex review before declaring any PR done (`~/.npm-global/bin/codex`, off PATH; `-s read-only`).
- gh quirks: GraphQL 401 with ram-de token → use REST; workflow_dispatch needs the workflow file on the default branch.

## For my cofounder
The whole MVP chain is done: walker (#1) → CI acceptance gate (#2) → Feature Pack synthesis (#3). A real, schema-valid Streamly Feature Pack sits in R2 at `customers/streamly-sandbox/featurepacks/2026-W24/` — 12 capabilities, each with a reverse PRD and reverse Figma, synthesized from crawl data alone. The honest-test gate passed with zero content overlap against our hand-authored sample, which is the proof the pipeline isn't circular. Natural next move: wire that pack into the simulator as the first real customer import.
