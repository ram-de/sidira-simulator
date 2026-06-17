# Position Paper — Claude Council, Round 1

*Five seats convened: S1 Causal inference & experimentation · S2 LLM silicon-sampling / generative agents · S3 Computational social science / ABM · S4 Survey methodology, measurement & calibration · S5 ML evaluation & metrics. Dissent is surfaced, not smoothed.*

---

## 1. Thesis (≤200 words)

A behavioral simulator earns the label "directionally correct" only if it is **measured to be**, on a held-out backtest of the product's own historical experiments, a classifier whose *sign* and *rank* track real ATEs above explicit thresholds — not because it is built from LLM personas that "feel real." The unit of truth is the **decision**, not the prediction: the simulator's job is to triage a queue of candidate changes into {ship-to-experiment, kill, redesign}, and its value is the **decision regret** it saves versus the PM's current triage policy. We argue the only defensible architecture is a *calibrated comparator*: the LLM/persona ensemble produces a raw directional signal, and a thin, fitted calibration layer — trained on past experiments — maps that signal to a probability of positive sign and an honest confidence. The raw generative layer is a feature extractor, never the oracle. Absent a calibration backtest with ≥ ~50 historical experiments, the system must report **"uncalibrated"** and claim nothing quantitative. The dominant risk is not that LLMs cannot role-play — it is **leakage and overfitting to a tiny, biased ground-truth set**, plus the stated-vs-revealed gap. Directional correctness is achievable; *certified* directional correctness is hard, and the certification is the product.

---

## 2. Definition of directional correctness (the estimand + loss + decision)

### 2.1 The real-world target (the estimand)

For a candidate change *c* against the live product, the ground truth is the **ATE on a pre-registered primary metric** *Y* (e.g. D7 retention, activation rate, conversion), estimated from a real A/B test:

$$\tau_c \;=\; \mathbb{E}[Y \mid \text{treatment}=c] - \mathbb{E}[Y \mid \text{control}]$$

estimated by the experiment as $\hat\tau_c$ with standard error $\widehat{se}_c$. This is the Neyman/Rubin ATE (Imbens & Athey 2015; Rubin 1974). **The simulator does not need to estimate $\tau_c$.** It needs to estimate properties of its *sign and rank* that are decision-relevant.

Define the **true sign** with a dead-band around zero to avoid rewarding luck on null effects:

$$
s(c) =
\begin{cases}
+1 & \hat\tau_c > +\delta \text{ and stat-sig at } \alpha \\
-1 & \hat\tau_c < -\delta \text{ and stat-sig at } \alpha \\
0 & \text{otherwise (practically null)}
\end{cases}
$$

where $\delta$ is the **minimum practically-important effect** (set by the PM, e.g. +0.5pp retention). The dead-band is essential: a simulator that "correctly" calls the sign of a +0.01pp wobble has told you nothing.

### 2.2 What the simulator outputs

For change *c*, the simulator emits a **signed score** $g(c) \in \mathbb{R}$ (direction + intensity) and, after calibration, a **probability of helping** $\hat p_+(c) = \Pr(s(c)=+1 \mid g(c))$ and a symmetric $\hat p_-(c)$.

### 2.3 The three measurable definitions (S5 + S1)

Directional correctness is **not one number**. We commit to three, in priority order:

1. **Sign-match rate (SMR)** — on changes with $s(c)\neq 0$: $\Pr(\operatorname{sign} g(c) = s(c))$. The headline metric. A balanced-accuracy variant (averaging the +1 and −1 recall) guards against a base-rate-chasing simulator that just predicts the majority sign.
2. **Rank correlation (Kendall's $\tau_b$ / Spearman $\rho$)** — across a *set* of candidate changes, does the simulator order them by impact the way reality does? This is what actually drives the triage queue. Kendall's $\tau_b$ (handles ties) is preferred to Spearman for small *n*.
3. **Calibration of confidence** — does a stated $\hat p_+ = 0.8$ correspond to ~80% empirical positive sign? Measured by reliability diagram + Expected Calibration Error (ECE) and Brier score decomposition.

### 2.4 The loss the PM actually faces (decision theory — S1)

The PM runs a triage policy. The relevant loss is **asymmetric** and depends on capacity. Let experiment slots be scarce (the real constraint). The two errors are not equal:

- **False-green** (simulator says ship, reality says hurts/null): wastes an experiment slot *and* risks shipping a regression if the team is tempted to skip the test. Cost $L_{FG}$.
- **False-red** (simulator says kill, reality says it would have helped): a *missed winner* — invisible, never measured, and therefore the **most dangerous and least auditable** error. Cost $L_{FR}$.

We define **decision regret** against the PM's status-quo policy $\pi_0$ (e.g. "test everything in the backlog in PM-priority order"):

$$
\text{Regret} = \mathbb{E}\big[ U(\pi_0) - U(\pi_{\text{sim}}) \big]
$$

where $U$ is realized metric gain per experiment slot over a season. **The simulator only has value if $\text{Regret} < 0$** (it beats the status quo) at the operating point the PM chooses on the ROC/cost curve. S1 insists: report the **cost-weighted decision curve**, not just AUC, because the optimal threshold depends on $L_{FG}/L_{FR}$ and slot scarcity, which are the PM's to set.

### 2.5 Explicit non-goals

The simulator is **not** required to: estimate magnitude, be unbiased about magnitude, predict the winning variant's lift to within a CI, or model long-run equilibrium. Claiming any of these without evidence is the cardinal sin. Magnitude error is *expected and acceptable* (brief §1) **iff** sign and rank survive.

> **S4 dissent (recorded here, expanded in §7):** the estimand assumes a clean primary metric and a clean experiment. In practice ground-truth experiments are themselves noisy, peeked-at, and metric-shopped. The "truth" we calibrate to is itself an estimate with its own bias; treating $\hat\tau_c$ as ground truth without modeling experiment quality will *over*-state simulator error on genuinely-null changes.

---

## 3. The method

### 3.1 Design principle: the generator is a feature extractor, the calibrator is the oracle

**KNOWN.** LLM "silicon samples" can reproduce some population-conditional response patterns (Argyle et al. 2023, *Out of One, Many* — conditioning GPT-3 on demographic backstories recovered ANES-like marginal and conditional distributions; Horton 2023, *homo silicus* — LLMs reproduce qualitative directions of classic behavioral-economics experiments). Generative agents can produce believable individual and emergent behavior (Park et al. 2023, *Generative Agents*).

**KNOWN, equally.** These same samples exhibit **mode collapse / demographic flattening** (the model's "average person" leaks through every persona), **sycophancy** (responses bend toward what the prompt seems to want — Perez et al. 2022; Sharma et al. 2023), **position/label order effects**, and **stated-vs-revealed divergence** inherited from the text corpus. Silicon samples reproduce *what people say*, which is a biased proxy for *what people do* (the classic intention–behavior gap, Sheeran 2002; Ajzen).

**DEFENSIBLE INFERENCE.** Therefore the LLM should never be trusted to emit a calibrated probability or magnitude. Its reliable output is a **noisy, biased, but sign-informative signal**. The architecture must wrap it in a layer that has been *empirically calibrated against the product's own real experiments*. This is the load-bearing claim of the paper.

### 3.2 Architecture (four layers)

```
[A] Population construction  →  [B] Generative response  →  [C] Aggregation/effect extraction  →  [D] Calibration & decision
     (S3, S4)                     (S2)                         (S3, S5)                            (S1, S5)
```

**[A] Population construction (S3, S4).** Personas are *not* free-text vibes. Each persona is a **structured vector** of behaviorally-relevant covariates extracted from real user data — tenure, plan, usage frequency/intensity, feature-adoption history, jobs-to-be-done segment, device, prior churn signals. Calibrate the *joint* distribution of these covariates to the real userbase by **post-stratification / raking** (Groves et al., survey methodology) so the agent population matches real marginals *and* key interactions, not just one-at-a-time marginals. Heterogeneity is the asset: the simulator's edge over a single focus group is covering the tails (power users, at-risk users) at their true weight. Sample size per segment must be large enough that segment-level signal isn't noise (power analysis, §5.4).

**[B] Generative response (S2).** Each persona is shown (i) the *current* product behavior (the weekly snapshot — critical: the agent must react to a *change*, so it needs the baseline) and (ii) the proposed change (PRD + design). Elicitation is engineered against known biases:
- **De-sycophancy:** never reveal that the change is "the team's idea" or "new/improved." Present control and treatment as neutral, randomized, **blinded** alternatives (A vs B), randomize order, and ask for a choice/behavioral commitment, not an opinion. This directly imports the survey-methodology fix for acquiescence bias into prompt design.
- **Anti-mode-collapse:** sample at temperature with persona-conditioning strong enough to separate segments; *measure* the realized between-persona variance and reject runs where it collapses (§4.1). Consider ensembling across prompt framings and across models to break single-model idiosyncrasy.
- **Behavioral, not attitudinal, elicitation:** ask "what do you do next / do you keep using it / do you upgrade?" with a concrete scenario, not "do you like this?" Where possible, elicit a **revealed-preference proxy** (would you click, would you pay, would you return tomorrow) over a Likert attitude.

**[C] Aggregation / effect extraction (S3, S5).** Convert per-agent responses into a simulated effect $g(c)$: the **weighted** (post-strat weights) difference in the target-metric proxy between treatment and control arms across the agent population. Bootstrap over agents to get a simulated dispersion. Output both the population $g(c)$ and the **per-segment** $g_k(c)$ — segment-level directional disagreement is itself a diagnostic the PM wants ("power users love it, new users churn").

**[D] Calibration & decision (S1, S5).** Fit a monotone map (isotonic regression, or Platt/logistic if data is scarce) from $g(c)$ to $\hat p_+(c)$ **using historical experiments as training labels**. This layer:
- absorbs the systematic stated→revealed shrinkage (LLMs over-state enthusiasm → the calibrator learns to discount it);
- produces honest confidence;
- yields the **operating threshold** on the decision curve given the PM's $L_{FG}/L_{FR}$.

Without layer [D] fit on real data, the system is **uncalibrated** and may only output qualitative, hedged, per-segment narratives — never a confidence score.

### 3.3 Why this would be directionally correct (the grounded argument)

1. **Sign is easier than magnitude.** This is the whole bet. A biased-but-monotone signal — even one that systematically over- or under-states magnitude — preserves sign and rank after a *monotone* calibration. Statistically: directional correctness only requires the simulator's score to be **stochastically ordered** with the true effect (a rank condition), a far weaker requirement than unbiased point estimation. S5 and S1 agree this is the soundest part of the thesis.
2. **Calibration fixes bias, not variance.** The stated–revealed gap and LLM enthusiasm bias are largely *systematic* (a roughly consistent shift/scale), which calibration removes. What it cannot remove is *variance and sign-flips on near-null changes* — hence the dead-band $\delta$ and the explicit "abstain" region.
3. **Heterogeneity + interaction surfacing.** Real userbases are heterogeneous; a population simulator can catch segment-level sign reversals a single aggregate intuition misses. This is a genuine information gain (S3), *to the extent the population is calibrated to real joints.*

### 3.4 Honest scope of the method

- It predicts **first-order, individual-level reactions** to a presented change. It does **not** model **network/equilibrium/marketplace** effects (two-sided pricing, virality, congestion) — those require an interacting ABM and are out of scope for v1 (S3 flags this as a hard wall, §7).
- It is a **triage** instrument, explicitly upstream of experiments, never a replacement (brief §1, the firm constraint).

---

## 4. Failure modes & mitigations

| # | Failure mode | Seat | Why it breaks directional correctness | Mitigation (concrete) | Detectable by |
|---|---|---|---|---|---|
| F1 | **Sycophancy / demand effects** | S2 | Agents praise the "new" option → systematic false-green | Blinded A/B framing, randomized order, behavioral elicitation, never signal authorship | Order-swap symmetry test (§6); A-vs-A null test |
| F2 | **Mode collapse / demographic flattening** | S2, S3 | Personas converge to model's mean → heterogeneity and tail signal vanish → misses segment sign reversals | Measure realized between-persona variance vs. target; ensemble framings/models; reject collapsed runs | Between-persona variance ratio < threshold |
| F3 | **Stated vs. revealed preference** | S4 | Intentions over-state action; gap differs by metric (payment ≫ clicks) | Calibration layer [D] learns the shrinkage *per metric family*; prefer revealed-proxy elicitation | Calibration residuals; per-metric isotonic fit |
| F4 | **Missing / mis-weighted heterogeneity** | S3, S4 | Agent population doesn't match real joint distribution → aggregate effect biased | Raking/post-stratification to real joints; segment-level power check | Covariate-balance diagnostics vs. real userbase |
| F5 | **Interaction / network / equilibrium effects** | S3 | First-order sim misses marketplace, virality, cannibalization, novelty-decay | **Scope exclusion**: flag changes with network exposure; route them to experiment directly, low confidence | Change-type classifier flags "networked" PRDs |
| F6 | **Distribution / product shift** | S1, S5 | Calibration fit on old product/users degrades as product evolves (the *weekly snapshot* is the moving part) | Time-decayed calibration; rolling re-fit; monitor calibration drift; expire calibration after N weeks | Prospective calibration monitoring (PSI on $g$) |
| F7 | **Leakage in backtest** | S5 | LLM has seen the historical outcome (famous launches), or the persona-builder uses post-outcome data → inflated SMR | Strict temporal split; redact outcome-revealing context; test on *recent/internal* experiments the model can't know; counterfactual-label permutation test | Permutation/placebo test; known-vs-obscure split |
| F8 | **Tiny, biased ground-truth set** | S5, S1 | < ~50 past experiments, survivorship (only shipped winners measured) → SMR CI enormous, optimistic bias | Report SMR **with CIs**; include killed/null experiments; partial-pooling across products; refuse quantitative claims below sample floor | Sample-size gate; CI width report |
| F9 | **Metric/construct mismatch** | S4 | Agent's elicited proxy ≠ the experiment's primary metric → measuring the wrong thing | Pre-map each PRD to its primary metric; validate proxy↔metric construct link per family | Per-metric backtest stratification |
| F10 | **Overconfidence / fake precision** | S5, S1 | A crisp "78% confidence" implies calibration that doesn't exist | Confidence is a *function of the calibration backtest's coverage*; output "uncalibrated/low-coverage" when off-support | Coverage check of $g(c)$ vs. training support |
| F11 | **Prompt/format steering** | S2 | Effect size swings with prompt wording → non-robust | Prompt-perturbation ensemble; report sign-stability across perturbations as part of confidence | Prompt-perturbation variance |
| F12 | **Multiplicity / garden of forking paths** | S1, S5 | Many candidate changes → some "validated" by chance; tuning the calibrator on the test set | Pre-register metric & threshold; nested CV for calibration; Benjamini–Hochberg on backtest claims | Held-out, pre-registered eval only |

**Cross-cutting mitigation (S1+S5 consensus):** *the system must be allowed to abstain.* An honest triage tool outputs three classes — ship / kill / **insufficient-confidence-go-experiment** — and the abstain region is where near-null, off-support, networked, or high-perturbation-variance changes land. Forcing a binary call is the root of most failure modes above.

---

## 5. Validation protocol (metrics, backtest, thresholds)

### 5.1 The backtest design

**Ground truth = the product's own past experiments.** Assemble a registry of historical A/B tests: each with PRD/design artifacts *as they existed pre-test*, the primary metric, $\hat\tau_c$, $\widehat{se}_c$, decision taken, and — crucially — **the killed and null ones**, not just shipped winners (F8). For each, reconstruct the product snapshot *as of the test date* and run the simulator blind to the outcome.

- **Temporal split (mandatory):** calibrate layer [D] on experiments before date $T$; evaluate on experiments after $T$. No future leakage (F7).
- **Leakage scrub:** redact any text that reveals the real outcome; prefer recent/internal experiments the base model cannot have memorized.
- **Include nulls:** the dead-band $s(c)=0$ class is evaluated separately (can the sim *abstain* correctly on practically-null changes?).

### 5.2 Primary metrics & estimators

| Metric | Estimator | What it gates |
|---|---|---|
| **Sign-match rate (SMR)** | balanced accuracy on $s\neq0$ subset, with Wilson/bootstrap CI | headline directional correctness |
| **Rank correlation** | Kendall $\tau_b$ across candidate sets, bootstrap CI | triage ordering quality |
| **Calibration** | ECE + reliability diagram + Brier score & decomposition | honesty of confidence |
| **Abstention quality** | precision/recall of the "go-experiment" class; selective-prediction risk–coverage curve | does confidence track correctness |
| **Decision regret** | simulated season replay: realized metric gain/slot under $\pi_{sim}$ vs $\pi_0$, with bootstrap CI | the only metric that proves *value* |
| **Robustness** | sign-stability under prompt/order perturbation (% sign flips) | trustworthiness of a single call |

### 5.3 Go / no-go thresholds (proposed; S5 owns, S1 co-signs)

These are **operating thresholds, defended as defensible inference, not laws of nature.** They should be re-derived per product once enough data exists.

- **GO (deploy as triage aid):**
  - SMR (balanced) **≥ 0.70** with lower 90% CI bound **> 0.55** (i.e. beats a coin meaningfully), AND
  - Kendall $\tau_b$ **≥ 0.3** (lower CI > 0), AND
  - ECE **≤ 0.10**, AND
  - **Decision regret < 0** (beats status quo) at the PM's cost ratio, AND
  - A-vs-A null test shows no spurious directional signal (false-positive sign rate ≤ $\alpha$).
- **CONDITIONAL (qualitative-only / per-segment narratives, no confidence score):** SMR in [0.55, 0.70) or sample floor not met → ship as *interview/diagnostic* tool, suppress the numeric confidence.
- **NO-GO:** SMR lower CI ≤ 0.5, or fails A-vs-A, or decision regret ≥ 0. The simulator is not better than the PM's prior; do not ship a confidence number.

**Sample floor:** quantitative claims require **≥ ~50 outcome-labeled experiments** (with both signs represented); below that, report "uncalibrated." (Rationale in §5.4.)

### 5.4 Statistics of small-sample ground truth (S5, the hard truth)

The binding constraint is almost never the LLM — it is that **most products have tens, not thousands, of clean past experiments.** Consequences:
- SMR CI at $n=30$ is roughly $\pm0.17$ at 90% — you genuinely cannot distinguish SMR 0.65 from 0.82. *Report the CI every time;* a point SMR with no interval is malpractice.
- Use **partial pooling / hierarchical** estimation across products or change-types to borrow strength.
- Power the agent population so per-segment $g_k$ isn't noise: enough agents that segment effect SE ≪ $\delta$.
- **Pre-register** the metric, threshold, and split before looking (F12).

### 5.5 What the confidence score may and may not claim

- **May:** "Calibrated probability that the real ATE sign is positive, given this simulator's backtested reliability on N=… past experiments of this change-type." It is a statement about *the simulator's historical hit rate*, conditioned on coverage.
- **May not:** claim to predict magnitude; claim validity for change-types absent from the backtest (off-support → must say so); claim to substitute for the experiment; imply more precision than the backtest CI supports.
- The confidence score is **a property of the calibration set, not of the persona's eloquence.** A vivid agent interview with no calibration behind it is qualitative color, and must be labeled as such.

---

## 6. The test harness (concrete, runnable spec)

A gating harness, runnable in CI before any "directionally correct" claim ships. Six tests; each emits a pass/fail and a statistic.

### Inputs
- `experiments.jsonl`: one row per historical experiment — `{id, date, prd_text, design_ref, snapshot_ref, primary_metric, tau_hat, se, n_users, decision, outcome_sign∈{+1,0,-1}}`. Must include nulls and kills.
- `personas.parquet`: structured persona vectors + post-strat weights, with `covariate_marginals_real` for the balance check.
- `sim_runner(prd, snapshot, personas, framing_seed) → {g, g_per_segment, between_persona_var, per_agent_responses}`.

### Outputs
- `report.json`: every metric in §5.2 with CIs; per-test pass/fail; overall GO/CONDITIONAL/NO-GO.
- `reliability.png`, `risk_coverage.png`, `decision_curve.png`.

### Test 1 — A-vs-A null (placebo) test  *(guards F1, F10)*
Feed the simulator two identical arms (control = treatment). **Expected:** $g \approx 0$; fraction of runs producing a |sign| call beyond dead-band ≤ $\alpha$ (e.g. 5%). **Stat:** one-sample test that mean $|g|$ over the null distribution is within noise; report false-directional rate. **Fail** if it manufactures signal.

### Test 2 — Order/framing symmetry  *(guards F1, F11)*
Run each experiment with arm labels swapped and ≥5 prompt-framing perturbations. **Stat:** sign-flip rate across perturbations; demand-effect bias = mean($g_{A=new}$ − $g_{B=new}$). **Pass** if sign-flip rate < 10% and demand-effect bias CI contains 0.

### Test 3 — Population calibration (covariate balance)  *(guards F4)*
Compare simulated population's covariate joint distribution to `covariate_marginals_real`. **Stat:** standardized mean differences per covariate + a joint PSI/χ². **Pass** if all |SMD| < 0.1 after raking.

### Test 4 — Heterogeneity / anti-collapse  *(guards F2)*
**Stat:** ratio of realized between-persona response variance to a target (estimated from real segment-level metric dispersion, or a held-out human panel if available). **Pass** if ratio ≥ 0.5 (sim retains at least half of real heterogeneity) and no segment is degenerate.

### Test 5 — Directional backtest (the core)  *(guards F3, F6, F7, F8, F9, F12)*
Temporal split. Fit calibrator on train, evaluate on test. **Stats:** balanced SMR + Wilson CI; Kendall $\tau_b$ + bootstrap CI; ECE + reliability curve; Brier. **Leakage controls:** (a) **label-permutation test** — shuffle outcome signs, re-run whole pipeline; SMR must collapse to ~0.5 (if it doesn't, you have leakage or a degenerate metric); (b) **known-vs-obscure split** — SMR on famous/memorizable launches must not exceed SMR on obscure internal ones by more than noise. **Pass** if §5.3 GO thresholds met AND permutation SMR ∈ [0.4,0.6].

### Test 6 — Decision-regret replay  *(guards the value claim, S1)*
Replay the test-period experiment queue under (i) status-quo policy $\pi_0$ and (ii) simulator-triage policy $\pi_{sim}$ at the PM's cost ratio $L_{FG}/L_{FR}$ and slot budget. **Stat:** realized metric gain per slot, $\Delta = U(\pi_{sim}) - U(\pi_0)$, bootstrap CI. Also emit the full **decision curve** over thresholds. **Pass** if $\Delta$'s lower CI > 0 at the chosen operating point.

### Gate logic
```
GO          := Test1 ∧ Test2 ∧ Test3 ∧ Test4 ∧ Test5(GO) ∧ Test6
CONDITIONAL := Test1 ∧ Test2 ∧ Test4 ∧ Test5(0.55≤SMR<0.70 ∨ n<floor)   # qualitative-only, no confidence score
NO-GO       := ¬Test1 ∨ ¬Test5(min) ∨ Test6.ΔlowerCI ≤ 0
```
The harness **refuses to emit a numeric confidence score** unless GO. CONDITIONAL ships interviews + per-segment narratives only.

---

## 7. Dissents & open questions (named, per-seat)

- **S2 (LLM silicon-sampling) dissents on the population-construction premise.** Argyle-style conditioning recovered *attitudinal distributions on topics in the training corpus*. There is little evidence LLMs recover **product-specific behavioral** responses to a *novel UI change* the model never saw. S2's position: the generative layer's sign signal may be near-random for genuinely novel features, and the calibrator would then just be fitting noise to a tiny label set. **Open question:** is there *any* product where the raw $g(c)$ beats chance pre-calibration? If not, the architecture is calibration fitting nothing. S2 wants Test 5's permutation result watched like a hawk.

- **S4 (survey methodology) dissents on the ground truth.** Calibrating to $\hat\tau_c$ treats noisy, possibly metric-shopped experiments as truth. Many "null" experiments were under-powered, not truly null; many "winners" were peeked. S4 argues we are calibrating a biased instrument against another biased instrument and may certify directional correctness that is partly shared bias. **Mitigation request:** weight backtest experiments by their own power/quality; model experiment SE explicitly in the loss.

- **S3 (computational social science) dissents on scope.** The brief's setting includes a *userbase* — which has interactions, social proof, network effects, and novelty/habituation dynamics. A first-order independent-agent simulator is structurally blind to these, and many of the *highest-stakes* product changes (referrals, social features, pricing) are exactly the networked ones. S3 will not co-sign "directionally correct" as a blanket claim — only "directionally correct **for first-order, non-networked changes**." Pushing further needs an interacting ABM with its own (much harder) calibration.

- **S1 (causal inference) holds the line on decision-first evaluation but flags an estimand subtlety.** The simulator predicts a *response to a presented artifact*; the experiment measures a response to a *shipped, polished, possibly-iterated implementation*. These are different treatments (the PRD ≠ the eventual build). Sign can flip in implementation. S1's open question: how much of backtest error is simulator error vs. PRD-to-ship drift? Recommend logging implementation-fidelity as a covariate.

- **S5 (ML eval) dissents on feasibility timeline, not on method.** The whole protocol presumes ≥~50 clean, sign-balanced, low-leakage historical experiments. Most products do not have this. S5's blunt view: for the majority of Sidira's customers the honest answer in Round 1 is **CONDITIONAL at best** — a qualitative interview tool whose numeric confidence is *unearned* until the backtest exists. Selling a confidence score before the calibration set exists is the single biggest integrity risk in the product.

**Shared open questions:**
1. Cold-start: what does the system claim on day 1, before any backtest? (Council consensus: "uncalibrated, qualitative-only.")
2. Transfer: can a calibrator fit on Product A's experiments inform Product B? (Hierarchical pooling — untested.)
3. Negative controls: where do we get *killed* experiments' counterfactual outcomes, since they were never run? (We mostly can't — survivorship is structural.)

---

## 8. Claims ledger

> Numbered, falsifiable, one line each. The other council marks **AGREE / DISAGREE / REFINE**.

1. Directional correctness must be **measured on a held-out backtest of the product's own historical experiments**, not asserted from persona realism.
2. The estimand is the **sign and rank of the real ATE on a pre-registered primary metric**, with a **dead-band $\delta$** = minimum practically-important effect so near-null changes are not scored.
3. The simulator's value must be judged by **decision regret vs. the PM's status-quo triage policy**, not by prediction accuracy alone; it has value only if regret < 0.
4. The decision loss is **asymmetric**; the **false-red (missed-winner) error is the most dangerous because it is unobservable**, and thresholds must be set on a cost-weighted decision curve, not AUC.
5. The LLM/persona layer is a **biased, sign-informative feature extractor**; it must **never directly emit a calibrated probability or magnitude**.
6. A **fitted calibration layer (isotonic/Platt) trained on real past experiments** is mandatory to map the raw signal to honest confidence and to absorb the stated→revealed shrinkage.
7. **Sign and rank are recoverable even when magnitude is badly biased**, because directional correctness needs only stochastic ordering (a monotone-calibration condition), not unbiased estimation.
8. Elicitation must be **blinded, order-randomized, and behavioral** (choice/action, not Likert attitude) to suppress sycophancy and demand effects.
9. The agent population must be **calibrated to the real userbase's joint covariate distribution by raking/post-stratification**, and must pass a covariate-balance check (|SMD| < 0.1).
10. **Realized between-persona variance must be measured and floored** (≥ ~0.5 of target heterogeneity); mode-collapsed runs are rejected.
11. The method is **valid only for first-order, non-networked changes**; network/marketplace/equilibrium effects are out of scope and such changes route straight to experiment.
12. **Leakage is the dominant threat to backtest validity**; a label-permutation test must collapse SMR to ~0.5, and famous-vs-obscure SMR gaps must be within noise.
13. **Quantitative claims require ≥ ~50 sign-balanced, outcome-labeled historical experiments** (including kills/nulls); below this floor the system reports "uncalibrated" and suppresses the confidence score.
14. **Every directional metric must be reported with a confidence interval**; a point SMR without an interval is invalid given small-sample ground truth.
15. Proposed **GO thresholds**: balanced SMR ≥ 0.70 (90% CI lower bound > 0.55), Kendall $\tau_b$ ≥ 0.3, ECE ≤ 0.10, decision regret < 0, and a passed A-vs-A null test.
16. The system **must be allowed to abstain** ("insufficient confidence — go experiment"); forcing a binary ship/kill call is itself a primary failure mode.
17. The **confidence score is a property of the calibration backtest's coverage**, not of persona eloquence; off-support change-types must be flagged as uncalibrated.
18. The simulator is a **pre-experiment triage instrument, never a replacement** for live experimentation.
19. **An A-vs-A placebo test is a mandatory gate**: a simulator that manufactures directional signal from identical arms is disqualified regardless of backtest SMR.
20. **Ground truth is itself noisy**; backtest experiments should be weighted by their statistical power/quality, because calibrating to under-powered "nulls" injects shared bias.
