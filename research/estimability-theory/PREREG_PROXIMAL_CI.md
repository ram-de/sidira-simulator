# PREREG — Proximal causal inference: correct-and-answer vs detect-and-abstain

Sealed before run. The adversary's sharpest non-rediscovery point: we implemented the **2010**
negative-control *falsification* test (detect hidden confounding → abstain) but NOT the **2018**
proximal-causal-inference frontier (Miao-Geng-Tchetgen Tchetgen; COCA, Tchetgen Tchetgen 2014),
which *corrects* the bias and can recover the SIGN on cases the single-NC guard currently throws
away as "abstain." This experiment tests whether moving from detection to correction **expands the
estimable slice** — and, just as importantly, where it **backfires** (introduces confident-wrong
answers, region C). A method that only trades abstention for *wrong* answers is worse than the guard.

## Estimators
- **naive**: diff-in-means on Y.
- **adjusted**: T-learner / IPW on observed covariates X (the current `estimate()`).
- **single-NC guard** (current): abstain if |adjusted effect of T on the NC outcome W| > floor(0.05).
- **COCA (new)**: under additive equi-confounding (the confounding bias on Y equals that on the
  negative-control outcome W), the bias-corrected effect is
  `ate_coca = adjusted_ate(Y) − adjusted_ate(W)`  (subtract the NC residual the guard already computes).
  Decide sign from `ate_coca`. This converts the guard's "trip" signal from an abstain trigger into
  a *correction term*.
- **double-NC / proximal bridge (stretch)**: if a negative-control EXPOSURE/action Z (affects W, not
  Y, shares U) is available in the synthetic DGP, fit the two-stage proximal bridge for a correction
  that does NOT require equi-confounding. Run only on synthetic where Z is constructed.

## Data
- **Synthetic** (generalize the existing generator): U = unobserved confounder; X observes a fraction
  rho_obs of U; propensity = sigmoid(gamma·U); Y has true signed effect tau (incl. tau=0); W is an NCO
  with TRUE T-effect 0 and confounder coupling kappa. Two confounding modes: **EQUI** (W and Y share
  the same U-loading → COCA's assumption holds) and **VIOLATED** (W loads on U differently → assumption
  broken). Grid over {rho_obs, gamma, tau, kappa, mode}. Known ground-truth sign for every cell.
- **Real anchors** (clean RCTs, gamma≈0): Hillstrom (true +4.52pp visit), Cookie Cats (true ~−0.82pp
  retention). Here the NC residual ≈ 0, so COCA must be ≈ a no-op — a safety check, not a win condition.

## Metrics
- **Recovery on the abstain pile**: among cells where the single-NC guard ABSTAINS (residual>floor),
  the fraction where the *sign* is correct, for COCA vs adjusted vs naive.
- **Silent-failure rate (region C)**: P(confident AND directional AND wrong) for COCA vs guard, overall
  and split by EQUI vs VIOLATED.
- **Over-correction harm**: cases the adjusted estimator got RIGHT that COCA flips WRONG.
- **Real-anchor safety**: does COCA change the (correct) sign on Hillstrom / Cookie Cats? (must not.)

## Pre-registered predictions (genuine, leaned — sealed)
1. **EQUI band — the win:** COCA recovers the correct sign on **≥ 50%** of guard-abstained confounded
   cells that the adjusted estimator got *wrong*. (Bet: PASS — equi-confounding is exactly COCA's
   home turf.)
2. **VIOLATED band — no free lunch:** COCA's silent-failure rate is **strictly higher** than the
   guard's in the VIOLATED mode (it "corrects" in the wrong direction). Bet: PASS — i.e. COCA is NOT
   universally safe; the equi-confounding assumption is load-bearing and unverifiable from data alone
   (the same shape as the NC-nomination limit → an LLM/domain must assert it).
3. **Real-anchor safety:** COCA does NOT flip the correct sign on Hillstrom or Cookie Cats, and does
   not invent a direction on true-null cells. Bet: PASS.

## Verdict mapping
- **LEAD** if (1) holds AND (3) holds AND (2)'s harm is *bounded and predictable* (confined to the
  VIOLATED mode) — i.e. COCA expands the slice *conditionally*, and the deployable artifact is
  "COCA-correct **inside** a guard that still abstains when equi-confounding is implausible."
- **NULL** if COCA does not beat the adjusted estimator on the abstain pile (no recovery).
- **MECH-ONLY** if it only works synthetic and the real anchors are uninformative (expected — they're
  clean RCTs, safety checks not win conditions).

## Honesty rails
- COCA's equi-confounding assumption is unverifiable from observational data — a PASS on (1) is NOT a
  free expansion; (2) is the price, and must be reported as prominently as (1).
- Synthetic recovery ≠ real recovery (the adversary's circularity critique stands). This experiment
  characterizes the *mechanism and its failure mode*; promotion still needs the real corpus.
- Pre-registered; one scored run; report raw numbers including any prediction refuted.
