---
type: session
domain: phase-4.6-ab-experiment-mode
status: active
started: 2026-05-26
owner: ram-de
---

# Session: phase-4.6-ab-experiment-mode — A/B experiment mode (treatment vs control)

## Goal
Ship Phase 4.6: extend the simulator to run two arms (treatment + control), compute a predicted lift between them, and surface it in the result UI. Builds on the Phase 4 chat infrastructure (agents, identity_seed, scoring, result table) which all shipped on 2026-05-26.

## In Progress
- [ ] **#87 — design: A/B experiment mode scope (CEO + Eng review)**. Lock four decisions before any code: (1) control-arm artifact shape, (2) score-formula choice, (3) paired vs independent sampling, (4) cost model. Output is `docs/4.6-ab-experiment-mode.md`. Blocks every other 4.6 ticket.

## Completed
(nothing yet — session just started)

## Next Steps
**Phase 4.6 implementation order (tickets filed 2026-05-26):**

1. **#87 design scope** — `/plan-ceo-review` on (1) control-arm artifact + (3) paired vs independent + (4) cost model; `/plan-eng-review` on (2) score formula. Produce `docs/4.6-ab-experiment-mode.md`. ROADMAP.md updated from "deferred" to "in progress".
2. **#88 schema + wizard arm-split input** — `SimulationRequest.arm_split: ArmSplit | None`. Wizard adds an experiment-mode toggle + treatment-fraction slider + cost preview. Backwards-compat: single-arm sims unchanged. Smallest cohesive change; ships before runtime/scoring redesign.
3. **#89 control-arm prompt + dual-arm orchestrator** — variant of `compose_identity_prompt` for the status-quo arm; `SimulationRunner` materializes both cohorts with `arm: "treatment" | "control"` tag; identity_seed paired or independent per #87. Codex gate (touches `prompt_composer.py` — #77 regression risk).
4. **#90 lift formula + paired CI** — `SimulationResult.lift` + `lift_ci` (formula per #87). Unit tests against known-answer fixtures (similar shape to `test_statistics.py`). Per-arm `confidence_score` calculations preserved unchanged.
5. **#91 frontend: result-table arm split + lift display** — big-number lift card above the table; persona-grouped table splits into treatment/control sections. Backwards-compat: single-arm sims render exactly as today.
6. **#92 e2e dogfood with calibration hypotheses** — three runs (expected-lift / expected-null / expected-negative-lift) against the demo Persona Pack. Same dogfood pattern that surfaced #77 + #78 in Phase 4. Documents PM-read interpretations. Closes Phase 4.6.

## Key Files
- `sessions/ab-experiment-mode/context.md` — the prior strategic-decision session that deferred this to post-Phase-4. Read it FIRST before re-litigating Product B (rejected) or the four open Q's.
- `ROADMAP.md` — has the deferral note and the trigger-to-re-open language. Update from "deferred 2026-05-26" to "in progress" as part of #87.
- `docs/agent-chat-ui-spec.md` — Phase 4 chat surfaces. Unchanged by 4.6: existing 1:1 + persona-group chat surfaces handle drill-down from either arm with no changes.
- `backend/pythia_simulator/services/prompt_composer.py` — extension point for the control-arm prompt (#89). The #77 anti-template opener guidance MUST stay applied to both arms.
- `backend/pythia_simulator/services/simulation_runner.py` — `SimulationRunner` is the extension point for dual-arm execution.
- `backend/pythia_simulator/services/scoring.py` — extension point for lift calculation (#90).
- `backend/pythia_simulator/services/identity_seed.py` — paired-sampling decision lands here. `draw_identity_seed(persona, sample_index, run_seed)` is already deterministic; "paired" just means treatment + control use the SAME args.
- `backend/pythia_simulator/services/statistics.py` — home for the lift bootstrap / t-test / credible-interval helpers (#90).
- `backend/pythia_simulator/schemas/simulation.py` — `SimulationRequest` + `SimulationResult` schema extensions for #88 + #90.
- `frontend/app/simulations/new/page.tsx` — wizard input for #88.
- `frontend/app/simulations/[id]/page.tsx` — result-page lift display for #91.

## Key Context

**Phase 4 finished today (2026-05-26)** with #51 (sentiment chip + top quote) + #56 (calibration thumbs) + a major collective-mode pivot mid-session. Suite is at 257 backend tests. The re-open trigger for 4.6 ("Phase 4 shipping + PM watching transcripts") is met.

**The product framing is locked.** Per `sessions/ab-experiment-mode/context.md`:
- **Part (a) — A/B simulator extension** is THIS session's scope (Phase 4.6).
- **Part (b) — plug-and-play A/B analyzer for real A/B data** was rejected outright. Eppo/GrowthBook/Statsig territory; dilutes the agent-simulation moat. The natural home if we ever build it is Phase 9 Layer-3 calibration (real A/B outcomes as ground truth signal, not a standalone product). Do not re-litigate.

**Four open design decisions (#87):**

1. **Control-arm artifact.** What does the LLM see to react to the CURRENT product, with NO proposed change? Probably an explicit "current-state product description" doc per capability, separate from the proposed-change prose. Possibly auto-derivable from the Feature Pack.
2. **Score formula.** Paired bootstrap on per-agent sentiment delta vs Welch's t-test on arm-level mean vs Bayesian credible interval. Each has tradeoffs; `/plan-eng-review` it.
3. **Paired vs independent sampling.** Same `(persona_id, sample_index, run_seed)` in both arms = paired (cleaner statistically). Fresh draws = independent (matches real A/B more closely). Taste call; `/plan-ceo-review`.
4. **Cost model.** A 50-population sim becomes 100 agents (~2× LLM cost + latency). Price before customers sign.

**Identity-continuity invariant survives.** The chat surfaces (1:1 + persona-group + collective) are arm-agnostic. A PM clicks an agent and drills into its `/agents/[id]` page — that agent is either treatment or control, and the chat with it just continues from its frozen identity. No new chat surface needed for v1.

**Codex regression risk on #89.** `prompt_composer.py` is the file that took the #77 templated-opener fix. Touching it again means we need to be paranoid about regressing that work. The opener guidance (`### How to open` sub-section) MUST stay applied to both arms, and the codex review on #89 should explicitly check for that.

**The dogfood loop is the calibration gate.** Phase 4's #77 + #78 are the case study: PM-side eyes on real output is the only reliable surface for AI-slop / hidden-contradiction bugs. #92 is the explicit dogfood ticket for 4.6 with three calibration hypotheses (expected-lift, expected-null, expected-negative-lift) — if those three don't come out where we expect, something is broken upstream.

## Operational lessons (don't re-trip)
- **`npx next build` poisons the running `npm run dev` chunk cache.** Hit multiple times in Phase 4. Gate is `tsc --noEmit` + live smoke; codex catches what tsc misses. NEVER run `next build` against a running dev server.
- **Service contracts NEVER raise after irreversible work.** Codex #80/#82/#85 all flagged variants of this: a 500 after fan-out / load / append invites a client retry that doubles down on upstream state. Apply to every new service path in 4.6 — especially anything that touches the prompt+LLM call chain.
- **Schema additions for v2 features stay backwards-compatible.** New optional fields with `None` defaults so older `result_json` values still load. Pinned by `test_agent_summary_fields_are_none_for_pre_51_result_json`-style tests.

## For my cofounder
**Starting Phase 4.6 — A/B experiment mode (treatment vs control).** This was deferred from Phase 4 on 2026-05-26 and the trigger to re-open ("Phase 4 shipping + PM watching transcripts") is met. Six tickets filed (#87 → #88 → #89 → #90 → #91 → #92).

**The plan:** lead with #87 (pure design work, `/plan-ceo-review` + `/plan-eng-review`) to lock four open decisions before any code. After #87 produces `docs/4.6-ab-experiment-mode.md`, the code tickets follow in order. Phase 5a #68 (Postgres wiring) was the other reasonable next thing — deliberately deferred until #87 clarifies actual 4.6 scope, since 5a is small enough to interleave between #90 and #91 if dogfood reveals state-loss is a real problem.

**Estimated:** 1-2 weeks per the prior session, but #87 will tighten that estimate.

To pick this up: `/pythia-session resume phase-4.6-ab-experiment-mode`, read `sessions/ab-experiment-mode/context.md` (the strategic decision) + ROADMAP's "A/B experimentation mode (deferred 2026-05-26)" entry, then run `/plan-ceo-review` against ticket #87 with the four open questions.
