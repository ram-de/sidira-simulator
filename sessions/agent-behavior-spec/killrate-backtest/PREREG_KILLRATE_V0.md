# Pre-registration — kill-rate backtest v0 (#602), sealed before scoring

Date: 2026-07-08. Sim-free triage: only pre-launch-knowable inputs feed kill
verdicts. `real_winner`/`effect`/outcome fields are read ONLY at scoring time,
after verdicts are emitted.

## Kill rules (mechanical, no LLM judgment)

- **K1 power kill**: compute MDE (two-proportion, α=.05 two-sided, 80% power)
  from per-arm n and baseline rate. KILL if relative MDE > 10% — i.e. the
  experiment as designed can only detect a ≥10% relative lift on its primary
  metric (few deliberate product changes move a core metric that much).
  Requires: per-arm n + baseline. Missing → CANNOT_ASSESS(K1).
- **K2 ceiling kill**: KILL if baseline ≥ 90% of the metric's structural
  maximum. Requires baseline. Missing → CANNOT_ASSESS(K2).
- **K3 value-cap kill**: KILL if the historical effect distribution for this
  metric says even a detected winner is immaterial. Requires per-metric
  effect-size history (#525). Not available for any public case → always
  CANNOT_ASSESS(K3) in v0. Recorded to quantify the gap.
- **K4 analogy kill**: KILL if ≥3 similar prior experiments (same mechanism
  class × same metric) averaged ≤0. Requires an experiment corpus.
  CANNOT_ASSESS(K4) in v0 except within-Upworthy (same-mechanism corpus).

Verdict per case = KILL (any rule fires) / RUN (all assessable rules pass) /
CANNOT_ASSESS (no rule assessable).

## Corpora & ground truth

1. **Portfolio 8** (`PORTFOLIO_CASES.json` scored_cases): failure :=
   real_winner == control (proposed change lost/flat); success := treatment
   won. Pre-launch facts allowed only where the published source states them:
   cookiecats (n=90,189 two arms, baseline 7d retention 0.19), tinkoff
   (n=265,000, baseline form conversion unpublished), others: no quantitative
   pre-launch facts published → expect CANNOT_ASSESS. Coverage itself is a
   pre-registered endpoint: fraction of narrative cases assessable by grounded
   kills.
2. **Hillstrom** (raw CSV, one experiment, 3 arms ~21.3k each): scored twice,
   once per candidate primary metric (visit rate baseline from control arm;
   conversion rate baseline from control arm). Ground truth per metric:
   two-proportion z-test (best treatment arm vs control) significant at .05.
3. **Upworthy archive** (per-arm impressions/clicks): universe = tests with
   ≥2 packages and ≥1,000 total impressions. Ground truth conclusive :=
   chi-square across arms p<.05. Ex-ante inputs: per-arm n = test's mean
   impressions/arm (allocation policy); baseline = corpus median package CTR
   (computed once, all tests); plausible-effect prior = median relative lift
   of winner vs runner-up among conclusive tests (corpus-level constant —
   acknowledged mild circularity, stands in for the #525 prior). K1-Upworthy:
   KILL if 80%-power MDE_rel > plausible-effect prior. K4-Upworthy: not run in
   v0 (headline text similarity out of scope).

## Endpoints

- Per corpus: kill rate among true failures (sensitivity), false-kill rate
  among true successes, coverage (assessable fraction).
- Headline: "would have saved X of Y wasted slots at Z% false kills" on the
  assessable universe; plus the coverage finding on narrative cases.
