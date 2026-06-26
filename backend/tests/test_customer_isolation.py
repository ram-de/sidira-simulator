"""Cross-customer isolation matrix (#30).

Phase 5 scoping audit: customer A's data must be invisible to customer B
through every storage layer. Each test creates data as ``cust-a`` and
asserts ``cust-b`` reads nothing — covering the metadata repos (Simulation,
AgentInstance, AgentFeedback) and the path-keyed artifact layers
(AgentMemory, FeedbackLog, RunStateStore).

The final test is the regression guard the audit leaves behind: every API
route must resolve the tenant via ``current_customer_id`` unless it is on
the explicit tenant-agnostic allowlist. A new router added without scoping
fails this test instead of shipping a leak.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from sqlalchemy.dialects import postgresql

from sidira_simulator.adapters.db_models import AgentInstance, Simulation
from sidira_simulator.adapters.r2 import LocalArtifactStore
from sidira_simulator.adapters.repositories import (
    InMemoryAgentFeedbackRepo,
    InMemoryAgentInstanceRepo,
    InMemorySimulationRepo,
    PostgresAgentInstanceRepo,
    PostgresSimulationRepo,
)
from sidira_simulator.api.deps import current_customer_id
from sidira_simulator.main import app
from sidira_simulator.memory.agent_memory import AgentMemory
from sidira_simulator.memory.feedback_log import FeedbackLog
from sidira_simulator.schemas.agent import AgentInstanceMetadata
from sidira_simulator.schemas.feedback import FeedbackEvent, FeedbackTargetKind
from sidira_simulator.services.run_state import RunStateStore, SimulationRunState

CUST_A = "cust-a"
CUST_B = "cust-b"
NOW = datetime(2026, 6, 9, tzinfo=timezone.utc)


# ──────────────────────────────────────────────────────────────────────
# SimulationRepo
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_simulation_list_recent_isolated() -> None:
    """Customer A creates a sim; customer B's list_recent returns 0 rows."""
    repo = InMemorySimulationRepo()
    await repo.create(
        sim_id="sim-iso-1",
        customer_id=CUST_A,
        persona_pack_version="v_1",
        feature_pack_version="2026-W23",
        hypothesis_json={"prose": "isolation"},
    )
    assert await repo.list_recent(CUST_A) != []
    assert await repo.list_recent(CUST_B) == []


@pytest.mark.asyncio
async def test_simulation_get_and_update_isolated() -> None:
    """Cross-customer get returns None; cross-customer update raises."""
    repo = InMemorySimulationRepo()
    await repo.create(
        sim_id="sim-iso-2",
        customer_id=CUST_A,
        persona_pack_version="v_1",
        feature_pack_version="2026-W23",
        hypothesis_json={},
    )
    assert await repo.get("sim-iso-2", CUST_B) is None
    with pytest.raises(KeyError):
        await repo.update_status("sim-iso-2", CUST_B, "complete")
    # A's row is untouched by B's failed write.
    row = await repo.get("sim-iso-2", CUST_A)
    assert row is not None
    assert row["status"] == "pending"


# ──────────────────────────────────────────────────────────────────────
# AgentInstanceRepo
# ──────────────────────────────────────────────────────────────────────


def _agent_row(agent_id: str, customer_id: str, sim_id: str) -> dict:
    return {
        "id": agent_id,
        "customer_id": customer_id,
        "simulation_id": sim_id,
        "persona_id": "p_test",
        "persona_pack_version": "v_1",
        "persona_name": "Test Persona",
        "created_at": NOW,
        "last_active_at": NOW,
    }


@pytest.mark.asyncio
async def test_agent_instance_isolated() -> None:
    """B cannot list, get, or touch A's agents — even knowing the sim id."""
    repo = InMemoryAgentInstanceRepo()
    await repo.create(_agent_row("agent-iso-1", CUST_A, "sim-iso-1"))

    assert await repo.list_for_simulation("sim-iso-1", CUST_A) != []
    assert await repo.list_for_simulation("sim-iso-1", CUST_B) == []
    assert await repo.get("agent-iso-1", CUST_B) is None
    with pytest.raises(KeyError):
        await repo.touch("agent-iso-1", CUST_B)


# ──────────────────────────────────────────────────────────────────────
# AgentFeedbackRepo (write-only repo — rows must carry the tenant)
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_agent_feedback_rows_carry_customer_id() -> None:
    """Every recorded feedback row is stamped with the recording tenant."""
    repo = InMemoryAgentFeedbackRepo()
    await repo.record(
        feedback_id="fb-1",
        customer_id=CUST_A,
        agent_id="agent-iso-1",
        turn_index=0,
        realistic_flag=True,
    )
    # Non-empty first — an `all()` over zero rows would pass vacuously.
    assert len(repo._feedback) == 1
    assert all(row["customer_id"] == CUST_A for row in repo._feedback)


# ──────────────────────────────────────────────────────────────────────
# Postgres repos — the production tenant boundary. SQL-shape tests assert
# the customer predicate is in the emitted query; the get/touch/update
# paths (Python-side check after session.get) are exercised with a stub
# row owned by customer A.
# ──────────────────────────────────────────────────────────────────────


class _RecordingSession:
    """Minimal AsyncSession stand-in: records statements, stubs `get`."""

    def __init__(self, result=None, row=None) -> None:
        self.statements: list = []
        self._result = result
        self._row = row
        self.committed = False

    async def execute(self, statement):
        self.statements.append(statement)
        return self._result

    async def get(self, model, key):
        return self._row

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass

    def in_transaction(self) -> bool:
        return True

    @property
    def new(self):
        return set()

    @property
    def dirty(self):
        return set()

    @property
    def deleted(self):
        return set()


class _EmptyScalarResult:
    def scalars(self):
        return self

    def all(self) -> list:
        return []


def _compiled_sql(statement) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))


@pytest.mark.asyncio
async def test_postgres_simulation_list_recent_has_customer_predicate() -> None:
    """The emitted SQL must filter simulations on customer_id."""
    session = _RecordingSession(result=_EmptyScalarResult())
    repo = PostgresSimulationRepo(session)

    await repo.list_recent(CUST_B)

    assert "simulations.customer_id =" in _compiled_sql(session.statements[0])


@pytest.mark.asyncio
async def test_postgres_simulation_get_and_update_enforce_customer() -> None:
    """A row owned by A is invisible/immutable through B's repo calls."""
    row = Simulation(id="sim-iso-1", customer_id=CUST_A, status="pending")
    session = _RecordingSession(row=row)
    repo = PostgresSimulationRepo(session)

    assert await repo.get("sim-iso-1", CUST_B) is None
    with pytest.raises(KeyError):
        await repo.update_status("sim-iso-1", CUST_B, "complete")
    assert session.committed is False
    assert row.status == "pending"


@pytest.mark.asyncio
async def test_postgres_agent_list_has_customer_predicate() -> None:
    """The emitted SQL must filter agent_instances on customer_id."""
    session = _RecordingSession(result=_EmptyScalarResult())
    repo = PostgresAgentInstanceRepo(session)

    await repo.list_for_simulation("sim-iso-1", CUST_B)

    assert "agent_instances.customer_id =" in _compiled_sql(session.statements[0])


@pytest.mark.asyncio
async def test_postgres_agent_get_and_touch_enforce_customer() -> None:
    """A's agent row is invisible/untouchable through B's repo calls."""
    row = AgentInstance(
        id="agent-iso-1",
        customer_id=CUST_A,
        simulation_id="sim-iso-1",
        persona_id="p_test",
        persona_pack_version="v_1",
        persona_name="Test Persona",
        created_at=NOW,
        last_active_at=NOW,
        message_count=0,
    )
    session = _RecordingSession(row=row)
    repo = PostgresAgentInstanceRepo(session)

    assert await repo.get("agent-iso-1", CUST_B) is None
    with pytest.raises(KeyError):
        await repo.touch("agent-iso-1", CUST_B)
    assert session.committed is False
    assert row.message_count == 0


# ──────────────────────────────────────────────────────────────────────
# Path-keyed artifact layers (R2 / local store)
# ──────────────────────────────────────────────────────────────────────


def _metadata(customer_id: str) -> AgentInstanceMetadata:
    return AgentInstanceMetadata(
        id="agent-iso-1",
        simulation_id="sim-iso-1",
        customer_id=customer_id,
        persona_id="p_test",
        persona_pack_version="v_1",
        persona_name="Test Persona",
        created_at=NOW,
        last_active_at=NOW,
    )


def test_agent_memory_isolated_by_path(tmp_path: Path) -> None:
    """Same agent id + sim id under customer B resolves to nothing."""
    store = LocalArtifactStore(tmp_path)
    memory = AgentMemory(store, store)
    memory.write_identity(_metadata(CUST_A), "identity body")
    memory.write_initial_reaction(_metadata(CUST_A), "reaction body")

    assert memory.load(_metadata(CUST_A)).identity_prompt == "identity body"
    with pytest.raises(FileNotFoundError):
        memory.load(_metadata(CUST_B))


def test_feedback_log_isolated_by_path(tmp_path: Path) -> None:
    """A's feedback events are unreadable under B's key prefix."""
    store = LocalArtifactStore(tmp_path)
    flog = FeedbackLog(store)
    flog.append(
        customer_id=CUST_A,
        simulation_id="sim-iso-1",
        event=FeedbackEvent(
            target_kind=FeedbackTargetKind.AGENT,
            target_id="agent-iso-1",
            turn_index=0,
            realistic_flag=True,
            created_at=NOW,
        ),
    )
    assert flog.read_all(customer_id=CUST_A, simulation_id="sim-iso-1") != []
    assert flog.read_all(customer_id=CUST_B, simulation_id="sim-iso-1") == []
    assert (
        flog.latest_flags(
            customer_id=CUST_B,
            simulation_id="sim-iso-1",
            target_kind=FeedbackTargetKind.AGENT,
            target_id="agent-iso-1",
        )
        == {}
    )


def test_run_state_isolated_by_path(tmp_path: Path) -> None:
    """Live run state written for A is a 404-shaped miss for B."""
    store = LocalArtifactStore(tmp_path)
    rs = RunStateStore(store)
    rs.write_state(
        SimulationRunState(
            simulation_id="sim-iso-1",
            customer_id=CUST_A,
            started_at=NOW,
            updated_at=NOW,
        )
    )
    assert rs.read_state(CUST_A, "sim-iso-1").customer_id == CUST_A
    with pytest.raises(FileNotFoundError):
        rs.read_state(CUST_B, "sim-iso-1")


# ──────────────────────────────────────────────────────────────────────
# Route-level regression guard
# ──────────────────────────────────────────────────────────────────────

# Routes that legitimately serve no tenant-scoped data. Adding a path here
# is a deliberate, reviewable act — the test failure message points people
# at this list.
TENANT_AGNOSTIC_ROUTES = {
    ("GET", "/health"),
    # Signature IS the auth; provisions the tenant rather than reading one.
    ("POST", "/webhooks/clerk"),
    # Process-wide model catalog — no tenant data.
    ("GET", "/models"),
    # Process-wide simulation caps — no tenant data.
    ("GET", "/config/limits"),
    # Service-to-service credential pull (#206 Slice C): the tenant is the
    # {customer} path segment, not a browser session — CI carries no session.
    # Auth is the dedicated SIDIRA_CRAWLER_CREDENTIALS_TOKEN bearer (see
    # api/internal.py), not current_customer_id.
    ("GET", "/internal/crawl-credentials/{customer}"),
    # Experiment-memory (#28/#29 + #31/#32): pure RETRIEVAL over the demo SEED
    # archive (real experiments) and the synthetic-simulation seed — no tenant
    # data is read or written (mirrors /models, /config/limits). When this meets
    # a real customer the archive load becomes tenant-scoped and these move out.
    ("POST", "/experiments/search-similar"),
    ("POST", "/experiments/chat"),
    ("POST", "/experiments/conversation"),
    # Connector onboarding (#19): catalog + CSV parsing/validation helpers that
    # read/write NO tenant archive — they list connectors, serve the static CSV
    # template/sample, parse an uploaded CSV for preview, and validate credential
    # SHAPE. The tenant-scoped connector routes (/{kind}/preview, /{kind}/import,
    # GET /connectors/imports) DO depend on current_customer_id and are not listed
    # here. When validate/preview begin persisting per-customer connector state
    # they move out of this allowlist.
    ("GET", "/connectors"),
    ("GET", "/connectors/csv/template"),
    ("GET", "/connectors/csv/sample"),
    ("POST", "/connectors/csv/preview"),
    ("POST", "/connectors/{kind}/validate"),
}

# Non-APIRoute mounts FastAPI registers itself (docs/openapi). Anything else
# (WebSocketRoute, Mount, raw Starlette Route) can't be checked for the
# current_customer_id dependency, so it must be deliberately listed here.
FRAMEWORK_ROUTE_PATHS = {
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
}


def _depends_on_customer_id(dependant) -> bool:
    if dependant.call is current_customer_id:
        return True
    return any(_depends_on_customer_id(d) for d in dependant.dependencies)


def test_every_route_resolves_the_tenant() -> None:
    """Every API route must depend on current_customer_id or be allowlisted.

    This is the durable output of the #30 scoping audit: a new endpoint
    that forgets tenant scoping fails here instead of shipping a
    cross-customer leak.
    """
    unscoped: list[str] = []
    unverifiable: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            # WebSocket routes, mounts, and raw Starlette routes have no
            # dependant we can inspect — they must be explicitly known.
            if getattr(route, "path", None) not in FRAMEWORK_ROUTE_PATHS:
                unverifiable.append(f"{type(route).__name__} {getattr(route, 'path', route)}")
            continue
        for method in route.methods - {"HEAD", "OPTIONS"}:
            if (method, route.path) in TENANT_AGNOSTIC_ROUTES:
                continue
            if not _depends_on_customer_id(route.dependant):
                unscoped.append(f"{method} {route.path}")

    assert not unverifiable, (
        "Non-APIRoute routes the guard cannot inspect for tenant scoping "
        f"(scope them by hand, then add to FRAMEWORK_ROUTE_PATHS): {sorted(unverifiable)}"
    )
    assert not unscoped, (
        "Routes without current_customer_id dependency (add scoping, or "
        f"allowlist in TENANT_AGNOSTIC_ROUTES with a comment): {sorted(unscoped)}"
    )
