---
type: session
domain: weighted_population
status: active
started: 2026-05-22
owner: rmkmar
---

# Session: weighted_population — Phase 2.5 weighted population sampling

## Goal
Replace `persona_sample_size` (a literal agent count) with `population_size` (modeled userbase size that gets stratified down to N actual agents), add per-agent `identity_seed` variance, and aggregate with proper confidence intervals — so simulation scores stop being a single point estimate against the top-6 personas.

## In Progress
- [ ] PR for #57 (schema swap) — branch `feat/2.5-schema-population-size`, codex review pending

## Completed (this session, continued)

## Completed
- [x] Surveyed current state: `_top_personas_by_weight` truncates by head_count weight (not real stratification); 60 backend tests baseline.
- [x] Resolved the three open ROADMAP questions in chat: hybrid deterministic+optional-prose identity_seed; emit `behavioral_seeds` from pythia-personas v1.1 with simulator-side fallback; use Phase 4's persona-grouped table (#51) for the detail view (merge #10 into #51).
- [x] Created three new tickets: simulator [#57](https://github.com/ram-de/pythia-simulator/issues/57) (schema swap), simulator [#58](https://github.com/ram-de/pythia-simulator/issues/58) (population_sampler), pythia-personas [#4](https://github.com/ram-de/pythia-personas/issues/4) (behavioral_seeds in v1.1).
- [x] Implemented #7 (Groq backoff) on branch `feat/2.5-groq-backoff`: `_retry_on_rate_limit` helper wraps both GroqChat and AnthropicChat; exponential backoff with jitter; cap 3 retries; structlog WARN on each retry. 4 new tests, full suite 64/64 green. PR merged as `54c2e61`.
- [x] Implemented #57 (schema swap) on branch `feat/2.5-schema-population-size`: SimulationRequest.population_size (1..10_000_000, `extra="forbid"` rejects the old field), Simulation.population_size/sampled_agent_count, Weakness CI fields (all optional), SimulationResult.confidence_score_ci, Persona.behavioral_seeds, AgentInstance.identity_seed, new schemas/identity.py + BehavioralSeedSchema. PersonaPack.schema_version accepts "1.0" or "1.1". API route derives sample_size = min(population_size, PYTHIA_MAX_AGENTS|50) until #58 lands. 9 new tests, full suite 73/73 green. Frontend gen-types clean; one call site renamed.

## Next Steps
1. Read current `_sample_personas` and surrounding scoring code to anchor the rewrite.
2. Walk through ROADMAP's three open questions with cofounder; document the decisions in this file under Key Context.
3. Sequence the work into landable PRs (rough order from ROADMAP "Phase 2.5 decisions locked"): schema swap → sampler → identity_seed injection → CI aggregation → frontend wizard → Groq backoff → degradation guard.
4. Open / claim the existing Phase 2.5 issues on the GitHub Project (#3-#14 area per ONBOARDING reference, but verify real numbers).

## Key Files
- `backend/pythia_simulator/services/simulation_runner.py` (where `_sample_personas` lives)
- `backend/pythia_simulator/services/scoring.py` (today's point-estimate scoring)
- `backend/pythia_simulator/schemas/simulation.py` (`SimulationRequest.persona_sample_size` to retire)
- `backend/pythia_simulator/adapters/llm.py` (Groq backoff lives here)
- `frontend/app/simulations/new/page.tsx` (sample-size input → population-size input)
- `ROADMAP.md` § "Phase 2.5" (locked decisions + open questions + constraints)

## Key Context
- ROADMAP locked these already: single input `population_size`, hard cap `min(population, MAX_AGENTS)` with `MAX_AGENTS` env-configurable default 50, identity_seed per-agent variance, Wilson CI on weakness frequencies + bootstrap on aggregate score.
- Open questions (block code): identity_seed rule-based vs hybrid, per-persona attribute schema source (pythia-personas v1.1 vs hand-roll), 50-agent detail-view UX (virtualized list vs grouped — and now the persona-grouped table from `docs/agent-chat-ui-spec.md` is a strong candidate for the answer).
- Hard constraints from ROADMAP: Groq rate-limit backoff must land before the 50-agent run (3 LLM calls per agent × 50 = 150 bursts will 429 the free tier). Scoring degradation guard for >50% classification failures (today silently produces ~70 when everything fails).
- The Phase 4 result table (issue #51, just opened) is the natural detail-view answer — persona-grouped rows expand to per-agent rows, scales cleanly to 50.

## For my cofounder
This is a multi-PR sprint, not a one-shot. Plan-eng-review is on the table before I write any code (AGENTS.md says we do that for non-trivial chunks). The three open questions in ROADMAP need answers before sampler design lands — none of them are blockers for the schema swap or the Groq backoff, so we can ship those in parallel while we decide.
