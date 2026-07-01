"""Grounded g-formula predictor — the RUNTIME manifest reader (Epic #538, #540).

Phase-1b of the engine rewire:

    LLM-as-translator (#539) → **grounded predictor (#540, THIS)**
    → negative-control watchdog (#541) → LLM fallback.

Given a :class:`~sidira_simulator.schemas.mechanism.MechanismSpec` (produced by
the #539 translator) and the customer's precomputed
:class:`~sidira_simulator.schemas.estimability.EstimabilityManifest`, this returns
a **direction-only** grounded prediction: the *sign* of the (treatment, outcome)
effect the build-time worker already estimated — or ``covered=False`` when the
pair was never precomputed, which the router (#542) reads to fall back to the
LLM.

**ML-FREE.** The heavy causal compute (support checks, g-formula / T-learner /
IPW) runs at pack-build time in ``sidira-persona-worker`` and is baked into the
manifest. This module does ZERO estimation — it only MATCHES + RETRIEVES. Pure
stdlib + pydantic; it imports NONE of the heavy ML stack. Keeping it here is what
lets the API image stay ML-free.

**Direction-only.** The prediction is a sign (``"positive"`` / ``"negative"``),
never a surfaced number. The point estimates ride ALONG inside the matched
``candidate`` for later calibration but are never the headline.

**Inert.** Nothing in a live request path (api / orchestrator / runner) imports
this yet — wiring is #542. Ships safe in prod. Never raises: every failure mode
degrades to a ``covered=False`` result carrying a human-readable ``reason``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import structlog

from sidira_simulator.schemas.estimability import CandidateEffect, EstimabilityManifest
from sidira_simulator.schemas.mechanism import MechanismSpec

log = structlog.get_logger()


@dataclass(frozen=True)
class GroundedPrediction:
    """The direction-only result of matching a spec against the manifest.

    - ``covered``: True iff a precomputed effect for the spec's (treatment,
      outcome) pair was found. When False the router (#542) falls back to the LLM.
    - ``direction``: the sign of the effect (``"positive"`` / ``"negative"``), or
      None when not covered — or when the matched candidate is not supportable and
      so carries no computed sign. THIS is the prediction; it is never a number.
    - ``supportable``: the build-time support verdict for the matched candidate.
      A covered-but-``supportable=False`` result means the pair was in the grid but
      the data couldn't support an estimate (weak overlap / thin arms); the
      watchdog (#541) / router treat it cautiously.
    - ``candidate``: the full matched :class:`CandidateEffect` (carries the point
      estimates for later calibration), or None when not covered.
    - ``reason``: why not covered, or which candidate matched — for logging / the
      router's audit trail.
    """

    covered: bool
    direction: Literal["positive", "negative"] | None
    supportable: bool
    candidate: CandidateEffect | None
    reason: str


def _find_candidate(
    manifest: EstimabilityManifest, treatment: str, outcome: str
) -> CandidateEffect | None:
    """First precomputed effect whose (treatment, outcome) matches, else None."""
    for effect in manifest.candidate_effects:
        if effect.treatment == treatment and effect.outcome == outcome:
            return effect
    return None


def grounded_predict(spec: MechanismSpec, manifest: EstimabilityManifest) -> GroundedPrediction:
    """Match a mechanism spec to a precomputed effect; return a direction-only sign.

    Logic (never raises):

    1. ``spec.mappable is False`` → NOT covered without touching the manifest (the
       translator couldn't ground the treatment/outcome to real columns).
    2. Otherwise find the candidate effect whose ``(treatment, outcome)`` equals
       ``(spec.treatment_column, spec.outcome_column)``.
       - No match → NOT covered (the pair was never precomputed → LLM fallback).
       - Match → COVERED. ``direction = candidate.sign_adjusted`` and
         ``supportable = candidate.supportable``. A matched-but-not-supportable
         candidate is still ``covered=True`` (the pair IS in the grid) but flagged
         via ``supportable=False`` and typically carries no ``direction``.
    """
    if not spec.mappable:
        return GroundedPrediction(
            covered=False,
            direction=None,
            supportable=False,
            candidate=None,
            reason=(
                "spec not mappable" + (f": {spec.unmapped_reason}" if spec.unmapped_reason else "")
            ),
        )

    # A mappable spec has non-None treatment/outcome columns (the schema validator
    # forces mappable=False otherwise), but guard anyway — never trust, never raise.
    treatment = spec.treatment_column
    outcome = spec.outcome_column
    if treatment is None or outcome is None:  # pragma: no cover — defensive
        return GroundedPrediction(
            covered=False,
            direction=None,
            supportable=False,
            candidate=None,
            reason="spec mappable but missing treatment/outcome column",
        )

    candidate = _find_candidate(manifest, treatment, outcome)
    if candidate is None:
        return GroundedPrediction(
            covered=False,
            direction=None,
            supportable=False,
            candidate=None,
            reason=f"no precomputed effect for (T={treatment!r}, Y={outcome!r})",
        )

    if not candidate.supportable:
        reason = f"matched (T={treatment!r}, Y={outcome!r}) but not supportable"
        if candidate.support_reasons:
            reason += f": {'; '.join(candidate.support_reasons)}"
        return GroundedPrediction(
            covered=True,
            direction=candidate.sign_adjusted,
            supportable=False,
            candidate=candidate,
            reason=reason,
        )

    return GroundedPrediction(
        covered=True,
        direction=candidate.sign_adjusted,
        supportable=True,
        candidate=candidate,
        reason=f"matched precomputed effect (T={treatment!r}, Y={outcome!r})",
    )


def estimability_manifest_key(customer_id: str, version: str, setup_id: str) -> str:
    """R2 key for the estimability manifest — beside the Feature Pack manifest.

    Mirrors ``feature_pack_loader``'s layout: the pack manifest lives at
    ``{feature_pack_prefix}/{version}/manifest.json``; the estimability manifest
    is its sibling, ``{feature_pack_prefix}/{version}/estimability_manifest.json``.
    Routing through ``feature_pack_prefix`` inherits the DEFAULT-setup legacy path
    and the path-traversal guard for named setups.
    """
    # Imported lazily so this module carries no import-time dependency on the R2 /
    # artifact adapters — keeps it trivially unit-testable and INERT.
    from sidira_simulator.adapters.feature_pack_loader import feature_pack_prefix

    return f"{feature_pack_prefix(customer_id, setup_id)}/{version}/estimability_manifest.json"


def load_estimability_manifest(
    customer_id: str, pack_version: str, setup_id: str = "default"
) -> EstimabilityManifest | None:
    """Load the manifest that sits beside a customer's Feature Pack, or None.

    Thin R2 read that MIRRORS ``FeaturePackLoader`` (same
    :func:`~sidira_simulator.adapters.r2.get_featurepack_store` read store, same
    ``feature_pack_prefix`` layout). The manifest is OPTIONAL / off-by-default: a
    customer whose pack predates the build-time precompute simply has no manifest,
    so a missing key returns None (not an error) and the router falls back to the
    LLM. A present-but-malformed manifest also degrades to None rather than
    raising — this read is never allowed to break a request.

    The predictor itself (:func:`grounded_predict`) takes an already-parsed
    manifest, so it is fully unit-testable WITHOUT R2 or this loader.
    """
    from sidira_simulator.adapters.base import load_json_artifact
    from sidira_simulator.adapters.r2 import get_featurepack_store

    key = estimability_manifest_key(customer_id, pack_version, setup_id)
    try:
        return load_json_artifact(get_featurepack_store(), key, EstimabilityManifest)
    except FileNotFoundError:
        # Expected for packs built before the precompute shipped — optional artifact.
        log.info(
            "grounded_predictor.manifest_absent",
            customer_id=customer_id,
            pack_version=pack_version,
            setup_id=setup_id,
        )
        return None
    except Exception as exc:  # noqa: BLE001 — a bad artifact degrades to LLM fallback, never raises
        log.warning(
            "grounded_predictor.manifest_load_failed",
            customer_id=customer_id,
            pack_version=pack_version,
            setup_id=setup_id,
            error=str(exc),
            exc_type=type(exc).__name__,
        )
        return None


__all__ = [
    "GroundedPrediction",
    "grounded_predict",
    "load_estimability_manifest",
    "estimability_manifest_key",
]
