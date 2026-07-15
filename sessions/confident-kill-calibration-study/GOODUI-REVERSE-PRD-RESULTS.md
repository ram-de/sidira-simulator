# GoodUI reverse-PRD experiment (2026-07-15)

Tests the one input lever the Upworthy headline study could NOT: **real product
context (reverse-PRD)**. Upworthy is text-only, so it can never exercise the
engine's `reverse_prd` + product-reasoning machinery. GoodUI Evidence provides
real product/UI A/B tests (checkout, layout, copy changes) with measured outcomes.

## Data (not committed — GoodUI is paywalled; see ToS note)
131 well-powered (statistical power ≥ 80%) real product/UI A/B tests from GoodUI
Evidence: 88 winners, 43 losers, effect −10.7% … +34.3%. Extracted via the member's
own logged-in session. **Raw GoodUI descriptions, effect sizes, and screenshots are
NOT committed** (their content, behind a paywall). Only the engine's own output
signal paired with a 1-bit win/lose label ships, in `data/results_goodui_min.csv`.

## Encoding (the point)
Each test runs through the engine's DESIGNED path — the lever Upworthy couldn't test:
- `reverse_prd` = real product context (which screen, what metric, current baseline)
- `hypothesis.prose` = the actual proposed change
- an e-commerce-shopper persona panel (`goodui_runner.py`)
- A/B mode → `lift` = predicted direction of the change vs the current design.

## Result (131, 0 failures)

| Metric | Value |
|---|---|
| Directional accuracy | **0.594** — vs coin flip **z=2.12, p=0.034 (SIGNIFICANT)** |
| (Upworthy headline floor) | 0.52, NOT significant |
| Majority-class base rate | 0.67 (88/131 won) |
| Confident-KILL, lift ≤ −5 | 18 killed, killed-winner 50% (vs 67% base), 21% coverage |
| Confident-KILL, lift ≤ −10 | 4 killed, killed-winner **0%** (all real losers) — but n=4, uncertified |
| Clean-KILL GO/NO-GO (≤5% killed-winner, ≥8 kills) | NO-GO |

## Reading it honestly
- **Real product context beats a coin flip for the first time in the campaign**
  (p=0.034). The reverse-PRD lever genuinely moves the needle.
- But 0.594 is **below the 0.67 majority-class base rate** — real signal, not a
  strong predictor.
- Confident-KILL: no clean high-volume region, BUT unlike Upworthy's *anti*-predictive
  tail, killed-winner **improves with margin** (67% base → 50% → 0%), i.e. the
  confident-negative tail is genuinely enriched for real losers — just too thin
  (4 cases) to certify.

## Why it's the first green light for the design-partner pilot
The signal is real but the confident tail is thin, and three levers this pilot did
NOT use should widen/clean it — and they are exactly the pilot's mechanics:
1. more data to populate the tail (public data is too small/noisy),
2. the client's OWN GMM persona packs (this used generic shopper personas),
3. a calibrator fit on the client's real outcomes.

## Reproduce
Extraction requires a GoodUI membership. `harness/goodui_runner.py` runs the engine
over a pairs CSV built from extracted tests; `analysis/analyze_goodui.py` produces the
accuracy + confident-KILL sweep from `results_goodui_min.csv`.
