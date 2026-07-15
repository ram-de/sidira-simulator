# Confident-KILL calibration study — Upworthy Research Archive

**Date:** 2026-07-14 · **N = 600** real headline A/B experiments · **0 run failures**

## Question
Can Sidira's LLM simulation engine, with a calibrated confidence layer, **confidently
KILL** losing variants at a bounded false-negative (killed-winner) rate — using public
A/B data with real outcomes, no client partner required?

## Method
- **Corpus:** Upworthy Research Archive (32,487 real headline A/B tests, measured CTR).
- **Pairs:** 600 tests with a *statistically significant* winner (own two-proportion
  z-test, p<0.05, ≥1,000 impressions/arm), spanning z=1.97→9.4. Each pair = (real
  winner headline, real loser headline) + article context (the story `lede`).
  Treatment/control assignment seeded-random (balance 49/51) to remove position bias.
- **Engine:** `SimulationRunner.run()`, A/B mode (`treatment_fraction=0.5`), 10-agent
  general-audience panel, `signal = result.lift`. Faithful to the product path.
- **Calibration:** real `PlattCalibrator`, honest 5-fold **cross-fit** (never fit &
  score the same pair). Swept KILL threshold τ, a raw negative-margin δ, and a signal
  deadzone. GO requires killed-winner ≤ 5% with ≥15 kills (min support).

## Results

| Metric | Value |
|---|---|
| Raw directional accuracy | **52.5%** (315/600) — vs coin flip **p = 0.22, NOT significant** |
| Naive "sign<0 → KILL" | 341 killed, **killed-winner 47.2%**, coverage 59% |
| Raw margin, most extreme 27 negatives (δ=28) | **killed-winner 40.7%** |
| Calibrated, most-confident 22 (P(neg)≥0.6) | **killed-winner 54.5%**, coverage 3.3% |
| **GO / NO-GO (5% ceiling)** | **NO-GO** — no threshold/margin/deadzone stays clean |

The killed-winner rate never drops below ~40% at **any** operating point. The engine's
*most confident* "this loses" calls are ~54% actually winners — confidence is
**anti-correlated** with correctness. Calibration correctly refuses to certify a KILL
(the safety-first default fires); it cannot manufacture signal that isn't present.

## Interpretation

1. **On subtle A/B (two already-good, editor-optimized headlines) the engine's direction
   is statistically indistinguishable from random.** Expected — this is the hardest
   discrimination (Upworthy ran 32k tests *because* humans can't call these either).
2. **Acting on raw LLM direction is catastrophic** (47% killed-winner). Hard proof, on
   600 real experiments, of why KILL must be gated behind calibration. This is the
   pivot's central guardrail, now measured, not asserted.
3. **The safety design is load-bearing and works:** with no clean threshold, the screen
   ABSTAINs and never ships a dangerous KILL.
4. **The product's actual claim is NOT tested here.** Sidira claims "screen out
   *obviously bad* variants," not "referee optimized headlines." Upworthy has no
   obviously-bad arm, so this study is an adversarial lower bound, not the real claim.

## Status of the claim
- Screening **subtle winners**: **disproven** (this study).
- Screening **obvious junk**: **still untested** (no public labeled corpus).

## Recommended next experiment
Build an **obviously-bad-variant** test set: pair each real winner against a
deliberately degraded arm (empty / nonsense / broken copy) and measure whether the
engine KILLs *those* cleanly. That tests the claim we actually make.

## Follow-up: obviously-bad-variant test (the claim we actually make)

240 pairs = each real winner vs a deliberately-degraded arm (empty / gibberish /
off-topic / vague), same engine harness, 0 failures:

| Metric | Value |
|---|---|
| Directional accuracy (good beats junk) | **100.0%** — all 240, every category |
| Median engine lift: good vs bad | **+43.8 / −24.3** (wide, no overlap) |
| Confident-KILL killed-winner | **0.000** at every margin |
| Coverage (junk caught) at δ≤5 | **100%** |

**The designed boundary, measured on both ends:** confident + correct on obvious
junk (0% killed-winner), at-chance and correctly-abstaining on subtle winners. The
engine is not broken — it has a real safe operating regime.

**Caveat:** these degradations are trivially bad. Real PM-submitted bad variants are
*plausible-but-mediocre*. The two endpoints are pinned; the commercially-decisive
MIDDLE (how far up the subtlety gradient confident-KILL survives) is still untested.
Next = a graded-difficulty ladder.

## Artifacts (scratchpad)
`labeled_pairs.csv` (600) · `results.csv` (signals+truth) · `batch_runner.py`
(harness) · `analyze_calibration.py` (cross-fit sweeps) · `upworthy_*.csv` (raw).
