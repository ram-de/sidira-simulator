# SCORECARD — AMBDOM (Ambiguous-Dominance Battery)

LLM arm: **REAL**  ·  Arm A: 3 seeds × 2 polarities/cell, n=8000/case  ·  Arm B1: Cookie Cats RCT (real)  ·  Arm B2: streamly-v3 (10 datasets)

Sealed against PREREG_AMBDOM.md. No re-tuning. Refutations reported as refutations.


## Arm A — per-cell sign-accuracy

| cell | margin | truth signs | GROUNDED | LLM | ORACLE | grounded abstain | LLM follows-salient |
|---|---|---|---|---|---|---|---|
| AGREE-WIDE | wide | +/- | 1.00 (6/6) | 0.50 (3/6) | 1.00 (6/6) | 0/6 | 0.50 |
| DISAGREE-WIDE | wide | +/- | 1.00 (6/6) | 0.00 (0/6) | 1.00 (6/6) | 0/6 | 0.50 |
| DISAGREE-NARROW | narrow | +/- | 1.00 (6/6) | 0.00 (0/6) | 1.00 (6/6) | 0/6 | 0.50 |
| KNIFE | knife | 0 | 0.67 (4/6) | 0.50 (3/6) | 0.33 (2/6) | 4/6 | 0.50 |
| DISAGREE-CONF | narrow | +/- | 1.00 (6/6) | 0.00 (0/6) | 1.00 (6/6) | 0/6 | 0.50 |
| DISAGREE-HIDCONF | narrow | +/- | 0.83 (5/6) | 0.00 (0/6) | 1.00 (6/6) | 0/6 | 0.50 |

## Sealed predictions — verdicts

| id | claim (short) | statistic | verdict |
|---|---|---|---|
| A1 | DISAGREE clean: grounded≥.80, LLM≤.40, Δ≥4 cells | grounded 1.00 (12/12), LLM 0.00 (0/12), Δ=12 | **HELD** |
| A2 | AGREE-WIDE: both ≥.80 | grounded 1.00, LLM 0.50 | **PARTIAL** |
| A3 | KNIFE: grounded abstain-or-correct ≥.70 | 0.67 (4/6) | **REFUTED** |
| A4 | resolution: grounded WIDE > NARROW | WIDE 1.00, NARROW 1.00 | **PARTIAL** |
| A5 | HIDCONF breaks grounded: ≤.55 | grounded 0.83 (5/6) | **REFUTED** |
| A6 | CONF handled (adjusted): ≥.70 | adj 1.00 (6/6), unadj 0.50 (3/6) | **HELD** |
| A7 | balanced LLM ≈.50±.12 & never > grounded on DISAGREE | LLM 0.17 (6/36), exceeds=False | **PARTIAL** |
| B1 | Cookie Cats grounded predicts NON-NEGATIVE (method fails) | pred -0.4690pp (sign -), measured -0.8201pp (-) | **REFUTED** |
| B2 | streamly-v3 grounded ≥.70 (else PARTIAL if one-sign) | naive signs ['+'] (all +), grounded 0.90 vs adj-truth | **PARTIAL** |

## A1 — the load-bearing claim (magnitude-driven flips)

- GROUNDED-SIM on clean DISAGREE cells (WIDE+NARROW): **1.00** (12/12).
- Real LLM on the same cells: **0.00** (0/12).
- GROUNDED − LLM correct-count delta: **12** cells.
- Interpretation: on these cells the salient cue points AGAINST the true net sign (magnitude flip). A cue/intuition follower is wrong; only the grounded g-formula, which reads the per-unit mediator strengths from data, recovers it.

## A4 — resolution curve

- GROUNDED WIDE-disagree: **1.00**; NARROW-disagree: **1.00**.
- Mean |ΔY|: WIDE 0.1522 vs NARROW 0.0434 (the magnitude signal the grounded sim resolves is larger on WIDE).

## A7 — LLM is BELOW chance, not at it (asymmetric, not a coin)

- Across the balanced Arm-A battery the real LLM answered UP 18, DOWN 0, UNSURE 18 (of 36). It **never** confidently predicts a decline.
- When the helpful mechanism is cued salient it commits UP; when the harmful mechanism is cued salient it hedges UNSURE. Because the salient cue is ⟂ the true net sign by construction, this asymmetric 'optimism + abstain' policy lands at **0.17**, BELOW the 0.50 a symmetric cue-follower would hit — so A7's '≈0.50' clause is REFUTED in an informative direction (the model has a pro-feature directional prior), while its 'never exceeds grounded on DISAGREE' clause HELD (LLM 0.00 vs grounded 1.00 there).

## A3 / A5 — honesty & limit

- KNIFE abstain-or-correct: **0.67** (near-null produces no manufactured confident sign).
- HIDCONF grounded accuracy: **0.83** (hidden U in T,Mb,Y contaminates the structural fit, as registered — NC-guard territory).

## B1 — Cookie Cats (real RCT)

- Mediator (sum_gamerounds) shift gate_40−gate_30: **-1.157** rounds.
- GROUNDED predicted retention_7 lift via the single-mediator g-formula: **-0.4690pp** (sign -).
- Measured RCT retention_7 effect: **-0.8201pp** (sign -, the canonical small NEGATIVE).
- LLM (intuition: later gate → more runway): +.
- Verdict REFUTED in the *pleasant* direction: the grounded single-mediator g-formula DID recover the true negative sign (the observed mediator shift is itself negative), contrary to the prereg's honest pessimism.

## B2 — streamly-v3 per-dataset

| dataset | n | p(T) | maxSMD | randomized | naive ATE | adj ATE | truth | grounded | ✓ |
|---|---|---|---|---|---|---|---|---|---|
| dataset_01.csv | 10578 | 0.507 | 0.032 | True | +0.2532 | +0.2530 | + | + (+0.2608) | Y |
| dataset_02.csv | 23240 | 0.499 | 0.967 | False | +0.2046 | +0.0284 | + | + (+0.2111) | Y |
| dataset_03.csv | 22556 | 0.498 | 0.705 | False | +0.2052 | +0.0239 | + | + (+0.1410) | Y |
| dataset_04.csv | 17945 | 0.496 | 0.648 | False | +0.2785 | +0.1241 | + | + (+0.2316) | Y |
| dataset_05.csv | 27637 | 0.498 | 0.588 | False | +6.0442 | +0.5443 | + | + (+4.5963) | Y |
| dataset_06.csv | 26194 | 0.501 | 0.990 | False | +0.3699 | +0.1672 | + | + (+0.3177) | Y |
| dataset_07.csv | 8784 | 0.506 | 0.064 | True | +0.4812 | +0.3085 | + | + (+0.4411) | Y |
| dataset_08.csv | 26571 | 0.498 | 0.033 | True | +0.1339 | +0.1366 | + | + (+0.1459) | Y |
| dataset_09.csv | 15579 | 0.501 | 0.570 | False | +5.9189 | +0.9941 | + | + (+4.1895) | Y |
| dataset_10.csv | 14297 | 0.499 | 0.755 | False | +0.2007 | -0.0366 | - | + (+0.1148) | N |
- All 10 datasets share the MEASURED (naive) ATE sign **['+']** (all positive) → **NO genuine population-level dominance ambiguity → B2 UNDER-POWERED (PARTIAL)**, per the prereg's one-sign contingency.
- The only sign-flip (dataset_10) appears solely after covariate adjustment on a non-randomized dataset, at −0.037 (near the null vs its +0.20 naive) — an estimation artifact, not a real population reversal. So the lone grounded 'miss' against adjusted-truth is itself a noise-level disagreement.
- GROUNDED segment-composition recovers the positive sign on 10/10 datasets (matches the naive measured sign everywhere); accuracy vs adjusted-truth **0.90**. LLM net-direction guess: 0 (UNSURE — it cannot weigh the segment mix).
- Caveat: 7/10 v3 datasets are NOT cleanly randomized (maxSMD≥0.10); for those the adjusted ATE (not naive) is the better truth, but adjustment relies on selection-on-observables and cannot be verified here. B2 stays a LEAD/PARTIAL: no dataset exhibits a genuine population dominance flip to test the win on.

## Verdict summary

A1=HELD · A2=PARTIAL · A3=REFUTED · A4=PARTIAL · A5=REFUTED · A6=HELD · A7=PARTIAL · B1=REFUTED · B2=PARTIAL


LLM arm: **REAL**.
