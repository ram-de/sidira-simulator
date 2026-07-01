# E2 Results — Same-Tag, Opposite-Sign Library Audit

**Prereg:** `PREREG_E2_TAG_SIGN_AMBIGUITY.md` (sealed 2026-07-01, before any tagging call)
**Run:** 2026-07-01 · tagger `claude-opus-4-8` · 3 runs/case · 17 real cases · 51 API calls
**Raw data:** `e2_result.json` (verbatim prompts + all raw tagger outputs, for the leakage audit)

## Verdict — **KILL**

**AMBIGUITY = 13/15 = 86.7%** (primary grain: `family` alone) — far above the 30% KILL threshold, with 15 in-group cases (≥5 required, so fully measurable). Per the prereg: **mechanism-tag retrieval is permanently banned from selecting a sign; the taxonomy remains an ensemble/uncertainty axis only** (paper rule R2 hardens into a measured result).

## Case → tag → truth

Truth: `real_winner=treatment → +`, `control → −` (portfolio); Hillstrom signs from the sealed spike file.

| Case | Family (majority of 3) | Truth |
|---|---|---|
| cookiecats_gate_move | friction_change | − |
| tinkoff_defer_passport | friction_change | + |
| cxl_form_fields_9_to_6 | friction_change | − |
| multistep_form_3_vs_6 | friction_change | − |
| etsy_infinite_scroll_search | friction_change | − |
| office_online_redesign | salience_attention | − |
| msn_homepage_extra_offers | salience_attention | − |
| price_com_hk_price_ranges | salience_attention | + |
| amazon_credit_card_offer_relocation | salience_attention | + |
| pinterest_signup_color_scheme | salience_attention | + |
| linkedin_volunteer_section_value_copy | salience_attention | + |
| hillstrom_mens_email_visit | salience_attention | + |
| hillstrom_mens_email_conversion | salience_attention | + |
| msn_realestate_widget | layout_navigation | + |
| msn_hotmail_link_new_tab | layout_navigation | + |
| duolingo_weekend_amulet | habit_loop | + |
| msn_support_personalized_answers | personalization | + |

## Group structure (primary grain, ≥2 members)

| Group | n | Signs | Sign-ambiguous? |
|---|---|---|---|
| salience_attention | 8 | + + + + + + − − | **YES** |
| friction_change | 5 | + − − − − | **YES** |
| layout_navigation | 2 | + + | no |
| *(singletons: habit_loop +, personalization +)* | 1 each | — | n/a (excluded) |

AMBIGUITY = (8 + 5) / (8 + 5 + 2) = **13/15 = 0.867**.

## Secondary reads (informational per prereg)

- **Finer grain (`family+mediator_role`):** 5/17 cases had no majority mediator string → `unstable` (excluded). Only one ≥2 group survives: `friction_change::form_completion_effort` {cxl −, multistep −} → ambiguity 0/2 = 0.0, but only 2 in-group cases (< 5, underpowered at this grain). The finer grain trades ambiguity for near-total group evaporation — no retrieval density.
- **Tag stability:** family grain **17/17 cases identical across all 3 runs** (100%). Family+mediator grain: only 5/17 fully identical (free-text mediator wording churns even when family is stable).
- **Per-family sign base rates (all tagged, incl. singletons):** friction_change 1+/4−, salience_attention 6+/2−, layout_navigation 2+/0−, habit_loop 1+/0−, personalization 1+/0−. No family with ≥2 members and both signs absent except layout_navigation (2/2 +, far too small to be an "always-up family").
- **UNMEASURABLE check:** 15 real cases in ≥2-member groups ≥ 5 → real arm is powered; verdict stands on the real arm.
- **Secondary synthetic arm (E1 composition cells):** not run — E1's generated cells were not available/finalized as a labeled artifact in this worktree at run time; per prereg it is density-only, never pooled with the real arm, and the real arm alone was decisive (KILL), so the conservative reading is unchanged.

## Hillstrom case construction

From `research/empirical-uplift-spike/realdata_hillstrom_result.json` (men's email vs no email):

- **visit** INCLUDED, truth `+` (true ATE +4.523pp; all 5 estimator signs RIGHT).
- **conversion** INCLUDED, truth `+` (true ATE +0.311pp; all 5 estimator signs RIGHT).
- **spend** EXCLUDED: not present in the sealed file at all (prereg itself notes spend ~0/ambiguous) — noted, no truth encodable.

Control/treatment shown to the tagger were plain prose of the campaign change (no-email vs men's-merchandise email over a two-week window); metric names "website visit rate within two weeks" / "purchase conversion rate within two weeks".

## Leakage guards

Per-case prompt = control description + treatment description + metric name ONLY (template `Control: …\nTreatment: …\nMetric: …`). No `effect`, no `real_winner`, no `counter_intuitive`, no `domain`, no case id. System prompt instructs classification only and explicitly forbids predicting direction/size. All 17 verbatim prompts + system prompt logged in `e2_result.json` for audit.

## Deviations from prereg

1. **`temperature` omitted** (prereg: temperature 0). The claude-opus-4-8 API rejects the parameter with 400 "`temperature` is deprecated for this model". The pre-registered 3-run majority rule covers stability regardless — and family tags were 100% identical across runs, so this deviation had no effect on the primary grain.
2. **Majority applied per grain independently** (prereg says "a case's tag = majority" without specifying the finer grain): family majority for the primary grain; the combined `family::mediator_role` string majority for the secondary grain. Conservative — a case can be stable at family grain and `unstable` at the finer grain, which only shrinks the (informational) secondary denominator.
3. **Hillstrom spend excluded** as above (file simply lacks it).
4. **Synthetic E1 arm not run** (secondary, density-only per prereg; real arm decisive on its own).

## Interpretation (one paragraph)

Even with a perfectly stable tagger (100% run-to-run agreement at family grain), the two biggest mechanism families — friction_change and salience_attention, covering 13 of 17 real cases — each contain real, certified effects of both signs. A "similar mechanism" tag match therefore carries almost no sign information at the family grain, and the grain fine enough to be unambiguous (family+mediator) is too sparse to retrieve on (max group size 2, 5/17 unstable). Tags are an uncertainty/ensemble axis, not a sign prior.

## API cost

51 calls (17 cases × 3 runs) · 14,280 input tokens + 1,538 output tokens on claude-opus-4-8 ≈ **$0.33** (at $15/M in, $75/M out).
