"""Behavioral-profile renderer — turns a persona's behavioral feature stats into
the natural-language deltas an agent reads as "how people like me behave."

This is the first shipping piece of the agent-context assembly layer
(agent-behavior-spec spec §2, `sessions/agent-behavior-spec/context-assembly.md`).
§1 (`treatment_renderer.py`) defined what *change* the agent reads; §2 defines
*who the agent is* when it reads it — the hierarchical-conditioning stack the
research named the single highest-leverage accuracy component.

What this module ships now (audited gap (b)). `Persona.centroid_features` —
the cluster's mean feature vector, expressed in population z-scores — already
exists on every pack and is read by ZERO code today. This renderer consumes it
and emits the persona's *population-relative* behavioral profile as plain-
language deltas: the salient ways this segment differs from the typical user
("much higher order frequency", "much lower browse dependency"). That profile
is the **reference frame** layer 4 (the per-agent individual row) deviates from
— so building it now builds the reusable delta core, and closes the dangling
`centroid_features` gap with real data, not fabricated precision.

What this module does NOT ship yet (the #7-gated step 2). The spec's headline
win is the per-agent *individual row* (layer 4) — one real or GMM-sampled user
row rendered as its deviation *from this centroid*, which is what creates
within-persona variety. That needs two things v1.0 packs do not carry:

  - a behavioral **row** (real anonymized, or sampled from the fitted GMM
    component), and
  - per-feature **scale** (within-cluster dispersion) to z-score the row's
    deviation from the centroid.

Both arrive with #7 (personas hygiene). Until then there is no honest per-agent
row to render — fabricating one from the centroid would manufacture exactly the
confabulated precision the whole spec is built to prevent — so the individual
row degrades to "not available" and only the centroid reference frame renders.
The seam is explicit: `SourceTier` already names the row tiers, and
`render_behavioral_profile` takes the same shape they will plug into.

Like the §1 renderer this module is deliberately pure and side-effect-free: no
LLM, no I/O, deterministic given its inputs, and unit-testable against fixture
personas. Wiring it into `prompt_composer` (the frozen-identity entry point) is
a separate, higher-blast-radius step.

Design choices grounded in the spec:
- **Salience threshold |z| ≳ 0.5** (§2 / open Q1): render only features whose
  centroid sits ≳ 0.5 SD off the population mean; the gestalt already covers the
  typical, and dumping every feature dilutes the salient ones and inflates the
  prompt. Sub-threshold features are *counted* (`suppressed_count`), never
  silently dropped — the no-silent-degradation rule shared with §1.
- **Direction + rough magnitude, not raw numbers** (§2): agents read calibrated
  comparatives ("much higher") better than decimals (1.62).
- **Group tendency, not personal fact** (§2 measured-vs-proxy honesty): the
  centroid is a *segment* statistic shared by every agent in the persona, so the
  block is framed as a tendency of "people like you", and says so explicitly.
  Per-feature measured-vs-proxy tagging needs feature-role metadata that also
  arrives with #7; until then the whole block carries the one honest hedge
  rather than faking a distinction it cannot compute.
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from sidira_simulator.schemas.persona import Persona

Direction = Literal["higher", "lower"]
# Rough magnitude bucket from |z|. Comparative words, never the raw z (§2).
Magnitude = Literal["somewhat", "much", "dramatically"]
# Where the rendered profile came from. Only the last two are produced today;
# the `individual_row_*` tiers are the #7-gated seam (real / GMM-sampled rows
# rendered as their deviation from this centroid) and are named here so the
# degradation path doubles as the documented benchmark↔prod contract (§2).
SourceTier = Literal[
    "individual_row_real",
    "individual_row_synthetic",
    "centroid_population",
    "none",
]

# Default salience threshold (§2 / open Q1): start at 0.5, treat as tunable.
DEFAULT_SALIENCE_THRESHOLD = 0.5

# |z| bucket edges → magnitude word. Ordered low→high; the first edge a feature
# clears from the top sets its word.
_MAGNITUDE_EDGES: tuple[tuple[float, Magnitude], ...] = (
    (2.0, "dramatically"),
    (1.0, "much"),
    (0.0, "somewhat"),
)

# z-feature names are conventionally suffixed to mark the units (population
# z-score). Strip these so the rendered label reads as plain behavior.
_Z_SUFFIXES = ("_zscore", "_zscored", "_z")


class BehavioralDelta(BaseModel):
    """One salient way this persona's centroid diverges from the population."""

    model_config = ConfigDict(extra="forbid")

    feature: str = Field(description="Raw feature key from centroid_features.")
    label: str = Field(description="Humanized feature name (suffix-stripped).")
    z: float = Field(description="Centroid value in population z-scores.")
    direction: Direction
    magnitude: Magnitude

    def line(self) -> str:
        """Render as one profile bullet: `**much higher** order frequency`."""
        return f"**{self.magnitude} {self.direction}** {self.label}"


class BehavioralProfile(BaseModel):
    """The deterministic output of the behavioral-profile renderer.

    `grounded` / `source_tier` / `suppressed_count` mirror §1's honesty flags so
    a thin or absent source can never masquerade as a rich profile: `grounded`
    is False only when there is no centroid data at all; `suppressed_count` names
    how many features were below the salience threshold (counted, not dropped).
    """

    model_config = ConfigDict(extra="forbid")

    persona_name: str
    deltas: list[BehavioralDelta] = Field(default_factory=list)
    suppressed_count: int = Field(
        default=0,
        description="Finite features below the salience threshold — counted, not "
        "silently dropped.",
    )
    grounded: bool = Field(
        description="True when centroid_features carried usable (finite) values; "
        "False when there was no behavioral signal to render at all.",
    )
    source_tier: SourceTier

    def render(self) -> str | None:
        """The "How you compare" block, or None when there is nothing salient.

        Returns None — so the composer emits no block — when no feature cleared
        the salience threshold (whether the centroid was absent, all-typical, or
        all-suppressed). A block only appears when the segment genuinely diverges.
        """
        if not self.deltas:
            return None
        lines = [
            "## How you compare",
            "",
            (
                "Compared with the typical user, people like you — the "
                f"**{self.persona_name}** segment — tend to show:"
            ),
            "",
        ]
        lines += [f"- {d.line()}" for d in self.deltas]
        lines += [
            "",
            "(These are tendencies of your segment, not exact personal numbers — "
            "react as someone who behaves this way, not by quoting figures.)",
        ]
        return "\n".join(lines)


def _humanize(feature: str) -> str:
    """`order_frequency_z` → `order frequency`. Suffix-strip, then unslug."""
    name = feature
    for suffix in _Z_SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return name.replace("_", " ").strip() or feature


def _magnitude(abs_z: float) -> Magnitude:
    for edge, word in _MAGNITUDE_EDGES:
        if abs_z >= edge:
            return word
    return "somewhat"


def render_behavioral_profile(
    persona: Persona,
    *,
    salience_threshold: float = DEFAULT_SALIENCE_THRESHOLD,
) -> BehavioralProfile:
    """Render a persona's population-relative behavioral profile (pure).

    Reads `persona.centroid_features` (feature → population z-score) and emits
    the salient deltas (|z| ≥ `salience_threshold`) as direction + rough-
    magnitude comparatives, most-salient-first. Deterministic: the only inputs
    are the persona's name and centroid, and ordering is stabilized by
    (−|z|, feature) so equal-magnitude features sort by name.

    Non-finite z-values (NaN/±inf from a malformed pack) are skipped, never
    rendered — a half-formed delta must not reach the prompt (the FM-3 rule
    shared with identity_seed's `_safe_choice`).
    """
    features = persona.centroid_features or {}
    if not features:
        return BehavioralProfile(
            persona_name=persona.name,
            deltas=[],
            suppressed_count=0,
            grounded=False,
            source_tier="none",
        )

    deltas: list[BehavioralDelta] = []
    suppressed = 0
    for feature, raw in features.items():
        z = float(raw)
        if not math.isfinite(z):
            # Malformed pack value — skip entirely, do not count as suppressed
            # (suppressed means "real but not salient", which this is not).
            continue
        if abs(z) < salience_threshold:
            suppressed += 1
            continue
        deltas.append(
            BehavioralDelta(
                feature=feature,
                label=_humanize(feature),
                z=z,
                direction="higher" if z > 0 else "lower",
                magnitude=_magnitude(abs(z)),
            )
        )

    deltas.sort(key=lambda d: (-abs(d.z), d.feature))

    if not deltas and suppressed == 0:
        # centroid_features was present but every value was non-finite — a
        # malformed pack with no usable signal. Report it as ungrounded so the
        # honesty flags don't let a broken pack masquerade as real centroid data
        # (all-finite-but-typical is the distinct grounded case below: suppressed
        # > 0). suppressed == 0 with no deltas can only mean "no finite feature
        # was seen", since we already returned early on an empty centroid.
        return BehavioralProfile(
            persona_name=persona.name,
            deltas=[],
            suppressed_count=0,
            grounded=False,
            source_tier="none",
        )

    return BehavioralProfile(
        persona_name=persona.name,
        deltas=deltas,
        suppressed_count=suppressed,
        # `grounded` reflects that usable (finite) centroid data existed, even if
        # everything was sub-threshold (an all-typical segment is a real,
        # grounded finding — suppressed > 0).
        grounded=True,
        source_tier="centroid_population",
    )
