---
type: session
domain: model-selection
status: active
started: 2026-05-27
owner: ram-de
---

# Session: model-selection -- PM-selectable LLM provider/model (#103)

## Goal
Ship #103: let PMs choose which LLM powers a simulation, spanning Groq, Anthropic, and OpenAI, while preserving today's Groq default and enforcing one model per simulation/A-B run.

## In Progress
- [ ] Lock the #103 implementation design before production code changes.

## Completed
- [x] Closed prior `arm-scoped-persona-chat` session and verified #98 Project status is Done.
- [x] Picked #103 as the next work item from `CONTEXT.md` and the GitHub Project.
- [x] Read #103 issue body and captured locked design constraints.
- [x] Assigned #103 to `ram-de` and moved its Project status to `In Progress`.
- [x] Created feature branch `feat/103-model-selection` from current `main`.
- [x] Inspected current LLM call paths: sim reactions, scoring, refinement, individual chat, persona-group collective/synthesis, and column mapping all depend on `adapters.llm.ChatClient`.
- [x] Checked installed SDKs: `openai==2.37.0` and `anthropic==0.103.1`; OpenAI client supports both `responses` and `chat`.
- [x] Verified current official model docs for implementation-time model IDs. OpenAI docs now list GPT-5.5/GPT-5.4 family; Anthropic docs list Claude Opus 4.7 / Sonnet 4.6 / Haiku 4.5; Groq docs list the existing llama defaults.

## Next Steps
1. Present the concrete #103 implementation design for approval before code.
2. Implement backend model registry + provider routing + `GET /models`.
3. Persist `model_id` through schema/repos/migration/orchestrator/runner.
4. Add wizard model selector and result-page model banner.
5. Regenerate frontend OpenAPI types and run backend + frontend verification.

## Key Files
- `backend/pythia_simulator/adapters/llm.py` -- current single-provider-ish ChatClient, Groq default, Anthropic fallback.
- `backend/pythia_simulator/services/simulation_runner.py` -- materializes agent reactions, then calls scoring + refinement.
- `backend/pythia_simulator/services/scoring.py` -- sentiment/weakness classifier LLM calls.
- `backend/pythia_simulator/services/refinement.py` -- refinement LLM call after scoring.
- `backend/pythia_simulator/api/simulations.py` -- POST/GET simulation contract.
- `backend/pythia_simulator/adapters/db_models.py` and `adapters/repositories.py` -- simulation row persistence.
- `frontend/app/simulations/new/page.tsx` -- wizard submit payload and advanced options UI.
- `frontend/app/simulations/[id]/page.tsx` -- result banners.
- `frontend/lib/api.ts` and `frontend/lib/api-types.ts` -- typed API client/OpenAPI generated types.

## Key Context

Locked constraints from #103:
- Default behavior remains today's Groq `llama-3.3-70b-versatile`; omitted `model_id` is backwards-compatible.
- v1 is multi-provider: Groq, Anthropic, and OpenAI behind one `ChatClient` routing abstraction.
- The backend exposes the configured model set via `GET /models`; missing provider API keys remove those providers from the returned set.
- `SimulationRequest` gains optional `model_id`; persisted `Simulation` rows expose the model used so the result page can show it later.
- A/B mode uses exactly one selected model for both treatment and control arms. Per-arm model selection is out of scope because it would confound the paired-lift formula.
- Unknown or unavailable `model_id` should fail fast with 400.
- Frontend wizard gets a grouped model selector; result page gets a model-used banner.
- v1 can use honest relative cost/speed labels rather than precise dollar estimates.

Discovery notes:
- The current `ChatClient` protocol has no per-call model argument; the cleanest path is to configure a model-bound client per simulation and pass that client into `SimulationRunner`/`ScoringService`/`RefinementService`.
- `SimulationRunner._score()` already constructs scoring/refinement with `self._chat_explicit`; that path will route correctly if `self._chat_explicit` is a model-bound router.
- API-created simulations use a process-level orchestrator dependency. The model choice should be persisted at prepare time, then `_run_in_background()` should build or select the model-bound chat client for that sim before running.
- Post-simulation chat and persona-group chat currently build fresh default clients from `get_chat_client()`. #103 acceptance is about sim-time agent reasoning + classifiers + result traceability; inheriting the sim's model for later chat is product-reasonable but adds repo reads/service plumbing. Decide explicitly in design.
- OpenAI docs changed since the ticket: the current official latest family is GPT-5.5/GPT-5.4, and the issue's "pick latest available at implementation time" points to using current official IDs rather than hard-coding `gpt-5`.

## For my cofounder
Starting #103 on `feat/103-model-selection`. The main risk is not the UI; it is keeping model routing explicit and testable across every LLM call path (agent reaction, sentiment classifier, weakness classifier, and refinement if it remains part of the sim flow). The design pass should confirm exactly where the current Groq client is injected before code changes.
