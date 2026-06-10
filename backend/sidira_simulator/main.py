"""FastAPI app entry point."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sidira_simulator import __version__
from sidira_simulator.adapters.migrations import run_startup_migrations
from sidira_simulator.api import auth
from sidira_simulator.api import (
    agents,
    capabilities,
    config,
    crawls,
    feature_stores,
    feedback,
    models,
    persona_builds,
    persona_groups,
    persona_packs,
    personas,
    sample_workspace,
    simulations,
    webhooks,
)
from sidira_simulator.services.runtime_config import resolve_sidira_env

# Paths that bypass BOTH auth gates. `/health` is the public liveness probe;
# `/webhooks/clerk` is Clerk's server-to-server delivery — it can't carry a
# browser session token or the internal key, so it self-authenticates via the
# Svix signature instead (see api/webhooks.py).
_PUBLIC_PATHS = frozenset({"/health", "/webhooks/clerk"})


def _cors_origins() -> list[str]:
    raw = resolve_sidira_env(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    assert raw is not None
    return [o.strip() for o in raw.split(",") if o.strip()]


def create_app() -> FastAPI:
    run_startup_migrations()

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

    # Middlewares run outermost-first in reverse registration order, so the
    # Clerk gate (registered first) runs *inside* the internal-key gate: in
    # prod the Caddy proxy must clear the internal-key network boundary before
    # we spend a token verification. Both must pass for protected routes.
    @app.middleware("http")
    async def clerk_auth_gate(request: Request, call_next):
        if (
            not auth.clerk_configured()
            or request.url.path in _PUBLIC_PATHS
            or request.method == "OPTIONS"
        ):
            return await call_next(request)
        state = auth.authenticate(request)
        if state is None:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        if state.customer_id is None:
            # Authenticated but the session carries no tenant claim. We must NOT
            # fall through here: current_customer_id() would then resolve the
            # SIDIRA_CUSTOMER_ID / "demo" env default and silently grant this
            # user the fallback tenant. Reject instead — a Clerk-gated request
            # only proceeds once it resolves to a concrete customer.
            return JSONResponse({"detail": "No tenant for user"}, status_code=403)
        request.state.user_id = state.user_id
        request.state.customer_id = state.customer_id
        return await call_next(request)

    @app.middleware("http")
    async def internal_api_key_gate(request: Request, call_next):
        expected = resolve_sidira_env("INTERNAL_API_KEY")
        if not expected or request.url.path in _PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)
        if request.headers.get("x-sidira-internal-key") != expected:
            return JSONResponse({"detail": "Not found"}, status_code=404)
        return await call_next(request)

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
    app.include_router(crawls.router)
    app.include_router(feature_stores.router)
    app.include_router(persona_builds.router)
    app.include_router(persona_packs.router)
    app.include_router(personas.router)
    app.include_router(sample_workspace.router)
    app.include_router(webhooks.router)

    return app


app = create_app()
