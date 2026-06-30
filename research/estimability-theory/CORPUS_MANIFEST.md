# Corpus Manifest — can the validation corpus be assembled, or must it be manufactured?

*From the `corpus-hunt` workflow (5 agents, 4 channels, 39 dataset records). The adversary's one
condition for the whole research program to be non-theater was: assemble ~hundreds of exchangeable
real per-user A/B interventions with covariates and withheld directional truth. This is the answer.*

## Verdict: hundreds is UNREACHABLE from public data — the bulk must be MANUFACTURED

- **Honest public ceiling:** ~**8–12 distinct experiments** meeting the hard requirement (row-per-user
  microdata + treatment + outcome + pre-treatment covariates + known/published sign), expanding to
  ~**15–25 intervention contrasts** if factorial arms count separately.
- **Counter-intuitive subset** (the cases that actually discriminate a prediction engine): just
  **~3–5**, several of which fail a *different* criterion (Cookie Cats has no covariates;
  Orange-Belgium covariates are PCA-anonymized).
- **Gap to "hundreds":** ~an order of magnitude — and *wider* than the raw count, because the public
  cases are **non-exchangeable** (charity mailers + voter GOTV + telecom churn + grocery SMS are not
  one population) and their withheld truth is **leaky** (anyone can recompute the sign from the RCT).
- The dominant "uplift-modeling canon" (Criteo, Lenta, X5, Megafon, Starbucks) is mostly **single-
  experiment** with **trivially-positive** signs (ads/emails/contact help — the naive prior is also
  right), so it is a **weak** counter-intuitive test. The real product-experiment literature (ASOS,
  Upworthy, Booking/Netflix/LinkedIn, the JMR/MktSci canon our 14 cases cite) is structurally
  **aggregate-only or NDA-locked** — which is exactly why we only ever had Hillstrom + Cookie Cats.

**This scarcity is itself the strategic finding**: it is the affirmative, literature-grounded case
for a **made-to-order BenchmarkCase factory** (the Senu→Sidira #222 feeder thesis), because a factory
can mint cases that are exchangeable, counter-intuitive *by construction*, covariate-rich, and with a
*genuinely sealed* (non-leaky) truth — none of which the public corpus offers at scale.

## But it also found real anchors we weren't using (turnkey, free, downloadable now)

This roughly **triples the real-RCT anchor set** (from 2 → ~13–18 contrasts) — not hundreds, but
enough to test **floor-transfer across multiple held-out real RCTs** (falsifiable prediction #5) and
to directly answer the adversary's "n=1 is a coincidence until shown on a dozen."

| Dataset | n | Why it matters | Access |
|---|---|---|---|
| **Hillstrom** (have) | 64k | 2 arms; real named covariates; documented spend/ad-aversion inversion | sklift, free |
| **Karlan-List 2007** charitable match | ~50k | canonical **counter-intuitive NULL** (3:1 match buys nothing over 1:1) + red/blue heterogeneity | openICPSR 113224 / Dataverse 10.7910/DVN/27853 |
| **Bertrand et al. 2010** S．African lender | ~53k | **~8 orthogonally-randomized content features**, counter-intuitive signs (photo-of-a-woman ≈ 25% rate cut) — best multi-intervention source | Dataverse 10.7910/DVN/II4HDS |
| **Gerber-Green-Larimer 2008** GOTV | ~344k | 4 mailer arms; large social-pressure effect; real covariates | ISPS Yale d001, free |
| **Orange-Belgium** churn (Verhelst 2023) | — | rare real **sign-backfire** (retention outreach *raises* churn) | OpenML 45580 (CC-BY-NC-ND) |
| **Information-R** insurance | — | 68 covariates; positive lift with net-negative WOE subgroups | CRAN, free |
| **Cookie Cats** (have) | 90k | clean counter-intuitive product change; **no covariates** (sign-only) | Kaggle |

## The program, now concrete (corpus-first, three lanes)

1. **DOWNLOAD NOW** (turnkey): the ~13–18 real contrasts above. Run the causal estimator +
   negative-control guard on each → test **floor-transfer on multiple held-out real RCTs** (turns the
   empirical core's validation from n=1 real toward n≈6 real). *This is the single highest-value
   runnable follow-up — it attacks the adversary's strongest critique directly.*
2. **CURATE (opportunistic, low hit-rate):** mine J-PAL/IPA + AEA/openICPSR for field experiments
   with deposited individual-level data — but most deposits are aggregate or PII-gated and skew
   off-domain, so treat as opportunistic, **not** the path to hundreds.
3. **MANUFACTURE (the real path to hundreds):** the Senu made-to-order BenchmarkCase factory —
   exchangeable, row-per-user cases with named pre-treatment covariates, an outcome **with variance**
   (not a ≥1 binary ceiling — the Beat-the-Clock lesson), and a **sealed counter-intuitive** truth,
   feeding predicted-vs-actual pairs into the #222 conversion_calibrator. The ~13–18 real contrasts
   become the **realism-anchor set** that validates the factory before its synthetic-but-grounded
   cases scale to the hundreds the risk-coverage curve needs.

## Bottom line
The adversary asked for hundreds of real exchangeable cases. They do not exist publicly and cannot be
bought — proven, not asserted. The corpus must be **manufactured**, which is precisely the Senu feeder
thesis. The consolation is real and immediate: ~6 new real RCTs that take the empirical core from one
real anchor to several, runnable this week with no manufacturing.
