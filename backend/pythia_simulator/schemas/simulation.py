"""Simulation request/result schemas — the PM-facing API contract."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from pythia_simulator.schemas.feature_pack import ReverseFigma


class Hypothesis(BaseModel):
    """PM-supplied feature change being validated."""

    capability_name: str
    prose: str
    proposed_prd: str | None = None
    proposed_figma: ReverseFigma | None = None


class SimulationRequest(BaseModel):
    hypothesis: Hypothesis
    persona_sample_size: int = Field(default=10, ge=1, le=200)


class SimulationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class Weakness(BaseModel):
    """One diagnosed weakness in the hypothesis."""

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


class SimulationResult(BaseModel):
    confidence_score: float = Field(ge=0, le=100)
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
    agent_instance_ids: list[str] = Field(default_factory=list)
    result: SimulationResult | None = None
