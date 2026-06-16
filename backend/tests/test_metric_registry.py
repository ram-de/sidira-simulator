"""Tests for the #275 metric registry — per-metric dispatch correctness.

The registry is the single dispatch seam replacing every inline
`if metric_name == "conversion"` branch. These tests pin:
- both metrics register with the fields the pipeline reads,
- an unknown metric fails LOUD (get_metric raises; the validator rejects it),
- required_template_fields drives the Hypothesis validator per metric,
- the descriptors wire the right aggregator / honesty / calibrator.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidira_simulator.schemas.scoring import MetricLiftResult
from sidira_simulator.schemas.simulation import (
    DEFAULT_CONVERSION_CHOICE_SET,
    Hypothesis,
)
from sidira_simulator.services.conversion_calibrator import IdentityCalibrator
from sidira_simulator.services.metric_registry import (
    get_metric,
    is_registered,
    required_template_fields,
)
from sidira_simulator.services.ctr_elicitor import DEFAULT_CTR_CHOICE_SET
from sidira_simulator.services.retention_elicitor import DEFAULT_RETENTION_CHOICE_SET


def test_all_metrics_registered() -> None:
    assert is_registered("conversion")
    assert is_registered("retention")
    assert is_registered("ctr")  # #276
    assert not is_registered("dwell_time")  # not yet registered
    assert not is_registered(None)


def test_get_metric_unknown_raises_loud() -> None:
    """A registered-but-unknown name (Literal/registry drift) must raise, never
    silently degrade to sentiment."""
    with pytest.raises(KeyError, match="unknown metric_name"):
        get_metric("dwell_time")


def test_hypothesis_rejects_unregistered_metric_at_construction() -> None:
    """The closed Literal is the first line of defense — an unknown metric never
    even reaches the registry."""
    with pytest.raises(ValidationError):
        Hypothesis(capability_name="x", prose="y", metric_name="dwell_time")


def test_required_template_fields_drive_validator() -> None:
    assert required_template_fields("conversion") == (
        "conversion_action",
        "conversion_action_label",
        "decision_point",
    )
    assert required_template_fields("retention") == ("decision_point",)
    assert required_template_fields("ctr") == ("decision_point",)


def test_required_template_fields_unknown_raises() -> None:
    with pytest.raises(KeyError):
        required_template_fields("dwell_time")


def test_conversion_descriptor_wiring() -> None:
    d = get_metric("conversion")
    assert d.name == "conversion"
    assert d.default_choice_set == DEFAULT_CONVERSION_CHOICE_SET
    assert d.paraphrase_count == 3
    # honesty hook speaks conversion's native unit
    _regime, relative = d.honesty(MetricLiftResult(lift_pp=5.0, paired_n=3))
    assert "converts directionally higher" in relative
    assert isinstance(d.calibrator_resolver(), IdentityCalibrator)


def test_retention_descriptor_wiring() -> None:
    d = get_metric("retention")
    assert d.name == "retention"
    assert d.default_choice_set == DEFAULT_RETENTION_CHOICE_SET
    assert d.paraphrase_count == 3
    _regime, relative = d.honesty(MetricLiftResult(lift_pp=5.0, paired_n=3))
    assert "retains directionally higher" in relative
    assert isinstance(d.calibrator_resolver(), IdentityCalibrator)


def test_ctr_descriptor_wiring() -> None:
    d = get_metric("ctr")
    assert d.name == "ctr"
    assert d.default_choice_set == DEFAULT_CTR_CHOICE_SET
    assert d.paraphrase_count == 3
    _regime, relative = d.honesty(MetricLiftResult(lift_pp=5.0, paired_n=3))
    assert "clicks through directionally higher" in relative
    assert isinstance(d.calibrator_resolver(), IdentityCalibrator)


def test_ctr_regime_is_strong_behavioral() -> None:
    """CTR sits in the §5 STRONG behavioral regime (rendered click correlates with
    the real outcome far better than the conversion/retention modality cliff), so
    its regime label differs from the weak-behavioral siblings."""
    d = get_metric("ctr")
    regime, _relative = d.honesty(MetricLiftResult(lift_pp=5.0, paired_n=3))
    assert regime == "strong_behavioral"
    # the weak-behavioral siblings keep their own label, unperturbed
    assert get_metric("conversion").honesty(MetricLiftResult())[0] == "weak_behavioral"
    assert get_metric("retention").honesty(MetricLiftResult())[0] == "weak_behavioral"


def test_conversion_target_terms_filters_action_and_label() -> None:
    d = get_metric("conversion")
    h = Hypothesis(
        capability_name="reorder",
        prose="x",
        metric_name="conversion",
        conversion_action="tap reorder and check out",
        conversion_action_label="check out now",
        decision_point="home",
    )
    terms = d.target_terms(h)
    assert "tap reorder and check out" in terms
    assert "check out now" in terms


def test_retention_target_terms_includes_default_return_label() -> None:
    d = get_metric("retention")
    h = Hypothesis(
        capability_name="feed",
        prose="x",
        metric_name="retention",
        decision_point="tonight",
    )
    terms = d.target_terms(h)
    assert "return next week" in terms


def test_ctr_target_terms_includes_default_click_label() -> None:
    d = get_metric("ctr")
    h = Hypothesis(
        capability_name="feed",
        prose="x",
        metric_name="ctr",
        decision_point="the banner is on your home feed",
    )
    terms = d.target_terms(h)
    assert "click it" in terms


def test_ctr_is_target_like_alternative_catches_click_phrasings() -> None:
    """Arbitrary grounded/PM-supplied click phrasings are detected as target-like
    (and so dropped from the alternatives), not just the exact target_terms — so a
    rendered click transition never survives as an uncounted click twin that would
    split p_metric (codex P2). The predicate is a no-op for the weak-behavioral
    siblings, so their filtering is unperturbed."""
    d = get_metric("ctr")
    for click_like in (
        "click the headline",
        "tap to open",
        "click_headline",  # token-format trigger (separators normalized)
        "Tap The Banner",
        "press play",
        "open the article",
        "select it",
    ):
        assert d.is_target_like_alternative(click_like.strip().lower()), click_like
    # genuine non-click alternatives are NOT target-like → they survive
    for non_click in ("browse the full menu", "keep scrolling", "leave", "compare prices"):
        assert not d.is_target_like_alternative(non_click)
    # word-boundary matched: a verb embedded in another word never trips it
    assert not d.is_target_like_alternative("uptick in interest")
    # the weak-behavioral siblings keep the default no-op predicate (unperturbed)
    assert get_metric("conversion").is_target_like_alternative("click the headline") is False
    assert get_metric("retention").is_target_like_alternative("tap to open") is False


def test_ctr_target_terms_includes_pm_supplied_label() -> None:
    d = get_metric("ctr")
    h = Hypothesis(
        capability_name="feed",
        prose="x",
        metric_name="ctr",
        conversion_action_label="tap the banner",
        decision_point="the banner is on your home feed",
    )
    terms = d.target_terms(h)
    assert "tap the banner" in terms
    # the registry default is still filtered too, so a grounded alternative equal
    # to the canonical click label never becomes a second click-like option.
    assert "click it" in terms
