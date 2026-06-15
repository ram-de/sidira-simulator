---
type: session
domain: persona-pack-v1.1
status: active
started: 2026-06-15
owner: ram-de
---

# Session: persona-pack-v1.1 — Persona Pack v1.1 producer work (sidira-personas)

## Goal
Track the `sidira-personas` producer-side work that emits Persona Pack v1.1 and the
#7 stability/holdout honesty fields — cross-repo work that has no `sessions/` dir of
its own (sidira-personas has no CLAUDE.md), so it lives here.

## In Progress
(nothing — see Next Steps)

## Completed
- **Synthetic end-to-end pipeline fixture** issue filed — `ram-de/sidira-personas#12`
  (replaces purged DoorDash `config/` + `samples/`; integration/smoke layer, distinct from #222).
- DoorDash artifact purge — PR #9 (merged). Removed real-company `config/` + `samples/`.
- Persona Pack methodology doc (investor-grade) — PR #10 (merged).
- Persona Pack **v1.1** producer fields — earlier this session: `centroid_full`,
  `feature_scale`, `sample_rows` (MVN covariance-aware synthetic rows), `posterior_mean`.
  Unblocks simulator §2 step-2 (per-agent individual row).
- **#7 Jaccard + holdout slice** — PR #11 (merged, squashed to `main` 2026-06-15):
  - `per_cluster_jaccard` (clusterboot-style classify-all; Hennig bands).
  - `holdout_evaluation` (held-out loglik + proportion TV drift; n≤k skip + train clamp).
  - `posterior_entropy` (assignment ambiguity); FIXED_* `stability` now `null` not fake 1.0.
  - 28 tests pass, ruff clean. Codex-reviewed (no P1; 3×P2 + 3×P3 all addressed in ea488c3).
  - Issue #7 commented with shipped + deferred (XGBoost cold-start, HTML report).

## Next Steps
1. (Deferred to #12) Build the synthetic end-to-end pipeline fixture + smoke test.
2. (Deferred to #7) XGBoost cold-start classifier; HTML diagnostic report.

## Key Files (sidira-personas repo)
- `sidira_personas/calibrate.py` — `per_cluster_jaccard`, `holdout_evaluation`, `posterior_entropy`, `jaccard_verdict`.
- `sidira_personas/schema.py` — Persona v1.1 fields; nullable `stability`; `PERSONA_PACK_SCHEMA_VERSION = "1.1"`.
- `sidira_personas/cli.py` — wires the new fields + holdout into the pack.
- `tests/test_stability.py`, `tests/test_schema.py`, `tests/test_sampling.py` — synthetic-Gaussian fixtures (unit-level only).

## Key Context
- Consumer back-compat: simulator `Persona` model has NO `stability` field (Pydantic ignores
  extras) and pins `schema_version ∈ {1.0, 1.1}` — so nullable `stability` + new fields are
  safe; do NOT bump to 1.2 (would break the consumer Literal).
- `sidira-personas` has no live service → no backend redeploy applies.
- **Coverage gap:** unit-test synthetic fixtures exist; a representative synthetic *company
  dataset* for an end-to-end smoke run does NOT (purged with DoorDash in #9). Being ticketed now.

## For my cofounder
Persona Pack v1.1 + #7 honesty fields are live on `sidira-personas:main` (PRs #9/#10/#11).
The simulator-side §2 step-2 consumption (PR #243 individual-row layer) is the matching half.
Next open thread: a synthetic end-to-end pipeline fixture (no real data lives in the repo anymore).
