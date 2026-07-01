# E1 RESULTS — Arithmetic-Sufficiency Test · **PASS**

**Prereg:** `PREREG_E1_ARITHMETIC_SUFFICIENCY.md` (sha256 `6df27685…`), sealed before generation.
**Answers fingerprint verified at scoring:** `a535b997…` (see `e1_score.json`).
**Date:** 2026-07-01.

## Verdict against pre-registered thresholds

| Predictor | Flip cells (12) | One-sign cells (12) | Cookie Cats (real) |
|---|---|---|---|
| **CALC** (translator → deterministic arithmetic) | **12/12 correct, 0 wrong, 0 abstain** | 12/12, 0 wrong | **both signs recovered from tier-1 moments alone**; deltas −0.8201pp (ret7) / −0.5905pp (ret1) — matching the sealed row-level truth (−0.82 / −0.591) |
| LLM-TABLES (claude-opus-4-8, same prose + same tables) | 12/12 correct | 11/12 — **1 arithmetic slip** (F1_onesign_3) | both signs recovered |
| CHANCE | 6/12 expected | — | — |

**PASS criteria met:** ≥9/12 flips correct-and-confident ✓ (12/12) · zero confident-wrong ✓ · abstention ≤6/12 ✓ (0) · zero wrong on one-sign ✓ · Cookie Cats signs recovered from collapsed tables ✓.

## The two findings that matter

1. **The tier-1 verdict rung exists for composition-driven changes.** The information IS in the frozen aggregate schema, and a ~100-line deterministic calculator extracts it with zero error, including on the 12 cells whose prose narrative leans the wrong way. The words-only regime (measured 0.00 on flips in AMBDOM) becomes 1.00 the moment the numbers arrive in tables — for the calculator AND for the LLM. Magnitude-blindness is confirmed as **information absence, not reasoning inability**: give the model the tables and its flip accuracy goes 0.00 → 12/12.
2. **The calculator still beats the frontier LLM on the same tables — on reliability, not coverage.** Opus-with-tables made one silent arithmetic error on an easy one-sign cell (called "down" on a true "+"). A confidently-wrong on an *easy* cell is precisely the failure class the product cannot ship. Deterministic arithmetic: 24/24, auditable, ~free per call. Per the prereg: any learned model must beat the calculator to be funded on this slice.

## Honesty caveats (pre-registered meta-rule: synthetic pass is necessary-not-sufficient)

- **Leg A shares its arithmetic with the generator by construction.** The synthetic battery tests *extraction and binding* (does the translator classify the mechanism family correctly — it went 24/24 — and does the pipeline route the right cells into the right arithmetic), not discovery of unknown behavioral physics. The promotable evidence is **Leg B**: real Cookie Cats data, collapsed to the tier-1 schema, both counter-intuitive negative signs recovered with magnitudes intact to the 4th decimal (the engagement-bin collapse is essentially lossless for arm means — which is itself the sufficiency claim for this schema).
- Truth structure is degenerate by design (all flips −, all one-signs +); predictors never saw flip labels, but a future battery should mix flip directions.
- LLM-TABLES uses the same model family as the translator step (claude-opus-4-8). The translator never outputs a sign (R2), so the contamination surface is classification only.
- `temperature` omitted (rejected by claude-opus-4-8 with 400 "deprecated"); prereg specified 0. Deviation recorded in the scripts.

## What this changes in the paper

- Frontier table §6, tier 1: "composition-driven flip calls" is now **measured, not hypothesized** (synthetic 12/12 + real Cookie Cats leg). Dissent #2 ("does tier 1 exist as a verdict rung?") resolves **for** the rung's existence — on the composition slice only; mediator-driven flips remain abstain-unless-purchased (E3's question).
- E1's branch condition fires: the deterministic calculator is the tier-1 wedge; E7 (PFN spike) must now beat 24/24-at-zero-cost to justify any spend on this slice.
