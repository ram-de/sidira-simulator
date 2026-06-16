"""Unit tests for the deterministic pre-flight answerability gate (#310 / T1).

Pure-function tests of `services.answerability.assess_answerability` — no LLM,
no I/O, no TestClient. The API-level wiring (422 payload, override resubmit,
happy path) is covered in test_simulations_api.py.
"""

from __future__ import annotations

from sidira_simulator.schemas.feature_pack import ReverseFigma
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.answerability import (
    REASON_OEC_UNDECLARED,
    REASON_STRUCTURALLY_INVISIBLE,
    assess_answerability,
)


def _hyp(**kw) -> Hypothesis:
    base = dict(capability_name="reorder", prose="Make the experience better.")
    base.update(kw)
    return Hypothesis(**base)


def _figma() -> ReverseFigma:
    """A minimal valid ReverseFigma so proposed_figma is non-None."""
    return ReverseFigma(screens=[], transitions=[])


# ── Check 1: structurally-invisible change ──────────────────────────────────


def test_ui_structure_prose_without_figma_is_needs_input() -> None:
    v = assess_answerability(
        _hyp(prose="Move the reorder button to the top of the home screen."),
        # Declare an OEC so ONLY the structural check can fire.
        allow_generic_reception=True,
    )
    assert v.state == "needs_input"
    assert REASON_STRUCTURALLY_INVISIBLE in v.reason_codes
    assert v.fixes  # carries a concrete fix
    # Structural-invisibility is never overridable.
    assert v.allow_override is False


def test_action_plus_ui_noun_prose_without_figma_is_needs_input() -> None:
    v = assess_answerability(
        _hyp(prose="Add a one-tap reorder button to the cart."),
        allow_generic_reception=True,
    )
    assert v.state == "needs_input"
    assert REASON_STRUCTURALLY_INVISIBLE in v.reason_codes


def test_ui_structure_prose_WITH_figma_is_answerable() -> None:
    v = assess_answerability(
        _hyp(
            prose="Move the reorder button to the top of the home screen.",
            proposed_figma=_figma(),
        ),
        allow_generic_reception=True,
    )
    assert v.state == "answerable"
    assert v.reason_codes == []


def test_non_structural_prose_without_figma_is_answerable() -> None:
    # Pure copy/positioning-free prose should NOT trip the structural check.
    v = assess_answerability(
        _hyp(prose="Reword the welcome message to sound friendlier."),
        allow_generic_reception=True,
    )
    assert v.state == "answerable"


def test_copy_edit_naming_a_ui_element_is_answerable() -> None:
    # codex P2 (#310): merely NAMING a UI noun (button, banner) in a copy edit
    # is not a structural change and must NOT hard-block. Only an action verb
    # paired with the noun (or an unconditional layout term) is structural.
    for prose in (
        "Reword the checkout button label to be more action-oriented.",
        "Change the banner headline copy.",
        "Update the menu item text.",
    ):
        v = assess_answerability(_hyp(prose=prose), allow_generic_reception=True)
        assert v.state == "answerable", prose


# ── Check 2: OEC undeclared ─────────────────────────────────────────────────


def test_metric_name_none_is_needs_input_with_override_available() -> None:
    # Non-structural prose + no metric → only the OEC check fires, override on.
    v = assess_answerability(_hyp(prose="Reword the welcome message."))
    assert v.state == "needs_input"
    assert REASON_OEC_UNDECLARED in v.reason_codes
    assert v.allow_override is True


def test_metric_name_none_with_override_proceeds() -> None:
    v = assess_answerability(
        _hyp(prose="Reword the welcome message."),
        allow_generic_reception=True,
    )
    assert v.state == "answerable"


def test_metric_declared_is_answerable() -> None:
    v = assess_answerability(
        _hyp(
            prose="Reword the welcome message.",
            metric_name="conversion",
            conversion_action="checkout",
            conversion_action_label="complete checkout",
            decision_point="you've added 2 items to your cart",
        )
    )
    assert v.state == "answerable"


# ── Both defects together ───────────────────────────────────────────────────


def test_both_defects_aggregate_and_override_not_advertised() -> None:
    # Structural prose + no figma + no metric: BOTH fire. The OEC override must
    # NOT be advertised because the un-overridable structural defect remains.
    v = assess_answerability(_hyp(prose="Move the reorder button to the top."))
    assert v.state == "needs_input"
    assert REASON_STRUCTURALLY_INVISIBLE in v.reason_codes
    assert REASON_OEC_UNDECLARED in v.reason_codes
    assert v.allow_override is False
    assert len(v.reasons) == 2 and len(v.fixes) == 2


def test_empty_prose_does_not_trip_structural_check() -> None:
    # Empty prose can't be a structural change; only the OEC check may fire.
    v = assess_answerability(_hyp(prose=""))
    assert REASON_STRUCTURALLY_INVISIBLE not in v.reason_codes
