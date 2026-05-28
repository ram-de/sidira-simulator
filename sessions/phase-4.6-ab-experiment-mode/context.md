---
type: session
domain: phase-4.6-ab-experiment-mode
status: active
started: 2026-05-26
closed: 2026-05-27
reopened: 2026-05-28
owner: ram-de
---

# Session: phase-4.6-ab-experiment-mode -- A/B experiment mode (treatment vs control)

## Goal
Ship Phase 4.6: extend the simulator to run two arms (treatment + control), compute a predicted lift between them, and surface it in the result UI. Builds on Phase 4 chat infrastructure (agents, identity_seed, scoring, result table) which all shipped 2026-05-26.

## In Progress
- [ ] **#99 -- de-asymmetric A/B per-arm confidence-score display.** Frontend implementation is done and verified locally (`npm run typecheck` + Playwright smoke with stubbed A/B data and real single-arm page). Next: codex review, commit, push, PR.

## Completed
- **#92 -- e2e calibration dogfood** (2026-05-27). Four wizard-driven A/B sims against `streamly_sample` (3 cleanly-predicted hypotheses + one re-run after an informative PM-prediction miss). Writeup in `docs/4.6-ab-experiment-mode.md` § "#92 e2e dogfood calibration (2026-05-27)". Calibration verdict: 3/3 cleanly-predicted hypotheses directionally confirmed (Skip Intro +15.9 [+9.6,+21.8]; Resume->Continue rename +10.0 [+1.8,+18.2] (borderline-null); remove-recs/A-Z-grid -11.2 [-19.8,-3.1]). The one PM-prediction override (autoplay-next-episode -10.5 [-21.0,-0.8]) was Pythia correctly catching the well-known autoplay-is-divisive dynamic the PM intuition missed. Zero drop counters across all runs. Pythia's lift formula is calibrated for production PM use.
  - Three #92-discovered findings carved out as separate tickets (filed 2026-05-27):
    - **#98** -- frontend: arm-scoped persona-group chat in A/B mode. PMs immediately want persona-group chat back; currently disabled per codex R2-P2 on #91. First dogfood question was literally "why can't I chat with the persona group?" Recommended: split into Treatment / Control rooms.
    - **#99** -- frontend: de-asymmetric the A/B per-arm confidence-score display. Control arm skips the weakness classifier per #90 contract, so "Treatment 34 / Control 59" reads as "treatment is 25 points worse" when the only apples-to-apples number is `lift`. Recommended: visual de-emphasis of per-arm scores in A/B mode + lift-first layout.
    - **#100** -- wizard: reconcile A/B cost preview with backend per-arm cap. Wizard preview says 50/arm; backend clamps to 20-25. Recommended: surface PYTHIA_MAX_AGENTS via a config endpoint.
  - Also closed stale issue **#90** (Phase 4.6 scoring) — PR #96 shipped 2026-05-26 but the merge commit didn't auto-close it.
- **#91 -- frontend: result-table arm split + lift display** (MERGED PR #97, commit `7f8f76a`, 2026-05-27).
  - **New `LiftCard` component** (`frontend/app/simulations/[id]/page.tsx`) above the confidence-score card. Big sign-coloured number (green/red, gray for `|lift| < 0.5`), 95% CI in confidence-score units with sign formatting, "CI crosses zero" caveat, paired-N footnote, drop counters surfaced inline. Copy explicitly names the metric ("predicted synthetic-agent reception, not a real business metric") -- this came from a live PM-read failure during smoke testing ("what's this lift on? what metric?") and is load-bearing for #92 dogfood interpretation.
  - **Confidence-score card** relabels to "Treatment arm confidence" in A/B mode + adds a Control-arm sub-row using `result.control_score`. Headline number stays `confidence_score` (= treatment arm per #90 contract).
  - **`PersonaGroupedAgents`** detects A/B and renders T | C twin chips per persona row; expanded view splits into Treatment / Control sub-sections via new `ArmAgentSubList`. Persona summary quote pinned to `treatmentAgents` only with a `TREATMENT` tag chip via new `TopQuoteLine.armLabel` prop -- the longest quote across mixed arms would otherwise surface a control-arm reaction labelled implicitly as treatment.
  - **`AB_MODE_DISABLED_UNTIL_LIFT = false`** in the wizard (`frontend/app/simulations/new/page.tsx:53`). Wizard A/B toggle is LIVE end-to-end now. Constant + staged-rollout-note plumbing kept as a one-line emergency rollback path -- worth deleting after #92 dogfood validates the feature for a couple of weeks.
  - **`AgentSummary.arm: Literal["treatment", "control"] | None`** added in `backend/pythia_simulator/api/simulations.py` (backwards-compatible -- legacy rows + single-arm sims return `arm=None`, and the frontend treats the table as A/B only when ANY row has a non-None arm).
  - **Codex review: 5 rounds, 4 P2s, ZERO P1s, ALL fixed. Round 5 = GATE PASS.** Every finding was a real correctness issue in the same family -- "are we correctly distinguishing A/B-mode from single-arm at the UI layer?":
    - R1-P2: gated lift card on `result.lift != null` -- collapsed "single-arm" and "A/B with no matched pairs" together (the latter has `lift=null + paired_n=0` per #90 codex R3-P2b). First fix: gate on `lift_paired_n != null`.
    - R2-P2: persona-group chat route fans out by `persona_id` with no arm filter -- A/B PMs clicking "💬 chat" would get a mixed treatment+control room. Disabled the persona-chat link in A/B mode (1:1 chat unaffected since each agent has a known arm). Arm-scoped persona-group chat = a separate follow-up ticket (touches the chat backend).
    - R3-P2a: population banner showed `sampled: 50 agents` on A/B runs that materialized 100 (50 T + 50 C). Append `per arm -- 2N total across treatment + control` in A/B mode.
    - R3-P2b: persona summary quote could be a control-arm reaction shown as if it were treatment. `pickGroupQuote(treatmentAgents)` in A/B + TREATMENT label chip.
    - R4-P2: fully-failed A/B run (zero successful agents, LLM outage) returns the generic single-arm placeholder result with NO `lift_paired_n` at all -- the R1 fix gate misclassified that as single-arm. THE FIX: gate everything off `sim.arm_split != null` (request-level truth) instead of result-shape fields. LiftCard internally handles three result variants: real lift / no-pairs / fully-failed.
  - The R4 pivot is the load-bearing one for future A/B-mode UI changes: `sim.arm_split` is the ONLY field that reliably says "user asked for A/B," and the rule "anything A/B-conditional keys off sim.arm_split, not result shape" generalizes. The result shape may be missing/broken; the request can't.
  - **CONFIRMED LIVE on main**: -20.5 lift from local smoke (negative-lift hypothesis), CI `[-25.9, -15.4]` excluded zero, 50 paired agents, persona table arm-split rendered correctly. Single-arm sim regression-check: untouched.
- **#90 -- lift formula + paired CI** (MERGED PR #96, commit `a58443d`, 2026-05-26).
  - `services/scoring.py`: new `aggregate_ab(treatment_analyses, control_analyses, cfg, run_seed) -> (treatment_result, control_result, ABLiftResult)` does per-arm aggregate + paired bootstrap. `_mean_paired_delta` computes the locked Q2 statistic (mean per-pair sentiment delta scaled by `sentiment_weight * 100` into confidence_score units); same statistic drives both point estimate and bootstrap CI so the CI brackets lift by construction. `_match_paired_analyses` matches by `(persona_id, sample_index)`, drops sentiment_failed pairs, surfaces 3 drop counters (unpaired_treatment, unpaired_control, sentiment_failure_drops). `_agent_delta` uses shrinkage-toward-neutral (`c * value + (1-c) * 0.5`) -- codex R4-P1 caught that the naive `c * value` silently strips confidence for NEGATIVE (value=0).
  - `ScoringService.score_ab(hypothesis, treatment_reactions, control_reactions, ...) -> (composed_result, analyses)`: parallel fan-out across both arms, composes a single `SimulationResult` with per-arm scores + lift fields. Headline `confidence_score` = treatment arm. One-arm-empty short-circuits to a degraded placeholder naming the missing arm (no LLM burn).
  - `ScoringService.analyze` is arm-aware: control reactions go through `_SENTIMENT_SYSTEM_CONTROL` ("user reacting to the product TODAY"), and weakness classification is **skipped** for control (the 6 categories describe experiment-design weaknesses in the proposed change, undefined for status-quo). New `weakness_attempted: bool = True` field on AgentAnalysis makes the aggregate degradation gate divide by attempted classifications, not 2N.
  - `services/simulation_runner.py`: `_score()` detects A/B mode via any `record.arm` and routes to `score_ab`. Missing-arm placeholder skips refinement (codex R6-P2 -- no LLM burn on broken runs).
  - `schemas/simulation.py`: `SimulationResult` gains 8 lift fields (`treatment_score`, `control_score`, `lift`, `lift_ci`, `lift_paired_n`, `lift_unpaired_treatment`, `lift_unpaired_control`, `lift_sentiment_failure_drops`), all None/0 defaults for back-compat. `paired_n=0` passes through verbatim (codex R3-P2b -- distinguishes "A/B attempted, no pairs matched" from "single-arm sim").
  - `schemas/scoring.py`: new `ABLiftResult` model + `AgentAnalysis.sample_index` (paired-matching key) + `AgentAnalysis.weakness_attempted`.
  - **Codex review: 6 rounds, 1 P1 + 6 P2s, ALL fixed. Round 7 = GATE PASS.** The findings, in order:
    - R1-P1: lift point and CI bootstrapped different statistics -> CI could exclude lift at small N (fixed by computing both from the same matched-subset statistic).
    - R1-P2: `set` iteration order of matched_keys was hash-randomized -> `run_seed` didn't actually give reproducible CIs (fixed by `sorted(matched_keys)`).
    - R2-P1: control reactions were scored with treatment-arm prompts that said "proposed product change" (fixed with `_SENTIMENT_SYSTEM_CONTROL` + skip weakness).
    - R2-P2: R1-P1 fix dragged weakness signal into lift -> broke the locked Q2 formula (reverted to sentiment-only paired delta, kept R1-P1 invariant since both point and CI now use the same delta statistic).
    - R3-P2a: control arm's `failed / 2N` denominator never tripped the strict `>` degradation gate (fixed with `weakness_attempted` flag).
    - R3-P2b: `paired_n=0` was coalesced to None (passthrough fix).
    - R4-P1: `c * value` silently dropped confidence for NEGATIVE (fixed with shrinkage-toward-neutral).
    - R5-P2: one-arm-empty A/B run looked like "treatment terrible" (degraded placeholder with named missing arm).
    - R6-P2: runner still ran refinement on missing-arm placeholder (skip refinement when `ab_missing_arm`).
  - Backend suite: 287 -> **312 passes**, 10 skips. 25 new tests (13 aggregate_ab + 4 arm-aware scoring + 3 confidence-weighting + 2 missing-arm + 2 degradation + 1 score_ab composition).
- **#87 -- design: A/B experiment mode scope** (CLOSED 2026-05-26). `/plan-ceo-review` locked Q1=B (reuse `Capability.reverse_prd` as the control-arm artifact), Q3=Paired sampling, Q4=wizard preview + 200-agent cap. `/plan-eng-review` locked Q2=paired bootstrap on per-agent sentiment delta. Output: `docs/4.6-ab-experiment-mode.md`. ROADMAP flipped from "deferred" to "in progress."
- **#88 -- schema + wizard arm-split input** (MERGED PR #93). `ArmSplit` Pydantic model + `arm_split: ArmSplit | None = None` on `SimulationRequest` / `Simulation`. Alembic 004 added `simulations.treatment_fraction` (Float, nullable). Wizard renders the toggle + cost preview + confirm-if-large; staged-rollout gate kept the toggle disabled because #89 wasn't wired yet. Codex P1 caught the silent-mismatch risk and forced the gate.
- **#89 -- dual-arm orchestrator + control-arm prompt** (MERGED PR #95, commit `2de943c`, 2026-05-26).
  - `compose_identity_prompt(arm: "treatment" | "control" = "treatment")` -- split into `_PREAMBLE_TEMPLATE` + `_TREATMENT_TASK_BLOCK` + `_CONTROL_TASK_BLOCK`. Preamble (persona / about-you / behavioral snapshot / product-today) byte-identical across arms -- the paired-comparison invariant. Control arm drops the proposed-change section + opener anchor, reframes the task as "react to the current product TODAY," adds an explicit "do not speculate" guard. All #77 anti-templated-opener guards preserved on BOTH arms.
  - `SimulationRunner.run(treatment_fraction)` -- when set, two `allocate()` calls produce per-arm specs. At the locked f=0.5, both calls receive identical inputs -> byte-equivalent `(persona_id, sample_index)` keys -> `draw_identity_seed` returns matching seeds per pair -> paired sampling for free.
  - `AgentInstance.arm: VARCHAR(16) NULL` (alembic 005) -- pinned at materialization, never changes (identity-continuity invariant). NULL for single-arm sims.
  - `AgentRecord` carries `sample_index` + `arm` so #90's lift formula can match pairs by tuple.
  - Orchestrator threads `treatment_fraction` from `prepare()` -> runner; API metadata constructors (`api/agents.py`, `api/feedback.py`, `api/persona_groups.py`) propagate `row["arm"]`.
  - **`ArmSplit.treatment_fraction` is now LOCKED at exactly 0.5** (`ge=0.5, le=0.5`). Codex round-2 caught that non-0.5 splits get silently overridden by the per-arm `max_agents` cap (e.g. f=0.8 + pop=1000 + cap=50 produces 50/50, not 80/20), AND #90's paired lift formula requires f=0.5 anyway. Re-open the range only when there's a product reason for asymmetric arms AND a scorer that supports them.
  - **Wizard A/B toggle stays gated** behind `AB_MODE_DISABLED_UNTIL_LIFT` (renamed from `AB_MODE_DISABLED_UNTIL_89`). The runner produces dual-arm output, but `ScoringService` still runs the single-arm path, so the result page would render `confidence_score` over a mixed treatment+control cohort -- a number that looks like predicted lift but isn't. Direct API still accepts `arm_split` for #89's dual-arm runner tests. The toggle flips when #90 (paired lift) + #91 (lift display) both land.
  - Codex review: 2 rounds, 3 P1s + 2 P2s, ALL fixed. Final round: GATE PASS. Backend suite: 287 passes / 10 skips.
- **Mid-session scope-adds (shipped on the way to #89):**
  - **Per-category weakness info button on result page** (MERGED PR #94). Click-to-expand popover with PM-readable definitions for all 6 weakness categories. Codex P2 caught wrong_cohort (sample-size framing instead of relevance/targeting) and underpowered_design (didn't cover the degradation-gate path); both rewritten to match the canonical classifier prompt in `services/scoring.py`.
  - **Cross-repo "/codex review on every PR" rule** (MERGED via `25e85b3` on `pythia-simulator` AGENTS.md). Auto-mode classifier blocked the cross-repo writes to `pythia-personas/AGENTS.md` and `pythia-crawler/AGENTS.md` even after explicit authorization -- prepared content was handed to the user to paste manually. **Cross-repo carryover: still pending on `pythia-personas` + `pythia-crawler`.**

## Next Steps
1. Run codex review on the #99 diff.
2. Commit + push `codex/99-de-asymmetric-ab-scores`.
3. Open PR with `Closes #99`; update this session when merged.

## Key Files
- `docs/4.6-ab-experiment-mode.md` -- LOCKED decisions (Q1=B, Q2=paired bootstrap, Q3=paired, Q4=wizard preview + 200 cap). Single source of truth before code.
- `ROADMAP.md` -- A/B mode entry is "in progress as Phase 4.6."
- `sessions/ab-experiment-mode/context.md` -- the prior strategic-decision session. Do NOT re-litigate Product B (rejected) or the four questions (locked).
- `backend/pythia_simulator/services/prompt_composer.py` -- split into preamble + treatment/control task blocks. The #77 anti-template guards apply to BOTH arms.
- `backend/pythia_simulator/services/simulation_runner.py` -- dual-arm dispatch on `treatment_fraction`. Per-arm semantics: `population_size` is the per-arm target, NOT the total to split (Codex P1 #95 lesson).
- `backend/pythia_simulator/services/scoring.py` -- extension point for #90 paired-lift aggregator.
- `backend/pythia_simulator/services/identity_seed.py` -- `draw_identity_seed(persona, sample_index, run_seed)` is deterministic; paired sampling rides on identical args across arms.
- `backend/pythia_simulator/services/statistics.py` -- home for #90 bootstrap helpers.
- `backend/pythia_simulator/schemas/simulation.py` -- `ArmSplit` now locks `treatment_fraction=0.5`. `SimulationResult` schema extension lands in #90.
- `backend/pythia_simulator/adapters/db_models.py` -- `Simulation.treatment_fraction` (Float, alembic 004) + `AgentInstance.arm` (VARCHAR(16), alembic 005). Both nullable for back-compat.
- `frontend/app/simulations/new/page.tsx` -- `AB_MODE_DISABLED_UNTIL_LIFT` gate. Flip in #91.
- `frontend/app/simulations/[id]/page.tsx` -- #91 lift card lives here; weakness info popover already in.
  - #99 changes here: A/B mode now renders `PerArmDetailCard` instead of the prominent confidence-score card; single-arm rendering stays unchanged.

## Key Context

**Phase 4.6 #88 + #89 + #90 + #91 are DONE on main as of 2026-05-27, and #92/#98 follow-ups have also shipped.** The wizard A/B toggle is LIVE end-to-end -- a PM can flip the A/B toggle, submit a sim with 50+50 agents, and read the lift card with CI on the result page. Backend suite at **312 passes / 10 skips** at the original close point.

**Session reopened 2026-05-28 for #99.** This is a Phase 4.6 follow-up carved out of #92: per-arm confidence scores are structurally asymmetric because the treatment arm includes the weakness debit and the control arm skips weakness classification. The UI fix is frontend-only: lift remains the A/B headline; per-arm scores become secondary detail with copy warning that only Lift is apples-to-apples.

**Lift statistic (locked Q2):** mean per-pair confidence-weighted sentiment delta, scaled by `sentiment_weight * 100` into confidence_score units. NOT the per-arm confidence_score diff (weakness signal stays in per-arm scores). Point estimate AND bootstrap CI use the same statistic, so the CI brackets lift by construction. Confidence weighting uses shrinkage-toward-neutral: `value_shrunk = c * value + (1-c) * 0.5` -- symmetric across POS/NEU/NEG (the naive `c * value` would have silently dropped confidence for NEGATIVE).

**Arm-aware scoring at the LLM call site.** `ScoringService.analyze` routes control reactions through `_SENTIMENT_SYSTEM_CONTROL` (frames reception as feelings-about-the-current-product) and skips weakness classification entirely for control (the 6 categories are experiment-design weaknesses in the proposed change, undefined for status-quo). `AgentAnalysis.weakness_attempted` makes the degradation gate count by attempted classifications instead of 2N.

**Result-shape contract for #91:**
- `result.lift: float | None` -- paired lift in confidence_score units (range [-100, +100]), None when uncomputable.
- `result.lift_ci: tuple[float, float] | None` -- 95% bootstrap CI in same units.
- `result.treatment_score` / `result.control_score: float | None` -- per-arm full-arm confidence_scores.
- `result.lift_paired_n: int | None` -- None for single-arm sims, 0 for "A/B attempted but no pairs", N>0 for matched-pair count.
- `result.lift_unpaired_treatment` / `lift_unpaired_control` / `lift_sentiment_failure_drops: int` -- drop counters (default 0).
- Single-arm sims keep `lift=None` and all lift_* fields at defaults -> frontend can branch on `result.lift is not None` for the lift card render.

**Per-arm allocation is now the rule (Codex P1 #95).** `population_size` in dual-arm mode is the PER-ARM target, not a total to split. At wizard defaults (pop=50, cap=50, f=0.5) the runner produces 50 treatment + 50 control = 100 agents -- matching the wizard cost preview. Pair matching works at odd populations too (pop=7 -> 7+7, all paired). The prior `int(pop * 0.5)` math is gone.

**Identity-continuity invariant survives.** `AgentInstance.arm` is pinned at materialization (`memory/agent_memory.py` guarantees) and never changes. Chat surfaces (1:1 + persona-group + collective) are arm-agnostic -- a PM clicks an agent and the chat continues from its frozen identity regardless of arm.

**Four locked design decisions (closed in #87):**
1. **Control-arm artifact = `Capability.reverse_prd`.** No new schema. Composer drops the proposed-change section in the control arm.
2. **Score formula = paired bootstrap on per-agent sentiment delta.** Drop counters for unpaired agents. Degenerate cases: zero pairs, all-positive deltas, all-zero deltas.
3. **Sampling = paired.** Same `(persona_id, sample_index, run_seed)` in both arms -> same `identity_seed` -> tightest paired-delta CI.
4. **Cost model = wizard preview ("~ 50 + 50 = 100 agents") + 200-agent total cap.** Wizard-side `WIZARD_PER_ARM_CAP = 50` mirrors API's `PYTHIA_MAX_AGENTS`; `CONFIRM_TOTAL_AGENTS_THRESHOLD = 100` gates a "this is a big run" acknowledgement before submit.

**Codex regression-gate paid off on #89.** Two rounds of review:
- Round 1: 2 P1s (split-first allocation halved the cohort + the unguarded wizard toggle would render confidence_score as if it were lift) + 1 P2 (API constructors dropping `row["arm"]`).
- Round 2: 1 P2 (non-0.5 fractions silently overridden by cap -> tightened schema to f=0.5 only).
- Round 3 (after lock): GATE PASS.

If `prompt_composer.py` ever gets touched again, the #77 anti-template guards (`"Honestly, I'm not"`, `"As someone who"`, `"mixed feelings"`, `"interesting proposed change"`) must stay applied to BOTH arms or paired comparison collapses to "comparison of templated drift."

## Operational lessons (don't re-trip)
- **For UI features in A/B mode, key everything off the REQUEST (`sim.arm_split`), not the RESULT shape.** Codex R4-P2 on #91. The result fields (`lift`, `lift_paired_n`, `control_score`) can be missing for at least three distinct reasons (single-arm sim, A/B with no matched pairs, fully failed A/B run) and gating UI off any one of them collapses subsets back together. The request-level field is the one source of truth that doesn't lie. Generalizes to any future A/B-mode UI conditional.
- **Copy that names what the metric IS prevents PM misread.** First-pass lift card said "−20.5 confidence-score points" -- live smoke produced the actual PM question "what's this lift on? what metric?" before any reviewer caught it. Copy now leads with "Synthetic-agent sentiment toward the proposed change vs. the current product -- a forecast of how the change will land, not a real business metric (orders, retention, conversion)." Worth doing this for every Pythia-specific metric on a result surface.
- **Toggle a feature flag only when the END-USER-VISIBLE consequence is correct, not when the layer you just wrote is done.** #89 wired the dual-arm runner but flipping `AB_MODE_DISABLED_UNTIL_89` would have shown PMs a confidence-score-over-mixed-cohort number that looks like lift. Codex P1 caught it. Rename the gate to point at the actual unblock (e.g. `_UNTIL_LIFT`) so it doesn't accidentally flip on the wrong PR.
- **"Per-arm" vs "total" semantics ambiguity bites at f=0.5 the worst.** When a code path splits a total into two halves, both halves work mathematically -- but the user-facing cost preview promised the OTHER interpretation. Whenever a wizard preview says "N + N = 2N," the runner must treat N as per-arm, not split a 2N total. Codex P1 caught it.
- **Tighten the schema instead of fixing dead code paths.** Codex round-2 flagged non-0.5 fractions getting silently overridden. The cheap fix (apportion the cap across arms) would defend a code path the product hasn't decided to support. The right fix was `ge=0.5, le=0.5` -- re-open when there's a product reason AND a scorer.
- **`npx next build` poisons the running `npm run dev` chunk cache.** Hit multiple times in Phase 4. Gate is `tsc --noEmit` + live smoke; codex catches what tsc misses. NEVER run `next build` against a running dev server.
- **Service contracts NEVER raise after irreversible work.** Codex #80/#82/#85 all flagged variants. Apply to every new service path in 4.6 -- especially anything that touches the prompt+LLM call chain.
- **Schema additions for v2 features stay backwards-compatible.** New optional fields with `None` defaults so older `result_json` values still load. New NULL columns for back-compat with pre-feature rows.
- **The auto-mode classifier blocks cross-repo writes even after explicit user authorization.** Prepared content handed off manually for `pythia-personas` + `pythia-crawler` AGENTS.md updates.

## For my cofounder
**Phase 4.6 is reopened for follow-up #99 (2026-05-28).** #87, #88, #89, #90, #91, #92, #98 are already shipped; #99 is now in progress. The goal is a frontend-only result-page cleanup: keep lift as the A/B headline and demote treatment/control confidence scores into explanatory detail because those two scores are not directly comparable.

**Current ticket: #99.** Treat this as a frontend follow-up, not a re-litigation of the A/B scoring formula. The scoring asymmetry is intentional; the UI needs to stop implying the two per-arm confidence scores should be subtracted.

**Codex review on #91 burned 5 rounds. The pattern was all one family: "are we correctly distinguishing A/B-mode from single-arm at the UI layer?"** The R4 lesson is the load-bearing one for everything downstream: gate A/B-conditional UI off `sim.arm_split` (the REQUEST), not result shape -- the result fields can be missing for at least three distinct reasons and any single-result-field gate collapses subsets together. This rule should generalize to any future A/B-mode UI conditional we add.

**Two #91 followups carved out into separate tickets (not Phase 4.6 blockers):**
1. Arm-scoped persona-group chat (currently disabled in A/B mode with a tooltip; clicking 1:1 chat on any agent still works fine).
2. Delete `AB_MODE_DISABLED_UNTIL_LIFT` constant + `stagedRolloutNote` plumbing after #92 dogfood proves out the feature.

To pick this up: `/pythia-session resume phase-4.6-ab-experiment-mode`, then start #92 -- pick three hypotheses with clear expected signs and run them at default settings (pop=50, f=0.5).
