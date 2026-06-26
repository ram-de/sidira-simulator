"""FastAPI app entry point."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sidira_simulator import __version__
from sidira_simulator.adapters.migrations import run_startup_migrations
from sidira_simulator.api import auth
from sidira_simulator.api import (
    agents,
    capabilities,
    config,
    connectors,
    crawls,
    experiments,
    feature_stores,
    feedback,
    internal,
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

# Service-to-service routes hit by CI, not a browser. They bypass BOTH the Clerk
# session gate (no session token to present) and the internal-key gate — the
# crawler reaches api.sidira.ai directly, and Caddy only staples
# X-Sidira-Internal-Key on the /_sidira_web_proxy/* paths, never on this
# fallthrough (deploy/Caddyfile.api). These routes are NOT public: each carries
# its own dedicated, constant-time bearer-token auth (see api/internal.py), which
# is the sole authority on this path.
_INTERNAL_PREFIX = "/internal/"

# loc path segments that mark a field whose rejected value is a secret. A 422
# from FastAPI/Pydantic echoes the offending `input` (and sometimes `ctx`) back
# to the caller by default — for the crawl-setup password (#206 Slice C) that
# would leak the very secret the field is write-only to protect. The handler
# below redacts `input`/`ctx` on any validation error whose loc touches one of
# these, covering both the per-item password field and model-level test_users
# errors that carry the whole (password-bearing) list as their input.
_SECRET_VALIDATION_LOC_TOKENS = frozenset({"password", "test_users"})

# Request paths whose body carries a write-only secret. A validation failure on
# an *unrelated* top-level field (e.g. a missing `capabilities`) still puts the
# whole submitted body — passwords and all — in the error `input`, and its loc
# would not match the secret tokens above. So for these paths the handler
# redacts `input` on every error, not just the secret-loc ones. Enumerate every
# write route whose request body carries a write-only credential — add new ones
# here when they appear:
#   - `/crawl-setup` (singular) + `/crawl-setups` (create) + `/crawl-setups/{id}`
#     (update): password-bearing CrawlSetup body (#206 Slice C, #215/#245).
#   - `/feature-stores` (create): Snowflake `password` on SnowflakeConnectionRequest
#     (#328). The `/feature-stores/{id}/...` sub-routes operate on a saved
#     connection and carry no password, so they are intentionally NOT matched.
def _is_secret_body_path(path: str) -> bool:
    return (
        path == "/crawl-setup"
        or path == "/crawl-setups"
        or path.startswith("/crawl-setups/")
        or path == "/feature-stores"
    )


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
            or request.url.path.startswith(_INTERNAL_PREFIX)
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
        if (
            not expected
            or request.url.path in _PUBLIC_PATHS
            or request.url.path.startswith(_INTERNAL_PREFIX)
            or request.method == "OPTIONS"
        ):
            return await call_next(request)
        if request.headers.get("x-sidira-internal-key") != expected:
            return JSONResponse({"detail": "Not found"}, status_code=404)
        return await call_next(request)

    @app.exception_handler(RequestValidationError)
    async def _redact_secret_validation_errors(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Same 422 shape as FastAPI's default handler, but with the rejected
        # value scrubbed from any error that touches a secret field — so an
        # invalid crawl-setup password is never reflected back (#206 Slice C).
        # On a secret-bearing path, scrub every error's input (a top-level
        # failure can carry the whole password-bearing body as its input).
        redact_all = _is_secret_body_path(request.url.path)
        cleaned = []
        for err in exc.errors():
            if redact_all or _SECRET_VALIDATION_LOC_TOKENS.intersection(
                str(p) for p in err.get("loc", ())
            ):
                err = {**err, "input": "<redacted>"}
                err.pop("ctx", None)  # ctx (e.g. limit errors) can echo it too
            cleaned.append(err)
        return JSONResponse(status_code=422, content={"detail": jsonable_encoder(cleaned)})

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
    app.include_router(capabilities.summary_router)
    app.include_router(capabilities.archive_router)
    app.include_router(crawls.router)
    app.include_router(experiments.router)
    app.include_router(connectors.router)
    app.include_router(internal.router)
    app.include_router(feature_stores.router)
    app.include_router(persona_builds.router)
    app.include_router(persona_packs.router)
    app.include_router(personas.router)
    app.include_router(sample_workspace.router)
    app.include_router(webhooks.router)

    return app


app = create_app()
