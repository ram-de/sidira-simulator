# Position Paper — Codex Council, Round 1

## 1. Thesis (≤200 words)

A directionally correct behavioral simulator should not be framed as a population of “digital twins.” It should be framed as a calibrated causal prior over a backlog of product changes. Its job is to rank candidate experiments and estimate the probability that each is positive, flat, or harmful on a specified business metric. The live experiment remains the ground truth.

The method is defensible only if it combines five ingredients: a precise causal estimand; population sampling from real user data with preserved heterogeneity; treatment/control delta elicitation rather than generic sentiment; calibration against historical randomized experiments; and a standing backtest harness that beats honest null baselines. LLM agents can contribute useful priors, especially for text, messaging, and first-impression preference tasks, but they are biased instruments: sycophantic, prompt-sensitive, mode-collapsing, and poor individual clones. Personas are useful scaffolding for stratification, interpretability, and interviewing, not the scientific source of truth.

The council’s core position: trust sign and rank only after blind, hash-committed validation; shrink magnitudes aggressively; abstain in weak regimes; and never use the simulator to kill tail-risk ideas outright.

## 2. Definition of directional correctness (the estimand + loss + decision)

Let product change \(j\) define a treatment \(T_j\) and a control \(C_j\), usually the current product. Let \(Y_i(t, h, m)\) be user \(i\)'s outcome on target metric \(m\) over horizon \(h\) under product state \(t\). The causal estimand is the product-population ATE or ITT:

\[
\tau_j = E_{i \sim P_t}[Y_i(T_j, h, m) - Y_i(C_j, h, m)]
\]

This follows the potential-outcomes lineage from Neyman, Rubin, and Holland: causal effects are contrasts between treatment and control potential outcomes, not free-floating opinions. The simulator cannot observe those counterfactuals; it predicts a distribution over \(\tau_j\). Known lineage: potential outcomes and the “fundamental problem of causal inference” are the right formal language for the target. ([en.wikipedia.org](https://en.wikipedia.org/wiki/Rubin_causal_model?utm_source=openai))

Define a metric-specific practical-null band \(\delta_m\). This should be pre-registered from the company’s experiment practice: the larger of the business minimum detectable useful effect, the experiment archive’s noise floor, and an outcome-specific guardrail threshold. Labels are:

- positive: \(\tau_j > \delta_m\)
- flat: \(|\tau_j| \le \delta_m\)
- negative: \(\tau_j < -\delta_m\)

The simulator returns:

\[
\hat{p}_{j,+}, \hat{p}_{j,0}, \hat{p}_{j,-}, \hat{\tau}^{raw}_j, \hat{\tau}^{cal}_j, I_j
\]

where \(I_j\) is a calibrated interval after shrinkage. The confidence score is not “confidence the LLM is right.” It is the calibrated probability that the predicted sign class is correct, conditional on the validated regime, input quality, model version, and abstention policy.

The PM’s actual decision is not “ship or do not ship.” It is:

1. Which ideas should enter scarce A/B-test slots first?
2. Which ideas require redesign before testing?
3. Which obviously dominated variants should be merged, reframed, or deprioritized?
4. Which ideas are outside the simulator’s validated regime and must go straight to experiment or research?

The loss function should match that decision:

\[
L = \lambda_1 \cdot 1[\hat{s}_j \ne s_j] + \lambda_2 \cdot \text{rank regret}_j + \lambda_3 \cdot \text{tail false negative}_j + \lambda_4 \cdot \text{miscalibration}_j
\]

The tail false-negative penalty must be large. A simulator that filters out rare high-upside winners can be commercially harmful even if its average sign accuracy looks good.

Seat positions:

- S1: The estimand must be a real experimental contrast on a named metric. Generic “user reception” is not an estimand.
- S2: LLM outputs are measurement instruments for a latent response distribution, not observations from humans.
- S3: If user outcomes depend on other users’ treatment exposure, the estimand must include network assignment conditions; otherwise SUTVA is violated.
- S4: Stated intention is not the target; revealed behavior is. Use stated reactions only after calibration.
- S5: “Directionally correct” means outperforming baselines on sign, rank, calibration, and regret, with uncertainty.

## 3. The method

### 3.1 Causal target contract

Every simulation starts with a target contract:

- metric: e.g. activation, click-through, paid conversion, retention, watch time
- horizon: e.g. first session, 7 days, 28 days
- randomization unit: user, account, session, geo, cluster
- eligible population: inclusion and exclusion criteria
- control state: what remains unchanged
- treatment state: what changes
- guardrails: metrics on which negative movement vetoes a “positive” result
- practical-null band \(\delta_m\)

Known: Online controlled experiments require disciplined metric, unit, horizon, and data-quality definitions. The online experimentation literature emphasizes SRM, OEC definition, novelty effects, interference, and variance reduction as first-class issues. ([arxiv.org](https://arxiv.org/abs/2212.11366?utm_source=openai))

Defensible inference: A behavioral simulator should inherit these exact experiment definitions. If the eventual experiment would be user-randomized over 28-day retention, the simulation should not predict generic first-impression sentiment.

### 3.2 Canonical treatment rendering

The simulator must render both product states in a machine-checkable format:

- current-state snapshot from crawl or product spec
- treatment diff
- “not changing” guard
- user journey context
- metric mechanism hypothesis
- screenshots or structured UI state where relevant

The agent prompt should be design-unblinded: it should say what changed and what held fixed. The benchmark scorer must remain outcome-blinded.

Mitigation: run 3-5 paraphrases of the same treatment contract. If sign flips under semantically equivalent wording, confidence is capped or the simulator abstains. Prompt-format sensitivity is documented; Sclar et al. show large performance swings from spurious prompt formatting. ([arxiv.org](https://arxiv.org/abs/2310.11324?utm_source=openai))

### 3.3 Population model

Build a weighted user population from real behavioral data:

- sample real anonymized rows when allowed
- otherwise sample synthetic rows from a fitted generative model
- preserve feature covariance, not just marginal demographics
- retain soft persona membership probabilities
- stratify by business-relevant weights: users, revenue, orders, active population
- carry posterior entropy and segment stability into confidence

Known lineage: Survey sampling and post-stratification say weighted representativeness matters. Computational social science and agent-based modeling say heterogeneity is not decoration; it changes aggregate outcomes. Causal forests and related HTE methods show that treatment effects can vary strongly by covariates. ([arxiv.org](https://arxiv.org/abs/1510.04342?utm_source=openai))

Defensible inference: personas should be a compression and interpretation layer. They should not collapse ambiguous users into hard archetypes. A user with 0.45/0.35/0.20 posterior mass across three segments should generate mixed response priors, not a crisp fictional identity.

### 3.4 Hierarchical agent conditioning

Each simulated unit receives:

- persona gestalt: the segment’s behaviorally grounded pattern
- individual row deltas: how this sampled user differs from the segment centroid
- empirical seed values: tenure, recent behavior, current state, pain point, device, plan
- measured response priors: prior segment responses to similar historical treatments where available

The council rejects pure archetype prompting as insufficient. A persona-only agent is too close to stereotype. A row-only agent may predict better but loses interpretability. The preferred design is persona-plus-row, then ablate it against row-only, persona-only, and generic LLM panels.

Known: LLM “silicon sample” work argues models can approximate subgroup response distributions when conditioned appropriately, not that they are literal people. Argyle et al. introduced this algorithmic-fidelity framing. ([arxiv.org](https://arxiv.org/abs/2209.06899?utm_source=openai))

Known: generative-agent architectures can produce believable behavior in sandbox settings, but “believable” is not the same as causally accurate. Park et al. are useful for memory/planning architecture, not for proving A/B-prediction validity. ([arxiv.org](https://arxiv.org/abs/2304.03442?utm_source=openai))

### 3.5 Delta elicitation, not sentiment polling

For each sampled user \(i\), elicit a distribution over behavior under treatment and control:

\[
\hat{d}_i = \hat{Y}_i(T_j) - \hat{Y}_i(C_j)
\]

Use paired seeds: the same sampled user sees control and treatment. Ask metric-keyed questions, not generic “do you like this?” Examples:

- “Would this make you more or less likely to complete checkout in this session?”
- “Would this increase, decrease, or not change the probability that you watch another episode today?”
- “Which of these two variants would you click first, if any?”

Use verbalized distribution elicitation: ask the model to allocate 100 probability points across positive, flat, and negative behavioral response, with brief rationale. Sample multiple completions at nonzero temperature. Aggregate distributions, not single deterministic reactions.

Known from survey methodology: response wording, retrieval, judgment, and response selection shape stated answers; the Tourangeau/Rips/Rasinski survey-response model is the right cautionary lineage. Social desirability and acquiescence biases also apply to LLM agents because their training favors helpful agreement. ([en.wikipedia.org](https://en.wikipedia.org/wiki/Acquiescence_bias?utm_source=openai)) ([en.wikipedia.org](https://en.wikipedia.org/wiki/Social-desirability_bias?utm_source=openai))

### 3.6 Calibration and shrinkage

Raw simulated effects are not product effects. Fit a calibration layer on historical experiments:

\[
\tau^{real}_j = \alpha + \beta \hat{\tau}^{raw}_j + \gamma^\top X_j + \epsilon_j
\]

where \(X_j\) includes modality, metric, population, input quality, prompt stability, segment entropy, and model version. Use hierarchical shrinkage by treatment class. Report raw and calibrated effects separately.

Known: LLM panels often inflate magnitudes even when signs are useful. The defensible claim is rank/sign after calibration, not absolute lift.

Defensible inference: until enough customer-specific experiments exist, use conservative global shrinkage and widen intervals. After 150-200 customer experiments, customer-specific calibration should dominate generic priors.

### 3.7 Response-grounded personas

When historical experiments exist, estimate heterogeneous treatment effects:

- causal forest or doubly robust learner per experiment
- GATES by persona and by soft-membership groups
- segment-level response priors for recurring treatment classes
- test whether personas explain CATE variance better than demographic and metadata baselines

Known: causal forests provide a lineage for estimating HTE under assumptions such as unconfoundedness in observational settings or randomization in experiments. ([arxiv.org](https://arxiv.org/abs/1510.04342?utm_source=openai))

Defensible inference: a persona that does not stratify past treatment response should not be trusted to stratify future simulated response. It may still be useful for explanation, but not for accuracy.

### 3.8 Network and interaction layer

Default independent-agent simulation is acceptable only for individual-response estimands: copy changes, onboarding UX, price framing, recommendation labels, empty-state messaging, and other first-exposure decisions.

For social products, marketplaces, ranking systems, and collaboration products, S3 requires an explicit interaction model:

- graph or bipartite marketplace structure
- exposure model
- peer effects
- supply-demand constraints
- equilibrium or repeated-session dynamics
- cluster-randomization estimand if interference is unavoidable

Speculation: LLM agents may help generate plausible behavioral rules for an agent-based model. They should not be trusted to solve equilibrium dynamics directly.

### 3.9 Output policy

The product output should be:

- predicted sign class with calibrated probabilities
- rank among candidate ideas
- practical-null probability
- key segment drivers
- uncertainty reasons
- abstention when outside validated regime
- suggested experiment design, not a replacement decision

The output must say “validated regime” explicitly. Example: “High confidence for text/copy CTR ranking; low confidence for networked marketplace equilibrium.”

## 4. Failure modes & mitigations

| Failure mode | Seat most concerned | Status | Mitigation |
|---|---:|---|---|
| Simulated effect is not the real ATE | S1 | Known | Require metric, treatment, control, population, horizon; calibrate only against randomized ground truth; call output a prior |
| Generic sentiment substituted for target metric | S1/S4 | Known | Metric-keyed elicitation; no generic confidence score as scientific endpoint |
| Stated preference diverges from revealed behavior | S4 | Known | Calibrate to experiments; prefer choice tasks and behavioral probabilities over Likert liking |
| Sycophancy toward PM hypothesis | S2/S4 | Known | Neutral prompts, hide PM preference, ask for reasons against, adversarial prompt variants; sycophancy benchmarks. Sycophancy is documented in RLHF models. ([arxiv.org](https://arxiv.org/abs/2310.13548?utm_source=openai)) |
| Mode collapse / demographic flattening | S2/S3 | Known | Nonzero temperature, distribution elicitation, row-level conditioning, posterior sampling, no-persona control |
| Persona stereotyping | S2/S4 | Known | Ground persona claims in observed data; hedge inferred motivations; survey-fuse attitudes before claiming JTBD |
| Hard segment assignment erases heterogeneity | S3/S5 | Defensible inference | Soft memberships, posterior entropy, within-segment seed pools |
| Network and spillover effects | S3/S1 | Known | Declare out of scope unless modeled; use graph ABM or require live experiment |
| Novelty, learning curves, long-run adaptation | S3/S4 | Known | Separate first-exposure, short-horizon, and long-horizon estimands; do not extrapolate |
| Product-state hallucination | S2 | Known | Structured crawl/state diff, screenshots, treatment/control rendering tests |
| Prompt-format instability | S2/S5 | Known | Paraphrase ensemble, format-spread tests, confidence cap on sign instability |
| Leakage from public experiments | S5 | Known | Use unpublished archives, time splits, hash-committed predictions, contamination labels |
| Small-n ground truth noise | S5/S1 | Known | Use shrunk experiment estimates; model ground-truth uncertainty; disattenuated correlation as secondary only |
| Always-flat baseline beats naive accuracy | S5 | Known | Balanced accuracy, MCC, Brier vs climatology, rank/regret; never raw accuracy |
| Tail-winner suppression | S1/S5 | Known | Tail false-negative metric; policy: re-rank, do not auto-kill |
| Model drift across LLM releases | S2/S5 | Known | Version pinning; golden-set rerun; model card per simulator version |
| PM uses output as proof | S1/S4 | Organizational | UI and docs must frame as calibrated prior; require experiment recommendation |

## 5. Validation protocol (metrics, backtest, thresholds)

### 5.1 Backtest design

Use three tiers.

Tier 0: public benchmark suite.

- Upworthy-style headline tests for text/CTR ranking
- survey-experiment treatment archives for text-framed persuasion and policy effects
- Hillstrom and Criteo-style uplift datasets for end-to-end user-feature-to-treatment-response validation
- placebo and A/A null suite

Tier 1: customer archive blind backtest.

- minimum 150 historical experiments for quantitative claims
- 50-149 experiments allowed only for exploratory calibration
- below 50 experiments: no accuracy claim; use generic priors and abstain more often
- Sidira receives pre-launch artifacts only: PRD, screenshots, target metric, population, date, product context
- ground truth is withheld
- predictions are hash-committed before unblinding
- score against baselines

Tier 2: prospective registry.

- predictions timestamped before experiment launch
- quarterly scorecard
- no cherry-picking of public wins
- model/prompt version locked

### 5.2 Baselines

Every report must beat these, not a strawman:

- always-flat / climatology
- random rank
- metadata-only model: metric, surface, team, population, treatment type
- empirical-Bayes prior from experiment archive
- no-persona base LLM panel
- PM or expert forecast, if available
- simple copy-only model for text benchmarks

### 5.3 Metrics

Primary metrics:

- 3-class balanced accuracy: positive / flat / negative
- Matthews correlation coefficient for 3-class direction
- Brier score for \(P(positive)\), \(P(flat)\), \(P(negative)\)
- expected calibration error with 10 equal-frequency bins
- Spearman \(\rho\) and Kendall \(\tau\) for ranking by calibrated effect
- precision@k for selecting the top experiment candidates
- decision regret versus oracle and versus baseline
- tail-winner recall: fraction of top-decile true winners not deprioritized
- abstention quality: accuracy on covered cases and error rate on abstained cases

Secondary metrics:

- Pearson \(r\) on calibrated effect sizes
- calibration slope and intercept
- 80% interval coverage
- persona lift over no-persona panel
- modality-stratified performance
- cohort-stratified performance
- prompt-stability sign-flip rate

### 5.4 Go/no-go thresholds

For production use as experiment triage, the simulator must satisfy all of these on a blind customer archive or on a relevant public benchmark for the claimed regime:

1. Null integrity: on placebo/A/A tests, no more than 5% are labeled actionable positive or actionable negative at confidence ≥0.70.
2. Leakage check: shuffled outcome labels produce \(|\rho| < 0.10\) and MCC in \([-0.05, 0.05]\).
3. Direction: 3-class MCC exceeds the best baseline by at least 0.10 absolute, with paired bootstrap 95% CI lower bound above 0.
4. Balanced accuracy: exceeds best baseline by at least 8 percentage points, with 95% CI lower bound above 0.
5. Ranking: Spearman \(\rho \ge 0.30\) for mixed product changes, \(\rho \ge 0.45\) for text/copy regimes, with 95% CI lower bound above 0.10.
6. Calibration: Brier improves over climatology by at least 10%; ECE ≤0.08 for covered predictions.
7. Intervals: nominal 80% calibrated intervals cover 70-90% of realized shrunk effects.
8. Tail safety: top-decile true-winner recall ≥0.80 among ideas the product recommends deprioritizing. If not met, the product may re-rank only and must not recommend parking ideas.
9. Persona value: persona-conditioned panel beats no-persona panel on at least one primary metric without hurting tail-winner recall.
10. Abstention: abstained cases have materially lower expected accuracy or higher prompt instability than covered cases; otherwise abstention is cosmetic.

S5 dissent: these thresholds are starting gates, not scientific constants. They should be tightened after the first 300 prospective experiments.

### 5.5 What an honest confidence score may claim

It may claim:

- calibrated probability that the sign class is correct
- whether the prediction is inside a validated treatment modality
- whether the model is stable to paraphrase and sampling
- whether historical calibration exists for similar changes

It must not claim:

- statistical significance of the eventual experiment
- exact lift
- individual-user truth
- that the experiment is unnecessary
- validity outside the validated metric, population, horizon, or modality

## 6. The test harness (concrete, runnable spec)

### 6.1 Inputs

A runnable harness has these files.

`experiments.jsonl`:

```json
{
  "experiment_id": "exp_001",
  "date": "2025-04-12",
  "surface": "onboarding",
  "metric": "activation_7d",
  "horizon_days": 7,
  "randomization_unit": "user",
  "population_query": "new_users_us_mobile",
  "control_artifact": "artifacts/exp_001/control.json",
  "treatment_artifact": "artifacts/exp_001/treatment.json",
  "prd_artifact": "artifacts/exp_001/prd.md",
  "guardrails": ["refund_rate", "support_contact_rate"],
  "treatment_type": "onboarding_copy",
  "public_leakage_risk": "low",
  "ground_truth_ref": "withheld/exp_001_result.json"
}
```

`ground_truth.jsonl`, withheld until scoring:

```json
{
  "experiment_id": "exp_001",
  "effect": 0.018,
  "standard_error": 0.006,
  "practical_null": 0.005,
  "label": "positive",
  "sample_size": 184221,
  "srm_passed": true,
  "guardrail_veto": false
}
```

`population_snapshot/`:

- user feature table or synthetic benchmark population
- feature dictionary
- allowed weights
- time window
- consent/privacy metadata

`sim_config.yaml`:

```yaml
model_version: "provider/model/version"
temperature: 0.7
agent_panel_size: 1000
paraphrases: 5
elicitation: "paired_delta_distribution"
persona_mode: "persona_plus_row"
calibration_model: "hierarchical_shrinkage_v1"
abstention_policy: "prompt_flip_or_out_of_regime"
random_seed: 20260617
```

### 6.2 Runner

For each experiment:

1. Build or load persona pack from training-period population only.
2. Render control and treatment artifacts into canonical state-diff.
3. Generate \(K=5\) paraphrases.
4. Sample \(N=1000\) agents with survey-style weights and soft persona membership.
5. For each agent and paraphrase, elicit distribution over positive/flat/negative metric effect.
6. Aggregate to raw sign probabilities and raw effect proxy.
7. Apply calibration model trained only on prior experiments.
8. Emit prediction JSON.
9. Hash prediction file before ground truth is loaded.

Prediction output:

```json
{
  "experiment_id": "exp_001",
  "predicted_p_positive": 0.64,
  "predicted_p_flat": 0.24,
  "predicted_p_negative": 0.12,
  "predicted_label": "positive",
  "raw_effect_proxy": 0.041,
  "calibrated_effect": 0.014,
  "interval_80": [0.002, 0.026],
  "confidence": 0.64,
  "abstained": false,
  "validated_regime": "text_and_onboarding",
  "prompt_sign_flip_rate": 0.0,
  "persona_lift_baseline_delta": 0.07,
  "model_version": "provider/model/version",
  "prediction_hash": "sha256:..."
}
```

### 6.3 Scorer

Compute:

- labels from ground truth using \(\delta_m\)
- balanced accuracy and MCC
- one-vs-rest Brier for each class
- ECE:
  - bin predictions by max class probability
  - compare confidence to empirical correctness
- Spearman and Kendall rank over calibrated effects
- precision@k:
  - k = 10%, 20%, and customer’s actual monthly experiment capacity
- regret:
  - compare value of selected top-k experiments with oracle top-k and baseline top-k
- tail-winner recall:
  - true winners in top decile of realized effect
  - fraction retained in top 50% of simulator ranking
- interval coverage
- modality-stratified metrics
- persona lift:
  - paired comparison against no-persona panel over the same experiments
  - bootstrap CI on metric deltas

All CIs use paired bootstrap over experiments, not over agents. Agent-level bootstrap is allowed for internal Monte Carlo error but cannot substitute for experiment-level uncertainty.

### 6.4 Null suite

Run the same harness on:

1. A/A artifacts: treatment identical to control.
2. Placebo diffs: irrelevant wording changes unrelated to metric.
3. Outcome-shuffled labels.
4. Treatment/control swapped cases: predicted sign should invert where the treatment is symmetric.
5. Paraphrase-only variants: sign should not change.
6. Future-leakage canary: include deliberately leaked post-experiment fact in one artifact and verify the leakage detector flags it.
7. No-persona base panel.
8. Random synthetic persona labels.

Pass criteria are the null-integrity thresholds in section 5.4.

### 6.5 Ablation matrix

Run the winning configuration against these variants:

- generic LLM, no personas, no rows
- persona-only
- row-only
- persona-plus-row
- hard persona assignment
- soft persona membership
- point elicitation
- distribution elicitation
- temperature 0
- sampled temperature
- single prompt
- paraphrase ensemble
- no calibration
- global calibration
- customer-specific calibration
- no product-state diff
- canonical state diff

Pre-register expected ordering:

\[
persona+row \ge row-only > persona-only \ge generic
\]

Cut any component that fails to improve held-out prediction or null integrity.

## 7. Dissents & open questions (named, per-seat where relevant)

S1 dissent: Do not call the output an ATE estimate unless it has been calibrated to randomized experiments on the same metric class. Before calibration, it is a prior over the ATE sign. S1 also objects to any “confidence score” not tied to a target estimand.

S2 dissent: LLM agents can be useful synthetic respondents, but individual digital twins remain scientifically weak. S2 expects useful signal in text, pricing-framing, and first-impression tasks, but much weaker signal in habit formation, social pressure, churn, and long-run retention. S2 also worries that stronger instruction-tuned models may be worse simulators because they are optimized for agreeable assistant behavior.

S3 dissent: Independent agent panels are not agent-based models in the computational social science sense. They miss network effects, congestion, marketplace balance, social proof, creator ecosystems, and repeated adaptation. S3 permits independent panels only when the estimand is individual first-exposure response.

S4 dissent: The phrase “simulated users” invites construct-validity errors. These are calibrated response instruments. The PM interview feature is valuable for hypothesis generation, but its narratives should not be treated as evidence unless their claims trace back to observed features or calibrated response priors.

S5 dissent: The proposed thresholds are necessary but not sufficient. A clever simulator can overfit public benchmarks. The real proof is a prospective registry or a blind customer archive with at least 150-200 experiments. S5 also insists that raw accuracy is banned because always-flat baselines can look excellent in mature experimentation programs.

Open questions:

1. What is the minimum viable public benchmark mix before first customer archive access?
2. How should the system price abstention versus wrong ranking in the PM workflow?
3. Should calibration be per metric, per surface, per company, or hierarchical across all three?
4. How much does persona narrative add beyond row-level behavioral conditioning?
5. Can LLM-generated rationales improve PM redesign decisions even when sign accuracy is only modest?
6. How should the simulator handle guardrail metrics where a positive primary effect is commercially unacceptable?
7. What is the correct estimand for product changes with network interference: direct effect, total effect, equilibrium effect, or cluster-level policy effect?

## 8. Claims ledger — a numbered list of falsifiable claims this council commits to

1. A simulator that does not specify metric, population, treatment, control, and horizon is not directionally correct in the causal sense.

2. For product experimentation, sign and rank prediction are more defensible product claims than uncalibrated lift magnitude.

3. The live randomized experiment remains the ground truth; simulation should be positioned as a calibrated prior, not a replacement.

4. Persona-only prompting will underperform persona-plus-row conditioning on held-out experiment prediction.

5. Soft persona membership will outperform hard assignment when user segments overlap materially.

6. Metric-keyed delta elicitation will outperform generic sentiment elicitation for predicting experiment outcomes.

7. Distribution elicitation will produce better calibrated sign probabilities than single deterministic LLM reactions.

8. A no-persona LLM panel is a mandatory baseline for proving that personas add predictive value.

9. Prompt paraphrase instability predicts lower out-of-sample accuracy and should reduce confidence or trigger abstention.

10. Raw effect magnitudes from LLM simulation will be too large on average and require shrinkage.

11. Text/copy/first-impression treatments will validate at higher rank correlation than networked, marketplace, or long-horizon behavioral treatments.

12. Independent-agent panels are invalid for strong network-effect estimands unless paired with an explicit interaction model.

13. A simulator can show high raw accuracy while being useless if the archive has a high flat/negative base rate.

14. Balanced accuracy, MCC, Brier score, ECE, rank correlation, decision regret, and tail-winner recall are all required to assess directional correctness.

15. A system that fails placebo/A/A null tests must not be trusted on real treatment predictions.

16. Historical backtests must be hash-committed before unblinding ground truth to be credible.

17. Fewer than 50 historical experiments cannot support a quantitative accuracy claim for a customer-specific simulator.

18. A 150-200 experiment blind archive is the minimum credible range for proving modest directional lift over baselines.

19. Tail-winner false negatives are more dangerous than ordinary sign errors for backlog triage.

20. The product should re-rank and redesign ideas, not automatically kill ideas, unless tail-winner recall has been validated.

21. Persona narratives are valuable for explanation and PM interviewing even if most predictive lift comes from row-level conditioning and calibration.

22. Segment response priors estimated from past experiments will improve simulation accuracy when treatment classes repeat.

23. Stated preference outputs must be calibrated to revealed behavior before they are used as product-decision evidence.

24. LLM sycophancy is a material bias for hypothesis validation and must be tested explicitly.

25. Model and prompt versions must be rerun on a golden benchmark set before any accuracy claim transfers to a new release.