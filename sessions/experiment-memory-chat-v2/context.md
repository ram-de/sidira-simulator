# Experiment-memory chat v2 — #31 fusion + #32 multi-turn

Branch: `feat/experiment-memory-chat-v2` (worktree, off `main` @ `ffefdc1d`).

## Scope

Extend the merged experiment-memory feature (`/memory`) with two tickets:

- **#31 — Fuse Sidira simulation predictions with real experiments.** Retrieval now
  draws from BOTH the real-experiment seed archive AND a parallel
  **synthetic-simulation seed** (Sidira's own *predicted* hypotheses). Answers tell a
  story across both: "we *predicted* X (Sidira sim), the real A/B *measured* Y,
  learning Z." Citations distinguish **PREDICTED (Sidira sim)** vs
  **MEASURED (real experiment)**.
- **#32 — Glean-style multi-turn conversation.** The single-shot "Ask the archive"
  becomes a threaded conversation: message history held in component state, context
  carried across turns (a follow-up resolves against the prior turn), per-answer
  citations, suggested follow-up chips + a free-text box. Grounded / extractive
  fallback preserved.

## Why a synthetic-simulation seed

The live `Simulation` model (`schemas/simulation.py`) is DB-backed + engine-produced
and is NOT reachable from the offline/seed path. Per ticket #31's instruction, a small
synthetic-simulation seed (`services/simulation_archive.py`) is added parallel to
`experiment_archive.py` so the fusion is demoable offline. The seed is deliberately
PAIRED to experiments by shared change/metric/category vocabulary so the story
(predicted vs measured) lands. The real simulation data model is read, NOT refactored.

## Constraints honored

- DESIGN.md is law. No emoji, no icon library, tokens only. §8.2 retrieval-verdict
  lexicon respected; a **PREDICTED / MEASURED citation-source lexicon** is added to
  §8.2 in the SAME PR (lockstep). Chat is §7.4 "evidentiary but human"; §9.4 reading
  choreography honored for streamed turns (settled-frame fallback for reduced motion).
- The existing `experiment_archive` READ interface (`seed_experiments`) is NOT
  refactored — builder B owns ingestion. Fusion composes on top.
- Existing `/experiments/chat` + `/experiments/search-similar` routes untouched
  (back-compat). New work lands on a NEW `/experiments/conversation` route.

## Files

Backend:
- `schemas/simulation_archive.py` (new) — `SimulatedHypothesis` predicted record.
- `services/simulation_archive.py` (new) — synthetic-sim seed, paired to experiments.
- `services/experiment_fusion.py` (new) — fused retrieval + multi-turn context.
- `schemas/experiment_memory.py` (extended) — citation `source`, conversation turn schemas.
- `api/experiments.py` (extended) — new `POST /experiments/conversation`.

Frontend:
- `lib/api.ts` — new conversation types + `converseExperiments`.
- `app/memory/MemoryConsoleV2.tsx` — threaded conversation UI.
- `styles/v2-theme.css` — new `.v2-mem-*` thread classes (tokens only).

Tests:
- `backend/tests/test_experiment_memory_fusion.py` (new) — fusion retrieval + multi-turn context.

DESIGN.md: §8.2 addendum (PREDICTED/MEASURED citation lexicon) + changelog row.

## Test/typecheck

- Backend: `PYTHONPATH=backend backend/../../../../backend/.venv/bin/python -m pytest`
  (the venv lives in the MAIN checkout; PYTHONPATH must point at the WORKTREE backend
  so the worktree package shadows the editable install).
- Frontend: `cd frontend && npx tsc --noEmit`.

## Status: DONE — PR opened

- Backend: fusion service + synthetic-sim seed + `POST /experiments/conversation`;
  18 new fusion/multi-turn tests pass; full suite 1611 passing.
- Fixed a PRE-EXISTING breakage: `test_customer_isolation` did not allowlist the
  experiment-memory routes (chat/search-similar were already failing on baseline);
  added all three `/experiments/*` routes to `TENANT_AGNOSTIC_ROUTES` (seed-only,
  no tenant data).
- Frontend: threaded conversation UI (history, follow-up chips + free-text box,
  PREDICTED/MEASURED citations); `tsc --noEmit` clean.
- DESIGN.md 0.3.7: §8.2 PREDICTED/MEASURED fused-citation lexicon + changelog.
- KNOWN pre-existing reds NOT in scope (red on baseline `ffefdc1d`, untouched):
  `test_deploy_config.py::test_public_api_is_gated_by_backend_internal_key` and
  `::test_frontend_splits_public_site_from_product_app_hosts` (marketing homepage /
  domain split — unrelated to experiment-memory).
