"""
Feature taxonomy as data — the canonical 33-class feature-store schema
(FEATURE_STORE_SPEC.md §2) encoded so a persona pack can be scored against it.

PRODUCT-AGNOSTIC by construction. The 33 feature CLASSES are domain-neutral
CONCEPTS (a "per-surface friction telemetry" class, a "lifecycle/RFM/habit"
class, …). Only the column-NAME patterns are vertical-specific, so they are
split in two:

  - `generic_patterns` : vertical-NEUTRAL signal words that appear across
                         products (e.g. "recency", "tenure", "mis_tap",
                         "time_to", "churn", "latency"). These are the
                         best-effort fallback when no vertical/column map is
                         supplied.
  - `ADAPTERS[vertical][code]` : the domain-specific column-name patterns for a
                         given vertical (marketplace, saas, ecommerce,
                         content_media, fintech). Scored patterns =
                         ADAPTERS[vertical][class] ∪ generic_patterns.

Each `FeatureClass` carries:
  - `concept`      : a one-line domain-neutral description of the class.
  - `generic_patterns` : case-insensitive substring/regex fragments matched
                     against a pack's column NAMES (vertical-neutral).
  - `data_source`  : where the class is sourced from (§2 notation).
  - `weight`       : roadmap-coverage contribution (§3/§5 priority) → the score roll-up.
  - `requires_variation` : True for classes whose VALUE needs historical treatment/
                     price variation, not mere presence (A1, A2, B3, B4). Presence +
                     spread is only a proxy for the real support these need.
  - `unlocks`      : experiment-type keys this class helps ground.

`EXPERIMENT_REGISTRY` maps the canonical experiment types to their required
(non-guard) feature classes, drawn from the §3 coverage matrix, and flags the
structurally-`abstain_only` families (§4).

Patterns are intentionally generous-but-specific: a single column may match more
than one class (a column can inform several classes), which is by design.

HONEST two-sidedness: the supply-equilibrium classes (F1/F2/F3) and the
two-sided supply ENTITY class (E2) carry NO adapter patterns for single-sided
verticals (saas, content_media, fintech, and 1P ecommerce). Those products do
not run two-sided experiments, so the score correctly reflects that they can't
answer them.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# --------------------------------------------------------------------------- #
# Weight tiers (relative, defensible — see §5 build-priority ordering)
# --------------------------------------------------------------------------- #
W_HIGH = 3.0    # the reusable spine + dominant anchor: C1, B1, A2, A1
W_MED = 2.0     # high-value moderators / entity / context classes
W_LOW = 1.0     # long-tail, low-confidence, abstain-leaning classes
W_GUARD = 1.5   # validity gates (enablers, not direct predictors)


@dataclass(frozen=True)
class FeatureClass:
    code: str
    name: str
    group: str                       # A..I
    generic_patterns: list[str]      # vertical-NEUTRAL substring/regex vs column names
    data_source: str                 # transactions|telemetry|profile|experiment-history|external|derived
    weight: float
    requires_variation: bool = False
    unlocks: list[str] = field(default_factory=list)
    concept: str = ""                # one-line domain-neutral description


@dataclass(frozen=True)
class ExperimentType:
    """A canonical experiment family and the feature classes required to ground its
    sign. `required` lists the core non-guard classes (§3 'R'); guards (H*) are
    universal and handled separately. `abstain_only` marks the §4 hard-floor /
    structurally-unidentifiable families."""
    required: list[str]
    abstain_only: bool = False
    reason: str = ""


# --------------------------------------------------------------------------- #
# The 33 feature classes
# --------------------------------------------------------------------------- #
TAXONOMY: list[FeatureClass] = [
    # --- A. Empirical anchor classes ------------------------------------- #
    FeatureClass(
        "A1", "Experiment-history prior store", "A",
        ["treatment_family", "experiment_change_type", "experiment_history",
         "prior_experiment", "n_prior_experiment", "historical_lift",
         "historical_effect", "measured_effect_magnitude", "measured_friction_delta",
         "win_rate_for_family", "historical_hte", "prior_.*_arm_response"],
        "experiment-history", W_HIGH, requires_variation=True,
        unlocks=["ui_friction_flow", "checkout_onboarding", "pricing_promo",
                 "ranking_recs", "notification_lifecycle"],
        concept="prior measured effect/lift of past experiments, keyed by change-family"),
    FeatureClass(
        "A2", "Pre-period covariates (CUPED/CUPAC)", "A",
        ["cuped", "cupac", "pre_period", "predicted_outcome_baseline",
         "pre_treatment_baseline"],
        "derived", W_HIGH, requires_variation=True,
        unlocks=["ui_friction_flow", "pricing_promo", "ranking_recs", "latency_perf"],
        concept="pre-period baseline covariate that de-noises the outcome (CUPED/CUPAC)"),

    # --- B. User state / propensity classes ------------------------------ #
    FeatureClass(
        "B1", "Lifecycle / RFM / habit state", "B",
        ["rfm", "recency", "frequency", "tenure", "lifecycle", "account_age",
         "days_since", "habit", "monetary", "power_user", "active_days",
         "weekly_active_streak"],
        "transactions", W_HIGH,
        unlocks=["checkout_onboarding", "notification_lifecycle", "pricing_promo"],
        concept="where the user sits in the lifecycle: recency/frequency/tenure/habit state"),
    FeatureClass(
        "B2", "Monetization / churn / membership", "B",
        ["ltv", "churn", "subscription", "membership", "is_member", "loyalty_tier",
         "renewal", "trial_status", "points_balance", "margin_per_user",
         "incentive_roi"],
        "profile", W_MED,
        unlocks=["pricing_promo", "notification_lifecycle"],
        concept="monetization state: subscription/membership, churn risk, lifetime value"),
    FeatureClass(
        "B3", "Price/fee elasticity & deal-proneness", "B",
        ["elasticity", "discount", "price_sens", "coupon", "promo", "deal", "wtp",
         "redemption_rate", "incentive_response"],
        "derived", W_MED, requires_variation=True,
        unlocks=["pricing_promo"],
        concept="sensitivity of behavior to a price/cost/incentive change"),
    FeatureClass(
        "B4", "Reference-price & anchoring", "B",
        ["reference_price", "anchor", "last_paid", "avg_seen_price", "price_gap",
         "discount_depth_vs_reference"],
        "derived", W_MED, requires_variation=True,
        unlocks=["pricing_promo"],
        concept="reference-price/anchoring: how a price reads relative to expectation"),
    FeatureClass(
        "B5", "Preference / substitution / choice-set", "B",
        ["affinity", "brand_loyalty", "novelty_seeking", "embedding_user",
         "user_embedding", "substitution", "choice_set", "category_concentration",
         "outside_option", "price_tier_pref"],
        "derived", W_MED,
        unlocks=["ranking_recs"],
        concept="taste / substitution structure: which alternatives a user would switch to"),
    FeatureClass(
        "B6", "Channel responsiveness & fatigue", "B",
        ["push_open", "email_ctr", "push_opt_in", "msgs_received", "fatigue",
         "unsubscribe", "best_send_hour", "channel_pref", "sends_7d", "notif"],
        "telemetry", W_MED,
        unlocks=["notification_lifecycle"],
        concept="responsiveness and fatigue to messaging across channels"),
    FeatureClass(
        "B7", "Friction / cognitive-load & default-acceptance", "B",
        ["form_abandon", "decision_paralysis", "steps_tolerance", "rage_tap",
         "default_acceptance", "kept_default", "default_override", "cognitive_load",
         "opt_out_friction", "preselected"],
        "derived", W_MED,
        unlocks=["ui_friction_flow", "checkout_onboarding"],
        concept="tolerance for friction and tendency to accept defaults"),
    FeatureClass(
        "B8", "Trust / social-proof / scarcity sensitivity", "B",
        ["reviews_read", "review_read_depth", "rating_sensitivity", "scarcity",
         "social_proof", "skepticism", "risk_aversion", "countdown",
         "guarantee_redeem"],
        "derived", W_LOW,
        unlocks=["trust_social_proof"],
        concept="how much trust signals (reviews, scarcity, guarantees) move the user"),
    FeatureClass(
        "B9", "Referral / social-graph propensity", "B",
        ["referral", "invite_propensity", "social_connectedness", "social_graph"],
        "derived", W_LOW,
        unlocks=["acquisition"],
        concept="propensity to refer / invite, and position in the social graph"),
    FeatureClass(
        "B10", "Proficiency / familiarity / habituation", "B",
        ["proficiency", "muscle_memory", "familiarity", "habituation",
         "prior_error_rate", "feature_adoption_breadth", "surface_visit_count"],
        "profile", W_LOW,
        unlocks=["ui_friction_flow"],
        concept="how practiced the user is with the surface (proficiency/habituation)"),

    # --- C. Session / interaction telemetry classes ---------------------- #
    FeatureClass(
        "C1", "Per-surface friction & funnel telemetry", "C",
        ["mis_tap", "mistap", "rage_tap", "rage_click", "dead_click", "error_click",
         "time_to", "time_on", "median_dwell", "dwell", "backtrack", "scroll",
         "tap_target", "step_completion", "step_abandon", "hesitation", "funnel",
         "abandon", "drop_off", "truncation", "payment_retry", "save_resume"],
        "telemetry", W_HIGH,
        unlocks=["ui_friction_flow", "checkout_onboarding"],
        concept="per-surface friction and funnel telemetry: mis-taps, dwell, drop-off, time-to-action"),
    FeatureClass(
        "C2", "Attention / engagement signals", "C",
        ["viewport_impression", "hover_dwell", "scroll_velocity", "scroll_reversal",
         "items_viewed", "above_fold_dwell", "element_view_to_tap",
         "truncation_view", "banner_blindness", "carousel_swipe", "scroll_depth_p"],
        "telemetry", W_MED,
        unlocks=["ui_friction_flow", "ranking_recs"],
        concept="attention signals: impressions, dwell, scroll behavior, view-to-action"),
    FeatureClass(
        "C3", "Latency / QoE / performance", "C",
        ["render_ms", "time_to_interactive", "api_response_ms", "latency",
         "skeleton_to_content", "jank", "cold_start_ms", "crash_rate",
         "api_timeout", "app_latency", "connection_class"],
        "telemetry", W_MED,
        unlocks=["latency_perf"],
        concept="latency / quality-of-experience: render time, crashes, jank"),
    FeatureClass(
        "C4", "Session intent / state", "C",
        ["session_intent", "session_depth", "entry_channel", "elapsed_session",
         "time_of_day_bucket", "screens_per_session"],
        "derived", W_MED,
        unlocks=["ui_friction_flow", "notification_lifecycle"],
        concept="what the session is for: intent, depth, entry channel"),
    FeatureClass(
        "C5", "Search / browse intent behavior", "C",
        ["browse_vs_search", "filters_used", "results_scrolled", "query_specificity",
         "query_refinement", "zero_result_abandon", "search_to_action"],
        "telemetry", W_MED,
        unlocks=["ranking_recs"],
        concept="search/browse intent behavior: query refinement, filter use, zero-result abandon"),

    # --- D. Context / device classes ------------------------------------- #
    FeatureClass(
        "D1", "Device / platform / modality / a11y", "D",
        ["platform", "device_tier", "device_class", "app_version", "screen_width",
         "screen_size", "input_modality", "os_platform", "connection_type",
         "reduced_motion", "rtl_flag", "locale", "dynamic_text_scale"],
        "telemetry", W_MED,
        unlocks=["ui_friction_flow", "latency_perf"],
        concept="device, platform, input modality and accessibility context"),
    FeatureClass(
        "D2", "Temporal / seasonality / external", "D",
        ["hour_of_day", "daypart", "day_of_week", "is_holiday", "weather",
         "local_event", "days_to_payday", "seasonality", "macro_demand",
         "median_income_zip", "market_maturity"],
        "external", W_MED,
        unlocks=["pricing_promo", "notification_lifecycle"],
        concept="temporal and external context: time, seasonality, local conditions"),

    # --- E. Entity (supply-side & content) classes ----------------------- #
    FeatureClass(
        "E1", "Per-item content / quality / price", "E",
        ["item_ctr", "avg_rating", "review_count", "has_photo",
         "content_completeness", "popularity_rank", "is_long_tail", "item_price",
         "item_margin", "price_dispersion", "out_of_stock", "is_sponsored"],
        "transactions", W_MED,
        unlocks=["ranking_recs", "trust_social_proof"],
        concept="per-item content/quality/price attributes of the thing being ranked or shown"),
    FeatureClass(
        "E2", "Per-supplier quality / reliability / economics", "E",
        # NEUTRAL two-sided supply terms only; vertical-specific (merchant/dasher/
        # GOV) live in ADAPTERS['marketplace']. Single-sided verticals get NONE.
        ["supplier_rating", "provider_rating", "provider_reliability",
         "seller_quality", "supply_partner_rating", "fulfillment_reliability"],
        "transactions", W_MED,
        unlocks=["ranking_recs", "trust_social_proof", "marketplace_supply"],
        concept="the supply-side ENTITY in a two-sided market: provider/seller quality, reliability, economics"),
    FeatureClass(
        "E3", "Treatment-surface position / composition", "E",
        ["funnel_depth", "baseline_traffic_share", "above_fold_flag", "exposure_rate",
         "interactive_element_count", "primary_cta_size", "cta_contrast",
         "text_char_length", "is_truncated", "tap_target_min_size", "media_present",
         "default_preselected", "step_count", "surface_position"],
        "derived", W_MED,
        unlocks=["ui_friction_flow"],
        concept="composition of the treated surface: CTA size/contrast, element count, truncation"),

    # --- F. Marketplace-equilibrium classes (two-sided / network only) --- #
    FeatureClass(
        "F1", "Market supply/demand balance", "F",
        ["supply_demand", "active_supply", "order_backlog", "surge", "undersupplied",
         "busyness", "capacity_utilization"],
        "telemetry", W_LOW,
        unlocks=["marketplace_supply"],
        concept="instantaneous balance of supply and demand in a two-sided market"),
    FeatureClass(
        "F2", "Cross-side spillover / cannibalization", "F",
        ["substitute_share", "cannibalization", "cross_side_load",
         "cluster_interference", "market_share_of_treated"],
        "derived", W_LOW,
        unlocks=["marketplace_supply"],
        concept="spillover/cannibalization across the two sides or substitutes"),
    FeatureClass(
        "F3", "Network / cluster / interference-exposure", "F",
        ["cluster_id", "graph_degree", "neighbor_treated", "interference_exposure",
         "switchback", "treated_neighbor"],
        "derived", W_LOW,
        unlocks=["marketplace_supply"],
        concept="network/cluster interference exposure (needs switchback/cluster design)"),

    # --- G. Acquisition & semantic classes ------------------------------- #
    FeatureClass(
        "G1", "Anonymous / pre-login visitor", "G",
        ["visitor_id", "first_touch", "attribution", "device_fingerprint",
         "device_graph", "loggedout", "landing_page", "referrer_domain", "utm_",
         "install_attribution"],
        "telemetry", W_LOW,
        unlocks=["acquisition"],
        concept="the anonymous / pre-login visitor entity (first-touch, attribution)"),
    FeatureClass(
        "G2", "Creative / copy / image embeddings", "G",
        ["copy_text_embedding", "image_embedding", "llm_judge", "readability_grade",
         "sentiment_polarity", "headline_specificity", "visual_salience"],
        "derived", W_LOW,
        unlocks=["acquisition", "aesthetic_brand"],
        concept="semantic embeddings of creative/copy/imagery"),

    # --- H. Guard / validity classes (gates, not predictors) ------------- #
    FeatureClass(
        "H1", "Negative-control / confound guard", "H",
        ["neg_control", "negative_control", "pre_treatment_metric_balance",
         "placebo", "confound_proxy", "guard_floor", "neg_control_ratio"],
        "derived", W_GUARD,
        unlocks=[],
        concept="negative-control / confound guard (does a placebo channel stay null)"),
    FeatureClass(
        "H2", "Assignment-validity / SRM guard", "H",
        ["srm", "exposure_log_completeness", "trigger_dilution", "peeking",
         "assignment_imbalance", "variance_inflation"],
        "derived", W_GUARD,
        unlocks=[],
        concept="assignment-validity / SRM guard (is randomization intact)"),
    FeatureClass(
        "H3", "Consent / coverage / data-quality", "H",
        ["att_consent", "analytics_consent", "telemetry_coverage", "logging_gap",
         "feature_missingness"],
        "derived", W_GUARD,
        unlocks=[],
        concept="consent / logging coverage / data-quality guard"),

    # --- I. Longitudinal & cross-experiment classes ---------------------- #
    FeatureClass(
        "I1", "Novelty / time-since-exposure decay", "I",
        ["exposure_age", "response_slope", "habituation_curve", "novelty_lift_decay",
         "day1_vs_day30", "cumulative_exposure"],
        "derived", W_LOW,
        unlocks=[],
        concept="novelty decay: how the effect changes with time since exposure"),
    FeatureClass(
        "I2", "Long-horizon surrogate / proxy", "I",
        ["surrogate_ltv", "proxy_retention", "early_signal_to_ltv",
         "deal_seeking_training", "return_regret"],
        "derived", W_LOW,
        unlocks=[],
        concept="short-horizon surrogate for a long-horizon outcome"),
    FeatureClass(
        "I3", "Cross-experiment concurrency", "I",
        ["concurrent_arm", "co_running_treatment", "interaction_collision",
         "shared_surface_experiment"],
        "experiment-history", W_LOW,
        unlocks=[],
        concept="concurrent overlapping experiments that may interact"),
]

# Quick sanity: 33 classes, codes unique.
assert len(TAXONOMY) == 33, f"expected 33 classes, got {len(TAXONOMY)}"
assert len({c.code for c in TAXONOMY}) == 33, "duplicate class codes"

BY_CODE: dict[str, FeatureClass] = {c.code: c for c in TAXONOMY}


# --------------------------------------------------------------------------- #
# Vertical adapters — {vertical: {class_code: [domain-specific patterns]}}
#
# Effective presence patterns when a vertical is supplied =
#     ADAPTERS[vertical].get(code, []) ∪ FeatureClass.generic_patterns
#
# HONEST two-sidedness: single-sided verticals (saas, content_media, fintech,
# and 1P ecommerce) carry NO E2 / F1 / F2 / F3 keys — they don't run two-sided
# experiments, so those classes stay absent and the score reflects it.
# --------------------------------------------------------------------------- #
ADAPTERS: dict[str, dict[str, list[str]]] = {
    # ---- marketplace (food-delivery / ride-hailing style patterns) -------- #
    "marketplace": {
        "B1": ["orders", "orders_l", "orders_lifetime", "reorder", "order_count"],
        "B2": ["free_delivery_eligible", "dashpass", "delivery_subscription"],
        "B3": ["fee_paid", "abandon_rate_when_fee", "basket_value",
               "subsidy_dependence", "promo_share", "delivery_fee"],
        "B4": ["strikethrough", "menu_price_anchor"],
        "B5": ["cuisine", "repeat_merchant", "merchant_switch"],
        "B7": ["tip_rate", "preselected_addon"],
        "C1": ["cart_abandon", "time_to_order", "checkout_abandon"],
        "C3": ["payment_error_rate"],
        "C4": ["cart_present", "is_reorder_session"],
        "C5": ["search_to_order"],
        "D2": ["competitor_density", "local_price_level"],
        "E1": ["item_pcvr", "menu_item", "dish"],
        "E2": ["merchant_pcvr", "merchant_rating", "fulfillment_reliability",
               "reliability_score", "prep_time", "cancel_rate", "menu_breadth",
               "menu_depth", "photo_coverage", "is_new_merchant", "commission_rate",
               "merchant_conversion", "merchant_price_index", "tenure_on_platform",
               "catalog_freshness", "gov", "dasher", "courier"],
        "F1": ["courier_supply", "open_orders", "avg_eta", "fulfillment_rate_zone",
               "dasher_supply"],
    },
    # ---- saas (single-sided) --------------------------------------------- #
    "saas": {
        "B1": ["seats", "logins", "login_count", "last_login", "active_days",
               "days_active", "workspace_age"],
        "B2": ["mrr", "arr", "plan_tier", "seats_licensed", "subscription_tier",
               "upgrade", "downgrade", "expansion"],
        "B3": ["plan_price", "seat_price", "upgrade_elasticity", "annual_discount"],
        "B4": ["list_plan_price", "prior_plan_price"],
        "B5": ["feature_usage_mix", "module_affinity", "integration_mix"],
        "B6": ["email_digest", "in_app_nudge", "product_email"],
        "B7": ["onboarding_abandon", "setup_friction", "activation_step_drop"],
        "C1": ["time_to_complete", "workflow_abandon", "activation_step",
               "time_to_activate"],
        "C3": ["dashboard_load_ms", "query_latency"],
        "C4": ["workspace_session", "seat_session", "feature_usage"],
        "C5": ["command_palette_query", "in_app_search"],
        "D1": ["browser", "os"],
        "D2": ["billing_cycle_day"],
        "E1": ["feature_adoption", "integration_rating", "template"],
        "E3": ["onboarding_step_count", "empty_state_cta"],
    },
    # ---- ecommerce (single-sided / 1P retail) ---------------------------- #
    "ecommerce": {
        "B1": ["orders", "purchase_count", "sessions", "repeat_purchase"],
        "B2": ["loyalty", "store_credit", "subscription", "vip_tier"],
        "B3": ["coupon", "cart_discount", "price_drop_response", "promo"],
        "B4": ["strikethrough", "was_price", "list_price", "msrp"],
        "B5": ["brand_affinity", "category_affinity", "wishlist"],
        "B6": ["email_ctr", "abandoned_cart_email"],
        "B7": ["checkout_abandon", "guest_checkout", "form_field_drop"],
        "C1": ["cart_abandon", "checkout_step", "add_to_cart", "time_to_checkout"],
        "C4": ["cart_present", "browse_session"],
        "C5": ["search_to_cart", "pdp_view", "product_search"],
        "D2": ["promo_season", "sale_event", "black_friday"],
        "E1": ["sku", "catalog", "product_rating", "aov", "price", "wishlist_count"],
        "E3": ["pdp_cta_size", "checkout_step_count"],
    },
    # ---- content_media (single-sided) ------------------------------------ #
    "content_media": {
        "B1": ["active_days", "watch_streak", "sessions", "days_since_play",
               "plays", "streams"],
        "B2": ["subscription", "tier", "trial", "churn", "ad_supported"],
        "B3": ["subscription_price", "plan_downgrade", "ad_tier_switch"],
        "B5": ["genre_affinity", "title_affinity", "playlist_affinity"],
        "B6": ["push_open", "new_episode_notif", "title_drop_notif"],
        "B7": ["paywall_abandon", "signup_friction"],
        "C1": ["play_abandon", "buffering_abandon", "time_to_play", "skip_rate"],
        "C2": ["watch_time", "completion_rate", "plays", "streams", "binge_depth"],
        "C3": ["startup_time", "rebuffer_ratio", "stream_quality"],
        "C4": ["session_play", "binge_session"],
        "C5": ["title_search", "browse_to_play"],
        "D2": ["release_window", "new_season", "premiere"],
        "E1": ["title", "episode", "play_count", "watch_time_per_title",
               "content_rating", "playlist"],
        "E3": ["thumbnail", "row_position", "hero_banner"],
    },
    # ---- fintech (single-sided) ------------------------------------------ #
    "fintech": {
        "B1": ["transactions", "txn_count", "active_days", "days_since_txn"],
        "B2": ["balance", "aum", "deposit_balance", "account_tier", "premium",
               "subscription"],
        "B3": ["fee_sensitivity", "interchange", "transfer_fee_response",
               "fx_fee_response"],
        "B4": ["prior_fee", "competitor_fee_anchor"],
        "B5": ["payment_method_pref", "merchant_category_mix"],
        "B6": ["push_open", "statement_email", "payment_reminder"],
        "B7": ["kyc_abandon", "onboarding_dropoff", "verification_friction"],
        "C1": ["transfer_abandon", "kyc_step", "time_to_fund", "payment_retry",
               "deposit_abandon"],
        "C3": ["auth_latency", "payment_decline_rate"],
        "C4": ["session_balance_check", "transfer_session"],
        "C5": ["payee_search", "transaction_search"],
        "D2": ["payday", "statement_cycle"],
        "E1": ["product_apr", "card_tier", "fee_schedule", "deposit_rate"],
        "E3": ["kyc_step_count", "deposit_cta"],
    },
}


# --------------------------------------------------------------------------- #
# Experiment-type registry (§3 coverage matrix → core required non-guard classes)
# --------------------------------------------------------------------------- #
EXPERIMENT_REGISTRY: dict[str, ExperimentType] = {
    # UI / interaction / flow (CTA + layout + form/checkout friction union).
    "ui_friction_flow": ExperimentType(["C1", "C2", "E3", "B7"]),
    # Checkout / onboarding funnel.
    "checkout_onboarding": ExperimentType(["C1", "B1", "B7"]),
    # Fee / price / promo / framing.
    "pricing_promo": ExperimentType(["B3", "B4"]),
    # Search ranking / recommendation / relevance.
    "ranking_recs": ExperimentType(["B5", "E1", "C5"]),
    # Push / email / in-app cadence & content.
    "notification_lifecycle": ExperimentType(["B6"]),
    # Latency / performance.
    "latency_perf": ExperimentType(["C3"]),
    # Trust / social-proof / scarcity.
    "trust_social_proof": ExperimentType(["B8", "E1"]),
    # Two-sided / surge / dispatch / supply — needs switchback, not a tabular read.
    "marketplace_supply": ExperimentType(
        ["F1", "F3", "E2"], abstain_only=True,
        reason="interference-dominated: market-state conditions but cannot IDENTIFY "
               "the sign from per-user data; needs switchback/cluster design (§4.3)"),
    # Top-of-funnel / marketing-creative — needs an anonymous-visitor entity.
    "acquisition": ExperimentType(["G1", "G2"]),
    # Pure aesthetic / brand / taste.
    "aesthetic_brand": ExperimentType(
        ["G2"], abstain_only=True,
        reason="taste/novelty: equally-usable variants give identical friction "
               "telemetry; wins are found by testing, not predicted (§4.2)"),
    # Net-new surface with no behavioral analog.
    "net_new": ExperimentType(
        [], abstain_only=True,
        reason="cold-start hard floor: no prior, no friction analog — the surface "
               "never existed (§4.1)"),
}
