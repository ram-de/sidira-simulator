# Moat Construction + The Amazon Question

**2026-07-01 · Follow-up to BUYER_VERDICT.md** (joint finding: "the moat does not exist yet; it must be earned customer by customer"). This memo is the constructive answer: what to build so it exists, and what "buyable by Amazon" can realistically mean.

> **FOUNDER DECISION 2026-07-01 (overrides parts of this memo — see addendum at bottom):**
> Senu is an **internal data factory only — no customer-facing measurement SKU**. Sidira is **solely a product that helps design and prioritize hypotheses worth testing**. The founder runs studies internally to improve the model; **the moat = the paired corpus (hypothesis, panel-measured shift, real outcome), surfaced through a calibrated hypothesis-worth model** — never a sign oracle. Layer 2 below is amended from "measurement supply chain SKU" to "internal factory feeding layer 1"; tier-1.5 quote language in the paper is retired as a product concept.

## Part 1 — The four moat layers, ranked by defensibility

The debate established that method is not a moat here (calculator ≈ 50 lines, shrinkage is published, abstention is a sprint). What compounds:

### 1. The certificate corpus — the only data-network-effect asset (THE moat)
Every sealed audit produces measured (population, change-type, outcome, receipt) triples and a hash-sealed backtest certificate. At N customers, the calibration priors, base rates by change-type, and abstention thresholds are fit on evidence no competitor or internal DS team possesses — an internal team can clone the math but starts at corpus size 1 (themselves).
**Build actions:** (a) contract clause from audit #1 granting rights to retain anonymized, abstracted triples + calibration parameters (legal review before the first pitch — retrofitting this is 10× harder); (b) **run E6 early** — the corpus only compounds if triples transfer across customers, and transport is currently "the council's largest shared exposure"; (c) design the triple schema now so audit #1's output is corpus-ready, not a PDF.

### 2. Senu — the proprietary measurement supply chain
No experimentation platform owns a human-panel factory that can price and deliver a missing Δmediator measurement. The EVOI quote ("we abstain; this $X measurement unlocks the call") is only defensible if we can actually fulfill it — platforms can copy the audit math; standing up a verifiable-reward panel factory with payment rails, quality scoring, and HMAC-verified completions is a different company. This converts the product's biggest weakness (abstention) into its purchase path.
**Build actions:** E6 transport pilot gates everything here; until then Senu quotes stay "experimental — external validity unproven" per the tier-1.5 rule.

### 3. The sealed-certification brand — the ratings-agency position
Certifiers (UL, S&P, SOC 2 auditors) moat on *independence + track record*, not method. We already run sealed preregs, fingerprinted truths, recorded deviations — internally. Productize the discipline: customer-facing, third-party-verifiable certificates (hashes published, methodology public), plus the **negative-evidence corpus** as the trust anchor — we are the vendor that measured our own persona-sim idea to death and published it. Every "AI agents simulate your users" competitor pitch becomes our sales asset.
**Build actions:** publish the accuracy whitepaper (honest-null framing, already planned — publish the *measurement* methodology, conceal the calibration corpus); make certificate verification public (a hash registry page); write the anti-pitch into every surface.

### 4. The frozen export schema as an open standard + switching costs
Open-spec the tier-1 per-arm export schema (E3-P measured that the missing table, not the method, blocks 86% of post-pilot calls — whoever owns the interface owns the funnel). The certification + corpus layer on top stays proprietary. Per-customer, the accumulated decision ledger (every call, abstention, receipt) is history a rival restarts from zero.
**Build actions:** publish the schema with the whitepaper; ship the in-warehouse validator as the free artifact that seeds audits.

**The clock:** platforms (Statsig/Eppo) can ship shrinkage + curse-audits natively in 18–24 months. The race is corpus + demand receipts before that — which is why the 3–5 paid audits are simultaneously the demand test AND the moat's first bricks.

## Part 2 — Three real doors into Amazon (and the one fake one)

**The fake door:** selling internal A/B accuracy to the central org. P ≈ 5%, overdetermined kill (they authored the fix; build-vs-buy; procurement). Spend zero energy here.

**Door 1 — AWS as channel, not Amazon as customer (nearest-term).** List the zero-egress audit/watchdog on AWS Marketplace (product runs in the customer's warehouse — the architecture is already the pitch). "Amazon pays" inverts into "Amazon takes a rev-share to sell us": AWS wants workloads, co-sell motion exists for exactly this shape, and mid-market ICP #1 already lives there. Realistic in year one; also the cleanest procurement path into any enterprise later.

**Door 2 — certify Amazon's *ecosystem*, where Amazon structurally cannot self-certify (the strategic door).** Independence is the one thing an internal team can never build:
- **Ads incrementality:** advertisers don't trust Amazon grading its own ad-measurement homework. An independent, sealed incrementality certificate makes Amazon's ads *more sellable* — Amazon has paid for third-party measurement before (Nielsen/DoubleVerify pattern) because external verification increases ad revenue.
- **Marketplace sellers/brands:** millions of SMB sellers run pseudo-experiments (pricing, listings, creatives) with no Weblab access. A seller-facing decision-audit layer is a product Amazon could embed or resell — Amazon as distribution to the exact DS-poor segment we already target.
This door requires the certification brand (moat layer 3) to exist first; it is a year-2/3 motion.

**Door 3 — test-starved BUs + the acquisition tail.** Amazon is not one buyer: hardware/Alexa (slow cycles), new international marketplaces, physical stores, B2B (Amazon Business) are traffic-scarce corners where each test is expensive and pilot-extrapolation + EVOI matter — entry via one BU champion (ideally a Weblab alumnus), never via central. And the honest endgame both councils flagged: if the corpus + factory + certification standard become real across mid-market, the Amazon-class outcome is **acquisition of the corpus and the standard**, not a license. Being acquirable = clean IP on the corpus rights (moat action 1a), the factory, and an independent brand worth owning.

## Sequencing (what I'd do in the next 90 days)

1. Draft the corpus-rights contract clause + triple schema (moat 1) — before pitch #1.
2. Sell the 3–5 audits (demand test = moat bricks; unchanged from BUYER_VERDICT).
3. Run **E6 next instead of E5** — both moat layers 1 and 2 are gated on transport; E5 (watchdog repair on confounded exhaust) slots in behind it. *(This is a proposed change to the joint experiment order — founder call.)*
4. Publish the whitepaper + open export schema + public certificate registry (moat 3+4).
5. Start AWS Marketplace listing paperwork (door 1) — long lead time, zero strategic risk.
6. Amazon ecosystem/BU doors: dormant until ≥5 certificates exist. Revisit at the first renewal.

---

## Addendum — Founder decision (2026-07-01) and the reshaped experiment queue

**The decision.** No Senu SKU; no selling studies. Product identity: **hypothesis design + prioritization for experiments** ("which of your 100 ideas deserve your 12 tests' worth of traffic, and why"), with the audit retained as an entry artifact (it is the data grant and the source of loser/flat labels, not the identity). The moat, stated precisely: **the paired corpus is the moat; the model is its interface.** Paired records of (hypothesis, Senu-measured behavioral shift, real experiment outcome) are unpurchasable — platforms have outcomes without measurements, panel companies have measurements without outcomes. Studies run internally under the already-locked §11 calibration contract (Senu emits role-named arms; Sidira predicts blind; outcomes carry variance).

**Model guardrails (binding, from the evidence base).** The model is a **calibrated hypothesis-worth scorer** — P(direction) with calibrated uncertainty, effect-size posterior, EVOI, power requirements, call/abstain — never an outcome oracle (six negative results; N5 trap: a model trained on public A/B lore learns publication bias and is confidently wrong exactly on the counter-intuitive slice). E2 ban carries into the learned pipeline: no mechanism-tag→sign pathways; tags remain uncertainty/coverage bookkeeping only. Zero-confident-wrong admission rule intact. **Ship gate: the model touches a customer only after beating the calculator + the six-baseline set under seal on decision economics** (false-ship/false-kill/regret at useful coverage), per debate resolution #4.

**Known risks accepted with the decision:** slow corpus growth (dozens–hundreds of pairs in year one → hierarchical priors by change-type bucket, not deep learning; interim revenue stays on the deterministic layer); transport risk goes silent inside the model (so every internal study carries a sealed blind prediction vs measured outcome — E6 discipline internalized); selective labels (customers only test what they like → audit exhaust keeps feeding losers/flats).

**Reshaped experiment queue (supersedes the DEBATE_CONCLUSION.md joint order, which is preserved as the historical record):**

1. **Internal study cadence = the new E6 (starts as soon as Senu ops launch — still founder-gated on deploy/KYC/panel).** Every study: sealed blind prediction → measured outcome → paired triple into the corpus. The first studies ARE the transport validation; no customer-facing language is gated on it anymore — model feature admission is.
2. **E5 — proximal double-NC** (unchanged): the audit wedge needs the watchdog working on naturally confounded exhaust.
3. **E4 — abstention gate** (unchanged), now also the calibration layer for the hypothesis-worth scores.
4. **E3-P follow-up — design-partner Arm-B coverage measurement** (unchanged; the demand-side number).
5. **E7 — the hypothesis-worth model**, redefined per the guardrails above; trained on paired corpus + audit exhaust; runs only when the corpus clears a pre-registered n-floor per change-type bucket; evaluated under seal against calculator + six baselines on decision economics.
6. **Product surface (buildable now, deterministic layer):** estimand labels, instrumentation/power preflight, EVOI ranking of the backlog, abstention ledger — the hypothesis-design console that the model later slots into.
