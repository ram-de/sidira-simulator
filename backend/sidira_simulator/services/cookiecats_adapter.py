"""Cookie Cats rows → BenchmarkCase adapter (in-scope product-change benchmark).

The Cookie Cats mirror of `services.hillstrom_adapter`. It turns the randomized
mobile-game A/B test (`services.cookiecats_archive.CookieCatsRow`) into the SAME
`(Capability, Hypothesis)` shape production builds, each carrying a `GroundTruth`
computed from the trial's UNBIASED difference-in-means uplift:

    uplift(Y) = E[Y | gate_40] − E[Y | gate_30]

for a binary retention outcome Y (`retention_7` primary, `retention_1`
secondary). Because assignment was randomized, the difference in arm means is an
unbiased estimate of the average treatment effect — no covariate adjustment.

THE PRODUCT CHANGE UNDER TEST. The control (`gate_30`) is the current state: the
game's first forced progress GATE sits at level 30 (a hard wait/payment wall the
player hits early). The treatment (`gate_40`) moves that same gate to level 40 —
the player gets more uninterrupted early play before the first wall. This is
exactly ONE `CHANGED` delta: the gate-level value on the "progress gate" screen.
The retention action (returning after install) is the deliberative outcome.

THE COUNTER-INTUITIVE GROUND TRUTH. The real RCT finds `gate_30` OUTPERFORMS
`gate_40` on 7-day retention (≈95% confidence) — the EARLIER gate is better, even
though naive intuition ("a later gate = more free play = happier players")
predicts the opposite. This counter-intuitiveness is what makes it a
discriminating test: a sim that just parrots priors gets the SIGN wrong. So the
observed_lift (gate_40 − gate_30) is NEGATIVE for retention_7.

HONESTY CAVEAT (carried in PREREG). The gate-timing → retention effect is itself
PARTLY BEHAVIORAL / sub-deliberative (forced-break / hedonic-adaptation
psychology), not purely a deliberative reaction to a visible change. So
introspective agent simulation MAY get it wrong too — this is a HARD test, not a
guaranteed positive.

STRATIFICATION (≥8 cases from ONE A/B). Unlike Hillstrom (2 arms × 4 segments),
Cookie Cats is a single comparison. To clear the null-cert's 8-experiment floor
we stratify the population by ENGAGEMENT into octiles of `sum_gamerounds` — eight
`eng_o1`..`eng_o8` strata, each comparing gate_30 vs gate_40 retention WITHIN that
engagement band. Octile boundaries are read off the pooled (both-arm)
`sum_gamerounds` distribution so the split is data-driven and reproducible, and
the strata align to the engagement-tier persona pack the by-segment run conditions
on. Eight strata × one comparison = 8 cases.

Reuses `services.statistics` helpers (no scipy/numpy), mirroring the Hillstrom
adapter. The CIs ride on the adapter's own result dataclasses, NOT on
`GroundTruth` (kept unchanged): the case carries the point-estimate `GroundTruth`
the runner scores; the richer CI structure is for the pre-registration layer.
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
)
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.cookiecats_archive import (
    CONTROL_VERSION,
    TREATMENT_VERSION,
    CookieCatsRow,
)
from sidira_simulator.services.statistics import bootstrap_percentile_ci

_SOURCE = "cookiecats"

# Screen / component ids for the gate-level product-change state-diff.
GAME_SCREEN_ID = "level_progress"
GATE_COMPONENT_ID = "progress_gate"

# The two scorable retention metrics. Both are scored through the engine's
# `retention` metric (the in-scope deliberative-return class); the day window
# (1 or 7) is a DATA-LAYER selector for which outcome column anchors ground truth
# and how the decision_point moment is phrased. `retention_7` is the primary
# endpoint (the one the RCT certifies, and where the counter-intuitive sign lives);
# `retention_1` is the secondary, shorter-horizon return.
RETENTION_7 = "retention_7"
RETENTION_1 = "retention_1"
SCORABLE_METRICS = frozenset({RETENTION_7, RETENTION_1})

# Default bootstrap config for the difference-in-means CI (matches the
# 1000-resample convention in statistics.py / scoring.py).
_BOOTSTRAP_RESAMPLES = 1000
# Stable mask so the adapter's uplift-CI RNG stream is reproducible and distinct
# from the runner / null-cert streams. "COOKIE" as hex bytes.
_UPLIFT_SEED_MIX = 0x43_4F_4F_4B_49_45

# The engagement stratification: octiles of pooled sum_gamerounds → 8 strata.
N_ENGAGEMENT_STRATA = 8


@dataclass(frozen=True)
class GateUplift:
    """Overall difference-in-means uplift of gate_40 vs gate_30.

    `observed_lift = treatment_rate − control_rate` (raw probability delta, the
    same unit as `GroundTruth.observed_lift`). `ci` is a percentile-bootstrap
    interval on that delta; `n_control` / `n_treatment` size the estimate so a
    downstream power check is explicit.
    """

    metric_name: str
    control_rate: float
    treatment_rate: float
    observed_lift: float
    ci: tuple[float, float]
    n_control: int
    n_treatment: int


@dataclass(frozen=True)
class SegmentUplift:
    """Per-engagement-segment uplift of gate_40 vs gate_30 within a stratum.

    The heterogeneity material: does the gate move help/hurt THIS engagement band
    more than another? Same fields as `GateUplift`, plus the `segment` key naming
    the stratum (e.g. `eng_o1`..`eng_o8`).
    """

    segment: str
    metric_name: str
    control_rate: float
    treatment_rate: float
    observed_lift: float
    ci: tuple[float, float]
    n_control: int
    n_treatment: int


def _outcome(row: CookieCatsRow, metric_name: str) -> int:
    """The binary outcome value for `metric_name` (the two scorable metrics)."""
    if metric_name == RETENTION_7:
        return row.retention_7
    if metric_name == RETENTION_1:
        return row.retention_1
    raise ValueError(
        f"unsupported Cookie Cats metric_name {metric_name!r}; v1 scores "
        f"{sorted(SCORABLE_METRICS)} only"
    )


def _rate(values: Sequence[int]) -> float:
    """Mean of a 0/1 sequence (the arm's retention rate). 0.0 on an empty arm."""
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
    rather than raising. Mirrors `hillstrom_adapter._bootstrap_lift_ci`.
    """
    if not control or not treatment:
        point = _rate(treatment) - _rate(control)
        return (point, point)
    rng = random.Random(seed ^ _UPLIFT_SEED_MIX)
    n_c = len(control)
    n_t = len(treatment)

    def _delta(_ignored: Sequence[int]) -> float:
        c = rng.choices(control, k=n_c)
        t = rng.choices(treatment, k=n_t)
        return _rate(t) - _rate(c)

    return bootstrap_percentile_ci(
        list(control),
        _delta,
        n_resamples=n_resamples,
        rng=rng,
    )


def compute_gate_uplift(
    rows: Sequence[CookieCatsRow],
    *,
    metric_name: str = RETENTION_7,
    seed: int = 0,
    n_resamples: int = _BOOTSTRAP_RESAMPLES,
) -> GateUplift:
    """Overall difference-in-means uplift of gate_40 vs gate_30.

    The control rate is the gate_30 retention rate over ALL rows; the treatment
    rate is gate_40's. Because assignment was randomized this difference is an
    unbiased ATE estimate. Raises ValueError on an unknown metric.
    """
    control = [_outcome(r, metric_name) for r in rows if r.version == CONTROL_VERSION]
    treatment = [_outcome(r, metric_name) for r in rows if r.version == TREATMENT_VERSION]
    control_rate = _rate(control)
    treatment_rate = _rate(treatment)
    lift = treatment_rate - control_rate
    ci = _bootstrap_lift_ci(control, treatment, seed=seed, n_resamples=n_resamples)
    return GateUplift(
        metric_name=metric_name,
        control_rate=control_rate,
        treatment_rate=treatment_rate,
        observed_lift=lift,
        ci=ci,
        n_control=len(control),
        n_treatment=len(treatment),
    )


def engagement_octile_edges(
    rows: Sequence[CookieCatsRow],
    *,
    n_strata: int = N_ENGAGEMENT_STRATA,
) -> list[float]:
    """The interior octile boundaries of pooled (both-arm) `sum_gamerounds`.

    Reads the engagement quantile cut points off the POOLED distribution (both
    arms together) so the stratification is RANDOMIZATION-PRESERVING: each stratum
    still contains a random mix of gate_30/gate_40 players, so the within-stratum
    difference stays an unbiased ATE for that engagement band. Returns `n_strata-1`
    ascending interior edges; an empty input yields no edges.

    STRUCTURALLY BLIND: keyed only on `sum_gamerounds` (a pre-retention engagement
    feature) — never on `version` (the arm) or any retention outcome.
    """
    if n_strata < 2:
        raise ValueError("n_strata must be at least 2 to form interior edges")
    vals = sorted(r.sum_gamerounds for r in rows)
    if not vals:
        return []
    edges: list[float] = []
    n = len(vals)
    for i in range(1, n_strata):
        # Linear-interpolation quantile at fraction i/n_strata.
        pos = (i / n_strata) * (n - 1)
        lo = int(pos)
        hi = min(lo + 1, n - 1)
        frac = pos - lo
        edges.append(vals[lo] + (vals[hi] - vals[lo]) * frac)
    return edges


def _segment_key(value: int, edges: Sequence[float]) -> str:
    """The engagement-octile stratum key for a `sum_gamerounds` value.

    `edges` are the interior octile boundaries from `engagement_octile_edges`.
    A value at or below the first edge is `eng_o1`; above the last edge is
    `eng_o{n}`. Stable, freezable keys so the pre-registration hash can pin them.
    """
    idx = 0
    for e in edges:
        if value <= e:
            break
        idx += 1
    return f"eng_o{idx + 1}"


def compute_segment_uplift(
    rows: Sequence[CookieCatsRow],
    *,
    metric_name: str = RETENTION_7,
    seed: int = 0,
    n_resamples: int = _BOOTSTRAP_RESAMPLES,
    n_strata: int = N_ENGAGEMENT_STRATA,
) -> list[SegmentUplift]:
    """Per-engagement-segment uplift of gate_40 vs gate_30 across the strata.

    Within each engagement octile, the gate_40 retention rate minus the gate_30
    rate IN THAT SAME stratum (so the control is matched on engagement). Strata
    are emitted in stable sorted order so the pre-registration hash is
    reproducible. A stratum with no control or no treatment rows is still emitted
    (with a degenerate CI) rather than dropped, so coverage stays honest. Raises
    ValueError on an unknown metric or empty rows.
    """
    if not rows:
        raise ValueError("compute_segment_uplift requires at least one row")
    edges = engagement_octile_edges(rows, n_strata=n_strata)
    control_by_seg: dict[str, list[int]] = defaultdict(list)
    treatment_by_seg: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        key = _segment_key(r.sum_gamerounds, edges)
        if r.version == CONTROL_VERSION:
            control_by_seg[key].append(_outcome(r, metric_name))
        elif r.version == TREATMENT_VERSION:
            treatment_by_seg[key].append(_outcome(r, metric_name))

    out: list[SegmentUplift] = []
    keys = sorted(
        set(control_by_seg) | set(treatment_by_seg),
        key=lambda k: int(k.split("_o")[1]),
    )
    for i, key in enumerate(keys):
        control = control_by_seg.get(key, [])
        treatment = treatment_by_seg.get(key, [])
        control_rate = _rate(control)
        treatment_rate = _rate(treatment)
        lift = treatment_rate - control_rate
        ci = _bootstrap_lift_ci(control, treatment, seed=seed + i + 1, n_resamples=n_resamples)
        out.append(
            SegmentUplift(
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


def _gate_figma(gate_level: int) -> ReverseFigma:
    """The level-progress screen for one arm.

    Both arms show the SAME progress screen; the single CHANGED delta is the gate
    LEVEL value on the progress-gate component (30 in control, 40 in treatment).
    No new screen is added — only the gate position moves, exactly the production
    copy/value-state-diff path.
    """
    body = (
        f"As you progress through levels, the first forced wait gate appears at "
        f"level {gate_level}. Until then you can keep playing without interruption; "
        f"at level {gate_level} you must wait (or pay) to continue."
    )
    return ReverseFigma(
        screens=[
            Screen(
                id=GAME_SCREEN_ID,
                name="Level progress",
                components=[
                    Component(id=GATE_COMPONENT_ID, role="body", text=body),
                ],
            )
        ],
        transitions=[],
    )


def _gate_capability_hypothesis() -> tuple[Capability, Hypothesis]:
    """The shared `(Capability, Hypothesis)` gate-move delta pair.

    Control = the first progress gate at level 30 (current state); treatment = the
    SAME screen with the gate moved to level 40. Carries ONLY the gate-level delta,
    never any retention outcome / ground-truth signal. Reused by the population and
    per-segment case builders so both score the IDENTICAL rendered change — the
    per-segment cases differ only in their ground truth + case_id.
    """
    reverse_prd = (
        "A new player is progressing through the early levels of the mobile game. "
        "In the current experience, the first forced progress gate — a wait/pay "
        "wall that interrupts play — sits at level 30."
    )
    capability = Capability(
        name="early-game progress gate",
        surfaces=["mobile_game"],
        roles=["player"],
        entry_points=["level_progress"],
        reverse_prd=reverse_prd,
        reverse_figma=_gate_figma(gate_level=30),
        implicit_metric="whether the player keeps returning to the game after install",
    )
    hypothesis = Hypothesis(
        capability_name=capability.name,
        prose=(
            "Move the first forced progress gate later — from level 30 to level 40 "
            "— so players get more uninterrupted early play before hitting the first "
            "wait wall. Nothing else about the game changes."
        ),
        proposed_prd=None,
        proposed_figma=_gate_figma(gate_level=40),
    )
    return capability, hypothesis


def build_cookiecats_case(
    rows: Sequence[CookieCatsRow],
    *,
    metric_name: str = RETENTION_7,
    seed: int = 0,
    n_resamples: int = _BOOTSTRAP_RESAMPLES,
) -> BenchmarkCase:
    """Build ONE benchmark case for the whole-population gate_40-vs-gate_30 A/B.

    The case is the SAME `(Capability, Hypothesis)` shape production builds:
    control = gate at level 30; treatment = gate at level 40 as a value delta.
    `GroundTruth` carries the trial's overall difference-in-means uplift point
    estimate for `metric_name`. Raises ValueError on an unknown metric / empty rows.
    """
    if not rows:
        raise ValueError("build_cookiecats_case requires at least one row")
    uplift = compute_gate_uplift(rows, metric_name=metric_name, seed=seed, n_resamples=n_resamples)
    capability, hypothesis = _gate_capability_hypothesis()
    ground_truth = GroundTruth(
        metric_name=metric_name,
        control_metric=uplift.control_rate,
        treatment_metric=uplift.treatment_rate,
        observed_lift=uplift.observed_lift,
        winner=_winner(uplift.observed_lift),
    )
    return BenchmarkCase(
        case_id=f"cookiecats:gate40_vs_gate30:{metric_name}",
        source=_SOURCE,
        capability=capability,
        hypothesis=hypothesis,
        ground_truth=ground_truth,
    )


def build_cookiecats_segment_case(seg: SegmentUplift) -> BenchmarkCase:
    """Build one per-SEGMENT benchmark case from a `SegmentUplift`.

    The heterogeneity material: a case whose `GroundTruth` is the gate move's
    uplift WITHIN one engagement octile, so a run can be scored on whether the sim
    predicts the gate move's effect varies by engagement band.

    The stimulus (capability + hypothesis gate delta) is IDENTICAL to the
    population-level case — only the ground truth (per-stratum uplift) and the
    case_id (which carries the 4th `:<segment>` component the `by_segment` honesty
    stratifier reads) differ. The predictor stays blind: the stratum is encoded
    ONLY in the case_id/ground_truth, never in the rendered change.
    """
    capability, hypothesis = _gate_capability_hypothesis()
    ground_truth = GroundTruth(
        metric_name=seg.metric_name,
        control_metric=seg.control_rate,
        treatment_metric=seg.treatment_rate,
        observed_lift=seg.observed_lift,
        winner=_winner(seg.observed_lift),
    )
    return BenchmarkCase(
        case_id=f"cookiecats:gate40_vs_gate30:{seg.metric_name}:{seg.segment}",
        source=_SOURCE,
        capability=capability,
        hypothesis=hypothesis,
        ground_truth=ground_truth,
    )


def cookiecats_segment_cases(
    rows: Sequence[CookieCatsRow],
    *,
    metric_name: str = RETENTION_7,
    seed: int = 0,
    n_resamples: int = _BOOTSTRAP_RESAMPLES,
    n_strata: int = N_ENGAGEMENT_STRATA,
) -> list[BenchmarkCase]:
    """Enumerate per-engagement-segment cases (≥8, clearing the null-cert floor).

    For each engagement octile (`eng_o1`..`eng_o8`), one case whose ground truth
    is the gate move's uplift within that stratum. These carry the 4-component
    case_id the `benchmark_honesty.by_segment` stratifier reads, so directional
    accuracy can be reported per engagement stratum. Raises ValueError if `rows`
    is empty.

    VALIDITY REQUIREMENT. The cases differ ONLY in ground truth + case_id — their
    stimulus is deliberately IDENTICAL, and the predictor is blind to
    ground_truth/case_id. So a caller that scores these against ONE
    undifferentiated audience would have the engine emit the same prediction for
    every stratum (seed noise), measuring nothing. The runner MUST condition the
    simulated audience on the stratum — via
    `cookiecats_panel_loader.cookiecats_segment_subpack` — for the per-segment
    scores to reflect heterogeneous response. The `benchmark-cookiecats` CLI does
    exactly this (it runs each stratum against its sub-pack).
    """
    if not rows:
        raise ValueError("cookiecats_segment_cases requires at least one row")
    return [
        build_cookiecats_segment_case(seg)
        for seg in compute_segment_uplift(
            rows, metric_name=metric_name, seed=seed, n_resamples=n_resamples, n_strata=n_strata
        )
    ]


def cookiecats_rows_to_cases(
    rows: Sequence[CookieCatsRow],
    *,
    metric_name: str = RETENTION_7,
    seed: int = 0,
    n_resamples: int = _BOOTSTRAP_RESAMPLES,
) -> list[BenchmarkCase]:
    """The whole-population A/B as a single benchmark case (the arm-level path).

    Cookie Cats is one comparison, so the arm-level enumeration yields exactly one
    case: control = gate_30, treatment = gate_40, with the trial's measured uplift
    as ground truth. (Use `cookiecats_segment_cases` for the ≥8-case by-segment
    path that clears the null-integrity certificate floor.) Raises ValueError if
    `rows` is empty.
    """
    return [
        build_cookiecats_case(rows, metric_name=metric_name, seed=seed, n_resamples=n_resamples)
    ]
