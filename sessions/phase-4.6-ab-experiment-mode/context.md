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
- [ ] **#91 — frontend: result-table arm split + lift display**. Next ticket. Blocked on #90 has been cleared — paired-lift backend is in. Build the lift card above the result table + persona-grouped table arm-split. **Flip `AB_MODE_DISABLED_UNTIL_LIFT` → false in the same PR.** Backwards-compat: single-arm sims render unchanged.

## Completed
- **#90 — lift formula + paired CI** (MERGED PR #96, commit `a58443d`, 2026-05-26).
  - `services/scoring.py`: new `aggregate_ab(treatment_analyses, control_analyses, cfg, run_seed) -> (treatment_result, control_result, ABLiftResult)` does per-arm aggregate + paired bootstrap. `_mean_paired_delta` computes the locked Q2 statistic (mean per-pair sentiment delta scaled by `sentiment_weight × 100` into confidence_score units); same statistic drives both point estimate and bootstrap CI so the CI brackets lift by construction. `_match_paired_analyses` matches by `(persona_id, sample_index)`, drops sentiment_failed pairs, surfaces 3 drop counters (unpaired_treatment, unpaired_control, sentiment_failure_drops). `_agent_delta` uses shrinkage-toward-neutral (`c × value + (1−c) × 0.5`) — codex R4-P1 caught that the naive `c × value` silently strips confidence for NEGATIVE (value=0).
  - `ScoringService.score_ab(hypothesis, treatment_reactions, control_reactions, ...) -> (composed_result, analyses)`: parallel fan-out across both arms, composes a single `SimulationResult` with per-arm scores + lift fields. Headline `confidence_score` = treatment arm. One-arm-empty short-circuits to a degraded placeholder naming the missing arm (no LLM burn).
  - `ScoringService.analyze` is arm-aware: control reactions go through `_SENTIMENT_SYSTEM_CONTROL` ("user reacting to the product TODAY"), and weakness classification is **skipped** for control (the 6 categories describe experiment-design weaknesses in the proposed change, undefined for status-quo). New `weakness_attempted: bool = True` field on AgentAnalysis makes the aggregate degradation gate divide by attempted classifications, not 2N.
  - `services/simulation_runner.py`: `_score()` detects A/B mode via any `record.arm` and routes to `score_ab`. Missing-arm placeholder skips refinement (codex R6-P2 — no LLM burn on broken runs).
  - `schemas/simulation.py`: `SimulationResult` gains 8 lift fields (`treatment_score`, `control_score`, `lift`, `lift_ci`, `lift_paired_n`, `lift_unpaired_treatment`, `lift_unpaired_control`, `lift_sentiment_failure_drops`), all None/0 defaults for back-compat. `paired_n=0` passes through verbatim (codex R3-P2b — distinguishes "A/B attempted, no pairs matched" from "single-arm sim").
  - `schemas/scoring.py`: new `ABLiftResult` model + `AgentAnalysis.sample_index` (paired-matching key) + `AgentAnalysis.weakness_attempted`.
  - **Codex review: 6 rounds, 1 P1 + 6 P2s, ALL fixed. Round 7 = GATE PASS.** The findings, in order:
    - R1-P1: lift point and CI bootstrapped different statistics → CI could exclude lift at small N (fixed by computing both from the same matched-subset statistic).
    - R1-P2: `set` iteration order of matched_keys was hash-randomized → `run_seed` didn't actually give reproducible CIs (fixed by `sorted(matched_keys)`).
    - R2-P1: control reactions were scored with treatment-arm prompts that said "proposed product change" (fixed with `_SENTIMENT_SYSTEM_CONTROL` + skip weakness).
    - R2-P2: R1-P1 fix dragged weakness signal into lift → broke the locked Q2 formula (reverted to sentiment-only paired delta, kept R1-P1 invariant since both point and CI now use the same delta statistic).
    - R3-P2a: control arm's `failed / 2N` denominator never tripped the strict `>` degradation gate (fixed with `weakness_attempted` flag).
    - R3-P2b: `paired_n=0` was coalesced to None (passthrough fix).
    - R4-P1: `c × value` silently dropped confidence for NEGATIVE (fixed with shrinkage-toward-neutral).
    - R5-P2: one-arm-empty A/B run looked like "treatment terrible" (degraded placeholder with named missing arm).
    - R6-P2: runner still ran refinement on missing-arm placeholder (skip refinement when `ab_missing_arm`).
  - Backend suite: 287 → **312 passes**, 10 skips. 25 new tests (13 aggregate_ab + 4 arm-aware scoring + 3 confidence-weighting + 2 missing-arm + 2 degradation + 1 score_ab composition).
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
**Phase 4.6 implementation order (post-#90):**

1. **#91 frontend: result-table arm split + lift display (NEXT, unblocked)** — big-number lift card above the table reading `SimulationResult.lift` + `lift_ci` (in confidence_score units); persona-grouped table splits into treatment/control sections. **Flip `AB_MODE_DISABLED_UNTIL_LIFT` → false in the same PR.** Backwards-compat: single-arm sims (no `result.lift`) render exactly as today. Surface the drop counters (`lift_unpaired_treatment`, `lift_unpaired_control`, `lift_sentiment_failure_drops`) on the result page when nonzero — small inline note, not a banner.
2. **#92 e2e dogfood with calibration hypotheses (blocked on #91)** — three runs (expected-lift / expected-null / expected-negative-lift) against the demo Persona Pack. Same dogfood pattern that surfaced #77 + #78 in Phase 4. Documents PM-read interpretations. Closes Phase 4.6.

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

**Phase 4.6 #88 + #89 + #90 are DONE on main as of 2026-05-26.** A direct API caller can submit `arm_split={"treatment_fraction": 0.5}` and the simulator runs both arms with paired identity seeds, scores them with arm-aware prompts, and returns a `SimulationResult` with `lift` + `lift_ci` + drop counters populated. The wizard A/B toggle still stays disabled (`AB_MODE_DISABLED_UNTIL_LIFT`) until #91 wires the frontend lift display. Backend suite is at **312 passes / 10 skips**.

**Lift statistic (locked Q2):** mean per-pair confidence-weighted sentiment delta, scaled by `sentiment_weight × 100` into confidence_score units. NOT the per-arm confidence_score diff (weakness signal stays in per-arm scores). Point estimate AND bootstrap CI use the same statistic, so the CI brackets lift by construction. Confidence weighting uses shrinkage-toward-neutral: `value_shrunk = c × value + (1−c) × 0.5` — symmetric across POS/NEU/NEG (the naive `c × value` would have silently dropped confidence for NEGATIVE).

**Arm-aware scoring at the LLM call site.** `ScoringService.analyze` routes control reactions through `_SENTIMENT_SYSTEM_CONTROL` (frames reception as feelings-about-the-current-product) and skips weakness classification entirely for control (the 6 categories are experiment-design weaknesses in the proposed change, undefined for status-quo). `AgentAnalysis.weakness_attempted` makes the degradation gate count by attempted classifications instead of 2N.

**Result-shape contract for #91:**
- `result.lift: float | None` — paired lift in confidence_score units (range [-100, +100]), None when uncomputable.
- `result.lift_ci: tuple[float, float] | None` — 95% bootstrap CI in same units.
- `result.treatment_score` / `result.control_score: float | None` — per-arm full-arm confidence_scores.
- `result.lift_paired_n: int | None` — None for single-arm sims, 0 for "A/B attempted but no pairs", N>0 for matched-pair count.
- `result.lift_unpaired_treatment` / `lift_unpaired_control` / `lift_sentiment_failure_drops: int` — drop counters (default 0).
- Single-arm sims keep `lift=None` and all lift_* fields at defaults → frontend can branch on `result.lift is not None` for the lift card render.

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
**Phase 4.6 is 4/6 tickets shipped (2026-05-26 late evening).** #87 (design locks), #88 (schema + wizard input), #89 (dual-arm runner + control-arm prompt), and **#90 (paired-lift formula)** are all on main. The end-user feature is STILL NOT live — the wizard A/B toggle is gated behind `AB_MODE_DISABLED_UNTIL_LIFT` because the result page doesn't yet render lift. That gate flips when #91 lands.

**Next ticket: #91 frontend lift card + arm-split result table.** Reads `result.lift` / `result.lift_ci` / `result.treatment_score` / `result.control_score` from the backend (all wired). Backwards-compat: single-arm sims have `result.lift = None`, so the lift card only renders when `result.lift is not None`. Flip `AB_MODE_DISABLED_UNTIL_LIFT → false` in the same PR.

**Direct API path is live end-to-end now.** A POST to `/simulations` with `arm_split={"treatment_fraction": 0.5}` runs both arms, scores them with arm-aware prompts, computes paired lift with CI, and returns the full result shape. Useful for #91 dogfood — you can hit the API directly and inspect `result.lift` / `result.lift_ci` before wiring the frontend.

**Codex review burned 6 rounds on #90.** The lift formula has a lot of subtle gotchas (statistic consistency, set-iteration reproducibility, control-arm prompt mismatch, locked Q2 vs full per-arm diff, degradation-gate denominator, confidence-weighting math, missing-arm handling, refinement short-circuit). All landed correctly. If #91 or #92 touch the scoring math, re-run `/codex review` paranoia — this surface is fragile.

To pick this up: `/pythia-session resume phase-4.6-ab-experiment-mode`, read the new "Result-shape contract for #91" block in Key Context, then start the frontend work.
