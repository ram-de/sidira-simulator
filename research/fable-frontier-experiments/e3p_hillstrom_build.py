#!/usr/bin/env python3.11
"""E3-P local case assembler (Parts A-C): Hillstrom + Cookie Cats + portfolio-15 curated stratum.

Deterministic (seed 20260701). Writes:
  - e3p_backlog_local.json  (NO outcome information anywhere)
  - e3p_truths_local.json   (sealed truths; never printed to stdout)
  - e3p_truths_local.sha256

Part A (hil_01..hil_04, stratum "realistic"): Hillstrom MineThatData email test,
  .data/hillstrom.csv. A 20% random "pilot" subsample simulates the post-pilot
  regime honestly. arm_b_tables = pilot-only per-arm aggregates (n + rate overall
  and by history_segment). arm_a_tables = baseline-only aggregates (full-file
  segment mix; no-email-holdout baseline rates by segment) - nothing encoding the
  treatment contrast. Truth = FULL-dataset direction; "flat" if |diff| < 0.1pp.

Part B (cc_01, cc_02, stratum "realistic"): Cookie Cats engagement-bin cross-tabs
  from e1_cookiecats_tables.json, verbatim, as arm_b_tables. These are
  FULL-experiment aggregates (circularity limitation; declared in
  availability_notes). Truth = pooled per-arm rates computed from the tables.

Part C (cur_01..cur_15, stratum "curated"): all 15 scored cases from
  sessions/agent-behavior-spec/portfolio-benchmark/PORTFOLIO_CASES_V3.json,
  descriptive fields only (outcome-bearing fields stripped); truths from the
  case file's ground-truth winner mapped to up/down on the primary metric
  (all primary metrics are higher-is-better).

Blinding: this script NEVER prints a direction, rate, or outcome hint to stdout.
"""
import csv
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent  # research/fable-frontier-experiments
REPO = ROOT.parent.parent
SEED = 20260701
PILOT_FRACTION = 0.20
FLAT_THRESHOLD = 0.001  # 0.1 percentage points, in rate units

# ---------------------------------------------------------------- Part A: Hillstrom

rows = list(csv.DictReader(open(REPO / ".data" / "hillstrom.csv")))
SEGS = sorted({r["history_segment"] for r in rows})

rnd = random.Random(SEED)
idx = list(range(len(rows)))
rnd.shuffle(idx)
pilot_idx = set(idx[: int(round(PILOT_FRACTION * len(rows)))])
pilot = [rows[i] for i in sorted(pilot_idx)]

METRIC_COL = {"visit_rate": "visit", "conversion_rate": "conversion"}


def rate(rs, col):
    return (sum(int(r[col]) for r in rs) / len(rs)) if rs else None


def by_segment(rs, col):
    out = []
    for s in SEGS:
        sub = [r for r in rs if r["history_segment"] == s]
        out.append({"history_segment": s, "n": len(sub),
                    "rate": round(rate(sub, col), 5) if sub else None})
    return out


no_email_full = [r for r in rows if r["segment"] == "No E-Mail"]

ARM_A_HILLSTROM = {
    "description": ("Baseline-only aggregates available before launch: customer-file segment mix "
                    "(pre-treatment covariate) and baseline outcome rates by history segment from the "
                    "no-contact holdout population (proxy for historical baseline). Contains no "
                    "treatment-arm information and no treatment contrast."),
    "customer_file_segment_mix": {
        "total_customers": len(rows),
        "segments": [
            {"history_segment": s,
             "n": sum(1 for r in rows if r["history_segment"] == s),
             "share": round(sum(1 for r in rows if r["history_segment"] == s) / len(rows), 4)}
            for s in SEGS
        ],
    },
    "baseline_rates_no_contact": {
        "n": len(no_email_full),
        "visit_rate_overall": round(rate(no_email_full, "visit"), 5),
        "conversion_rate_overall": round(rate(no_email_full, "conversion"), 5),
        "by_history_segment": [
            {"history_segment": s,
             "n": len([r for r in no_email_full if r["history_segment"] == s]),
             "visit_rate": round(rate([r for r in no_email_full if r["history_segment"] == s], "visit"), 5),
             "conversion_rate": round(rate([r for r in no_email_full if r["history_segment"] == s], "conversion"), 5)}
            for s in SEGS
        ],
    },
}


def arm_b_hillstrom(email_arm, metric_key):
    col = METRIC_COL[metric_key]
    t = [r for r in pilot if r["segment"] == email_arm]
    c = [r for r in pilot if r["segment"] == "No E-Mail"]

    def arm(rs):
        return {"n": len(rs), "rate_overall": round(rate(rs, col), 5),
                "by_history_segment": by_segment(rs, col)}

    return {
        "description": (f"Pilot-only per-arm aggregates for metric '{metric_key}': a {int(PILOT_FRACTION*100)}% "
                        f"random subsample of the customer file (seed {SEED}), drawn deterministically and "
                        "independently of any outcome. Per-arm n and rate, overall and by history segment."),
        "regime": "post-pilot",
        "pilot_fraction": PILOT_FRACTION,
        "seed": SEED,
        "metric": metric_key,
        "arms": {"treatment_email": arm(t), "no_email_holdout": arm(c)},
    }


def hillstrom_truth(email_arm, metric_key):
    col = METRIC_COL[metric_key]
    t = [r for r in rows if r["segment"] == email_arm]
    diff = rate(t, col) - rate(no_email_full, col)
    if abs(diff) < FLAT_THRESHOLD:
        return "flat"
    return "up" if diff > 0 else "down"


HIL_SPECS = [
    ("hil_01", "Mens E-Mail", "visit_rate", "men's-merchandise email", "website visit rate"),
    ("hil_02", "Mens E-Mail", "conversion_rate", "men's-merchandise email", "purchase conversion rate"),
    ("hil_03", "Womens E-Mail", "visit_rate", "women's-merchandise email", "website visit rate"),
    ("hil_04", "Womens E-Mail", "conversion_rate", "women's-merchandise email", "purchase conversion rate"),
]

hil_cases, hil_truths = [], []
for cid, arm_name, metric_key, arm_desc, metric_desc in HIL_SPECS:
    prose = (
        "A catalog and online merchandiser ran an email test on customers who had purchased within the "
        "last twelve months. Customers were randomized to one of three groups: an email campaign featuring "
        "men's merchandise, an email campaign featuring women's merchandise, or no email at all. "
        f"This case compares the {arm_desc} campaign against the no-email holdout. "
        "Outcomes were tracked for two weeks following the campaign delivery. "
        f"The primary metric is the {metric_desc} over the two-week window."
    )
    hil_cases.append({
        "id": cid,
        "stratum": "realistic",
        "source": "Hillstrom MineThatData e-mail analytics challenge dataset (.data/hillstrom.csv, 64,000 customers)",
        "company_context": ("Mid-sized catalog/online merchandiser; customer file of 64,000 people who "
                            "purchased within the last twelve months; customers segmented by dollars spent "
                            "in the past year (history_segment), recency, channel, and urban/suburban/rural zip class."),
        "control": "No email is sent (holdout group).",
        "treatment": f"Customers receive an email campaign featuring {arm_desc.replace(' email', '')} merchandise.",
        "primary_metric": metric_key + " (two-week window)",
        "prose": prose,
        "arm_a_tables": ARM_A_HILLSTROM,
        "arm_b_tables": arm_b_hillstrom(arm_name, metric_key),
        "availability_notes": (
            "Honest post-pilot simulation: Arm B tables are aggregates from a deterministic 20% random pilot "
            f"subsample (seed {SEED}) of the customer file; the truth is computed on the FULL dataset, so the "
            "pilot is a genuine noisy preview, not a restatement of the truth. Arm A tables are baseline-only "
            "(segment mix + no-contact holdout baseline rates by segment) and encode no treatment contrast. "
            "The no-contact baseline is taken from the no-email arm as a proxy for historical baseline rates."
        ),
    })
    hil_truths.append({
        "id": cid,
        "direction_primary": hillstrom_truth(arm_name, metric_key),
        "truth_source": ("Full Hillstrom dataset (64,000 rows): email-arm rate minus no-email rate on the case "
                         "metric; 'flat' if absolute difference < 0.1 percentage points. Computed by e3p_hillstrom_build.py."),
        "notes": "up = email arm beats no-email holdout on the metric; pilot subsample NOT used for truth.",
    })

# ---------------------------------------------------------------- Part B: Cookie Cats

cc_tables = json.load(open(ROOT / "e1_cookiecats_tables.json"))


def cc_pooled_rate(arm, key):
    bins = cc_tables["arms"][arm]["bins"]
    return sum(b["users"] * b[key] for b in bins) / sum(b["users"] for b in bins)


def cc_truth(key):
    diff = cc_pooled_rate("gate_40", key) - cc_pooled_rate("gate_30", key)
    if abs(diff) < FLAT_THRESHOLD:
        return "flat"
    return "up" if diff > 0 else "down"


CC_SPECS = [
    ("cc_01", "retention_1_rate", "1-day retention", "whether the player opens the game again one day after installing"),
    ("cc_02", "retention_7_rate", "7-day retention", "whether the player opens the game again seven days after installing"),
]

cc_cases, cc_truths = [], []
for cid, metric_key, metric_name, metric_def in CC_SPECS:
    cc_cases.append({
        "id": cid,
        "stratum": "realistic",
        "source": "Cookie Cats A/B test (public dataset mirror); per-arm engagement-bin cross-tabs from e1_cookiecats_tables.json",
        "company_context": ("Free-to-play mobile puzzle game (Cookie Cats, Tactile Games); roughly 90,000 new "
                            "players in the test; monetization includes in-app purchases at forced progress gates."),
        "control": "The first forced progress gate is placed at level 30.",
        "treatment": "The first forced progress gate is placed at level 40.",
        "primary_metric": f"{metric_name} ({metric_key})",
        "prose": (
            "A free-to-play mobile puzzle game places forced progress gates at fixed levels; when a player "
            "reaches a gate they must wait for a timer or make an in-app purchase to continue playing. "
            "In the control condition the first gate appears at level 30. In the treatment condition the first "
            "gate appears at level 40. New players were randomly assigned to one gate placement when they "
            f"installed the game. The primary metric is {metric_name}: {metric_def}."
        ),
        "arm_a_tables": None,
        "arm_b_tables": {
            "description": ("Per-arm cross-tabs of users and retention rate by engagement bin (game rounds "
                            "played in the first 14 days). NOTE: these are FULL-experiment aggregates, not a "
                            "pilot subsample."),
            "schema": cc_tables["schema"],
            "metric": metric_key,
            "arms": {
                arm: {
                    "total_users": cc_tables["arms"][arm]["total_users"],
                    "bins": [
                        {"gamerounds_bin": b["gamerounds_bin"], "users": b["users"], metric_key: b[metric_key]}
                        for b in cc_tables["arms"][arm]["bins"]
                    ],
                }
                for arm in ("gate_30", "gate_40")
            },
        },
        "availability_notes": (
            "CIRCULARITY LIMITATION: the Arm B tables are FULL-experiment per-arm aggregates (the entire "
            "90k-player test collapsed to engagement bins), NOT a pilot subsample - any Arm B call on this case "
            "is computed from the same data that defines the truth. No baseline-only tables are available, so "
            "Arm A tables are null (strict pre-launch arm must abstain or work from prose alone). Same underlying "
            "experiment as cur_01 in the curated stratum."
        ),
    })
    cc_truths.append({
        "id": cid,
        "direction_primary": cc_truth(metric_key),
        "truth_source": ("Pooled per-arm rates computed from e1_cookiecats_tables.json (user-weighted across "
                         "engagement bins; full experiment); 'flat' if absolute difference < 0.1 percentage "
                         "points. Computed by e3p_hillstrom_build.py."),
        "notes": "up = gate_40 (treatment) beats gate_30 (control) on the retention metric.",
    })

# ---------------------------------------------------------------- Part C: portfolio curated stratum

# Descriptive fields transcribed from PORTFOLIO_CASES_V3.json scored_cases (control/treatment strings are the
# valence-normalized v2/v3 versions). Outcome-bearing fields (real_winner, effect, counter_intuitive, status,
# caveat, note) are STRIPPED from the backlog; the winner map below feeds ONLY the truths file.
CUR = [
    {"id": "cur_01", "src_id": "cookiecats_gate_move",
     "source": "Cookie Cats A/B; raw mirror ryanschaub/Mobile-Games-A-B-Testing-with-Cookie-Cats (via PORTFOLIO_CASES_V3.json)",
     "company_context": "Free-to-play mobile puzzle game; roughly 90,000 new players; monetization includes in-app purchases at forced progress gates.",
     "control": "The first forced progress gate is at level 30.",
     "treatment": "The first forced progress gate is at level 40.",
     "primary_metric": "7-day retention",
     "prose": ("A free-to-play mobile puzzle game places forced progress gates at fixed levels; at a gate the "
               "player must wait for a timer or make an in-app purchase to continue. In the control condition "
               "the first gate appears at level 30. In the treatment condition the first gate appears at level 40. "
               "New players were randomly assigned to one placement when they installed the game. The primary "
               "metric is 7-day retention: whether the player returns to the game seven days after installing."),
     "availability_notes": ("Published-case regime: no per-arm tables provided in this stratum entry (arm tables "
                            "null). Raw data for this experiment exists publicly and appears in the realistic "
                            "stratum as cc_01/cc_02 (same underlying experiment; overlap logged)."),},
    {"id": "cur_02", "src_id": "duolingo_weekend_amulet",
     "source": "Duolingo engineering/blog (via PORTFOLIO_CASES_V3.json)",
     "company_context": "Consumer language-learning app with a daily-streak habit mechanic (consecutive days of practice).",
     "control": "Missing a day of practice ends the user's streak.",
     "treatment": "An equippable 'Weekend Amulet' item keeps the streak active through one skipped weekend day.",
     "primary_metric": "week-later return rate",
     "prose": ("A language-learning app tracks a daily streak: the number of consecutive days a user has "
               "practiced. In the control condition, missing a day of practice ends the streak. In the treatment "
               "condition, users can equip an item called the Weekend Amulet that keeps the streak active through "
               "one skipped weekend day. Users were randomly assigned to one condition. The primary metric is the "
               "week-later return rate: whether the user returns to the app a week later."),
     "availability_notes": "Published narrative case; no per-arm aggregate tables available (arm tables null)."},
    {"id": "cur_03", "src_id": "msn_realestate_widget",
     "source": "Kohavi et al., Online Experimentation at Microsoft (DMCS 2009) (via PORTFOLIO_CASES_V3.json)",
     "company_context": "Large web portal's real-estate page; a 'Find a home' widget refers visitors to partner sites for revenue.",
     "control": "The incumbent 'Find a home' widget.",
     "treatment": "A redesigned 'Find a home' widget with a search-box-style layout.",
     "primary_metric": "referral revenue",
     "prose": ("A web portal's real-estate page includes a 'Find a home' widget that sends visitors to partner "
               "sites. In the control condition the incumbent widget design is shown. In the treatment condition "
               "a redesigned widget with a search-box-style layout is shown. Visitors were randomly assigned to "
               "one design. The primary metric is referral revenue generated from clicks out of the widget."),
     "availability_notes": "Published narrative case; no per-arm aggregate tables available (arm tables null)."},
    {"id": "cur_04", "src_id": "office_online_redesign",
     "source": "Kohavi et al., DMCS 2009 (via PORTFOLIO_CASES_V3.json)",
     "company_context": "Office-software product's public website; a Buy page sells the product online.",
     "control": "The existing Buy page layout.",
     "treatment": "A redesigned Buy page with a reorganized layout; one element shown on the existing page (the price) is not shown.",
     "primary_metric": "Buy-button clickers",
     "prose": ("An office-software product's public website includes a page where visitors can buy the product. "
               "The control condition shows the existing Buy page layout, which displays the price. The treatment "
               "condition shows a redesigned Buy page with a reorganized layout in which the price shown on the "
               "existing page is not displayed. Visitors were randomly assigned to one layout. The primary metric "
               "is the number of visitors who click the Buy button."),
     "availability_notes": ("Published narrative case; no per-arm aggregate tables available (arm tables null). "
                            "The source discusses metric-choice caveats for this experiment; that commentary is "
                            "outcome-entangled and was stripped - score on the stated primary metric.")},
    {"id": "cur_05", "src_id": "msn_homepage_extra_offers",
     "source": "Kohavi et al., DMCS 2009 (via PORTFOLIO_CASES_V3.json)",
     "company_context": "Large web portal home page mixing editorial content and commercial modules, including a shopping module.",
     "control": "The MSN homepage as-is.",
     "treatment": "The MSN homepage with 3 additional paid offers placed below the shopping module.",
     "primary_metric": "clicks and page-views per user-day",
     "prose": ("A large web portal's home page contains editorial and commercial modules, including a shopping "
               "module. In the control condition the home page is unchanged. In the treatment condition three "
               "additional paid offers are placed below the shopping module. Visitors were randomly assigned to "
               "one version of the page. The primary metric is clicks and page-views per user-day."),
     "availability_notes": "Published narrative case; no per-arm aggregate tables available (arm tables null)."},
    {"id": "cur_06", "src_id": "tinkoff_defer_passport",
     "source": "VWO case-study showcase (via PORTFOLIO_CASES_V3.json)",
     "company_context": "Bank's online credit-card application; multi-step onboarding form collecting applicant details (n=265k applicants).",
     "control": "The card application requires passport details at step 2.",
     "treatment": "The card application adds a 'Don't remember? Add later' checkbox that defers the passport field to a later step.",
     "primary_metric": "form conversion",
     "prose": ("A bank's online credit-card application collects applicant details across several steps; step 2 "
               "asks for passport details. In the control condition the passport fields must be completed at "
               "step 2. In the treatment condition the form adds a 'Don't remember? Add later' checkbox that "
               "defers the passport fields to a later step. Applicants were randomly assigned to one version of "
               "the form. The primary metric is form conversion: the fraction of applicants who complete the "
               "application."),
     "availability_notes": "Published vendor showcase; no per-arm aggregate tables available (arm tables null)."},
    {"id": "cur_07", "src_id": "cxl_form_fields_9_to_6",
     "source": "CXL / Michael Aagaard (via PORTFOLIO_CASES_V3.json)",
     "company_context": "Company collecting sign-ups/leads through a web form (client anonymized in the source).",
     "control": "A 9-field form.",
     "treatment": "A 6-field form (three of the nine fields removed).",
     "primary_metric": "conversions",
     "prose": ("A company collects sign-ups through a web form. The control version of the form has nine fields. "
               "The treatment version has six fields: three of the nine fields are removed. Visitors were randomly "
               "assigned to one version. The primary metric is conversions: the fraction of visitors who complete "
               "and submit the form."),
     "availability_notes": "Published practitioner case (client anonymized); no per-arm aggregate tables available (arm tables null)."},
    {"id": "cur_08", "src_id": "multistep_form_3_vs_6",
     "source": "Named CRO practitioner case (via PORTFOLIO_CASES_V3.json)",
     "company_context": "Lead-generation site collecting prospect information through a multi-step form (client anonymized in the source).",
     "control": "A 6-step form.",
     "treatment": "A 3-step form (the 6 steps condensed into 3).",
     "primary_metric": "lead conversion",
     "prose": ("A lead-generation site collects prospect information through a multi-step form. The control "
               "version spreads the questions across six steps. The treatment version condenses the same "
               "questions into three steps. Visitors were randomly assigned to one version. The primary metric "
               "is lead conversion: the fraction of visitors who complete the form."),
     "availability_notes": "Published practitioner case (client anonymized, no percentages disclosed); no per-arm aggregate tables available (arm tables null)."},
    {"id": "cur_09", "src_id": "price_com_hk_price_ranges",
     "source": "Ng/Plant/Sheng, arXiv:1610.05562 field experiment (via PORTFOLIO_CASES_V3.json)",
     "company_context": "Comparison-shopping site (Hong Kong); category listing pages show products with price information from participating sellers; ~2.5M page views in the test.",
     "control": "On a category listing page, each product shows one price: the most recently offered price for that product.",
     "treatment": "On a category listing page, each product shows a price stated as a low-to-high range across the prices currently offered for that product.",
     "primary_metric": "product click-throughs per listing-page view",
     "prose": ("A comparison-shopping site lists products on category pages, with each product shown alongside "
               "price information drawn from participating sellers. In the control condition each product shows "
               "one price: the most recently offered price for that product. In the treatment condition each "
               "product shows a price stated as a low-to-high range across the prices currently offered for that "
               "product. Page views were randomly assigned to one presentation. The primary metric is product "
               "click-throughs per listing-page view."),
     "availability_notes": "Peer-reviewed field experiment; no per-arm aggregate tables reproduced in the case file (arm tables null)."},
    {"id": "cur_10", "src_id": "amazon_credit_card_offer_relocation",
     "source": "Kohavi et al., Seven Rules of Thumb, KDD 2014 (via PORTFOLIO_CASES_V3.json)",
     "company_context": "Large e-commerce site cross-selling its own credit card to shoppers.",
     "control": "The credit-card offer is placed in the top slot of the home page.",
     "treatment": "The credit-card offer is placed on the shopping-cart page after an item is added, and states a dollar amount computed from the current cart contents.",
     "primary_metric": "expected profit per user",
     "prose": ("An e-commerce site promotes its own credit card to shoppers. In the control condition the "
               "credit-card offer occupies the top slot of the home page. In the treatment condition the offer "
               "instead appears on the shopping-cart page after an item is added, and states a dollar amount "
               "computed from the current cart contents. Shoppers were randomly assigned to one placement. The "
               "primary metric is expected profit per user."),
     "availability_notes": "Published narrative case; no per-arm aggregate tables available (arm tables null)."},
    {"id": "cur_11", "src_id": "msn_hotmail_link_new_tab",
     "source": "Kohavi et al., Seven Rules of Thumb, KDD 2014 (via PORTFOLIO_CASES_V3.json)",
     "company_context": "Large web portal home page with a link to the portal's web-mail service; test replicated on millions of users.",
     "control": "Clicking the mail link loads the mail destination in the current tab.",
     "treatment": "Clicking the mail link loads the mail destination in a new tab.",
     "primary_metric": "clicks per user on the home page",
     "prose": ("A web portal's home page includes a link to the portal's web-mail service. In the control "
               "condition, clicking the mail link loads the mail destination in the current tab. In the treatment "
               "condition, clicking the mail link loads the mail destination in a new tab. Visitors were randomly "
               "assigned to one behavior. The primary metric is clicks per user on the home page."),
     "availability_notes": "Published narrative case; no per-arm aggregate tables available (arm tables null)."},
    {"id": "cur_12", "src_id": "msn_support_personalized_answers",
     "source": "Kohavi et al., Online Experimentation at Microsoft, DMCS 2009 (via PORTFOLIO_CASES_V3.json)",
     "company_context": "Software company's support site; a 'most common issues' box links to answer pages.",
     "control": "The 'most common issues' box shows a single fixed list of answers.",
     "treatment": "The 'most common issues' box shows a list of answers that varies by the visitor's browser and operating system.",
     "primary_metric": "click-through rate on the answers section",
     "prose": ("A software company's support site shows a 'most common issues' box with links to answer pages. "
               "In the control condition the box shows a single fixed list of answers for all visitors. In the "
               "treatment condition the box shows a list of answers that varies by the visitor's browser and "
               "operating system. Visitors were randomly assigned to one condition. The primary metric is the "
               "click-through rate on the answers section."),
     "availability_notes": "Published narrative case; no per-arm aggregate tables available (arm tables null)."},
    {"id": "cur_13", "src_id": "pinterest_signup_color_scheme",
     "source": "Pinterest Engineering (Jean Yang), Medium (via PORTFOLIO_CASES_V3.json)",
     "company_context": "Consumer web product (visual discovery/bookmarking); signup page for new visitors.",
     "control": "The signup page uses black text on a white background.",
     "treatment": "The signup page uses white text on a black background.",
     "primary_metric": "daily signups",
     "prose": ("A consumer web product tests the visual scheme of its signup page. In the control condition the "
               "page uses black text on a white background. In the treatment condition the page uses white text "
               "on a black background. Visitors were randomly assigned to one scheme. The primary metric is "
               "daily signups."),
     "availability_notes": "First-party engineering-blog case; no per-arm aggregate tables available (arm tables null)."},
    {"id": "cur_14", "src_id": "linkedin_volunteer_section_value_copy",
     "source": "LinkedIn Engineering, XLNT platform (via PORTFOLIO_CASES_V3.json)",
     "company_context": "Professional network; profile-completion module suggests sections for members to add to their profile.",
     "control": "A profile-completion module prompts the member to add a volunteer-experience section.",
     "treatment": ("A profile-completion module prompts the member to add a volunteer-experience section and "
                   "includes the line 'Add more color to your professional identity by showing what you care about.'"),
     "primary_metric": "edits of the volunteer-experience section",
     "prose": ("A professional network shows members a profile-completion module suggesting sections to add. In "
               "the control condition the module prompts the member to add a volunteer-experience section. In "
               "the treatment condition the module shows the same prompt and additionally includes the line 'Add "
               "more color to your professional identity by showing what you care about.' Members were randomly "
               "assigned to one version. The primary metric is edits of the volunteer-experience section."),
     "availability_notes": ("First-party engineering-blog case; no per-arm aggregate tables available (arm tables "
                            "null). The treatment is inherently an added persuasive line; the portfolio's "
                            "independent auditor ruled this an inherent-mechanic asymmetry, not an authoring leak.")},
    {"id": "cur_15", "src_id": "etsy_infinite_scroll_search",
     "source": "Dan McKinley (Etsy), Design for Continuous Experimentation (via PORTFOLIO_CASES_V3.json)",
     "company_context": "Handmade/vintage e-commerce marketplace; search results page for shoppers.",
     "control": "Search results are shown in numbered pages; the user clicks a page link to load more results.",
     "treatment": "Search results load automatically as the user scrolls, with more results appended below and no page links.",
     "primary_metric": "search engagement (clicks, favorites, purchases-from-search)",
     "prose": ("An e-commerce marketplace displays search results to shoppers. In the control condition results "
               "are shown in numbered pages and the user clicks a page link to load more results. In the "
               "treatment condition results load automatically as the user scrolls, with more results appended "
               "below and no page links. Users were randomly assigned to one presentation. The primary metric is "
               "search engagement, measured as clicks, favorites, and purchases from search."),
     "availability_notes": "First-party conference-talk case; no per-arm aggregate tables available (arm tables null)."},
]

# Ground-truth winner per source case (from PORTFOLIO_CASES_V3.json real_winner; feeds ONLY the truths file).
# All primary metrics are higher-is-better, so: winner=treatment -> "up"; winner=control -> "down".
CUR_WINNER = {
    "cookiecats_gate_move": "control",
    "duolingo_weekend_amulet": "treatment",
    "msn_realestate_widget": "treatment",
    "office_online_redesign": "control",
    "msn_homepage_extra_offers": "control",
    "tinkoff_defer_passport": "treatment",
    "cxl_form_fields_9_to_6": "control",
    "multistep_form_3_vs_6": "control",
    "price_com_hk_price_ranges": "treatment",
    "amazon_credit_card_offer_relocation": "treatment",
    "msn_hotmail_link_new_tab": "treatment",
    "msn_support_personalized_answers": "treatment",
    "pinterest_signup_color_scheme": "treatment",
    "linkedin_volunteer_section_value_copy": "treatment",
    "etsy_infinite_scroll_search": "control",
}

cur_cases, cur_truths = [], []
for spec in CUR:
    src_id = spec.pop("src_id")
    case = {
        "id": spec["id"],
        "stratum": "curated",
        "source": spec["source"],
        "company_context": spec["company_context"],
        "control": spec["control"],
        "treatment": spec["treatment"],
        "primary_metric": spec["primary_metric"],
        "prose": spec["prose"],
        "arm_a_tables": None,
        "arm_b_tables": None,
        "availability_notes": spec["availability_notes"],
    }
    cur_cases.append(case)
    cur_truths.append({
        "id": spec["id"],
        "direction_primary": "up" if CUR_WINNER[src_id] == "treatment" else "down",
        "truth_source": (f"PORTFOLIO_CASES_V3.json real_winner field for source case '{src_id}' "
                         "(primary-source-verified published winner)."),
        "notes": "up = treatment beats control on the (higher-is-better) primary metric; mapped by e3p_hillstrom_build.py.",
    })

# ---------------------------------------------------------------- write artifacts

backlog = hil_cases + cc_cases + cur_cases
truths = hil_truths + cc_truths + cur_truths

backlog_path = ROOT / "e3p_backlog_local.json"
truths_path = ROOT / "e3p_truths_local.json"

backlog_path.write_text(json.dumps(backlog, indent=1) + "\n")
truths_path.write_text(json.dumps(truths, indent=1) + "\n")

sha = hashlib.sha256(truths_path.read_bytes()).hexdigest()
(ROOT / "e3p_truths_local.sha256").write_text(f"{sha}  e3p_truths_local.json\n")

# stdout: counts and paths ONLY - never directions, rates, or outcome hints.
print(f"backlog cases written: {len(backlog)} "
      f"(hillstrom={len(hil_cases)}, cookiecats={len(cc_cases)}, curated={len(cur_cases)})")
print(f"truth records written: {len(truths)}")
print(f"pilot rows drawn: {len(pilot)} of {len(rows)} (fraction={PILOT_FRACTION}, seed={SEED})")
print(f"backlog: {backlog_path}")
print(f"truths (sealed): {truths_path}")
print(f"truths sha256: {sha}")
