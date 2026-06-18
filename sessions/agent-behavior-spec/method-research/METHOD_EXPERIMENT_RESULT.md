# Method experiment — RESULT: NULL (prompt-level method changes do not fix product-change direction; two made it worse)

**Pre-registered** (`PREREG_METHOD_EXPERIMENT.json`, cases SHA `b110dce3…`, sealed before result).
4 arms over the V4 counter-intuitive set, Sonnet, k=4. Discriminator = less-won accuracy;
guard = more-won must not regress.

| arm | less-won | more-won | overall | more-is-better pick rate |
|---|---|---|---|---|
| comparative baseline | 2/4 | 2/4 | 5/10 | 5/8 |
| comparative + mechanism ledger | **1/4** | 2/4 | **4/10** | **6/8** |
| per-arm behavioral (isolated) | **0/4** | 2/4 | **3/10** | 5/8 (tie_rate 0.00) |
| placebo leaner-advocate | 2/4 | 2/4 | 5/10 | 3/8 |

## Verdict (per sealed decision rule): NULL
No arm reached the REAL_FIX bar (less≥3/4 AND more≥3/4). The two principled interventions
made it WORSE, not better.

1. **Mechanism ledger BACKFIRED** — the councils' unanimous top fix dropped less-won 2/4→1/4
   and RAISED the more-is-better pick rate 5/8→6/8. Forcing "reason about both sides" let the
   model articulate a richer-arm rationale and commit to the prior more confidently — the
   "mechanism-text-rationalizes-valence" trap two council members flagged, here dominant.
2. **Per-arm isolation: tie_rate 0.00 (no collapse-to-ties), but worst accuracy (0/4 less-won,
   3/10 overall).** The founder's signal-collapse concern did not manifest as ties; instead
   isolated behavioral estimates were confidently DIFFERENT but confidently WRONG. Isolation is
   still harmful, via a different mechanism than the old two-pass tie-collapse.
3. **Placebo thumb did not beat baseline** (2/4) — the less-won cases are not gameable by
   "always pick simpler"; they are genuinely case-specific.

## Honest reading + limits
- At the cheap prompt/elicitation level, the more-is-better / prior-echo failure is NOT fixable
  and resists the consensus method changes. The limit is deeper than the reasoning target.
- n=10 (less-won n=4) detects only large effects — but the direction is unambiguous: nothing
  helped, two things hurt.
- NOT tested: the full PERSONA-PANEL behavioral simulation (a panel of grounded personas each
  ENACTING a decision, aggregated to a rate). The per-arm arm here was a lightweight
  population-level responsiveness estimate, not that. The heavier engine-level version remains
  the one untested council lever.
- Predicted wrong in the un-flattering direction (I recommended the ledger as the safe bet; it
  was the worst-but-one) — recorded as such.
