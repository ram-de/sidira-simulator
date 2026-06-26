# Experiment-Memory chat + pre-gate hypothesis dedup (#28, #29)

## Why
The LOW-RISK wedge for Sidira: pure RETRIEVAL over an archive of PAST experiment
outcomes — no model prediction — so it's valuable regardless of engine accuracy.

Two capabilities:
1. Chat over the experiment archive (grounded RAG, cites real past experiments).
2. Pre-gate hypothesis dedup: a NEW hypothesis returns semantically-similar PAST
   experiments + their real results, trust-ordered BEFORE any prediction:
   - (a) already-tested -> show the real result;
   - (b) similar -> analogical prior, labelled HONESTLY ("similar != guaranteed
     same effect");
   - (c) novel -> "no prior match - candidate for testing."

## Plan / state
- Backend (FastAPI under `backend/sidira_simulator/`):
  - `schemas/experiment_memory.py` — Experiment model + request/response schemas.
  - `services/experiment_archive.py` — SEED archive (~25 synthetic experiments
    across copy/pricing/UI/flow, incl. counter-intuitive ones).
  - `services/experiment_similarity.py` — offline TF-IDF + cosine (pure-python,
    no new deps); trust-ordered verdict logic (tested / similar / novel).
  - `services/experiment_chat.py` — RAG over the archive using the existing
    `adapters/llm.get_chat_client`; offline extractive fallback when no LLM key.
  - `api/experiments.py` — `POST /experiments/search-similar`,
    `POST /experiments/chat`. NEW routes only; existing endpoints untouched.
  - Registered in `main.py` via `app.include_router(experiments.router)`.
- Frontend (Next.js): new page `/memory` (client island) — hypothesis-check
  input (similar matches + trust verdict) + a chat box. Mirrors AppShellV2 +
  v2-theme.css token-driven styling (DESIGN.md). New rail nav item "Memory".
- Tests: `backend/tests/test_experiment_memory.py` — similarity ranking +
  trust-ordering thresholds + the two endpoints (chat stubbed, no live LLM).

## Hard constraints honoured
- Two-table firewall: data model is retrieval over KNOWN past outcomes; the
  search input (hypothesis text) carries NO outcome, and the model keeps inputs
  (change_description/variants/category) cleanly separate from outcome fields
  (winner/result/effect_size). No invented leakage path.
- Offline-safe: similarity is pure-python TF-IDF/cosine; chat degrades to an
  extractive grounded answer when no LLM provider key is configured, so the
  suite + a keyless local demo both run.
- Identity = ram-de for the PR. Do NOT merge, do NOT deploy.

## Status: DONE — PR #486 (feat/experiment-memory), not merged/deployed
- Backend + frontend + tests built and green.
- Backend suite: 1595 passed; 3 pre-existing test_deploy_config.py failures
  (Caddyfile basic_auth / host helpers) unrelated to this change.
- Frontend: tsc clean, next build compiles /memory. next lint has no committed
  eslint config in-repo (interactive prompt) — pre-existing, untouched.
- GitNexus detect-changes: risk low, 0 affected processes.

## Decisions for review
- Trust thresholds (cosine): >=0.62 "already-tested", >=0.28 "similar",
  else "novel". Tuned against the seed set; easy to revisit.
- Chat falls back to extractive (no-LLM) so the demo works keyless; with a key
  set it uses get_chat_client() like agent_chat.py.
