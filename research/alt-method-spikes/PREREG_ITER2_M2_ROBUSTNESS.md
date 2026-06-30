# PREREG — iter2: M2 (few-shot analogy) robustness stress-test

Sealed before run. Iter1 surprise: M2 leave-one-out few-shot analogy = 11/14 (0.79), the ONLY
above-chance method (M0 holistic 7/14, M1 decomposition 7/13, M3 selective degenerate). Iter1
showed M2 beats the base-rate-only control (8/14 = 0.57) by correctly flipping 4/6 treatment cases
while keeping 7/8 control — genuine discrimination, mechanism = few-shot examples de-bias M0's
change-wins prior. Before recording a LEAD, test internal robustness (LLMs are in-context-order
sensitive; a model echoing the last example's label would be fragile and not a real LEAD).

Model: Groq `llama-3.3-70b-versatile`, temp 0.0. Cases: PORTFOLIO_CASES_CONFIRM.json (the same 14
used in iter1 — 8 control / 6 treatment).

## Method
Re-run M2 (leave-one-out few-shot) across **5 random orderings of the in-context examples** ×
**3 seeds** (15 runs total per held-out case). Report the distribution of M2 accuracy across the
15 runs. Also formally compute the **base-rate-only control** (predict the example-majority label
for each held-out case) as the floor.

## Pre-registered pass criteria (sealed, genuine lean)
- **PASS (LEAD confirmed):** median M2 accuracy across the 15 runs ≥ 0.70 AND the 10th-percentile
  run ≥ 0.64 (i.e. even unlucky orderings stay above the 0.57 base-rate floor). My genuine lean:
  **PASS** — the de-biasing mechanism is a distributional calibration, not last-example echoing, so
  it should be order-robust.
- **FAIL (artifact → downgrade to NULL/inconclusive):** median < 0.64 or wide swings dipping to
  chance under reordering ⇒ the 0.79 was an ordering artifact.
- Either way, the EXTERNAL-validity caveat stands and is NOT resolved by this test: the examples are
  from a counter-intuitive-curated set, so even a PASS = "LEAD, internally robust, external validity
  unproven, requires a representative real labeled corpus" — which is the data wall. This test only
  decides whether M2 is internally real enough to be worth that corpus investment.

## Honesty rails
- n=14, 15 runs: still underpowered. PASS = LEAD, never PROMOTED.
- The base-rate floor (0.57) is the number M2 must clear to mean anything.
- Report the raw 15-run accuracy list so the cofounder can audit the spread.
