"""Tests for the Upworthy archive→Hypothesis adapter (#222, agent-behavior-spec §1).

The load-bearing assertions are the *parity* ones: a benchmark case must flow
through the EXACT same path production uses, with no benchmark-only rendering.
Two legs:
- the shared renderer — the adapter's (capability, hypothesis) renders
  identically to a hand-built Hypothesis (`test_adapter_changelog_matches_
  handbuilt_hypothesis`), and
- the production composer — feeding a benchmark case to `compose_identity_prompt`
  (treatment arm) embeds that same rendered view byte-for-byte
  (`test_benchmark_case_flows_through_the_production_composer`).
If both pass, the Tier-0 benchmark is a real test of the production
treatment-rendering layer.
"""

from __future__ import annotations

import pytest

from sidira_simulator.schemas.benchmark import UpworthyTest, UpworthyVariant
from sidira_simulator.schemas.feature_pack import (
    Capability,
    Component,
    ReverseFigma,
    Screen,
    Transition,
)
from sidira_simulator.schemas.persona import Persona
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.benchmark_adapter import (
    ARTICLE_SCREEN_ID,
    CARD_SCREEN_ID,
    CLICK_TRIGGER,
    HEADLINE_COMPONENT_ID,
    build_upworthy_case,
    upworthy_test_to_cases,
)
from sidira_simulator.services.prompt_composer import compose_identity_prompt
from sidira_simulator.services.treatment_renderer import render_state_diff

CONTROL_HEADLINE = "He Thought It Was Just A Dog. What Happened Next Stunned Him."
TREATMENT_HEADLINE = "This Rescue Dog Did Something No One Expected"


def _test(
    *,
    control_clicks: int = 100,
    treatment_clicks: int = 150,
    impressions: int = 10_000,
    control_eyecatcher: str | None = "img_a",
    treatment_eyecatcher: str | None = "img_a",
) -> UpworthyTest:
    return UpworthyTest(
        test_id="t_abc",
        article_context="A rescue dog alerts its owner to a house fire.",
        variants=[
            UpworthyVariant(
                headline=CONTROL_HEADLINE,
                clicks=control_clicks,
                impressions=impressions,
                eyecatcher_id=control_eyecatcher,
            ),
            UpworthyVariant(
                headline=TREATMENT_HEADLINE,
                clicks=treatment_clicks,
                impressions=impressions,
                eyecatcher_id=treatment_eyecatcher,
            ),
        ],
    )


# ── source schema ──────────────────────────────────────────────────────────


def test_variant_ctr_is_clicks_over_impressions():
    v = UpworthyVariant(headline="x", clicks=250, impressions=10_000, eyecatcher_id=None)
    assert v.ctr == pytest.approx(0.025)


def test_variant_rejects_zero_impressions():
    with pytest.raises(ValueError):
        UpworthyVariant(headline="x", clicks=0, impressions=0, eyecatcher_id=None)


def test_variant_rejects_clicks_exceeding_impressions():
    # ctr > 1 is impossible — a malformed archive row must not reach a label.
    with pytest.raises(ValueError, match="exceed impressions"):
        UpworthyVariant(headline="x", clicks=10_001, impressions=10_000, eyecatcher_id=None)


def test_variant_requires_explicit_eyecatcher_id():
    # No default: omitting the field is a validation error, so an importer that
    # "didn't record it" can never masquerade as a held-fixed image. The choice
    # (a real id, or the explicit None no-image sentinel) must be deliberate.
    with pytest.raises(ValueError, match="eyecatcher_id"):
        UpworthyVariant(headline="x", clicks=100, impressions=10_000)


# ── single-case shape: exactly one CHANGED/copy delta on the headline ────────


def test_headline_swap_renders_single_copy_delta():
    case = build_upworthy_case(_test(), 0, 1)
    rendered = render_state_diff(case.capability, case.hypothesis)

    assert len(rendered.changes) == 1
    change = rendered.changes[0]
    assert change.kind == "CHANGED"
    assert change.target_type == "component"
    assert change.target_id == HEADLINE_COMPONENT_ID
    assert change.screen_id == CARD_SCREEN_ID
    assert change.modality == "copy"
    # both headlines appear verbatim in the changelog detail
    assert CONTROL_HEADLINE in change.detail
    assert TREATMENT_HEADLINE in change.detail


def test_headline_swap_is_strong_copy_regime():
    case = build_upworthy_case(_test(), 0, 1)
    rendered = render_state_diff(case.capability, case.hypothesis)
    assert rendered.touched_modalities == ["copy"]
    assert rendered.reliability_regime == "strong"


def test_not_changing_names_the_unchanged_article_screen():
    case = build_upworthy_case(_test(), 0, 1)
    rendered = render_state_diff(case.capability, case.hypothesis)
    # The destination article is held fixed across arms → the renderer's
    # mandatory NOT-changing guard names it concretely (not just a catch-all).
    assert f"screen `{ARTICLE_SCREEN_ID}`" in rendered.not_changing


def test_click_transition_is_held_fixed_and_emits_no_change():
    case = build_upworthy_case(_test(), 0, 1)
    rendered = render_state_diff(case.capability, case.hypothesis)
    transition_changes = [c for c in rendered.changes if c.target_type == "transition"]
    assert transition_changes == []
    # but the transition exists in the proposed state (the §3a click event)
    assert case.hypothesis.proposed_figma is not None
    sigs = {t.trigger for t in case.hypothesis.proposed_figma.transitions}
    assert CLICK_TRIGGER in sigs


# ── blinding: standalone view shows only the proposed headline ───────────────


def test_standalone_view_is_blinded_to_the_control_headline():
    case = build_upworthy_case(_test(), 0, 1)
    rendered = render_state_diff(case.capability, case.hypothesis)
    standalone = rendered.standalone_state_view()
    assert standalone is not None
    assert TREATMENT_HEADLINE in standalone
    assert CONTROL_HEADLINE not in standalone  # no "what changed" framing leaks


def test_unblinded_view_carries_both_headlines_and_the_guard():
    case = build_upworthy_case(_test(), 0, 1)
    view = render_state_diff(case.capability, case.hypothesis).state_plus_diff_view()
    assert CONTROL_HEADLINE in view
    assert TREATMENT_HEADLINE in view
    assert "### Explicitly NOT changing" in view
    assert f"screen `{ARTICLE_SCREEN_ID}`" in view


# ── ground truth ─────────────────────────────────────────────────────────────


def test_ground_truth_lift_sign_matches_clicks():
    up = build_upworthy_case(_test(control_clicks=100, treatment_clicks=150), 0, 1)
    assert up.ground_truth.observed_lift > 0
    assert up.ground_truth.winner == "treatment"

    down = build_upworthy_case(_test(control_clicks=150, treatment_clicks=100), 0, 1)
    assert down.ground_truth.observed_lift < 0
    assert down.ground_truth.winner == "control"

    tie = build_upworthy_case(_test(control_clicks=100, treatment_clicks=100), 0, 1)
    assert tie.ground_truth.observed_lift == 0
    assert tie.ground_truth.winner == "tie"


# ── enumeration + the forcing-function skip ──────────────────────────────────


def test_enumerate_builds_baseline_vs_each_variant():
    test = _test()
    test.variants.append(
        UpworthyVariant(
            headline="A third option", clicks=120, impressions=10_000, eyecatcher_id="img_a"
        )
    )
    result = upworthy_test_to_cases(test)
    assert [c.case_id for c in result.cases] == ["t_abc:0v1", "t_abc:0v2"]
    assert result.skipped == []


def test_enumerate_rejects_out_of_range_baseline():
    test = _test()
    with pytest.raises(ValueError, match="out of range"):
        upworthy_test_to_cases(test, baseline_index=5)
    with pytest.raises(ValueError, match="out of range"):
        upworthy_test_to_cases(test, baseline_index=-1)


def test_build_case_rejects_out_of_range_index():
    # The public single-case builder validates its own indexes — a negative one
    # must not silently wrap into a `-1v0` case_id.
    test = _test()
    with pytest.raises(ValueError, match="out of range"):
        build_upworthy_case(test, -1, 0)
    with pytest.raises(ValueError, match="out of range"):
        build_upworthy_case(test, 0, 5)


def test_noop_headline_pair_is_rejected_and_skipped():
    # Same index → identical state → no delta to render; never score it.
    with pytest.raises(ValueError, match="no-op pair"):
        build_upworthy_case(_test(), 0, 0)

    # A duplicate headline package elsewhere in the test is recorded as skipped.
    test = _test()
    test.variants.append(
        UpworthyVariant(
            headline=CONTROL_HEADLINE, clicks=99, impressions=10_000, eyecatcher_id="img_a"
        )
    )
    result = upworthy_test_to_cases(test)
    assert [c.case_id for c in result.cases] == ["t_abc:0v1"]
    assert len(result.skipped) == 1
    assert result.skipped[0].treatment_index == 2
    assert "no-op" in result.skipped[0].reason


def test_image_swap_is_recorded_as_skipped_not_faked_as_copy():
    # A pair that also changes the eyecatcher image cannot be a copy state-diff.
    test = _test(control_eyecatcher="img_a", treatment_eyecatcher="img_b")

    with pytest.raises(ValueError, match="image"):
        build_upworthy_case(test, 0, 1)

    result = upworthy_test_to_cases(test)
    assert result.cases == []
    assert len(result.skipped) == 1
    assert result.skipped[0].control_index == 0
    assert result.skipped[0].treatment_index == 1


def test_no_image_sentinel_pair_is_a_held_fixed_headline_swap():
    # Both variants carry no image: None is the explicit "no distinguishing image"
    # sentinel, a defined held-fixed state — not "unknown". Such a pair is a valid
    # pure-copy swap (the card simply has no eyecatcher to hold fixed), so it
    # builds a case rather than being rejected as multi-factor.
    test = _test(control_eyecatcher=None, treatment_eyecatcher=None)
    case = build_upworthy_case(test, 0, 1)
    rendered = render_state_diff(case.capability, case.hypothesis)

    assert len(rendered.changes) == 1
    assert rendered.changes[0].modality == "copy"
    # no eyecatcher component is emitted when there is no image
    assert case.capability.reverse_figma is not None
    card = next(s for s in case.capability.reverse_figma.screens if s.id == CARD_SCREEN_ID)
    assert [c.id for c in card.components] == [HEADLINE_COMPONENT_ID]
    # …and the PRD prose stays consistent with that image-free state.
    assert "story image" not in case.capability.reverse_prd


def test_prd_mentions_the_image_only_when_the_card_has_one():
    with_image = build_upworthy_case(_test(), 0, 1)
    assert "above the story image" in with_image.capability.reverse_prd


# ── PARITY: the benchmark case renders identically to a hand-built Hypothesis ─


def _handbuilt_equivalent() -> tuple[Capability, Hypothesis]:
    """The same (Capability, Hypothesis) a human would author directly, without
    going through the adapter — used to prove the adapter adds no special-casing."""

    def figma(headline: str) -> ReverseFigma:
        return ReverseFigma(
            screens=[
                Screen(
                    id=CARD_SCREEN_ID,
                    name="Promoted story card",
                    components=[
                        Component(id=HEADLINE_COMPONENT_ID, role="headline", text=headline),
                        Component(id="eyecatcher", role="image", text=None),
                    ],
                ),
                Screen(id=ARTICLE_SCREEN_ID, name="Story article", components=[]),
            ],
            transitions=[
                Transition(
                    trigger=CLICK_TRIGGER,
                    from_screen=CARD_SCREEN_ID,
                    to_screen=ARTICLE_SCREEN_ID,
                )
            ],
        )

    capability = Capability(
        name="promoted story headline",
        surfaces=["feed"],
        roles=["reader"],
        entry_points=["feed"],
        reverse_prd="anything — the diff is structural, not prose-driven",
        reverse_figma=figma(CONTROL_HEADLINE),
        implicit_metric="click-through rate (reader clicks the story card)",
    )
    hypothesis = Hypothesis(
        capability_name=capability.name,
        prose="swap the headline",
        proposed_prd=None,
        proposed_figma=figma(TREATMENT_HEADLINE),
    )
    return capability, hypothesis


def test_adapter_changelog_matches_handbuilt_hypothesis():
    case = build_upworthy_case(_test(), 0, 1)
    hand_cap, hand_hyp = _handbuilt_equivalent()

    adapted = render_state_diff(case.capability, case.hypothesis)
    handbuilt = render_state_diff(hand_cap, hand_hyp)

    # Identical structural diff — same changelog lines, modalities, regime, and
    # NOT-changing guard. (Prose differs by construction, so compare the parts
    # the renderer derives structurally, not the free-text prose.)
    assert [c.line() for c in adapted.changes] == [c.line() for c in handbuilt.changes]
    assert adapted.not_changing == handbuilt.not_changing
    assert adapted.touched_modalities == handbuilt.touched_modalities
    assert adapted.reliability_regime == handbuilt.reliability_regime


# ── PARITY: a benchmark case flows through the production composer unchanged ──


def _reader_persona() -> Persona:
    return Persona(id="p1", name="Casual feed reader", description="Scrolls the feed on breaks.")


def test_benchmark_case_flows_through_the_production_composer():
    """The strongest parity claim: a benchmark case fed to the EXACT production
    composer (treatment arm) embeds the shared renderer's unblinded view — so the
    benchmark agent and a production agent read byte-identical change framing."""
    case = build_upworthy_case(_test(), 0, 1)

    prompt = compose_identity_prompt(
        customer_id="upworthy",
        persona=_reader_persona(),
        capability=case.capability,
        hypothesis=case.hypothesis,
        arm="treatment",
    )

    expected_view = render_state_diff(case.capability, case.hypothesis).state_plus_diff_view()
    assert expected_view in prompt
    assert TREATMENT_HEADLINE in prompt


def test_control_arm_does_not_leak_the_proposed_headline():
    case = build_upworthy_case(_test(), 0, 1)

    prompt = compose_identity_prompt(
        customer_id="upworthy",
        persona=_reader_persona(),
        capability=case.capability,
        hypothesis=case.hypothesis,
        arm="control",
    )
    # control reacts to today's product only — the proposed headline must not appear
    assert TREATMENT_HEADLINE not in prompt
    assert "## What's changing" not in prompt
