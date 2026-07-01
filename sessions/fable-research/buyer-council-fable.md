# Fable Buyer-Viability Council — full record

Workflow wf_333bf71d-2fd, 7 agents, 2026-07-01. Question: would an Amazon-class company pay for Sidira to improve A/B test accuracy?

## Chair synthesis

**BUYER-VIABILITY COUNCIL — CHAIR'S MEMO**
*Sidira / pre-test decision intelligence — 2026-07-01*

---

**1. THE VERDICT: Does an Amazon-class company pay? No. Unanimous.**

Six lenses, zero dissent, probability spread **3–5%** (amazon-insider 3%, market-analyst 3–5%, ds-skeptic 3–5%, economic-buyer 5%, gtm-strategist 5%, red-team 3%; red-team caps even the softened "any F500 with a central experimentation org" version at <10%). Consensus midpoint: **~4%**, and the residual tail is an acqui-hire or a single test-starved BU years out, not a license.

The kill is overdetermined, on three independent axes:

- **They authored the fix.** Lee & Shen, Coey & Cunningham, Azevedo et al. — the winner's-curse literature the tier-2 wedge implements — was written at Airbnb, Facebook, and their peers. Weblab ships shrinkage natively. Selling this to Amazon is selling the textbook back to its authors.
- **The measured numbers don't clear their bar.** E3-P: 2.3% pre-launch prevalence, 13.6% post-pilot coverage, called accuracy 0.667 — exactly tying "always ship it," against a free PM base rate of 61%. Traffic is not scarce at Amazon; the cheapest measurement is the test.
- **Procurement physics.** No vendor has ever cracked Weblab; feature-store egress fails security review before the science review starts. Tier-3 — the only rung with a proven edge (12/12 on magnitude flips) — requires exactly the access Amazon would sooner replicate than grant.

Generalize this: **any company with a central experimentation-science org is a non-buyer** — Microsoft, Meta, Booking, Airbnb, Netflix. Amazon's correct role in the GTM is alumni pipeline: the ex-Weblab scientist at a mid-market company is the champion, because they know the math is real and know their new employer can't build it.

**2. THE REAL ANSWER — who pays, for what, at what price.**

Nobody pays to "improve A/B accuracy" — the test *is* the accuracy. The evidence supports exactly three purchasable claims: (i) un-ship past false winners, (ii) compress expensive tests via pilot extrapolation, (iii) never confidently ship the wrong sign. The artifact that carries all three is the **fixed-fee winner's-curse audit of past exhaust** — zero prediction risk, day-one ROI, and contractually it *is* the data grant that unlocks everything above it.

Ranked ICPs:

1. **Mid-market consumer company (e-comm, subscription, gaming, marketplace), $50–500M revenue, 100–300 resolved experiments on Statsig/Eppo/GrowthBook, no experimentation scientist.** Their PM reads the dashboard at face value, i.e., ships the curse. Entry: audit at **$25–50k**. Expand: certificate + abstention ledger + post-pilot calculator at **$60–150k/yr**, priced against one reversed bad launch (3–5 lenses converge on this band independently).
2. **Traffic-scarce, high-stakes verticals — consumer fintech, insurance/telco digital arms, email/CRM retail (Hillstrom-shaped).** Each test is 6–8 compliance-gated weeks; pilot→full-test extrapolation frees real roadmap. Big warehouse, tiny test traffic: the ideal zero-egress buyer. Caveat: many can't reach the ~30-non-null certificate floor, so price honestly at $30–60k "triage, no guarantee."
3. **PE portfolio-operations teams.** One audit contract replicated across 8 portfolio companies — the multiplier account and the fastest route to the cross-customer backtest library.

$200k+ ACV exists only after a live tier-3 feature-store engagement proves customer-side coverage. It is not priceable today.

**3. POINTS OF HARD AGREEMENT.**

- Amazon-class: no, ~3–5%, for the same three reasons in every lens.
- The sellable artifact is the **audit**, not prediction. Sell prediction and a competent buyer runs your own E3-P table back at you.
- The product's honest core — zero-sign-error + calibrated abstention + priced data asks — is real and novel *discipline*, but it is a **policy, not an asset**; every lens that checked concluded a competent team clones the method in a sprint-to-quarter.
- Coverage is blocked by data logistics, not method — which is fatal upmarket (they solved logistics) and the whole opportunity downmarket (they own their pilot exports).
- Platform absorption (Eppo/Statsig shipping shrinkage natively) sets an **18–24 month clock**; the only structural defense is the conflict of interest — platforms sell "run more tests" and won't ship "we can't call 86% of your backlog."

**4. THE SHARPEST DISAGREEMENT — and my ruling.**

Five lenses assume the audit sells: reverse one bad launch and it pays for itself. The red team attacks **demand itself**: winner's curse presents as success — metrics up, launch email sent, promotion cycled. The audit's deliverable indicts the buyer's past decisions, and its natural champion is the person it embarrasses. Painkillers sell; this is a diagnosis of an asymptomatic disease delivered to the patient's ego. Objections 1, 2, 4, 5 are handled or handleable; objection 3 attacks whether a buyer exists at all, and there is **zero conversion evidence** either way.

**Ruling: the red team is right that this is the fatal-unless-disproven risk, and wrong to treat it as a verdict.** The other five lenses' ROI math is sound *conditional on a buyer feeling the pain*; that conditional is untested. So I rule: the audit remains the wedge, but it must ship in the red team's repaired framing — **dollar-denominated and forward-looking** ("this shipped win will miss its annualized projection by $X; here's the cheap holdout that proves it") — converting embarrassment into budget defense. And demand is now a registered hypothesis with a receipt metric (see §7), not an assumption. Secondary note: the gtm-strategist's revenge-purchase archetype (DTC brand burned by CRO-agency "wins") partially dissolves objection 3 — target buyers where the embarrassment belongs to a *vendor*, not the champion.

**5. THE IRREPRODUCIBLE ASSET — the honest answer.**

Today, in code or method: **nothing.** The arithmetic is ~50 lines, the shrinkage is published literature, the admission rules and abstention ledger are a sprint, conformal gating a quarter. The ds-skeptic's audit is correct and no lens rebutted it. What a sprint cannot clone:

- **The sealed negative-evidence corpus** — measured proof that persona sims, LLM ensembles, and mechanism tags don't pick signs. Real, but it's diligence value (a reason to trust you and distrust competitors), not license value.
- **Prospectively:** per-customer sealed backtest certificates and a cross-customer library of measured (population, change, outcome) triples — the only compounding asset in the deck. But E6 is unrun; the factory's external validity is, per the record, "the council's largest shared exposure."
- **Structurally:** the platform conflict of interest. Not an asset you own — a gap they choose to leave. Worth 18–24 months, not a moat.

The crux, stated plainly: **the moat does not exist yet; it must be earned customer by customer**, and the audit is the instrument that earns it. The business is a race to accumulate sealed certificates before platforms ship the feature.

**6. KILL CONDITIONS.**

1. **Demand kill:** 3–5 audit pitches to on-profile ICPs fail to convert, or a delivered audit reverses a real decision and the buyer still doesn't renew/expand — red-team objection 3 confirmed; no repositioning survives it.
2. **Coverage kill:** the design-partner Arm-B measurement (owned per-arm pilot exports, real backlog) comes back materially below ~40%, or produces one confident-wrong sign in the wild — the ownership argument dies and with it the subscription.
3. **Clock kill:** Statsig/Eppo ship native curse-audit + shrinkage before first renewals close.
4. **Guard kill:** E5 (proximal double-NC repair) fails — the watchdog is then unusable on naturally confounded exhaust, which is most exhaust.
5. **Factory kill:** E6 shows the measured-triples library doesn't transfer across customers — the only compounding asset evaporates.

**7. WHAT TO DO NEXT — three moves.**

1. **Sell 3–5 paid winner's-curse audits at $25–50k fixed fee, now**, in the dollar-denominated forward-looking framing, targeting ICP #1 (bias toward the "burned by agency wins" revenge profile). Receipt metric per red team: at least one documented reversed decision or skipped test the buyer valued above the fee, evidenced by renewal or expansion. This simultaneously tests kill condition 1 and executes the data-grant trust sequence.
2. **Land one design partner and measure customer-side Arm-B coverage** on their owned pilot exports — the single number the entire council agrees converts "ownership argument" into demand evidence, and the top of E3-P's own limits list.
3. **Stop all Amazon/enterprise motion**; redirect that energy to (a) productizing the sealed certificate + abstention ledger so audits compound into the library, and (b) running E5 and E6 to close the guard and factory exposures before a renewal conversation depends on them.

The truth in one sentence: you built a statistical conscience, and consciences are bought by organizations that lack one — the business lives or dies on whether they can be made to *feel* its absence in dollars, which is exactly what the next five audits must prove.

---

## Lens outputs (provenance)

### Lens: amazon-insider

All four grounding files read. Here is the verdict.

---

I ran experimentation at Amazon scale. Let me be exact about what this product is, per its own sealed evidence, before answering whether anyone like us would buy it.

**What it actually is (measured, not pitched).** Three proven engines: a deterministic composition calculator over per-arm aggregate tables (E1: 24/24, zero sign errors, held in the wild in E3-P), direct A/B estimates, and a grounded g-formula mediation sim (12/12 on magnitude-driven flips, needs the feature store). Plus a validated negative-control watchdog and a winner's-curse audit of A/B exhaust. Everything else abstains. On a realistic 44-case backlog: pre-launch arithmetic covers 2.3% of hypotheses; post-pilot coverage 13.6%; called accuracy 0.667 — which exactly ties naive PM optimism on the called set. The differentiator is zero-confident-wrong plus calibrated abstention plus a priced data ask. That is a real, honest property. It is also a property Amazon already has, institutionally.

**Build-vs-buy at Amazon.** Walk the components:

- *Winner's-curse / EB shrinkage audit.* Weblab's science team ships shrinkage-corrected lift estimates natively; the "reverse your past launch decisions" audit is a quarterly internal exercise, and the people who'd evaluate this vendor include coauthors of the literature it cites. Value of the wedge at Amazon: zero — the wedge's own paper concedes this in §9 dissent 3 ("experimentation platforms could ship EB shrinkage natively; exhaust-rich buyers are not obviously prediction buyers").
- *Composition calculator.* The paper itself calls it ~50 lines. A bar-raiser will ask "why not build this in a sprint," and the honest answer is: you would. E3-P proves the binding constraint is data logistics (per-arm exports), and Amazon has no data-logistics problem — Weblab *is* the frozen export.
- *g-formula over the feature store.* Amazon owns the feature store, the economists, and long-term holdout infrastructure for exactly the mediation/long-run questions this targets. The one measured moat — 12/12 on magnitude flips — is a method, not an asset; methods published in your own PAPER.md are reproducible by a two-pizza science team in a quarter.
- *Abstention/conformal gating, test prioritization under fixed traffic.* Real gaps exist here even at Amazon (most teams over-test low-information hypotheses), but the internal meta-analysis groups own that roadmap, and the E3-P result — called accuracy *ties* optimism; PM is right 61% anyway — kills the ROI slide. At tens of thousands of experiments/year, traffic is not scarce enough for a 13.6%-coverage skip-recommender to price against.

Then the vendor gate: no external analytics vendor has ever cracked Amazon for core experimentation tooling. Not Optimizely, not Statsig, not Eppo — Weblab is sovereign, and shipping experiment exhaust or feature-store access to an outside party fails security review before the science evaluation even starts. Zero-egress warehouse-native deployment is designed for Snowflake/BigQuery shops; Amazon is neither, culturally or technically, for this workload.

**So who does pay?** Invert every Amazon property. The buyer is a company where: (a) traffic is *scarce* — each test costs 2–6 weeks and the backlog is 10× capacity; (b) there is no central experimentation-science team — a handful of DSs, no shrinkage, no FDR control, launch decisions made on raw p<0.05 winners (so the winner's-curse audit reverses real decisions on day one — the measured, zero-prediction-risk deliverable); (c) the data already sits in Snowflake/BigQuery so the zero-egress story lands; (d) tests are *expensive per unit* — fintech, marketplaces with supply-side risk, subscription products where a bad ship burns cohorts. That's Series B–D product companies, roughly 30–300 resolved experiments of exhaust (the ≈30 non-null certificate floor is exactly calibrated to this segment), 50–500 employees, no Kohavi-reader on staff. The paper's own tier-2-first sales motion, confirmed by E3-P, describes this buyer precisely. Amazon-class companies are the *donor/instrument* tier at best — and they won't grant that either.

**Brutal summary.** This product's honest core — "we never call a wrong sign, we abstain loudly, and we price the measurement that would unlock a call" — is an integrity feature, and integrity features sell to organizations that lack internal statistical trust, not to the organizations that manufacture it. Amazon is the manufacturer. The measured numbers (2.3% prevalence, 13.6% coverage, tie with optimism on direction, 61% PM base rate) would not survive the first WBR at Amazon as a purchase justification, and the team knows it: the sealed record already routed the company away from "beat the platform" toward "audit the platformless."

VERDICT: Amazon-class pays: no — everything measurable here is a quarter of internal build for a team that already employs the literature's authors, and no experimentation vendor has ever cleared Weblab's build-vs-buy or security bar; P(Amazon-class pays for this within 3 years) ≈ 3%.

ICP: First check comes from a Series B–D product/fintech/marketplace company on Snowflake or BigQuery with 30–300 experiments of exhaust, scarce traffic, and no experimentation-science team — buying the winner's-curse audit of past launches, with selective post-pilot verdicts riding along.

PRICE: They pay for the tier-2 audit-plus-abstention-gate as an annual subscription — defensibly framed at $60–120k/yr (a fraction of one data-science hire, or 2–4 recovered bad-launch decisions), with priced per-measurement micro-study add-ons; not a per-prediction oracle price, which the coverage numbers cannot support.

---

### Lens: market-analyst

**Where this sits on the map.** Optimizely, VWO, AB Tasty, Kameleoon sell workflow to marketing orgs; Statsig, Eppo, GrowthBook sell warehouse-native infrastructure (assignment, flags, metrics, CUPED, sequential stats) to product/eng orgs. This product is neither: it is a decision-layer that consumes a platform's exhaust — winner's-curse audit of past wins (tier 2), a zero-sign-error post-pilot calculator with 13.6% coverage, an abstention ledger, and priced data asks. The market history of decision-layers is unkind: they get absorbed as features. Eppo shipped variance reduction and Bayesian shrinkage as line items; Statsig ships meta-analysis dashboards. The paper's own dissent 3 concedes platforms could ship EB shrinkage natively — Lee & Shen wrote the winner's-curse paper *at Airbnb*, Coey & Cunningham *at Facebook*. The statistics are public, ~200 lines, and platforms own the exhaust already.

**Amazon specifically: no, and it's not close.** Three independent kills:

1. *They already own the fix.* Weblab has a central experimentation science org; Amazon economists publish in the winner's-curse literature the audit is built on (the Azevedo et al. lineage is priced into their launch criteria). Selling EB shrinkage to Amazon is selling the textbook back to its authors. The audit wedge's real function — per the debate conclusion — is a *data grant and trust sequence* for the ladder above it. Amazon needs no trust sequence; it needs nothing above rung 2 that it can't build in a quarter with one L6 scientist.

2. *The measured numbers don't clear their bar.* E3-P is the honest ceiling: strict pre-launch coverage 0%, in-principle prevalence 2.3%, post-pilot coverage 13.6%, and — the killer for this buyer — called-set accuracy 0.667 *ties* always-treatment-wins on the called subset. At Weblab scale (tens of thousands of tests), a 13.6%-coverage advisor that doesn't beat PM optimism on direction is noise; their sequential-testing machinery already provides early stopping on pilots, which is what the post-pilot calculator competes with. The zero-sign-error + calibrated-abstention property is genuinely novel discipline, but Amazon buys that as a hire, not a vendor.

3. *Procurement is disqualifying.* Tier-3 (the only rung with the proven 12/12 g-formula edge) requires feature-store access. Amazon does not grant behavioral row-level access — or even standardized aggregate exports — to a seed-stage vendor for any price the vendor could charge. Zero-egress warehouse-native deployment fixes DPA friction for Snowflake mid-market, not for Amazon's internal stack.

Generalize: **any company with a central experimentation-science team is a non-buyer** — Microsoft, Booking, Airbnb, Meta, Netflix. They are the *authors* of this product's bibliography.

**Who actually pays.** The buyer profile is defined by three simultaneous conditions: (a) real exhaust — 100–1,000 resolved experiments (tier 2's ≥30 non-null floor, comfortably), (b) *no* staff causal-inference bench — the PM or growth lead reads the platform dashboard at face value, i.e., ships the winner's curse, and (c) expensive traffic or expensive false-ships — mid-market e-commerce, consumer subscription, gaming, marketplaces. That is precisely the Eppo/GrowthBook/Statsig-cloud mid-market, one layer up. The purchase logic buyers recognize is not "predict my A/B tests" (a category the evidence base says nobody can honestly sell, and sophisticated buyers now correctly distrust — the persona-sim graveyard poisoned it) but two things that do have recognized shapes: **an audit** ("30% of your shipped wins were curses; here are the reversals" — reads like a pen-test / data-quality engagement) and **capacity relief** ("here's which backlog items are decidable from your own pilot exhaust, with a certificate and a 10–15% audit clause"). The audit is a beachhead with services economics and feature-absorption risk; the defensible residue is the sealed per-customer backtest certificate + abstention ledger, which platforms are structurally disinclined to ship because "we can't call 86% of your backlog" cannibalizes their run-more-tests business model. That misalignment is the actual moat, and it is real but narrow.

**Willingness-to-pay calibration.** Statsig sold to OpenAI (~$1.1B, 2025) and Eppo to Datadog on *platform/infrastructure* multiples — sticky, usage-priced, in the request path. Decision-layers price like analytics add-ons: 20–40% of the platform line they sit on. Mid-market experimentation ACVs run $30k–$150k; enterprise $200k–$500k. A defensible frame for this product: the audit as a fixed-scope entry ($25–50k, one-time-ish, "reverse your worst launch and it pays for itself"), converting to an annual subscription for the certificate + ledger + calculator priced against *avoided experiment cost* — if a customer runs 300 tests/yr at ~$5–15k fully-loaded each, certifying even 10% skips with the audit-clause discount supports $60–150k/yr on honest ROI math. Anything above $150k requires the tier-3 g-formula rung live at that customer, which is founder-gated and unproven commercially (customer-side coverage is, per E3-P's own limits, "an ownership argument, not a measurement").

**The brutal sentence:** the measured product is a discipline layer whose headline is what it *refuses* to say; companies sophisticated enough to value calibrated refusal mostly already employ it, and companies naive enough to lack it must be taught the category one audit at a time. That's a viable niche services-to-SaaS wedge, not an Amazon logo.

VERDICT: [Amazon-class pays: no — central experimentation-science orgs are the authors, not buyers, of this product's methods, and E3-P's 13.6% coverage / optimism-tying accuracy doesn't clear their internal bar; P(any Weblab-tier logo pays within 3 years) ≈ 3–5%]
ICP: [Head of Growth/Data at a mid-market consumer company (e-comm, subscription, gaming) with 100–1,000 tests of exhaust on Statsig/Eppo/GrowthBook and no staff causal-inference scientist — bought as a winner's-curse audit first]
PRICE: [Entry: fixed-scope past-wins audit $25–50k; expand: annual certificate + abstention ledger + post-pilot calculator at $60–150k/yr, priced as a fraction of avoided experiment cost, with $200k+ only after a live tier-3 feature-store engagement proves customer-side coverage]

---

### Lens: ds-skeptic

I read the paper, the joint debate conclusion, and the E1/E2/E3-P ledger. Here is the procurement verdict, written from the buyer's chair.

---

**DILIGENCE MEMO — hostile staff DS review**

**1. The measured headline disqualifies the pitch at our scale.** On the vendor's own sealed realistic backlog (E3-P, n=44): pre-launch coverage 0%, post-pilot coverage 13.6%, in-principle prevalence of pre-launch-decidable hypotheses 2.3%, and on the 6 cases it did call, directional accuracy 0.667 — exactly tying the "always assume the treatment wins" baseline, which is what our PMs do for free. The vendor concedes this in writing: "the calculator's value on this backlog is not beating PM optimism on direction." At Weblab volumes, a system that calls 2% of hypotheses pre-launch and matches PM intuition on the rest is a rounding error. Traffic is not our binding constraint; we can just run the test.

**2. Every proven engine is commodity to us.** The three engines the joint statement admits as proven are: two-proportion arithmetic over per-arm aggregate tables (E1), direct A/B estimates, and a g-formula mediation sim over a per-user feature store. My team teaches the first two to interns. Empirical-Bayes shrinkage for winner's curse — the tier-2 "wedge" — is literature we wrote (Lee & Shen, Coey & Cunningham, Azevedo et al. are cited *in the vendor's own paper*) and Microsoft EXP-style teams already automate it. The E3-P finding that "coverage was blocked by data logistics, not method" is the fatal admission for an Amazon sale: Weblab already has every per-arm aggregate, instrumented, joined, and warehoused. The vendor's priced data ask — "give us your pilot's per-arm export" — describes a problem we solved fifteen years ago.

**3. The LLM layer adds nothing we'd pay for.** The vendor's own sealed campaign proves the LLM contributes only translation/narration (E2 KILL: mechanism tags carry no sign information; N1–N5: every words-only and persona method at or below chance). So the differentiated-sounding part is disproven by the seller, and the working part is arithmetic.

**Steelman — what is genuinely good here, and can we clone it?**

- *Zero-sign-error discipline*: 0 confident-wrong across E1 (24/24) and E3-P (0/44 called wrong, 2 conservative under-calls). Real, but it's a verdict-admission *policy* (R1–R3: magnitudes measured-or-purchased, words never pick signs, sign stability under ensemble + flat-prior refit). Policy is reproducible. My team could implement the admission rules and the abstention ledger in a sprint; the conformal gating (Learn-then-Test) in a quarter.
- *Calibrated flat-calls and the abstain ledger*: the most honest artifact in the deck — 86% of abstains traced to a named missing table with a priced remedy. Good UX for a data-poor buyer. For us it's a dashboard our experimentation platform team would build as a feature.
- *Negative-control guard / winner's-curse audit on shipped wins*: validated on synthetic + Hillstrom, failed one naturally-confounded benchmark (single-NC), repair route (proximal double-NC) not yet run (E5 pending). We would not accept a guard with a known unrepaired failure mode on confounded exhaust — which is most exhaust.

**Is anything irreproducible?** Honestly audited: no *code or method* is. The only assets a sprint can't clone are (a) the sealed negative-evidence corpus — the measured proof that persona sims, LLM ensembles, and mechanism priors don't work, which is worth reading before some other vendor sells us exactly those, and (b) prospectively, a cross-customer library of measured (population, change, outcome) triples — but the factory's external validity is untested (E6 unrun; dissent 7 calls it "the council's largest shared exposure"). Diligence value, not license value.

**So who does pay?** The economics invert for a buyer who lacks what Amazon has. A company with 30–300 experiments of exhaust, no staff statistician, no automated shrinkage, PMs shipping winner's-cursed "wins" into roadmaps: for them, the tier-2 audit (recomputing past launch decisions with EB shrinkage + NC guard, reversing some) is day-one ROI they cannot self-serve, the zero-sign-error post-pilot calculator is a real second opinion, and the abstain ledger's priced data ask is a feasible afternoon of SQL, not an insult. The vendor's own joint statement already concedes this positioning ("the audit is the wedge; sales motion leads tier-2-first"). The threat there is Eppo/Statsig/Optimizely shipping shrinkage natively — the paper's own dissent 3 — so the sale must be the audit-plus-abstention *service* and trust sequence, not the statistics.

**Price logic.** What's actually bought: (1) a one-time portfolio audit of shipped experiments with reversal recommendations, (2) ongoing post-pilot verdicts with the zero-sign-error/abstain contract, (3) the EVOI data-quote surface. Benchmark against the alternative: a fraction of one senior experimentation data scientist ($250–400k loaded) or 1–2 reversed bad launches per year. That supports a $30–60k audit entry and $50–150k/yr platform for the mid-market ICP. It does not support a seven-figure enterprise deal anywhere the buyer employs the people who wrote the citations.

---

VERDICT: [Amazon-class pays: no — every proven engine is commodity in-house, coverage is blocked by data logistics Amazon solved long ago, and called accuracy ties the free PM-optimism baseline; probability of a paid Amazon-class deal ≈ 3–5% (and then only as an acqui-hire or negative-evidence consult, not a license).]
ICP: [Mid-market product companies (~30–500 experiments of A/B exhaust, no dedicated experimentation-science team) buying the winner's-curse audit of past shipped wins first, with post-pilot zero-sign-error verdicts riding along.]
PRICE: [A $30–60k fixed-fee portfolio audit as the entry, expanding to $50–150k/yr for the ongoing audit + post-pilot verdict + abstention-ledger service — priced against a fraction of one experimentation data scientist or one reversed bad launch, never as a prediction oracle.]

---

### Lens: economic-buyer

All grounding read. Here is the verdict.

---

**The honest inventory of what's sellable.** Measured, the product delivers: (1) a post-pilot arithmetic calculator with a zero-sign-error record (E1 24/24; E3-P 6 wild calls, 0 confident-wrong) but 13.6% coverage on public artifacts and ~2.3% strict pre-launch prevalence; (2) a winner's-curse/EB audit of past A/B exhaust; (3) calibrated abstention plus a priced data ask. Critically, on the called set the calculator only *tied* PM optimism directionally (0.667 vs 0.667). So you are not selling accuracy uplift. You are selling **insurance on the 39%** (the false-ship tail of a 61%-right optimism base rate), **test-slot compression** (pilot→full-test extrapolation, the Hillstrom 3/4+1-flat regime), and **decision-reversal on past wins** (the audit). Price against those, or the buyer's data-science team will shred the deck.

**(a) Amazon-class, ~100k tests/yr — NO.** Three independent kills. First, *marginal cost of truth*: Weblab makes running the test nearly free relative to their scale; when the experiment itself costs a rounding error, "skip the knowable test" has near-zero EVOI — the cheapest measurement is the test. Second, *they already own the counter-tech*: the winner's-curse and EB-shrinkage literature (Coey, Deng, Kohavi-adjacent) is written by their staff or ex-staff; the tier-2 audit is ~internal-tools work for one applied scientist, and your own dissent 3 concedes platforms can ship EB shrinkage natively. Third, *procurement physics*: a zero-egress warehouse app still can't clear Amazon security review faster than an internal replication. Best case is a research citation or acqui-hire conversation, not ACV. Even a 1bp EBITDA argument fails because the counterfactual (build it in a quarter) dominates buy.

**(b) Mid-market, 50–500 tests/yr, Statsig/Eppo customer — CONDITIONAL, and this is where the math barely clears.** Take 200 tests/yr, fully loaded ~$25–50k per test (eng+PM+DS+calendar) → a $5–10M experimentation program. Value levers: the audit plausibly reverses 1–3 curse-inflated "wins" a year (each a shipped regression or misallocated roadmap bet worth $100k–$1M in a $50–500M revenue company); flat-call discipline on the 39% wrong-optimism tail deters a couple of false ships; prioritization/EVOI ranking reclaims a handful of slots. That's a defensible $150–600k of annual value → supports a **$50–150k ACV at a 3–5x value multiple**. Two brutal caveats: coverage at 13.6% means ~86% of their decisions still require the test, so this is a *supplement*, never a platform-replacement budget line; and the audit wedge is copyable by their existing platform vendor — your moat is the sealed per-customer backtest + audit-clause certificate machinery, which Eppo won't build because it caps their own "we found you winners" narrative. That conflict-of-interest is your actual defensibility.

**(c) Test-scarce, <50 tests/yr — the pain is real, the product fit is partial.** Here each test is 6–8 weeks of scarce traffic; a slot is worth $50–200k of opportunity cost, and a false ship isn't caught by the next test because there isn't one — the asymmetry is maximal. Pilot-extrapolation (call the full-test outcome from a 20% pilot's per-arm export) is genuinely worth money: compressing five 8-week tests to 2-week pilots frees ~30 weeks of roadmap. But your own certificate floor (~30 resolvable non-null experiments) means many of these companies **can't reach certified status** — they get "triage, no guarantee," which is honest but hard to price above $30–60k. And E3-P's customer-side coverage remains an ownership *argument*, not a measurement.

**Where EBITDA actually moves.** Winner's-curse correction moves EBITDA at (b) — enough exhaust to audit, enough revenue that a reversed bad launch is six figures. Test-prioritization/skipping moves it almost nowhere pre-launch (2.3% prevalence — the paper's own number kills that pitch). Pilot-extrapolation moves it at (b) and (c) where traffic is the binding constraint. The 61% base rate cuts both ways: optimism being right 3-in-5 means "we predict your tests" is a weak product, but 2-in-5 wrong launches at $100k+ apiece means "we catch your bad ships and never sign-err doing it" is a real one.

**The uncomfortable core.** Nobody on Earth pays to "improve A/B test accuracy" as stated — the test *is* the accuracy. They pay to (i) un-ship past false winners, (ii) shorten expensive tests, (iii) not ship the 39%. The evidence supports exactly those three claims and no others. Sell prediction and a competent buyer's DS team will run your E3-P table back at you.

VERDICT: Amazon-class pays: no — near-zero marginal test cost plus in-house winner's-curse authorship makes build-vs-buy a rout; P(paid ACV within 2 years) ≈ 5%.
ICP: Traffic-constrained mid-market product companies (B2B SaaS, fintech, marketplaces, $50–500M revenue, 50–300 tests/yr on Statsig/Eppo, 1–5 data scientists) whose platform vendor is conflicted out of auditing its own declared winners.
PRICE: Land at $30–50k for the A/B-exhaust winner's-curse audit (one-time, data-grant Trojan horse), expand to $75–150k/yr for the sealed-backtest certificate + post-pilot calculator + audit-clause skip program — framed as 20–30% of the value of reversed false ships and freed test slots, never as prediction accuracy.

---

### Lens: gtm-strategist

All four grounding files read. Here is the verdict.

---

**The brutal read of the evidence first.** The product, as measured, does not beat a PM's gut on direction — E3-P says called accuracy (0.667) exactly ties "always treatment wins" on the called set, and optimism is already right 61% of the time. What the evidence actually supports selling is three narrower things: (1) zero-sign-error post-pilot arithmetic with calibrated abstention, (2) a winner's-curse audit of past A/B exhaust that reverses launch decisions with pure computation, and (3) a priced, itemized data ask (EVOI quote) for everything it refuses to call. That is a *statistical conscience*, not an oracle. Who pays for a conscience? Organizations where a wrong ship is expensive, traffic is scarce, and there is no in-house experimentation-science team. Score Amazon against those three conditions.

**Amazon fails all three.** Weblab exists precisely because traffic is not scarce at Amazon; the marginal cost of just running the test is near zero for most surfaces. Amazon-class platform teams (Amazon, Microsoft, Meta, Airbnb, Booking) employ the people who *wrote* Lee & Shen, Coey & Cunningham, Azevedo et al. — the tier-2 audit is a shrinkage estimator their platform can ship natively (the paper's own dissent §9.3 concedes this). And the tier-3 rung requires feature-store access or warehouse-native deployment inside a company whose security review alone outlasts a seed company's runway. The honest wildcard is the one the question names: Amazon has test-starved corners (new-country launches, Pharmacy, B2B verticals, physical retail, email/push where sends are capped). But those corners still sit behind Weblab's org, central procurement, and a culture that builds. A single-BU landing is a 12–18-month enterprise motion with ~5% odds — for a seed-stage company that is a distraction, not a lighthouse. Amazon's correct role in this GTM is **alumni pipeline**: the ex-Weblab/ex-Microsoft-ExP data scientist who lands at a mid-market company *is* your champion, because they know the winner's-curse math is real and know their new employer can't build it.

**The honest wedge, sequenced.** Land with the **tier-2 exhaust audit** as a fixed-fee artifact: "send the CSV of your last 30+ resolved experiments; we'll tell you which of your celebrated wins were winner's-curse mirages and which shipped losers you can reverse." Zero prediction risk, zero egress fight, day-one ROI, and contractually it *is* the data grant. Convert to the **ongoing watchdog subscription**: every future "win" gets a CONFIRMS / CONTRADICTS / CAN'T-VALIDATE stamp before launch review, plus the post-pilot calculator (zero sign errors in the wild, per E3-P) riding along once the frozen per-arm export exists — E3-P showed 86% of abstains are a missing export, not a missing method, and a real customer owns their own pilot tables. Top rung is the **decision console**: warehouse-native tier-3, selective pre-test calls on the slice the g-formula proves out (12/12 on magnitude flips), abstention ledger, priced micro-study quotes. Sell it as "never ship a sign-error again and know exactly what each unanswerable question costs to answer" — never as prediction accuracy, which the evidence cannot support.

**First 10 logos, by archetype** (each: 30+ experiments of exhaust, expensive tests, no stats bench):
1. Mid-size mobile-gaming studio (Cookie-Cats-class; LTV decisions, monetization/retention trade-offs — the measured magnitude-flip regime).
2. Subscription consumer app (fitness/meditation/language) with capped install volume — every test burns scarce cohort.
3. DTC e-commerce brand, $100–300M GMV, burned by CRO-agency "wins" that never showed in revenue — the audit is a revenge purchase.
4. Email/CRM-heavy retailer (Hillstrom-shaped): sends are the scarce resource; per-arm aggregates already exist.
5. Regional marketplace scale-up with thin-traffic supply side.
6. Consumer fintech where each experiment is compliance-gated and slow.
7. Regional streaming/OTT player fighting churn with small test cells.
8. B2C edtech with seasonal traffic (can't rerun a failed semester test).
9. Insurance/telco digital arm: enormous revenue per decision, tiny digital test traffic, big warehouse — ideal zero-egress buyer.
10. PE portfolio-operations team — one audit contract, replicated across 8 portfolio companies; the multiplier account.

**Ladder economics.** Audit report $25–60k fixed. Watchdog subscription $60–150k/yr (priced against one reversed launch decision — a single winner's-curse rollback typically dwarfs the fee). Console (tier-3) $150–400k/yr at the top of mid-market. The Amazon-class endgame, if any, is entering years later through archetype 9 or an acquired subsidiary — after per-customer sealed backtests exist as reference collateral — or, more likely, exit-by-acquisition when an experimentation platform (Eppo/Statsig/Optimizely class) wants the audit + abstention layer they didn't build.

VERDICT: Amazon-class pays: no — they have free traffic, in-house winner's-curse authors, and build-culture; the only entry is a single test-starved BU years out, and chasing it now is a distraction (P(meaningful Amazon-class contract within 3 years) ≈ 5%).
ICP: A traffic-scarce, exhaust-rich mid-market B2C company (mobile gaming, subscription apps, DTC/CRM retail, insurance-digital) with 30+ resolved experiments, no experimentation-science team, and a recent expensive false win — often championed by an ex-big-tech-platform data scientist.
PRICE: They buy a fixed-fee winner's-curse audit of past A/B exhaust ($25–60k) converting to an ongoing pre-launch watchdog + selective-verdict subscription at $60–150k/yr (tier-3 console $150–400k/yr), priced against the cost of one reversed bad launch, not against prediction accuracy.

---

### Lens: red-team

**RED TEAM: the case that nobody pays**

**1. The sellable slice is a rounding error, and on it you tie the coin the PM already flips.** E3-P is the product's own measurement: 2.3% of a realistic backlog is pre-launch decidable; 13.6% post-pilot; and on the called set, accuracy (0.667) exactly ties "the treatment wins" — the null strategy of just shipping. PM optimism is right 61% of the time for free. The pitch has already retreated from "we predict your tests" to "we never sign-err and we abstain honestly on the 86–98% we can't call." That is a statistics hygiene property, not a line item. You cannot invoice a company for the tests you refused to predict.

**2. Sophisticated buyers self-serve.** Everything in the tier-2 wedge — empirical-Bayes shrinkage, winner's-curse correction, false-discovery portfolios — is published (Lee & Shen 2018, Azevedo et al. 2020, Coey & Cunningham 2019). Amazon didn't just read this literature; its alumni network wrote it. Weblab has internal meta-analysis teams, and Microsoft/Booking/Airbnb ship shrinkage in-house. For Amazon specifically, add: data egress is a non-starter, procurement for a statistics vendor against a 200-person internal science org is a joke, and the one thing they'd want (the g-formula's 12/12 on magnitude flips) requires the feature-store access they'd sooner replicate than grant. Amazon-class is not a customer; it's a competitor's recruiting pool.

**3. Unsophisticated buyers don't feel the pain.** Winner's curse presents as success: metrics went up, the launch email went out, the promotion cycle closed. The audit's deliverable is "your celebrated wins were partly noise" — a product whose core output indicts the buyer's past decisions and whose champion is the person it embarrasses. Painkillers sell; this is a diagnosis of an asymptomatic disease delivered to the patient's ego.

**4. The honest product mostly says "I don't know."** The abstain ledger is scientifically the finding and commercially the demo-killer. A prospect uploads 40 hypotheses; the product calls one, flat-calls two, and hands back 37 priced data-asks. The EVOI quote reframes abstention as a sales surface, but the first-session experience is a vending machine that returns your coin with a note explaining why.

**5. Platforms kill the standalone.** Statsig/Eppo/GrowthBook own the exhaust, the pipeline, and the PM's screen. Shrinkage and curse-audits are a quarter's roadmap for them, shipped free as retention features. The paper's own dissent 3 concedes this. A standalone whose wedge is a feature of the incumbent's data plane is a company-shaped feature request.

---

**Adjudication: fatal vs repairable**

- **(1) Small slice / ties optimism — fatal for the prediction framing, already conceded.** The joint statement pivoted to "audit is the wedge; selective prediction is the product." The residual risk is drift back into prediction marketing; the guardrail exists. Repairable *because the team already repaired it.*
- **(2) Sophisticated self-serve — fatal only for the top of market**, which was never the ICP. Below Amazon/Meta/Microsoft, the "known statistics" are known the way lint rules are known: nobody runs them. Repairable by ICP selection.
- **(3) No felt pain — the genuinely fatal one.** It attacks demand itself, not delivery. Every other objection assumes a buyer exists. The only repair is making the curse dollar-denominated and forward-looking ("this shipped win will miss its annualized projection by $X — here's the cheap holdout that proves it"), converting embarrassment into budget defense. Unvalidated: zero evidence yet that anyone converts on this.
- **(4) Abstention UX — repairable.** Package as pipeline triage + priced measurement quotes; the pilot-first mode (post-pilot calculator on owned per-arm exports) plausibly lifts coverage far above 13.6% — but that number is an *ownership argument, not a measurement* (E3-P Limits). Repair is claimed, not shown.
- **(5) Platform commoditization — serious but survivable on a clock.** Platforms optimize for running tests, not refusing them; a curse-audit that tells customers to run fewer tests is mildly counter-positioned to their pricing. But this buys 18–24 months, not a moat. The durable moat, per the evidence, is only the tier-3 g-formula regime plus per-customer sealed backtests — which requires surviving long enough to earn that data grant.

**Net:** (3) is fatal-unless-disproven; (5) sets the clock; (1),(2),(4) are handled or handleable. Amazon is the wrong question — the product's own E3-P data says the value is zero-sign-error triage plus a priced data ask, which a company with infinite internal statisticians values at zero.

**The single piece of evidence that would most change my mind:** one design partner's *measured* customer-side Arm-B coverage — their real backlog, their owned per-arm pilot exports — showing ≥40% coverage with zero confident-wrong, **plus one documented decision reversed or test skipped that the buyer valued above the fee** (renewal or expansion as the receipt). That converts the ownership argument into demand evidence and kills objection (3) or confirms it. It is exactly the founder-gated measurement E3-P's Limits section says is missing.

VERDICT: [Amazon-class pays: no — they wrote the literature, run it internally at Weblab scale, and will not egress data; P(pay) ≈ 3%; the conditional version (any F500 with a central experimentation org) is still <10%]
ICP: [Mid-market e-commerce/marketplace/subscription companies (~30–300 experiments/yr of exhaust, no staff experimentation scientist, real unit-economics stakes per launch) entering through a winner's-curse audit of past shipped wins]
PRICE: [A $15–25k fixed-fee exhaust audit (priced against one reversed launch decision) converting to a $60–120k/yr selective-verdict subscription priced at ~10–20% of the traffic/eng-weeks saved on certified skips — defensible only after the design-partner coverage number exists]

---
