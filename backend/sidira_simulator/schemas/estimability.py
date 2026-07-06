"""Estimability manifest — the READ schema for the build-time precompute artifact.

Epic #538, ticket #540 (Phase-1b of the engine rewire). The heavy causal
compute (support checks + g-formula / T-learner / IPW estimation) runs ONCE at
persona-pack build time in the separate ``sidira-persona-worker`` — see
``research/empirical-uplift-spike/manifest_builder.py`` — which writes an
``estimability_manifest.json`` beside ``manifest.json`` in R2. That producer
depends on the heavy ML stack (dataframes + scikit-learn estimators).

The Sidira API backend is deliberately **ML-FREE**. These models therefore
mirror ONLY the *output shape* of the build-time dataclasses (``ColumnEntry``,
``CapabilityLink``, ``CandidateEffect``, ``Manifest``) as a pure-stdlib +
pydantic read schema. NONE of the build-time compute is ported here; the runtime
grounded predictor (:mod:`sidira_simulator.services.grounded_predictor`) only
MATCHES a :class:`~sidira_simulator.schemas.mechanism.MechanismSpec` against a
precomputed :class:`CandidateEffect` and returns its sign. Direction-only.

**Tolerance.** Unlike the strict, ``extra="forbid"`` internal schemas, these
parse an EXTERNAL artifact produced by another codebase (the worker) whose
manifest_version may drift ahead of the API. We use ``extra="ignore"`` so a
newer manifest that adds fields still loads (forward compatibility) rather than
crashing the reader — a manifest is optional/off-by-default, so a permissive
read that can still find the (T, Y) sign is the safe posture.
"""

from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

# ``extra="ignore"``: this is an external artifact (produced by the worker, whose
# manifest_version can run ahead of this reader). Tolerating unknown keys keeps a
# newer manifest loadable instead of hard-failing an optional read path.
# ``populate_by_name=True``: several NC-guard fields carry validation aliases (so
# a producer that flattens the raw ``GuardedEstimate`` — ``floor`` / ``trips`` /
# ``confidence`` / ``reason`` — parses too), but we must still accept the canonical
# ``guard_*`` field names (what our own constructors / tests use).
_READ_CONFIG = ConfigDict(extra="ignore", populate_by_name=True)


class ColumnEntry(BaseModel):
    """One feature-store column as classified at build time (read mirror)."""

    model_config = _READ_CONFIG

    name: str
    dtype: str
    # treatment_candidate | outcome_candidate | covariate (kept as a str, not a
    # Literal — the taxonomy is the worker's, and we never branch on it at runtime).
    role: str
    distinct_count: int | None = None
    null_fraction: float = 0.0
    has_variation: bool = True


class CapabilityLink(BaseModel):
    """A crawler capability linked (or not) to a treatment column (read mirror)."""

    model_config = _READ_CONFIG

    capability_name: str
    surfaces: list[str] = []
    # None → the capability is not represented as a lever in the data → LLM route.
    treatment_column: str | None = None
    linked: bool = False


class CandidateEffect(BaseModel):
    """One precomputed (treatment → outcome) effect (read mirror of the producer).

    The grounded predictor consumes ``treatment`` / ``outcome`` to match a spec's
    ``(treatment_column, outcome_column)``, then reads ``sign_adjusted`` as the
    direction-only prediction and ``supportable`` as the caution flag. The point
    estimates (``naive_ate`` / ``t_learner_ate`` / ``ipw_ate`` / …) are carried
    ALONG for later calibration but are NEVER surfaced as the prediction.

    **Negative-control guard (optional, forward-compatible).** The ``guard_*`` /
    ``neg_control_*`` fields mirror the build-time ``GuardedEstimate`` (see
    ``research/empirical-uplift-spike/causal_estimator.py::negative_control_guard``)
    — the precomputed NC-guard verdict the persona-worker bakes in. They are the
    evidence the runtime watchdog (#541,
    :mod:`sidira_simulator.services.negative_control_watchdog`) reads to stamp
    CONFIRMS / CONTRADICTS / CAN'T-VALIDATE. All default to None/empty so packs
    built BEFORE the producer emits them still parse; ``guard_trips is None`` means
    NC evidence was not precomputed → the watchdog cannot certify trust.
    """

    model_config = _READ_CONFIG

    treatment: str
    outcome: str
    covariates: list[str] = []
    supportable: bool
    support_reasons: list[str] = []
    n_treat: int | None = None
    n_control: int | None = None
    # Point estimates are None on a not-supportable candidate (build-time skips
    # estimation). Carried for calibration only — never the headline prediction.
    naive_ate: float | None = None
    t_learner_ate: float | None = None
    ipw_ate: float | None = None
    overlap_fraction: float | None = None
    naive_adjusted_gap: float | None = None
    # The direction-only verdict. None on a not-supportable candidate (no estimate
    # was computed), else "positive" / "negative". The producer types this
    # ``str | None`` (``manifest_builder.CandidateEffect``); we pin the taxonomy.
    sign_adjusted: Literal["positive", "negative"] | None = None
    # --- Negative-control guard (precomputed, optional). Mirrors GuardedEstimate.
    # Additive + forward-compatible: absent on pre-guard packs (all None/empty),
    # so ``guard_trips is None`` distinguishes "NC evidence absent" from a verdict.
    # The ``guard_*`` fields also accept the raw ``GuardedEstimate`` key names
    # (``floor`` / ``trips`` / ``confidence`` / ``reason``) via validation aliases,
    # so the reader is robust whether the producer emits the canonical ``guard_*``
    # names or flattens the dataclass verbatim.
    neg_control_effect: float | None = None  # decisive (max-|effect|) NC residual
    neg_control_effects: dict[str, float] = {}  # {control_name: residual}
    guard_floor: float | None = Field(
        default=None, validation_alias=AliasChoices("guard_floor", "floor")
    )
    guard_ratio: float | None = None
    # True = untrustworthy (hidden confounding / effect indistinguishable from bias);
    # False = trustworthy empirical; None = NC evidence NOT precomputed.
    guard_trips: bool | None = Field(
        default=None, validation_alias=AliasChoices("guard_trips", "trips")
    )
    # Producer-supplied tag; informational only (the watchdog gates on ``guard_trips``,
    # never on this value). Known values today: "high" / "low/abstain" (mirroring
    # GuardedEstimate.confidence) and "unverified" (producer's no-vouched-NC path).
    # Kept ``str | None`` — NOT a strict Literal — precisely because this is an
    # external, independently-versioned artifact: a Literal here would reject an
    # unmodeled value and, since the loader degrades a malformed manifest to None,
    # a SINGLE such candidate would silently discard the ENTIRE manifest.
    guard_confidence: str | None = Field(
        default=None, validation_alias=AliasChoices("guard_confidence", "confidence")
    )
    guard_reason: str | None = Field(
        default=None, validation_alias=AliasChoices("guard_reason", "reason")
    )


class EstimabilityManifest(BaseModel):
    """The full build-time manifest, read-only (mirror of ``manifest_builder.Manifest``)."""

    model_config = _READ_CONFIG

    manifest_version: str
    customer_id: str
    setup_id: str
    pack_version: str
    feature_store: str
    columns: list[ColumnEntry] = []
    capability_links: list[CapabilityLink] = []
    candidate_effects: list[CandidateEffect] = []
    built_at: str | None = None


__all__ = [
    "ColumnEntry",
    "CapabilityLink",
    "CandidateEffect",
    "EstimabilityManifest",
]
