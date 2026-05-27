---
type: session
domain: phase-4.6-ab-experiment-mode
status: active
started: 2026-05-26
owner: ram-de
---

# Session: phase-4.6-ab-experiment-mode — A/B experiment mode (treatment vs control)

## Goal
Ship Phase 4.6: extend the simulator to run two arms (treatment + control), compute a predicted lift between them, and surface it in the result UI. Builds on Phase 4 chat infrastructure (agents, identity_seed, scoring, result table) which all shipped 2026-05-26.

## In Progress
- [ ] **#90 — lift formula + paired CI**. Next ticket. Eng-locked at `/plan-eng-review` on 2026-05-26: paired bootstrap on per-agent sentiment delta with `aggregate_ab()`, `_match_paired_analyses` helper, drop counters, degenerate-case handling. Unblocked — #88 + #89 have shipped.

## Completed
- **#87 — design: A/B experiment mode scope** (CLOSED 2026-05-26). `/plan-ceo-review` locked Q1=B (reuse `Capability.reverse_prd` as the control-arm artifact), Q3=Paired sampling, Q4=wizard preview + 200-agent cap. `/plan-eng-review` locked Q2=paired bootstrap on per-agent sentiment delta. Output: `docs/4.6-ab-experiment-mode.md`. ROADMAP flipped from "deferred" to "in progress."
- **#88 — schema + wizard arm-split input** (MERGED PR #93). `ArmSplit` Pydantic model + `arm_split: ArmSplit | None = None` on `SimulationRequest` / `Simulation`. Alembic 004 added `simulations.treatment_fraction` (Float, nullable). Wizard renders the toggle + cost preview + confirm-if-large; staged-rollout gate kept the toggle disabled because #89 wasn't wired yet. Codex P1 caught the silent-mismatch risk and forced the gate.
- **#89 — dual-arm orchestrator + control-arm prompt** (MERGED PR #95, commit `2de943c`, 2026-05-26).
  - `compose_identity_prompt(arm: "treatment" | "control" = "treatment")` — split into `_PREAMBLE_TEMPLATE` + `_TREATMENT_TASK_BLOCK` + `_CONTROL_TASK_BLOCK`. Preamble (persona / about-you / behavioral snapshot / product-today) byte-identical across arms — the paired-comparison invariant. Control arm drops the proposed-change section + opener anchor, reframes the task as "react to the current product TODAY," adds an explicit "do not speculate" guard. All #77 anti-templated-opener guards preserved on BOTH arms.
  - `SimulationRunner.run(treatment_fraction)` — when set, two `allocate()` calls produce per-arm specs. At the locked f=0.5, both calls receive identical inputs → byte-equivalent `(persona_id, sample_index)` keys → `draw_identity_seed` returns matching seeds per pair → paired sampling for free.
  - `AgentInstance.arm: VARCHAR(16) NULL` (alembic 005) — pinned at materialization, never changes (identity-continuity invariant). NULL for single-arm sims.
  - `AgentRecord` carries `sample_index` + `arm` so #90's lift formula can match pairs by tuple.
  - Orchestrator threads `treatment_fraction` from `prepare()` → runner; API metadata constructors (`api/agents.py`, `api/feedback.py`, `api/persona_groups.py`) propagate `row["arm"]`.
  - **`ArmSplit.treatment_fraction` is now LOCKED at exactly 0.5** (`ge=0.5, le=0.5`). Codex round-2 caught that non-0.5 splits get silently overridden by the per-arm `max_agents` cap (e.g. f=0.8 + pop=1000 + cap=50 produces 50/50, not 80/20), AND #90's paired lift formula requires f=0.5 anyway. Re-open the range only when there's a product reason for asymmetric arms AND a scorer that supports them.
  - **Wizard A/B toggle stays gated** behind `AB_MODE_DISABLED_UNTIL_LIFT` (renamed from `AB_MODE_DISABLED_UNTIL_89`). The runner produces dual-arm output, but `ScoringService` still runs the single-arm path, so the result page would render `confidence_score` over a mixed treatment+control cohort — a number that looks like predicted lift but isn't. Direct API still accepts `arm_split` for #89's dual-arm runner tests. The toggle flips when #90 (paired lift) + #91 (lift display) both land.
  - Codex review: 2 rounds, 3 P1s + 2 P2s, ALL fixed. Final round: GATE PASS. Backend suite: 287 passes / 10 skips.
- **Mid-session scope-adds (shipped on the way to #89):**
  - **Per-category weakness info button on result page** (MERGED PR #94). Click-to-expand popover with PM-readable definitions for all 6 weakness categories. Codex P2 caught wrong_cohort (sample-size framing instead of relevance/targeting) and underpowered_design (didn't cover the degradation-gate path); both rewritten to match the canonical classifier prompt in `services/scoring.py`.
  - **Cross-repo "/codex review on every PR" rule** (MERGED via `25e85b3` on `pythia-simulator` AGENTS.md). Auto-mode classifier blocked the cross-repo writes to `pythia-personas/AGENTS.md` and `pythia-crawler/AGENTS.md` even after explicit authorization — prepared content was handed to the user to paste manually. **Cross-repo carryover: still pending on `pythia-personas` + `pythia-crawler`.**

## Next Steps
**Phase 4.6 implementation order (post-#89):**

1. **#90 lift formula + paired CI (NEXT, eng-locked)** — extend `services/scoring.py` (or new `services/lift.py`) with `aggregate_ab(agent_records: list[AgentRecord]) -> LiftResult`. Paired bootstrap on per-agent sentiment delta. `_match_paired_analyses` helper that matches by `(persona_id, sample_index)` and counts drops. Degenerate cases: zero pairs, all-positive deltas, all-zero deltas. Unit tests against known-answer fixtures (`test_statistics.py` is the shape reference). `SimulationResult.lift` + `SimulationResult.lift_ci` schema fields. Per-arm `confidence_score` calculations preserved unchanged.
2. **#91 frontend: result-table arm split + lift display (blocked on #90)** — big-number lift card above the table; persona-grouped table splits into treatment/control sections. **Flip `AB_MODE_DISABLED_UNTIL_LIFT` → false in the same PR.** Backwards-compat: single-arm sims render exactly as today.
3. **#92 e2e dogfood with calibration hypotheses (blocked on #88-#91)** — three runs (expected-lift / expected-null / expected-negative-lift) against the demo Persona Pack. Same dogfood pattern that surfaced #77 + #78 in Phase 4. Documents PM-read interpretations. Closes Phase 4.6.

**Carryover (out-of-band, not Phase 4.6 blockers):**
- Drop the broadened `/codex review on every PR` AGENTS.md section into `pythia-personas` + `pythia-crawler` manually.
- **#86** multi-replica feedback lock followup — blocked on Phase 5a Postgres wiring.

## Key Files
- `docs/4.6-ab-experiment-mode.md` — LOCKED decisions (Q1=B, Q2=paired bootstrap, Q3=paired, Q4=wizard preview + 200 cap). Single source of truth before code.
- `ROADMAP.md` — A/B mode entry is "in progress as Phase 4.6."
- `sessions/ab-experiment-mode/context.md` — the prior strategic-decision session. Do NOT re-litigate Product B (rejected) or the four questions (locked).
- `backend/pythia_simulator/services/prompt_composer.py` — split into preamble + treatment/control task blocks. The #77 anti-template guards apply to BOTH arms.
- `backend/pythia_simulator/services/simulation_runner.py` — dual-arm dispatch on `treatment_fraction`. Per-arm semantics: `population_size` is the per-arm target, NOT the total to split (Codex P1 #95 lesson).
- `backend/pythia_simulator/services/scoring.py` — extension point for #90 paired-lift aggregator.
- `backend/pythia_simulator/services/identity_seed.py` — `draw_identity_seed(persona, sample_index, run_seed)` is deterministic; paired sampling rides on identical args across arms.
- `backend/pythia_simulator/services/statistics.py` — home for #90 bootstrap helpers.
- `backend/pythia_simulator/schemas/simulation.py` — `ArmSplit` now locks `treatment_fraction=0.5`. `SimulationResult` schema extension lands in #90.
- `backend/pythia_simulator/adapters/db_models.py` — `Simulation.treatment_fraction` (Float, alembic 004) + `AgentInstance.arm` (VARCHAR(16), alembic 005). Both nullable for back-compat.
- `frontend/app/simulations/new/page.tsx` — `AB_MODE_DISABLED_UNTIL_LIFT` gate. Flip in #91.
- `frontend/app/simulations/[id]/page.tsx` — #91 lift card lives here; weakness info popover already in.

## Key Context

**Phase 4.6 #88 + #89 are DONE on main as of 2026-05-26.** A direct API caller can submit `arm_split={"treatment_fraction": 0.5}` and the simulator runs both arms with paired identity seeds. The wizard toggle stays disabled until #90 + #91. Backend suite is at 287 passes / 10 skips.

**Per-arm allocation is now the rule (Codex P1 #95).** `population_size` in dual-arm mode is the PER-ARM target, not a total to split. At wizard defaults (pop=50, cap=50, f=0.5) the runner produces 50 treatment + 50 control = 100 agents — matching the wizard cost preview. Pair matching works at odd populations too (pop=7 → 7+7, all paired). The prior `int(pop * 0.5)` math is gone.

**Identity-continuity invariant survives.** `AgentInstance.arm` is pinned at materialization (`memory/agent_memory.py` guarantees) and never changes. Chat surfaces (1:1 + persona-group + collective) are arm-agnostic — a PM clicks an agent and the chat continues from its frozen identity regardless of arm.

**Four locked design decisions (closed in #87):**
1. **Control-arm artifact = `Capability.reverse_prd`.** No new schema. Composer drops the proposed-change section in the control arm.
2. **Score formula = paired bootstrap on per-agent sentiment delta.** Drop counters for unpaired agents. Degenerate cases: zero pairs, all-positive deltas, all-zero deltas.
3. **Sampling = paired.** Same `(persona_id, sample_index, run_seed)` in both arms → same `identity_seed` → tightest paired-delta CI.
4. **Cost model = wizard preview ("≈ 50 + 50 = 100 agents") + 200-agent total cap.** Wizard-side `WIZARD_PER_ARM_CAP = 50` mirrors API's `PYTHIA_MAX_AGENTS`; `CONFIRM_TOTAL_AGENTS_THRESHOLD = 100` gates a "this is a big run" acknowledgement before submit.

**Codex regression-gate paid off on #89.** Two rounds of review:
- Round 1: 2 P1s (split-first allocation halved the cohort + the unguarded wizard toggle would render confidence_score as if it were lift) + 1 P2 (API constructors dropping `row["arm"]`).
- Round 2: 1 P2 (non-0.5 fractions silently overridden by cap → tightened schema to f=0.5 only).
- Round 3 (after lock): GATE PASS.

If `prompt_composer.py` ever gets touched again, the #77 anti-template guards (`"Honestly, I'm not"`, `"As someone who"`, `"mixed feelings"`, `"interesting proposed change"`) must stay applied to BOTH arms or paired comparison collapses to "comparison of templated drift."

## Operational lessons (don't re-trip)
- **Toggle a feature flag only when the END-USER-VISIBLE consequence is correct, not when the layer you just wrote is done.** #89 wired the dual-arm runner but flipping `AB_MODE_DISABLED_UNTIL_89` would have shown PMs a confidence-score-over-mixed-cohort number that looks like lift. Codex P1 caught it. Rename the gate to point at the actual unblock (e.g. `_UNTIL_LIFT`) so it doesn't accidentally flip on the wrong PR.
- **"Per-arm" vs "total" semantics ambiguity bites at f=0.5 the worst.** When a code path splits a total into two halves, both halves work mathematically — but the user-facing cost preview promised the OTHER interpretation. Whenever a wizard preview says "N + N = 2N," the runner must treat N as per-arm, not split a 2N total. Codex P1 caught it.
- **Tighten the schema instead of fixing dead code paths.** Codex round-2 flagged non-0.5 fractions getting silently overridden. The cheap fix (apportion the cap across arms) would defend a code path the product hasn't decided to support. The right fix was `ge=0.5, le=0.5` — re-open when there's a product reason AND a scorer.
- **`npx next build` poisons the running `npm run dev` chunk cache.** Hit multiple times in Phase 4. Gate is `tsc --noEmit` + live smoke; codex catches what tsc misses. NEVER run `next build` against a running dev server.
- **Service contracts NEVER raise after irreversible work.** Codex #80/#82/#85 all flagged variants. Apply to every new service path in 4.6 — especially anything that touches the prompt+LLM call chain.
- **Schema additions for v2 features stay backwards-compatible.** New optional fields with `None` defaults so older `result_json` values still load. New NULL columns for back-compat with pre-feature rows.
- **The auto-mode classifier blocks cross-repo writes even after explicit user authorization.** Prepared content handed off manually for `pythia-personas` + `pythia-crawler` AGENTS.md updates.

## For my cofounder
**Phase 4.6 is ~3/6 tickets shipped (2026-05-26 end-of-day).** #87 (design locks), #88 (schema + wizard input), #89 (dual-arm runner + control-arm prompt) are on main. The end-user feature is NOT live yet — the wizard A/B toggle is still gated behind `AB_MODE_DISABLED_UNTIL_LIFT` because the result page would render confidence_score over a mixed cohort instead of lift. That gate flips when #90 (paired lift formula) and #91 (lift display) both land.

**Next ticket: #90 paired bootstrap on per-agent sentiment delta.** Eng-locked at `/plan-eng-review`. `aggregate_ab()` over `AgentRecord[]`, match by `(persona_id, sample_index)`, drop unpaired, return `LiftResult` with point estimate + CI. Unit tests against known-answer fixtures.

**Direct API path is live for testing.** A POST to `/simulations` with `arm_split={"treatment_fraction": 0.5}` runs both arms end-to-end and writes `treatment` / `control` to `agent_instances.arm`. Useful for ad-hoc smoke testing #90 once it lands.

To pick this up: `/pythia-session resume phase-4.6-ab-experiment-mode`, then read `docs/4.6-ab-experiment-mode.md` (the locked decisions) and start #90. The runner side is done.
