# CONTEXT — Current Sprint Narrative

**This file is the team's shared running context.** Both founders read it. AI agents read it before picking up work. Keep it short (2–3 screens), keep it current.

**Last updated:** 2026-05-27 (#103 model selection shipped)

---

## What just shipped

✅ **#103 -- model selection, SHIPPED 2026-05-27 (PR #105, commit `ea5440e`, session `model-selection`).**
PMs can now pick the LLM provider/model that powers a simulation while preserving the Groq `llama-3.3-70b-versatile` default. Backend exposes `GET /models` filtered to configured providers, validates unknown/unavailable `model_id`s up front, persists the selected model on each simulation, and routes sim reactions, scoring, refinement, follow-up agent chat, persona-group collective fan-out, and synthesis through that same model. A/B mode uses one selected model for both arms so paired-lift math stays apples-to-apples. The wizard shows grouped Groq/Anthropic/OpenAI choices, and result pages show the model used while legacy rows with `NULL model_id` render as untracked instead of being mislabeled. Groq selection now includes GPT-OSS 120B, GPT-OSS 20B, Qwen3 32B, Llama 4 Scout, and the existing Llama defaults. Verification: backend 346 passed / 10 skipped, frontend typecheck clean, live `/models` + wizard rendering verified, Codex review clear.

✅ **#101 -- persona filter, SHIPPED 2026-05-27 (PR #102, commit `2a313c1`, session `persona-filter`).**
PMs can narrow a sim to a subset of personas via a checkbox list behind the wizard's "Advanced options" disclosure. Default unchanged (all personas). Allocator re-weights the selected personas' weights to sum to 1 before largest-remainder, so a 12%-weight persona selected solo gets the full 50 agents -- preserves the cohort sample size. New `GET /personas` endpoint feeds the wizard's checkbox list. Cohort banner on the result page surfaces "filtered to N of M personas: {names}" so a PM revisiting the page in two weeks remembers they filtered. A/B mode + filter compose symmetrically (same persona subset in both arms preserves the #89 paired-sampling invariant). Backend suite at 327 passed / 10 skipped (15 new #101 tests). Codex review: 2 rounds, 1 P2 fixed, R2 GATE PASS.

✅ **#98 -- arm-scoped persona-group chat, SHIPPED 2026-05-27 (PR #104, commit `bdac59b`, session `arm-scoped-persona-chat`).**
A/B persona rows now expose separate Treatment and Control persona-group chat rooms (`💬 T` / `💬 C`) instead of disabling group chat. Backend chat POST/GET routes accept `?arm=treatment|control`, filter fan-out/replay to that arm, and physically isolate transcripts under `persona_groups/<persona_id>/<arm>/turns.jsonl`. Persona-group feedback is also arm-scoped via `{sim_id}/{persona_id}/{arm}` target IDs so T/C turn indexes cannot collide. Direct/old A/B calls without `?arm=` now 400 instead of recreating the mixed treatment/control room. Empty-arm chat pills are disabled when a persona has no surviving agents in that arm. Verification: backend 331 passed / 10 skipped, frontend typecheck + build clean, Codex review clear.

---

## What just shipped (earlier)

✅ **Phase 4.6 -- A/B experiment mode, SHIPPED 2026-05-27 (session `phase-4.6-ab-experiment-mode`).**
PMs can now submit a hypothesis with the A/B toggle enabled, watch both treatment and control arms run with paired sampling, and read a predicted-lift card with bootstrap CI on the result page. All six tickets landed (#87 design / #88 schema + wizard input / #89 dual-arm runner + control-arm prompt / #90 paired-lift formula + CI / #91 result-page lift card + arm-split table + wizard toggle live / #92 e2e calibration dogfood). Wizard A/B toggle is live end-to-end. Backend suite at 312 passed / 10 skipped (same baseline #90 established).

- **#90 paired-lift formula (PR #96):** mean per-pair confidence-weighted sentiment delta scaled into confidence-score units, with paired bootstrap CI on the same statistic. Locked through 6 rounds of `/codex review` (1 P1 + 6 P2s, all fixed). Backend exposes `lift`, `lift_ci`, `treatment_score`, `control_score`, `lift_paired_n`, and three drop counters on `SimulationResult`.
- **#91 result-page lift card + arm-split table (PR #97):** new `LiftCard` component with sign-coloured big number, paired CI, drop-counter callouts, and clear "this is synthetic-agent reception, not a real business metric" copy (added after a live PM-read failure during smoke testing -- "what's this lift on? what metric?"). Persona table grows T|C twin chips with treatment-pinned summary quote. `AB_MODE_DISABLED_UNTIL_LIFT` flipped to false in same PR. Codex review: 5 rounds, 4 P2s all fixed, ZERO P1s. The load-bearing fix (R4): gate A/B UI on `sim.arm_split` (request-level truth), not result-shape fields, because results can be missing for at least three distinct reasons.
- **#92 e2e calibration dogfood (2026-05-27):** four wizard-driven sims against `streamly_sample` -- 3 cleanly-predicted hypotheses (Skip Intro +15.9 / Resume->Continue rename +10.0 borderline-null / remove-recs A-Z grid -11.2) all confirmed directionally. Bonus finding: PM-predicted autoplay-next-episode as expected-positive; Pythia returned -10.5 with 85% `hidden_guardrail_risk` weakness flag, correctly catching the well-known autoplay-is-divisive dynamic. Full writeup in `docs/4.6-ab-experiment-mode.md` § "#92 e2e dogfood calibration (2026-05-27)".

**Two followups carved out of #92 (separate tickets, not Phase 4.6 blockers):**
1. **#99** -- De-asymmetric the A/B result-page UX. Per #90 contract the control arm skips weakness classification, so per-arm side-by-side scores aren't on the same scale -- "Treatment 34 / Control 59" reads as "treatment is 25 points worse" when the only apples-to-apples number is `lift`. Recommended: visual de-emphasis of per-arm scores in A/B mode + lift-first layout.
2. **#100** -- Wizard cost preview vs. backend cap. Wizard says 50/arm; backend clamps to 20-25 in practice. Recommended: surface `SIDIRA_MAX_AGENTS` via a config endpoint (`PYTHIA_MAX_AGENTS` remains the legacy fallback during the rename).
3. Pure plumbing TODO (no ticket): delete `AB_MODE_DISABLED_UNTIL_LIFT` constant + `stagedRolloutNote` plumbing after the feature soaks for a couple of weeks.

**Lasting lesson from Phase 4.6:** for A/B-mode UI conditionals, key everything off the REQUEST (`sim.arm_split`), not the RESULT shape. The result fields can be missing for at least three distinct reasons (single-arm sim, A/B with no matched pairs, fully-failed A/B run), and gating on any single result field collapses subsets back together. Generalizes to any future A/B-mode UI conditional.

---

## What just shipped (earlier)

✅ **Magic Moment Sprint — Phases 2 + 3 done in one sitting (2026-05-21).**
A PM can submit a hypothesis through `/simulations/new`, see 6 personas react via real Groq LLM calls, and get a confidence score + 3 diagnosed weaknesses + 3 refinement suggestions rendered live on `/simulations/[id]`. Verified end-to-end with sim `63c778c8` returning score 30/100.

Waves 0–6 landed:
- Wave 0: 8 architecture decisions locked via `/plan-eng-review` (commit `6de33f8`)
- Waves 1–3: Postgres schema, Repository Protocol pattern, end-to-end POST /simulations (commits `69b34d8`, `cbabb2c`)
- Wave 4: Scoring + refinement services with locked `0.6 sentiment + 0.4 (1-weakness)` formula. Codex review fixups applied (`8c03641`, `71325b9`, PR #1)
- Wave 5: Frontend submit + result view + live polling, built via 2 parallel sub-agents (`808f689`, PR #2)
- Wave 6: T12 e2e demo, `/qa`, `/review`, `/retro`. Discovered + fixed CORS bug (`2713752`), shipped the simulation list view (`6b458a9`), three review fixups (`b39db2b`).

60/60 backend tests passing. Frontend typecheck clean. All on `main`.

Retrospective: `git show b39db2b` in conversation history, plus the lessons captured in the next section.

✅ **Phase 2.5 — Weighted Population Sampling, fully shipped (2026-05-22, session `weighted_population`).**
Six backend tickets + three frontend tickets + one follow-on backend endpoint. Suite 60 → 153 passed.

- **#7** Groq backoff with jitter (PR #59).
- **#57** schema swap: `population_size` replaces `persona_sample_size`; new `Weakness.frequency/ci_low/ci_high`, `SimulationResult.confidence_score_ci`, `AgentInstance.identity_seed`, `Persona.behavioral_seeds` fields (PR #60).
- **#58** `services/population_sampler.py` with Hamilton largest-remainder allocation (PRs #61 + #63).
- **#5** `services/identity_seed.py` — deterministic per-agent context (`age_band, locale_band, tenure_band, current_state, recent_gripe`) seeded from `(persona_id, sample_index, run_seed)` via sha256→int64. Splices into prompt; persisted to R2 as a sidecar (PR #64).
- **#6** Wilson CIs on weakness frequencies + percentile bootstrap (B=1000) on aggregate score. Pure-Python in `services/statistics.py`, no scipy dep. `ScoringConfig.bootstrap_resamples=0` is the test-fast skip sentinel. Determinism via `run_seed` mixed with a domain-separation XOR mask (PR #65).
- **#8** degradation guard: if >50% of LLM classifications fail, discount confidence_score by 30% and prepend an `underpowered_design` weakness explaining the rate. Two-gate collapse when low-N + degradation both fire (PR #66).
- **#9 + #10 + #51** frontend bundle: wizard rename `Sample size`→`Population` with stratification helper, Population banner, `ScoreCiBar` + `WeaknessFrequencyBar` visualizations, persona-grouped collapsible agent table. Live-test surfaced `GET /agents/{id}` is 501-stubbed for Phase 4 chat → added lightweight `GET /simulations/{id}/agents` summary endpoint to unblock #51 (PR #67).

End-to-end verified locally against a 12-population demo sim: Hamilton allocated 6 personas in correct weighted proportions; score 33 with bootstrap CI [30.0–39.1]; 3 weaknesses each with Wilson CIs; persona-grouped table renders and expands. **The calibration thesis is true in code AND visible in the UI.**

✅ **Second-vertical sample + customer resolver loosened (2026-05-22, session `sample_creations`).**
Shipped a `streamly_sample` customer fixture (video streaming, 6 personas, 2 capabilities, pre-registered "Smart Resume" hypothesis) and an env-var override on `current_customer_id()` so the same running backend can be pointed at any local-artifacts fixture without code edits. Verified live: sim `89d01a19-…` returned 6/6 real Groq persona reactions in ~13s. The `demo` flow is unchanged. Useful for pressure-testing that the simulator isn't accidentally food-delivery-shaped, and as a non-DoorDash demo surface.

Current gaps live in the [GitHub Project](https://github.com/users/ram-de/projects/) under their respective Phase tags (2.5 / 4 / 4.5 / 5). `ROADMAP.md` has the strategic "where we are today" view.

---

## What's next

Two reasonable paths from here; pick based on appetite:

**Path A — Phase 4 (Agent chat, the differentiator).** Bigger product win, more design surface to nail. See ticket list below.

**Path B — Phase 5a (Postgres wiring, #68).** ~1 day standalone. Right now every uvicorn restart wipes the simulation list because `InMemorySimulationRepo` is the wired-up repo (the Postgres adapter + schema both exist, just the FastAPI `AsyncSession` dep is stubbed). Worth landing before showing the simulator to anyone external, and a hard prereq for Phase 7 (Lumen MVP). Carved out of Phase 5 so the small persistence win doesn't wait for the Clerk + multi-tenancy work.

---

**Phase 4 — Agent chat (the differentiator).** PMs can talk to each agent that participated in a simulation. Infrastructure is already in place (`AgentMemory`, frozen `identity_seed`, R2 sidecars, `_CHAT_GUARD_PREFIX`); what's missing is the API + the chat surface.

Five open tickets:
- **#52** backend: un-stub `GET /agents/{id}` + `POST /agents/{id}/messages` against `AgentMemory`. (Currently 501.)
- **#53** frontend: individual-agent chat with pinned persona + identity_seed + initial reaction at top.
- **#54** api: persona-group chat with per-agent fan-out + one-line LLM synthesis. ("Ask the whole `DashPass Power × 15` group why they pushed back.")
- **#55** frontend: persona-group chat page with side-by-side per-agent replies + synthesis.
- **#56** per-turn calibration thumbs (👍/👎 on each reply) — feeds Phase 9 Layer-3.

Open question to brainstorm before code: **synthesis quality bar.** A bad one-line synthesis ("the group had mixed feelings") is worse than no synthesis. Worth a `/plan-ceo-review` before #54 lands to decide on prompt strategy + a quality eval.

**Carryover TODOS from Phase 2.5** (not blocking, capture for later):
- LLM prose synthesis on `identity_seed` (richer agent personality, follow-up to #5)
- v1.1 personas pack rollout for true cross-persona variance (currently `_DEFAULT_BEHAVIORAL_SEEDS` shared across personas)
- BCa bootstrap on aggregate score (Layer-3 calibration, follow-up to #6)
- Block-bootstrap by persona (Layer-3, follow-up to #6)
- v1.0-pack `_DEFAULT_BEHAVIORAL_SEEDS` fallback alerting (separate from #8, not currently ticketed)
- Founder rotates the PAT that was pasted in chat during MCP setup (security hygiene)

Tickets live in the [GitHub Project](https://github.com/users/ram-de/projects/) under Phase 4.

---

## Lessons we keep paying attention to

From the Magic Moment retro:
1. **Lock decisions first, code second.** `/plan-eng-review` before any phase >1 day of work. Eliminates mid-implementation second-guessing.
2. **Cross-model review at PR boundaries.** `/codex` review caught 5 P2/P3 issues in the scoring formula in 19 minutes, before Wave 5 doubled down on a flawed foundation.
3. **Parallel sub-agents work when the contract is locked.** Wave 5's 2,468 lines of frontend shipped in ~1h05m because the API contract was decided in Wave 0.
4. **`/qa` before the demo, not after.** Curl-based smoke tests miss browser-origin bugs (CORS).
5. **Name placeholders honestly in code.** A function called `_sample_personas` that doesn't sample is a lie. Future-you blames past-you.
6. **Hand-authored fixtures need the schema next to them.** Writing `streamly_sample` reverse-figma JSON, we guessed the transition shape wrong twice — `from`/`to`/`roles` instead of `from_screen`/`to_screen`/`role_gated`. Pydantic caught it on load, but the round-trip cost ten minutes. If we keep adding fixtures, fold a one-page schema crib into `docs/`.

From Phase 2.5:

7. **The browser test catches what `tsc --noEmit` + `next build` can't.** Phase 2.5 frontend compiled clean, codex passed three rounds, but the first live click revealed that `/agents/{id}` is 501-stubbed (Phase 4 work) so the persona-grouped table was just hitting its fallback path. CI gates verify shape; only the click verifies the wired-up flow. Bake "open the browser and click the thing" into the PR boundary, not after merge.
8. **Recommend the lightweight summary endpoint over N+1 fan-out, *before* you ship N+1.** Codex round 1 explicitly flagged the `Promise.all(getAgent)` pattern as "the right fix if this ever bottlenecks is a `/simulations/{id}/agents` summary endpoint." It bottlenecked on round zero (a 501) — the endpoint should have shipped with #51 from the start. Trust codex's "right fix" framing, don't defer "if this ever."
9. **Stale duplicate tickets accumulate fast under solo velocity.** #3 and #4 were re-scoped into #57 and #58 mid-phase and silently left open. Re-audit the GitHub Project at every phase boundary; closing stale tickets is part of "closing the phase."

---

## How to use this file

- **Updating this file is the last step of every sprint.** "What just shipped" advances, "What's next" gets refreshed from ROADMAP, "Lessons" gets at most 1–2 new entries.
- **Don't dump scratch notes here.** Personal scratch lives in your own notes app or Obsidian vault. CONTEXT.md is the shared, durable thread.
- **Co-founder + AI agents read this first** when picking up work. Make sure the next person walking in cold can orient in 2 minutes.
