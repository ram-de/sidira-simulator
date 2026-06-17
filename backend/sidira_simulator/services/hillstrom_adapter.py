"""Hillstrom RCT rows → BenchmarkCase adapter (#222 Hillstrom directional uplift).

The Hillstrom mirror of `services.benchmark_adapter` (Upworthy). It turns the
randomized e-mail RCT (`services.hillstrom_archive.HillstromRow`) into the SAME
`(Capability, Hypothesis)` shape production builds, each carrying a `GroundTruth`
computed from the trial's UNBIASED difference-in-means uplift (PLAN.md §2):

    uplift_arm(Y) = E[Y | arm] − E[Y | No E-Mail]

for arm ∈ {Mens E-Mail, Womens E-Mail} and a binary outcome Y (conversion in v1;
the runner can also be pointed at `visit` — both are registered). Because
assignment was randomized, the difference in arm means is an UNBIASED estimate of
the average treatment effect — no covariate adjustment needed.

Modelling choice. The control arm ("No E-Mail") is the current state: the
customer simply does not receive a campaign e-mail. The treatment arm is the SAME
customer receiving a promotional e-mail — exactly ONE `CHANGED` copy delta: an
`email` screen whose body carries the campaign copy, added on top of the
unchanged inbox. The conversion action (click through and purchase) is the click
transition off that e-mail. This is the production copy-state-diff path, so parity
is structural, not a benchmark-only renderer (treatment-rendering-layer.md §4).

Ground truth + heterogeneity. `compute_arm_uplift` returns the overall per-arm
uplift with a bootstrap CI; `compute_segment_uplift` returns the PER-SEGMENT
uplift across a pre-registered stratifier aligned to the committed 4-persona pack
(`mens_buyer` / `womens_buyer` / `high_spender` / `mid_tier` — see `_segment_key`)
— the endpoint #3 "does the sim know who responds most" claim (PLAN §2). Four
strata × two arms = 8 cases, clearing the null-cert's 8-experiment floor, and each
stratum conditions on ONE distinct persona sub-pack so the cases carry real
heterogeneity signal rather than re-using one audience.
Both reuse `services.statistics` helpers (no scipy/numpy). The CIs ride on the
adapter's own result dataclasses, NOT on `GroundTruth` (kept unchanged): the case
carries the point-estimate `GroundTruth` the runner scores; the richer CI /
segment structure is for the pre-registration + honesty-table layer (PR-B).
"""

from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from sidira_simulator.schemas.benchmark import BenchmarkCase, GroundTruth
from sidira_simulator.schemas.feature_pack import (
    Capability,
    Component,
    ReverseFigma,
    Screen,
    Transition,
)
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.hillstrom_archive import (
    SEGMENT_MENS,
    SEGMENT_NO_EMAIL,
    SEGMENT_WOMENS,
    HillstromRow,
)
from sidira_simulator.services.statistics import bootstrap_percentile_ci

_SOURCE = "hillstrom"

# Screen / component / transition ids for the e-mail touchpoint state-diff.
INBOX_SCREEN_ID = "inbox"
EMAIL_SCREEN_ID = "promo_email"
EMAIL_BODY_COMPONENT_ID = "email_body"
CLICK_TRIGGER = "click_email"

# The treatment arms we adapt (control is always No E-Mail). Maps an arm name to a
# short campaign descriptor used in the rendered copy + PRD.
_TREATMENT_ARMS: dict[str, str] = {
    SEGMENT_MENS: "men's merchandise",
    SEGMENT_WOMENS: "women's merchandise",
}

# Default bootstrap config for the difference-in-means CI (matches the
# 1000-resample convention in statistics.py / scoring.py).
_BOOTSTRAP_RESAMPLES = 1000
# Stable mask so the adapter's uplift-CI RNG stream is reproducible and distinct
# from the runner / null-cert streams.
_UPLIFT_SEED_MIX = 0x48_49_4C_4C_53_54  # "HILLST" as hex bytes


@dataclass(frozen=True)
class ArmUplift:
    """Overall difference-in-means uplift of one treatment arm vs No E-Mail.

    `observed_lift = treatment_rate − control_rate` (raw probability delta, the
    same unit as `GroundTruth.observed_lift`). `ci` is a percentile-bootstrap
    interval on that delta; `n_control` / `n_treatment` size the estimate so a
    downstream power check (PLAN §5 — conversion is a small effect) is explicit.
    """

    arm: str
    metric_name: str
    control_rate: float
    treatment_rate: float
    observed_lift: float
    ci: tuple[float, float]
    n_control: int
    n_treatment: int


@dataclass(frozen=True)
class SegmentUplift:
    """Per-segment uplift of one treatment arm vs No E-Mail within a stratum.

    The endpoint #3 heterogeneity material (PLAN §2): does the arm move THIS
    stratum (e.g. the mens_buyer cohort) more than another? Same fields as
    `ArmUplift`, plus the `segment` key naming the stratum.
    """

    arm: str
    segment: str
    metric_name: str
    control_rate: float
    treatment_rate: float
    observed_lift: float
    ci: tuple[float, float]
    n_control: int
    n_treatment: int


def _outcome(row: HillstromRow, metric_name: str) -> int:
    """The binary outcome value for `metric_name` (the two scorable v1 metrics)."""
    if metric_name == "conversion":
        return row.conversion
    if metric_name == "visit":
        return row.visit
    raise ValueError(
        f"unsupported Hillstrom metric_name {metric_name!r}; v1 scores 'conversion' "
        "and 'visit' only (spend is continuous/zero-inflated — out of scope)"
    )


def _rate(values: Sequence[int]) -> float:
    """Mean of a 0/1 sequence (the arm's outcome rate). 0.0 on an empty arm."""
    return (sum(values) / len(values)) if values else 0.0


def _winner(lift: float) -> str:
    if lift > 0.0:
        return "treatment"
    if lift < 0.0:
        return "control"
    return "tie"


def _bootstrap_lift_ci(
    control: Sequence[int],
    treatment: Sequence[int],
    *,
    seed: int,
    n_resamples: int,
) -> tuple[float, float]:
    """Percentile-bootstrap CI on the difference in means (treatment − control).

    Resamples each arm independently with replacement and recomputes the rate
    delta, reusing `statistics.bootstrap_percentile_ci`. On an empty arm the CI
    collapses to the point estimate (no resampling signal), surfaced honestly
    rather than raising.
    """
    if not control or not treatment:
        point = _rate(treatment) - _rate(control)
        return (point, point)
    rng = random.Random(seed ^ _UPLIFT_SEED_MIX)
    n_c = len(control)
    n_t = len(treatment)

    def _delta(_ignored: Sequence[int]) -> float:
        # bootstrap_percentile_ci resamples its `data` arg, but we need to resample
        # BOTH arms per draw; ignore the passed resample and draw both arms here.
        c = rng.choices(control, k=n_c)
        t = rng.choices(treatment, k=n_t)
        return _rate(t) - _rate(c)

    # The `data` we hand the helper is a throwaway non-empty sequence; the real
    # two-arm resampling happens inside `_delta`. Pass `control` so n matches.
    return bootstrap_percentile_ci(
        list(control),
        _delta,
        n_resamples=n_resamples,
        rng=rng,
    )


def compute_arm_uplift(
    rows: Sequence[HillstromRow],
    arm: str,
    *,
    metric_name: str = "conversion",
    seed: int = 0,
    n_resamples: int = _BOOTSTRAP_RESAMPLES,
) -> ArmUplift:
    """Overall difference-in-means uplift of `arm` vs No E-Mail (PLAN §2).

    Raises ValueError on an unknown arm / metric. The control rate is the
    No-E-Mail outcome rate over ALL rows; the treatment rate is the arm's rate.
    Because assignment was randomized this difference is an unbiased ATE estimate.
    """
    if arm not in _TREATMENT_ARMS:
        raise ValueError(
            f"unknown treatment arm {arm!r}; expected one of {sorted(_TREATMENT_ARMS)}"
        )
    control = [_outcome(r, metric_name) for r in rows if r.segment == SEGMENT_NO_EMAIL]
    treatment = [_outcome(r, metric_name) for r in rows if r.segment == arm]
    control_rate = _rate(control)
    treatment_rate = _rate(treatment)
    lift = treatment_rate - control_rate
    ci = _bootstrap_lift_ci(control, treatment, seed=seed, n_resamples=n_resamples)
    return ArmUplift(
        arm=arm,
        metric_name=metric_name,
        control_rate=control_rate,
        treatment_rate=treatment_rate,
        observed_lift=lift,
        ci=ci,
        n_control=len(control),
        n_treatment=len(treatment),
    )


# The leading rank (1..7) of a `history_segment` cell (e.g. "5) $500 - $750" → 5).
# A high-spender is rank >= this; everything below is mid/low tier. This boundary
# matches the committed pack's clustering: the high-spender persona (P03) centres
# on history_segment 5-7 ($500+), the mid-tier persona (P04) on 3-4 ($200-500).
_HIGH_SPEND_TIER = 5


def _history_tier(history_segment: str) -> int:
    """The leading integer rank of a Hillstrom `history_segment` cell.

    The dataset spells the cell as ``"<rank>) $lo - $hi"`` (rank 1..7, ascending
    spend). We read the rank off the leading digits so the spend-tier split is
    robust to the exact dollar wording. Returns 0 for an unparseable cell so it
    falls into the low/mid tier rather than crashing the stratifier."""
    head = history_segment.strip().split(")", 1)[0].strip()
    try:
        return int(head)
    except ValueError:
        return 0


def _segment_key(row: HillstromRow) -> str:
    """Pre-registered heterogeneity stratifier aligned to the committed 4-persona
    pack (PLAN §2, endpoint #3).

    The earlier (gender-only) stratifier collapsed every both-gender buyer into a
    single ``both_history`` stratum, yielding only 3 strata on the real trial (it
    has no mens=0∧womens=0 customers) → 6 by-segment cases, below the null-cert's
    8-experiment floor. This finer key matches the 4 GMM personas the pack
    actually clusters, so each stratum conditions on ONE distinct persona sub-pack
    (the heterogeneity signal endpoint #3 measures):

        womens_buyer  → P01  (womens-only buyer)
        mens_buyer    → P02  (mens-only buyer)
        high_spender  → P03  (buys BOTH genders, history_segment >= 5 i.e. $500+)
        mid_tier      → P04  (buys BOTH genders, history_segment <= 4)

    STRUCTURALLY BLIND: keyed ONLY on pre-treatment features (mens / womens flags
    + history_segment spend tier) — never on `segment` (the arm), `visit`,
    `conversion`, or any outcome. Stable, freezable keys so the pre-registration
    hash can pin them. A single-gender buyer is keyed by gender regardless of
    spend (P01/P02 are the trial's low-spend single-gender clusters); a both-gender
    buyer is split by spend tier into the high-spender / mid-tier clusters."""
    single_gender = row.mens != row.womens  # exactly one of the two flags set
    if single_gender:
        return "mens_buyer" if row.mens else "womens_buyer"
    if row.mens and row.womens:
        return (
            "high_spender" if _history_tier(row.history_segment) >= _HIGH_SPEND_TIER else "mid_tier"
        )
    # Neither gender flag (no recorded purchase history). The real trial has none,
    # but an edge CSV could; key it to the mid-tier cluster (the lowest-commitment
    # both/neither cohort) so it stays a known stratum the loader can condition.
    return "mid_tier"


def compute_segment_uplift(
    rows: Sequence[HillstromRow],
    arm: str,
    *,
    metric_name: str = "conversion",
    seed: int = 0,
    n_resamples: int = _BOOTSTRAP_RESAMPLES,
) -> list[SegmentUplift]:
    """Per-segment uplift of `arm` vs No E-Mail across the heterogeneity strata.

    The endpoint #3 material (PLAN §2): within each `_segment_key` stratum, the
    arm's outcome rate minus the No-E-Mail rate IN THAT SAME stratum (so the
    control is matched on the stratum). Strata are emitted in a stable sorted order
    so the pre-registration hash is reproducible. A stratum with no control or no
    treatment rows is still emitted (with a degenerate CI) rather than dropped, so
    coverage stays honest.
    """
    if arm not in _TREATMENT_ARMS:
        raise ValueError(
            f"unknown treatment arm {arm!r}; expected one of {sorted(_TREATMENT_ARMS)}"
        )
    control_by_seg: dict[str, list[int]] = defaultdict(list)
    treatment_by_seg: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        key = _segment_key(r)
        if r.segment == SEGMENT_NO_EMAIL:
            control_by_seg[key].append(_outcome(r, metric_name))
        elif r.segment == arm:
            treatment_by_seg[key].append(_outcome(r, metric_name))

    out: list[SegmentUplift] = []
    for i, key in enumerate(sorted(set(control_by_seg) | set(treatment_by_seg))):
        control = control_by_seg.get(key, [])
        treatment = treatment_by_seg.get(key, [])
        control_rate = _rate(control)
        treatment_rate = _rate(treatment)
        lift = treatment_rate - control_rate
        # Per-stratum seed so each stratum's bootstrap stream is distinct yet
        # reproducible for a fixed base seed.
        ci = _bootstrap_lift_ci(control, treatment, seed=seed + i + 1, n_resamples=n_resamples)
        out.append(
            SegmentUplift(
                arm=arm,
                segment=key,
                metric_name=metric_name,
                control_rate=control_rate,
                treatment_rate=treatment_rate,
                observed_lift=lift,
                ci=ci,
                n_control=len(control),
                n_treatment=len(treatment),
            )
        )
    return out


def _email_figma(received: bool, campaign: str) -> ReverseFigma:
    """The inbox state for one arm.

    Control (No E-Mail): the inbox carries no campaign e-mail — only the unchanged
    inbox screen. Treatment: the SAME inbox plus a `promo_email` screen whose body
    carries the campaign copy, with a click transition to it. The single CHANGED
    delta between the two states is the addition of the e-mail body copy.
    """
    screens = [Screen(id=INBOX_SCREEN_ID, name="Inbox", components=[])]
    transitions: list[Transition] = []
    if received:
        body = (
            f"A promotional e-mail showcasing {campaign}. Tap through to browse the "
            "featured items and check out."
        )
        screens.append(
            Screen(
                id=EMAIL_SCREEN_ID,
                name="Promotional e-mail",
                components=[
                    Component(id=EMAIL_BODY_COMPONENT_ID, role="body", text=body),
                ],
            )
        )
        transitions.append(
            Transition(
                trigger=CLICK_TRIGGER,
                from_screen=EMAIL_SCREEN_ID,
                to_screen=INBOX_SCREEN_ID,
            )
        )
    return ReverseFigma(screens=screens, transitions=transitions)


def _arm_capability_hypothesis(arm: str) -> tuple[Capability, Hypothesis]:
    """The shared `(Capability, Hypothesis)` copy-delta pair for a treatment arm.

    The structural blindness boundary: this carries ONLY the e-mail copy delta
    (control = no e-mail, treatment = the arm's campaign e-mail), never any
    outcome / ground-truth signal. Reused by the arm-level and per-segment case
    builders so both score the IDENTICAL rendered change — the per-segment cases
    differ only in their ground truth + case_id, never in the stimulus.
    """
    campaign = _TREATMENT_ARMS[arm]
    reverse_prd = (
        "A returning customer is in their inbox; in the current experience they "
        "receive no promotional e-mail from the store."
    )
    capability = Capability(
        name="promotional e-mail campaign",
        surfaces=["email"],
        roles=["customer"],
        entry_points=["inbox"],
        reverse_prd=reverse_prd,
        reverse_figma=_email_figma(received=False, campaign=campaign),
        implicit_metric=("site visit and purchase conversion after the campaign touchpoint"),
    )
    hypothesis = Hypothesis(
        capability_name=capability.name,
        prose=(
            f"Send the customer a promotional e-mail featuring {campaign}. Nothing "
            "else about their experience changes — only the e-mail is added."
        ),
        proposed_prd=None,
        proposed_figma=_email_figma(received=True, campaign=campaign),
    )
    return capability, hypothesis


def build_hillstrom_case(
    rows: Sequence[HillstromRow],
    arm: str,
    *,
    metric_name: str = "conversion",
    seed: int = 0,
    n_resamples: int = _BOOTSTRAP_RESAMPLES,
) -> BenchmarkCase:
    """Build ONE benchmark case for a treatment arm vs the No-E-Mail control.

    The case is the SAME `(Capability, Hypothesis)` shape production builds:
    control = no campaign e-mail; treatment = the campaign e-mail as a copy delta.
    `GroundTruth` carries the trial's overall difference-in-means uplift point
    estimate for `metric_name` (the runner scores predicted-vs-observed lift); the
    richer per-arm / per-segment CI structure is returned separately by
    `compute_arm_uplift` / `compute_segment_uplift` for pre-registration.

    Raises ValueError on an unknown arm / metric.
    """
    uplift = compute_arm_uplift(
        rows, arm, metric_name=metric_name, seed=seed, n_resamples=n_resamples
    )
    capability, hypothesis = _arm_capability_hypothesis(arm)

    ground_truth = GroundTruth(
        metric_name=metric_name,
        control_metric=uplift.control_rate,
        treatment_metric=uplift.treatment_rate,
        observed_lift=uplift.observed_lift,
        winner=_winner(uplift.observed_lift),
    )

    # case_id encodes (source-implied) arm + metric so it is stable + unique across
    # the two arms × two metrics enumerated from one trial.
    arm_slug = arm.lower().replace(" ", "_").replace("-", "")
    return BenchmarkCase(
        case_id=f"hillstrom:{arm_slug}:{metric_name}",
        source=_SOURCE,
        capability=capability,
        hypothesis=hypothesis,
        ground_truth=ground_truth,
    )


def build_hillstrom_segment_case(
    seg: SegmentUplift,
    arm: str,
) -> BenchmarkCase:
    """Build one per-SEGMENT benchmark case from a `SegmentUplift` (endpoint #3).

    The heterogeneity material (PLAN §2 #3): a case whose `GroundTruth` is the
    arm's uplift WITHIN one purchase-history stratum, so a run can be scored on
    whether the sim predicts the men's e-mail moves men-history customers more
    than women-history ones — the only non-trivially-guessable endpoint.

    The stimulus (capability + hypothesis copy delta) is IDENTICAL to the
    arm-level case for this arm — only the ground truth (per-stratum uplift) and
    the case_id (which carries the 4th `:<segment>` component the `by_segment`
    honesty stratifier reads) differ. The predictor stays blind: the stratum is
    encoded ONLY in the case_id/ground_truth, never in the rendered change.
    """
    capability, hypothesis = _arm_capability_hypothesis(arm)
    ground_truth = GroundTruth(
        metric_name=seg.metric_name,
        control_metric=seg.control_rate,
        treatment_metric=seg.treatment_rate,
        observed_lift=seg.observed_lift,
        winner=_winner(seg.observed_lift),
    )
    arm_slug = arm.lower().replace(" ", "_").replace("-", "")
    return BenchmarkCase(
        case_id=f"hillstrom:{arm_slug}:{seg.metric_name}:{seg.segment}",
        source=_SOURCE,
        capability=capability,
        hypothesis=hypothesis,
        ground_truth=ground_truth,
    )


def hillstrom_segment_cases(
    rows: Sequence[HillstromRow],
    *,
    metric_name: str = "conversion",
    seed: int = 0,
    n_resamples: int = _BOOTSTRAP_RESAMPLES,
) -> list[BenchmarkCase]:
    """Enumerate per-(arm × heterogeneity-segment) cases (endpoint #3).

    For each treatment arm (Mens / Womens E-Mail) and each pre-registered
    purchase-history stratum (`_segment_key`), one case whose ground truth is that
    arm's uplift within that stratum. These carry the 4-component case_id the
    `benchmark_honesty.by_segment` stratifier reads, so directional accuracy can
    be reported per heterogeneity stratum. Raises ValueError if `rows` is empty.

    VALIDITY REQUIREMENT (the endpoint-#3 crux). The cases for one arm differ ONLY
    in ground truth + case_id — their stimulus (capability + hypothesis) is
    deliberately IDENTICAL, and the predictor is blind to ground_truth/case_id. So
    a caller that scores these against ONE undifferentiated audience would have the
    engine emit the same prediction for every stratum (seed noise), measuring
    nothing. The runner MUST condition the simulated audience on the stratum —
    e.g. via `hillstrom_panel_loader.hillstrom_segment_subpack` — for the
    per-segment scores to reflect heterogeneous response. The `benchmark-hillstrom`
    CLI does exactly this (it runs each stratum against its sub-pack).
    """
    if not rows:
        raise ValueError("hillstrom_segment_cases requires at least one row")
    cases: list[BenchmarkCase] = []
    for arm in (SEGMENT_MENS, SEGMENT_WOMENS):
        for seg in compute_segment_uplift(
            rows, arm, metric_name=metric_name, seed=seed, n_resamples=n_resamples
        ):
            cases.append(build_hillstrom_segment_case(seg, arm))
    return cases


def hillstrom_rows_to_cases(
    rows: Sequence[HillstromRow],
    *,
    metric_name: str = "conversion",
    seed: int = 0,
    n_resamples: int = _BOOTSTRAP_RESAMPLES,
) -> list[BenchmarkCase]:
    """Enumerate both treatment arms (Mens / Womens E-Mail) as benchmark cases.

    Each arm is one case: control = No E-Mail, treatment = that arm's campaign
    e-mail, with the trial's measured uplift as ground truth. Raises ValueError if
    `rows` is empty (nothing to estimate a rate from is a caller bug).
    """
    if not rows:
        raise ValueError("hillstrom_rows_to_cases requires at least one row")
    return [
        build_hillstrom_case(rows, arm, metric_name=metric_name, seed=seed, n_resamples=n_resamples)
        for arm in (SEGMENT_MENS, SEGMENT_WOMENS)
    ]
