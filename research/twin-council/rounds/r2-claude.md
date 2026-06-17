# Claude Council — Round 2

*Five seats reconvened: S1 causal inference · S2 LLM silicon-sampling · S3 ABM/computational social science · S4 survey methodology & calibration · S5 ML evaluation. Cross-critique toward a single ledger both councils sign.*

We read both Round 1 papers and the arbitration. The convergence on A1–A12 is real and we do not relitigate it. Below: marks on Codex's 25 claims, committed resolutions to D1–D5 with the binomial math, a merged ledger, and the (few) remaining disagreements.

---

## A. Marks on Codex's ledger

| # | Codex claim (abbrev.) | Mark | Reason (only where DISAGREE/REFINE) |
|---|---|---|---|
| C1 | No estimand (metric/pop/treatment/control/horizon) → not directionally correct | **AGREE** | — |
| C2 | Sign & rank more defensible than uncalibrated magnitude | **AGREE** | — |
| C3 | Live experiment is ground truth; sim is a calibrated prior | **AGREE** | — |
| C4 | Persona-only < persona-plus-row on held-out prediction | **REFINE** | Likely true but it is an *empirical* claim, not an axiom; commit it as a falsifiable ablation hypothesis (pre-registered ordering), not a design mandate. The variance-floor/raking spec (D3) is the mandate; persona+row is the leading hypothesis to test. |
| C5 | Soft membership > hard assignment when segments overlap | **AGREE** | — (we fold this into the unified D3 spec) |
| C6 | Metric-keyed delta elicitation > generic sentiment | **AGREE** | — |
| C7 | Distribution elicitation > single deterministic reaction | **REFINE** | Agree it is better-calibrated *in expectation*, but verbalized 100-point allocations are themselves a biased instrument (anchoring on round numbers, modal collapse to 60/30/10). Commit it but require the calibration layer to own the final probability — the elicited distribution is a feature, not the reported confidence. |
| C8 | No-persona LLM panel is a mandatory baseline | **AGREE** | — |
| C9 | Paraphrase instability predicts lower OOS accuracy → cut confidence/abstain | **AGREE** | — |
| C10 | Raw LLM magnitudes too large → require shrinkage | **AGREE** | — |
| C11 | Text/copy/first-impression validate higher than networked/long-horizon | **AGREE** | — |
| C12 | Independent panels invalid for strong network estimands w/o interaction model | **AGREE** | — |
| C13 | High raw accuracy can be useless under high flat/negative base rate | **AGREE** | — (this is why we use balanced accuracy/MCC, not raw accuracy) |
| C14 | Bal-acc, MCC, Brier, ECE, rank corr, regret, tail-recall all required | **REFINE** | Agree all are *reported*; disagree they are co-equal *gates*. Per D2/D5 we make decision regret + tail-winner recall the decision-layer primaries and treat the rest as necessary diagnostic gates. "All required to assess" — yes. "All co-primary" — no. |
| C15 | Fail A/A null → must not be trusted | **AGREE** | — |
| C16 | Backtests must be hash-committed before unblinding | **AGREE** | — (stronger than our Round-1 wording; we adopt it) |
| C17 | < 50 experiments cannot support a quantitative customer-specific claim | **AGREE** | — (this is our floor; see D1) |
| C18 | 150–200 blind archive is the minimum *credible* range | **REFINE** | The binomial math (D1) says n≈100 already gives ~0.92 power to clear a 0.70/LB>0.55 single-product gate; 150–200 is the *comfortable* range and the right floor for the harder 3-class-MCC-beats-baseline gate. We reconcile: 100 credible (single-product sign gate), 150–200 required for the MCC-lift gate. Not a flat 150–200 for everything. |
| C19 | Tail-winner false negatives more dangerous than ordinary sign errors | **AGREE** | — (identical to our false-red argument) |
| C20 | Re-rank/redesign, don't auto-kill, unless tail recall validated | **AGREE** | — |
| C21 | Persona narratives valuable for explanation/interview even if lift is from rows | **AGREE** | — |
| C22 | Segment response priors from past experiments improve accuracy on repeat classes | **REFINE** | Agree directionally; flag that this needs enough per-class experiments to estimate the prior (the same small-n wall as D1, now per treatment-class). Commit as conditional on class-level sample sufficiency. |
| C23 | Stated preference must be calibrated to revealed behavior before use as evidence | **AGREE** | — |
| C24 | Sycophancy is material and must be tested explicitly | **AGREE** | — |
| C25 | Model/prompt versions rerun on golden set before claim transfers | **AGREE** | — |

No new decisive objection to A1–A12.

---

## B. Resolutions to D1–D5

### D1 — Minimum historical-experiment count (hard floor + credible target), with the binomial math

We resolve the ≥50 vs 150–200 gap by separating **floor** (below which: no quantitative claim, period) from **credible target** (power to actually pass the GO gate) and from the **harder MCC-lift gate** Codex wants. All numbers are on the sign-balanced, sign-non-null subset (the cases where `s(c)≠0`), since SMR is only defined there.

**The estimator is a binomial proportion (SMR).** Wilson 90% interval at observed SMR = 0.70:

| n | Wilson 90% CI | half-width | lower bound |
|---|---|---|---|
| 30 | [0.551, 0.816] | 0.133 | 0.551 |
| 50 | [0.585, 0.794] | 0.104 | 0.585 |
| 75 | [0.607, 0.779] | 0.086 | 0.607 |
| 100 | [0.620, 0.769] | 0.075 | 0.620 |
| 150 | [0.635, 0.758] | 0.061 | 0.635 |
| 200 | [0.644, 0.750] | 0.053 | 0.644 |

**Power to pass the GO gate** (gate = observed SMR high enough that Wilson 90% lower bound > 0.55), evaluated at a true SMR of 0.70:

| n | min observed SMR to clear gate | power at true SMR=0.70 |
|---|---|---|
| 50 | 0.680 (34/50) | **0.68** |
| 75 | 0.653 | 0.84 |
| 100 | 0.640 | **0.92** |
| 150 | 0.620 | 0.99 |
| 200 | 0.610 | 1.00 |

And the resolution-power question — can you even tell SMR 0.65 from 0.82? At n=50 the 90% CIs still overlap; they separate only at n≈100.

**Committed numbers:**
- **Hard floor = 50** sign-balanced, outcome-labeled experiments (both signs present, kills/nulls included). Below 50: report **"uncalibrated"**, no numeric confidence, qualitative/per-segment only. This matches Codex C17 exactly. Rationale: at n<50 the CI half-width exceeds ±0.10 and power to clear the gate is <0.68 — you cannot distinguish a good simulator from a mediocre one, so a quantitative claim is unearned.
- **Credible target for the single-product sign gate = 100.** At n=100, power to correctly pass a genuinely-0.70 simulator is 0.92 and the CI half-width drops to ±0.075. This is the smallest n we will call "credible."
- **Required floor for the MCC-beats-baseline gate = 150** (Codex's gate, D5 #3). The 3-class MCC-lift-over-baseline test with a paired-bootstrap CI lower bound > 0 needs more cases than a one-proportion test (it estimates a difference of two correlated statistics over a 3-class confusion matrix). 150 is the floor where that paired test has adequate power; 200 is comfortable. This is exactly Codex's 150–200, now scoped to the metric that needs it.

So: **50 floor / 100 credible (sign) / 150–200 required (MCC-lift)**. Both councils' numbers survive, each attached to the gate it actually powers. Where a single product cannot reach 100, **hierarchical partial pooling across products/treatment-classes** is mandatory to borrow strength, and the pooled effective-n (not the raw count) is what the gate reads.

### D2 — Is decision regret THE primary criterion or one of several?

**Single primary criterion: decision regret vs. the PM's status-quo triage policy, subject to a tail-winner-recall floor as a hard side-constraint.** Formally it is a constrained objective, not a basket vote:

> minimize Regret(π_sim, π_0)  **subject to** tail-winner recall ≥ 0.80.

Rationale: regret is the only metric denominated in the unit the product is sold on — realized metric gain per scarce experiment slot. Balanced accuracy, MCC, Brier, ECE, and rank correlation are **necessary diagnostic gates** (each can independently disqualify — e.g. fail A/A, or ECE > 0.10 means the confidence number is a lie) but none of them, passed alone, proves *value*. A simulator can have excellent MCC and still produce negative value if its errors land on the high-traffic decisions. Conversely the tail-recall constraint prevents "good average regret" from being bought by silently killing rare high-upside winners (the false-red / unobservable error, A11) — that is why it is a side-constraint, not a term traded off inside the regret average.

So the basket is: **primary = decision regret (lower CI < 0 at the PM's cost ratio); binding side-constraint = tail-winner recall ≥ 0.80; gating diagnostics = balanced SMR, 3-class MCC-lift, ECE, rank correlation, A/A null, leakage permutation.** This fully absorbs Codex's 7-metric basket — every Codex metric remains required — while naming the one number that decides ship/no-ship.

### D3 — One unified population-construction spec

Codex's soft persona membership and our raking-to-real-joints are **the same pipeline at two stages**; they were never in conflict. Unified spec:

1. **Source of truth is real user rows**, not archetypes. Sample anonymized behavioral rows where allowed; otherwise sample from a generative model fit to the real joint covariate distribution (preserve *covariance*, not just marginals).
2. **Personas are a soft compression layer, not identities.** Each sampled unit carries a posterior membership vector over segments (e.g. 0.45/0.35/0.20), never a hard archetype. Hard assignment is banned (Codex C5; our F2).
3. **Conditioning is persona-gestalt + individual-row deltas** (Codex 3.4): the segment pattern plus how this row departs from the centroid, plus empirical seed values.
4. **Raking / post-stratification to the real joint distribution** is applied as the *weighting* step over the sampled population, so the weighted panel matches real marginals *and* key interactions. Gate: all |standardized mean difference| < 0.1 after raking (our Test 3).
5. **Variance floor against mode collapse:** realized between-unit response variance ≥ 0.5 of target heterogeneity (our F2/Test 4). Soft membership and nonzero-temperature distribution elicitation are the *mechanisms* that produce the spread; the variance floor is the *acceptance test* that they worked.
6. **Posterior entropy / segment instability flow into confidence** (Codex 3.3): high-entropy or unstable-segment units widen the interval rather than asserting a crisp response.

One sentence: *sample real rows → soft-segment them → condition each unit on persona-gestalt + row-deltas → rake the weighted panel to the real joint distribution → accept only if covariate-balance and between-unit-variance gates pass.* Soft membership and raking are complementary, not alternatives.

### D4 — Precise semantics of the confidence score

The confidence score **reports the calibrated probability that the predicted sign class is correct, conditional on (a) the validated regime, (b) input quality/prompt stability, and (c) the calibration backtest's coverage of this change-type.** It is a property of the calibration set, not of persona eloquence. It unifies both councils: Codex's "distribution-elicited calibrated sign probability" is *how the number is produced*; our "property of the backtest's coverage" is *the condition under which the number is allowed to be emitted at all*.

Precise contract:
- **What it reports:** P(sign class = predicted | regime, inputs) — i.e. the simulator's historical hit-rate for change-types like this one, after the isotonic/Platt + shrinkage calibration layer maps the raw distribution-elicited signal to a probability.
- **It must say "uncalibrated" (suppress the number, output qualitative/per-segment only) when ANY of:**
  1. fewer than the D1 floor (50) of relevant outcome-labeled experiments exist, or the pooled effective-n for this change-type is below floor;
  2. the change-type is **off-support** — outside the validated regime/modality covered by the backtest (PSI of the raw signal g vs. training support beyond threshold);
  3. **prompt/paraphrase sign-flip rate** exceeds threshold (Codex C9) — the call is not robust;
  4. the change is **flagged networked/equilibrium** (A10) — out of scope for first-order simulation;
  5. **calibration has drifted** past its expiry (rolling re-fit failed / PSI drift on g).
- **It must never claim:** statistical significance of the eventual experiment, exact lift, individual-user truth, that the experiment is unnecessary, or validity outside the validated metric/population/horizon/modality (verbatim Codex 5.5 — we adopt it wholesale).

An "uncalibrated" output is a first-class, expected state, not a failure — it is the honest day-1 and off-support answer.

### D5 — One agreed metric set with numeric GO / NO-GO thresholds

All CIs by **paired bootstrap over experiments** (agent-level bootstrap is Monte-Carlo error only — Codex 6.3, we adopt). Baselines: always-flat/climatology, random-rank, metadata-only, empirical-Bayes archive prior, no-persona LLM panel (Codex 5.2). Metrics computed on the sign-non-null subset for SMR; full set for the rest.

**GO (deploy as calibrated triage aid, numeric confidence permitted) — ALL must hold:**

| # | Gate | Threshold | Owner |
|---|---|---|---|
| G1 | Null integrity (A/A + placebo) | ≤ 5% of null cases labeled actionable at confidence ≥ 0.70 | S1/S5 |
| G2 | Leakage (label-permutation) | shuffled-label SMR ∈ [0.40, 0.60] AND \|ρ\| < 0.10 AND 3-class MCC ∈ [−0.05, 0.05] | S5 |
| G3 | Sign accuracy | balanced SMR ≥ 0.70, Wilson 90% lower bound > 0.55 | S5 |
| G4 | Direction vs. baseline | 3-class MCC exceeds best baseline by ≥ 0.10 absolute, paired-bootstrap 95% CI LB > 0 | S5 |
| G5 | Ranking | Spearman ρ / Kendall τ_b ≥ 0.30 (mixed), ≥ 0.45 (text/copy), 95% CI LB > 0.10 | S5 |
| G6 | Calibration | ECE ≤ 0.08 on covered predictions AND Brier improves ≥ 10% over climatology | S4/S5 |
| G7 | Interval coverage | nominal 80% intervals cover 70–90% of realized shrunk effects | S4 |
| G8 | **Tail safety (side-constraint)** | top-decile true-winner recall ≥ 0.80 among ideas recommended for deprioritization; else re-rank only, no parking | S1/S5 |
| G9 | Persona value | persona-conditioned panel beats no-persona panel on ≥ 1 primary metric without hurting tail recall | S2/S3 |
| G10 | Abstention quality | abstained cases have materially lower covered-accuracy or higher instability than covered cases (else abstention is cosmetic) | S5 |
| **G11** | **PRIMARY — decision regret** | realized metric-gain-per-slot under π_sim beats π_0, paired-bootstrap CI lower bound > 0 at the PM's cost ratio L_FG/L_FR | S1 |
| G0 | Sample sufficiency | ≥ 50 floor for any numeric claim; ≥ 100 pooled-effective-n for G3; ≥ 150 for G4 | S5 |

**CONDITIONAL (qualitative / per-segment narratives only, numeric confidence SUPPRESSED):** G1, G2, G9, G10 pass but sample below the G0 thresholds for G3/G4, OR SMR ∈ [0.55, 0.70). Ships as an interview/diagnostic and redesign tool.

**NO-GO:** fails G1 (A/A) OR fails G2 (leakage) OR G3 lower bound ≤ 0.50 OR G11 regret CI lower bound ≤ 0 OR G8 tail recall < 0.80 while recommending parking. The simulator is not better than the PM's prior; ship no number.

This is one table both councils can sign: it is Codex's 10 thresholds verbatim (now G1–G10) **plus** our G11 decision-regret primary and G0 sample gate, with our SMR/ECE numbers tightened to Codex's where Codex was stricter (ECE 0.08 not 0.10) and the regret gate elevated to PRIMARY per D2.

---

## C. Revised merged claims ledger

> Numbered, falsifiable, one line each. Designed to be what Codex would also sign. `[HELD]` marks anything we keep over a Codex objection.

1. A simulator with no precise estimand (metric, population, treatment, control, horizon) is not directionally correct; the estimand is inherited from the eventual experiment. *(A3; Codex C1, Claude C2)*
2. The target is the **sign and rank** of the real ATE on a pre-registered primary metric with a metric-specific dead-band δ_m; magnitude is a non-goal and LLM magnitudes are shrunk. *(A2; C2/C10, Claude C2/C7)*
3. The live randomized experiment remains ground truth; the simulator is a calibrated causal prior and a **pre-experiment triage instrument, never a replacement**. *(A1; C3/C21, Claude C18)*
4. The LLM/persona layer is a **biased, sign-informative feature extractor** and must never directly emit a calibrated probability or magnitude; a fitted calibration + shrinkage layer trained on real past experiments does that. *(A4/A5; C4/C16/C23, Claude C5/C6/C8)*
5. Sign and rank are recoverable under badly biased magnitude because directional correctness needs only stochastic ordering (a monotone-calibration condition), not unbiased estimation. *(Claude C7)*
6. Elicitation is **metric-keyed, blinded, order-randomized, behavioral** (paired control/treatment delta, choice not Likert), with verbalized distribution elicitation as a feature the calibrator owns — not the reported confidence. *(A12; C6/C7/C24, Claude C8)*
7. **Sycophancy, prompt-format instability, and mode collapse are material and must be tested**; paraphrase sign-flip rate caps confidence or triggers abstention. *(A9/A12; C9/C24)*
8. Population construction is the **unified D3 spec**: real rows → soft segment membership (hard assignment banned) → persona-gestalt + row-delta conditioning → rake the weighted panel to the real joint distribution → accept only if |SMD| < 0.1 and between-unit response variance ≥ 0.5× target heterogeneity. *(A9; C5, Claude C9/C10)*
9. A **no-persona LLM panel is a mandatory baseline**; persona-plus-row conditioning is the leading hypothesis and must *empirically* beat it on held-out prediction without hurting tail recall — it is not assumed. *(A6; C4/C8, refined)*
10. The method is **valid only for first-order, non-networked changes**; network/marketplace/equilibrium/long-horizon changes are out of scope, flagged, and routed straight to experiment. *(A10; C11/C12, Claude C11)*
11. **Leakage is the dominant backtest threat**: predictions are hash-committed before unblinding, a label-permutation test must collapse SMR to ~0.5, and famous-vs-obscure SMR gaps must be within noise. *(A8; C16, Claude C12)*
12. **A/A placebo null is a disqualifying gate**: a simulator that manufactures directional signal from identical arms is out, regardless of backtest SMR. *(A7; C15, Claude C19)*
13. The decision loss is **asymmetric and the false-red / tail-winner miss is the most dangerous error because it is unobservable**; the system must be allowed to abstain and must **re-rank/redesign, not auto-kill**, unless tail-winner recall ≥ 0.80 is validated. *(A11; C19/C20, Claude C4/C16)*
14. **Decision regret vs. the PM's status-quo triage policy is THE primary criterion** (value iff regret CI lower bound < 0), **subject to a tail-winner-recall ≥ 0.80 side-constraint**; balanced acc, MCC, Brier, ECE, rank correlation are necessary gating diagnostics, not co-primaries. *(D2; reconciles Claude C3/C4 with Codex C14)*
15. **Every directional metric is reported with a CI by paired bootstrap over experiments**; agent-level bootstrap is Monte-Carlo error only and cannot substitute. *(Claude C14; Codex 6.3)*
16. **Sample gates:** ≥ 50 outcome-labeled sign-balanced experiments is the hard floor for any numeric claim; ≥ 100 pooled-effective-n for the SMR gate; ≥ 150–200 for the MCC-beats-baseline gate; below floor → "uncalibrated", qualitative-only. *(D1; reconciles Claude C13 with Codex C17/C18)*
17. The **confidence score** reports the calibrated P(sign class correct | regime, input quality, backtest coverage) and **must say "uncalibrated"** when below sample floor, off-support, prompt-unstable, networked, or calibration-drifted. *(D4; Claude C17, Codex 5.5)*
18. The **agreed GO/NO-GO gate is the D5 table (G0–G11)**, with decision regret (G11) as primary and Codex's 10 thresholds as G1–G10; NO-GO on A/A fail, leakage fail, SMR LB ≤ 0.5, regret LB ≤ 0, or tail recall < 0.80 while recommending parking. *(D5; merges both gates)*
19. **Calibration must be re-fit on a rolling, time-decayed basis** and expire after N weeks; the weekly product snapshot is the moving part and calibration drift is monitored (PSI on g). *(F6; Claude, Codex C25 model-version reruns)*
20. **Hierarchical partial pooling** across products and treatment-classes is mandatory when a single product is below the credible-n target; segment/class response priors from past experiments improve accuracy only where class-level sample sufficiency holds. *(D1; Codex C22, refined)*

---

## D. Remaining disagreements

Almost everything converged. Two items we hold, both narrow and both `[HELD]` for stated reasons; neither blocks a merged ledger.

1. **[HELD] Decision regret is PRIMARY, not co-equal in a 7-metric basket (ledger #14, D2).** Codex C14 lists the seven metrics as jointly "required to assess directional correctness," which reads as co-equal. We hold that exactly one number — regret-vs-status-quo, under a tail-recall side-constraint — decides ship/no-ship, and the other six are necessary *gating diagnostics* that can disqualify but cannot, alone, certify value. Reason: only regret is denominated in realized metric-gain-per-scarce-slot, the unit the product is sold on; a simulator can ace MCC and still destroy value if its errors land on high-traffic decisions. We believe Codex can sign this, since it preserves every Codex metric as a required gate and only adds a hierarchy.

2. **[HELD, soft] The "150–200" floor applies specifically to the 3-class-MCC-beats-baseline gate, not to every quantitative claim (ledger #16, D1).** Codex C18 states 150–200 as the blanket minimum credible range. The binomial math shows a single-product SMR gate (0.70, 90% LB > 0.55) already reaches 0.92 power at n=100, so we refuse a flat 150–200 for the sign claim while fully accepting it for the harder MCC-lift gate. This is a refinement, not a rejection — both numbers live in the merged ledger, each attached to the gate it powers. If Codex insists on 150 as a single conservative floor for all numeric claims, we would concede it as a product-safety choice rather than a statistical necessity; we do not consider this worth a Round 3.

No other open disagreements. A1–A12 stand; D1–D5 resolved as above.
