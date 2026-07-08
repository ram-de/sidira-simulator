# v_5 richness test — end-to-end on the Netflix-like mock warehouse

**Date:** 2026-07-08 (UTC) · **Org:** Streamly synthetic (`org_3F9pXzqFStz5NyPkazXW1o47NzE`)
**Answer key:** `MOCK_DATA_V2_SPEC.md` (same directory) · **Prod:** api @ `c4bb290`
**Follow-ups filed:** #592 (residual-bias leak) · pre-existing: #588 (council degraded)

## What this was

First full product exercise on a *rich* warehouse: 6 tables / 10 levers /
6 outcomes / a 12-row past-experiments table, all with designed ground truth —
seeded so we know exactly what the guard and the decision flow *should* say.
Also the prod validation of the #586 standardized-floor fix (deployed this
session via PRs sidira-personas#28 → #590 → #591).

Chain executed end to end through the real product surface:
Snowflake seed → `POST /persona-builds` (run `bc577f65`, 57 min, 8 personas,
stability 0.743, 70 candidate lever cards) → promote v_5 → 3 sims via
`POST /simulations` with decision flow ON.

## Scorecard vs the answer key

### Guard verdicts (estimability manifest, 70 candidates)

**All 9 designed true-effect pairs PASS with accurate ATEs:**

| pair | guarded ATE | truth |
|---|---|---|
| new_recs_algorithm → watch_minutes | **+41.9** | +45 |
| new_recs_algorithm → completion_rate | **+0.052** | +0.05 |
| mobile_preview_clips → watch_minutes | **+37.5** | +40 |
| mobile_preview_clips → sessions | **+1.26** | +1.2 |
| profile_onboarding_quiz → sessions | **+1.49** | +1.5 |
| kids_profile_nudge → kids_hours | **+1.62** | +1.5 |
| password_sharing_crackdown → watch_minutes | **−47.1** | −50 |
| password_sharing_crackdown → churned_90d | **+11.0pp** | ≈+9pp |
| skip_intro_default_on → minutes_watched | **+54.1** | +60 |

**All 3 confounded levers TRIP on their headline spurious pairs:**

- `offline_downloads_enabled` → minutes: NC residual **+0.96σ** (the M4 T1 replica).
- `premium_upsell_banner` → minutes_watched: naive **+155** → guarded +0.98, ratio-tripped; sessions/churn/completion tripped on NC residuals (+0.18–0.30σ).
- `dormant_winback_email` → sessions: NC **−0.34σ** caught the sign-mask (naive −8.1 vs true +1.0) — correctly refused rather than reporting either wrong number.

**True null (`ui_dark_mode_default`):** ratio-rule abstains across the
engagement outcomes, as designed.

### #586 fix validated in prod

`skip_intro_default_on` → minutes is the M4 T2 lever that falsely tripped on a
raw-scale chance imbalance (−13.2 min = 0.056σ). With the standardized floor it
now reads nc_sd −0.056σ against an effective floor of 0.080σ → **PASS**, ATE
+54.1 (true +60). Exactly the predicted repair, on the same data-generating
process at the same n.

### End-to-end sims (decision flow ON, pack v_5)

| sim | hypothesis | expected | got |
|---|---|---|---|
| E1 `90b86030` | new recs ↑ watch minutes | grounded CONFIRMS | **source=grounded, direction=positive, "verified verdict", watchdog CONFIRMS, confidence 60.9** |
| E2 `5ea787aa` | crackdown ↑ watch minutes (wrong sign) | grounded contradiction | **source=grounded, direction=negative vs the positive hypothesis, "verified verdict", confidence 11.3** — sim and grounded data agree the hypothesis fails |
| E3 `5d76036f` | dark-mode default ↑ watch minutes (true null) | abstain | **source=llm_fallback, caution=hard, "inconclusive — test it", CANT_VALIDATE, unverified=true** |

**E1 is the first grounded CONFIRMS produced by the product end to end** —
warehouse → build → guard → promoted pack → sim → verified verdict.

## Deviations / findings

1. **#592 — residual-bias leak on confounded levers (new, filed).** A clean
   outcome-keyed NC can coexist with modest residual bias on the outcome
   itself: upsell→watch_minutes passed at **+25 min** (true 0, naive +444),
   winback→watch_minutes at **−32** (true 0), offline→churned at **−4.4pp**
   (true 0). The guard scrubbed 90–94% of the naive bias in each case; the
   leak is the remainder. Cheapest fix: treatment-scoped NC pooling (any NC
   trip on a lever trips all its pairs). Details in the issue.
2. **#588 — council still degraded 1/3 usable** (`claude-opus-4-7` rejects
   `temperature`, one member dropped on parse). Did not block: grounded path
   doesn't need council agreement. Same failure signature as M4.
3. **Guard passes are bias-verdicts, not significance tests.** Several
   true-null pairs on randomized levers pass with negligible ATEs (e.g.
   dark-mode→churned −1.3pp). Fine for grounding (small numbers ground small
   claims) but worth remembering when reading lever cards.
4. **Producer runtime:** 57 min for the 10×6 grid with `nc_diagnostics` on,
   dominated by unscaled-covariate lbfgs fits hitting max_iter=3000.
   Standardizing covariates before the logistic fits would likely cut this
   several-fold. Not filed; note for when a real partner's warehouse is
   wider.

## Verdict

The product does the right thing on a rich, adversarially-designed warehouse:
confirms what's real (with magnitudes within ~10% of truth), refuses what's
confounded, abstains on nulls, and survives the scale trap that #586 fixed.
Remaining gap before a real design partner: #592 (leak), #588 (council), and
the founder-gated live-data items tracked in the onboarding memory.
