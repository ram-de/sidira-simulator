# X5 RetailHero Heterogeneity Generalization Test — Result

**Question.** Does the simulator's certified Hillstrom "who-responds-more"
heterogeneity-ranking capability (blinded Sonnet expert-forecaster, Spearman
rank-rho **+0.42**) GENERALIZE to a second independent real RCT — the X5
RetailHero uplift dataset?

**Discipline.** Pre-registered before any model call
(`PREREG_X5_HETEROGENEITY.json`, SHA-pinned ground-truth vector
`2bee90d0…`). Single run, temperature 0.0, no peeking, no re-tuning, no
segment re-selection after seeing predictions. Method mirrors
`hillstrom-benchmark/forecaster_powered.py`.

## Headline

| Metric | X5 (this test) | Hillstrom (certified) |
|---|---|---|
| Spearman rank-rho | **+0.163** | +0.42 |
| Permutation p (5000 shuffles, \|rho\|) | **0.520** | <0.05 |
| Kendall tau-b | +0.120 | — |
| Direction accuracy (sign vs 0) | 0.944 | — |
| Pre-registered bar (rho>0.30 AND p<0.05) | **FAIL** | PASS |

## Verdict — DOES NOT GENERALIZE (at the pre-registered bar)

On X5 the blinded forecaster's ranking is **positively but weakly** correlated
with the real per-segment uplift (rho **+0.163**) and is **not statistically
distinguishable from chance** (permutation p **0.52**). It clears neither half
of the pre-registered bar. The Hillstrom +0.42 heterogeneity-ranking result
**did not replicate** on this fresh RCT.

The sign of the relationship is correct — the model gets the *direction* of
the effect right almost everywhere (0.944 sign accuracy: it correctly predicts
nearly every segment responds positively to the SMS) — but it does **not
recover the rank order of WHO responds more**, which is the capability under
test.

## Why it failed (honest diagnosis, from the prediction trace)

The model's predictions are **saturated and low-variance within gender**.
- All 9 **women** segments were predicted +3.2pp (one at +2.8) — essentially
  no discrimination among women, even though their real uplift spans
  −0.0005 to +0.0999.
- **Men** segments were predicted lower (+1.2 to +2.3) and with slightly more
  spread, but the rank within men only loosely tracks reality.

So the model captured a coarse **gender-level** prior (it expected women to
respond more, and predicted higher for them) but could not resolve the
**age × tenure** gradient that drives most of the real heterogeneity. The
real ranking is dominated by an age/tenure effect (older + newer members
respond most strongly; young long-tenure women are flat) that the forecaster
did not anticipate. The flat within-gender predictions are exactly what kills
a rank correlation.

## What is — and isn't — comparable to Hillstrom

- **Same marketing-nudge family.** X5 SMS promotion ≈ Hillstrom promotional
  email — both are "should we contact this customer" nudges. The treatment
  class is a fair match, so the failure is not a domain-mismatch artifact.
- **Different covariates / market.** Hillstrom segmented on
  gender × recency × email-creative (purchase-history signal). X5 segments on
  demographic age × gender × loyalty-tenure (no purchase-history signal in the
  small files used). The X5 covariates are weaker, more demographic predictors
  of uplift — plausibly a harder ranking task with less forecastable signal.
- **18 segments, single model, single run.** Same order as Hillstrom's design;
  no extra power was spent and none was borrowed.

## Limits (do not over-read this single result)

- **Single model (Sonnet), single temperature-0 run.** No ensembling/voting,
  no multi-model confirmation. A different framing or model could move rho;
  pre-registration deliberately forbids us from trying after seeing the data.
- **18 segments** is a small n for a rank test — perm p has wide error bars;
  rho +0.163 is "weak positive," not "zero."
- **Covariate poverty.** Only age/gender/tenure were used (the 670MB purchase
  file was intentionally not downloaded). Purchase-history features — the kind
  that powered the Hillstrom segments — were unavailable, so this is a
  *harder* generalization target than a like-for-like replication.
- **Unknown-gender dropped.** 92,832 matched clients had gender "U" and were
  excluded (no interpretable audience description); the test covers only the
  F/M population.
- **No segments dropped for size** — all 18 cells cleared n≥200/arm, so there
  is no truncation bias.

## Bottom line

Under honest pre-registration discipline, the Hillstrom heterogeneity-ranking
capability **did NOT generalize** to X5 at the pre-registered bar: rho **+0.163**
(p **0.52**) vs Hillstrom's **+0.42** (p<0.05). The forecaster recovers effect
*direction* (everyone responds, 0.944 sign accuracy) but **not the rank of who
responds more** — the actual capability claim. The most likely culprit is a
flat, gender-anchored prior plus genuinely weaker (purely demographic)
covariates, not a coding or leakage error. This is a real, reportable
non-replication, not a fabricated win.

## Artifacts (all under `sessions/agent-behavior-spec/x5-benchmark/`)

- `data/clients.csv.gz`, `data/uplift_train.csv.gz` — X5 source (scikit-uplift S3 mirror)
- `build_ground_truth.py` → `x5_ground_truth.json` (REAL uplifts, SHA `2bee90d0…`)
- `PREREG_X5_HETEROGENEITY.json` (+ `.sha256`) — registered before any model call
- `forecaster_x5.py` → `x5_audience_descriptions.json`, `x5_predictions.json`,
  `forecaster_x5_result.json`
- `X5_HETEROGENEITY_RESULT.md` — this file
