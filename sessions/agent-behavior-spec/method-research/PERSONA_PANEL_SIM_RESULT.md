# Persona-panel behavioral sim — RESULT: NULL (the final technical lever fails at this scope)

**Pre-registered** (`PREREG_PERSONA_PANEL_SIM.json`, cases SHA `b110dce3…`, sealed before result).
12 trait-diverse personas, each ENACTS (convert/defer/abandon) on each version in isolation;
arm = fraction who convert; winner = higher rate. Sonnet. First PERSONA-GROUNDED product-change
test (all prior product-change runs were population-level forecaster judgments).

| metric | persona-panel | forecaster baseline |
|---|---|---|
| less-won (discriminator) | **1/4** | 2/4 |
| more-won (guard) | 1/4 scored (**3 TIES**) | 2/4 |
| overall | 3/7 scored (3 ties) | 5/10 |

## Verdict (per sealed rule): NULL — and slightly WORSE than baseline on the discriminator.

Two failure modes, one bright spot:

1. **More-is-better persisted on 3/4 less-won cases.** The panel *converted more* on the
   feature-rich arm: discount-surfacing (0.58 vs 0.42), countdown timer (0.25 vs 0.08), image-zoom
   (0.50 vs 0.17) — all the arm that really LOST. The personas "liked the richer thing" even when
   enacting. The bias survived the behavioral framing.
2. **NEW failure: insensitivity to small changes → ties.** On 3/4 more-won cases (the "Only" word,
   12-vs-16 carousel, popularity count) the panel produced IDENTICAL rates for both arms → ties,
   no signal. Generic personas reading abstract descriptions can't feel a one-word or one-tile
   tweak — the signal-collapse risk, now real on subtle changes.

3. **BRIGHT SPOT — one mechanism fired correctly.** The coupon-deadline case (less-won) it got
   RIGHT, via the RIGHT mechanism: the 2-month deadline drove conversions to 0.0 (everyone defers)
   vs 0.08 for the 3-week — procrastination surfaced through enactment, exactly as theory predicts.
   So the approach CAN capture a tail mechanism — it just didn't generalize; on most cases the
   personas defaulted to liking the richer option.

## Reading
- The persona-panel sim — your product's actual mechanism, tested faithfully for the first time on
  these cases — does NOT recover counter-intuitive product-change direction at this scope (generic
  panel, abstract stimulus). less-won 1/4 ≤ baseline 2/4 → NULL by the sealed rule.
- The one correct mechanism (deadline→defer) is a proof-of-concept that enactment isn't hopeless;
  but it's swamped by (a) residual more-is-better and (b) insensitivity to subtle stimuli.
- Per the decision rule, this exhausts the inexpensive technical levers. Next: repositioning, or
  customer-data validation (a real GMM pack + real stimulus fidelity — the two things this run
  lacked: customer-specific personas and a concrete rendered experience, not an abstract sentence).
