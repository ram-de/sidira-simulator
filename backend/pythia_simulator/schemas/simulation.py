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


class SimulationResult(BaseModel):
    confidence_score: float = Field(ge=0, le=100)
    confidence_score_ci: tuple[float, float] | None = None
    weaknesses: list[Weakness] = Field(default_factory=list)
    refinement_suggestions: list[str] = Field(default_factory=list)


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
    agent_instance_ids: list[str] = Field(default_factory=list)
    result: SimulationResult | None = None
