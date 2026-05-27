"""Personas route — list personas in the active Persona Pack.

Phase 5 #101: the wizard's persona-filter checkbox list needs the active
pack's persona metadata (id + name + weight) to render. Today the only
public way to discover persona ids was to wait for a sim to materialize
agents and inspect `/simulations/{id}/agents`; #101 needs it at submit
time, so this route exposes it directly.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from pythia_simulator.adapters.base import ArtifactNotFound
from pythia_simulator.adapters.persona_loader import PersonaPackLoader
from pythia_simulator.api.deps import current_customer_id, get_persona_loader

router = APIRouter(prefix="/personas", tags=["personas"])


class PersonaSummary(BaseModel):
    """Wizard-shaped projection of a Persona.

    Just what the persona-filter checkbox list needs to render -- id (for
    the SimulationRequest.selected_personas payload), name (for the label),
    and weight (for the "{N}% of population" subtext). The full Persona
    schema carries description + behavioral_seeds etc. that the wizard
    doesn't surface.
    """

    id: str
    name: str
    weight: float


class ActivePersonasResponse(BaseModel):
    pack_version: str
    personas: list[PersonaSummary]


@router.get("", response_model=ActivePersonasResponse)
async def list_active_personas(
    customer_id: str = Depends(current_customer_id),
    loader: PersonaPackLoader = Depends(get_persona_loader),
) -> ActivePersonasResponse:
    """Return the active Persona Pack's personas + head-count weights.

    Used by the wizard's #101 persona-filter UI. `weight` is from the
    `head_count` scheme (the same one allocate() uses by default), so the
    subtext displayed to PMs matches what the allocator would actually do.
    """
    try:
        pack = loader.load_latest(customer_id)
    except ArtifactNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    head_count = pack.weights.head_count
    return ActivePersonasResponse(
        pack_version=pack.version,
        personas=[
            PersonaSummary(
                id=p.id,
                name=p.name,
                weight=head_count.get(p.id, 0.0),
            )
            for p in pack.personas
        ],
    )
