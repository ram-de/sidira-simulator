---
type: session
domain: persona-filter
status: closed
started: 2026-05-27
closed: 2026-05-27
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
-- session complete --

## Completed
- **#101 -- persona filter** (MERGED PR #102, commit `2a313c1`, 2026-05-27). PMs can now narrow a sim to a subset of personas via a checkbox list behind the wizard's Advanced options. Default unchanged (all personas).
  - **Backend:**
    - `SimulationRequest.selected_personas: list[str] | None = None` with Pydantic validator rejecting empty list + dedup'ing dupes.
    - `population_sampler.allocate(..., selected_personas=...)` -- filter + renormalize step runs BEFORE existing largest-remainder. Self-validates (unknown ids + empty list rejected) as defense-in-depth.
    - `simulation_runner.run` + `orchestrator.prepare` thread the field through; A/B mode applies the filter SYMMETRICALLY across both arms (paired-sampling invariant from #89 holds because both arms run the same persona set).
    - `api/simulations.py POST` eager-validates unknown persona_ids against the active pack in `orchestrator.prepare()` before persisting the sim row. `ValueError -> 400`.
    - `api/simulations.py GET` surfaces `row["selected_personas"]` so the frontend cohort banner can branch off it.
    - **New endpoint `GET /personas`** (`api/personas.py`) returns `{pack_version, personas: [{id, name, weight}]}` for the wizard's filter checkbox list. Sibling of `/capabilities`.
    - `adapters/db_models.py` Simulation.selected_personas JSONB NULL column; alembic 006 ADD COLUMN; repositories updated for both Postgres and InMemory + the `_simulation_to_dict` mapper.
  - **Frontend:**
    - `lib/api.ts` -- new `PersonaSummary`, `ActivePersonasResponse` types + `getActivePersonas()`.
    - `app/simulations/new/page.tsx` -- `PersonaFilterSection` component rendered inside the (renamed) "Advanced options" disclosure. All personas checked by default; select-all / clear-all links; per-persona weight subtext.
    - **Submit-payload null-vs-list convention:** sends `selected_personas=null` when ALL personas are checked (matches backend "None = all"), AND when `/personas` hasn't loaded yet or errored (codex R1-P2 fix). Sends explicit subset ONLY when PM has actually narrowed.
    - `app/simulations/[id]/page.tsx` -- new `CohortBanner` above the population banner when `sim.selected_personas != null`. Joins persona_ids against `agentMeta` to surface persona NAMES (not IDs); falls back to IDs if `agentMeta` hasn't joined yet.
  - **Codex review: 2 rounds. 1 P2 (round 1), 0 P1s. Round 2 = GATE PASS.**
    - R1-P2: when `/personas` is still loading or errored, `activePersonas.length === 0` and `selectedPersonas` is empty; the previous code derived `personaFilter = Array.from(selectedPersonas)` = `[]`, and the API 422-rejected -- breaking the exact fallback path the in-UI error message promised would "run against all personas." Fix: also send `null` when `totalPersonaCount === 0`. Commit `534989d`.
    - R1 also hung once at 5.5min (codex API stall) before coming back clean on retry. Documented in PR #102 body.
  - **Backend suite at 327 passed / 10 skipped** (15 new #101 tests on top of the #91 baseline of 312). Zero regression.

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
#101 persona filter is SHIPPED (PR #102 merged 2026-05-27, commit `2a313c1`). PMs can narrow a sim to a persona subset via the wizard's Advanced options checkbox list. Default unchanged (all personas). Backend test suite at 327 passed / 10 skipped.

**Load-bearing decisions worth preserving if you touch this code:**
- Allocator re-weight happens BEFORE existing largest-remainder, not after. Test `test_selected_personas_reweights_subset_preserves_population_size` pins the math (3-of-6 with weights .28/.20/.12 at n=50 -> 23/17/10, full population preserved).
- "None = all personas" is the backwards-compat contract at every layer. The wizard sends `null` when all checked AND when `/personas` is unloaded/errored -- never `[]`, because the API 422-rejects empty.
- A/B mode + persona filter compose symmetrically: same selected_personas in both `allocate()` calls preserves the #89 paired-sampling invariant.

**Three new followups on top of this PR (not blockers, separate tickets):**
- **#103** -- model selection (multi-provider: Anthropic + OpenAI + Groq). Filed 2026-05-27, ~3-4 days. Biggest engineering piece is the multi-provider `ChatClient` abstraction.

**Older still-active followups (Phase 4.6 A/B-mode leftovers):**
- **#98** -- arm-scoped persona-group chat in A/B mode (currently disabled with a tooltip)
- **#99** -- de-asymmetric the per-arm confidence-score display (Treatment 34 vs Control 59 is misleading)
- **#100** -- wizard cost preview vs backend cap reconciliation
