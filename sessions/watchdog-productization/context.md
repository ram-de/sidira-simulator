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
  - [ ] #539 LLM-as-translator (hypothesis → structured mechanism spec) — front of pipeline
  - [ ] #540 grounded mediation sim (g-formula) as the predictor
  - [ ] #541 negative-control watchdog as the runtime trust gate
  - [ ] #542 runtime decision-flow orchestrator (the router; integrates #309/#511 lever pre-flight)
- **Phase 2 — surfaces**
  - [ ] #543 3-model heterogeneous-bias council (abstain-siren / caution-dial)
  - [ ] #544 re-ground talk-to-users conversation on computed results
  - [ ] #545 direction-only output contract + triage + guardrail breadth + FRONTEND lever/verdict
- **Phase 3 — discipline + loop-close**
  - [ ] #546 model-robustness regression harness (sealed battery per new model)
  - [ ] #222 calibrator wiring (grounded-blind vs measured, via the study-store adapter)

## In Progress
- [ ] **Iteration 1 = #539.** Explore agent (aa3fc5e5) mapping the engine runtime first so build
      briefs are precise. Then fresh worktree agent builds #539.

## Completed
- [x] Reconciled: Epic #538 + #539-546 already exist, cleanly phased; no new tickets needed.
      Integration points = router pre-flight #309/#511 (lever-in-data), calibrator #222.
- [x] Study-store + adapter shipped this session (#547-#549, PRs #548/#549/#550) — the
      predicted-vs-actual sink #222 will read from.

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
