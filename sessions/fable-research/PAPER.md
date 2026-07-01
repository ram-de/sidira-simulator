# The Data-Efficiency Frontier for Trustworthy Pre-Test Prediction

### Restructuring — not dissolving — the grounding dependency in product-experiment simulation

**Sidira Research · 2026-07-01 · council draft v1.1**
*Produced by a six-lens research council (causal transportability · outcome-grounded training · calibration/uncertainty · minimal-data-ask design · simulation science · systems pragmatics), each proposal adversarially red-teamed against the campaign's sealed negative results, scored by a three-judge panel, and synthesized by a chair. Full provenance: `council-dossiers.md`, `council-synthesis.md` (this directory).*

> **v1.1 changelog (same day):** the paper was debated to convergence against an independent codex council (`codex-council-r1.md` → `fable-response-r1.md` → `codex-council-r2.md`; joint statement `DEBATE_CONCLUSION.md`), and two of §7's experiments were RUN under seal with the opposing council auditing the raw artifacts: **E1 = PASS** (the tier-1 composition verdict rung exists: calculator 24/24 incl. 12/12 misleading-narrative flips; real Cookie Cats signs and magnitudes recovered from tier-1 moments alone) and **E2 = KILL** (86.7% same-tag opposite-sign ambiguity on real cases — mechanism tags are permanently banned from selecting signs, including "soft" tier-0 family priors). Key amendments now binding: "validity is constant down the ladder" is retired in favor of *"the error-control policy target is constant; the evidentiary basis, estimand, and coverage narrow sharply down the ladder"*; every call must carry an **estimand label** (direction *of what*: primary / guardrail / net-business / segment) and an **evidence class** (replay / interpolation / arithmetic-aggregate / transported-or-purchased / novel-abstain); tier 1.5 ships only as a priced measurement quote (experimental) until E6 passes per bucket; "certificate" is reserved for per-customer sealed-backtest-earned status; learned models are sequenced calculator → tabular-supervised-on-measured-triples → PFN → RL, each stage gated on beating the previous under seal on **decision economics** (false-ship/false-kill at useful coverage against PM-hypothesis, flat-prior, base-rate, EB-shrinkage, calculator, and LLM-with-same-tables baselines).

---

## Abstract

Predicting the outcome of a product change before running the A/B test would save experimentation cost — if the prediction were trustworthy. Our sealed benchmark campaign established two hard constraints. First, the cheap architecture — persona data seeding LLM agents that role-play users — is not merely unproven but *disproven*: 0.29 directional accuracy (below chance) on counter-intuitive cases, with a model-specific structural prior (llama never predicts decline; Opus 4.8 shows mirror-image pessimism; gpt-5.5 scores 0.00 on magnitude-driven flips) and a shared failure we term **magnitude-blindness**: when a change helps one way and hurts another, the sign of the net effect is decided by quantities that are physically absent from words. Second, the architecture that works — a grounded mediation simulation (g-formula) gated by an empirical watchdog, measured at 12/12 on magnitude-flip cells where every frontier LLM is at or below chance — requires the customer's per-user behavioral feature store: a data ask that dominates onboarding friction and time-to-first-value.

This paper asks whether that data dependency can be reduced without surrendering trustworthiness. The council's answer is that it cannot be dissolved — the flip-deciding magnitude information does not exist in personas, prose, or priors — but it can be **restructured** along four axes: (1) move the expensive knowledge (response surfaces, effect-size priors) to the vendor's side via a mechanism-tagged effect library and, eventually, a data factory; (2) shrink the customer's ask to artifacts exportable in an afternoon (past A/B logs, one standardized aggregate schema) and eliminate row-level egress with warehouse-native computation; (3) convert missing magnitudes for novel changes into **purchasable measurements** (priced micro-studies) rather than hallucinated priors; and (4) gate every rung with a computed, auditable abstention boundary so that the error-control policy target is constant down the ladder while the evidentiary basis, estimand, and coverage narrow honestly with the data. We specify the unified architecture, state the data-efficiency frontier as a falsifiable table, and pre-register a seven-experiment agenda (the first four at zero cost) with explicit kill criteria — including the experiments that would kill this paper's own central claims.

---

## 1. Introduction

Online controlled experiments are the ground truth of product decision-making and also its bottleneck: each test costs weeks of traffic, engineering time, and opportunity cost, and most organizations can run only a small fraction of their hypothesis backlog. A system that could predict test outcomes — even just the *direction* on the primary and guardrail metrics, with honest confidence — would let teams skip tests whose outcome is knowable and spend their traffic on the ones that are not.

The seductive architecture is user simulation by large language models: build personas from customer data, instantiate LLM agents, show them the change, and read off the outcome. It is cheap, demo-friendly, and requires little from the customer beyond persona-grade aggregates. It is also wrong, in a way we can now quantify (§2). The architecture that survives our campaign — grounded causal computation with the LLM demoted to translator and narrator — works precisely because it consumes numeric, per-user behavioral data. Its accuracy is real and its data appetite is the problem: the feature-store ask arrives before the customer trusts the product enough to grant it.

This is the tension this paper addresses. We frame it as a **data-efficiency frontier** question: over a ladder of customer-data tiers —

- **Tier 0** — persona aggregates already on hand;
- **Tier 1** — aggregate statistics (one standardized segment × mediator-bin × outcome export);
- **Tier 2** — historical A/B exhaust (per-experiment summary logs);
- **Tier 3** — the per-user, event-level feature store —

what verdict quality is *honestly* deliverable at each rung, by what method, and what moves value toward the cheap rungs? The framing matters because it converts an architectural argument into a measurable object: a coverage-at-guaranteed-error curve per tier, which can be published, audited, and improved.

**Contributions.** (i) A synthesis of six independently derived and adversarially red-teamed research programs into one architecture with four separated roles — predictor, calibrator, guard, converser — and three verdict-admission rules that provably exclude the failure modes we measured (§5). (ii) The data-efficiency frontier stated as a falsifiable table rather than a marketing claim (§6). (iii) A pre-registered experimental agenda with kill criteria, four of whose seven experiments run at zero cost on assets already in the repository (§7). (iv) A negative catalogue: nine designs the council examined and rejected, with the evidence each collides with (§8). We also record unresolved dissents (§9) honestly, because two of them are decisions evidence cannot make.

---

## 2. The evidence base

All results below are from sealed, pre-registered runs (predictions fingerprinted before scoring). They function as hard constraints on the design space: any proposed architecture must explain, mechanically, why it does not re-run into each of them.

**N1 — Persona role-play is below chance as a predictor.** LLM agents seeded with persona packs who "become" users and produce the outcome scored **0.29** directional accuracy on counter-intuitive cases. The persona machinery actively hurts relative to a one-line comparison prompt.

**N2 — No words-only method reaches past chance.** Naive/comparative one-shot prompting ≈ 0.50; decomposition, selective-prediction prompting, and reference-class analogy all null.

**N3 — Ensembling makes it worse.** A council-of-priors (multiple LLM perspectives + router) degraded accuracy. Where two frontier models *agree* on magnitude-driven flip cases they are **0/12** correct: agreement is the confidently-wrong mode, because the models' priors are correlated. A three-model heterogeneous-bias panel flags 100% of flips — usable as an **abstain siren**, never as a predictor.

**N4 — Model strength does not fix it.** llama exhibits structural optimism (never predicts a decline); Opus 4.8 the mirror image (predicted DOWN 39× on the same ambiguous prose); gpt-5.5 scored 0.00 on flips. The durable phenomenon is **magnitude-blindness**: on cases where the net sign depends on *how much* two opposing effects move, the deciding information is not present in the text, so no textual predictor can beat chance *by construction*. Model upgrades improve translation quality (Opus 0.68 vs llama 0.42 on narration/translation), never the verdict.

**N5 — Production confirms it.** In blind tests with a design partner, the deployed persona-sim engine tracked intuition, not truth: it predicted a business lift every time and was wrong on the business metric of every counter-intuitive case.

**N6 — A predictability ceiling exists.** The Fragile Families mass collaboration (Salganik et al. 2020) found the entire ML arsenal converging to trivial baselines on individual life outcomes: some behavior is unpredictable in principle, and the binding constraint is data, not method. Our LLM-at-chance results carry the same signature.

**What survived.** (S1) **Grounded mediation simulation**: a g-formula over the customer's per-user feature store scored **1.00 (12/12)** on magnitude-flip cells versus 0.00 for the LLM, and recovered the counter-intuitive Cookie Cats negative on real data — right sign, magnitude off ~40%, hence the product ships *sign + confidence*, never point estimates. (S2) **The empirical watchdog**: causal estimate + negative-control guard stamping CONFIRMS / CONTRADICTS / CAN'T-VALIDATE; the single-NC guard is a lead that failed one hard naturally-confounded benchmark, with proximal double-negative-control as the named repair route (E5). (S3) **The LLM as translator and narrator**: English/Figma → mechanism spec (mediator, cannibalization sibling, negative controls, confounders, estimand); computed records → an interrogable "why." (S4) The **Bridgewater lesson** (Thinking Machines 2026): the verifiable labeled dataset was the moat and the RL recipe downstream of it — motivating a data factory (Senu) that manufactures (population, change, measured-outcome) triples, over-sampling the counter-intuitive failure-mode taxonomy.

---

## 3. Problem statement

Let a hypothesis h describe a product change. The customer wants the sign of the treatment effect Δ on a primary metric and on guardrail metrics, per segment, with a trustworthy confidence — or an honest abstention. The surviving estimator family (direct causal estimate where the lever varied historically; g-formula mediation where the mechanism is observed) consumes:

1. per-user covariates X (who the users are),
2. mediator observations M (the lever the change moves),
3. an estimate of the change→mediator shift ΔM,
4. a response surface E[Y | M, X] fit to real behavior,
5. negative controls and confounder sets for the guard.

Items (2), (4), (5) traditionally require tier-3 data *in the target customer*. The research question: **which of these objects can be relocated (to a vendor-side library), compressed (to aggregate sufficient statistics), purchased (as a micro-study measurement), or bounded (partial identification) — and what verdict quality survives each substitution?**

Two clarifications sharpen the problem. First, the magnitude-blindness result (N4) is an *information* statement, not a modeling statement: for flip cases, no reweighting of tier-0 information can produce the answer, because the answer is not a function of tier-0 information. Any tier-0 "verdict" is therefore a prior in disguise — which is N5 re-armed. Second, much of the practical friction is **data egress** (privacy, DPAs, security review), which is distinct from **data existence** (whether the events are logged and joined at all). Methods that fix egress without touching existence are valuable and must be labeled honestly as such (§9, dissent 6).

---

## 4. Why the cheap path cannot work (and what personas are actually for)

The persona-seeded agent architecture fails for a reason deeper than prompt quality. A persona pack is a distributional summary of *who the users are*: P(z) over segments and traits. The outcome of a two-sided change is decided by *response magnitudes* — how much each opposing mechanism moves per segment. The persona pack does not contain those magnitudes; the LLM therefore fills them from its prior; the prior is model-specific and structurally biased (N4); and ensembling correlated priors compounds rather than cancels the error (N3).

But this diagnosis contains the persona pack's correct role, and the council was unanimous on it: **P(z) is the transport weight.** In every surviving design, persona aggregates enter as the covariate/effect-modifier distribution that reweights *measured* response surfaces to the target population — the exact mathematical object transport formulas require from the target side (Pearl & Bareinboim 2014; Bareinboim & Pearl 2016). Numbers flow *into* persona-weighted aggregates; persona prompts never flow into imagined numbers. Remove the persona pack and you lose reweighting precision; remove the measured surfaces and the system abstains rather than guesses. This inverts the disproven information flow while preserving the asset customers already provide.

---

## 5. The unified architecture

One system, four separated roles, one ladder. The skeleton is a staged trust ladder ("Backtest Ladder"); the verdict-admission policy is an ensemble gate stack; the trust surface is a conformal abstention layer ("Abstention Ledger"); the deployment mode is zero-egress warehouse-native computation; the magnitude supply chain is the data factory sold as a measurement SKU.

### 5.1 Three verdict-admission rules

These rules are the architecture's core safety property; each traces to a measured failure it excludes.

**R1 — Magnitudes are data-derived or purchased, never LLM-declared.** The change→mediator shift ΔM for a novel change must come from: observed natural variation; the customer's own experiment exhaust; a validated donor response surface; or a priced micro-study that *measures* it (≈₹40/respondent via the Senu factory). If none exists, the mandatory output is ABSTAIN. Three red-teams independently found the same smuggling route — magnitude priors re-entering through mechanism-spec "estimates," taxonomy retrieval, or trained network priors — and R1 closes all of them. *(Excludes N4/N5.)*

**R2 — Words never pick the sign.** LLM outputs (taxonomy classification, donor-surface selection, mechanism tags) are treated as an *uncertainty axis*, not a decision: if any plausible taxonomy cell or donor assignment flips the sign, the system abstains automatically. *(Excludes N1/N2; keeps the translator role that survived.)*

**R3 — Verdicts require full-product sign stability.** A called sign must survive a joint ensemble over: the dependence structure of the reconstructed population (copula family) × the donor-surface posterior (multiple donors per taxonomy cell) × the plausible ΔM range × the taxonomy-cell assignment. Confident-wrong becomes a design property to be engineered to zero, not a hope. Additionally, any verdict whose sign does not survive a **flat-prior refit** is demoted to abstain: if the prior is the verdict, the verdict is an abstention ("prior quarantine"). *(Excludes N3's correlated-agreement mode; cross-environment agreement tightens bounds only because environments are statistically independent — and the factory counts as ONE environment.)*

### 5.2 The four roles

**Predictor — grounded computation only.** The only verdict-emitting engine at any tier is the validated causal stack: direct estimates where the lever varied; per-customer g-formula where mechanism is observed (the measured 1.00 regime); *transported donor surfaces over a moment-matched synthetic population* where the customer lacks per-user data — always under R1–R3.

**Calibrator — the customer's own exhaust plus a zero-centered library prior.** Tier-2 A/B logs do four jobs: (a) a **winner's-curse / empirical-Bayes portfolio audit** (Lee & Shen 2018; Azevedo et al. 2020; Coey & Cunningham 2019) — the day-one deliverable that reverses past launch decisions using pure computation, zero prediction risk, and functions contractually as the data grant; (b) a **sealed per-customer backtest** — time-masked, outcome-scrubbed hypothesis descriptions → predictions → revealed truth — producing a per-customer trust certificate before any forward call; (c) a customer-specific effect-size prior, fat-tailed and near-zero-centered (the empirical distribution of experiment effects is exactly this; it structurally kills always-predicts-lift); (d) causal moment conditions pinning response slopes for levers within the exhaust's span. Cross-customer and factory knowledge enter as a hierarchical random-effects prior with reported between-source heterogeneity τ² — quarantined by R3's flat-prior test.

**Guard — the Abstention Ledger.** Every verdict passes the negative-control watchdog (proximal double-NC as the repair route, E5), then a Learn-then-Test / conformal-risk-control abstain gate (Angelopoulos et al.) calibrated on watchdog-surviving labels, Mondrian-stratified per failure-mode bucket. The word "certificate" is reserved for PAC-style coverage above pre-registered n-floors (≈100 marginal / 40–60 per bucket of trustworthy labels); below the floor the identical gate ships as "triage — no guarantee," with the n-to-certificate countdown displayed as the onboarding hook. Production identifiability is secured by a **randomized-audit clause**: the customer runs a random ε ≈ 10–15% of certified skips as cheap directional holdouts; pricing applies to the (1−ε) saved fraction; no audit clause → no certificates, only triage. The three-model disagreement panel survives *only* as an abstain siren (N3's polarity: disagreement raises caution; agreement never certifies).

**Converser — the LLM, translator and narrator, never the verdict.** Unchanged from S3, with one routing rule: explanation of an existing computed result → the agent answers, grounded; a *new* counterfactual → back to the g-formula. Per-person both-arm views remain labeled **calibrated fiction** — reliable in aggregate, fictional per individual (N6 honored at every tier).

**Deployment (orthogonal).** The full row-level estimator ships as a zero-egress warehouse-native app (Snowflake Native App / BigQuery routine): models fit in the customer's warehouse; only verdicts, stamps, and aggregate tables leave. This wins the privacy/DPA battle without the sufficiency loss of moment-only exports — and is marketed as *privacy-preserving*, never as *no feature store needed* (§9, dissent 6).

### 5.3 The ladder, rung by rung

**Tier 0 — persona aggregates (minutes to first artifact).** No verdicts, ever — the measured accuracy is chance-or-worse and the council refuses to fake otherwise. Ships: mechanism-spec structuring of the whole backlog; failure-mode taxonomy classification; a guardrail-breadth checklist (the metrics the PM forgot to worry about); library base rates *labeled prior-not-prediction*; the abstain siren; and the **data quote** — for each hypothesis, the exact tier-1 table, tier-2 export, or priced micro-study that would unlock a verdict, ranked by expected value of information. Tier 0's product is time-to-first-artifact and a priced path upward.

**Tier 1 — one standardized cross-tab export (an afternoon of SQL; zero egress).** A single frozen schema: segment × mediator-bin × outcome, plus segment moments — versioned like an API, so the ask is one query, not a negotiation. Two engines: (a) the **deterministic composition calculator** — Simpson/mix-flip and gross-vs-net arithmetic over the tables, wired to the translator (~50 lines; if E1 confirms sufficiency this is the tier-1 wedge); (b) the **transported g-formula** over a moment-matched synthetic population (iterative proportional fitting + copula ensemble), gated by R3, with Manski-style **sign sets** where identification fails. Stated expectation: tier-1 verdict coverage is small and concentrated on composition-driven flips; mediator-driven flips abstain unless a measurement is purchased. The abstain rate at this tier is a headline number to be measured (E3), not hidden.

**Tier 1.5 — tier 1 plus a purchased Δmediator micro-study.** The factory's load-bearing SKU: a matched-panel micro-study *measures* the change→mediator shift that decides a flip; the g-formula runs with a measured ΔM; external validity of the panel→customer transfer is flagged and itself tested (E6). The missing number is bought, not sampled from a prior.

**Tier 2 — past A/B exhaust (a day; the recommended entry rung).** Everything above, plus the audit wedge, the sealed backtest certificate, customer-calibrated conformal thresholds, and in-span forward verdicts. Pre-registered minimum-exhaust bar (≈30 resolvable non-null experiments) for any certificate; platform export required rather than a curated deck (survivorship); the translator sees outcome-scrubbed descriptions only (leakage).

**Tier 3 — the per-user feature store (the premium rung, not the entry toll).** The proven regime: full per-customer g-formula with heterogeneity/CATE, proximal double-NC for naturally-confounded exhaust, surrogate-index estimation *only here* (where long-run linkage exists to validate surrogacy; Athey et al.), and talk-to-users over computed records. Tier-3 customers additionally serve two system roles: **donor** (fitted response surfaces pooled with opt-in — never rows) and **instrument** — their data is degraded to tier-1/2 views and re-scored, permanently, publishing the per-rung accuracy/abstain delta. This standing measurement is how the frontier table (§6) becomes a maintained empirical object rather than an argument.

---

## 6. The data-efficiency frontier

The error-control policy target is constant down the ladder — the gate bounds directional error on the called set or refuses the verdict — while the evidentiary basis and the estimand narrow sharply with the data (v1.1 wording; below the label floor a called subset is disciplined abstention, not guaranteed validity). What each rung buys is **coverage of the sellable counter-intuitive slice**. Coverage values below are targets to be measured by E3/E4 and the tier-3 instrument program; the council explicitly repudiates invented percentages.

| Tier (customer ask) | Honestly deliverable | Verdict type | Trust | Expected abstain on flips | Method |
|---|---|---|---|---|---|
| **0** — persona pack on hand (minutes) | Backlog structuring; taxonomy; guardrail-breadth checklist; base rates *labeled prior*; flip-siren; **priced EVOI data quote** | None (triage ordering only) | Unverified, labeled | ~100% by design | Translator + taxonomy + disagreement siren + EVOI ranker; personas as P(z) only |
| **1** — one standardized cross-tab (afternoon; zero egress; *presupposes events exist in-warehouse*) | Composition-driven flip calls (mix-flip, gross-vs-net, trade-down); prior-free sign sets; per-segment direction breadth | Direction, R3-gated; sign-sets otherwise | Moderate; every call traces to the customer's own tables or abstains | High — mediator-driven flips abstain unless measured | Composition calculator (if E1 passes) + transported g-formula + Manski sets |
| **1.5** — tier 1 + purchased Δmediator micro-study *(v1.1: EXPERIMENTAL — visible only as a priced measurement quote; no verdicts until E6 passes per bucket; evidence labeled external-measured, never customer)* | Mediator-driven flip calls where measured shift + donor/own surface pins the net | Direction + CONTRADICTS, gated | Moderate-high; the deciding number is *measured*; transfer tested | Falls case-by-case as measurements are bought | g-formula with measured ΔM; NC guard; R3 |
| **2** — A/B log CSV (a day; ≈30 non-null experiments for a certificate) | **Winner's-curse portfolio audit** (day-one ROI); sealed backtest certificate; calibrated thresholds; in-span forward verdicts; which-tests-to-run-next | Direction + CONFIRMS/CONTRADICTS in-span; certified skips above n-floor **with audit clause** | High, *quantified per customer* (calibration curve + e-process) | Moderate in-span; high on out-of-span novel flips | EB shrinkage/audit; sealed backtest; conformal gate; exhaust as moments |
| **3** — feature store (zero-egress in-warehouse; the real cost is modeling work) | The proven regime: 1.00 on magnitude flips; Cookie-Cats-class negatives; full heterogeneity; proximal NC; surrogate index; talk-to-users | Full CONFIRMS/CONTRADICTS/CAN'T-VALIDATE incl. flip slice | Highest; watchdog-gated; per-person views labeled calibrated fiction | Lowest, never zero (the ceiling is priced, not denied) | Per-customer g-formula + watchdog + Ledger; customer doubles as donor + instrument |

**One sentence:** below tier 3, a confident call on the counter-intuitive slice is bought either with the customer's own exhaust span or with a purchased measurement — never with a prior.

---

## 7. Pre-registered experimental agenda

Sealed, fingerprinted before scoring, in the existing runstore/LEDGER discipline. E1–E4 need zero customer data and zero spend and are runnable this month on assets already in the repository.

**E1 — Arithmetic-sufficiency test** *(2 days, ₹0 — run first).* **[RUN 2026-07-01: PASS — calculator 12/12 flips + 12/12 one-sign, zero abstain; real Cookie Cats both signs from tier-1 moments (−0.8201/−0.5905pp = row-level truth); Opus-with-tables 23/24 with one silent arithmetic slip. The tier-1 branch fires: the calculator is the wedge. Scope per the codex audit: this proves extraction from sufficient observed tables, not inference of unobserved shifts from prose. `research/fable-frontier-experiments/E1_RESULTS.md`.]** Translator → mechanism spec → deterministic composition calculator on tier-1 standardized tables; scored on composition-driven AMBDOM flip cells + aggregate-collapsed Cookie Cats; baselines = a frontier LLM *given the same tables* (not the words-only 0.00) and chance. **Branch:** calculator wins → it is the tier-1 wedge and any learned model must later beat it. Calculator fails → the aggregate information isn't there; tier-1 verdict ambitions die cheaply and the ladder's middle rung is 1.5/2.

**E2 — Same-tag, opposite-sign library audit** *(this week, ₹0).* **[RUN 2026-07-01: KILL — 86.7% ambiguity (13/15 in-group real cases; Wilson 95% [62.1%, 96.3%]; threshold 30%). Mechanism tags never pick signs, including soft tier-0 family priors. `research/fable-frontier-experiments/E2_RESULTS.md`.]** Across every case on disk, tag mechanisms with the existing translator; measure how often identical tags carry opposite-signed true effects. **Kill:** ambiguity above a pre-registered threshold (e.g. >30%) permanently bans mechanism-tag retrieval from selecting a sign — taxonomy stays an ensemble axis. (The cheapest test of whether retrieval re-imports magnitude-blindness.)

**E3 — Moment-degradation battery** *(2 weeks, ₹0).* Per dataset (12 AMBDOM flip cells, GNCE, real Cookie Cats, Hillstrom, the 10 one-sign sets): degrade to the exact tier-1 schema (authored blind, fingerprinted first); rebuild population via IPF + copula ensemble; transport surfaces cross-dataset where possible; run the unchanged g-formula under the full R3 ensemble, including an adversarial wrong-donor arm and a realistic arm where ΔM is *not* leaked from source rows. **Pre-registered pass:** ≥9/12 flip cells correct-and-confident with **zero confident-wrong**; Cookie Cats negative recovered from moments alone; zero confident-wrong on one-sign sets; the tier-1 abstain rate reported as a headline number. **Kill:** any confident-wrong on flips, or <6/12 → tier 1 has no verdict rung. Meta-rule: a synthetic pass is necessary-not-sufficient; promotion needs the real-data legs.

**E4 — Abstention Ledger, part A** *(2 weeks, ₹0).* Pool ~50–70 labeled cases; predictor stack = grounded sim where data exists + trust features; α = 0.10; leave-one-bucket-out Mondrian; thresholds sealed before scoring; real-data held-out coverage required; **falsification arm:** the gate wrapped around the words-only chance predictor must drive flip certification to ~0 — a gate that certifies a chance predictor is broken. **Kill:** coverage violated; grounded-predictor abstention ≈100%; or the falsification arm passes the chance predictor.

**E5 — Proximal / double-negative-control** *(2–3 weeks)* on the benchmark that broke the single-NC guard (Miao, Geng & Tchetgen Tchetgen 2018; Tchetgen Tchetgen et al. 2020). **Kill:** no sign recovery → naturally-confounded exhaust stays "untrustworthy-empirical → abstain" and tier-2 label admission tightens.

**E6 — Factory Δmediator SKU pilot** *(gated on factory deployment; first real spend).* One matched-panel micro-study measuring a change→mediator shift for a case where E3 abstained; predict, seal, compare against held-out truth; the panel→customer external-validity edge is the explicit hypothesis. **Kill:** measured shifts don't transport even directionally → the factory is a calibration-set supplier (Mondrian bucket-filler for E4's n-floors), not a magnitude supplier — still valuable, differently priced.

**E7 — Behavioral prior-fitted-network spike** *(gated on E1's branch + E3; ≤2 weeks, one GPU).* Only for where the calculator can't go (CausalPFN / Do-PFN lineage). Train on 5 of 6 taxonomy families plus an independently authored sealed generator; test on the held-out family; baselines = the calculator and a same-tables LLM; a conditional-bias audit (directional base rate given change-type features, balanced flip set) with a hard fail threshold. **Kill:** held-out-family failure or conditional-bias failure → the amortized-prior bet dies before any corpus spend — proving the feature-store ask irreducible for ₹0 is itself a publishable answer.

**Standing instrument (not an experiment):** every tier-3 customer's data is permanently degraded to tier-1/2 views and re-scored, publishing the per-rung accuracy/abstain delta. This converts §6 from argument to maintained measurement.

---

## 8. Rejected designs

The council's negative catalogue — each entry independently derived by at least one red-team, and each traceable to measured evidence.

1. **Tier-0/1 confident verdicts of any kind** (all six original proposals). The flip-deciding magnitude is not in cheap-tier data; a Bayesian posterior in non-identified directions *is* the prior — N5 re-armed.
2. **Intersection-of-bounds across source environments** (transport lens). Valid only under source independence; a factory-dominated library shares one panel, incentive structure, and horizon — N3's 0/12 failure wearing data. Replaced by random-effects pooling with reported τ², factory = one environment.
3. **Cross-product transport as an identification claim** (transport lens). Transport theorems require shared structural equations; mechanism-tag matching is verbal analogy — and reference-class analogy measured null (N2). Transport survives only as an ensemble-gated *donor* mechanism, falsified per-customer against exhaust.
4. **An antisymmetric output head as a "provable kill" of directional bias** (training lens). It blocks only marginal bias; content-conditional bias ("new-feature-ish description ⇒ up") passes through. Demoted to marginal-bias removal + a mandatory conditional-bias audit (E7).
5. **Moment tables as sufficient statistics for the validated estimator** (query-compiler lens). False for logistic response models and per-row overlap diagnostics. Replaced by the in-warehouse full estimator; moment SQL survives as a labeled lower-trust fallback.
6. **The surrogate bridge at cheap tiers.** No reachable library source has genuinely long-run outcomes; surrogacy violations flip signs. Deferred to tier 3 with per-customer validation.
7. **Global conformal guarantees from the ~6–12-case public pool.** Exchangeability is indefensible at that n and heterogeneity — guarantee theater. Certificates are per-customer, n-floored, audit-clause-backed only.
8. **Un-audited certificates.** Certified skips self-censor their own labels; without the randomized-audit clause the headline error rate is unfalsifiable in production.
9. **Training before the information question is settled** (PFN corpus spend, RL fine-tunes). If a 50-line deterministic program ties the proposed model on the target slice, the model is unfunded (E1 gates E7; the factory learning-curve gate gates the corpus).

Standing kill-list, re-litigable only with new evidence: persona role-play as predictor; words-only verdicts; LLM ensembles as predictors; calibrated point-estimate claims.

---

## 9. Dissents

Recorded because they are real and two of them are not empirically resolvable.

1. **Top-pick split (2–1).** The decision-theoretic and venture judges picked the Backtest Ladder (first deliverable changes real decisions in days; the audit contract *is* the data grant). The scientific-soundness judge picked the Abstention Ledger (the only artifact whose every claim is a finite-sample guarantee or a labeled non-claim — the one a hostile data-science team cannot shred). The chair's merge (Ledger as the mandatory gate inside the Ladder skeleton) is a synthesis both would sign, but the emphasis question — *audit-led wedge with a guarantee inside, or guarantee-led instrument with an audit on top?* — is a go-to-market decision the evidence cannot make.
2. **Does tier 1 exist as a verdict rung at all?** *(v1.1: RESOLVED by E1 for the composition/arithmetic slice — the rung exists; prevalence over a real backlog stays open, per the codex-audited scoping.)* *(v1.2, E3-P RUN 2026-07-01: prevalence measured on a 44-case realistic backlog — 2.3% composition-decidable pre-launch; COVERAGE-A 0%, COVERAGE-B 13.6% with 0 confident-wrong → MARGINAL per the sealed bands. The red-teams were right about near-total pre-launch abstention; the lenses were right that the called slice is genuinely arithmetic. Tier 1 = minor rung + data-quote surface; sales motion leads tier-2-first; the abstain ledger — 86% of post-pilot abstains are missing per-arm exports rather than missing methods — is the priced ask, while customer-side coverage remains an ownership argument, not a measurement. research/fable-frontier-experiments/E3P_RESULTS.md.)* Two red-teams argue honest tier-1 collapses to near-total abstention (Manski sets straddle zero at realistic 1–3pp effect sizes); two lenses maintain composition-driven flips are genuinely arithmetic over aggregates. E1 + E3's abstain-rate headline resolves this empirically; the architecture prices both branches.
3. **Is the audit wedge defensible?** Experimentation platforms could ship EB shrinkage natively; and exhaust-rich buyers are not obviously prediction buyers. Counter: the audit's value is the data grant and trust sequence, not the statistics. The wedge's moat is the ladder above it.
4. **Will customers sign the randomized-audit clause?** It consumes part of the very ROI being sold. The repair prices around it (charge on the (1−ε) fraction); one judge holds it non-negotiable for identifiability, another doubts it commercially. If customers refuse, certificates degrade to triage — the product survives; the *word* doesn't.
5. **The PFN's worth.** Highest ceiling and deepest eventual moat on one scoring; the riskiest verdict path on another (a *trained* prior dominating exactly on the sellable slice is N5 with extra steps). Both endorse the same sequencing, so the dissent is about hope, not action.
6. **How much was the data ask actually reduced?** The sharpest shared finding: most "tier-1" designs reduce data *egress* (real — DPA friction often binds) while leaving data *existence and modeling* untouched. The council adopts the honest phrasing — "privacy-preserving"; "who must trust you with rows, not what must exist" — and records a minority view that even this synthesis is partly a relabel.
7. **What is the factory?** Magnitude supplier (tier 1.5), prior/corpus source (E7), or calibration-set filler (E4 n-floors)? All three roles are claimed; E6 decides. The panel→customer external-validity gap is load-bearing in every role and validated in none — the council's largest shared exposure.

---

## 10. Limitations

**The ceiling is real and priced, not denied.** Even at tier 3, some behavior is unpredictable in principle (N6); the abstain tail never closes; the honest quantification of the 80/20 taxonomy bet is a coverage-at-guaranteed-error curve, to be measured, not asserted. **Per-person counterfactuals remain calibrated fiction** — trustworthy in aggregate, fictional per individual — at every tier. **The synthesis rests on small-n existence proofs**: the 12/12 grounded result is decisive but narrow; Cookie Cats is one real dataset; the guard failed one real benchmark. **The factory's external validity is untested** (dissent 7). **Egress ≠ existence** (dissent 6): nothing here creates events a customer never logged. And the council notes its own method's exposure: six lenses and three judges were instantiated from the same model family; genuinely independent human adversarial review of this paper is the next layer of the same discipline the paper advocates.

---

## 11. Related work

**Transportability and data fusion:** Pearl & Bareinboim (2014); Bareinboim & Pearl (2016); Degtiar & Rose (2021) — the formal basis for P(z)-reweighted transported surfaces. **Partial identification:** Manski (1990); Tamer (2010); Fan & Park (2010) — sign sets where identification fails. **Proximal causal inference:** Miao, Geng & Tchetgen Tchetgen (2018); Tchetgen Tchetgen et al. (2020) — the double-NC repair route. **Surrogates:** Athey, Chetty, Imbens & Kang (REStud 2025). **Experiment meta-analysis and the winner's curse:** Azevedo et al. (JPE 2020); Lee & Shen (KDD 2018); Coey & Cunningham (WWW 2019) — the zero-centered fat-tailed prior and the audit wedge. **Conformal/selective prediction and anytime-valid inference:** Angelopoulos, Bates et al. (Learn-then-Test, AoAS 2025; Conformal Risk Control, ICLR 2024); Prediction-Powered Inference (Science 2023; PPI++); Ramdas et al. (2023); Johari et al. (2022). **Amortized causal estimation:** Müller et al. (ICLR 2022, PFNs); Hollmann et al. (Nature 2025, TabPFN); CausalPFN (arXiv:2506.07918); Do-PFN (arXiv:2506.06039). **Simulation-based inference and moment calibration:** McFadden (1989); Cranmer, Brehmer & Louppe (PNAS 2020); Kennedy & O'Hagan (2001); Platt (JEDC 2020); Chopra et al. (AAMAS 2025) on LLM-ABM limits. **Population synthesis:** IPF + copula methods (Kao et al. 2016; TR-C 2024). **LLMs as experiment predictors:** Hewitt et al. (2024) — the optimistic upper bound our sealed campaign fails to reproduce on counter-intuitive cases. **Predictability ceilings:** Salganik et al. (PNAS 2020). **Outcome-grounded post-training:** Thinking Machines × Bridgewater (2026); GRPO (Shao et al. 2024).

---

## Appendix A — Council process and provenance

Six proposer agents (lenses: causal transportability; outcome-grounded training; calibration/uncertainty; minimal-data-ask design; simulation science; systems pragmatics) received the sealed evidence base and produced literature-grounded structured proposals. Each was adversarially red-teamed against N1–N6 (verdicts: 6/6 "revise" — none survived unrepaired, none died outright). Three judges scored all repaired proposals through decision-theoretic, scientific-soundness, and venture lenses (top-pick split 2–1, §9.1). A chair synthesized the unified architecture. Full artifacts: `council-dossiers.md` (proposals, critiques, scores), `council-synthesis.md` (chair synthesis). Workflow run `wf_4385dd55-493`, 2026-07-01; 16 agents; ~1.04M tokens.

*Ties to: `founder-readout/simulation-engine-where-we-landed.md` (evidence base), `founder-readout/finetuned-simulator-readout.md` (factory/training analysis), `research/engine-strength-campaign/LEDGER.md` (sealed-run discipline), memory `project-empirical-uplift-and-council-spike`.*
