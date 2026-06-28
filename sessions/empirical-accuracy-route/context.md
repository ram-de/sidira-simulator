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
- [ ] Hillstrom real-data confounding test (clean PRE-treatment covariates) — the
      methodologically tight version of the Cookie Cats win.

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
- [x] PR **#508** opened (research/empirical-uplift-spike/, no prod code touched).

## Next Steps
1. Hillstrom: real-data confounding test with clean pre-treatment covariates (recency,
   history, channel measured before the email). The tight external-validity version.
2. Hillstrom/Upworthy LLM: confirm "no-persona ≥ persona-roleplay" generalizes beyond
   the 14 cases (less contamination than famous Cookie Cats).
3. Product implication to socialize: a ROUTER — feature-expressible + data-supported →
   empirical engine (provably accurate, no LLM); else → LLM engine (broad, flagged).

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
