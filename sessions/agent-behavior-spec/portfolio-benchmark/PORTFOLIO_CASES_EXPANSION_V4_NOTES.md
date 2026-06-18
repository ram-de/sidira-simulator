# V4 Expansion — Authoring Notes

Authored 2026-06-17/18 under strict blinding discipline. Each scored case's
real winner was verified from a primary or first-party source via an
independent web-research pass **before** the winner was locked. Cases whose
claimed winner could not be verified — or that the primary source
contradicts — were **held back** (`verify: false`), not scored, per the
no-fabrication rule.

Companion file: `PORTFOLIO_CASES_EXPANSION_V4.json` (V3 scored-set schema).

## Scored cases — verified winner + citation

| id | real_winner | metric | source (primary) | confidence |
|----|-------------|--------|------------------|------------|
| apparel_hide_discount_surfacing | treatment (no discount-surfacing) | ASP / margin / conversion | Ngwe, Ferreira & Teixeira, JMR 2019 56(6):944-959, DOI 10.1177/0022243719865516 | HIGH (dir); magnitudes institutional (HBS) |
| gift_certificate_expiry_window | control (3-week window) | redemption rate | Shu & Gneezy, JMR 2010 47(5):933-944, DOI 10.1509/jmkr.47.5.933 | HIGH (31% vs 6%, n=64) |
| referral_reward_sender_certainty | treatment (uncertain sender reward) | # referrals | Li, Belo & Li, Mgmt Sci 2024, DOI 10.1287/mnsc.2024.05685 | HIGH (+20.9%, from full-text MS) |
| referral_reward_recipient_certainty | control (fixed recipient reward) | # referrals | Li, Belo & Li, Mgmt Sci 2024, DOI 10.1287/mnsc.2024.05685 | HIGH (-12.3%; sign flip verified) |
| time_scarcity_promo_framing | treatment (no urgency) | WTP / purchase intent | Hmurovic, Lamberton & Goldsmith, JMR 2023 60(2):299-328, DOI 10.1177/00222437221118856 | HIGH (dir); effect sizes paywalled |
| product_image_hover_zoom | treatment (no zoom) | purchase likelihood | Naegelein, Spann & Molitor, DSS 2019 121:109-120 | HIGH (dir); magnitude paywalled |
| homepage_carousel_item_count | treatment (16 items) | engagement | Kohavi/Tang/Xu 2020 (SRM ch.); Fabijan et al., KDD 2019 | HIGH (SRM-corrected +3.3%) |
| donation_banner_only_word | treatment ("Only ...") | $ / impression | Wikimedia Meta, Fundraising 2010/Banner testing (Dec 28 test) | dir HIGH; significance unconfirmed |
| upload_dropzone_border_button_weight | treatment (thicker border, bigger button) | upload completion | Danny Coates, Firefox Test Pilot (Medium), Oct 2 2017 | HIGH (37.47% vs 36.18%, small) |
| vendor_listing_popularity_count | treatment (show count) | clicks/contacts | Tucker & Zhang, Mgmt Sci 2011 57(5):828-842, DOI 10.1287/mnsc.1110.1312 | HIGH (DiD 0.16-0.18; niche 0.35-0.47) |

## Cases I could NOT verify — HELD BACK (verify: false, not scored)

- **loyalty_stretch_goal_offer (S4).** The supplied winner (control) is
  **contradicted** by the primary source. Wang, Lewis, Cryder & Sprigg
  (Marketing Science 2016 35(4):565-575, n=95,532) state in the published
  abstract: *"the promotion led to increased purchasing in the post-promotion
  period."* The stretch-goal **treatment raised net post-period spend** — so
  control did not win on net. The "treatment lowers spend" story holds **only
  for the 80% goal-failure subgroup**; the 20% who hit the goal spent more, and
  the net treatment effect was positive. Not scored. If ever re-scoped to the
  goal-failure subgroup alone, re-verify the in-text coefficients (paywalled)
  first.

- **video_ad_preroll_vs_postroll (S7).** **Misattribution.** Kohavi et al. 2009
  (Controlled Experiments on the Web, DMKD 18(1):140-181) contains **no**
  pre-roll-vs-post-roll video-ad return-rate experiment (full text read; zero
  hits for pre-roll/post-roll/video-ad ordering). The paper's actual ad example
  is the MSN home-page extra-offers test (+3 offer slots -> CTR -0.38%, p=0.02,
  scrapped) — which is **already** in V3 as `msn_homepage_extra_offers`. No
  peer-reviewed controlled experiment found showing post-roll beats pre-roll on
  net return. Not scored.

## Latent-winner cases needing extra blinding care

- **S4 loyalty_stretch_goal_offer** — the FLAGGED latent-winner case. Net
  vs goal-attainment-subgroup effects differ in **sign**, which is exactly why
  it is held back here. Any future inclusion must (a) fix the unit of analysis
  (net vs subgroup) and (b) never let the description hint at goal attainment,
  since attainment is the mediator that flips the sign. Whole-experiment net
  winner = treatment, not control.

- **time_scarcity_promo_framing (S5)** — a **null/backfire**: the control-side
  expectation (urgency lifts response) is the lay prior, but online the
  no-urgency arm wins on WTP. Marked counter_intuitive. The description states
  identical economics in both arms so the only difference is the
  countdown/urgency mechanic — no valence on either side.

## Blinding / valence notes

- Both arms of every scored case are mechanic-only, parallel, symmetric in
  detail. No evaluative adjectives, no outcome numbers, no "winner of N."
- The two paired referral cases (sender / recipient) use **identical** arm
  wording except for who receives the reward — so the sign flip cannot be
  inferred from copy valence; only the party differs.
- Highest memorization risk in this batch: `donation_banner_only_word`
  (retold CRO anecdote) and `apparel_hide_discount_surfacing` (HBS-publicized).
  Most others are obscure peer-reviewed field experiments (low memo risk). If
  the sim aces the two famous ones but flunks the obscure ones, suspect
  recitation.

## Citation corrections found during verification (for the record)

- S1 paper is "The Impact of Increasing Search Frictions on Online Shopping
  Behavior" (JMR 2019), **not** "Walking the Tightrope" (a different
  Ngwe/Teixeira paper).
- S6 first author is **Philipp** Naegelein (not Patrick). Zoom hurt, but the
  paper's separate "alternative photos" technology helped — the case isolates
  hover-zoom only; do not conflate.
- S12: niche vendors gain **disproportionately more**, not exclusively;
  broad-appeal vendors also gained. No winner-take-all flock to mainstream.
- S3 authors are Andy Tao Li, Rodrigo **Belo**, Ting Li.

## Balance

Scored 10: 2 control-won, 8 treatment-won. Skewed treatment-won because cases
were chosen for VALIDITY, not balance. Recompute the always-treatment baseline
when merging into the full scored portfolio so the combined headline dir_acc is
held to the correct floor.
