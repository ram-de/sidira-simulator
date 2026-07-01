---
type: session
domain: watchdog-productization
status: active
started: 2026-07-01
owner: ram-de
---

# Session: watchdog-productization — ship the research architecture into the live engine

## Goal
Bring the DEPLOYED simulation engine to parity with the validated research architecture:
LLM-as-translator → grounded g-formula predictor → negative-control watchdog → LLM/council
fallback, routed by whether the hypothesis's LEVER is observable in the customer's data.
Replaces the disproven persona role-play. Backend runtime + frontend lever/verdict surfacing.

## The architecture being shipped (Epic #538, readout §5e + §6c)
```
Hypothesis ──[LLM TRANSLATOR]──► mechanism + lever
   │
   ├─ lever IN data ──► GROUNDED SIM (front door) ──► NEG-CONTROL WATCHDOG
   │                                                   CONFIRMS/CONTRADICTS/CANT-VALIDATE
   │                                                        │
   │                                          trustworthy──►ship sign | cant-validate──►abstain
   └─ lever NOT in data ─────────────────────────────────► LLM sim (fallback, flagged)
```
Precedence: trustworthy-empirical > LLM > untrustworthy-empirical (→ abstain).
Direction-only output; magnitude backstage. Council = abstain-siren ONLY (never predictor).

## Discipline (HARD RULES for every iteration)
- **Ship additive / OFF-BY-DEFAULT / abstaining** — the watchdog guard is a LEAD, not promoted
  (failed a hard real benchmark). Wire the architecture; flip on per-build once data promotes it.
- Worktree rule: each build in a FRESH general-purpose agent in an isolated worktree.
- `gitnexus_impact` before editing any engine symbol; `gitnexus_detect_changes` before commit.
- ruff + pytest green → `/codex review` → PR (as ram-de) → merge → **manual backend redeploy if
  backend/ touched** (deploy/REDEPLOY.md; api.sidira.ai does NOT auto-deploy).
- Direction-only in the customer-facing verdict; abstain-branch surfaces labeled
  "unverified — hypothesis, not verdict".

## Phased plan (loop iterations, in dependency order)
- **Phase 1 — core predictive path**
  - [x] #539 LLM-as-translator (hypothesis → structured mechanism spec) — MERGED PR #551
  - [x] #540 grounded mediation sim (g-formula) as the predictor — MERGED PR #552
  - [x] #541 negative-control watchdog as the runtime trust gate — MERGED PR #553
  - [x] #542 runtime decision-flow orchestrator (the router) — MERGED PR #554
- **Phase 2 — surfaces**
  - [x] #543 3-model heterogeneous-bias council (abstain-siren / caution-dial) — MERGED PR #555
  - [ ] #544 re-ground talk-to-users conversation on computed results
  - [ ] #545 direction-only output contract + triage + guardrail breadth + FRONTEND lever/verdict
- **Phase 3 — discipline + loop-close**
  - [ ] #546 model-robustness regression harness (sealed battery per new model)
  - [ ] #222 calibrator wiring (grounded-blind vs measured, via the study-store adapter)

## In Progress — PHASE 1 DONE (#539–#542). Phase 2: #543 DONE, now #544.
- [ ] **Iteration 6 = #544** re-ground the talk-to-users conversation on the COMPUTED results.
      The founder's simulate-novel-Qs + talk-to-users USP surface, but grounded in the decision-flow
      output (DecisionResult) instead of free persona role-play: the conversation cites the grounded
      verdict / watchdog stamp / council caution, labels unverified branches honestly, and abstains
      where the router abstains. Find the existing conversation/chat surface; ship additive +
      off-by-default (same flag family); no redeploy (batches to #545).

## Completed
- [x] Reconciled: Epic #538 + #539-546 already exist, cleanly phased; no new tickets needed.
      Integration points = router pre-flight #309/#511 (lever-in-data), calibrator #222.
- [x] Study-store + adapter shipped this session (#547-#549, PRs #548/#549/#550) — the
      predicted-vs-actual sink #222 will read from.
- [x] **#539 LLM-as-translator — MERGED (PR #551).** `schemas/mechanism.py` (MechanismSpec,
      mappable DERIVED via referential-integrity validator) + `services/mechanism_translator.py`
      (mirrors input_lint LLM-judge; never raises). codex P2 caught + fixed (client resolution
      moved inside the guard) + regression test. 21 tests. Ships INERT (no runtime import).
      Independently verified: 4 pre-existing suite failures are unrelated (route-resolution/
      deploy-config/identity-seed subprocess), not caused by the change.
- [x] **#540 grounded predictor — MERGED (PR #552).** `schemas/estimability.py` (READ models,
      extra=ignore, forward-compatible with the R2 artifact) + `services/grounded_predictor.py`
      (`grounded_predict` matches MechanismSpec (T,Y) → precomputed candidate → direction-only
      `sign_adjusted` + `supportable`; "not covered" → LLM fallback; never raises). ML-free,
      INERT. **I found + fixed a codex-missed integration bug during review:** the manifest READ
      key mirrored the feature-pack loader, but persona_builder WRITES it beside the PERSONA pack
      (`customers/<id>/personas/<version>/estimability_manifest.json` via `get_store`) — keys
      didn't match, runtime would never find it. Fixed `estimability_manifest_key` +
      `load_estimability_manifest` to the persona-pack path (dropped setup_id). Verified producer
      emits setup_id (example artifact) so the required field is correct. 19 tests, codex clean.
      No redeploy (INERT; single redeploy batched to #542).
- [x] **#541 negative-control watchdog — MERGED (PR #553).** Extended `CandidateEffect` with 7
      OPTIONAL NC-guard fields (mirror GuardedEstimate; AliasChoices so a producer that flattens
      the raw dataclass — floor/trips/confidence/reason — parses too; `populate_by_name=True`).
      New `services/negative_control_watchdog.py`: `watchdog_classify(prediction, *, llm_direction)`
      → CONFIRMS / CONTRADICTS / CANT_VALIDATE. `guard_trips is None` (NC evidence absent) →
      CANT_VALIDATE (honest default). codex caught 2 P2s (guard-clean-but-sign-None → abstain;
      alias robustness) — both fixed + tested. 11 tests, 29 in scope pass. ML-free, INERT.
      Independently verified (ruff/pytest/logic) before merge. Producer (sidira-personas
      manifest_builder) does NOT emit the NC fields yet → follow-up producer ticket needed.
- [x] **#542 §5e decision-flow orchestrator — MERGED (PR #554). PHASE 1 DONE.** New
      `services/decision_flow.py`: `decide()` (never raises) composes translate→grounded→watchdog→
      council-calibrated LLM fallback; `DecisionResult` audit trail; `Council` Protocol + NullCouncil
      default; `decision_flow_enabled()` (env `SIDIRA_DECISION_FLOW_ENABLED`, OFF default). Routing
      matches §5e exactly (trustworthy→grounded/none; CONTRADICTS→"data overrides intuition";
      abstain+disagree→hard/no-arrow; abstain+agree→moderate/unverified; exception→safe hard-caution).
      Seam = `SimulationOrchestrator._maybe_log_decision_flow`, a LOG-ONLY shadow hook placed AFTER
      `_run_with_id` sets terminal complete status (line 487) so it can't delay/false-fail the run;
      guarded (never raises into the run's except); flag-off = cheap env read + return, run path
      byte-identical. codex caught 3 P2s (blocking LLM on event loop→asyncio.to_thread; hook on
      critical path→moved post-run+30s timeout; manifest reload sentinel) all fixed. Setup-mismatch
      guard → abstain. 30 tests, 100 in-chain pass. Independently verified the seam + OFF path +
      routing before merge. **NO redeploy** (off-by-default, no live consumer). Real-customer
      end-to-end = founder-gated.
- [x] **#543 3-model heterogeneous-bias council — MERGED (PR #555).** New `services/council.py`:
      `HeterogeneousCouncil` implements the #542 `Council` Protocol; `DEFAULT_PANEL`
      (llama-3.1-8b-instant=optimist · claude-opus-4-7=pessimist · gpt-5.5=balanced); `BIAS_PROFILE`
      + `assert_bias_diversity` (≥2 distinct known profiles — degenerate all-same panel raises).
      Fans out concurrently (ThreadPoolExecutor, per-model timeout), drops abstains/errors/unavailable,
      aggregates abstain-siren: <2 usable directional OR split → agreement=False/hard; unanimous →
      agreement=True + direction/moderate. NEVER raises. Wired into the #542 hook via
      `build_default_council()` (guarded → NullCouncil on failure). codex P2: added additive opt-in
      `request_timeout` to llm.py clients + get_chat_client (default None = every existing caller
      byte-identical — verified). 16 council tests, 143 in-chain pass. Off-by-default; NO redeploy.
      Real-model campaign reproduction = founder-gated/offline (unit tests reproduce aggregation).

## Key Files
- Engine runtime: backend/sidira_simulator/services/ (SimulationOrchestrator) — mapping in progress
- Estimability cores: sidira-personas `sidira_personas/estimability/` (causal_estimator,
  negative_control_guard, manifest_builder) — ported PRs #20/#21/#510
- Schemas: backend/sidira_simulator/schemas/{simulation,feature_pack,benchmark}.py
- Frontend: SimulationNewV2 / SimulationDetailV2 (live v2 routes)
- Readout: founder-readout/simulation-engine-where-we-landed.md (§5e flow, §6c plumbing)

## Key Context
- Deployed engine today = disproven persona role-play. Target = this watchdog architecture.
- Standing user grant this session: build the whole epic in a LOOP, permission to MERGE + DEPLOY.
- Backend deploys manual (api.sidira.ai); frontend auto-rebuilds on push to main (Amplify).

## For my cofounder
Starting the productization epic (#538) autonomously — grounded-sim + watchdog + LLM-router into
the live engine, one sub-ticket per PR, additive/off-by-default. Founder granted merge+deploy.
