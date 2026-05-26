"""Simulation request/result schemas — the PM-facing API contract."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from pythia_simulator.schemas.feature_pack import ReverseFigma


class Hypothesis(BaseModel):
    """PM-supplied feature change being validated."""

    capability_name: str
    prose: str
    proposed_prd: str | None = None
    proposed_figma: ReverseFigma | None = None


class SimulationRequest(BaseModel):
    """PM-submitted simulation request (Phase 2.5).

    `population_size` is the modeled userbase size — the simulator stratifies
    down to at most MAX_AGENTS actual agents using largest-remainder allocation.
    """

    model_config = ConfigDict(extra="forbid")  # reject the retired persona_sample_size

    hypothesis: Hypothesis
    population_size: int = Field(default=1000, ge=1, le=10_000_000)
    # Bound to signed BIGINT range so over-large values fail at request validation
    # rather than as a Postgres INSERT error after the row is half-built. (codex P2)
    run_seed: int | None = Field(
        default=None, ge=-(2**63), le=2**63 - 1
    )


class SimulationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class Weakness(BaseModel):
    """One diagnosed weakness in the hypothesis.

    `frequency`/`ci_low`/`ci_high` are optional today; populated by the
    Wilson-CI scoring path (Phase 2.5 issue #6).
    """

    category: Literal[
        "wrong_metric",
        "wrong_cohort",
        "broken_mechanism",
        "untestable_hypothesis",
        "hidden_guardrail_risk",
        "underpowered_design",
    ]
    summary: str
    supporting_agent_ids: list[str] = Field(default_factory=list)
    frequency: float | None = Field(default=None, ge=0.0, le=1.0)
    ci_low: float | None = Field(default=None, ge=0.0, le=1.0)
    ci_high: float | None = Field(default=None, ge=0.0, le=1.0)


class AgentAnalysisSummary(BaseModel):
    """Per-agent post-run summary (#51 result table).

    Compact projection of `services.scoring.AgentAnalysis` shaped for the
    result-table cell render. Persisted on `SimulationResult.per_agent_analyses`
    so the table can render sentiment chips + top quotes without N R2 reads.

    `top_quote` is a short prefix of the agent's frozen `initial_reaction`,
    trimmed to a clean word boundary. Computed once at score time so a
    20-row table doesn't fan out 20 R2 GETs every page load.
    """

    agent_id: str
    sentiment: Literal["positive", "neutral", "negative"]
    sentiment_confidence: float = Field(ge=0.0, le=1.0)
    top_quote: str = Field(
        description="Short prefix of the agent's initial reaction.",
    )


class SimulationResult(BaseModel):
    confidence_score: float = Field(ge=0, le=100)
    confidence_score_ci: tuple[float, float] | None = None
    weaknesses: list[Weakness] = Field(default_factory=list)
    refinement_suggestions: list[str] = Field(default_factory=list)
    per_agent_analyses: list[AgentAnalysisSummary] = Field(
        default_factory=list,
        description=(
            "Per-agent sentiment + top quote for the result-table render. "
            "Populated by the runner when scoring completes. Empty for sims "
            "that ran before #51 landed (backwards-compatible)."
        ),
    )


class Simulation(BaseModel):
    id: str
    customer_id: str
    created_at: datetime
    status: SimulationStatus
    persona_pack_version: str
    feature_pack_version: str
    hypothesis: Hypothesis
    population_size: int | None = None
    sampled_agent_count: int | None = None
    run_seed: int | None = None
    agent_instance_ids: list[str] = Field(default_factory=list)
    result: SimulationResult | None = None
