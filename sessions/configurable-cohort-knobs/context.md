---
type: session
domain: configurable-cohort-knobs
status: active
started: 2026-06-22
owner: ram-de
---

# Session: configurable-cohort-knobs — user-settable agent count + population

## Goal
Make the two cohort knobs user-configurable per simulation: raise the default
agent cap to 100, default population stays 1000, and let the user set BOTH
explicitly in the v2 sim wizard. The env cap (`SIDIRA_MAX_AGENTS`) stays a HARD
cost ceiling the per-request value can lower but never exceed (user-chosen
option 1).

## What "the gap" was
Today `population_size` (modeled userbase, default 1000) stratifies DOWN to at
most `MAX_AGENTS` actual LLM agents via largest-remainder allocation
(`population_sampler.allocate`). The agent count was env-only (default 50), not
a user knob — `api/simulations.py` derived `min(population, env_cap)`. This work
adds the second knob.

## Completed (PR pending)
- [x] `runtime_config.DEFAULT_MAX_AGENTS` 50 → 100; `population_sampler._DEFAULT_MAX_AGENTS` 50 → 100
- [x] `SimulationRequest.sampled_agent_count: int | None` (ge=1, optional) — None reproduces historical derive-from-cap behavior
- [x] `api/simulations.py`: realized = `min(population_size, sampled_agent_count, env_cap)`; env cap stays hard ceiling
- [x] Backend tests: 2 new (knob lowers below cap; knob clamped to env ceiling); updated config/sampler default assertions 50→100; fixed stale "default 50" comment
- [x] Frontend v2 wizard (`SimulationNewV2.tsx`): new "Agents" input beside Population (blank = cap), `realizedAgentCount` single-source helper, A/B cost calc + manifest preview + hint all honor it, sends `sampled_agent_count` only when set
- [x] `api-types.ts`: hand-added `sampled_agent_count?` to generated SimulationRequest
- [x] Gates green: ruff clean, backend pytest (config/sampler/sim-api/arm-split/runner) all pass, frontend tsc --noEmit exit 0
- [x] codex review: one P3 (Agents=0 slipped validation → backend 422) FIXED — guard `< 1` explicitly

## The 10,000-agents question (founder asked; answer = mostly no, logged as follow-up)
Raising agent count buys PRECISION, not ACCURACY:
- The accuracy problem is BIAS (Upworthy/Hillstrom directional nulls), not variance. 10k agents = a tight CI around a possibly-wrong number.
- DETERMINISM GOTCHA: agents are allocated across the pack's personas. On a **v1.0 pack** (centroid-only) every agent on the same persona is an identical identity; at `temperature=0` / `elicitation_samples=1` the weighted aggregate is INVARIANT to agent count — 100 vs 10,000 give the *literally identical* lift at 100× cost. On a **v1.1 pack** (PR #243 per-agent individual-row sampling) each agent is a distinct draw, so more agents covers within-segment heterogeneity — there hundreds-to-low-thousands pays off.
- Cheaper variance lever = `elicitation_samples` (#221), not 10k distinct agents.
- Decision: keep the hard env ceiling (100); raising it is an ops decision (`SIDIRA_MAX_AGENTS`), only worth it on v1.1 packs with stochastic reactions on + a real cost preview.

## Follow-ups logged
- GH issue (filed below): high agent-count exploration — when/whether to allow >100, gated on pack version + stochasticity + cost preview + async execution.
- Minor (not filed): frontend hard-caps population at 10,000 while backend allows 10M (`population_size le=10_000_000`). Left as-is; revisit if a customer needs a larger modeled userbase.

## Key Files
- backend/sidira_simulator/services/runtime_config.py, population_sampler.py
- backend/sidira_simulator/schemas/simulation.py, api/simulations.py
- backend/tests/test_{config_api,population_sampler,simulations_api}.py
- frontend/app/simulations/new/SimulationNewV2.tsx, frontend/lib/api-types.ts

## Deploy note
Touches `backend/` → api.sidira.ai is manual-deploy. After merge, run the
deploy/REDEPLOY.md runbook. NO migration (additive optional field; no schema
change to persisted rows).

## Next Steps
1. PR as ram-de → merge → backend redeploy (autonomous, per founder grant)
2. /pythia-session close once deployed + verified
