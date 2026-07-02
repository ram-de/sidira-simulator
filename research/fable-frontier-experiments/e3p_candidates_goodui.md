# E3-P Candidate Audit Log — Source (1): GoodUI public evidence / test database

Assembled 2026-07-01, after prereg seal, per PREREG_E3P_BACKLOG_PREVALENCE.md "Case sourcing".
Assembler: GoodUI case assembler (this file is the anti-cherry-picking log; every candidate
encountered gets a line).

**BLINDING NOTE — the prediction runner must NOT read this file until predictions are sealed.**
GoodUI post URLs and titles frequently contain outcome text; they are reproduced here for audit
completeness. For the same reason, source URLs are withheld from `e3p_backlog_goodui.json`
(replaced by opaque audit-log refs); the id→URL mapping lives here and in the truths file.
Candidate one-line descriptions below are written outcome-free; exclusion reasons never reference
a case's result direction.

**Truths seal:** `e3p_truths_goodui.json` sha256 =
`6bb1198a2daa3d7138e6dbc9e5ba1cf796c962f3fce437595dcac5463a3b05e9` (also in e3p_truths_goodui.sha256),
computed at assembly completion, before any pipeline run.

## Traversal order (fixed, recorded as executed)

1. goodui.org/leaks (listing page 1 + 2 detail pages fetched) — Section B.
2. goodui.org current patterns/tests database (index pages) — Section A.
3. Legacy free "GoodUI Evidence" database (115 tests; via Wayback Machine, index archived 2019) — Section E.
4. goodui.org/post-tags/results/ — the 31 free blog write-ups, processed strictly in listing order
   (reverse-chronological, an outcome-neutral order fixed by the site) — Section C.

**Inclusion cap rule:** tasking target = 12–18 included cases, taken in encounter order.
The 18th inclusion occurred at C27 (blog post 18 of 31); every subsequent candidate is logged
as CAP-CUT (not assessed for inclusion because the encounter-order cap was reached), except where
a candidate independently fails the criteria, in which case the merit reason is also given.

## Section A — Current patterns/tests database (goodui.org/patterns/, /tests/, /evidence/ → same app)

Category determination: individual test pages (e.g. /patterns/41/tests/657/) hide all results
("X.X%", "Join to see the effect") behind a paid membership ($60+/mo). Control/treatment detail and
outcomes are not freely accessible. All entries encountered on the free index are excluded for the
same reason: RESULTS PAYWALLED (fails "directional outcome publicly reported" via free access).

| # | Source | Candidate (one line) | Decision |
|---|--------|----------------------|----------|
| A01 | goodui.org/patterns/41/tests/657/ | Sticky Call To Action on Obsbygg.no (1,238,014 visitors) | EXCLUDED — results paywalled |
| A02 | goodui.org/patterns/41/tests/656/ | Sticky Call To Action on Obs.no (675,173 visitors) | EXCLUDED — results paywalled |
| A03 | goodui.org/patterns/113/tests/655/ | More Or Fewer Plans | EXCLUDED — results paywalled |
| A04 | goodui.org/patterns/11/tests/654/ | Gradual Reassurance | EXCLUDED — results paywalled |
| A05 | goodui.org/patterns/41/tests/653/ | Sticky Call To Action on Kensingtontours.com (312,834 visitors) | EXCLUDED — results paywalled |
| A06 | goodui.org/patterns/26/tests/652/ | Cart Reminder And Recently Viewed on Kay.com | EXCLUDED — results paywalled |
| A07 | goodui.org/patterns/37/tests/651/ | List Or Grid View | EXCLUDED — results paywalled |
| A08 | goodui.org/patterns/37/tests/650/ | List Or Grid View | EXCLUDED — results paywalled |
| A09 | goodui.org/patterns/141/tests/649/ | Square or Rounded Buttons | EXCLUDED — results paywalled |
| A10 | goodui.org/patterns/82/tests/648/ | Onboarding Callouts | EXCLUDED — results paywalled |
| A11 | goodui.org/patterns/79/tests/647/ | Product Highlights | EXCLUDED — results paywalled |
| A12 | goodui.org/patterns/79/tests/646/ | Product Highlights | EXCLUDED — results paywalled |
| A13 | goodui.org/patterns/34/tests/645/ | Open In A New Tab | EXCLUDED — results paywalled |
| A14 | goodui.org/patterns/34/tests/644/ | Open In A New Tab | EXCLUDED — results paywalled |
| A15 | goodui.org/patterns/135/tests/643/ | Product Categories | EXCLUDED — results paywalled |

(The /tests/ index continues to older entries, all equally paywalled; not further enumerated.)

## Section B — Leaks (goodui.org/leaks/, 112 total)

Category determination (verified on two full detail pages, B21 and B10): leak write-ups describe
observed variants on major sites concretely, but publish NO metric of any kind — "No specific
metrics, percentages, or conversion numbers are provided" — and the outcome is GoodUI's inference
from later observing which variant the company rolled out. This fails two inclusion criteria:
"a primary metric named" and "a directional outcome publicly reported" (a rollout observation is a
decision, not a reported measurement). All leaks are excluded on this category basis. Page-1
entries and detail pages actually encountered are logged individually below; pages 2–6 (~90 more
leaks) were not individually enumerated after the category determination — recorded as an assembly
limitation. Rollout-status labels shown on the listing are deliberately omitted from this log.

| # | Source (goodui.org/leaks/…) | Candidate (one line) | Decision |
|---|-----------------------------|----------------------|----------|
| B01 | etsy-tests-black-vs-yellow-add-to-cart-buttons/ | Etsy: black vs yellow add-to-cart buttons | EXCLUDED — leaks category (no metric; outcome = rollout inference) |
| B02 | walmart-a-b-tests-and-rolls-out-this-new-product-page-layout/ | Walmart: new product page layout | EXCLUDED — leaks category |
| B03 | etsy-fails-to-replicate-airbnbs-customer-reviews-banner/ | Etsy: customer reviews banner (Airbnb-style) | EXCLUDED — leaks category |
| B04 | etsy-a-b-c-tests-category-links-vs-breadcrumbs/ | Etsy: category links vs breadcrumbs (A/B/C) | EXCLUDED — leaks category |
| B05 | walmart-runs-a-potentially-confounded-button-color-a-b-test/ | Walmart: button color test (confounded) | EXCLUDED — leaks category |
| B06 | walmarts-2nd-take-on-its-new-navigation-seems-to-have-worked/ | Walmart: navigation redesign, 2nd attempt | EXCLUDED — leaks category |
| B07 | etsy-a-b-tests-this-high-contrast-button-style/ | Etsy: high contrast button style | EXCLUDED — leaks category |
| B08 | etsy-a-b-tests-3-footer-variations-with-their-story-and-customer-support-links/ | Etsy: 3 footer variations | EXCLUDED — leaks category |
| B09 | amazon-a-b-tests-this-floating-product-page-navigation-that-is-accepted/ | Amazon: floating product page navigation | EXCLUDED — leaks category |
| B10 | airbnb-a-b-tests-hidden-vs-shown-price-totals/ | Airbnb: hidden vs shown price totals (detail page fetched; confirmed no metrics) | EXCLUDED — leaks category |
| B11 | reverbs-ui-redesign-succeeds-in-this-a-b-test/ | Reverb: UI redesign | EXCLUDED — leaks category |
| B12 | amazon-a-b-tests-and-rejects-this-product-description-format/ | Amazon: product description format | EXCLUDED — leaks category |
| B13 | walmart-ran-this-big-navigation-a-b-test-with-8-confounded-ui-changes-rejecting-it/ | Walmart: big navigation test, 8 changes | EXCLUDED — leaks category |
| B14 | booking-a-b-tests-a-highly-prominent-deals-page-and-possibly-rejects-it/ | Booking: prominent deals page | EXCLUDED — leaks category |
| B15 | one-possible-reason-why-etsys-floating-buy-box-ui-was-rejected/ | Etsy: floating buy box | EXCLUDED — leaks category |
| B16 | booking-a-b-tests-rounded-corners-on-multiple-elements/ | Booking: rounded corners | EXCLUDED — leaks category |
| B17 | amazon-a-b-c-d-e-tests-and-discovers-better-product-information-for-their-listing-tiles/ | Amazon: listing tile product info (A/B/C/D/E) | EXCLUDED — leaks category |
| B18 | booking-a-b-c-d-tests-and-detects-a-better-calendar-widget/ | Booking: calendar widget (A/B/C/D) | EXCLUDED — leaks category |
| B19 | amazon-a-b-tests-and-rejects-wider-and-smaller-product-titles/ | Amazon: wider/smaller product titles | EXCLUDED — leaks category |
| B20 | walmart-a-b-tests-shipping-choices-vs-shipping-reassurances/ | Walmart: shipping choices vs reassurances | EXCLUDED — leaks category |
| B21 | netflix-a-b-tests-and-rejects-free-trials/ | Netflix (Canada, 2019): 30/14/7-day free trial vs payment-first signup (detail page fetched; confirmed no metrics) | EXCLUDED — leaks category |
| B22 | amazon-a-b-tests-and-rolls-out-product-reassurances/ | Amazon: product reassurances (encountered via search listing only) | EXCLUDED — leaks category |

## Section E — Legacy free "GoodUI Evidence" database (115 tests, 2013–2018)

Category determination: the legacy evidence app (goodui.org/evidence/) was free, but it was a
single-page app whose per-test detail (screenshots, control/treatment description, per-arm data)
loaded from an AJAX endpoint `/evidence/test/<id>`. That endpoint (a) now redirects to the current
paywalled patterns app on the live site, and (b) is essentially absent from the Wayback Machine
(only 6 captures exist, all from 2024, and they contain only PHP deprecation errors — verified on
/evidence/test/23). The freely accessible archived index provides only each test's short title and
an effect dot. Every test therefore fails "control and treatment described concretely enough to
translate" from free content, and all 115 are excluded on that basis. Where the same test is
concretely described in a free blog write-up, it re-enters through Section C (cross-referenced).
Archived index used: web.archive.org capture of goodui.org/evidence/ (2019).

| # | Candidate (title from archived index) | Decision |
|---|----------------------------------------|----------|
| E001 | Test 1: Single VS. Multi Page Form | EXCLUDED — detail page inaccessible (see section header) |
| E002 | Test 2: Crossed Out List Price Anchor | EXCLUDED — detail page inaccessible (see section header) |
| E003 | Test 3: Without & With Comments | EXCLUDED — detail page inaccessible (see section header) |
| E004 | Test 4: Buy Now VS. Contact Buttons | EXCLUDED — detail page inaccessible (see section header) |
| E005 | Test 5: What It’s Worth | EXCLUDED — detail page inaccessible (see section header) |
| E006 | Test 6: Yes-I-Want-To Benefit Buttons | EXCLUDED — detail page inaccessible (see section header) |
| E007 | Test 7: A Learn More Link, No More | EXCLUDED — detail page inaccessible (see section header) |
| E008 | Test 8: Hello, With A Face | EXCLUDED — detail page inaccessible (see section header) |
| E009 | Test 9: Click To See Email Field | EXCLUDED — detail page inaccessible (see section header) |
| E010 | Test 10: With & Without Fields | EXCLUDED — detail page inaccessible (see section header) |
| E011 | Test 11: No Password Confirmation, No Birthday Fields | EXCLUDED — detail page inaccessible (see section header) |
| E012 | Test 12: Featured Blog Posts, No More | EXCLUDED — detail page inaccessible (see section header) |
| E013 | Test 13: Small Preview / Teaser Link | EXCLUDED — detail page inaccessible (see section header) |
| E014 | Test 14: Words & Forms | EXCLUDED — detail page inaccessible (see section header) |
| E015 | Test 15: Words & Forms II | EXCLUDED — detail page inaccessible (see section header) |
| E016 | Test 16: Hamburger Vs. Hamburger + Menu | EXCLUDED — detail page inaccessible (see section header) |
| E017 | Test 17: Hamburger Vs. Menu | EXCLUDED — detail page inaccessible (see section header) |
| E018 | Test 18: Hamburger Vs. Menu II | EXCLUDED — detail page inaccessible (see section header) |
| E019 | Test 19: Time Delayed Modal | EXCLUDED — detail page inaccessible (see section header) |
| E020 | Test 20: Without "Try" Buttons | EXCLUDED — detail page inaccessible (see section header) |
| E021 | Test 21: Endless Vs. Limited Search Results | EXCLUDED — detail page inaccessible (see section header) |
| E022 | Test 22: Lots Of Video Testimonials | EXCLUDED — detail page inaccessible (see section header) |
| E023 | Test 23: Product Usage Story | EXCLUDED — detail page inaccessible (see section header) |
| E024 | Test 24: Auto-Renewal Opt-Out | EXCLUDED — detail page inaccessible (see section header) |
| E025 | Test 25: Room Type Choice Before Signup | EXCLUDED — detail page inaccessible (see section header) |
| E026 | Test 26: Without Social Buttons | EXCLUDED — detail page inaccessible (see section header) |
| E027 | Test 27: Gradual Book Covers | EXCLUDED — detail page inaccessible (see section header) |
| E028 | Test 28: No Company Field | EXCLUDED — detail page inaccessible (see section header) |
| E029 | Test 29: More Focused Shopping Cart | EXCLUDED — detail page inaccessible (see section header) |
| E030 | Test 30: I Even Use My Own Credit Card | EXCLUDED — detail page inaccessible (see section header) |
| E031 | Test 31: 60,000 People Use This | EXCLUDED — detail page inaccessible (see section header) |
| E032 | Test 32: Faded Dashboard Just One Click Away | EXCLUDED — detail page inaccessible (see section header) |
| E033 | Test 33: Blog Samples | EXCLUDED — detail page inaccessible (see section header) |
| E034 | Test 34: Gradually Engaging Quiz | EXCLUDED — detail page inaccessible (see section header) |
| E035 | Test 35: Cart Reminders | EXCLUDED — detail page inaccessible (see section header) |
| E036 | Test 36: Gradual Reassurance | EXCLUDED — detail page inaccessible (see section header) |
| E037 | Test 37: Send Or Receive 500 For 4.99 | EXCLUDED — detail page inaccessible (see section header) [covered by blog post C37 (cap-cut)] |
| E038 | Test 38: Inline Form VS. Overlay Form | EXCLUDED — detail page inaccessible (see section header) |
| E039 | Test 39: All Fields VS. Progressive Fields | EXCLUDED — detail page inaccessible (see section header) |
| E040 | Test 40: Order VS. Upload Buttons | EXCLUDED — detail page inaccessible (see section header) |
| E041 | Test 41: Segmented Vs. Inline Form | EXCLUDED — detail page inaccessible (see section header) |
| E042 | Test 42: No Coupon Code | EXCLUDED — detail page inaccessible (see section header) |
| E043 | Test 43: Ratings & Reviews | EXCLUDED — detail page inaccessible (see section header) |
| E044 | Test 44: 9 Reasons For Best Pet Care | EXCLUDED — detail page inaccessible (see section header) |
| E045 | Test 45: Removing Fearful Copy | EXCLUDED — detail page inaccessible (see section header) |
| E046 | Test 46: More Calls To Action | EXCLUDED — detail page inaccessible (see section header) |
| E047 | Test 47: Directional Testimonials | EXCLUDED — detail page inaccessible (see section header) |
| E048 | Test 48: Beneﬁt & Bio Testimonials | EXCLUDED — detail page inaccessible (see section header) |
| E049 | Test 49: Smarter Tipping Option | EXCLUDED — detail page inaccessible (see section header) |
| E050 | Test 50: Thank You In Advance | EXCLUDED — detail page inaccessible (see section header) |
| E051 | Test 51: Secure Badge | EXCLUDED — detail page inaccessible (see section header) |
| E052 | Test 52: You Take Beautiful Photos | EXCLUDED — detail page inaccessible (see section header) |
| E053 | Test 53: Customer Reviews | EXCLUDED — detail page inaccessible (see section header) |
| E054 | Test 54: Social Download Counts | EXCLUDED — detail page inaccessible (see section header) |
| E055 | Test 55: Exposed Navigation | EXCLUDED — detail page inaccessible (see section header) |
| E056 | Test 56: Get More Reviews Headline | EXCLUDED — detail page inaccessible (see section header) |
| E057 | Test 57: Modal Upsell | EXCLUDED — detail page inaccessible (see section header) |
| E058 | Test 58: Madlib Signup Form | EXCLUDED — detail page inaccessible (see section header) |
| E059 | Test 59: Conversational Forms | EXCLUDED — detail page inaccessible (see section header) |
| E060 | Test 60: Words & Forms III | EXCLUDED — detail page inaccessible (see section header) |
| E061 | Test 61: Single Vs Multiple Step Checkout | EXCLUDED — detail page inaccessible (see section header) |
| E062 | Test 62: Single Vs. Multiple Step Checkout II | EXCLUDED — detail page inaccessible (see section header) |
| E063 | Test 63: Authentic Product Photos | EXCLUDED — detail page inaccessible (see section header) [covered by blog post C29 (cap-cut)] |
| E064 | Test 64: Floating Navigation | EXCLUDED — detail page inaccessible (see section header) |
| E065 | Test 65: Up-front Form | EXCLUDED — detail page inaccessible (see section header) [covered by blog post C30 (cap-cut)] |
| E066 | Test 66: 3 Vs. 4 Checkout Steps | EXCLUDED — detail page inaccessible (see section header) [covered by blog post C31 (cap-cut)] |
| E067 | Test 67: Benefit Headline: Fastest | EXCLUDED — detail page inaccessible (see section header) |
| E068 | Test 68: Benefit Headline: Easiest | EXCLUDED — detail page inaccessible (see section header) |
| E069 | Test 69: Anchors Vs. Modals | EXCLUDED — detail page inaccessible (see section header) [covered by blog post C28 (cap-cut)] |
| E070 | Test 70: Most To Least Expensive Plans | EXCLUDED — detail page inaccessible (see section header) [covered by blog post C27 → INCLUDED as gui_18] |
| E071 | Test 71: With Profile Pictures | EXCLUDED — detail page inaccessible (see section header) [covered by blog post C26 → INCLUDED as gui_17] |
| E072 | Test 72: Passive Benefits | EXCLUDED — detail page inaccessible (see section header) [covered by blog post C25 → INCLUDED as gui_16] |
| E073 | Test 73: List Of Benefits | EXCLUDED — detail page inaccessible (see section header) [covered by blog post C24 → INCLUDED as gui_15] |
| E074 | Test 74: Publish Engaging Polls | EXCLUDED — detail page inaccessible (see section header) [covered by blog post C22 → INCLUDED as gui_13] |
| E075 | Test 75: Headline | EXCLUDED — detail page inaccessible (see section header) [covered by blog post C23 → INCLUDED as gui_14] |
| E076 | Test 76: Full Height Email Grab | EXCLUDED — detail page inaccessible (see section header) |
| E077 | Test 77: Top Aligned Labels With Example Inputs | EXCLUDED — detail page inaccessible (see section header) |
| E078 | Test 78: Almost Completed Signup | EXCLUDED — detail page inaccessible (see section header) |
| E079 | Test 79: Three Reassuring Bullets | EXCLUDED — detail page inaccessible (see section header) |
| E080 | Test 80: Exposed Call Button | EXCLUDED — detail page inaccessible (see section header) |
| E081 | Test 81: Bypassing Form Fields | EXCLUDED — detail page inaccessible (see section header) |
| E082 | Test 82: Postponed Modal With Input Field | EXCLUDED — detail page inaccessible (see section header) |
| E083 | Test 83: Beneficial Testimonial | EXCLUDED — detail page inaccessible (see section header) |
| E084 | Test 84: Usage Counts As Social Proof | EXCLUDED — detail page inaccessible (see section header) |
| E085 | Test 85: No Canned Response Textarea | EXCLUDED — detail page inaccessible (see section header) |
| E086 | Test 86: No Phone Field | EXCLUDED — detail page inaccessible (see section header) |
| E087 | Test 87: Contact Benefits | EXCLUDED — detail page inaccessible (see section header) |
| E088 | Test 88: What It's Worth II | EXCLUDED — detail page inaccessible (see section header) |
| E089 | Test 89: Checkout Testimonials | EXCLUDED — detail page inaccessible (see section header) |
| E090 | Test 90: Centered Form | EXCLUDED — detail page inaccessible (see section header) |
| E091 | Test 91: Multiple Steps | EXCLUDED — detail page inaccessible (see section header) |
| E092 | Test 92: Benefit Headline: Empowering | EXCLUDED — detail page inaccessible (see section header) |
| E093 | Test 93: Exposed Top Content Links | EXCLUDED — detail page inaccessible (see section header) |
| E094 | Test 94: Exposed Pulldown Options - Agent Type | EXCLUDED — detail page inaccessible (see section header) |
| E095 | Test 95: Bulleted Reassurances  | EXCLUDED — detail page inaccessible (see section header) |
| E096 | Test 96: Local Is Better | EXCLUDED — detail page inaccessible (see section header) |
| E097 | Test 97: Clear Response Times | EXCLUDED — detail page inaccessible (see section header) |
| E098 | Test 98: More Visible Response Times | EXCLUDED — detail page inaccessible (see section header) |
| E099 | Test 99: Online Presence | EXCLUDED — detail page inaccessible (see section header) |
| E100 | Test 100: Canned Response Retest | EXCLUDED — detail page inaccessible (see section header) |
| E101 | Test 101: Inline Link Nudge | EXCLUDED — detail page inaccessible (see section header) |
| E102 | Test 102: Response Rate & Time | EXCLUDED — detail page inaccessible (see section header) |
| E103 | Test 103: Gradual Language Types | EXCLUDED — detail page inaccessible (see section header) |
| E104 | Test 104: Upload Benefits | EXCLUDED — detail page inaccessible (see section header) |
| E105 | Test 105: Explanation Tooltips | EXCLUDED — detail page inaccessible (see section header) |
| E106 | Test 106: Three Reassurances | EXCLUDED — detail page inaccessible (see section header) |
| E107 | Test 107: Exposed Individual EBooks | EXCLUDED — detail page inaccessible (see section header) |
| E108 | Test 108: Centered Form II | EXCLUDED — detail page inaccessible (see section header) |
| E109 | Test 109: Canned Response | EXCLUDED — detail page inaccessible (see section header) |
| E110 | Test 110: Exposed Menu Options | EXCLUDED — detail page inaccessible (see section header) |
| E111 | Test 111: Full Height Email Grab II | EXCLUDED — detail page inaccessible (see section header) |
| E112 | Test 112: Canned Response II | EXCLUDED — detail page inaccessible (see section header) |
| E113 | Test 113: Instant Refresh Results | EXCLUDED — detail page inaccessible (see section header) |
| E114 | Test 114: Explained Course Links With Descriptions | EXCLUDED — detail page inaccessible (see section header) |
| E115 | Test 115: Beneficial Testimonials | EXCLUDED — detail page inaccessible (see section header) |

## Section C — Free blog write-ups (goodui.org/post-tags/results/, 31 posts, listing order)

These are GoodUI's published A/B test write-ups (client tests and community-shared tests) with
concrete control/treatment descriptions, named metrics, and publicly reported outcomes — the only
GoodUI surface meeting all four inclusion criteria for free. Posts processed strictly in the
listing order of /post-tags/results/. Multi-test posts yield one candidate per distinct experiment,
in within-post order of appearance.

| # | Source (goodui.org/blog/…) | Candidate (one line) | Decision |
|---|----------------------------|----------------------|----------|
| C01 | why-did-thomasnet-reject-a-registration-wall-a-b-test-with-a-record-1135-to-signups/ | Thomasnet.com article pages: full article vs registration wall; signups primary, engagement (profile visits) tracked | INCLUDED → gui_01 |
| C02 | 12-landing-page-patterns-for-42-more-leads-on-kensingtontours.com/ | KensingtonTours.com: 12-change landing page redesign, split test on paid traffic; completed leads | INCLUDED → gui_02 |
| C03 | 6-signup-form-ui-changes-with-17-more-signups-for-thomasnet/ | Thomasnet.com supplier signup page: 6-change redesign; signups | INCLUDED → gui_03 |
| C04 | 13-course-landing-page-ui-changes-with-49-enrollments-for-designlab/ | Designlab course landing page: 13-change redesign | EXCLUDED — not an A/B experiment: changes were rolled out directly and evaluated as a before/after comparison ("decided to simply roll them out... conversion rate compared before and after") |
| C05 | 4-checkout-ui-changes-for-a-highly-significant-1-sales-on-menufy-com/ | Menufy.com checkout tip section: 4-change variation; sales (thank-you page visits) | INCLUDED → gui_04 |
| C06 | 6-landing-page-changes-for-30-signups-on-bomgar-com/ | Bomgar.com landing page: 6-change variation; signups (next-page visits) | INCLUDED → gui_05 |
| C07 | insignificant-significance-why-reverb-com-rejected-a-winning-a-b-test/ | Reverb.com product page message form: blank textarea vs canned default copy; sales primary, negotiations started tracked | INCLUDED → gui_06 |
| C08 | how-normanrecords-com-replicated-the-no-coupon-fields-pattern-successfully/ (referenced comparison test) | Adoramapix.com checkout: visible coupon field vs removed/de-emphasized; sales; baseline ~70% given | INCLUDED → gui_07 (limitation: variation described at pattern level, no screenshot for this site) |
| C09 | how-normanrecords-com-replicated-the-no-coupon-fields-pattern-successfully/ | Normanrecords.com checkout: visible coupon field vs 'add a voucher code' link; sales | INCLUDED → gui_08 |
| C10 | 7-experiments-we-ran-this-month-jan-2018/ (item 1) | Examine.com pricing page: 3 extra purchase buttons vs learn-more only | EXCLUDED — no outcome publicly reported in free content (result lives on paywalled pattern page) |
| C11 | 7-experiments-we-ran-this-month-jan-2018/ (item 2) | Trydesignlab.com checkout: pay-later message added | EXCLUDED — no outcome publicly reported in free content |
| C12 | 7-experiments-we-ran-this-month-jan-2018/ (item 3) | Akademiafotografii.pl course page: pay-later copy above lead form | EXCLUDED — no outcome publicly reported in free content |
| C13 | 7-experiments-we-ran-this-month-jan-2018/ (item 4) | Trydesignlab.com course page: added bottom call to action | EXCLUDED — no outcome publicly reported in free content |
| C14 | 7-experiments-we-ran-this-month-jan-2018/ (item 5) | Vivareal.com.br search results: hover-only property CTAs (desktop) | EXCLUDED — no outcome publicly reported in free content |
| C15 | 7-experiments-we-ran-this-month-jan-2018/ (item 6) | Normanrecords.com: no coupon fields | EXCLUDED — duplicate of C09 |
| C16 | 7-experiments-we-ran-this-month-jan-2018/ (item 7) | Reverb.com: canned response | EXCLUDED — duplicate of C07 |
| C17 | 7-pricing-screen-ui-changes-for-28-sales-on-examine-com/ | Examine.com pricing screen: 7-change variation; sales | INCLUDED → gui_09 |
| C18 | a-flawless-copy-paste-test-how-glass-net-replicated-the-canned-response-pattern/ (referenced prior test) | Vivareal.com.br listing contact form: canned default copy in message textarea; leads | INCLUDED → gui_10 |
| C19 | a-flawless-copy-paste-test-how-glass-net-replicated-the-canned-response-pattern/ | Glass.net quote-request form: canned default copy in message textarea; leads | INCLUDED → gui_11 |
| C20 | pattern-31-instant-results-increased-leads-for-vivareal-com-br/ | Vivareal.com.br search filters: search-button refresh vs instant results; leads | INCLUDED → gui_12 |
| C21 | getting-a-higher-ab-test-win-rate-using-patterns-2017-q2-performance-report/ | Aggregate quarterly win-rate report over 15 tests | EXCLUDED — aggregate report, no individual experiment described |
| C22 | evidence-74-publish-engaging-polls/ | Poll-app.com homepage headline: 'Ask Questions. Get Answers.' vs 'Publish Engaging Polls On Facebook'; signup starts | INCLUDED → gui_13 |
| C23 | evidence-74-publish-engaging-polls/ (referenced companion Test #75) | Poll-app.com homepage headline: same control vs 'Polls For Your Facebook Page & Timeline'; signup starts | INCLUDED → gui_14 |
| C24 | evidence-73-list-of-benefits/ | Theorytestpro.co.uk dashboard instructor module: paragraph vs bullets + copy + button label; leads (instructor page visits) | INCLUDED → gui_15 |
| C25 | evidence-72-passive-benefits/ | Findsomeone.co.nz homepage: 4-box layout vs single-column passive-benefit message; signup intent (step-2 visits) | INCLUDED → gui_16 |
| C26 | evidence-71-social-proof-that-didnt-work/ | Findsomeone.co.nz homepage: member profile photos added as social proof; searches | INCLUDED → gui_17 |
| C27 | evidence-70-least-or-most-expensive-plans-first/ | Uptowork.com pricing page: plans least-expensive-first vs most-expensive-first; revenue / plan-mix | INCLUDED → gui_18 — **CAP REACHED (18 inclusions)** |
| C28 | evidence-69-anchors-vs-modals/ | Digitalmarketer.com: CTA buttons anchor-scroll to form vs launch modal; leads | CAP-CUT — not assessed (encounter-order cap reached) |
| C29 | evidence-63-a-possible-23-adds-to-cart/ | Yotpo customer product page: customer Instagram photos added; adds to cart | CAP-CUT — not assessed |
| C30 | evidence-65-a-possible-4-9-to-leads-from-up-front-forms/ | Digitalmarketer.com: 2-step postponed form vs up-front form; leads | CAP-CUT — not assessed |
| C31 | evidence-66-a-possible-5-5-to-sales-from-an-extra-checkout-step/ | Widerfunnel client checkout: 3 steps vs 4 steps; sales | CAP-CUT — not assessed |
| C32 | results-natural-language-forms/ | Reader poll on natural-language vs top-aligned forms | EXCLUDED — not an experiment (opinion poll, 230 survey responses) |
| C33 | what-we-know-already-sept-2016/ | Monthly certainty/observation list | EXCLUDED — aggregate report, no individual experiment described |
| C34 | adding-social-counts-increases-conversions/ | Meta-observation pooling 2 unnamed tests on social counts | EXCLUDED — no individual case with concrete control/treatment |
| C35 | reassuring-for-a-possible-17-to-sales/ | Covenanteyes.com homepage: six reassurances (+ other changes); paid account signups | CAP-CUT — not assessed |
| C36 | 20-sale-starts-from-gradual-reassurance/ | Wpallimport.com homepage: video vs gradual-reassurance interaction; sale starts | CAP-CUT — not assessed |
| C37 | evidence-37-a-possible-8-8-to-sales/ | Onlinefaxes.com: quantity anchor ('500 pages') shown before price; sales | CAP-CUT — not assessed |
| C38 | the-signup-story-with-12-to-signups/ | Undisclosed site, 2 of 8 variations: with vs without 6-step 'How It Works' story; signups | CAP-CUT — not assessed |
| C39 | a-58782-more-annoying-modal-popup/ | Undisclosed site: floating footer vs delayed modal popup; signup rate primary | EXCLUDED — primary-metric outcome not in free content (paywalled Datastories issue); the freely reported number is an incidental close-rate on a comparison the author flags as unfair |
| C40 | insight-a-simple-way-to-increase-scroll-rate/ | Same site as C39, variations B vs C: expectation-setting headline 'Before We Show You…'; signup rate primary, scroll rate secondary | CAP-CUT — not assessed |

## Counts

- Candidates logged: 15 (A) + 22 (B) + 115 (E) + 40 (C) = **192**
- INCLUDED: **18** (gui_01…gui_18, all from Section C)
- EXCLUDED on criteria: **165** = 15 (A, paywalled) + 22 (B, category) + 115 (E, category)
  + 13 (C: C04, C10, C11, C12, C13, C14, C15, C16, C21, C32, C33, C34, C39)
- CAP-CUT (encounter-order cap reached, not assessed): **9** (C28, C29, C30, C31, C35, C36, C37, C38, C40)

Check: 18 included + 165 excluded + 9 cap-cut = 192 logged. Within Section C: 18 + 13 + 9 = 40.

## Assembly limitations (recorded per prereg)

1. **Inline outcomes:** GoodUI write-ups state results inline (often in the title/URL). Recording
   description fields before reading results was not feasible; the prereg anticipates this. No
   outcome information was written into the backlog; because slugs carry outcome text, source URLs
   were withheld from the backlog file and are mapped here and in the truths file instead.
2. **Encounter-order caveat:** the /post-tags/results/ listing is reverse-chronological (site-fixed,
   outcome-neutral ordering); the legacy Evidence index, by contrast, is sorted by effect size and
   was therefore only used at title level (all excluded on accessibility grounds anyway) — no
   inclusion decision depended on an outcome-sorted ordering.
3. **Leaks not fully enumerated:** leak pages 2–6 (~90 entries) were excluded at category level
   without individual lines, after two detail-page verifications of the category basis.
4. **Two included cases are referenced-comparison tests** (gui_07, gui_10) described inside another
   test's post; their descriptions are thinner (pattern-level) than the directly-written cases.
5. **Per-arm data:** no GoodUI free write-up publishes per-arm tables; all `arm_b_tables` are null
   and only two cases carry a published baseline aggregate (`arm_a_tables` for gui_07, gui_08).
   Arm-B (post-pilot) composition inputs will have to come from the declared-availability modeling,
   not from published tables, for this stratum slice.
6. **Consultancy source:** a source-level caveat about the publisher is recorded in the truths file
   (not here, to keep this file safe-ish for post-prediction audit; defense in depth).
