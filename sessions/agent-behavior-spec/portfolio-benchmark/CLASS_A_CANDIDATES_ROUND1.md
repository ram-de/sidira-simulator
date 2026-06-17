# Class-A confirmatory portfolio — candidate sourcing (round 1)

Goal: a FRESH, pre-registered, class-A-only (substantive-deliberative) powered run to
confirm the exploratory subset finding (substantive-class 7/10=0.70). Must be BALANCED —
enriched with **control-won** cases — because the sim's localized weakness is a pro-change
tilt (treatment-class 4/4 vs control-class 3/6 within v3 class-A; all 3 misses are
control-won "the change lost" cases: cxl, multistep, office_online).

## CRITICAL TRIAGE FINDING (round 1)
The round-1 agent conflated "simplification/reduction wins" with "control wins." In 9/11
candidates the reduction IS THE TREATMENT arm (remove fields/ads/gate), so they are
**treatment-won** — the sim's pro-change tilt scores them RIGHT and they do NOT stress the
weak spot. Adding them would re-create the treatment-lean-flattered trap the prereg warns
against. Only ONE round-1 case is genuinely control-won.

## Round-1 candidates, triaged by real_winner (the axis that matters)

### CONTROL-WON (the scarce, valuable kind — the change LOST)
- **office_help_widget_multistep_wins** — KEEP (solid). Two-stage Yes/No feedback control
  beat a single 5-star treatment ~2.2x; ~90% ratings drop. Kohavi DMKD 2009 §2.2. Distinct
  from the excluded "office online redesign." memo=medium.

### TREATMENT-WON, well/decently sourced (KEEP as the treatment half — do NOT over-weight)
- **recommender_set_size_alibaba** — HIGH. 2 products beats 3-4 (inverted-U, +2.05pp/+67%
  rel, p<0.001, n=1.6M). MSOM 2024. memo=medium. (reduction-wins, but treatment arm.)
- **low_default_charity_pledge** — HIGH. Low suggested default beats high/none ($2.62 vs
  $1.89/person, p=.003; lower-bar effect). JMR 2016, n=11,508. memo=low.
- **bing_antimalware_ad_removal** — directional. Removing injected ad clutter wins (faster
  success, +$several M/yr). Kohavi KDD 2014 Rule #1. memo=low.
- **growthrock_add_star_rating_summary** — good stats. Adding a review block lifts conv
  +15% (94% sig), rev/session +17% (97%); add-to-cart unchanged (non-obvious). Agency case,
  client unnamed. memo=low. (treatment-won, ADD a block — pure pro-change confirm.)
- **bionicgloves_remove_coupon_fields** — directional, vendor. Removing 2 coupon fields
  +24% rev. GoodUI #1. memo=low. No p-value; low-traffic niche → mild skepticism.
- **blivakker_remove_three_reg_fields** — directional, vendor. Removing 3 signup fields
  +10.48% conv. VWO. memo=low. Vendor self-report, no sig.

### DROPPED (provenance / memorization / not-a-clean-A/B)
- **totango_no_creditcard_trial** — DROP. Aggregated cross-vendor benchmark (~100 vendors),
  not a single controlled split test.
- **uie_guest_checkout ($300M button)** — DROP. memo=HIGH + anecdotal usability study, no
  published controlled experiment, company never named.
- **supermarket_variety_reduction_niche** — DROP. Segment-moderated, no clean single winner.
- **dating_choice_capacity_male_null** — DROP. Gender-heterogeneous (control for men,
  treatment for women); no clean single real_winner.

## Standing tally after round-1 triage
- Solid control-won: 1 (office_help_widget)
- Solid/decent treatment-won: up to 6 (alibaba, charity strongest; bing; growthrock;
  bionicgloves, blivakker vendor-flagged)
- GAP: need ~6-8 more CONTROL-WON "the intuitive change backfired / status quo won" cases
  to balance. This is the genuine scarcity (publication bias: people blog wins). Round 2
  targets exactly this from the Kohavi corpus / "Trustworthy Online Controlled Experiments"
  book / Microsoft ExP / Booking.com / Netflix / academic field experiments.
