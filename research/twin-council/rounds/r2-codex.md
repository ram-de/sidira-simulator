# Codex Council — Round 2

## A. Marks on Claude's ledger

1. **AGREE**.
2. **AGREE**.
3. **REFINE** — decision regret is the primary value criterion, but not the sole validity gate; null integrity, calibration, rank, and tail safety remain mandatory diagnostics.
4. **AGREE**.
5. **AGREE**.
6. **AGREE**.
7. **REFINE** — sign/rank are recoverable only if the raw simulator score is empirically stochastically ordered with real effects; this is a testable condition, not an assumption.
8. **AGREE**.
9. **REFINE** — raking/post-stratification must include row-level covariates and soft persona-membership probabilities; soft personas are not an alternative to population weighting.
10. **REFINE** — the 0.5 heterogeneity floor is acceptable as a gate when the target heterogeneity estimate comes from real segment dispersion, historical response priors, or a held-out human panel.
11. **AGREE**.
12. **AGREE**.
13. **REFINE** — `>=50` is the hard floor for provisional quantitative claims; `150-200` is the credible target for strong product-level certification.
14. **AGREE**.
15. **REFINE** — adopt the Claude gates but add MCC/Brier improvement, tail-winner recall, and explicit bootstrap lower-bound requirements.
16. **AGREE**.
17. **REFINE** — confidence reports calibrated sign-class reliability conditional on calibration coverage, prompt/model version, input quality, and support; off-support or underpowered regimes must say `uncalibrated`.
18. **AGREE**.
19. **AGREE**.
20. **AGREE**.

## B. Resolutions to D1-D5

### D1 — Historical-experiment count

Resolved:

- **Hard floor:** `n_dir >= 50` non-null, sign-decisive historical experiments for any quantitative directional-accuracy claim.
- **Credible target:** `n_dir >= 150` for a credible customer/product-level claim; `n_dir ~= 200` before slicing claims by surface, metric family, modality, or segment.

Here `n_dir` means historical experiments whose true label is positive or negative after the practical-null dead-band. Null experiments are still required to validate abstention and flat-class calibration; if nulls are common, the total archive usually needs more than 50 experiments to yield `n_dir = 50`.

Statistical justification using Wilson intervals for an observed balanced SMR of 0.70:

- At `n = 50`, 90% CI is approximately `[0.585, 0.794]`, width `0.209`.
- At `n = 150`, 90% CI is approximately `[0.635, 0.758]`, width `0.122`.
- At `n = 200`, 90% CI is approximately `[0.644, 0.750]`, width `0.106`.

So Claude’s `>=50` is acceptable only as a **minimum provisional floor**: it can distinguish a strong observed 0.70 SMR from coin-flip only coarsely. Codex’s `150-200` is the right range for **credible certification**, because the SMR half-width drops from about `+/-0.10` at 50 to about `+/-0.06` at 150 and `+/-0.05` at 200.

### D2 — Primary criterion

Resolved:

- **Single primary criterion:** cost-weighted decision utility improvement versus the PM/status-quo triage policy.

Use:

\[
\Delta U = U(\pi_{sim}) - U(\pi_0)
\]

The simulator has demonstrated product value only if `Delta U > 0` with a bootstrap 90% lower confidence bound above 0 at the pre-registered experiment-slot budget and false-green / false-red cost ratio.

Supporting diagnostic basket:

- Balanced SMR on non-null effects.
- 3-class MCC over positive / flat / negative.
- Kendall `tau_b` for ranking.
- Brier improvement over climatology.
- ECE / reliability.
- Null A/A integrity.
- Leakage / permutation collapse.
- Prompt/order stability.
- Tail-winner recall.
- Abstention quality.
- Persona lift over no-persona baseline.

Decision regret is therefore **the primary value criterion**, but it is not allowed to launder a system that fails calibration, null, leakage, or tail-safety gates.

### D3 — Unified population-construction spec

Resolved population spec:

1. Start from real pre-treatment user rows where available: tenure, plan, device, geography, usage intensity, feature adoption, recency/frequency, lifecycle state, prior pain points, and metric-relevant behavioral history.
2. Estimate **soft persona membership** for each row: `z_i = [p(persona_1), ..., p(persona_K)]`. Never collapse overlapping users to hard archetypes unless an ablation proves no loss.
3. Treat persona probabilities as covariates, not replacements for covariates.
4. Construct the simulated population by calibration weighting / raking / post-stratification to the real joint distribution of core covariates and key interactions.
5. Balance requirements:
   - All primary covariates: `|SMD| <= 0.10`.
   - Key two-way interactions: `|SMD| <= 0.15`.
   - Joint distribution PSI: `<= 0.10` where measurable.
   - Weight cap: no final weight above `5x` the median weight without an explicit variance warning.
6. Agent conditioning uses both:
   - row-level facts for the sampled user;
   - the full soft persona-membership vector, including entropy.
7. Segment-level claims require effective simulated sample size `>=100` in the displayed segment and historical calibration support `>=20` comparable cases; otherwise show the segment qualitatively only.

This reconciles the councils: raking/post-stratification gives representativeness; soft persona membership preserves ambiguity and interpretability.

### D4 — Confidence-score semantics

Resolved:

The confidence score is:

\[
\hat{p}_{\hat{s}} = P(S = \hat{s} \mid g, X, R, M_v, Q)
\]

where:

- `S` is the true experiment sign class after the dead-band: positive, flat, or negative.
- `hat{s}` is the simulator’s predicted class.
- `g` is the raw simulator signal.
- `X` includes treatment type, metric, population, surface, and input-quality features.
- `R` is the validated regime / support region.
- `M_v` is the pinned model and prompt version.
- `Q` includes prompt stability, rendering validity, and experiment-quality weighting.

It reports **empirical calibrated reliability of the predicted sign class**, estimated out-of-fold from historical experiments. It does not report LLM certainty, individual-user truth, statistical significance, expected lift magnitude, or permission to skip a live experiment.

The system must say **`uncalibrated`** and suppress numeric confidence when any of these hold:

- `n_dir < 50` for the relevant customer/product calibration.
- Either positive or negative class has fewer than 10 historical non-null examples.
- The local calibration bin / nearest support region has effective `n < 20`.
- The change is off-support by metric, surface, population, treatment type, or covariate distribution.
- The model or prompt version changed without a golden-set rerun.
- A/A null, leakage, or label-permutation gates fail.
- Prompt/order sign-flip rate exceeds `10%`.
- Treatment/control rendering cannot be verified.
- Calibration quality on the validation set fails: `ECE > 0.10` for covered predictions.

In those cases the product may still show raw directional signal, segment narratives, and experiment-design advice, but the confidence field must read `uncalibrated`.

### D5 — Agreed metric set and numeric thresholds

All CIs below are computed over experiments, not agents.

**GO as quantitative triage aid requires all of:**

1. **Sample floor:** `n_dir >= 50`, both signs represented with at least 10 examples each. Credible certification label requires `n_dir >= 150`.
2. **A/A null integrity:** identical-arm tests produce actionable positive/negative calls at confidence `>=0.70` no more than `5%` of the time.
3. **Prompt/order robustness:** sign-flip rate across order swaps and prompt perturbations `<=10%`; demand-effect bias CI contains 0.
4. **Leakage check:** label permutation collapses balanced SMR to `[0.40, 0.60]`, MCC to `[-0.05, 0.05]`, and `|rho| < 0.10`.
5. **Direction:** balanced SMR `>=0.70` with 90% lower bound `>0.55`.
6. **3-class classification:** MCC beats the best non-LLM baseline by `>=0.10`, with paired-bootstrap 90% lower bound `>0`.
7. **Ranking:** Kendall `tau_b >=0.30`, with 90% lower bound `>0`.
8. **Calibration:** ECE `<=0.10`; Brier score improves over climatology by `>=10%`.
9. **Decision value:** `Delta U = U(pi_sim) - U(pi_0) > 0`, with bootstrap 90% lower bound `>0`.
10. **Tail safety:** top-decile true-winner recall `>=0.80` among ideas the simulator would deprioritize below the test cutoff.
11. **Abstention quality:** covered predictions have lower error than the full set, and risk decreases monotonically as coverage narrows.
12. **Persona value claim:** persona-plus-row must beat the no-persona panel on at least one primary metric with no primary metric worse by more than `0.02`; otherwise suppress persona-specific accuracy claims and use the best validated configuration.

**NO-GO for numeric confidence if any of these occur:**

- Sample floor fails.
- A/A null or leakage gate fails.
- Balanced SMR 90% lower bound `<=0.50`.
- Decision-value lower bound `<=0`.
- ECE `>0.15`.
- Brier fails to beat climatology.
- Tail-winner recall `<0.70` while the product recommends deprioritization.
- Prompt/order sign-flip rate `>20%`.

Between GO and NO-GO is **CONDITIONAL**: qualitative interview aid, redesign support, or rank-only internal research, but no numeric confidence and no auto-kill recommendation.

## C. Revised merged claims ledger

1. A simulator that does not specify metric, population, treatment, control, horizon, randomization unit, and practical-null band is not directionally correct in the causal sense.
2. The live randomized experiment remains ground truth; the simulator is a calibrated prior for experiment triage, not a replacement.
3. Directional correctness must be measured on held-out or prospective historical experiments, not inferred from persona realism.
4. The target claim is sign and rank of the real ATE/ITT on a pre-registered primary metric, not uncalibrated lift magnitude.
5. Quantitative directional claims require `n_dir >=50`; credible customer/product certification requires `n_dir >=150`, with `~200` preferred for sliced claims.
6. The LLM/persona layer is a biased feature extractor; it must not directly emit calibrated probability, magnitude, or experiment significance.
7. A fitted calibration layer trained on real past experiments is mandatory before showing numeric confidence.
8. The confidence score is calibrated empirical reliability of the predicted sign class conditional on support, version, input quality, and prompt stability.
9. Off-support, underpowered, unstable, or failed-gate predictions must say `uncalibrated`.
10. Population construction must combine real row-level covariates, soft persona membership, and raking/post-stratification to the real joint covariate distribution.
11. Population balance must meet `|SMD| <=0.10` for primary covariates and `|SMD| <=0.15` for key interactions.
12. Persona-plus-row, row-only, persona-only, hard-assignment, soft-assignment, and no-persona panels must be evaluated as ablations; personas must earn predictive lift.
13. Elicitation must be paired treatment/control delta elicitation, blinded, order-randomized, and behavioral rather than generic sentiment or Likert liking.
14. Prompt paraphrase instability predicts lower out-of-sample accuracy and must cap confidence or trigger abstention.
15. A/A placebo tests are disqualifying gates; a simulator that manufactures signal from identical arms cannot be trusted.
16. Leakage controls are mandatory: prediction hash-commitment before unblinding and label-permutation collapse to chance.
17. Network, marketplace, equilibrium, virality, congestion, and long-run adaptation effects are out of scope unless modeled with an explicitly calibrated interaction layer.
18. Decision utility improvement versus status-quo triage is the primary value criterion; GO requires `Delta U` 90% lower bound above 0.
19. Directional diagnostics remain mandatory: balanced SMR, MCC, Kendall `tau_b`, Brier, ECE, null integrity, robustness, abstention quality, and tail-winner recall.
20. Tail-winner false negatives are the most dangerous backlog-triage error; no auto-kill or hard deprioritization is allowed unless tail-winner recall is `>=0.80`.
21. Raw LLM effect magnitudes are expected to be inflated and must be shrunk; magnitude claims require separate validation.
22. Experiment ground truth must account for experiment quality: SRM failures, peeking, low power, guardrail vetoes, and standard errors should be modeled or downweighted.
23. Segment-level simulator claims require adequate simulated effective sample size and historical calibration support; otherwise segment output is explanatory only.
24. Persona narratives are useful for hypothesis generation and PM redesign, but they are not evidence unless tied to observed features or calibrated response priors.
25. Model, prompt, population, and calibration versions must be pinned and rerun on a golden set before any accuracy claim transfers to a new release.

## D. Remaining disagreements

None. No claim above is held over an unresolved Claude objection. The Round 1 differences are resolved as:

- `50` historical directional cases is the hard quantitative floor; `150-200` is the credible certification range.
- Decision regret is the primary value criterion; the metric basket remains mandatory for validity and safety.
- Soft persona membership and raked/post-stratified joint population calibration are one unified population spec.
- Confidence is calibrated sign-class reliability and must say `uncalibrated` outside validated support.
- The merged GO/NO-GO thresholds above are the shared operating gate.