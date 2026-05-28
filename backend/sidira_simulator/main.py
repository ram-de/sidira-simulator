"""FastAPI app entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sidira_simulator import __version__
from sidira_simulator.api import (
    agents,
    capabilities,
    config,
    feature_stores,
    feedback,
    models,
    persona_builds,
    persona_groups,
    persona_packs,
    personas,
    simulations,
)
from sidira_simulator.services.runtime_config import resolve_sidira_env


def _cors_origins() -> list[str]:
    raw = resolve_sidira_env(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    assert raw is not None
    return [o.strip() for o in raw.split(",") if o.strip()]


def create_app() -> FastAPI:
    app = FastAPI(
        title="Sidira Simulator API",
        version=__version__,
        description=(
            "Sidira simulation engine — pre-experiment hypothesis validation via "
            "behavioral simulation + post-simulation agent chat."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    app.include_router(simulations.router)
    app.include_router(agents.router)
    app.include_router(persona_groups.router)
    app.include_router(feedback.agent_router)
    app.include_router(feedback.group_router)
    app.include_router(models.router)
    app.include_router(config.router)
    app.include_router(capabilities.router)
    app.include_router(feature_stores.router)
    app.include_router(persona_builds.router)
    app.include_router(persona_packs.router)
    app.include_router(personas.router)

    return app


app = create_app()
