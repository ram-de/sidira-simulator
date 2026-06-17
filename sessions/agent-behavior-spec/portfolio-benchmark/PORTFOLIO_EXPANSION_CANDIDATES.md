# Portfolio Expansion Candidates — triaged (2026-06-17)

Goal: grow the 8-case directional portfolio toward a LARGER, ~50/50-balanced set so the
headline dir_acc must beat 0.5 (not an inflated constant baseline) and n clears significance
vs chance. Current 8 = 5 control / 3 treatment (control-heavy → overweight TREATMENT additions).

Research agent (aad1ba35) returned 13 verified candidates + rejections. Below is MY triage
applying the campaign's stimulus-construction discipline. **NOTHING here is wired into
PORTFOLIO_CASES.json yet** — each requires: (1) neutral/parallel/mechanic-only blinded
descriptions, (2) an INDEPENDENT adversarial valence/leak audit (same as v2→v2.1), (3) a fresh
pre-registration (canonical SHA before any run). Author-sees-data risk applies, so the
neutrality audit is mandatory before scoring.

## ⛔ HARD EXCLUSION
- **highrise person-page** (agent #2): this IS our existing HELD-OUT memorization control
  `highrise_simple_person_page` (real_winner=treatment). Keep it HELD-OUT. Moving it to the
  scored set destroys its value as a recitation control AND the sim already "aced" it by
  memory. DO NOT add to scored set.

## TIER 1 — solid primary sources (Kohavi corpus / peer-reviewed / first-party eng blogs)
These are the trustworthy additions. Most are treatment-won → rebalances toward 50/50.
| case | winner | counter-int | source (primary) | memo | notes |
|------|--------|-------------|------------------|------|-------|
| price-com-hk-price-ranges | treatment | no | Ng/Plant/Sheng arXiv 1610.05562 (2.5M visits, magnitude RELIABLE) | low | BEST: real field exp, CI-backed |
| amazon-credit-card-offer-relocation | treatment | YES | Kohavi "Seven Rules of Thumb" KDD 2014 | med | won despite LOWER CTR (great discriminator) |
| msn-hotmail-link-new-tab | treatment | no | Kohavi ROT KDD 2014 | med | replicated, triggered users |
| msn-support-personalized-answers | treatment | no | Kohavi DMCS 2009 | low | +50% CTR, OS/browser-segmented answers |
| wikipedia-donor-count-framing | treatment | YES | Linek & Traxler JEBO 188 (2021), arXiv 2106.11128 | low-med | peer-reviewed; CAVEAT: framing = borderline nudge, score direction only |
| pinterest-signup-color-scheme | treatment | YES | Pinterest Eng (Jean Yang) Medium, verbatim quote | med | pure color inversion moved signups |
| linkedin-volunteer-section-value-copy | treatment | no | LinkedIn Eng XLNT blog | low | first-party, value-prop copy line |
| etsy-infinite-scroll-search | control | YES | Dan McKinley (Etsy) talk/danwin.com | med | one of few CONTROL-won counter-intuitive adds |

Tier-1 = 7 treatment / 1 control. Adding all 8 → portfolio 16 cases = 6 control / 10 treatment
(38/62). Slightly treatment-leaning; combine with 1-2 tier-2 control-won to hit ~50/50.

## TIER 2 — CRO-vendor "surprised experts" case studies (include with CAVEAT or hold)
Real but weaker: clients often anonymized (can't independently verify winner), single-week
tests, and SELECTED for being counter-intuitive (publication bias toward surprises). The
selection-for-surprise makes them a HARDER test (conservative, not inflating), but anonymized
winners are lower-confidence. Use only if more volume needed; mark provenance explicitly.
| case | winner | source | concern |
|------|--------|--------|---------|
| taloon-remove-social-share-buttons | treatment | VWO | 1-week test |
| bettingexpert-no-spam-privacy-line | control | Aagaard/ContentVerve via Unbounce | memo med-HIGH (famous Aagaard case) |
| lead-form-remove-truste-seal | treatment | VWO | client ANONYMIZED |
| buildcom-nav-category-icons | control | VWO | client unnamed |

## ROUTE TO HELD-OUT MEMORIZATION PROBE (high memo — NOT scored)
Bing font-colors, Bing ad-background-color, Bing "$100M" ad-headline, Bing SERP-truncate-to-20,
Twitter 280-char. All verified (Kohavi ROT) but textbook-famous → recitation risk. Use as
held-out probe expansion, never scored.

## REJECTED (agent's honest nulls — no fabrication)
Expedia remove-company-field ($12M, lore only, no clean primary), Spotify/Wayfair (ML-ranking,
not user-describable UI control/treatment), Zillow guided-search (in-progress, no winner),
MSN pre/post-roll ad (mixed tradeoff metric), DoorDash/Uber/Shopify/Yelp/Groupon (publish infra
not specific winners).

## RECOMMENDED EXECUTION (when ready — after Hillstrom re-run hot path clears)
1. Take Tier-1 (8 cases) + 2 tier-2 control-won (bettingexpert, buildcom) → 18 total =
   8 control / 10 treatment (44/56). [agent's recommended balance]
2. Author neutral/parallel/mechanic-only control+treatment descriptions for each (NO valence,
   NO outcome hint) — mirror the v2.1 normalization rules.
3. INDEPENDENT adversarial valence/leak audit (fresh agent) before any run.
4. Pull every winner from the PRIMARY source cited above (not the secondary retelling).
5. Fresh pre-reg (canonical SHA before result) + run on box for POWER → headline must beat 0.5.
