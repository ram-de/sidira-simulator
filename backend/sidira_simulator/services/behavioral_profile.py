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

What this module ALSO ships now (the formerly #7-gated step 2). `render_individual_row`
renders the spec's headline win — the per-agent *individual row* (layer 4): one
GMM-sampled user row rendered as its deviation *from this centroid*, which is
what creates within-persona variety. It consumes the Persona Pack **v1.1** fields
(sidira-personas#7 producer side, shipped 2026-06-14) that v1.0 packs do not carry:

  - `sample_rows` — N privacy-clean synthetic behavioral rows (GMM-sampled), and
  - `centroid_full` + `feature_scale` — the cluster mean and per-feature
    within-cluster dispersion, both in adapted-feature space, to z-score the
    row's deviation from the centroid.

On a v1.0 pack (no row inputs) the individual row degrades to "not available" and
the composer falls back to the centroid reference frame — fabricating a row from
the centroid would manufacture exactly the confabulated precision the whole spec
is built to prevent. `posterior_mean` is carried on the schema but its named
soft-membership hedge is a follow-up (it needs a component→persona-id map the
pack doesn't yet provide).

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
        """The behavioral-comparison block, or None when there is nothing salient.

        Returns None — so the composer emits no block — when no feature cleared
        the salience threshold (whether the source was absent, all-typical, or
        all-suppressed). A block only appears when there is genuine divergence.

        The heading and framing follow `source_tier`: the centroid tier renders
        the **persona-vs-population** comparison ("How you compare"), shared by
        every agent in the persona; the individual-row tiers render the
        **agent-vs-persona** comparison ("What's distinctive about you"), unique
        to this agent. The two answer different questions on different reference
        frames, so the composer picks the most individual tier available rather
        than stacking both (avoiding a redundant double "compare" block).
        """
        if not self.deltas:
            return None
        if self.source_tier in ("individual_row_real", "individual_row_synthetic"):
            return self._render_individual_row()
        return self._render_centroid()

    def _render_centroid(self) -> str:
        """Persona-vs-population block ("How you compare") — the centroid tier."""
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

    def _render_individual_row(self) -> str:
        """Agent-vs-persona block ("What's distinctive about you") — layer 4.

        Frames the deltas as how THIS specific agent diverges from its segment's
        norm, not as a segment-vs-population tendency. The honesty hedge names
        the row as a representative behavioral draw (it is GMM-synthetic, not the
        agent's literal history), so the agent acts the texture without quoting
        figures it does not actually own.
        """
        lines = [
            "## What's distinctive about you",
            "",
            (
                f"You belong to the **{self.persona_name}** segment, but you're "
                "not an average member of it. Compared with the typical "
                f"**{self.persona_name}**, you specifically tend to show:"
            ),
            "",
        ]
        lines += [f"- {d.line()}" for d in self.deltas]
        lines += [
            "",
            "(This is the behavioral texture of one individual like you, not an "
            "exact personal record — react as this specific person would, without "
            "quoting figures.)",
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


def render_individual_row(
    persona: Persona,
    sample_index: int,
    *,
    salience_threshold: float = DEFAULT_SALIENCE_THRESHOLD,
) -> BehavioralProfile:
    """Render one agent's individual-row behavioral profile (pure — layer 4).

    This is the agent-behavior-spec §2 headline: the per-agent *individual row*
    that creates within-persona variety. It selects ONE synthetic row from
    `persona.sample_rows` deterministically by `sample_index`, then renders that
    row's **within-cluster** deviation from the persona centroid as salient
    natural-language deltas — the same delta core `render_behavioral_profile`
    uses, on a different reference frame.

    Reference frame (the key distinction from the centroid tier): the centroid
    tier compares the *persona* to the *population* (`centroid_features`,
    population z-scores). This tier compares *this agent* to its *persona*, using
    the v1.1 adapted-feature-space fields, which are mutually consistent so the
    within-cluster z is computed directly::

        z = (sample_row[f] - centroid_full[f]) / feature_scale[f]

    It never touches `centroid_features` (different units, different key
    namespace), so the two tiers cannot cross-contaminate.

    Selection determinism: `sample_rows[sample_index % len(sample_rows)]`. Keyed
    on `sample_index` ALONE — not the arm — so a treatment agent and its control
    twin (which share `sample_index`) draw the identical row, preserving the #90
    paired-comparison invariant. `run_seed` is not folded in: the rows are a
    fixed per-persona pool and `sample_index` is already the stable per-agent
    identifier, so identity stays reproducible across re-runs.

    Degradation (honesty): when the persona carries no v1.1 row inputs
    (`sample_rows` / `centroid_full` / `feature_scale` empty — i.e. a v1.0 pack)
    or no feature has usable finite values, returns an ungrounded profile whose
    `render()` is None, so the composer cleanly falls back to the centroid tier.
    Non-finite or non-positive-scale features are skipped, never rendered (the
    FM-3 rule shared with `render_behavioral_profile` and identity_seed).

    `source_tier` is `individual_row_synthetic`: `sample_rows` are GMM-sampled,
    privacy-clean draws, never real user rows. The `individual_row_real` tier
    (Hillstrom/Criteo benchmark) is a separate, out-of-scope source.
    """
    rows = persona.sample_rows or []
    centroid = persona.centroid_full or {}
    scale = persona.feature_scale or {}
    if not rows or not centroid or not scale:
        # No v1.1 row inputs (v1.0 pack) — the composer degrades to the
        # centroid-population tier. Ungrounded so the honesty flags never let a
        # missing row masquerade as a real individual draw.
        return BehavioralProfile(
            persona_name=persona.name,
            deltas=[],
            suppressed_count=0,
            grounded=False,
            source_tier="none",
        )

    row = rows[sample_index % len(rows)]

    deltas: list[BehavioralDelta] = []
    suppressed = 0
    for feature, centroid_raw in centroid.items():
        if feature not in row or feature not in scale:
            # A feature must appear in all three (centroid, row, scale) to z-score
            # it; a partial key set is a malformed pack — skip, don't fabricate.
            continue
        s = float(scale[feature])
        row_val = float(row[feature])
        c_val = float(centroid_raw)
        if not (math.isfinite(s) and math.isfinite(row_val) and math.isfinite(c_val)):
            continue
        if s <= 0.0:
            # Non-positive scale would divide-by-zero or flip the sign; the
            # producer floors std to a tiny epsilon, so this only trips on a
            # malformed pack. Skip rather than emit a bogus delta.
            continue
        z = (row_val - c_val) / s
        if not math.isfinite(z):
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
        # Row inputs were present but no feature had a usable (finite,
        # positive-scale, overlapping) value — a malformed pack. Report it as
        # ungrounded so a broken row can't masquerade as a real individual draw
        # (mirrors the centroid tier's all-non-finite guard).
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
        grounded=True,
        source_tier="individual_row_synthetic",
    )
