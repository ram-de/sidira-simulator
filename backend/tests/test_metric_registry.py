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
from sidira_simulator.services.retention_elicitor import DEFAULT_RETENTION_CHOICE_SET


def test_both_metrics_registered() -> None:
    assert is_registered("conversion")
    assert is_registered("retention")
    assert not is_registered("ctr")  # #276-next, not yet registered
    assert not is_registered(None)


def test_get_metric_unknown_raises_loud() -> None:
    """A registered-but-unknown name (Literal/registry drift) must raise, never
    silently degrade to sentiment."""
    with pytest.raises(KeyError, match="unknown metric_name"):
        get_metric("ctr")


def test_hypothesis_rejects_unregistered_metric_at_construction() -> None:
    """The closed Literal is the first line of defense — an unknown metric never
    even reaches the registry."""
    with pytest.raises(ValidationError):
        Hypothesis(capability_name="x", prose="y", metric_name="ctr")


def test_required_template_fields_drive_validator() -> None:
    assert required_template_fields("conversion") == (
        "conversion_action",
        "conversion_action_label",
        "decision_point",
    )
    assert required_template_fields("retention") == ("decision_point",)


def test_required_template_fields_unknown_raises() -> None:
    with pytest.raises(KeyError):
        required_template_fields("ctr")


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
