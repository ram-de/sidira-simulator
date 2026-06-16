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
    REASON_OUT_OF_SCOPE_LONG_HORIZON,
    REASON_OUT_OF_SCOPE_NETWORK_EFFECT,
    REASON_OUT_OF_SCOPE_NOVELTY_DECAY,
    REASON_STRUCTURALLY_INVISIBLE,
    _detect_out_of_scope,
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


# ── T2 (#311): out_of_scope instrument-fit detector ─────────────────────────


def test_long_horizon_revenue_is_out_of_scope() -> None:
    # Declare an OEC so the structural/OEC checks pass and only T2 can fire.
    v = assess_answerability(
        _hyp(prose="Will this lift 90-day revenue per cohort?"),
        allow_generic_reception=True,
    )
    assert v.state == "out_of_scope"
    assert REASON_OUT_OF_SCOPE_LONG_HORIZON in v.reason_codes
    assert v.reasons  # carries a named reason
    # Abstention is NOT a fixable block: no fixes, no override (the run proceeds).
    assert v.fixes == []
    assert v.allow_override is False


def test_lifetime_value_phrase_is_out_of_scope() -> None:
    codes, reasons = _detect_out_of_scope(
        _hyp(prose="Does the new onboarding improve customer lifetime value?")
    )
    assert REASON_OUT_OF_SCOPE_LONG_HORIZON in codes
    assert reasons


def test_network_effect_is_out_of_scope() -> None:
    v = assess_answerability(
        _hyp(prose="Will referral loops drive virality across the user base?"),
        allow_generic_reception=True,
    )
    assert v.state == "out_of_scope"
    assert REASON_OUT_OF_SCOPE_NETWORK_EFFECT in v.reason_codes


def test_marketplace_equilibrium_is_out_of_scope() -> None:
    codes, _ = _detect_out_of_scope(
        _hyp(prose="Does this cause cannibalization across the marketplace equilibrium?")
    )
    assert REASON_OUT_OF_SCOPE_NETWORK_EFFECT in codes


def test_novelty_decay_is_out_of_scope() -> None:
    v = assess_answerability(
        _hyp(prose="Once the novelty wears off, does engagement hold?"),
        allow_generic_reception=True,
    )
    assert v.state == "out_of_scope"
    assert REASON_OUT_OF_SCOPE_NOVELTY_DECAY in v.reason_codes


def test_multiple_out_of_scope_classes_aggregate() -> None:
    codes, reasons = _detect_out_of_scope(
        _hyp(prose="Does virality lift lifetime value once the novelty wears off?")
    )
    assert REASON_OUT_OF_SCOPE_LONG_HORIZON in codes
    assert REASON_OUT_OF_SCOPE_NETWORK_EFFECT in codes
    assert REASON_OUT_OF_SCOPE_NOVELTY_DECAY in codes
    assert len(reasons) == len(codes) == 3


def test_metric_bundle_decision_point_is_scanned_for_scope() -> None:
    # The detector scans the metric-bundle structured fields, not just prose:
    # a 90-day decision_point is as out-of-scope as the prose.
    codes, _ = _detect_out_of_scope(
        _hyp(
            prose="Tap the new button.",
            metric_name="retention",
            decision_point="it has been 90-day retention since you signed up",
        )
    )
    assert REASON_OUT_OF_SCOPE_LONG_HORIZON in codes


def test_numeric_horizon_without_hyphen_is_out_of_scope() -> None:
    # codex P2 (#311): spacing/hyphenation must not be a false-negative escape
    # hatch. "90 day retention" is as long-horizon as "90-day retention".
    for prose in (
        "Will this improve 90 day retention?",
        "Does it lift 30day revenue?",
        "Impact on 2 week retention?",
    ):
        codes, _ = _detect_out_of_scope(_hyp(prose=prose))
        assert REASON_OUT_OF_SCOPE_LONG_HORIZON in codes, prose


def test_revenue_in_product_label_does_not_false_abstain() -> None:
    # codex P2 (#311): a product-area label containing an outcome word (a
    # "Revenue dashboard" capability, a "churn" action) measured by an in-scope
    # metric must NOT abstain. Bare single-token signals apply to outcome text
    # (prose / decision_point), not to product/action labels.
    codes, _ = _detect_out_of_scope(
        _hyp(
            prose="Does the redesigned card increase click-through?",
            capability_name="Revenue dashboard",
            conversion_action="viral_share",
            conversion_action_label="share to feed",
            metric_name="conversion",
            decision_point="you've opened the dashboard",
        )
    )
    assert codes == []


def test_bare_revenue_in_prose_defers_to_declared_immediate_metric() -> None:
    # codex P2 (#311 R4): PM prose often repeats the product-area name ("the
    # Revenue dashboard"). When an explicitly-immediate OEC is declared
    # (conversion / ctr), a BARE long-horizon/network token in prose yields to
    # it — the panel CAN answer the first-session click/conversion question.
    for metric in ("conversion", "ctr"):
        kw = dict(
            prose="Does the new layout improve the Revenue dashboard's clicks?",
            metric_name=metric,
            decision_point="you've landed on the dashboard",
        )
        # conversion needs the extra action bundle to construct a valid Hypothesis.
        if metric == "conversion":
            kw.update(
                conversion_action="open_report",
                conversion_action_label="open the report",
            )
        codes, _ = _detect_out_of_scope(_hyp(**kw))
        assert codes == [], metric


def test_explicit_horizon_phrase_overrides_declared_immediate_metric() -> None:
    # The deferral is ONLY for bare tokens. An explicit horizon phrase
    # ("90-day revenue", "lifetime value") states the OEC outright and abstains
    # even when an immediate metric is declared — the prose contradicts it.
    codes, _ = _detect_out_of_scope(
        _hyp(
            prose="Will the new layout lift 90-day revenue?",
            metric_name="ctr",
            decision_point="you've landed on the page",
        )
    )
    assert REASON_OUT_OF_SCOPE_LONG_HORIZON in codes


def test_in_scope_hypothesis_stays_answerable() -> None:
    # A normal first-exposure question naming a metric must NOT abstain — over-
    # triggering (false abstention) is the costlier error (module docstring).
    v = assess_answerability(
        _hyp(
            prose="Does a friendlier welcome message improve checkout completion?",
            metric_name="conversion",
            conversion_action="checkout",
            conversion_action_label="complete checkout",
            decision_point="you've added 2 items to your cart",
        )
    )
    assert v.state == "answerable"
    assert v.reason_codes == []


def test_single_session_retention_metric_is_not_out_of_scope() -> None:
    # Declaring `retention` as a metric is NOT auto-out-of-scope (the elicitor
    # measures a session-end return-intent proxy). Only a multi-week/lifetime
    # HORIZON in the prose abstains.
    codes, _ = _detect_out_of_scope(
        _hyp(
            prose="Does the end-of-session summary make people want to come back?",
            metric_name="retention",
            decision_point="you've just finished tonight's session",
        )
    )
    assert codes == []


def test_in_scope_prose_mentioning_time_does_not_over_trigger() -> None:
    # Mentioning "time" or "engagement" is not by itself out of scope.
    for prose in (
        "Does the new layout reduce time-to-first-action?",
        "Will users engage more with the redesigned card?",
        "Reword the welcome banner to be friendlier.",
    ):
        codes, _ = _detect_out_of_scope(_hyp(prose=prose))
        assert codes == [], prose


def test_needs_input_takes_precedence_over_out_of_scope() -> None:
    # A structurally-invisible change that ALSO mentions a long-horizon OEC must
    # still block as needs_input (fix the run before abstaining on it).
    v = assess_answerability(
        _hyp(prose="Move the reorder button to lift 90-day revenue."),
        allow_generic_reception=True,
    )
    assert v.state == "needs_input"
    assert REASON_STRUCTURALLY_INVISIBLE in v.reason_codes
