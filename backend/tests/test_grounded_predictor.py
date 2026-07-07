"""Grounded predictor + estimability read-schema tests (Epic #538, #540).

Pure: no ML deps, no R2, no live LLM. Builds ``MechanismSpec``s directly and
matches them against an in-memory :class:`EstimabilityManifest`, plus a
round-trip of the real build-time example artifact.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sidira_simulator.schemas.estimability import EstimabilityManifest
from sidira_simulator.schemas.mechanism import MechanismSpec
from sidira_simulator.services.grounded_predictor import (
    GroundedPrediction,
    grounded_predict,
)

# The real build-time artifact (mirrors the producer's output shape exactly).
_EXAMPLE_JSON = (
    Path(__file__).resolve().parents[2]
    / "research"
    / "empirical-uplift-spike"
    / "estimability_manifest_example.json"
)


def _manifest() -> EstimabilityManifest:
    """A manifest with the two supportable Hillstrom effects + one NOT-supportable.

    Mirrors the example artifact's shape and adds a thin-support candidate so the
    covered-but-flagged path is exercised without needing a bespoke fixture file.
    """
    return EstimabilityManifest(
        manifest_version="1.0",
        customer_id="acme",
        setup_id="default",
        pack_version="v_1",
        feature_store="fixture://hillstrom",
        columns=[],
        capability_links=[],
        candidate_effects=[
            {
                "treatment": "womens_email",
                "outcome": "visit",
                "covariates": ["recency", "loghist", "mens", "womens", "newbie"],
                "supportable": True,
                "support_reasons": [],
                "n_treat": 21387,
                "n_control": 21306,
                "naive_ate": 0.0452,
                "t_learner_ate": 0.0453,
                "ipw_ate": 0.0454,
                "overlap_fraction": 1.0,
                "naive_adjusted_gap": 0.00013,
                "sign_adjusted": "positive",
            },
            {
                # Not supportable → no estimate, sign_adjusted null.
                "treatment": "womens_email",
                "outcome": "spend",
                "covariates": ["recency"],
                "supportable": False,
                "support_reasons": ["insufficient overlap", "thin treatment arm"],
                "n_treat": 3,
                "n_control": 21306,
                "naive_ate": None,
                "t_learner_ate": None,
                "ipw_ate": None,
                "overlap_fraction": None,
                "naive_adjusted_gap": None,
                "sign_adjusted": None,
            },
        ],
    )


def _spec(treatment: str | None, outcome: str | None) -> MechanismSpec:
    """A spec built WITHOUT an allowed-set → referential check skipped; mappable is
    driven only by whether both anchors are non-None."""
    return MechanismSpec(
        capability_name="Womens email campaign",
        treatment_column=treatment,
        treatment_contrast="womens email vs no email",
        outcome_column=outcome,
    )


def test_covered_matching_mappable_spec_returns_direction() -> None:
    """(a) A matching mappable spec is covered with the precomputed sign."""
    result = grounded_predict(_spec("womens_email", "visit"), _manifest())

    assert isinstance(result, GroundedPrediction)
    assert result.covered is True
    assert result.direction == "positive"
    assert result.supportable is True
    assert result.candidate is not None
    assert result.candidate.treatment == "womens_email"
    assert result.candidate.outcome == "visit"
    # The point estimate rides along for calibration but is not the prediction.
    assert result.candidate.t_learner_ate == pytest.approx(0.0453)


def test_pair_absent_from_manifest_is_not_covered() -> None:
    """(b) A mappable spec whose (T, Y) isn't precomputed → not covered."""
    result = grounded_predict(_spec("womens_email", "conversion"), _manifest())

    assert result.covered is False
    assert result.direction is None
    assert result.candidate is None
    assert "no precomputed effect" in result.reason


def test_not_mappable_spec_short_circuits() -> None:
    """(c) A mappable=False spec is not covered without touching the manifest."""
    spec = _spec(None, "visit")  # None treatment → validator forces mappable=False
    assert spec.mappable is False

    result = grounded_predict(spec, _manifest())

    assert result.covered is False
    assert result.direction is None
    assert result.candidate is None
    assert "not mappable" in result.reason


def test_covered_but_not_supportable_is_flagged() -> None:
    """(d) A matched candidate with supportable=False → covered but flagged."""
    result = grounded_predict(_spec("womens_email", "spend"), _manifest())

    assert result.covered is True
    assert result.supportable is False
    assert result.direction is None  # no computed sign on a not-supportable effect
    assert result.candidate is not None
    assert "not supportable" in result.reason
    assert "insufficient overlap" in result.reason


def test_example_manifest_round_trips() -> None:
    """(e) The real build-time example artifact parses into the read schema."""
    assert _EXAMPLE_JSON.exists(), f"missing fixture: {_EXAMPLE_JSON}"
    raw = json.loads(_EXAMPLE_JSON.read_text())

    manifest = EstimabilityManifest.model_validate(raw)

    assert manifest.customer_id == "acme"
    assert manifest.pack_version == "v_1"
    assert len(manifest.candidate_effects) == 2
    # And the predictor works end-to-end against the parsed real artifact.
    result = grounded_predict(_spec("womens_email", "visit"), manifest)
    assert result.covered is True
    assert result.direction == "positive"


def test_producer_unverified_guard_confidence_parses() -> None:
    """(f) Contract regression: the producer emits ``guard_confidence="unverified"``
    on its no-vouched-NC path (a value NOT in the old ``Literal["high","low/abstain"]``).

    Since the loader degrades a malformed manifest to None, a strict Literal here
    would let a SINGLE such candidate silently discard the ENTIRE manifest and route
    everything to the LLM. The field is ``str | None`` so it must parse cleanly, and
    ``guard_trips=None`` remains the sentinel the watchdog reads for CANT_VALIDATE.
    """
    manifest = EstimabilityManifest.model_validate(
        {
            "manifest_version": "1.0",
            "customer_id": "acme",
            "setup_id": "default",
            "pack_version": "v_1",
            "feature_store": "fixture://nc",
            "candidate_effects": [
                {
                    "treatment": "womens_email",
                    "outcome": "visit",
                    "covariates": ["recency"],
                    "supportable": True,
                    "support_reasons": [],
                    "n_treat": 21387,
                    "n_control": 21306,
                    "t_learner_ate": 0.045,
                    "sign_adjusted": "positive",
                    # no vouched negative control → producer's honest "unverified" path
                    "guard_trips": None,
                    "guard_confidence": "unverified",
                    "guard_reason": "no vouched negative control",
                }
            ],
        }
    )

    cand = manifest.candidate_effects[0]
    assert cand.guard_confidence == "unverified"
    assert cand.guard_trips is None  # sentinel the watchdog reads → CANT_VALIDATE


# ── coverage manifest + grounding fields (#564, read schema) ──────────────────


def _base_manifest_dict(**over) -> dict:
    base = {
        "manifest_version": "1.0",
        "customer_id": "acme",
        "setup_id": "default",
        "pack_version": "v_1",
        "feature_store": "fixture://cov",
        "candidate_effects": [],
    }
    base.update(over)
    return base


def test_legacy_manifest_without_564_fields_parses_with_defaults() -> None:
    """Backward-compat: a pre-#564 manifest parses exactly as before — coverage
    empty, grounding_complete=None (legacy/unknown), grounding_gaps empty."""
    manifest = EstimabilityManifest.model_validate(
        _base_manifest_dict(
            candidate_effects=[
                {
                    "treatment": "womens_email",
                    "outcome": "visit",
                    "supportable": True,
                    "sign_adjusted": "positive",
                }
            ]
        )
    )
    assert manifest.coverage == []
    cand = manifest.candidate_effects[0]
    assert cand.grounding_complete is None
    assert cand.grounding_gaps == []
    # And the predictor still matches it (behavior unchanged).
    result = grounded_predict(_spec("womens_email", "visit"), manifest)
    assert result.covered is True and result.direction == "positive"


def test_coverage_entries_parse_including_null_fraction_none() -> None:
    """The producer's 4-key coverage rows parse — incl. an expected-but-absent
    column whose null_fraction is unknown (null) and observed=False."""
    manifest = EstimabilityManifest.model_validate(
        _base_manifest_dict(
            coverage=[
                {"name": "recency", "missingness": "present", "null_fraction": 0.0, "observed": True},
                {"name": "sparse_col", "missingness": "behavioural", "null_fraction": 0.6, "observed": True},
                {"name": "dead_col", "missingness": "structural", "null_fraction": 1.0, "observed": True},
                {"name": "declared_but_untracked", "missingness": "structural", "null_fraction": None, "observed": False},
            ]
        )
    )
    assert [c.missingness for c in manifest.coverage] == [
        "present",
        "behavioural",
        "structural",
        "structural",
    ]
    absent = manifest.coverage[3]
    assert absent.null_fraction is None
    assert absent.observed is False
    assert manifest.coverage[1].null_fraction == 0.6


def test_unmodeled_missingness_value_does_not_nuke_manifest() -> None:
    """A future producer missingness value must parse (str, not Literal) — the
    degrade-to-None loader must never discard a whole manifest over one row."""
    manifest = EstimabilityManifest.model_validate(
        _base_manifest_dict(
            coverage=[
                {"name": "x", "missingness": "some_future_class", "null_fraction": 0.1, "observed": True}
            ]
        )
    )
    assert manifest.coverage[0].missingness == "some_future_class"
