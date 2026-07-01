# PART A — INDEPENDENT COUNCIL

## Setup

I convened five lenses and forced them to argue from only the two founder readouts:

- **Causal Inference / Transportability:** obsessed with identifiability, negative controls, and what can be inferred from the customer's data versus imported from elsewhere.
- **ML / Post-Training:** interested in whether a learned transferable simulator can reduce the customer data ask, but hostile to fine-tuning without verifiable rewards.
- **Uncertainty Quantification:** owns abstention, calibration, selective prediction, and the definition of "trustworthy."
- **Simulation Science:** separates real counterfactual simulation from role-play theater; cares about sufficient state, mechanisms, and validation.
- **Product / Systems:** optimizes time-to-first-value, buyer trust, onboarding friction, and what can be shipped without corrupting the claim.

The council accepts the sealed evidence as binding:

- LLM persona role-play as predictor is dead: 0.29 and worse on the exact counter-intuitive cases that matter.
- Words-only prediction is structurally magnitude-blind. Three frontier models express different priors, not better measurement.
- Model agreement is not reliability; on magnitude-driven flips it was confidently wrong.
- The survivor is grounded counterfactual computation: g-formula / mediation simulation over real user behavior, gated by a negative-control watchdog, with the LLM demoted to translator and narrator.
- The product cannot sell calibrated magnitudes. It can sell direction, confidence/abstain, contradiction catches, guardrail breadth, and a traceable reason.

## Council Fight

**Causal Inference:** "The question is not 'how do we use less data?' It is 'what estimand is identifiable at each data tier?' Tier 0 does not contain response magnitudes, so any verdict is a prior. Tier 1 may identify some composition effects if the aggregate table is literally the sufficient statistic for the mechanism. Tier 2 gives empirical calibration and in-span causal evidence. Tier 3 gives the real g-formula. Stop pretending these are interchangeable."

**ML / Post-Training:** "True, but if every customer needs tier 3 before seeing value, the product dies. The only way to reduce the ask is to move some learned response physics to Sidira's side: a library trained on Senu and historical experiment exhaust. Not an LLM role-play model; a supervised or RL-against-measured-outcomes model. It predicts only under a calibrated domain-of-applicability test."

**Uncertainty Quantification:** "A learned library is just a prior until it earns calibration. If it emits a sign on a non-identified case, it has recreated the disproven failure mode with a nicer interface. The product surface must be selective: high precision on a shrinking/expanding called set, not global accuracy. The key metric is coverage at bounded error, not raw accuracy."

**Simulation Science:** "The data tiers should be described in terms of the missing physical quantities. A proposed change has at least three needed objects: the target population, the change-to-mechanism shift, and the mechanism-to-outcome response surface. Persona aggregates provide only the first, crudely. Aggregate tables can sometimes provide the second or third in collapsed form. Past A/Bs provide observed shifts and responses for previous levers. Full feature stores provide all three."

**Product / Systems:** "The buyer needs an onboarding ladder. Tier 0 must do useful work without pretending to predict. Tier 1 must be a fixed export, not a bespoke analytics project. Tier 2 should be the recommended commercial entry because A/B exhaust already exists at serious experimentation orgs and lets us prove or disprove ourselves before asking for warehouse access. Tier 3 is the premium accuracy path, preferably warehouse-native to avoid row egress."

The fight resolves into a rule:

**Trustworthy accuracy with less customer data is possible only by reducing coverage, importing measured external evidence, or buying a missing measurement. It is not possible by asking an LLM/persona system to infer magnitudes from prose.**

## Architecture: Measurement-Led Selective Simulation

The architecture has six components. Each component exists to block a measured failure mode.

### 1. Translator, Not Oracle

The LLM translates a hypothesis into a structured causal/mechanism spec:

- primary metric and guardrails;
- hypothesized mediator(s);
- possible cannibalization/sibling metrics;
- affected segments;
- needed confounders;
- plausible negative controls;
- whether the change resembles a historically observed lever.

It may rank candidate mechanisms and ask clarifying questions. It never supplies the effect sign or a numeric mediator shift as a fact. If the system needs a magnitude and it is not measured, the output is abstain or "buy/collect this measurement."

### 2. Evidence Registry

For every hypothesis, Sidira builds an evidence card with the three decisive quantities:

- **Population:** who is exposed, with segment/effect-modifier distribution.
- **Mechanism shift:** how much the change moves the mediator or treatment lever.
- **Response surface:** how outcomes change as mediator/lever changes within segments.

Each quantity is marked as one of:

- customer-observed;
- customer-aggregate;
- historical A/B;
- external measured donor;
- Senu measured;
- prior only;
- missing.

Only the first five can support a verdict. "Prior only" can support triage or a data quote, not a called sign.

### 3. Predictor Stack

The predictor emits direction only, plus confidence/abstain:

- **Direct causal estimate:** when an equivalent or close lever varied historically.
- **Grounded g-formula mediation simulation:** when mediator and response surface are available in customer data.
- **Aggregate composition calculator:** when the sign is arithmetic over segment shares, mediator bins, or gross-vs-net tables.
- **Transported donor response surface:** only when donor evidence is measured, the target population can be reweighted, and sensitivity analysis preserves sign.
- **Senu micro-measurement path:** when a missing mediator shift can be measured externally and transported with explicit external-validity warnings.

No LLM verdict path exists. The "fallback to LLM when data abstains" should be weakly worded as narrative hypothesis, not a prediction product. If shown, it must be quarantined outside the predictor scorecard.

### 4. Watchdog and Identifiability Gate

The watchdog has two jobs:

- reject untrustworthy empirical estimates, especially hidden confounding;
- reject prior-dominated signs, even if the model is confident.

Minimum gates:

- negative-control/proximal guard where observational variation is used;
- overlap/support check for target segments;
- sign stability under plausible confounder adjustment;
- sign stability under mechanism-spec ambiguity;
- donor heterogeneity check for transported surfaces;
- flat-prior or weak-prior sensitivity check for library models.

The single negative-control guard is not promoted as solved; the readout says it failed a hard naturally-confounded benchmark. The roadmap should explicitly upgrade to proximal/double-negative-control methods before relying on naturally-confounded exhaust for high-trust calls.

### 5. Selective Calibration Layer

The product's formal claim should be:

> On the subset we call, our direction error is bounded/calibrated; otherwise we abstain.

This requires a ledger of sealed predictions and revealed outcomes. Calibration is per customer when enough customer outcomes exist, and otherwise global labels must be clearly lower trust.

Operationally:

- every call gets an evidence tier and reason for call/abstain;
- every abstain names the missing quantity;
- every future revealed A/B result updates the tier-specific calibration curve;
- every claimed skip should be audited by some randomized holdout policy, or else the product self-censors its failures.

No "certificate" language should ship until there are enough labels for the relevant bucket. Before that, call it triage.

### 6. Conversation Over Computed Records

The "talk to users" surface survives only after computation. The LLM receives a computed segment/user record:

- observed baseline behavior;
- modeled counterfactual change;
- outcome contribution;
- uncertainty and guardrail flags.

It narrates why that segment drove the result. If the user asks a new counterfactual, it routes back to the predictor stack. It does not improvise a new number.

## Data-Tier Frontier

The frontier is not "same product with less data." It is different deliverables with different decision rights.

### Tier 0: Persona Aggregates Only

**Available information:** segment names, weights, qualitative traits, maybe high-level usage summaries.

**Missing information:** response magnitudes, mediator distributions, treatment shifts, individual/segment response surfaces, confounding checks.

**Deliverable:**

- backlog structuring and mechanism translation;
- guardrail discovery: "metrics and segments you forgot";
- persona-weighted exposure map;
- failure-mode taxonomy;
- base-rate priors labeled as priors;
- disagreement/ambiguity siren;
- data quote: the exact table, A/B export, feature-store fields, or micro-study needed to call the hypothesis.

**Decision right:** no ship/kill prediction. At most "this is plausibly risky and needs measurement" or "this is likely a cheap test to run."

**Trust label:** unverified triage. If the UI shows an arrow at this tier, the product has re-imported the disproven persona path.

### Tier 1: Aggregate Stats / Segment Tables

**Minimum ask:** one frozen schema, not a custom analytics engagement. Example: segment x mediator-bin x outcome table, plus segment sizes, baseline metric rates, and guardrail rates. For A/B-like existing features, include arm or exposure aggregates if available.

**Available information:** some population composition, some mediator/outcome joint structure, maybe enough to compute mix shifts.

**Missing information:** row-level overlap, flexible confounder adjustment, individual heterogeneity, many interaction terms, and often the actual change-to-mediator shift for a novel design.

**Deliverable:**

- deterministic composition calls where the sign is arithmetic over the supplied table;
- Simpson/mix-flip detection;
- gross-vs-net and cannibalization arithmetic;
- segment-level direction breadth if the aggregate cells are aligned with the mechanism;
- sign bounds/sensitivity intervals when identification is partial;
- abstain with a precise missing field when the aggregate table is insufficient.

**Decision right:** limited direction calls for composition-dominated changes; otherwise prioritize measurement. This can be commercially useful, but coverage will probably be small.

**Trust label:** moderate for arithmetic calls traceable to customer tables; no trust for transported/learned signs unless sign survives sensitivity and donor ambiguity.

### Tier 2: Past A/B Exhaust

**Minimum ask:** platform export of past experiments, not slides: hypothesis/change description, dates, arms, exposure counts, primary and guardrail outcomes, segment cuts if available, launch decision, and ideally links to product surface/feature flags.

**Available information:** measured treatment effects, customer's own effect-size distribution, prior launch bias/winner's curse, in-span response patterns, calibration labels for Sidira.

**Deliverable:**

- portfolio audit: which historical launches were likely overcalled, underpowered, or guardrail-negative;
- sealed backtest: Sidira predicts held-out historical experiments from outcome-scrubbed specs, then reveals truth;
- customer-specific calibration curve and abstention threshold;
- in-span forward calls for mechanisms represented in the exhaust;
- recommended "test/skip/measure first" ranking for backlog;
- data-quality report showing what prevents tier-3 accuracy.

**Decision right:** credible triage and selective calls on mechanisms with historical support. This is the best commercial entry tier because it can earn trust before row-level access.

**Trust label:** high only after sealed backtest performance is acceptable. Without enough experiments, this remains triage, not certification.

### Tier 3: Full Event-Level Feature Store

**Minimum ask:** per-user behavioral feature store with covariates, mediator histories, outcomes, experiment exposures where available, guardrails, and negative controls. Prefer warehouse-native execution so rows need not leave the customer environment.

**Available information:** the substrate needed for the proven architecture: heterogeneity, response surfaces, mediator distributions, confounders, support diagnostics, and computed segment/user counterfactual records.

**Deliverable:**

- grounded g-formula mediation simulation;
- direct causal estimates where historical variation exists;
- full CONFIRMS / CONTRADICTS / CAN'T VALIDATE watchdog stamp;
- segment/guardrail breadth;
- "talk to users" over computed records;
- donor response surfaces if customer opts into pooled learning;
- maintained degradation benchmarks showing what lower tiers would have lost.

**Decision right:** highest-confidence direction and abstain decisions. Still no point-estimate sales claim; magnitude is backstage.

**Trust label:** highest, but still selective. Some hypotheses remain unidentifiable or unpredictable.

## How To Minimize The Customer Data Ask Without Lying

1. **Make Tier 2 the default first serious ask.** Past A/B exhaust is politically easier than a full feature store and produces an immediate audit/backtest artifact. It also tests whether Sidira deserves tier-3 trust.

2. **Offer Tier 1 as a fixed SQL contract.** Do not let aggregate onboarding become a disguised feature-store project. Freeze one or two schemas and publish what they can/cannot support.

3. **Run row-level models in the customer's warehouse.** This reduces data egress and security friction, though not the need for the data to exist. Market it precisely as "zero row egress," not "no data needed."

4. **Use Senu/factory data as measured donor evidence, not as a magic prior.** The data factory can reduce customer-specific measurement needs only if external validity is tested by bucket. It can shrink the abstain zone; it cannot erase it.

5. **Turn abstention into a conversion path.** Every abstain should say: "we cannot call this because X is missing; the cheapest unlock is Y; expected value is Z." This makes honesty useful rather than disappointing.

6. **Publish per-tier coverage, not just accuracy.** A model can look accurate by abstaining always or by predicting obvious wins. The real frontier is: among counter-intuitive/high-value cases, what fraction can each tier call with zero or bounded confident-wrong errors?

## Top-5 Experiment Agenda

### E1: Tier-1 Sufficiency / Composition Calculator

**Question:** Can a fixed aggregate schema support any trustworthy direction calls beyond trivial base rates?

**Method:** Convert AMBDOM/GNCE/Cookie Cats/Hillstrom-style cases into a pre-registered aggregate schema. Run a deterministic calculator for mix-flips, gross-vs-net, trade-down, and guardrail arithmetic. Compare against frontier LLM given the same tables and against chance.

**Pass:** zero confident-wrong on flip cases; non-trivial coverage on composition-driven cells; Cookie Cats sign recovered if the aggregate table genuinely contains the needed structure.

**Kill:** any confident-wrong on the counter-intuitive flip slice, or near-total abstention. Then Tier 1 is only structuring/data-quote, not verdict.

### E2: Tier-2 Historical Exhaust Backtest

**Question:** Does past A/B exhaust let Sidira earn a customer-specific trust certificate before feature-store access?

**Method:** For a real or synthetic customer exhaust set, time-split experiments. Hide outcomes. Give Sidira only outcome-scrubbed hypothesis/change descriptions plus allowed metadata. Predict direction/abstain under the proposed gate. Reveal outcomes.

**Pass:** called-set directional accuracy beats base-rate and PM hypothesis baselines with bounded confident-wrong rate; abstentions identify genuinely out-of-span mechanisms.

**Kill:** predictions track the customer's launch optimism or the LLM prior; confidence fails to calibrate; called set too small to matter.

### E3: Negative-Control Guard Upgrade

**Question:** Can the watchdog become trustworthy on naturally-confounded customer exhaust?

**Method:** Re-run the hard benchmark that broke the single negative-control guard. Implement proximal/double-negative-control variants and compare sign recovery, false contradiction rate, and abstention.

**Pass:** hard benchmark sign recovered or correctly abstained with fewer false trusts.

**Kill:** no improvement. Then naturally-confounded exhaust cannot support verdicts; only randomized A/B exhaust or full feature-store g-formula with stronger identification does.

### E4: Senu External-Validity Pilot

**Question:** Can purchased micro-measurements reduce the customer data ask by supplying missing change-to-mediator shifts?

**Method:** Choose cases where Tier 1/2 abstains solely because Δmediator is missing. Run a Senu matched-panel micro-study to measure that shift. Use customer or donor response surface, seal prediction, compare to held-out real outcome.

**Pass:** measured shifts transport directionally in at least one pre-registered bucket and improve coverage without confident-wrong.

**Kill:** panel shifts fail to transport. Then Senu is useful as a calibration/label factory, not as a per-hypothesis magnitude supplier.

### E5: Library Prior Quarantine / Donor Surface Audit

**Question:** Can external donor surfaces help without becoming the new LLM prior?

**Method:** Build a small measured library from public RCTs, Senu triples, and customer exhaust. For each target case, test sign stability across donor choices, weak-prior refits, and mechanism-tag ambiguity. Include same-tag opposite-sign cases.

**Pass:** donor evidence expands called coverage only when multiple measured donors agree under sensitivity; same-tag ambiguity triggers abstain.

**Kill:** library confidence is driven by taxonomy labels rather than measured surfaces; same-tag opposite-sign frequency is high; weak-prior refit changes sign often.

# PART B — CRITIQUE

## Where My Council Agrees With The Rival Council

The rival council gets the central result right: the data dependency cannot be dissolved. Magnitude information is not latent in persona prose; it must be measured, imported from measured donor evidence, or the system must abstain.

It also correctly separates the LLM roles. Translation and narration survive; verdict emission does not. The "words never pick the sign" rule is the most important design constraint in their synthesis and matches my council's conclusion.

The tier frontier is broadly right:

- Tier 0: no verdicts.
- Tier 1: maybe composition arithmetic, high abstain.
- Tier 2: best entry wedge via A/B exhaust and backtesting.
- Tier 3: proven g-formula/watchdog regime.

The rival council is also right that "data egress" and "data existence" are different problems. Warehouse-native computation lowers security friction but does not remove the requirement that events, mediators, and outcomes exist and are joinable.

Finally, I agree with the emphasis on a maintained frontier measurement program: degrade Tier 3 customers to Tier 1/2 views and continuously measure the accuracy/abstain loss. That is how this stops being philosophy.

## Where My Council Disagrees

### 1. The rival council overstates "validity is constant down the ladder."

Their phrase is attractive but too strong. If "validity" means "zero confident-wrong because we abstain whenever uncertain," then it is tautological. If it means comparable decision quality across tiers, it is false.

Tier 1 arithmetic calls and Tier 3 g-formula calls do not have the same validity object. Tier 1 may identify a sign for a narrow composition estimand; Tier 3 can model heterogeneous counterfactual response under richer support checks. A gate can control error on a called subset only after enough exchangeable labels exist. Before that, it is disciplined abstention, not guaranteed validity.

Better wording: **the policy target is constant precision/error control, but the evidentiary basis and the estimand narrow sharply down the ladder.** Do not let "validity constant, coverage varies" become the next overclaim.

### 2. Tier 1.5 / Senu-as-Δmediator supplier is under-validated and too productized.

The rival paper makes the purchased micro-study a named rung. That is plausible, but it is also the most dangerous part of the architecture. It assumes a panel-measured mechanism shift transports to the customer's users and product context. The founder readout explicitly warns that transfer is upside and external-validity risk.

This can easily re-import the failed persona path in quantitative clothing:

- LLM maps customer change to a generic Senu task.
- Senu respondents react in an artificial setting.
- The measured Δmediator is treated as customer magnitude.
- The product emits CONTRADICTS.

That is measured, but not necessarily measured on the target system. The difference matters. A Senu measurement should be called **external measured evidence**, not customer evidence, until bucket-level transport has been proven. I would not make Tier 1.5 a standard rung before E6 succeeds. I would make it an experimental add-on.

### 3. The "Abstention Ledger" risks guarantee theater at small n.

The rival council tries to avoid this with n-floors, but still leans heavily on conformal/PAC language. In this domain, labels are heterogeneous, mechanisms are non-exchangeable, and counter-intuitive cases are rare by construction. A 100-label marginal floor and 40-60 per bucket may still be weak if buckets are coarse or if Senu dominates the labels.

The falsification arm is good. The randomized audit clause is good. But the product should avoid "certificate" until it has customer-specific or very tightly bucketed evidence. Otherwise a hostile experimentation team will correctly ask: "exchangeable with what?"

The safer near-term product language is **sealed backtest + live audit rate**, not certificate.

### 4. The Backtest Ladder is commercially smart but may select the wrong buyers.

The rival council notes this dissent but underweights it. Customers with rich A/B exhaust often already have experimentation platforms, analysts, and skepticism. They may value audit, but the audit wedge competes with Eppo/Statsig/Optimizely analytics. Customers without exhaust feel the pain more acutely but cannot support the model.

This is not a reason to reject Tier 2. It is a reason to position Tier 2 as a **trust-earning diagnostic**, not the core product. The core product is "selective pre-test prediction after we prove we can calibrate on your history." If the audit becomes the wedge, Sidira risks becoming an experimentation analytics vendor with a research lab attached.

### 5. The rival council's transported donor surface path is underspecified.

They correctly reject cross-product transport as an identification claim, but then keep "transported donor surfaces over a moment-matched synthetic population" as a possible predictor. That can be valid only if the uncertainty set is brutal.

Open technical questions they do not resolve:

- What variables define shared effect modifiers across products?
- How is support/overlap checked from aggregate moments?
- How is donor selection protected from mechanism-tag verbal analogy?
- What happens when same mechanism tag has opposite signs by segment or baseline state?
- How many independent donor environments are needed before random-effects pooling is more than a prior?

Their R3 ensemble is a good defense, but it may collapse donor-surface coverage to almost zero. That is acceptable, but then the architecture should say donor transport is mostly an abstention test until proven otherwise.

### 6. The rival council is too generous to PFN / behavioral prior training.

They gate it properly, but the paper still gives it prestige by including CausalPFN / Do-PFN style spikes. My council would deprioritize this harder. The founder readouts already say the first honest build is tabular supervised response modeling on measured triples, and only later RL against outcomes. A PFN trained on synthetic task families risks learning the generator, not product behavior.

The research sequence should be:

1. deterministic calculator and g-formula baselines;
2. tabular supervised learned response model on measured triples;
3. only then amortized causal models or RL fine-tuning.

If the simple model cannot beat the grounded g-formula or extend coverage under calibration, no neural prior deserves budget.

### 7. The paper sometimes blurs "in-span forward verdicts" with novel product-change prediction.

Tier 2 can support forward calls for mechanisms represented in the exhaust. That is valuable, but it is not the original magical promise. A change "in span" of past A/Bs is closer to empirical generalization than novel simulation. The UI and sales language must distinguish:

- replay/audit of known lever families;
- interpolation within customer history;
- extrapolation using donor/Senu evidence;
- truly novel changes.

Those should not share one confidence scale without a visible evidence label.

### 8. The "data quote / EVOI" is excellent but under-specified.

Both councils like it. The rival council treats it as a product surface but not as a decision-theoretic object. This matters because a bad data quote becomes annoying homework.

The quote should compute:

- what missing quantity blocks the verdict;
- cheapest way to measure it;
- expected change in call probability;
- expected business value if call is unlocked;
- time/cost/privacy burden;
- whether the unlocked verdict would still be donor-limited or guard-limited.

Without this, "abstain with next step" degrades into a generic upsell.

## Specific Weak Claims / Failure-Mode Risks

**"Three independent judges and six independent red-teams converged..."** This is rhetorically weak. They are simulated agents instantiated from the same model family. The paper admits this later, but the abstract/intro should not lean on independence. The convergence is useful ideation, not evidence.

**"Tier 2 buys high trust."** Only after enough non-null, representative, outcome-scrubbed, non-survivorship-biased experiments exist. Many customer A/B archives are messy, selectively documented, and polluted by metric changes. The phrase should be "Tier 2 can earn high trust through sealed backtest."

**"One standardized cross-tab export."** Good product instinct, but the exact schema may be mechanism-family-specific. A single universal segment x mediator-bin x outcome table risks either being too weak to identify anything or too broad to be easy. Start with two or three frozen schemas by mechanism family.

**"Factory = one environment."** Correct as a warning, but incomplete. Senu may be many environments if sampling frames, task types, incentive structures, and outcome horizons differ in controlled ways. The right unit is not "factory" but exchangeability cluster. Treating all Senu as one environment is conservative; treating it as many without proof is inflated evidence.

**"Randomized audit clause is non-negotiable."** Scientifically yes. Commercially maybe fatal. The product needs a lower-friction mode: "advisory triage without certified skip claims," then graduate to audited savings when the customer is ready.

## What The Rival Council Is Missing

### 1. A crisp estimand taxonomy

The architecture should label what it predicts:

- primary metric sign;
- guardrail metric sign;
- net business objective sign;
- segment-specific sign;
- launch decision after metric weighting.

The founder evidence warns that production predicted a business lift and was wrong on the business metric. "Direction" is not enough. Direction of what? A tier may support guardrail breadth but not net business objective, or segment sign but not aggregate sign.

### 2. Explicit baseline competitors

The experiments should always compare against:

- PM stated hypothesis;
- always-flat / no-effect prior;
- historical base-rate by company;
- simple EB shrinkage on past A/Bs;
- deterministic calculator;
- frontier LLM with the same structured data.

Beating the disproven persona sim is no longer enough. The buyer's alternative is not a bad LLM; it is "run the A/B," "use PM judgment," or "use our experimentation platform."

### 3. Decision economics

The frontier should optimize expected saved experimentation cost at bounded regret, not abstract prediction accuracy. A 90% accurate call set containing only cheap obvious tests is less valuable than a 70% accurate/high-abstain system that catches a few expensive net-negatives with low false-kill risk.

Every tier should report:

- call coverage;
- false ship rate;
- false kill rate;
- abstain rate;
- expected test budget saved;
- expected regret from wrong skips/kills;
- audit cost.

### 4. Treatment rendering fidelity

The founder readout distinguishes crawled feature pack from feature store. The rival council mostly focuses on behavioral data. But product-change prediction also fails if the treatment is rendered differently in benchmark, Senu, and production. The translator must operate on a versioned treatment representation, not just text. Otherwise the mechanism spec becomes another leakage/prior channel.

### 5. Data quality and logging readiness

"Tier 1 aggregate export" and "Tier 3 feature store" assume instrumentation quality. The product needs an explicit preflight:

- are mediators logged?
- are guardrails linked?
- are exposure timestamps reliable?
- can users be joined across tables?
- are metrics stable across historical experiments?
- are segment cuts pre-treatment?

For many customers, the honest Tier 0/1 deliverable may be "you cannot use Sidira yet; here is the instrumentation plan."

## Five Most Consequential Disagreements To Debate

1. **Should Tier 1 be marketed as a verdict rung or only as a diagnostic until E1/E3 prove non-trivial coverage?** My council says diagnostic-first; the rival council gives it too much architectural prominence.

2. **Should Senu micro-studies be a named Tier 1.5 product before external-validity evidence exists?** My council says no: experimental add-on first, standard rung only after transport succeeds by bucket.

3. **What language is allowed for calibration: certificate, sealed backtest, or live-audited triage?** My council says avoid certificate until customer-specific or tightly bucketed exchangeability is proven.

4. **How hard should Sidira deprioritize learned priors/PFNs relative to simple measured-response models?** My council says much harder; learned priors are where the disproven failure mode will re-enter.

5. **Is the commercial wedge "audit past A/Bs" or "earn trust for selective future prediction"?** My council says the audit is the trust-earning wedge, not the company category. If Sidira becomes an audit tool, the strategic center drifts away from pre-test decision intelligence.

## Bottom Line

The rival council is directionally strong and much better than the failed persona-sim thesis. Its best rules should be adopted: no Tier 0 verdicts, words never pick signs, magnitudes must be measured/imported/purchased, and abstention must name the missing quantity.

The weak spots are over-certification, premature Senu productization, and residual faith that donor surfaces or learned priors can safely expand coverage before the information question is settled. The architecture should be more austere:

1. Tier 0 structures and quotes data.
2. Tier 1 earns only arithmetic/composition calls.
3. Tier 2 earns trust through sealed customer backtests.
4. Tier 3 is the real accuracy product.
5. Senu and learned models are coverage expanders only after sealed external-validity wins.

Anything else risks rebuilding the same failed oracle with more impressive machinery.
