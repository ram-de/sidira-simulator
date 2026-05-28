"""Model catalog endpoint for PM-selectable LLMs (#103)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from pythia_simulator.adapters.llm import (
    configured_model_specs,
    default_model_id,
)

router = APIRouter(prefix="/models", tags=["models"])


class ModelInfo(BaseModel):
    id: str
    provider: Literal["groq", "anthropic", "openai"]
    label: str
    description: str
    speed_label: str
    cost_label: str
    is_default: bool


class ListModelsResponse(BaseModel):
    models: list[ModelInfo]
    default_model_id: str


@router.get("", response_model=ListModelsResponse)
def list_models() -> ListModelsResponse:
    """Return models actually usable by this backend process.

    Providers without API keys are omitted so the wizard reflects runtime
    truth instead of presenting choices that would fail after submit.
    """
    resolved_default = default_model_id()
    return ListModelsResponse(
        default_model_id=resolved_default,
        models=[
            ModelInfo(
                id=spec.id,
                provider=spec.provider,  # type: ignore[arg-type]
                label=spec.label,
                description=spec.description,
                speed_label=spec.speed_label,
                cost_label=spec.cost_label,
                is_default=spec.id == resolved_default,
            )
            for spec in configured_model_specs()
        ],
    )
