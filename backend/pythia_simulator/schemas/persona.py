"""Persona Pack schema — produced by pythia-personas, consumed here.

Duplicated from pythia-personas until the shared pythia-schemas package lands.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class WeightSchemes(BaseModel):
    head_count: dict[str, float]
    order_weighted: dict[str, float] | None = None
    revenue_weighted: dict[str, float] | None = None


class Persona(BaseModel):
    """One persona — the template an AgentInstance is created from."""

    id: str
    name: str
    description: str
    jtbd: str | None = Field(default=None, description="Jobs-to-be-done summary")
    behavioral_snapshot: dict[str, float | int | str] = Field(default_factory=dict)
    centroid_features: dict[str, float] = Field(default_factory=dict)


class PersonaPack(BaseModel):
    version: str
    customer_id: str
    generated_at: datetime
    schema_version: Literal["1.0"] = "1.0"
    personas: list[Persona]
    weights: WeightSchemes
    stability_score: float
