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
- [ ] #58 (population_sampler) — branch + TDD next

## Completed
- [x] Surveyed current state: `_top_personas_by_weight` truncates by head_count weight (not real stratification); 60 backend tests baseline.
- [x] Resolved the three open ROADMAP questions in chat: hybrid deterministic+optional-prose identity_seed; emit `behavioral_seeds` from pythia-personas v1.1 with simulator-side fallback; use Phase 4's persona-grouped table (#51) for the detail view (merge #10 into #51).
- [x] Created three new tickets: simulator [#57](https://github.com/ram-de/pythia-simulator/issues/57) (schema swap), simulator [#58](https://github.com/ram-de/pythia-simulator/issues/58) (population_sampler), pythia-personas [#4](https://github.com/ram-de/pythia-personas/issues/4) (behavioral_seeds in v1.1).
- [x] **#7 (Groq backoff) merged** as `54c2e61`. `_retry_on_rate_limit` wraps both GroqChat + AnthropicChat; exp backoff + jitter; cap 3 retries; structlog WARN. 4 new tests. Codex was *not* run on this one (preceded the standing /codex rule).
- [x] **#57 (schema swap) merged** as `f10cbe9`. SimulationRequest.population_size (1..10_000_000, `extra="forbid"` rejects retired field), Simulation.population_size/sampled_agent_count (plumbed end-to-end through repo Protocol + Postgres model + alembic 002 + InMemory + orchestrator + API response), Weakness/SimulationResult CI fields (optional), Persona.behavioral_seeds + AgentInstance.identity_seed (both optional). PersonaPack.schema_version accepts "1.0" or "1.1". 11 new tests, suite 75/75. Codex review: 0 P1, 4 P2; 2 fix-now committed (env-parse hardening + repo plumbing), 2 deferred (`extra="forbid"` is intended; UI label/range is #9's scope).
- [x] Established: **MCP PR creation is blocked** for these repos — `mcp__github__create_pull_request` returns `422 "must be a collaborator"` because the rmkmar identity behind the MCP server has issue-create rights on `ram-de/*` but not branch-PR rights. Workaround: push branch, cofounder clicks the create-PR URL GitHub prints. See "For my cofounder" below for the fix.

## Next Steps
1. Branch `feat/2.5-population-sampler` for #58, TDD largest-remainder allocation, run /codex before push.
2. After #58: identity_seed service (#5), scoring CIs (#6), degradation guard (#8), then frontend (#9 + re-scoped #51).

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
Multi-PR sprint, two done. #7 and #57 are on main. Next branch is `feat/2.5-population-sampler` for #58 — pure-function TDD against the demo + streamly_sample packs.

**One fix needed from you:** PR creation via the GitHub MCP server is blocked because the `rmkmar` identity it uses isn't a collaborator on `ram-de/*`. Add `rmkmar` as a Write collaborator on `ram-de/pythia-simulator`, `ram-de/pythia-personas`, `ram-de/pythia-crawler` (GitHub → repo Settings → Collaborators → Add people). After that I can `mcp__github__create_pull_request` directly instead of pushing the branch and asking you to click the create-PR link.
