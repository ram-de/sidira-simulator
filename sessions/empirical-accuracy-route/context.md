---
type: session
domain: empirical-accuracy-route
status: active
started: 2026-06-27
owner: ram-de
---

# Session: empirical-accuracy-route — a non-LLM angle on engine accuracy

## Goal
Test whether a completely different route — empirical/causal ML on real behavioral
data, and a council-of-priors over the LLM — can crack directional accuracy where the
persona-simulation engine has come back null. Find the one angle that actually works.

## In Progress
- [ ] Productizing the ROUTER. Portable cores DONE in research/: `causal_estimator.py`
      (model) + `manifest_builder.py` (build-time precompute join+grid). Architecture
      decided: precompute an `estimability_manifest.json` at PACK BUILD (lives in
      **sidira-persona-worker**, per founder), shipped beside persona_pack.json in R2;
      runtime = match→retrieve→route in `SimulationOrchestrator.prepare`. NEXT = land the
      two cores into sidira-persona-worker + R2 write (PR there), then orchestrator MAP +
      router pre-flight (#309), then #222 calibrator wiring.

## Completed
- [x] **Phase A — empirical/causal route (synthetic): MECHANISM WORKS.** `uplift_spike.py`.
      On a feature-expressible change with the driver in the data, causal ML (IPW +
      T-learner) recovers the true SIGN where the "more-is-better" prior and naive
      correlation both get it wrong (S1). Honest bound: unobserved confounder defeats it
      (S2 → LLM territory).
- [x] **Phase C — council-of-priors: REJECTED.** `council_benchmark.py`. 4 explicit-prior
      members + regime router, pre-registered consolidation, blinded, 3 ablations. Live
      (Groq llama-3.3-70b). On the same 14 cases the comparative baseline scored 0.50:
      naive 0.64 > council-routed 0.57 > council-unrouted 0.50 — the council made it
      WORSE (extra priors flip correct answers; diversity ≠ accuracy, measured).
- [x] **"Naive beats engine" lead — investigated + RETRACTED.** The 0.50 baseline is the
      *comparative-forecaster* (same method as my naive call) on sonnet, NOT the
      persona-sim engine. Re-ran it on llama → 0.500 again. So 0.64-vs-0.50 = model
      confound + n=14 noise. ROBUST fact (known, #342): per-arm persona-roleplay 0.286
      (below chance) << comparative narrative 0.50 (at chance). No LLM method beats chance.
- [x] **Phase B — empirical route on REAL data (Cookie Cats 90,189 players).**
      `realdata_uplift.py`, design sealed in `PREREG_REALDATA.json` (sha256 027aa4a8).
      True RCT: gate_30 wins (retention_7 ATE −0.82pp). Injected selection bias on
      engagement (treatment arm 86.7 vs control 16.8 avg rounds) → naive diff-in-means
      **+22.01pp (sign WRONG)**; T-learner standardization **−0.81pp** and IPW −0.61pp
      (both RIGHT; recovers true −0.82pp almost exactly). Exactly as pre-registered.
- [x] **Phase B — Hillstrom (clean pre-treatment, 42,693 customers).**
      `realdata_hillstrom.py`, sealed `PREREG_HILLSTROM.json` (sha256 ffcb13d9). True
      email lift +4.52pp on visit (opposite polarity to Cookie Cats). Causal adjustment
      recovers it: T-learner +4.97 / IPW +4.88. PRIMARY prediction confirmed. TWO sub-
      predictions REFUTED + reported honestly (not re-tuned): naive didn't flip (only
      attenuated +2.12 — true effect too large); the unobserved-confounder ablation still
      recovered (+3.60 — other pre-treatment covariates proxy spend). Cookie Cats keeps the
      dramatic flip + clean S2; Hillstrom adds clean-covariate recovery.
- [x] PR **#508** opened (research/empirical-uplift-spike/, no prod code touched). MERGED.
- [x] **Engine-strength campaign launched** (`research/engine-strength-campaign/`): append-only
      `runstore.py` → `runs.jsonl` + auto `LEDGER.md`; pre-register+seal every run; codex made
      robust to flakiness via **self-blinding generation** (secret os.urandom seed, hidden
      regime→file shuffle, sealed key OUTSIDE worktree, only sha256 committed) — no live codex
      dependency. Verdict legend PROMOTED/LEAD/NULL/MECH-ONLY.
- [x] **iter0 — empirical core blind on 10-regime synthetic Streamly (MECH-ONLY).** causal 7/8
      vs naive 6/8 directional (the whole advantage = the sign-flip case). **KEY FINDING:**
      overlap-based confidence flagged 0 of its 3 errors — overlap is necessary, NOT sufficient.
- [x] **iter1 — negative-control guard (NULL by strict rule, mechanism confirmed).** A
      negative-control outcome (shares confounding, true effect 0) DOES reveal unobserved
      confounding overlap can't see (P1 2/2). But the pre-registered 0.02 band false-alarmed on
      benign observed-confounding residual incl the sign-flip win (P2 fail). Did NOT re-tune.
- [x] **iter2 — negative-control guard, floor 0.05, HELD-OUT (LEAD — first of campaign).**
      Floor chosen on iter1's residual gap (observed ≤0.04 vs hidden ≥0.10), validated on a
      FRESH independently-seeded v3 set. P1 2/2 + P2 7/7: catches both unobserved-confounder
      errors with ZERO false alarms incl sign-flip. Residual error = true-null false-positive
      (pre-registered limit a negative control structurally can't catch). Folded into
      SCOPE_ROUTER.md as the empirical-trust confidence gate. Synthetic ⇒ ceiling LEAD; real
      microdata replication still required before PROMOTED.

## Next Steps
1. **sidira-persona-worker PR** — port `manifest_builder.py` + `causal_estimator.py` in;
   feed real `ColumnProfile`s + crawler `Capability` list + a Snowflake `load_frame`; write
   `estimability_manifest.json` to R2 beside `persona_pack.json`; version it with the pack.
   Replace rule-based linkage with the LLM MAP step (same output shape).
2. **Orchestrator MAP + router** (backend) — in `SimulationOrchestrator.prepare`: load the
   manifest, match `hypothesis.prose` → catalog entry, route match→retrieve (empirical) vs
   unmatched→`SimulationRunner.run` (LLM, flagged).
3. **Pre-flight surface** (backend+frontend) — extend answerability #309 with the
   "estimable from your data?" branch + route/confidence card.
4. **#222 calibrator wiring** — hang the empirical estimate on the `MetricCalibrator` seam
   (replace `IdentityCalibrator` in `services/conversion_calibrator.py`).
5. (optional) Upworthy / no-persona LLM generalization beyond the 14 cases.
6. (optional) Land PR #508 to main once reviewed.

## Key Files
- `research/empirical-uplift-spike/README.md` — full writeup (the canonical record).
- `research/empirical-uplift-spike/uplift_spike.py` — Phase A synthetic (S1 win / S2 bound).
- `research/empirical-uplift-spike/council_benchmark.py` (+ `council_result*.json`) — Phase C council, rejected.
- `research/empirical-uplift-spike/realdata_uplift.py` (+ `realdata_cookiecats_result.json`) — Phase B real data.
- `research/empirical-uplift-spike/PREREG_REALDATA.json` (+ `.sha256`) — sealed pre-registration.
- `research/empirical-uplift-spike/comparative_llama_result.json` — the model-confound control.

## Key Context
- **The survivor = empirical/causal route.** It's the only thing that beat chance, because
  it learns from DATA, not narratives. Everything LLM-prompt-shaped (persona, no-persona,
  council) sits at/below chance on directional prediction.
- Persona-simulation (per-arm roleplay) is actively WORSE than a one-line comparison
  (0.286 vs 0.50) — the machinery hurts. Already known internally (#342); re-confirmed.
- Empirical route's limit (registered): needs the effect driver to be an OBSERVED,
  feature-expressible variable; unobserved confounder (spike S2) defeats it.
- LLM keys live in main-checkout `backend/.env` (gitignored, NOT in worktrees) — load
  GROQ_API_KEY from there to run LLM spikes. Cookie Cats data: ryanschaub mirror.
- Ties to [[project-empirical-uplift-and-council-spike]] (memory), the directional
  portfolio, and the #222 calibrator (the empty slot this route could eventually fill).

## For my cofounder
The big takeaway: no LLM-prompting trick (persona/council) beats a coin flip at predicting
which A/B arm wins — but the **empirical/causal route does**, and I now have it working on
real Cookie Cats data (recovers the true counter-intuitive winner under injected
confounding where naive averaging is off by +22pp). Next is Hillstrom for the clean
pre-treatment version. All in PR #508; nothing touches production. The council idea is a
documented dead end — don't re-spin it.
