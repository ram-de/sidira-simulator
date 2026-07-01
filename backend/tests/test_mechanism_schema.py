"""Unit tests for the MechanismSpec schema validator (Epic #538, ticket #539).

Isolates the DERIVED-mappability model_validator from the translator: the None-anchor
downgrade, the referential-integrity check against a supplied allowed-set, and the
`extra="forbid"` guard. Direction-only — the spec carries no number.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidira_simulator.schemas.mechanism import (
    AVAILABLE_COLUMNS_CONTEXT_KEY,
    MechanismSpec,
)


def _spec(**overrides) -> dict:
    base = {
        "capability_name": "cap",
        "treatment_column": "t",
        "treatment_contrast": "baseline vs treatment",
        "outcome_column": "y",
    }
    base.update(overrides)
    return base


def test_both_anchors_present_no_context_is_mappable() -> None:
    """With both anchors and no allowed-set, referential check is skipped → mappable."""
    spec = MechanismSpec(**_spec())
    assert spec.mappable is True
    assert spec.unmapped_reason is None


def test_none_treatment_forces_unmappable() -> None:
    spec = MechanismSpec(**_spec(treatment_column=None))
    assert spec.mappable is False
    assert "treatment_column" in (spec.unmapped_reason or "")


def test_none_outcome_forces_unmappable() -> None:
    spec = MechanismSpec(**_spec(outcome_column=None))
    assert spec.mappable is False
    assert "outcome_column" in (spec.unmapped_reason or "")


def test_context_allowed_set_all_present_is_mappable() -> None:
    spec = MechanismSpec.model_validate(
        _spec(covariates=["x1"], negative_controls=["nc1"]),
        context={AVAILABLE_COLUMNS_CONTEXT_KEY: ["t", "y", "x1", "nc1"]},
    )
    assert spec.mappable is True


def test_context_dangling_column_forces_unmappable() -> None:
    spec = MechanismSpec.model_validate(
        _spec(outcome_column="ghost"),
        context={AVAILABLE_COLUMNS_CONTEXT_KEY: ["t", "y"]},
    )
    assert spec.mappable is False
    assert "ghost" in (spec.unmapped_reason or "")


def test_context_dangling_covariate_and_neg_control_reported() -> None:
    spec = MechanismSpec.model_validate(
        _spec(covariates=["good", "bad_cov"], negative_controls=["bad_nc"]),
        context={AVAILABLE_COLUMNS_CONTEXT_KEY: ["t", "y", "good"]},
    )
    assert spec.mappable is False
    assert "bad_cov" in (spec.unmapped_reason or "")
    assert "bad_nc" in (spec.unmapped_reason or "")


def test_explicit_unmapped_reason_is_preserved() -> None:
    """A caller-provided reason is not clobbered by the derived one."""
    spec = MechanismSpec(**_spec(treatment_column=None, unmapped_reason="custom reason"))
    assert spec.mappable is False
    assert spec.unmapped_reason == "custom reason"


def test_extra_field_is_forbidden() -> None:
    with pytest.raises(ValidationError):
        MechanismSpec(**_spec(predicted_lift=0.12))


def test_defaults_are_sane() -> None:
    spec = MechanismSpec(**_spec())
    assert spec.covariates == []
    assert spec.negative_controls == []
    assert spec.mediator is None
    assert spec.sibling_metric is None
    assert spec.estimand == "ATE on outcome"
    assert spec.confidence == "low"
    assert spec.notes is None


def test_mediator_and_sibling_referential_integrity() -> None:
    """Mediator and sibling_metric are also checked against the allowed-set."""
    spec = MechanismSpec.model_validate(
        _spec(mediator="ghost_med", sibling_metric="ghost_sib"),
        context={AVAILABLE_COLUMNS_CONTEXT_KEY: ["t", "y"]},
    )
    assert spec.mappable is False
    assert "ghost_med" in (spec.unmapped_reason or "")
    assert "ghost_sib" in (spec.unmapped_reason or "")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
