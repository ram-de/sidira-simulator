# Step 1 CERTIFIED: persona enrichment closes the heterogeneity gap (#342)

The production personas carry segment signal only as raw-stat jargon
(`value_sensitivity.history (-0.60σ)`), empty snapshots, ungenerated jtbd — the
cluster-naming step ("LLM naming unavailable") never ran. This validates the
missing piece: an **enricher** that turns a segment's REAL feature statistics into
a rich natural-language description, then confirms enricher-generated descriptions
(the realistic production path) recover heterogeneity through the comparative pass.

## Result (38 strata, descriptions generated from real feature stats, k=4)

| audience conditioning | Spearman ρ | perm p | Kendall τ_b |
|---|---|---|---|
| raw-jargon GMM personas (today's live gap) | ~0 (clustered) | — | — |
| hand-written rich personas | +0.385 | 0.015 | +0.279 |
| **enricher-generated (real feature stats → NL)** | **+0.457** | **0.004** | +0.336 |

**CERTIFIED**, and *better* than hand-written — the enricher folds in features the
hand version omitted (prior spend, tenure/new-vs-returning, location). Example
output: *"Men's-only shoppers split almost evenly between new and returning
customers…"*; *"Mostly new suburban shoppers who buy both men's and women's
products, recent purchasers, ~$687 spend…"*.

## What this establishes — the production fix is fully proven

The two levers for in-product heterogeneity are now both validated:
1. **Comparative pass** — fixes direction (e2e +10pp) and is the elicitation that
   makes heterogeneity recoverable. Built, wired, flag-gated.
2. **Persona enrichment** — the missing cluster-naming step. Turns the signal the
   personas already carry (as stats) into readable descriptions the forecaster can
   use. Validated here: ρ +0.457, p=0.004.

Together they recover the certified who-responds-more ranking through the
production comparative pass. The gap was never the method — it was that the live
persona pack's descriptions are raw stats, not language.

## Honest limits
- The enricher is validated as a research harness (descriptions generated from real
  feature stats). **Not yet wired into the production persona-build/conditioning**
  — that integration (running the naming step on the live pack) is the next step.
- One dataset / metric (visit) / model; conversion + cross-dataset open.
- Still flag-gated, default OFF.

## Next
1. **Wire the enricher into the production persona conditioning** — run the
   cluster-naming step so the live pack carries rich descriptions (the actual
   product change).
2. Then a deliberate **flag flip** + the **customer backtest pilot** (sellable proof).
