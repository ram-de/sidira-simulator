"""Optional Postgres integration smoke for Phase 5a #68.

Set SIDIRA_TEST_DATABASE_URL to run this test against a disposable Postgres DB.
It is skipped by default so the normal fast suite still works without Docker or
Neon credentials.
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
from sidira_simulator.adapters.persona_loader import PersonaPackLoader
from sidira_simulator.adapters.postgres import get_sessionmaker
from sidira_simulator.adapters.r2 import LocalArtifactStore
from sidira_simulator.adapters.repositories import (
    PostgresAgentInstanceRepo,
    PostgresConversationRepo,
    PostgresCustomerRepo,
    PostgresSimulationRepo,
)
from sidira_simulator.schemas.scoring import (
    RefinementOutput,
    Sentiment,
    SentimentClassification,
    WeaknessClassification,
)
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.simulation_orchestrator import SimulationOrchestrator
from sidira_simulator.services.simulation_runner import SimulationRunner

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
FIXTURE_ROOT = REPO_ROOT / "local-artifacts"


class _StubChat:
    def chat(self, messages, max_tokens=4096, temperature=0.0, seed=None):
        return "I'd give it a shot."

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        if schema is WeaknessClassification:
            return WeaknessClassification(
                categories=["wrong_cohort"],
                primary_reason="Stubbed classifier response.",
            )
        if schema is SentimentClassification:
            return SentimentClassification(
                sentiment=Sentiment.POSITIVE,
                confidence=0.8,
                one_line_summary="Stub: positive reception.",
            )
        if schema is RefinementOutput:
            return RefinementOutput(
                suggestions=[
                    "Narrow the cohort.",
                    "Add a guardrail metric.",
                ]
            )
        raise NotImplementedError(f"stub has no response for {schema}")


def _reset_postgres_singletons() -> None:
    from sidira_simulator.adapters import postgres

    postgres._engine = None
    postgres._sessionmaker = None


def _run_migrations() -> None:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.upgrade(config, "head")


async def _truncate_db() -> None:
    async with get_sessionmaker()() as session:
        await session.execute(
            text("TRUNCATE agent_feedback, agent_instances, simulations, customers CASCADE")
        )
        await session.commit()


@pytest.mark.asyncio
async def test_postgres_background_run_persists_after_request_session_closes(monkeypatch) -> None:
    database_url = os.environ.get("SIDIRA_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("set SIDIRA_TEST_DATABASE_URL to run Postgres integration smoke")

    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("SIDIRA_LOCAL_ARTIFACTS", str(FIXTURE_ROOT))
    _reset_postgres_singletons()
    await asyncio.to_thread(_run_migrations)
    await _truncate_db()

    store = LocalArtifactStore(FIXTURE_ROOT)
    persona_loader = PersonaPackLoader(store)
    feature_loader = FeaturePackLoader(store)
    runner = SimulationRunner(chat_client=_StubChat())

    @asynccontextmanager
    async def background_factory():
        async with get_sessionmaker()() as session:
            yield SimulationOrchestrator(
                customer_repo=PostgresCustomerRepo(session),
                simulation_repo=PostgresSimulationRepo(session),
                agent_repo=PostgresAgentInstanceRepo(session),
                persona_loader=persona_loader,
                feature_pack_loader=feature_loader,
                runner=runner,
            )

    async with get_sessionmaker()() as request_session:
        orchestrator = SimulationOrchestrator(
            customer_repo=PostgresCustomerRepo(request_session),
            simulation_repo=PostgresSimulationRepo(request_session),
            agent_repo=PostgresAgentInstanceRepo(request_session),
            persona_loader=persona_loader,
            feature_pack_loader=feature_loader,
            runner=runner,
            background_orchestrator_factory=background_factory,
        )
        sim_id, run = await orchestrator.prepare(
            customer_id="streamly_sample",
            hypothesis=Hypothesis(
                capability_name="continue_watching",
                prose="Put a Smart Resume CTA on the home screen.",
            ),
            population_size=3,
            sampled_agent_count=3,
        )

    await run()

    async with get_sessionmaker()() as read_session:
        sim_repo = PostgresSimulationRepo(read_session)
        agent_repo = PostgresAgentInstanceRepo(read_session)
        row = await sim_repo.get(sim_id, "streamly_sample")
        agents = await agent_repo.list_for_simulation(sim_id, "streamly_sample")

    assert row is not None
    assert row["status"] == "complete"
    assert row["result_json"]["confidence_score_ci"] is not None
    assert len(agents) == 3


async def _truncate_conversations() -> None:
    async with get_sessionmaker()() as session:
        await session.execute(
            text("TRUNCATE conversation_turns, conversations, customers CASCADE")
        )
        await session.commit()


@pytest.mark.asyncio
async def test_postgres_conversation_repo_tenant_isolation(monkeypatch) -> None:
    """POSTGRES-path tenant isolation for #41 (mirrors the in-memory API test but
    against a real DB so the composite FK + customer-scoped turn queries are
    exercised end-to-end):

    - get_with_turns scopes turns by customer_id, so a turn belonging to another
      tenant can never be returned/replayed.
    - append_turn drives turn_index off a tenant-scoped count, so a sibling thread
      owned by a DIFFERENT tenant never perturbs this thread's indices.

    Skipped unless SIDIRA_TEST_DATABASE_URL is set (same gate as the smoke above).
    """
    database_url = os.environ.get("SIDIRA_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("set SIDIRA_TEST_DATABASE_URL to run Postgres integration smoke")

    monkeypatch.setenv("DATABASE_URL", database_url)
    _reset_postgres_singletons()
    await asyncio.to_thread(_run_migrations)
    await _truncate_conversations()

    # Two tenants must exist (conversations.customer_id FKs customers.id).
    async with get_sessionmaker()() as session:
        customers = PostgresCustomerRepo(session)
        await customers.ensure_exists("org_a")
        await customers.ensure_exists("org_b")

    # Tenant A builds a 2-turn thread.
    async with get_sessionmaker()() as session:
        repo = PostgresConversationRepo(session)
        conv_a = await repo.create(conversation_id="conv_a", customer_id="org_a")
        await repo.append_turn(
            turn_id="a_t0",
            conversation_id="conv_a",
            customer_id="org_a",
            question="A first?",
            answer="A0.",
            citations=[],
            used_llm=False,
        )
        await repo.append_turn(
            turn_id="a_t1",
            conversation_id="conv_a",
            customer_id="org_a",
            question="A second?",
            answer="A1.",
            citations=[],
            used_llm=False,
        )
    assert conv_a["customer_id"] == "org_a"

    # Tenant B has its own separate thread.
    async with get_sessionmaker()() as session:
        repo = PostgresConversationRepo(session)
        await repo.create(conversation_id="conv_b", customer_id="org_b")
        b_turn = await repo.append_turn(
            turn_id="b_t0",
            conversation_id="conv_b",
            customer_id="org_b",
            question="B first?",
            answer="B0.",
            citations=[],
            used_llm=False,
        )
    assert b_turn is not None
    # B's first turn is index 0 — A's two turns (different tenant) don't leak in.
    assert [t["turn_index"] for t in b_turn["turns"]] == [0]

    async with get_sessionmaker()() as session:
        repo = PostgresConversationRepo(session)

        # A sees only A's turns, in order.
        a_detail = await repo.get_with_turns("conv_a", "org_a")
        assert a_detail is not None
        assert [t["turn_index"] for t in a_detail["turns"]] == [0, 1]
        assert all(t["question"].startswith("A") for t in a_detail["turns"])

        # Cross-tenant read of A's thread as org_b returns None (never the turns).
        assert await repo.get_with_turns("conv_a", "org_b") is None

        # And appending the next A turn still gets index 2 — tenant-scoped count
        # is unaffected by B's thread.
        a_next = await repo.append_turn(
            turn_id="a_t2",
            conversation_id="conv_a",
            customer_id="org_a",
            question="A third?",
            answer="A2.",
            citations=[],
            used_llm=False,
        )
        assert a_next is not None
        assert [t["turn_index"] for t in a_next["turns"]] == [0, 1, 2]
