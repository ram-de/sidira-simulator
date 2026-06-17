# Class-A CONFIRMATORY set — assembled pool + design (2026-06-17)

Purpose: a FRESH, pre-registered, class-A-only (substantive-deliberative) run to confirm or
refute the exploratory v3 subset finding (substantive-class 7/10=0.70) on out-of-sample data.

## PRIMARY ENDPOINT (balance-independent): control-class accuracy
On the 8 FRESH control-won cases (the change backfired / status-quo won) — does the sim
RESIST its measured pro-change tilt? control_class_acc = (# control-won predicted control) / 8.
- Decision rule: >=0.5 (>=4/8) → real balanced discrimination on fresh data → narrow positive
  supported. <=3/8 → pro-change tilt confirmed intrinsic → in-scope "positive" was
  treatment-lean flattering → honest bounded-null + #221 (de-bias pro-change prior) is the lever.
- REGISTERED PREDICTION (honest, un-flattering-to-product): I expect the tilt to LARGELY PERSIST
  → control-class ~2-3/8 (0.25-0.375). These are adverse-signal/second-order cases (reference-price
  reset, choice overload, adverse quality signal, engagement↔revenue divergence) where a naive
  "would users like this feature?" simulation predicts the feature helps → treatment → WRONG.
  A control-class >=4/8 would pleasantly surprise me = credible positive evidence.
SECONDARY: headline dir_acc (vs baselines below), treatment-class acc (expect ~high, ~5-6/6,
confirming the asymmetry), rank_rho, null-integrity cert.

## Baselines (set is 8C/6T, control-heavy by design)
chance=0.5 ; always-control = 8/14 = 0.571 ; always-treatment = 6/14 = 0.429.
(Control-heavy is intentional: the pro-change tilt works AGAINST always-control, and the primary
endpoint is control-class which is balance-independent.)

## SCORED SET — 14 cases (author neutral, mechanic-only, parallel; NO valence/outcome leak)

### CONTROL-WON (8) — real_winner = control (the plausible change LOST)
1. ascarza_proactive_plan_recommendation — telecom retention. control: no proactive contact,
   customer stays on current plan. treatment: firm proactively contacts and recommends a
   cost-minimizing plan. metric: churn over next 3 months. winner: CONTROL (6% vs 10% churn).
   JMR 2016 53(1):46-60. memo=low. counter_intuitive=high. [cleanest pick]
2. kanuri_andrews_service_recovery_incentive — subscription/service recovery. control: after a
   delivery failure, no price-based incentive offered. treatment: offer a discount/credit after
   the failure. metric: contract renewal. winner: CONTROL (incentive lowered renewal). JM 2019
   83(5):57-77, n=6,919. memo=low. counter_intuitive=high.
3. algesheimer_ebay_community — marketplace. control: customer not invited to the community.
   treatment: customer emailed an invitation to join/participate. metric: amount spent + listings
   over the year. winner: CONTROL (participation lowered spend/listings). Mktg Sci 2010
   29(4):756-769, n=13,735. memo=low. counter_intuitive=high.
4. lambrecht_tucker_dynamic_retargeting — display advertising. control: generic brand/category
   banner. treatment: dynamic banner showing the specific products the user browsed. metric:
   purchase probability. winner: CONTROL (generic > dynamic on avg, early-funnel). JMR 2013
   50(5):561-576, N=77,937. memo=medium. counter_intuitive=high.
5. anderson_simester_installment_billing — catalog retail (prestige). control: catalog without
   an installment-billing offer. treatment: same catalog with an installment-billing offer added.
   metric: demand. winner: CONTROL (installment lowered demand, adverse quality signal). Mktg Sci
   2001 20(3):315-327. memo=medium. counter_intuitive=high.
6. dholakia_simonson_reference_points — online auctions. control: listing with no comparison
   instruction. treatment: listing with an added advisory to compare price against similar items.
   metric: bidding intensity / seller outcome. winner: CONTROL (advisory → cautious bidding).
   Mktg Sci 2005 24(2):206-217. memo=medium. counter_intuitive=high.
7. anderson_simester_sale_sign_saturation — retail signage. control: sale signs on SOME products
   in a category. treatment: sale signs on MORE/most products in the category. metric: per-sign
   demand / category sales. winner: CONTROL (over-signing erodes the credibility cue). Mktg Sci
   2001 20(2):121-142. memo=medium. counter_intuitive=high. [distinct from #5]
8. office_help_widget — help-article feedback widget. control: two-stage widget (Yes/No, then a
   follow-up asks why). treatment: a single consolidated 5-star ratings widget. metric: response
   rate. winner: CONTROL (two-stage ~2.2x the single widget). Kohavi DMKD 2009 §2.2. memo=medium.
   counter_intuitive=high. [distinct from excluded "office online redesign"]

### TREATMENT-WON (6) — real_winner = treatment (asymmetry check; expect sim ~right)
9. alibaba_recommender_set_size — recommender. control: message recommending 3-4 products.
   treatment: message recommending 2 products. metric: purchase probability. winner: TREATMENT
   (inverted-U, 2 optimal, +2.05pp/+67% rel, p<0.001). MSOM 2024 27(1):249-268, n=1.6M. memo=med.
10. low_default_charity_pledge — fundraising. control: high or no suggested default amount.
    treatment: a low suggested default amount. metric: revenue per person. winner: TREATMENT
    (low default $2.62 vs $1.89, p=.003). JMR 2016 53(5):829-846, n=11,508. memo=low.
11. bing_antimalware_ad_removal — SERP. control: page with injected third-party ads/content.
    treatment: block third-party DOM injection (remove the injected clutter). metric:
    time-to-success / revenue. winner: TREATMENT. Kohavi KDD 2014 Rule #1. memo=low. directional.
12. growthrock_add_star_rating — product page. control: page without a review star-rating
    summary near the top. treatment: page with the star-rating summary block added. metric:
    conversion. winner: TREATMENT (+15% conv, 94% sig). Growth Rock case. memo=low.
13. bionicgloves_remove_coupon_fields — checkout. control: cart with two coupon-code fields.
    treatment: both coupon fields removed. metric: revenue. winner: TREATMENT (+24%). GoodUI #1.
    memo=low. credibility: vendor directional (no p-value).
14. blivakker_remove_three_reg_fields — signup. control: full registration form. treatment: form
    with three fields removed. metric: registration conversion. winner: TREATMENT (+10.48%). VWO.
    memo=low. credibility: vendor directional (no sig).

## HELD-OUT (NOT scored in primary; memorization / near-null) — report separately
- iyengar_lepper_jam_assortment — control: 6-jam display. treatment: 24-jam display. winner:
  CONTROL (30% vs 3% purchase). JPSP 2000. memo=HIGH (THE choice-overload study — recitation would
  falsely inflate control-class; hold out, like netflix/highrise).
- bing_social_media_integration — control: SERP w/o social pane. treatment: add FB/Twitter pane.
  winner: CONTROL (near-null, negligible lift vs >$25M cost). HBR 2017. memo=med. borderline
  (no-lift, not measured negative) → held out of the strict primary.

## NEXT PIPELINE (no more sourcing): author (neutral, mechanic-only) → INDEPENDENT adversarial
valence audit (blind to winners where possible; block any arm-asymmetric valence or outcome leak;
apply auditor rewrites verbatim) → seal prereg (canonical SHA before run) → run on box (Groq, pop=50,
seed=42, n_perm=1000) → score control-class (primary) + headline/per-class (secondary).
