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
- [ ] Design the implementation against the current LLM/client, simulation runner, schema, and wizard code.

## Completed
- [x] Closed prior `arm-scoped-persona-chat` session and verified #98 Project status is Done.
- [x] Picked #103 as the next work item from `CONTEXT.md` and the GitHub Project.
- [x] Read #103 issue body and captured locked design constraints.

## Next Steps
1. Move #103 to In progress and assign `ram-de`.
2. Create feature branch `feat/103-model-selection` from current `main`.
3. Inspect existing LLM adapter, simulation schemas, runner call path, and frontend wizard/result page.
4. Present the concrete #103 implementation design for approval before code.

## Key Files
(to fill during discovery)

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

## For my cofounder
Starting #103 on `feat/103-model-selection`. The main risk is not the UI; it is keeping model routing explicit and testable across every LLM call path (agent reaction, sentiment classifier, weakness classifier, and refinement if it remains part of the sim flow). The design pass should confirm exactly where the current Groq client is injected before code changes.
