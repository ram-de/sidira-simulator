# Merged Claims Ledger (arbiter-canonical, v1) — for ratification

Built from the agreed core (A1–A12) plus the Round-2 resolutions of D1–D5 from
both councils. The two micro-deltas were arbiter-resolved as noted in M5 and M18.
Each claim is falsifiable and one line. Ratify by marking **AGREE** or
**OBJECT(reason)** per claim.

## Estimand & framing
- **M1.** A simulator with no precise estimand — metric, population, treatment,
  control, horizon, randomization unit, practical-null band δ — is not
  directionally correct in the causal sense.
- **M2.** The target is the **sign and rank** of the real ATE/ITT on a
  pre-registered primary metric; magnitude is a non-goal, and raw LLM magnitudes
  are expected to be inflated and must be shrunk.
- **M3.** The live randomized experiment remains ground truth; the simulator is a
  **calibrated causal prior for experiment triage, never a replacement**.
- **M4.** Sign and rank are recoverable even under badly biased magnitude,
  because directional correctness requires only stochastic ordering (a
  monotone-calibration condition), not unbiased estimation.

## The instrument
- **M5.** The LLM/persona layer is a **biased, sign-informative feature
  extractor**; it must never directly emit a calibrated probability, a magnitude,
  or a significance claim. A fitted calibration + shrinkage layer trained on real
  past experiments does that.
- **M6.** Elicitation is **metric-keyed, paired control/treatment delta, blinded,
  order-randomized, and behavioral** (choice, not Likert). Verbalized
  distribution elicitation is a *feature the calibrator owns*, not the reported
  confidence.
- **M7.** Sycophancy, prompt-format instability, and mode collapse are material
  biases and must be tested; paraphrase sign-flip rate caps confidence or
  triggers abstention.

## Population
- **M8.** Population construction = real row-level covariates → **soft** segment
  membership (hard assignment banned) → persona-gestalt + row-delta conditioning
  → rake/post-stratify the weighted panel to the **real joint covariate
  distribution**.
- **M9.** Balance gates: `|SMD| ≤ 0.10` primary covariates, `|SMD| ≤ 0.15` key
  two-way interactions, joint PSI ≤ 0.10 where measurable, no final weight > 5×
  median without a variance warning, and between-unit response variance ≥ 0.5×
  target heterogeneity (reject mode-collapsed runs).
- **M10.** A **no-persona LLM panel is a mandatory baseline**; persona-plus-row
  is the leading hypothesis and must *empirically* beat it on held-out prediction
  without hurting tail recall — never assumed. Run the full ablation set
  (persona-only, row-only, soft, hard, no-persona).

## Scope
- **M11.** Valid only for **first-order, non-networked** changes. Network,
  marketplace, equilibrium, virality, congestion, and long-horizon adaptation
  effects are out of scope, flagged, and routed straight to experiment unless an
  explicitly calibrated interaction layer is added.

## Validation integrity
- **M12.** **A/A placebo null is a disqualifying gate**: a simulator that
  manufactures directional signal from identical arms is out, regardless of
  backtest SMR.
- **M13.** **Leakage is the dominant backtest threat**: predictions are
  hash-committed before unblinding; a label-permutation test must collapse
  balanced SMR to ~0.5 (MCC to ~0, |ρ| < 0.10); famous-vs-obscure SMR gaps must
  be within noise.
- **M14.** Experiment ground truth is itself noisy and must be quality-weighted:
  SRM failures, peeking, low power, and guardrail vetoes are downweighted or
  modeled. Backtests weight by statistical power/quality.
- **M15.** Every directional metric is reported with a **CI by paired bootstrap
  over experiments**; agent-level bootstrap is Monte-Carlo error only and cannot
  substitute.

## The decision
- **M16.** The decision loss is **asymmetric**: the false-red / tail-winner miss
  is the most dangerous error because it is unobservable. The system must be
  allowed to **abstain** and must **re-rank / redesign, not auto-kill**, unless
  tail-winner recall ≥ 0.80 is validated.
- **M17.** **Decision-utility improvement vs. the PM's status-quo triage policy
  (ΔU = U(π_sim) − U(π₀)) is THE primary criterion** — GO requires ΔU 90%
  bootstrap lower bound > 0 — **subject to a tail-winner-recall ≥ 0.80
  side-constraint**. The diagnostic basket (balanced SMR, MCC, Kendall τ_b,
  Brier, ECE, null integrity, robustness, abstention quality) are necessary
  *disqualifying gates*, not co-primaries: none alone certifies value, any alone
  can disqualify.

## Confidence & calibration
- **M18.** The **confidence score** reports calibrated empirical reliability of
  the predicted sign class: P(sign class correct | validated regime, input
  quality, backtest coverage, pinned version). It does **not** report LLM
  certainty, individual-user truth, significance, expected magnitude, or
  permission to skip the experiment.
- **M19.** It must read **"uncalibrated"** (suppress the number; qualitative
  output only) when: below the sample floor; either sign class < 10 examples;
  local support effective-n < 20; off-support by metric/surface/population/
  treatment-type/covariate-distribution; prompt sign-flip rate > 10%; flagged
  networked; rendering unverifiable; version changed without golden-set rerun; or
  covered-prediction ECE > 0.10.
- **M20.** Calibration is re-fit on a **rolling, time-decayed basis** and expires
  after N weeks; the weekly product snapshot is the moving part, and calibration
  drift is monitored (PSI on the raw signal g). Model/prompt/population/
  calibration versions are pinned and rerun on a golden set before any accuracy
  claim transfers to a new release.
- **M21.** **Hierarchical partial pooling** across products and treatment-classes
  is mandatory when a single product is below its credible-n target; the pooled
  effective-n is what the gate reads. Segment/class response priors help only
  where class-level sample sufficiency holds.
- **M22.** Persona narratives are valuable for hypothesis generation, PM
  interviewing, and redesign, but are **not evidence** unless tied to observed
  features or calibrated response priors.

## The certification gate (G0–G11) — the operating contract
GO as a quantitative triage aid requires ALL of:
- **G0 — Sample sufficiency.** `n_dir ≥ 50` floor (both signs ≥ 10) for any
  numeric claim; `≥ 100` pooled-effective-n for the SMR gate; `≥ 150` (≈200 for
  sliced claims) for the MCC-beats-baseline gate. Below floor → uncalibrated.
- **G1 — A/A null integrity.** Identical-arm tests yield an actionable call at
  confidence ≥ 0.70 in ≤ 5% of runs.
- **G2 — Robustness.** Prompt/order sign-flip rate ≤ 10%; demand-effect bias CI
  contains 0.
- **G3 — Leakage.** Label permutation collapses balanced SMR to [0.40, 0.60],
  MCC to [−0.05, 0.05], |ρ| < 0.10.
- **G4 — Direction.** Balanced SMR ≥ 0.70, Wilson/bootstrap 90% LB > 0.55.
- **G5 — Classification.** 3-class (pos/flat/neg) MCC beats the best non-LLM
  baseline by ≥ 0.10, paired-bootstrap 90% LB > 0.
- **G6 — Ranking.** Kendall τ_b ≥ 0.30, 90% LB > 0.
- **G7 — Calibration.** ECE ≤ 0.08 (arbiter-merged: GO ≤0.08, CONDITIONAL
  0.08–0.15, NO-GO >0.15); Brier improves over climatology by ≥ 10%.
- **G8 — Decision value (PRIMARY).** ΔU = U(π_sim) − U(π₀) > 0, bootstrap 90%
  LB > 0, at the pre-registered slot budget and false-green/false-red cost ratio.
- **G9 — Tail safety.** Top-decile true-winner recall ≥ 0.80 among ideas the
  simulator would deprioritize below the test cutoff.
- **G10 — Abstention quality.** Covered predictions have strictly lower error
  than the full set; risk decreases monotonically as coverage narrows.
- **G11 — Persona value.** Persona-plus-row beats the no-persona panel on ≥ 1
  primary metric with no primary metric worse by > 0.02; else suppress
  persona-specific accuracy claims and ship the best validated configuration.

**NO-GO** (numeric confidence forbidden) if any: G0 fails; G1 or G3 fails; SMR
90% LB ≤ 0.50; ΔU 90% LB ≤ 0; ECE > 0.15; Brier fails to beat climatology; tail
recall < 0.70 while recommending deprioritization; or sign-flip rate > 20%.
**CONDITIONAL** (between GO and NO-GO): qualitative interview aid, redesign
support, rank-only internal research — no numeric confidence, no auto-kill.
