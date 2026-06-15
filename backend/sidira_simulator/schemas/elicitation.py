"""Within-agent reaction distribution (agent-behavior-spec Item B / ticket #221).

The consumption path historically elicited ONE reaction per agent at
`temperature=0` — the documented mode-collapse recipe (#221): with ~50 agents
over ~6 personas you get ~6 effective opinions with cosmetic seed jitter, and
the Wilson/bootstrap CIs then bracket a *collapsed* point estimate — confident
intervals around no variance (precisely wrong).

This module models the fix's data shape: a per-agent *distribution* of plausible
reactions (verbalized sampling — k candidate reactions, each with a probability),
elicited in one raised-temperature call. The modal sample remains the canonical
frozen reaction (the identity-continuity contract in `memory.agent_memory`),
while the full distribution is captured so the follow-up scoring slice can
aggregate within-agent variance hierarchically and un-collapse the CIs.

Scope: this is the data shape + capture only. The scorer still consumes the
modal sample, so at the default `k=1` it is byte-identical to the historical
path — see `services.reaction_elicitor`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReactionSample(BaseModel):
    """One candidate reaction within an agent's reaction distribution.

    `probability` is supplied as a *relative weight* (any value > 0); the parent
    `ReactionDistribution` normalizes the set to sum to 1, so after construction
    each stored value is a true probability in (0, 1]. Modelling it as a bare
    positive weight lets the elicitor pass the LLM's self-reported numbers
    through verbatim without pre-scaling — the normalization is the single source
    of truth for "these sum to 1".
    """

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    probability: float = Field(gt=0.0)


class ReactionDistribution(BaseModel):
    """A per-agent distribution of plausible reactions (#221 verbalized sampling).

    Invariant: `samples` is non-empty and its probabilities sum to 1 (enforced by
    normalization at construction). `temperature` records the sampling
    temperature used to elicit the distribution — provenance for the eval, so a
    captured distribution is self-describing about how much variance to trust.
    """

    model_config = ConfigDict(extra="forbid")

    samples: list[ReactionSample] = Field(min_length=1)
    temperature: float = Field(ge=0.0)

    @model_validator(mode="after")
    def _normalize_probabilities(self) -> ReactionDistribution:
        # The LLM's self-reported probabilities rarely sum to exactly 1, and the
        # elicitor passes raw weights through; normalize so the stored
        # distribution always satisfies the sum-to-1 invariant downstream code
        # can rely on. `model_copy` does not re-run field validation in pydantic
        # v2, so dividing cannot trip ReactionSample's gt=0 constraint.
        total = sum(s.probability for s in self.samples)
        if total <= 0:
            # Unreachable through valid ReactionSamples (each is gt=0), but guard
            # explicitly so a future construction path can't yield a degenerate,
            # un-normalizable distribution that silently divides by zero.
            raise ValueError("reaction distribution probabilities must sum to > 0")
        if abs(total - 1.0) > 1e-9:
            self.samples = [
                s.model_copy(update={"probability": s.probability / total}) for s in self.samples
            ]
        return self

    @property
    def modal(self) -> ReactionSample:
        """The highest-probability sample — the canonical frozen reaction.

        Ties resolve to the first occurrence (the order the agent emitted them),
        because `max` returns the first maximal element — so the choice is
        deterministic for a given distribution.
        """
        return max(self.samples, key=lambda s: s.probability)


# ── Per-metric outcome elicitation: conversion (#221 §3a) ───────────────────


class ConversionDecision(BaseModel):
    """A per-agent conversion decision (agent-behavior-spec §3a).

    The agent allocates a fixed number of "trials" (the §3a prompt frames it as
    10 times in their normal life) across the realistic actions it might take;
    `action_counts` is that allocation. `conversion_action_label` names which
    key is the conversion event. `p_conv` is the share of the allocation that
    went to conversion.

    Design note (deviation from the literal spec, recorded deliberately):
    `p_conv` normalizes by the ACTUAL total rather than a hard-coded 10. LLMs
    do not reliably make counts sum to exactly 10; normalizing by the real
    total yields the honest allocation fraction and is robust to a model that
    returns e.g. 9 or 11, while a degenerate total of 0 (or a missing
    conversion label) still surfaces as a per-agent failure (ValueError at
    construction) rather than a silent zero.
    """

    model_config = ConfigDict(extra="forbid")

    action_counts: dict[str, int] = Field(min_length=1)
    conversion_action_label: str = Field(min_length=1)
    primary_reason: str = ""
    self_reported_confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _validate(self) -> ConversionDecision:
        if any(v < 0 for v in self.action_counts.values()):
            raise ValueError("conversion action_counts must be non-negative")
        if self.conversion_action_label not in self.action_counts:
            raise ValueError(
                f"conversion_action_label {self.conversion_action_label!r} "
                "absent from action_counts"
            )
        if sum(self.action_counts.values()) <= 0:
            raise ValueError("conversion action_counts must sum to > 0")
        return self

    @property
    def p_conv(self) -> float:
        """Allocation share that went to the conversion action, in [0, 1]."""
        total = sum(self.action_counts.values())
        return self.action_counts[self.conversion_action_label] / total
