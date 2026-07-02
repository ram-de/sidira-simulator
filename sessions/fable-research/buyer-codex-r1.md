# Independent Buyer Council — Sidira for A/B Accuracy

Grounding constraint: repo evidence only. Inputs read: `PAPER.md` sections 6, 7, 9; `DEBATE_CONCLUSION.md`; `E3P_RESULTS.md`; `LEDGER.md`. I did not read any pre-existing buyer file.

## 1. COUNCIL

### Buyer-Side Experimentation Executive

Amazon-class probability of paying within 24 months: **8%**.

An Amazon-class experimentation leader will not buy Sidira as "better A/B test accuracy" if that means predicting experiment direction before launch. The measured strict pre-launch result is too weak: realistic backlog coverage-A is 0%, in-principle composition-decidable prevalence is 2.3%, and no LLM method beats chance on counter-intuitive direction. Their own teams already know winner's curse, shrinkage, negative controls, and experiment portfolio effects; Sidira cannot walk in with a generic audit and teach them the math. The only wedge they might respect is a sealed, zero-egress audit that proves their own historical decision process is systematically over-shipping or over-killing, then offers selective decision gates with bounded error on called cases. Even then, Amazon-class buyers will ask why this is not a two-quarter internal project. I would buy only if Sidira shows a proprietary benchmark, a clean in-warehouse deployment, and a material regret reduction on my own historical exhaust.

### Market Analyst

Amazon-class probability of paying within 24 months: **5%**.

The top of market is structurally unattractive as the first customer segment: massive experiment volume, mature internal statistics, low tolerance for opaque external claims, and strong build-vs-buy instincts. The repo evidence supports a narrow, credible product, not a broad platform: tier-2 winner's-curse audit plus negative-control guard as wedge, with selective pre-test decision intelligence as the eventual category. The commercial opening is not "we predict experiments"; it is "your org is making launch decisions from noisy positive tests, and we can quantify and reduce that regret using your exhaust." That message lands better with companies that run many tests but do not have Amazon/Microsoft-level experimentation science teams. The highest-probability market is experiment-rich, DS-constrained digital businesses where an audit creates executive urgency and the export burden is tolerable.

### Hostile Data Scientist

Amazon-class probability of paying within 24 months: **2%**.

I would attack Sidira's pre-launch claim immediately: E3-P says realistic pre-launch coverage is 0%, and called accuracy in post-pilot Arm B ties PM optimism at 0.667 on n=6. E2 kills mechanism tags as sign predictors, and the joint conclusion says the only proven engines are deterministic calculator, direct A/B estimates, and grounded g-formula with customer data and checks. That means the product does not escape the data requirement; it just formalizes when the data is sufficient and when to abstain. For Amazon-class teams, the tier-2 audit is mostly EB shrinkage, portfolio calibration, and guardrails they can build. Sidira survives my review only if it never claims sign prediction from personas/prose, exposes full abstention accounting, and wins a sealed backtest against the customer's existing launch rules. The irreproducible part is not the statistical method; it must be the operational package, benchmark discipline, and cross-customer calibration corpus, none of which is proven yet in the evidence.

### Value Engineer

Amazon-class probability of paying within 24 months: **10%**.

The value case can be real, but not on pre-launch oracle accuracy. For a high-volume experimentation org, shaving even a small fraction of false ships, false kills, and retest waste could be worth seven figures, but the buyer will require proof on their own exhaust. Sidira's best artifact is a sealed portfolio audit: ingest historical A/B logs, estimate winner's-curse/regret, calibrate selective decision thresholds, produce an abstention ledger, and name which future tests should run, expand, or stop. Pricing should anchor to volume and provable avoided waste: roughly **$150k-$400k** for an initial audit at mid-market scale, **$500k-$1.5M ACV** for a production decision gate at a serious experimentation org, and **$2M+ only after measured regret reduction** at an Amazon-class account. Without customer-side historical logs, the offer collapses to advisory triage and should be priced much lower.

### GTM Operator

Amazon-class probability of paying within 24 months: **6%**.

Do not start with Amazon. The sales cycle will be slow, the security review severe, the internal champion hard to find, and the first question will be "why would we not assign this to our experimentation platform team?" The first buyers are VP Product, Head of Growth, or Experimentation Lead at companies with enough tests to feel decision noise but not enough causal-inference depth to own the full solution. The entry offer should be a fixed-scope, low-egress "Experiment Decision Audit" that produces an executive readout and a backlog of policy changes, not a promise to forecast every new test. The expansion path is in-warehouse recurring monitoring: launch threshold calibration, negative-control guard, shrinkage-adjusted scorecards, selective pre-test/pilot calls when sufficient tables exist, and EVOI recommendations for what extra data to collect. Sales copy must avoid "AI agents simulate your users"; the evidence makes that a liability.

### Red Team

Amazon-class probability of paying within 24 months: **3%**.

The biggest commercial risk is that Sidira is mostly a disciplined wrapper around methods sophisticated buyers already know. The repo's strongest measured result, E1, proves arithmetic extraction from sufficient tables; that is reliable but not hard for a buyer's DS team to replicate. E3-P is commercially sobering: strict pre-launch tier-1 is a minor rung, and the post-pilot called set is tiny, with value coming from zero confident-wrong and abstention rather than superior directional accuracy. The moat is therefore not "model intelligence"; it is trust machinery, sealed evaluation practice, instrumentation templates, and maybe a future cross-customer evidence corpus. If the team cannot accumulate proprietary calibration data or make deployment radically easier than internal build, the product becomes a consulting audit with software margins aspirationally attached. Kill the Amazon wedge unless Amazon volunteers a design-partner path.

## 2. CHAIR SYNTHESIS

### Verdict On Amazon-Class

**Amazon-class companies are unlikely to pay real money within 24 months for Sidira as an A/B accuracy product. My synthesized probability is 5-8%.**

They may pay for a narrow, sealed, in-warehouse audit if it exposes avoidable decision regret in their own historical experiment exhaust, but they will not pay for the thing an outsider would naively pitch: pre-launch simulation of user response. The evidence does not support that pitch. E3-P measured realistic strict pre-launch coverage at 0%, E2 killed mechanism-tag sign selection, and the joint statement restricts proven engines to calculators over sufficient tables, direct A/B estimates, and grounded g-formula with real customer data and checks.

The Amazon-class objection is not "this is wrong." It is worse commercially: "this is correct, narrow, and buildable." Amazon-like teams have the experiment volume, internal literature, and platform control to replicate the known statistics if the value is obvious. Sidira would need to sell operational compression, sealed discipline, and external audit credibility, not novel causal magic.

### Ranked Top-3 ICPs Who Actually Pay First

1. **Experiment-rich, DS-constrained digital commerce / marketplace companies**

They run enough A/B tests that winner's curse and noisy launch decisions cost real money, but they do not have Amazon-grade experimentation science. Buyer: VP Product, Head of Growth, or Experimentation Lead. They buy a **sealed A/B portfolio decision audit**: historical exhaust ingest, shrinkage/regret analysis, negative-control guard, launch-threshold recommendations, abstention ledger, and next-test EVOI list. ACV frame: **$100k-$250k initial audit**, expanding to **$250k-$750k/year** for recurring in-warehouse monitoring and decision gates.

2. **Consumer subscription / gaming / marketplace teams with many small experiments**

These teams feel false positives, novelty effects, and segment/guardrail tradeoffs acutely, and the cost of a bad launch is legible. They buy a **pilot-to-launch decision gate**: standardized per-arm export, deterministic calculator where sufficient, direct A/B estimates with shrinkage, flat-call handling, and recommendations for when to continue, stop, or measure a mediator. ACV frame: **$150k-$500k/year**, with a lower fixed pilot around **$50k-$100k** if procurement friction is high.

3. **Mid-market experimentation platforms / consultancies serving many customers**

They may pay because Sidira becomes a differentiated audit layer they cannot credibly fake with dashboarding. They buy a **white-labeled or embedded experiment-quality audit module**: winner's-curse readouts, selective confidence gates, export-schema enforcement, and abstention reasons. ACV frame: **$75k-$300k/year** plus usage or services attach. This is less clean than direct enterprise sales because platform buyers may copy the feature, but it can create distribution and calibration data if structured carefully.

### The Artifact They Buy

The first paid artifact should be called something like **Experiment Decision Audit**, not "simulator."

Minimum credible package:

- Historical A/B exhaust import or in-warehouse connection.
- Sealed backtest against the customer's existing launch rules.
- Winner's-curse / shrinkage / regret report with decision-economics metrics.
- Negative-control guard and abstention ledger.
- Calibrated thresholds for future tests.
- Standardized per-arm export schema for post-pilot calls.
- EVOI queue: which missing quantity is worth measuring next.

The expansion artifact is **Selective Experiment Decision Gate**: an operational layer that says SHIP, KILL, CONTINUE, or ABSTAIN only when the evidence class supports it. This must preserve evidence labels: replay, interpolation, arithmetic aggregate, transported/purchased, or novel abstain.

### The Irreproducible-Asset Question

What can a buyer's own DS team not replicate in a sprint?

**Honestly: not the core statistics.** A competent experimentation DS team can reproduce deterministic arithmetic over sufficient tables, EB shrinkage, direct A/B estimates, and basic negative-control checks. An Amazon-class team can do more than that.

The potentially irreproducible assets are:

- A hardened, zero-egress deployment path that plugs into messy experiment logs faster than an internal platform team can prioritize.
- A sealed evaluation and audit workflow executives trust because it is external and pre-registered.
- A growing cross-customer calibration corpus mapping experiment metadata, abstention reasons, and decision outcomes, if Sidira can legally and technically accumulate it.
- A disciplined abstention product that refuses unsupported calls and names the cheapest measurement to unlock them.
- Domain-specific instrumentation templates that make the per-arm export and guardrail taxonomy cheap to adopt.

Right now, only the discipline is evidenced. The cross-customer corpus and deployment advantage are not yet proven. That is the crux. Without one of those becoming real, Sidira is a high-quality causal audit consultancy with a software interface.

### Kill Conditions

1. **No design partner will provide A/B exhaust.** If buyers will not share or connect historical logs, the tier-2 wedge fails and the product is stuck at low-value triage.

2. **Sealed backtests do not beat existing customer launch policy on decision economics.** Directional accuracy alone is insufficient, especially after E3-P tied PM optimism on the called subset. The product must reduce false-ship, false-kill, regret, wasted traffic, or time-to-decision at useful coverage.

3. **Coverage remains too low after customer-owned per-arm exports.** E3-P's 13.6% public-artifact coverage may be a floor, but if real customer logs do not lift it materially, the recurring gate is too narrow.

4. **Internal DS teams replicate the audit in one sprint.** If a prospect can build the same audit and thresholds quickly, Sidira needs either data-network effects or deployment leverage. Otherwise price collapses.

5. **The team drifts back into persona/LLM sign prediction.** E2 and E3-P make that a credibility-destroying path.

### Three Concrete Next Moves

1. **Run one paid or design-partner tier-2 audit on real A/B exhaust.**

Target a company with 100-1,000 historical experiments, not Amazon. Pre-register the scoring plan, compare against their actual launch decisions, and report regret, false-ship/false-kill, abstention, and saved traffic. This is the only evidence that will turn the wedge from plausible to sellable.

2. **Productize the frozen per-arm export and abstention ledger.**

Make the smallest in-warehouse artifact that a customer can run in an afternoon: schema checks, export validation, calculator calls, direct estimates, missing-quantity reasons, and EVOI output. E3-P says the missing ingredient is often the table, not another model; make that operationally cheap.

3. **Write the anti-pitch into the deck and sales script.**

Say explicitly: Sidira does not predict novel experiment direction from personas, prose, or mechanism tags. It improves experiment decisions by auditing historical exhaust, shrinking noisy wins, guarding against invalid comparisons, and making selective calls only when the evidence is sufficient. This will repel weak leads and earn the attention of serious experimentation buyers.

Bottom line: **Amazon is not the first buyer. The first buyer is an experiment-rich company whose decision process is expensive but statistically under-governed. They pay for a sealed decision audit and, if it works on their exhaust, a recurring selective decision gate.**
