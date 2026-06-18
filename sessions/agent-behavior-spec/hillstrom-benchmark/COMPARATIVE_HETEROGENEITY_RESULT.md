# CERTIFIED: heterogeneity recovers through the comparative engine pass — given segment-rich personas (#342)

**Pre-registered** (`PREREG_COMPARATIVE_HETEROGENEITY.json`, bar fixed before the
result: Spearman ρ > 0.30 AND permutation p < 0.05). 38 gender×recency×channel
strata (the certified set), each a descriptive Persona, driven through the
**production comparative pass** (`compose_comparative_metric_prompt` +
`elicit_visit_delta`), k=4. Ground truth: real per-cell visit uplift from the RCT.

## Result

| approach | Spearman ρ | perm p | Kendall τ_b |
|---|---|---|---|
| standalone forecaster (Fix #3, certified) | +0.42 | 0.01 | — |
| GMM-persona e2e (clustered) | ~0 | — | — |
| **comparative engine + rich personas** | **+0.385** | **0.0152** | +0.279 |

**CERTIFIED** — clears the pre-registered bar. (Per-cell direction accuracy 0.605
is noisier because several cells have tiny/near-zero real uplifts; the certified
claim is the who-responds-more *ranking*, ρ.)

## What this establishes

1. **Heterogeneity recovers through the production comparative engine pass** — ρ
   +0.385 (p=0.015), close to the standalone forecaster's +0.42. The engine can do
   the Kohavi-proof "who responds more" ranking, not just direction.
2. **The lever is the comparative pass AND segment-rich audiences — together.**
   The same comparative pass with thin GMM personas (the e2e) gave clustered deltas
   and no heterogeneity; with descriptive segment personas it recovers the ranking.
   So the production **persona pack being generic is the gap, not the method.**
3. **The full path-A picture is now coherent:** comparative pass fixes direction
   (e2e +10pp) AND, with rich personas, certifies heterogeneity (ρ +0.385). Both
   the elicitation architecture and the audience richness matter.

## Honest limits
- Descriptive personas hand-built for this run; the **production GMM persona pack
  is too generic to realize this in the live default** — enriching it (segment-
  descriptive conditioning) is the next product lever.
- One dataset / one metric (visit) / one model. Conversion heterogeneity and a
  larger powered run remain open.
- Still flag-gated, **default OFF**. This is the evidence to consider enriching the
  persona pack + flipping the flag — a deliberate decision, not done here.

## Next
1. **Enrich the production persona conditioning** so the live engine carries the
   segment signal that recovers heterogeneity (the now-identified gap).
2. Then a deliberate **default flip** + the **customer backtest pilot** (the
   sellable proof on a design partner's real experiments).
