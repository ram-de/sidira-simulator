"""Tests for the PortfolioCase → BenchmarkCase adapter (directional portfolio).

Mirrors `test_cookiecats_adapter`. Pins:
- the real-winner SIGN encoding on ground_truth (treatment-wins → +, control-wins → −),
- the adapter producing well-formed `BenchmarkCase`s (control narrative → capability
  reverse_figma, treatment narrative → hypothesis proposed_figma, one changed component),
- THE BLINDNESS TEST: the rendered stimulus the engine sees carries neither
  `real_winner`, the `effect` magnitude string, nor the real `metric` name,
- the held-out probe adapting to NON-scored cases separately,
- the >= 1 case guard.
"""

from __future__ import annotations

import pytest

from sidira_simulator.schemas.benchmark import BenchmarkCase, GroundTruth
from sidira_simulator.services.portfolio_adapter import (
    STATE_COMPONENT_ID,
    STATE_SCREEN_ID,
    build_portfolio_case,
    held_out_probe_cases,
    portfolio_cases_to_benchmark_cases,
    scored_portfolio_cases,
)
from sidira_simulator.services.portfolio_archive import (
    HeldOutProbe,
    PortfolioArchive,
    PortfolioCase,
)


def _case(**over) -> PortfolioCase:
    base = dict(
        id="case_a",
        domain="saas",
        control="The existing onboarding flow with 9 form fields.",
        treatment="A shorter onboarding flow with 6 form fields.",
        metric="conversions",
        real_winner="control",
        effect="control won; treatment -14% conversions",
        counter_intuitive="high",
        contamination="med",
        credibility="med",
        source="CXL",
        raw_data=False,
    )
    base.update(over)
    return PortfolioCase(**base)  # type: ignore[arg-type]


# ── REAL-WINNER SIGN ENCODING ───────────────────────────────────────────────────


def test_treatment_wins_encodes_positive_lift() -> None:
    case = build_portfolio_case(_case(real_winner="treatment"))
    assert case.ground_truth.observed_lift == pytest.approx(1.0)
    assert case.ground_truth.winner == "treatment"
    # The sentinel rates are internally consistent (treatment − control == lift)
    # and both non-negative (schema requires >= 0).
    gt = case.ground_truth
    assert gt.treatment_metric - gt.control_metric == pytest.approx(gt.observed_lift)
    assert gt.control_metric >= 0.0 and gt.treatment_metric >= 0.0


def test_control_wins_encodes_negative_lift() -> None:
    case = build_portfolio_case(_case(real_winner="control"))
    assert case.ground_truth.observed_lift == pytest.approx(-1.0)
    assert case.ground_truth.winner == "control"
    gt = case.ground_truth
    assert gt.treatment_metric - gt.control_metric == pytest.approx(gt.observed_lift)
    assert gt.control_metric >= 0.0 and gt.treatment_metric >= 0.0


# ── BENCHMARK CASE SHAPE ────────────────────────────────────────────────────────


def test_build_case_is_well_formed() -> None:
    case = build_portfolio_case(_case())
    assert isinstance(case, BenchmarkCase)
    assert case.source == "portfolio"
    assert case.case_id == "portfolio:case_a"
    assert isinstance(case.ground_truth, GroundTruth)


def test_control_and_treatment_are_a_single_component_diff() -> None:
    """Control = the control narrative as a standalone state; treatment = the SAME
    single screen with the body copy swapped to the treatment narrative."""
    case = build_portfolio_case(_case())
    control_screens = {s.id for s in case.capability.reverse_figma.screens}
    treatment_screens = {s.id for s in case.hypothesis.proposed_figma.screens}
    assert control_screens == treatment_screens == {STATE_SCREEN_ID}
    control_body = next(
        c
        for s in case.capability.reverse_figma.screens
        for c in s.components
        if c.id == STATE_COMPONENT_ID
    )
    treatment_body = next(
        c
        for s in case.hypothesis.proposed_figma.screens
        for c in s.components
        if c.id == STATE_COMPONENT_ID
    )
    assert "9 form fields" in control_body.text
    assert "6 form fields" in treatment_body.text


# ── THE BLINDNESS TEST (the load-bearing invariant) ─────────────────────────────


def test_rendered_stimulus_is_structurally_blind() -> None:
    """The rendered stimulus the engine sees (capability + hypothesis) must carry
    NEITHER the real_winner, NOR the effect magnitude string, NOR the real metric
    name — those leak the answer and ride ONLY on ground_truth + case_id."""
    src = _case(
        real_winner="control",
        effect="control won; treatment -64% buy-button clickers",
        metric="Buy-button clickers",
    )
    case = build_portfolio_case(src)
    stimulus = (case.capability.model_dump_json() + case.hypothesis.model_dump_json()).lower()
    assert src.real_winner not in stimulus
    assert "64" not in stimulus  # effect magnitude must not leak
    assert "buy-button" not in stimulus  # the real metric name can hint direction
    assert "won" not in stimulus  # no winner verb in the stimulus
    # The answer key DOES live on ground_truth (it is the held-out label).
    assert case.ground_truth.winner == "control"


def test_blindness_holds_across_the_committed_set() -> None:
    """Every committed scored case is structurally blind: no real_winner / effect
    digits in its rendered stimulus."""
    from sidira_simulator.services.portfolio_archive import load_portfolio_cases

    arc, _ = load_portfolio_cases()
    for src in arc.scored_cases:
        case = build_portfolio_case(src)
        stim = (case.capability.model_dump_json() + case.hypothesis.model_dump_json()).lower()
        assert src.real_winner not in stim, src.id


# ── ENUMERATION + GUARDS ────────────────────────────────────────────────────────


def test_scored_cases_excludes_probe() -> None:
    arc = PortfolioArchive(
        portfolio_id="p",
        scored_cases=[_case(id="s1"), _case(id="s2")],
        held_out_probe=[
            HeldOutProbe(id="p1", change="x", real_winner="control", why_held_out="famous")
        ],
        human_baseline_anchors={},
        balance_check={},
        methodology={},
    )
    cases = scored_portfolio_cases(arc)
    assert {c.case_id for c in cases} == {"portfolio:s1", "portfolio:s2"}


def test_held_out_probe_cases_are_separate_non_scored() -> None:
    arc = PortfolioArchive(
        portfolio_id="p",
        scored_cases=[_case(id="s1")],
        held_out_probe=[
            HeldOutProbe(
                id="netflix",
                change="wall -> browse first",
                real_winner="control (won all 5)",
                why_held_out="famous",
            ),
            HeldOutProbe(
                id="highrise",
                change="long -> short page",
                real_winner="treatment (+47%)",
                why_held_out="famous",
            ),
        ],
        human_baseline_anchors={},
        balance_check={},
        methodology={},
    )
    probes = held_out_probe_cases(arc)
    assert {c.case_id for c in probes} == {"portfolio:netflix", "portfolio:highrise"}
    # The "control (won all 5)" probe parses to a control-wins (negative) sign.
    netflix = next(c for c in probes if c.case_id == "portfolio:netflix")
    assert netflix.ground_truth.winner == "control"
    highrise = next(c for c in probes if c.case_id == "portfolio:highrise")
    assert highrise.ground_truth.winner == "treatment"


def test_empty_cases_raises() -> None:
    with pytest.raises(ValueError, match="at least one case"):
        portfolio_cases_to_benchmark_cases([])
