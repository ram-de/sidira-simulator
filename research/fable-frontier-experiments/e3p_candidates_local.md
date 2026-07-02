# E3-P Candidate Audit Log — Local Assembler (sources 3 + 4)

**Assembler:** CASE ASSEMBLER (local datasets + curated stratum), per PREREG_E3P_BACKLOG_PREVALENCE.md fixed source list items (3) Hillstrom and (4) PORTFOLIO_CASES_V3.json.
**Date:** 2026-07-01. **Build script:** `e3p_hillstrom_build.py` (deterministic, seed 20260701).
**Outputs:** `e3p_backlog_local.json` (21 cases, no outcome information), `e3p_truths_local.json` (sealed; sha256 in `e3p_truths_local.sha256`).

Per the prereg anti-cherry-picking rule, every candidate constructed or considered is logged below with an INCLUDED/EXCLUDED disposition. No directions, rates, or outcome hints appear in this log.

## Part A — Hillstrom MineThatData (stratum: realistic)

Source data: `.data/hillstrom.csv` (64,000 rows; three arms: Mens E-Mail / Womens E-Mail / No E-Mail; binary outcomes visit, conversion; continuous outcome spend).

| candidate | description | disposition |
|---|---|---|
| hil_01 | Mens email vs No email, visit rate | **INCLUDED** |
| hil_02 | Mens email vs No email, conversion rate | **INCLUDED** |
| hil_03 | Womens email vs No email, visit rate | **INCLUDED** |
| hil_04 | Womens email vs No email, conversion rate | **INCLUDED** |
| (considered) Mens email vs No email, spend | continuous per-customer spend metric | **EXCLUDED** — outside the assigned 2×2 case grid (email arm × {visit, conversion}); spend is continuous/heavy-tailed, not a rate metric of the tier-1 composition kind |
| (considered) Womens email vs No email, spend | same | **EXCLUDED** — same reason |
| (considered) Mens email vs Womens email head-to-head | variant-vs-variant comparison | **EXCLUDED** — not a control-vs-treatment product decision (no holdout baseline); out of the assigned case grid |

Construction notes (honest post-pilot simulation):
- A 20% random pilot subsample (12,800 of 64,000 rows; `random.Random(20260701).shuffle` over row indices) was drawn deterministically, before and independently of any outcome computation.
- `arm_b_tables` = pilot-only per-arm n + rate, overall and by history_segment (7 segments).
- `arm_a_tables` = baseline-only: full-file segment mix (pre-treatment covariate) + no-contact holdout baseline visit/conversion rates by segment. Encodes no treatment contrast. Limitation: the "historical baseline" is proxied by the no-email arm observed during the experiment window (no true pre-period file exists in this dataset).
- Truths computed on the FULL dataset (flat threshold: |diff| < 0.1pp), written directly to the truths file, never printed.
- The four cases share one underlying randomized population (two email arms × two metrics), so they are not four fully independent experiments — a within-source correlation limitation for prevalence accounting.

## Part B — Cookie Cats (stratum: realistic)

Source data: `e1_cookiecats_tables.json` (per-arm engagement-bin cross-tabs, gate level 30 vs 40).

| candidate | description | disposition |
|---|---|---|
| cc_01 | gate 30 vs 40, 1-day retention | **INCLUDED** |
| cc_02 | gate 30 vs 40, 7-day retention | **INCLUDED** |

Construction notes:
- `arm_b_tables` = the E1 bin tables verbatim (restricted to the case's metric column). **Declared limitation (in availability_notes): these are FULL-experiment aggregates, not a pilot subsample — Arm B calls on cc_01/cc_02 are circular with the truth.**
- `arm_a_tables` = null (no baseline-only tables exist for this dataset).
- Truths = pooled user-weighted per-arm rates computed from the tables by the script (same 0.1pp flat rule), written directly to the truths file, never printed.
- The two cases are two metrics on ONE experiment (correlated evidence), and the experiment also appears in the curated stratum as cur_01 (see overlap note below).

## Part C — Portfolio-15 curated stratum (stratum: curated)

Source: `sessions/agent-behavior-spec/portfolio-benchmark/PORTFOLIO_CASES_V3.json`, `scored_cases` (15). Per the prereg these are a SEPARATE CURATED stratum, never pooled into the prevalence headline (the set over-samples counter-intuitive outcomes by construction). All 15 included, per assignment; backlog entries built from descriptive fields only (control/treatment/metric/domain/source — the valence-normalized v2/v3 strings); outcome-bearing fields stripped: `real_winner`, `effect`, `counter_intuitive` (hints the outcome opposes intuition), `status`, `caveat` (office_online — outcome-entangled metric commentary), `note` (multistep_form — restates the winner), `balance_check`. No numeric per-arm tables of the E1 kind exist in the case file (only outcome point-estimate strings, which are outcome-bearing), so `arm_a_tables` = `arm_b_tables` = null for all 15.

| candidate | source case id | disposition |
|---|---|---|
| cur_01 | cookiecats_gate_move | **INCLUDED** — ⚠ overlap: same underlying experiment as cc_01/cc_02 (realistic stratum). Kept per assignment (different stratum, different availability regime: narrative-only here vs full-experiment tables there). Must not be double-counted in any pooled analysis. |
| cur_02 | duolingo_weekend_amulet | **INCLUDED** |
| cur_03 | msn_realestate_widget | **INCLUDED** |
| cur_04 | office_online_redesign | **INCLUDED** — outcome-entangled `caveat` field stripped; scored on the stated primary metric |
| cur_05 | msn_homepage_extra_offers | **INCLUDED** |
| cur_06 | tinkoff_defer_passport | **INCLUDED** |
| cur_07 | cxl_form_fields_9_to_6 | **INCLUDED** |
| cur_08 | multistep_form_3_vs_6 | **INCLUDED** — winner-restating `note` field stripped |
| cur_09 | price_com_hk_price_ranges | **INCLUDED** |
| cur_10 | amazon_credit_card_offer_relocation | **INCLUDED** |
| cur_11 | msn_hotmail_link_new_tab | **INCLUDED** |
| cur_12 | msn_support_personalized_answers | **INCLUDED** |
| cur_13 | pinterest_signup_color_scheme | **INCLUDED** — treatment/control are a symmetric scheme swap; prose kept strictly parallel |
| cur_14 | linkedin_volunteer_section_value_copy | **INCLUDED** — inherent-mechanic asymmetry (treatment IS added persuasive copy); portfolio's independent auditor ruled this not an authoring leak; noted in availability_notes |
| cur_15 | etsy_infinite_scroll_search | **INCLUDED** |
| (encountered) netflix_browse_before_signup | `held_out_memorization_probe` entry in the case file | **EXCLUDED** — not in the 15 scored cases; held out by portfolio design for high contamination |
| (encountered) highrise_simple_person_page | `held_out_memorization_probe` entry in the case file | **EXCLUDED** — same reason |
| (encountered) wikipedia_donor_count_framing | mentioned in the file's `expansion_v3.excluded` | **EXCLUDED** — already excluded by the portfolio itself (sub-deliberative nudge, out of the in-scope class); never a scored case |

Hillstrom does NOT appear inside the portfolio — no overlap on Part A.

## Counts

| part | stratum | included | excluded/considered-not-built |
|---|---|---|---|
| A Hillstrom | realistic | 4 | 3 |
| B Cookie Cats | realistic | 2 | 0 |
| C Portfolio | curated | 15 | 3 |
| **total** | | **21** | **6** |

## Limitations (blinding-safe)

1. **Assembler is not outcome-blind for Part C:** the portfolio case file states winners inline; the assembler read them to build the truths file (as the prereg anticipates — "where a source states the outcome inline, this is imperfect"). Mitigation: backlog strings are the portfolio's independently valence-audited neutral versions; every stripped field is itemized above; prediction-side blinding is preserved (truths sealed, sha256 `e3p_truths_local.sha256`).
2. **cc Arm-B circularity:** cc_01/cc_02 Arm-B tables are full-experiment aggregates (declared in availability_notes); any Arm-B call there is not an out-of-sample prediction.
3. **Correlated evidence units:** hil_01–04 share one randomized population; cc_01/cc_02 share one experiment; cur_01 duplicates the cc experiment across strata.
4. **Arm-A baseline proxy (Hillstrom):** baseline rates come from the no-email arm during the experiment window (no true pre-period exists in the dataset); labeled as a proxy in the tables.
5. **Truth flat-rule:** "flat" declared when |absolute difference| < 0.1 percentage points on the case metric (applies to hil/cc computed truths; portfolio truths come from the published winner field, where the source declared a winner in all 15).
