# Persona Classifier & Benchmark Strategy — Research-Grade Validation

**Session:** persona-classifier-research · 2026-06-11
**Scope:** (1) validate the current persona building plan, (2) chart the classifier algorithm v2, (3) design a benchmark strategy credible to experimentation-mature buyers (Meta, Google, Amazon).
**Inputs:** full audit of `sidira-personas` pipeline code + `sidira-simulator` consumption path; literature review of LLM user-simulation (40+ sources); review of big-co experimentation culture and prior art; segmentation/clustering methodology review. Sources at bottom.

---

## 0. Executive summary

**The founder premise — "persona extraction/construction is the highest-leverage controllable component" — is half right, and the half that's wrong changes the roadmap.**

What the evidence says:

1. **Aggregate prediction works; individual twins don't.** GPT-4-simulated populations predict treatment effects of survey experiments at r = 0.85 (r = 0.90 on unpublished, contamination-proof studies) [Hewitt et al. 2024]. But individual-level digital twins correlate with their humans at only r ≈ 0.20 [Funhouse Mirrors mega-study, 2025, 19 pre-registered sub-studies]. **Sell population-level effect prediction, never "digital clones."** The phrase "digital clone of users" should be banned from the pitch deck — buyers who know this literature will read it as overclaiming.
2. **The persona *clustering* is not where prediction accuracy comes from.** Demographic/archetype persona prompts explain <10% of human response variance [Hu & Collier, ACL 2024] and barely beat a no-persona base LLM [Funhouse Mirrors]. What does move accuracy: **individual-level conditioning** (interviews/behavioral rows ≫ archetypes ≫ demographics: 86% vs 74% normalized accuracy in Park et al. 2024), **calibration against historical experiments** (fine-tuning on past A/B tests: 65% → 82–84% pairwise winner accuracy in LOLA, Marketing Science 2025), and **distribution elicitation methodology** (fixes mode collapse).
3. **Therefore the highest-leverage controllable component is the *conditioning + calibration + evaluation stack*, of which the persona pack is the scaffolding — not the engine.** Personas remain essential as the stratification, interpretation, and product-communication layer. But the conditioning signal each agent receives must become individual-level, and the system's accuracy claims must rest on a backtest harness, not on cluster quality metrics.
4. **The current `sidira-personas` pipeline is a competent scaffold with real defects** (detailed in §2): hard assignment discards the GMM's own posteriors, the stability metric is non-standard and likely flattering, the planned supervised classifier is mostly unnecessary, zero test coverage, and the JTBD/motivation fields personas assert are behavioral proxies the data can't certify — which the LLM will then faithfully simulate as if true.
5. **For the Meta/Google/Amazon sale, the benchmark IS the product.** Ron Kohavi (built ExP at Microsoft, ran experimentation at Airbnb) has publicly attacked this exact product category (Nov 2025): synthetic users "hide untestable assumptions inside the LLM." These buyers know that ~67–90% of their experiments don't win, that humans predict outcomes below chance (Kohavi's survey: 2.3/8 average), and that "always predict flat" gets 90% raw accuracy. The only thing that moves them is a blind, pre-committed, properly-nulled prediction track record scored against the right baselines (§4).

**Top 5 changes, ranked by leverage:**

| # | Change | Why |
|---|--------|-----|
| 1 | **Hierarchical conditioning**: persona narrative + individual feature deltas (real or GMM-sampled rows) per agent, replacing archetype-only prompts | Strongest replicated result in the field (Park 2024; Twin-2K 2025) |
| 2 | **End-to-end backtest harness on held-out real experiments as THE model-selection criterion** (and the sales artifact) | Without it, no claim survives buyer scrutiny; with it, every pipeline choice becomes tunable |
| 3 | **Treatment-effect-heterogeneity grounding**: causal forests/GATES on customers' historical experiments → validate segments stratify response → inject measured response priors into persona cards | Converts the simulator from zero-shot guesser to empirically-anchored mixture-of-experts |
| 4 | **Soft membership end-to-end**: GMM posteriors carried into sampling, assignment, and monitoring; kill the planned XGBoost classifier except for cold-start | Free (already computed), fixes variance collapse + the label-noise classifier problem |
| 5 | **Distribution elicitation + calibration layer in the simulator**: predict deltas vs control, unblind the design, elevated temperature / verbalized sampling / SSR-style rating elicitation, learned effect-size shrinkage | LLM effect sizes are direction-right magnitude-inflated [Hewitt]; temperature=0 single-sample is the documented mode-collapse recipe |

---

## 1. Premise check: what actually drives simulation accuracy

The founder's model: `accuracy = f(hypothesis quality, feature pack, personas, model)`. The literature supports a refinement:

```
accuracy = f( conditioning signal richness     ← individual data ≫ archetypes ≫ demographics
            , elicitation methodology          ← distributions ≫ single samples; deltas ≫ levels
            , calibration to historical data   ← fine-tune/shrink on past experiments: biggest single lever
            , treatment modality               ← text/copy r≈0.85 ··· UI/behavioral r≈0.25 (hard ceiling)
            , base model                       ← log-linear in size [SimBench]; instruction tuning HURTS diversity
            , hypothesis description quality   ← confirmed: unblinding the design fixes causal confounding [Gui & Toubia]
            )
```

Key numbers to internalize (full citations §6):

- **Hewitt et al. 2024**: 70 pre-registered survey experiments, 476 treatment effects. GPT-4 simulated respondents: **r = 0.85** predicted-vs-actual effects; **r = 0.90 on unpublished studies**; beats human forecasters. BUT on 250-treatment megastudies (tiny, noisy effects — the regime closest to mature product A/B): **r = 0.34**. Effect magnitudes systematically inflated; require regression calibration.
- **Park et al. 2024** (1,052 interview-based agents): normalized accuracy **86% (interview+survey) vs 74% (demographics-only)**; interview conditioning also reduced subgroup bias.
- **Funhouse Mirrors 2025** (Twin-2K, 19 pre-registered sub-studies, 164 outcomes): twins ≈ base-LLM-with-no-persona on most outcomes; individual-level **r ≈ 0.20**; five named distortions (insufficient individuation, stereotyping, representation bias, ideological bias, hyper-rationality).
- **LOLA 2025** (Upworthy, 17.7k headline tests): prompting picks the better headline at ~65% pairwise (near chance on multi-arm winner: 46.3%); **fine-tuned models: 82–84% pairwise**. The winning architecture was **simulation-as-prior inside Thompson sampling**, not simulation-as-replacement.
- **SimBench 2025** (20 datasets, 10.9M targets): best model **40.8/100**; instruction tuning improves consensus questions but *degrades* diverse-opinion questions — the alignment–simulation tradeoff.
- **Chen et al. 2025**: 276 published field experiments, 78% directional — but bimodal, collapsing on ethnicity/norms/ethics treatments, contamination not ruled out.
- **PyMC Labs × Colgate 2025** (57 real product surveys): with semantic-similarity elicitation (not direct Likert), ~90% of human test-retest reliability on product *ranking* — evidence that elicitation methodology, not persona quality, was their binding constraint.

**Implications for Sidira's premise:**
- "Crawling/feature pack is deterministic" — agreed, and Gui & Toubia adds: the *prompt must unblind the experimental design* (state what is randomized, what is held fixed) or the simulation confounds treatment with imagined covariates.
- "Hypothesis quality depends on user input" — true but product-fixable: a hypothesis-linting step (does it specify the metric? cohort? mechanism?) is cheap and the existing weakness taxonomy (wrong_metric, wrong_cohort…) is already most of it.
- "Personas are the most important thing we control" — **revised**: the conditioning stack (which includes personas), the calibration loop, and the evaluation harness are what you control. Persona *cluster quality* (ARI 0.67 vs 0.75) is weakly coupled to prediction accuracy; persona *conditioning depth* (archetype vs individual) is strongly coupled.

---

## 2. Audit of the current system

### 2.1 What is genuinely good (keep, and say so in the pitch)

- **7 fixed feature groups as a cross-company contract** — matches Multiple Factor Analysis logic, gives interpretable persona dimensions, and is the right portability abstraction (swap Layer A only).
- **Weights as a first-class output** (head_count / order / revenue), Hamilton largest-remainder stratified sampling, deterministic identity seeds, paired treatment/control sampling sharing seeds — this is *better experimental hygiene than most vendors in this space have*. The paired-sampling design is exactly right for delta prediction.
- **Identity seeds injecting per-agent variance** — this is a proto-version of upgrade #1 (hierarchical conditioning). The instinct was right; it needs to be data-grounded rather than drawn from hand-written pools.
- **Wilson CIs + bootstrap, degradation guards, reproducibility (seeded)** — the statistical hygiene is real.
- **LLM-first naming with generic fallback; removal of hard-coded DoorDash rules** — correct genericity call.
- **No-pretraining decision** (off-the-shelf LLMs + prompts) — correct per the evidence; the 8B specialized model should stay parked.

### 2.2 Defects in `sidira-personas` (from code audit)

Ordered by severity for downstream simulation:

1. **Hard assignment discards GMM posteriors** (`cluster.py: assign()` exports hard labels + max-prob only). With overlapping components (ARI 0.67 ⇒ boundaries are mush), ~30–40% of probability mass is misassigned *by construction*. Every simulated agent then inherits a falsely crisp identity. Fix is free: the model already computes posteriors.
2. **Persona narratives assert motivations the data can't certify.** The "Motivations/JTBD" and "Pain Points" columns are behavioral proxies (model scores, flags). The Layer-E prompt then asks the LLM to write a first-person JTBD — fabricating intent from behavior. The downstream agent will *faithfully roleplay the fabrication*. Fix: hedge proxy-derived claims in the card; longer-term, survey-fuse real attitudinal data (§3.6).
3. **Stability methodology is non-standard and likely flattering.** Bootstrap refits are compared against a single full-data baseline fit (not standard clusterboot), 20–30 iters, **global ARI only** — no per-cluster Jaccard. Hennig thresholds (≥0.85 highly stable, ≥0.75 valid, ≤0.5 dissolved) say 0.67 global = "real structure, unreliable boundaries," and it almost certainly hides 2–3 solid clusters and 2–3 artifacts. Also: fixed lifestage personas get hard-coded `stability=1.0` — misleading.
4. **Tandem-analysis bias + model mismatch.** PCA-then-GMM is the classic criticized "tandem" design (PCA can rotate cluster structure into discarded components); fixed 8-dim per group is an arbitrary block-weighting; one-hot categoricals z-scored into PCA + Gaussian components is a likelihood mismatch (BIC then adds components to fit non-Gaussianity, not real subpopulations). k_range [4,8] is arbitrary; no ICL beside BIC.
5. **No holdout anything**: all 8,823 users used for fit + profiling; no train/test; **zero unit tests in the repo** (`tests/__init__.py` is empty); planned supervised assignment classifier not implemented (good — see §3.5, mostly shouldn't be).
6. Smaller: baseline-leakage between fixed personas and the Active-only clustering baseline (inflated z-deltas); silent LLM-naming failures; `centroid` dict only contains top features (downstream consumers may assume full centroid); excluded groups (demographics, lifecycle) still appear in prompts as if persona-distinctive.

### 2.3 Defects in the simulator's consumption path

1. **`temperature=0` + single sample per agent** is the documented recipe for mode collapse / variance compression [Bisbee 2024; Meister 2024]. With 50 agents across 6 personas at temp 0, you get ~6 effective opinions with cosmetic identity-seed jitter. The CI machinery then computes confident intervals around a collapsed distribution — *precisely wrong*.
2. **Sentiment-heavy scoring** (`0.6 × sentiment + 0.4 × (1 − weakness_concentration)`): direct-rating sentiment from LLM agents carries positivity/elicitation artifacts; the formula's weights are arbitrary and untethered to any outcome. Should be replaced (or at least re-fit) once the backtest harness exists — the score should be *calibrated to predict something measurable*.
3. **Absolute-level prediction**: A/B mode already computes treatment−control deltas on paired seeds (good), but single-arm mode predicts levels, and no shrinkage/calibration layer exists anywhere. LLM effect magnitudes are systematically inflated [Hewitt]; ship a learned shrinkage layer from day one of the backtest era.
4. **No no-persona control arm.** Much of any persona panel's apparent signal is base-model behavior [Funhouse Mirrors]. Every accuracy claim must be reported as *delta over a no-persona base-LLM run* — also a cheap, differentiating honesty artifact.
5. **Identity seeds are hand-written pools** (6 gripes, 6 states, demo overrides) — fabricated variance. Should be drawn from the persona pack's actual per-cluster distributions (v1.1 behavioral_seeds does this — prioritize it) and eventually from sampled real rows.

---

## 3. Classifier algorithm plan v2

### 3.1 Architecture (revised 4 layers + new Layer F)

```
Layer A  Adapter (per-company)       — unchanged contract; add FAMD/PCAmix for categoricals
Layer B  Block weighting + reduction — MFA-style inverse-first-eigenvalue block weights
                                       (or block weights tuned against Layer-F backtest);
                                       prefer MCFA/mixture-of-factor-analyzers (joint
                                       reduction+clustering) over tandem PCA→GMM
Layer C  Persona model               — GMM/MCFA with BIC *and* ICL; merge components when
                                       BIC's k ≫ ICL's k; HDBSCAN/UMAP demoted to diagnostics;
                                       LCA variant when data is survey-heavy
Layer D  Calibration                 — posteriors carried end-to-end; per-cluster Jaccard
                                       (clusterboot-style, Hennig thresholds) + prediction
                                       strength (≥0.8) + null-data reference; weights as today
Layer E  Compile                     — persona card = narrative + archetypal direction (not
                                       centroid average) + hedged proxy-claims + MEASURED
                                       response priors (from Layer F) + per-cluster seed pools
Layer F  NEW: Response grounding +   — causal forests/GATES on customer's historical
         backtest harness              experiments; end-to-end backtest = the model-selection
                                       criterion for k, block weights, soft-vs-hard, prompt form
```

### 3.2 Conditioning: the hierarchical agent prompt (upgrade #1)

Per agent: **persona narrative (gestalt) + individual deltas (specifics)**.

- Draw user i = real anonymized row (with customer consent) or **synthetic row sampled from the fitted GMM** — the mixture is already a generative model; sampling it is free and privacy-clean.
- Persona z_i ~ Categorical(posterior_i) — soft sampling, so mixed users say "primarily a [P3] with strong [P6] tendencies" when posterior entropy is high.
- Render the row's deviations from the persona centroid above |z| ≈ 0.5 in natural language ("unlike most in this group, orders weekly and is on iOS").
- Identity-seed pools (age/tenure/state/gripe) come from per-cluster empirical distributions (v1.1), not hand-written lists.
- This preserves: the persona as the human-readable product artifact, the full joint feature distribution, and within-segment variance. Ablate archetype-only vs hierarchical vs persona-free row-sampling on the Layer-F harness; Park et al. predicts the ordering but measure it on Sidira's task.

### 3.3 Elicitation & calibration in the simulator

1. Predict **deltas vs the control arm** (paired seeds — already built) everywhere; single-arm "absolute score" mode becomes a delta vs the current-state feature pack.
2. **Unblind the design** in the prompt: explicitly state what changed and what is held fixed (price, quality, everything else equal) [Gui & Toubia].
3. **Elicit distributions, not point reactions**: elevated temperature; verbalized sampling (k responses with probabilities); SSR-style mapping of free-text reactions onto rating scales via embeddings instead of direct Likert. Replace "1 reaction per agent at temp 0" with "distribution per agent."
4. **Learned shrinkage layer**: regression from (predicted effect, realized effect) pairs accumulated in the backtest harness; report calibrated effects with intervals. Until data exists, apply a fixed conservative shrinkage prior anchored on Hewitt's documented inflation.
5. **Always run the no-persona control panel** and report persona-lift over it.
6. **Paraphrase ensemble**: run hypothesis description through 3–5 paraphrases; a prediction that flips under paraphrase is surfaced as low-confidence (formatting alone can swing LLM outputs massively [Sclar et al.]).

### 3.4 Response grounding (upgrade #3)

For each customer with an experiment archive (even 3–5 past experiments/promos):
- Fit causal forests / X-learner per experiment → per-user CATE estimates → **GATES per persona** (group average treatment effects, Chernozhukov et al. framework).
- **Validation gate**: personas must stratify historical treatment effects better than a demographic strawman (fraction of CATE variance explained by segment membership). If they don't, the segmentation carries no useful heterogeneity and must be revised — this is the test that makes "personas predict reactions" falsifiable.
- **Inject measured response priors into persona cards**: "this segment showed +9% lift to free-shipping promos, null response to UI redesigns." The agent now reasons from causal facts, not vibes.
- Optionally enrich the clustering basis with response-profile vectors (shrunken CATEs across experiments) once m ≥ 3–5 heterogeneous experiments exist — segmenting on *how users respond* is the most direct route to predicting A/B outcomes; the hybrid (behavioral base + response enrichment) hedges treatment-specificity.

### 3.5 New-user assignment ("the classifier")

- **Default: no new model.** Apply fitted preprocessing + projection + **GMM posterior** — Bayes-optimal under the model, calibrated by construction, soft. The originally-planned XGBoost-on-cluster-labels is solving a problem that mostly doesn't exist and adds label-noise (training a student on a noisy unsupervised teacher).
- **Cold-start exception** (new user with reduced features, e.g., first-30-days): supervised model is legitimate. Train on **posterior soft targets** (cross-entropy vs the posterior vector, not hard labels), calibrate (isotonic), add a **reject option** below max-posterior ≈ 0.5–0.6 → "mixed" users get posterior-sampled in simulation.
- **Drift monitoring**: (a) population drift — PSI per feature group + GMM average log-likelihood of incoming users as a single "does the model still explain users" alarm; (b) cluster drift — mixture-weight shifts, rising mean posterior entropy, falling per-cluster Jaccard on rolling refits. Re-cluster on sustained degradation, not calendar. On re-cluster, Hungarian-match old→new components so persona identities persist; report births/deaths/splits explicitly.

### 3.6 Data upgrades

1. **v1.1 behavioral_seeds (already roadmapped)** — promote: per-cluster empirical seed pools are the prerequisite for honest agent variance.
2. **Survey fusion** (the biggest *data* upgrade): 500–1,500-user attitude/motivation/price-sensitivity survey, fused into the behavioral file via mixture-model data fusion [Kamakura & Wedel 1997; Gilula et al. 2006]. This is what makes the JTBD field *true* instead of fabricated. Offer it as a premium onboarding step.
3. **Stratified sampling fix** (known): current 10K is 88% Active / 72% high-value — not a population sample. Persona weights computed on it misrepresent the population the simulator claims to mirror.
4. Round-2 feature enrichment (PSM scores, loyalty) as planned — but note: its value should now be measured on the Layer-F backtest, not on whether global ARI crosses 0.75.

### 3.7 Engineering hygiene (table stakes before any benchmark claim)

- Unit tests for adapter/encoder/cluster/calibrate (currently **zero**); holdout split; fix stability bootstrap to standard clusterboot procedure; log LLM-naming failures; full centroids in the pack; remove `stability=1.0` hardcode for fixed personas; persona pack schema v1.1 with per-cluster Jaccard + posterior entropy + response priors fields.

---

## 4. Benchmark strategy: selling to Meta / Google / Amazon

### 4.1 The adversarial context (do not pitch into this blind)

- **Their base rates**: Microsoft ~⅓ win/⅓ flat/⅓ negative; Bing 10–20%; Booking ~10%; Airbnb ~8%. ⇒ "always predict flat/loser" achieves 67–90% raw accuracy. Any accuracy number not benchmarked against this null is dead on arrival.
- **Their self-knowledge**: Kohavi's surveys show their own people predict outcomes below chance (avg 2.3/8 on 3-class). The opportunity: the bar to beat *human triage* is low and they know it quantitatively.
- **The direct attack**: Kohavi, Nov 2025, on synthetic-user A/B simulation: "you can't bypass the fundamental problem of causal inference; you're just hiding untestable assumptions inside the LLM." This post will be quoted in every procurement review. The only viable positioning: **"we beat your current prioritization prior and warm-start your experiments — we do not replace them."** LOLA (peer-reviewed, Marketing Science) is the citation that this architecture (simulation-as-prior + real traffic correction) beats both pure A/B and pure LLM.
- **Their trust rituals**: A/A tests, SRM checks, Twyman's law, OEC discipline, winner's-curse shrinkage. The benchmark artifacts below deliberately mirror these rituals — that mirroring is itself persuasive.
- **The modality cliff**: published evidence: text/copy treatments r ≈ 0.85; behavioral/field/non-text r ≈ 0.25–0.34. Most of a Meta/Amazon roadmap (ranking, latency, pricing, layout) is in the weak regime. **Publish the stratified honesty table** (accuracy by treatment modality, including "we are near-chance here" cells). A vendor claiming uniform 90% accuracy is read — correctly — as a fraud signal by this audience; published failure regimes are read as competence.
- **The fat-tails trap** [Azevedo et al., JPE 2020: top 2% of Bing ideas = 74.8% of gains]: if simulation triage filters out rare 10× winners, its expected value is negative even at high average accuracy. Must report **false-negative rate on tail winners** specifically, and recommend the product be used to *re-rank and warm-start*, never to kill ideas outright.

### 4.2 Scoring methodology (pre-commit to this; it does most of the persuasion)

| Metric | Against which null | Notes |
|---|---|---|
| 3-class directional (win/flat/lose) **balanced** accuracy / MCC | always-flat null; base-rate random | never raw accuracy |
| Brier + ECE on P(ship-positive) | climatology (predict base rate always) | report resolution vs calibration decomposition |
| Effect-size r (Pearson+Spearman) | archive empirical-Bayes prior; metadata GBM | report **raw and disattenuated** (split-half reliability of ground truth, Coey–Cunningham); evaluate vs shrunk estimates |
| Rank / precision@k on variant sets | random; averaged PM forecasts | the real commercial use is triage |
| **Decision regret** | actual launch decisions; oracle | value-weighted, the metric executives understand |
| Tail-winner false-negative rate | — | the Azevedo defense |
| Null-integrity suite | — | ≥50 placebo/paraphrase "experiments" must predict ≈0; the simulator's A/A test |
| Persona-lift | no-persona base-LLM panel | proves the persona layer earns its keep |

**Power discipline**: distinguishing 60% from 50% directional accuracy at 80% power needs ~150–200 experiments. Never claim from a 20-experiment pilot; sophisticated buyers will size this themselves and dismiss small-n claims.

### 4.3 The evidence ladder (phased artifacts)

**Tier 0 — now, no customer needed (4–8 weeks of work):**
1. **Upworthy confirmatory-set blind eval** — 22,743 held-out headline tests (exploratory 4,873 allowed for tuning). Persona-conditioned simulation vs: random, GPT-prompting (~65% pairwise / 46.3% multi-arm), LOLA's fine-tuned baselines (82–84% pairwise). Target: beat prompting decisively, approach fine-tuned, with calibrated margins. Honest caveat: text/CTR is the easy regime — say so.
2. **Hewitt archive + megastudies eval** (476 + 346 treatment effects, includes unpublished = contamination-controlled; Milkman gym/vaccine megastudies for the hard tiny-effect regime). Target: r ≥ 0.6 on field/behavioral effects with correct top-5 rank ordering beats both published LLM and human-forecaster anchors.
3. **Null-integrity certificate** — placebo/paraphrase suite, published. Cheap, disproportionately persuasive.
4. **Stratified honesty table** — accuracy by treatment modality across 1–3, failure cells included.
5. **End-to-end pipeline eval on Hillstrom + Criteo Uplift** — the only public datasets with individual user features AND measured treatment responses, hence the only public test of the full persona-construction → simulation stack (§6.1). Items 1–4 validate the simulation engine with synthetic demographic panels; item 5 validates the pipeline.

**Tier 1 — first design partner (the artifact that closes deals):**
6. **Buyer-archive blind backtest**: 150–200 of *their* historical experiments; Sidira receives specs/screenshots only; predictions (3-class + effect-size distribution) **hash-committed before unblinding**; contamination screen for publicly-leaked tests; scored per §4.2 against always-flat, their archive's empirical-Bayes prior, a metadata GBM, and averaged internal PM forecasts. Win condition: statistically significant lift over the best non-simulation baseline at n ≥ 150 + demonstrated non-filtering of top-decile winners. This doubles as the Layer-F calibration data.

**Tier 2 — standing credibility (moat):**
7. **Prospective escrow registry**: predictions filed before each experiment starts, third-party timestamped (Social Science Prediction Platform is the template), scored and published quarterly. The only design that fully answers contamination; no vendor in this space has one — first mover gets the category's only audited track record.
8. **Re-run the golden set on every model/prompt version** (documented LLM behavioral drift across snapshots) — version-pinned accuracy is part of the SLA.

### 4.4 The twelve questions they will ask (have written answers before the first meeting)

1. Why isn't this CRO folklore regurgitation? (→ no-persona control + null suite + archive-calibration)
2. Contamination? (→ escrow registry; unpublished-study evals; hash-commitment)
3. Beat always-flat? (→ balanced accuracy/MCC, climatology-Brier)
4. Beat a two-analyst-week empirical-Bayes prior + metadata GBM? (→ those are pre-registered baselines in the backtest)
5. Ground-truth noise / attenuation ceiling? (→ split-half reliability, raw + disattenuated r, shrunk-estimate targets)
6. Tail-winner false negatives? (→ reported metric + "re-rank, never kill" usage policy)
7. Non-text treatments? (→ stratified honesty table)
8. Your A/A test? (→ null-integrity certificate)
9. Calibration + abstention? (→ ECE, paraphrase-ensemble confidence, explicit abstain class)
10. Network effects / novelty effects / learning curves? (→ out of scope, stated plainly — simulation predicts first-exposure reaction, not equilibrium; surrogate-index methods are complementary)
11. OEC alignment? (→ simulate against the customer's OEC definition from the feature pack, not generic sentiment — this is a real product gap today, see §2.3.2)
12. Audited track record + what decision does this change at our traffic scale? (→ registry; positioning = triage which 20% of ideas to test first + LOLA-style warm-start priors, valuable even when traffic is free)

### 4.5 Positioning sentence

> "Sidira does not replace your experiments. It is a calibrated prior over your experiment backlog — built from your users' behavioral data, validated blind on your own archive, and honest about where it is near-chance. It re-ranks what you test first and warm-starts what you launch; your platform remains the ground truth that keeps it calibrated."

---

## 5. Roadmap integration (suggested resequencing)

| Phase | Item | Effort | Depends on |
|---|---|---|---|
| Now | §3.7 hygiene: tests, per-cluster Jaccard, posteriors in pack schema v1.1, holdout | S | — |
| Now | Simulator: temperature/distribution elicitation + delta-mode default + no-persona control arm + design unblinding | S–M | — |
| Now | **Tier-0 benchmarks** (Upworthy + Hewitt archive + null suite) — also forces the eval harness to exist | M | elicitation fixes |
| Next | Hierarchical conditioning (persona + sampled-row deltas); ablation archetype/hierarchical/persona-free on Tier-0 harness | M | v1.1 seeds |
| Next | Layer F: backtest harness as model-selection criterion; shrinkage calibration layer | M | Tier-0 harness |
| Customer 1 | GATES response grounding + response priors in cards; buyer-archive blind backtest (Tier 1) | M–L | customer archive |
| Customer 1 | Survey fusion premium onboarding | M | customer |
| Later | Prospective escrow registry (Tier 2); MCFA/LCA clustering upgrade if backtest says it pays | L | Tier 1 |

Notably deprioritized: the XGBoost assignment classifier (use posteriors), HDBSCAN productionization (diagnostic only), chasing global ARI 0.75 via feature enrichment (measure enrichment on the backtest instead), the specialized 8B model (stays parked).

---

## 6. Addendum (2026-06-12): benchmark input sourcing & the treatment-rendering gap

*Added after founder Q&A. Two questions: (a) where do the three simulation inputs — existing state, proposed change, personas+users — come from for public-experiment benchmarks? (b) did this analysis audit how the current-feature PRD and change PRD are ingested?*

### 6.1 Sourcing the three inputs per Tier-0 dataset

| Dataset | Proposed change | Existing state | Personas / users |
|---|---|---|---|
| **Upworthy** (22,743 confirmatory tests) | In the archive: every variant's headline text + image ID | Reconstructable once via Wayback Machine (upworthy.com 2013–15); headline tests need little more than site/story context | **None available.** Synthetic panel calibrated to the documented audience (Facebook-referred, skewed female, liberal-leaning US social-media users — archive paper + Pew 2013–14 social-media surveys). Demographic-grade only. |
| **Hewitt archive** (476 effects) | Published stimulus texts (treatmenteffect.app / OSF) | Survey frame — minimal by design | Published per-study sample demographics (often census-representative) → census-calibrated synthetic panels, the same move the source papers make |
| **Milkman megastudies** (~600 effects) | Full SMS/message texts in supplements | Gym membership / pharmacy messaging program context, published | Published participant demographics (24 Hour Fitness members; pharmacy patients) |
| **Hillstrom** (64K customers) | Two email campaigns + control, fully described | E-commerce email program | **Real individual RFM behavioral features per user** — run the actual sidira-personas pipeline on them |
| **Criteo Uplift** (13M users) | Ad exposure treatment | Ad serving context | **Real per-user feature vectors** (anonymized, 12 features) |

**The structural consequence:** Upworthy/Hewitt/Milkman have no user-level behavioral data, so Tier-0 artifacts 1–4 validate the **simulation engine** (elicitation, calibration, delta prediction, null integrity) under demographic-grade conditioning — a deliberate **lower bound**: "even with generic panels we score X; behavioral conditioning adds Y per Park et al." They cannot validate the persona-extraction pipeline. **Hillstrom and Criteo are the only public end-to-end tests**: cluster real user features → build personas → simulate the treatment → score against measured uplift, including the GATES-style check that our personas stratify the real treatment effect. Narrow regimes (email/ads, conversion outcomes) and Criteo's features are anonymized — but it is the one public proof the full stack can exist before a design partner does. Hence Tier-0 artifact #5. Full-stack validation on product-grade experiments remains a Tier-1 (customer-archive) deliverable; say so plainly when presenting Tier-0 numbers.

### 6.2 The treatment-rendering layer (gap acknowledged)

This analysis covers how the change description should be *used* — design unblinding (§3.3), paraphrase ensembles (§3.3), hypothesis linting (§1), OEC-aligned scoring (§4.4 Q11) — but did **not** audit how the crawler's feature pack and the user's change PRD are currently ingested, diffed, and rendered into agent context. That scoping followed the founder premise ("crawling is deterministic; hypothesis quality is user-dependent"), and the premise hid a real component: **treatment rendering** — (existing state, proposed change) → the exact text/image context an agent reads — is its own design surface with documented accuracy consequences (prompt-format sensitivity [Sclar]; the modality cliff §4.1). Two requirements fall out:

1. **Benchmark↔production format parity.** Public experiments must be rendered to agents in the *same* format customer PRDs are rendered, or Tier-0 scores will not transfer. The renderer is therefore shared infrastructure between the benchmark harness and the product, and should be built once, in the harness, first.
2. **The agent behavior spec** (the identified follow-up doc) must own the full agent-context assembly: feature pack + change PRD + persona narrative + individual row — including the diff representation (what changed, what is explicitly held fixed) and per-modality handling (copy vs UI screenshot vs pricing/mechanics).

---

## 7. Key sources

**LLM simulation accuracy:** Hewitt, Ashokkumar, Ghezae & Willer 2024 (70 experiments, r=0.85/0.90; treatmenteffect.app) · Park et al. 2024, arXiv:2411.10109 (1,052 interview agents, 85% of test-retest; interviews ≫ demographics) · Toubia et al. 2025, Twin-2K-500, arXiv:2505.17479 (public 2,058-person testbed) · Peng et al. 2025/26 "Funhouse Mirrors," arXiv:2509.19088 (individual r≈0.20; five distortions) · SimBench, arXiv:2510.17516 (40.8/100; alignment–simulation tradeoff) · Chen, Hu & Lu 2025, arXiv:2504.01167 (78% on 276 field experiments, bimodal) · Aher et al. ICML 2023 (Turing Experiments; hyper-accuracy) · Argyle et al. 2023, Political Analysis (silicon sampling) · Horton 2023, NBER w31122.
**Failure modes:** Bisbee et al. 2024, Political Analysis (variance compression, temporal drift) · Cheng et al. EMNLP 2023, CoMPosT (caricature) · Wang et al., Nature MI 2025 (out-group portrayals) · Hu & Collier ACL 2024 (<10% persona variance) · Sclar et al. (prompt-format swings) · Atari et al. 2023 (WEIRD, r=−0.70 cultural distance) · Santurkar et al. ICML 2023 (OpinionQA) · Gui & Toubia, arXiv:2312.15524 (causal confounding; unblinding fix).
**Elicitation/calibration:** Meister, Guestrin & Hashimoto 2024, arXiv:2411.05403 (distributional alignment) · Zhang et al., Verbalized Sampling, arXiv:2510.01171 · Maier et al. (PyMC Labs×Colgate), arXiv:2510.08338 (SSR, 90% of test-retest) · arXiv:2510.11408 (rectification with small human samples) · arXiv:2502.04262 (PPI for experiments) · arXiv:2502.17773 (effective sample size of an LLM).
**A/B prediction & experimentation culture:** Ye et al., LOLA, Marketing Science 2025, arXiv:2406.02611 (Upworthy; 65%→82–84%; simulation-as-prior) · Kohavi, Tang & Xu 2020, Trustworthy Online Controlled Experiments · Kohavi & Thomke HBR 2017 · Kohavi LinkedIn Nov 2025 (synthetic-user critique) · Azevedo et al., JPE 2020 (fat tails: 2% of ideas = 75% of gains) · Goldberg & Johndrow 2017 (eBay empirical-Bayes priors) · Coey & Cunningham WWW 2019 (experiment splitting, attenuation) · Athey et al. surrogate index, NBER w26463 · Netflix 200-test surrogate eval, arXiv:2311.11922 · DellaVigna & Pope, JPE 2018 + Social Science Prediction Platform · Upworthy Research Archive, Nature Sci Data 2021 (32,487 tests) · Liu & Cardoso, NeurIPS 2021 D&B (OCE dataset scarcity) · Milkman et al., Nature 2021 (megastudies) · Meta WW/WES arXiv:2004.05363 · Google RecSim NG arXiv:2103.08057 · AgentA/B arXiv:2504.09723 (Amazon-affiliated; closest prior art).
**Segmentation methodology:** Wedel & Kamakura 2000, Market Segmentation · Hennig 2007 CSDA (clusterboot; Jaccard thresholds) · Biernacki et al. 2000 (ICL) · Tibshirani & Walther 2005 (prediction strength) · von Luxburg 2010 (stability caveats) · Şenbabaoğlu et al. 2014 (consensus-clustering null) · Escofier & Pagès 1994 (MFA) · McLachlan et al. 2003 (mixtures of factor analyzers) · Baek et al. 2010 (MCFA) · Cutler & Breiman 1994 (archetypal analysis) · Chavent et al. (PCAmix/FAMD) · Kamakura & Wedel JMR 1997 + Gilula et al. JMR 2006 (data fusion) · Wager & Athey JASA 2018 + Athey et al. 2019 (causal forests/grf) · Künzel et al. PNAS 2019 (X-learner) · Chernozhukov et al. (GATES) · Northcutt et al. JAIR 2021 (label noise) · Niculescu-Mizil & Caruana ICML 2005 (calibration) · Grinsztajn et al. NeurIPS 2022 (tabular DL vs trees).
