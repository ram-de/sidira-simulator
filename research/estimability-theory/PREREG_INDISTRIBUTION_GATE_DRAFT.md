# PREREG (DRAFT — not sealed; finalize + sha-seal when a design partner's data lands)

## In-distribution engine validation, gated by persona information-sufficiency

**Status:** DRAFT. No data yet. This is the experiment that runs the day a design partner provides a
sealed A/B history. Finalize N, thresholds, and the gate spec WITH the partner's real schema, then
sha256-seal the (gate-partition + predictions) BEFORE unsealing outcomes. Thresholds below are
placeholders to be frozen at seal time, not tuned after.

**One-line thesis:** the engine's directional accuracy is gated by whether the persona representation
encodes the variable the hypothesis turns on. We pre-commit a persona **information-sufficiency**
partition (PASS/FAIL) BLIND to outcomes, then test that the engine beats chance ONLY on PASS. This
validates the gate AND gives the LLM/engine half its first honest in-domain test.

---

## Data (from the design partner)
- N historical A/B tests (**target N ≥ 25**; honestly underpowered — pilot, LEAD-generating, n=1
  partner). Each carries:
  - the change + a stated **mechanism** (the causal story, e.g. "reduces choice overload"),
  - the **persona pack / feature store as of test time** (no post-test leakage),
  - per-user pre-test behavioral logs,
  - the **sealed real directional outcome** (winner / no-diff), unsealed only after commit.
- Outcomes are sealed; only the sha256 of {gate-partition + per-case predictions} is committed first.

---

## GATE 1 — persona information-sufficiency (computed BLIND to the A/B outcome)
For each hypothesis, map mechanism → persona feature(s) and score three layers (cheap → rigorous):

- **L0 presence:** the mechanism-relevant feature(s) exist in the persona pack schema.
- **L1 variance:** they are non-degenerate across the population (coefficient of variation above a
  frozen floor; a constant feature carries zero discriminating information).
- **L2 discriminability (the information floor):** a flexible model (e.g. gradient-boosted) predicting
  a **pre-test behavioral proxy** for the mechanism (NOT the A/B outcome — e.g. historical
  browse-abandon rate for "overload") from the mechanism feature(s) beats its own permutation null by
  a frozen margin (Fragile-Families-style: if even a flexible model can't extract the signal, the LLM
  won't). Using a pre-test proxy keeps this BLIND to the sealed outcome.

**PASS** = L0 ∧ L1 ∧ L2. The PASS/FAIL label per case is committed before any outcome is seen.
(Reported but NOT part of the gate: **L3 simulation-sensitivity** — does the engine's simulated
behavior actually move when the mechanism feature is perturbed? A diagnostic of whether the engine
*exploits* present information, separate from whether information is present.)

---

## ENGINE prediction (blind, committed with the partition)
Per case the router emits a directional prediction + confidence/abstain: empirical/causal estimate
where feature-expressible (with the negative-control guard), else **data-grounded** persona simulation
(personas resampled from the real feature store, not invented). Predictions sealed before unsealing.

---

## Pre-registered predictions
- **P1 — the gate validates (PRIMARY):** directional accuracy on the **PASS** set significantly
  exceeds the base-rate baseline AND exceeds the FAIL-set accuracy. *(This is the differentiated,
  sellable claim.)*
- **P2 — the gate is necessary:** directional accuracy on the **FAIL** set is at the base-rate
  baseline (the engine cannot manufacture signal that the representation doesn't carry). If FAIL also
  beats baseline, information-sufficiency was NOT the binding constraint (or there is leakage) —
  reported straight.
- **P3 — coverage is non-trivial:** the PASS set is a meaningful fraction of N (the product is not
  "abstain on everything"); report the full accuracy–coverage curve, not a single point.
- **P4 — beats the obvious:** on the PASS set the engine beats BOTH (a) the **majority-class / base-rate
  predictor** (NOT 0.5 — A/B winners are imbalanced; this is the floor the analogy method died on) and
  (b) the **naive-intuition prior** (always predict the "obvious" direction), so a win is not just
  re-predicting the obvious.
- **P5 — the cases that matter:** accuracy reported SPLIT by intuitive vs **counter-intuitive** (where
  the naive prior is wrong). Beating chance only on intuitive cases is near-worthless; the
  counter-intuitive PASS slice is the real prize and is reported separately even if tiny.

## Scoring & honesty rails (freeze at seal time)
- Base rate / "chance" = the majority-class directional rate in this partner's history, not 0.5.
- One scored pass. Report effect sizes + CIs; with N≈25 split four ways the CIs will be wide —
  **this is a LEAD-generating pilot, n=1 partner; PROMOTION requires ≥3 partners** with the same
  pre-registered protocol. State this up front.
- Case-selection confound: a partner tests what it's unsure about; note the sampling is non-random and
  do not generalize the base rate beyond this partner.
- Leakage audit: confirm the persona pack and L2 proxy are strictly pre-test; any feature derived from
  the outcome voids the case.
- Self-blinding: sha256 of {gate-partition + predictions + frozen thresholds} committed before the
  partner unseals outcomes. Verdict legend: PROMOTED / LEAD / NULL / MECH-ONLY as in the campaign
  runstore. Most likely honest outcome of a single pilot = **LEAD or NULL**, recorded either way.

## What each outcome means
- **P1 ∧ P2 hold →** information-sufficiency is the gate; the engine half has real in-domain signal on
  the cases it should. LEAD (→ replicate on more partners to PROMOTE).
- **P1 holds, P2 fails →** engine beats chance but the gate doesn't explain where; the partition isn't
  the right cut — investigate before claiming the gate.
- **P1 fails →** even in-distribution with sufficient information the engine is at chance; the data
  wall holds inside one domain too, and the honest product is empirical-only + abstain.
