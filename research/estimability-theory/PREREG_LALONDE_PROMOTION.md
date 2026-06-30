# PREREG — promotion test on naturally-confounded REAL data (LaLonde NSW)

Sealed before run. This is the LEAD→PROMOTED gate and the answer to the adversary's three hardest
critiques: (c) "the synthetic phase-diagram is circular — you get out the structure you put in",
(d) "n=1 real", (e) "nothing transfers synthetic→real". The negative-control guard and COCA have been
validated on SYNTHETIC confounding (where we encoded it) and SAFETY-checked on clean RCTs (no
confounding to correct). Neither has faced REAL, naturally-occurring confounding with a known
experimental truth. The LaLonde/NSW benchmark is the canonical such test.

## The benchmark (LaLonde 1986; Dehejia-Wahba 1999)
- **Experimental NSW**: a randomized job-training RCT. Known experimental ATE on 1978 earnings is
  POSITIVE (~+$1,600–1,800 on the Dehejia-Wahba subset). The clean ground truth.
- **Observational NSW**: replace the experimental controls with a non-experimental comparison group
  (PSID or CPS). Now treatment is NOT randomized → severe selection confounding. The NAIVE estimate
  is large and NEGATIVE (wrong sign, ~−$8k to −$15k) — the textbook failure.
- Covariates: age, education, black, hispanic, married, nodegree, re74 (1974 earnings), re75 (1975
  earnings). Treatment = training; outcome = re78 (1978 earnings).
- **Negative-control outcome**: `re74` (1974 earnings) is PRE-treatment (training was 1976–77), so
  treatment CANNOT cause it, yet it is confounded by the same selection — the canonical placebo/NC
  outcome (exactly how Dehejia-Wahba diagnose balance). The guard estimates the (adjusted) effect of
  T on re74; a large effect ⇒ unblocked confounding ⇒ abstain.

## Estimators (reuse `causal_estimator.py`)
naive · adjusted (T-learner on the 6 baseline covariates + re75, NOT re74 which is the NC) ·
single-NC guard (NC = re74, floor on the standardized scale) · COCA (= adjusted_ate(re78) −
adjusted_ate(re74)). Run on: (A) experimental NSW, (B) NSW-treated vs PSID controls, (C) NSW-treated
vs CPS controls. Earnings are continuous → use the continuous null-band; standardize so the 0.05
floor is comparable (report both raw-$ and standardized).

## Pre-registered predictions (genuine, leaned — sealed)
1. **Specificity on the clean RCT (A):** on experimental NSW the guard does NOT trip (re74 placebo
   ≈ 0 because randomization balances it) and adjusted/COCA give the correct POSITIVE sign. Bet: PASS.
2. **Detection on confounded data (B,C):** on the observational PSID/CPS versions the naive estimate
   has the WRONG (negative) sign, the re74 placebo effect is LARGE, the guard TRIPS → abstains —
   correctly refusing to ship the confounded-wrong answer. Bet: PASS. **This is the load-bearing
   claim**: the guard's whole value proposition is detecting REAL hidden confounding it never saw in
   training, on data where the confounding is genuinely unobserved-by-construction.
3. **COCA recovery (the open question, leaned):** does COCA recover the correct POSITIVE experimental
   sign from the observational data? **Genuine lean: NO / not reliably** — real selection into job
   training is NOT additive-equi-confounding (the bias on re78 differs from the bias on re74), so
   COCA will over/under-correct and will NOT reliably flip to the experimental positive sign. I.e. on
   real naturally-confounded data the HONEST system ABSTAINS rather than magically recovers — the
   real-world value is calibrated abstention, not free correction. If COCA DOES recover the sign on
   PSID and/or CPS, that is a STRONGER result than I'm betting and I'll report it as such.

## Verdict mapping
- **PROMOTED (guard)** if predictions 1 AND 2 both hold: the guard transfers synth→real, detecting
  genuine natural confounding (specificity on the RCT, sensitivity on the observational versions) —
  this is the first REAL naturally-confounded test it passes, n now >1.
- **COCA stays LEAD** unless prediction 3 flips positive on real data (then COCA→stronger LEAD).
- **NULL/return-to-bench** if the guard FAILS to trip on the confounded PSID/CPS data (false-confident
  on real hidden confounding) — that would be a serious, honestly-reported failure of the core claim.

## Honesty rails
- re74 as the NC is standard but imperfect (it proxies the confounder strongly — which is the
  favorable case; report that the guard's power here depends on re74's coupling, the known limit).
- A single benchmark family (NSW) is n≈3 conditions, not "a dozen" — promotion here is necessary,
  not sufficient; IHDP/ACIC + the ~6 corpus RCTs are the next breadth. Report the honest scope.
- One scored run; report raw $ effects, placebo effects, trip decisions, and COCA signs for A/B/C.
