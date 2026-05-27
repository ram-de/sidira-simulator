---
type: session
domain: persona-filter
status: active
started: 2026-05-27
owner: ram-de
---

# Session: persona-filter -- run sims against a subset of personas (#101)

## Goal
Ship #101: optional `selected_personas` filter on `SimulationRequest`. Default = all personas (today's behavior). Power-user option = pick a subset; backend re-weights and largest-remainder-allocates the full `population_size` across just those.

Use cases:
1. **Persona-targeted hypotheses** (e.g. "lower price for first-time users" -> filter to `new_trialer`).
2. **Drill-down debugging** -- after #92 Run 1 (autoplay) tanked at -10.5, the PM wanted to re-run with just `binge_marathoner` to confirm whether THAT persona reacts the same way. Today's all-personas sim doesn't support that.

## Locked design decisions (2026-05-27)

1. **Allocation: RE-WEIGHT** the selected personas' weights to sum to 1, then largest-remainder-allocate `population_size` across them. (Rejected: keep absolute weights -- a 5%-weight persona selected solo would get 2-3 agents, defeating the purpose.)
2. **Wizard UI: behind "Advanced options" disclosure**. (Rejected: always-visible checkbox list -- too noisy for the standard "everyone reacts" flow.)
3. **Cohort banner on result page: YES** -- above the population banner, lists `{N} of {M} personas: {names}`. Without this a PM looking at the page in two weeks won't remember they filtered.

## In Progress
- [ ] **#101 backend**: schema + allocator re-weight branch + Simulation row field

## Completed
(nothing yet)

## Next Steps
1. Backend schema (`SimulationRequest.selected_personas: list[str] | None = None`) + Pydantic validators (subset of pack, non-empty if non-None) + persist on `Simulation`.
2. Allocator (`services/population_sampler.allocate`) gains `selected_personas` kwarg; filters + renormalizes before existing largest-remainder.
3. Orchestrator (`services/simulation_runner._prepare`) threads `selected_personas` to allocator.
4. Backend tests: re-weight math, unknown-ID rejection, empty-list rejection, all-personas equivalence, A/B + filter composition.
5. Frontend: checkbox list behind Advanced options, cohort banner on result page.
6. /codex review + dogfood.

## Key Files
- `backend/pythia_simulator/schemas/simulation.py` -- `SimulationRequest.selected_personas` field + validator
- `backend/pythia_simulator/services/population_sampler.py` -- `allocate(..., selected_personas=...)` re-weight branch
- `backend/pythia_simulator/services/simulation_runner.py` -- thread the field through `_prepare` -> `allocate`
- `backend/pythia_simulator/adapters/db_models.py` -- `Simulation.selected_personas` column (alembic migration)
- `backend/pythia_simulator/api/simulations.py` -- POST handler reads new field; Simulation response exposes it
- `frontend/app/simulations/new/page.tsx` -- checkbox list in Advanced disclosure + cost-preview subtitle
- `frontend/app/simulations/[id]/page.tsx` -- cohort banner above population banner

## Key Context

**A/B mode composition** (#88-#91): persona filter applies symmetrically across both arms. Existing paired-sampling invariant from #89 keeps working -- both arms run the same filtered persona set, so `(persona_id, sample_index)` keys still match. No interaction with the per-arm cap, lift math, or paired-bootstrap CI.

**Re-weight math (locked):** if PM picks 3 of 6 personas with original weights [0.30, 0.20, 0.10, 0.15, 0.15, 0.10] and selects indices {0, 2, 4} (weights 0.30, 0.10, 0.15), then renormalized weights = [0.30/0.55, 0.10/0.55, 0.15/0.55] = [0.545, 0.182, 0.273]. Then largest-remainder applies as today on these renormalized weights. The total population_size is preserved (50 agents go to these 3 personas, not 27.5).

**Schema validation:**
- `selected_personas = None` -> all personas (backwards-compat, today's behavior).
- `selected_personas = []` -> 400 ("must select at least one persona").
- `selected_personas = ["unknown_id"]` -> 400 (unknown persona ID).
- `selected_personas = ["p1", "p2"]` where {p1, p2} is a subset of the active pack -> allocator gets these only.
- Persisted on `Simulation` row (denormalized for result-page render even after pack changes).

**Followups out of scope:**
- Per-persona weight overrides (custom 50/50 between two personas, not just include/exclude).
- Persona search / faceting for packs with 20+ personas. v1 assumes small lists (demo + streamly are 6 each).
- Result-page "compare to all personas" CTA that fires a sibling sim.

## For my cofounder
Phase 4.6 just closed (PR #97 + writeup). Starting #101 (persona filter) on branch `feat/persona-filter-101`. Three followups also exist as separate tickets: #98 (arm-scoped persona chat), #99 (de-asymmetric per-arm display), #100 (wizard cap vs backend). None of those block #101.

Re-weight math is the load-bearing decision -- if you touch the allocator, the renormalization step happens BEFORE the existing largest-remainder, and the test suite should pin that with a known-answer fixture.
