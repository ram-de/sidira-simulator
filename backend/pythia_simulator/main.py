"""FastAPI app entry point."""

from __future__ import annotations

from fastapi import FastAPI

from pythia_simulator import __version__
from pythia_simulator.api import agents, capabilities, simulations


def create_app() -> FastAPI:
    app = FastAPI(
        title="pythia-simulator",
        version=__version__,
        description=(
            "Pythia simulation engine — pre-experiment hypothesis validation via "
            "behavioral simulation + post-simulation agent chat."
        ),
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    app.include_router(simulations.router)
    app.include_router(agents.router)
    app.include_router(capabilities.router)

    return app


app = create_app()
