# X5 RetailHero Heterogeneity — RICH Behavioral Covariates (follow-up to the X5-thin miss)

**Question.** The X5-thin run missed (Spearman rho **+0.163**, perm p 0.52, FAIL).
Its diagnosis blamed *covariate poverty* — segments built only on demographics
(age/gender/tenure). **Does swapping in RICH PRE-TREATMENT BEHAVIORAL covariates
(purchase-history RFM) on the SAME dataset and SAME RCT ground truth recover the
"who-responds-more" ranking?**

**Discipline.** Pre-registered before any model call
(`PREREG_X5_RICH.json`, SHA `9fe33eec…`; SHA-pinned ground-truth vector
`3f5b2d55…`). Single run, temperature 0.0, no peeking, no re-tuning, no segment
re-selection after seeing predictions. Method mirrors
`x5-benchmark/forecaster_x5.py` and `hillstrom-benchmark/forecaster_powered.py`.
Result SHA verified to match the pre-registered ground truth.

## Headline

| Metric | **X5-RICH (this)** | X5-thin | Hillstrom (certified) |
|---|---|---|---|
| Covariates | purchase-history RFM | demographics | gender×recency×email |
| # segments | 26 (1 dropped <200/arm) | 18 | 38 |
| Spearman rank-rho | **−0.161** | +0.163 | +0.42 |
| Permutation p (5000, \|rho\|) | **0.428** | 0.520 | <0.05 |
| Kendall tau-b | −0.086 | +0.120 | — |
| Direction accuracy (sign vs 0) | 0.923 | 0.944 | — |
| Pre-registered bar (rho>0.30 AND p<0.05) | **FAIL** | FAIL | PASS |

## Verdict — RICH COVARIATES DID NOT RECOVER THE RANKING (and slightly INVERTED it)

The covariate-poverty hypothesis is **not supported**. Giving the blinded
forecaster genuinely rich, pre-treatment behavioral features (recency,
frequency, monetary, basket size, category breadth, redeem share) did **not**
move the ranking from "weak positive non-replication" toward the Hillstrom
+0.42. It moved it the *other* way: rho went from **+0.163 → −0.161**, i.e. the
predicted order is now mildly *anti-correlated* with the real per-segment uplift.
The result is still **indistinguishable from chance** (perm p 0.43), so the
honest reading is "no recoverable rank signal," with a hint of a wrong-direction
prior. The pre-registered bar is failed on both halves.

This is exactly the **counter-risk that was pre-registered**: that the model
would apply a naive "engaged / high-value customers respond more" prior, which
is the *opposite* of the truth in this dataset.

## Why it inverted (honest diagnosis, from the prediction trace)

The real ground truth has a clear **ceiling / headroom** structure:

- The **largest** real uplifts are **low- and mid-monetary** segments with
  mid frequency — e.g. `R-mid/F-mid/M-low` **+0.0737**, `R-high/F-mid/M-low`
  **+0.0687**, `R-high/F-low/M-low` **+0.0471**. Under-engaged, lower-spend
  loyalty members have the most room for an SMS to move them.
- The **smallest / negative** real uplifts are **high-monetary, high-frequency**
  segments — `R-high/F-low/M-high` **−0.0057**, `R-mid/F-low/M-high` −0.0015,
  `R-low/F-high/M-high` +0.0041, `R-high/F-high/M-high` +0.0043. Heavy, high-spend
  shoppers are already near their purchase ceiling; the SMS barely moves them.

The forecaster bet the opposite way on the dominant axis. It read **monetary
value and lapsed-recency as responsiveness signals**: its top predictions
(+2.8pp) went to high/mid-monetary, longer-recency-gap segments
(`R-high/F-low/M-high`, `R-high/F-mid/M-high`, `R-high/F-mid/M-mid`), and its
lowest (+0.8pp) went to recent, high-frequency shoppers (`R-low/F-high/*`,
`R-mid/F-high/*`). That is a defensible *marketing-intuition* prior ("win back
lapsed high-value customers; loyal regulars don't need a nudge"), but in this
RCT the real winners are the low-spend mid-frequency group, so the prior points
the wrong way. Predictions also remained **low-variance / saturated** (only five
distinct values: 0.8, 1.2, 1.8, 2.1, 2.8), echoing the thin run's flat-prediction
failure mode and capping any achievable |rho|.

## Three-point comparison (the actual point of this run)

- **Hillstrom +0.42 (rich behavioral covariates) — generalized? NO.** It was the
  *original* certification, not an independent replication. It used
  gender×recency×email-creative on a US apparel retailer.
- **X5-thin +0.163 (demographics) — FAILED.** First independent RCT; weak
  positive, p 0.52. Diagnosis: blamed thin demographic covariates.
- **X5-rich −0.161 (purchase-history RFM) — FAILED, mildly inverted (THIS).**
  Same dataset, same RCT ground truth, genuinely rich pre-treatment behavioral
  features. **Richness did not rescue it.**

**Does behavioral richness recover the ranking? NO.** The two X5 runs now
*bracket zero* (+0.163 and −0.161), both well inside the chance band (p 0.52 and
0.43). The most parsimonious conclusion is **not** "X5 needs richer features" —
it is that on X5 the blinded Sonnet forecaster has **no reliable rank signal for
who responds more**, regardless of whether segments are demographic or
behavioral. The Hillstrom +0.42 looks increasingly like a dataset-specific
result that does **not** generalize across either feature regime tested on X5.

## What is — and isn't — comparable

- **Same dataset, same RCT, same treatment, same target, same bar, same model,
  same forecaster framing** as the thin run — the ONLY deliberate change is the
  covariate set (demographic → behavioral RFM). So this is a clean A/B on the
  covariate-poverty hypothesis, not a domain swap.
- **More segments (26 vs 18)** and a genuine 3-way RFM interaction — a *harder*
  rank task, but also a richer real signal (uplift spans −0.006..+0.074), so the
  ceiling structure is clearly present in the ground truth for the model to find.
- **Single model (Sonnet), single temperature-0 run** — same power budget; no
  ensembling, no re-tries after seeing rho.

## Limits (do not over-read)

- **Pre-treatment cutoff = 2019-02-19 is an assumption.** purchases.csv.gz has
  no explicit treatment-date column. History spans 2018-11-25..2019-03-18; the
  documented SMS window starts 2019-02-19, so features use purchases strictly
  before that. 32.6M of 45.8M purchase rows (71%) are pre-cutoff; 13.2M post-cutoff
  rows were dropped from features. If the true SMS dates differ per client, some
  features could be slightly contaminated — but contamination would tend to
  *help* the model, not hurt it, so it does not explain the inversion.
- **190,099 of 200,039 uplift_train clients matched a feature record** (95%);
  9,940 clients with no pre-cutoff purchase were excluded from segmentation.
- **One cell dropped** for the n≥200/arm floor (`R-high/F-high/M-low`, 117T/102C);
  no silent truncation.
- **Single model, single run, 26 segments, perm p wide error bars.**
  rho −0.161 is "weak negative," statistically a null; do not read it as a
  confident inversion claim. Pre-registration forbids re-trying a different
  framing/model after seeing this.
- **Saturated predictions (5 distinct values)** mechanically cap |rho|; a
  forecaster that refused to spread its estimates cannot score a strong rank
  correlation in either direction.

## Bottom line

Under honest pre-registration discipline, **rich behavioral covariates did NOT
recover the X5 ranking**. rho went **+0.163 → −0.161** (perm p 0.52 → 0.43):
the model swapped one chance-level result for another, mildly anti-correlated
one, by applying a "lapsed high-value customers respond more" prior that this
RCT contradicts (the real winners are low-spend, mid-frequency members with
purchase headroom). The covariate-poverty explanation for the thin-run miss is
**falsified** — the miss was not about feature richness. Across both X5 feature
regimes the who-responds-more capability is at chance, so the Hillstrom +0.42
**does not generalize** to X5 on either demographic or behavioral covariates.
This is a real, reportable non-recovery, not a fabricated win.

## Artifacts (all under `sessions/agent-behavior-spec/x5-benchmark-rich/`)

- `data/clients.csv.gz`, `data/uplift_train.csv.gz`, `data/purchases.csv.gz` — X5 source (scikit-uplift S3 mirror)
- `build_features.py` → `data/client_features.json` (+ `client_features_meta.json`): pre-cutoff RFM features, 380,083 clients
- `build_ground_truth.py` → `x5_rich_ground_truth.json` (REAL uplifts, SHA `3f5b2d55…`)
- `PREREG_X5_RICH.json` (+ `.sha256` `9fe33eec…`) — registered before any model call
- `forecaster_x5_rich.py` → `x5_rich_audience_descriptions.json`, `x5_rich_predictions.json`, `forecaster_x5_rich_result.json`
- `X5_RICH_HETEROGENEITY_RESULT.md` — this file
