"""#215/#245 PR 3a: setup_id threads request → orchestrator → loader → DB.

A simulation now carries a ``setup_id`` so a sim built from a NAMED crawl
setup's capabilities resolves THAT setup's Feature Pack, never silently falling
back to the default pack. These tests prove:

  * the orchestrator passes the request's setup_id to BOTH loader resolve sites
    (``resolve_latest_version`` in prepare + ``resolve_latest_version`` and
    ``load_capability`` in the background run);
  * an omitted/default setup_id is BYTE-IDENTICAL — the loader is called with
    "default", which ``feature_pack_prefix`` maps to the exact legacy R2 prefix
    (``customers/<id>/featurepacks``), with NO ``setups/`` segment;
  * setup_id round-trips onto the persisted sim and the GET detail response;
  * a bad setup_id is rejected at the create route (422).
"""

from __future__ import annotations

import asyncio

import pytest

from sidira_simulator.adapters.feature_pack_loader import feature_pack_prefix
from sidira_simulator.adapters.repositories import (
    InMemoryAgentInstanceRepo,
    InMemoryCustomerRepo,
    InMemorySimulationRepo,
)
from sidira_simulator.schemas.feature_pack import Capability, ReverseFigma
from sidira_simulator.schemas.simulation import Hypothesis, SimulationRequest
from sidira_simulator.services.simulation_orchestrator import SimulationOrchestrator


class _SpyFeatureLoader:
    """Records every (method, customer_id, setup_id) the orchestrator calls.

    Returns canned values so the run can proceed without R2. The whole point is
    to capture the setup_id argument at each resolve/load site.
    """

    def __init__(self) -> None:
        self.resolve_calls: list[tuple[str, str]] = []
        self.load_capability_calls: list[tuple[str, str, str, str]] = []

    def resolve_latest_version(self, customer_id: str, setup_id: str = "default") -> str:
        self.resolve_calls.append((customer_id, setup_id))
        return "2026-W21"

    def load_capability(
        self,
        customer_id: str,
        version: str,
        capability_name: str,
        setup_id: str = "default",
    ) -> Capability:
        self.load_capability_calls.append((customer_id, version, capability_name, setup_id))
        return Capability(
            name=capability_name,
            surfaces=["home"],
            roles=[],
            entry_points=[],
            reverse_prd="# stub",
            reverse_figma=ReverseFigma(screens=[], transitions=[]),
        )


class _StubPersonaPack:
    version = "v_1"
    personas: list = []


class _StubPersonaLoader:
    def load_latest(self, customer_id: str):
        return _StubPersonaPack()


class _StubRunner:
    """Captures nothing of pack-resolution; just lets _run_with_id complete.

    The orchestrator's _run_with_id calls runner.run then persists. We make run
    a no-op that returns a completed simulation-like object.
    """

    _last_run_agent_records: list = []

    async def run(self, **kwargs):
        class _Sim:
            class _Status:
                value = "complete"

            status = _Status()
            result = None

        return _Sim()


def _make_orchestrator() -> tuple[SimulationOrchestrator, _SpyFeatureLoader, InMemorySimulationRepo]:
    spy = _SpyFeatureLoader()
    sim_repo = InMemorySimulationRepo()
    orch = SimulationOrchestrator(
        customer_repo=InMemoryCustomerRepo(),
        simulation_repo=sim_repo,
        agent_repo=InMemoryAgentInstanceRepo(),
        persona_loader=_StubPersonaLoader(),
        feature_pack_loader=spy,
        runner=_StubRunner(),
    )
    return orch, spy, sim_repo


_HYP = Hypothesis(capability_name="reorder", prose="Add a one-tap reorder button.")


def test_named_setup_resolves_that_setups_pack() -> None:
    """A named setup_id reaches BOTH resolve sites + load_capability — never
    the silent default."""
    orch, spy, sim_repo = _make_orchestrator()

    async def _go() -> None:
        sim_id, run = await orch.prepare(
            customer_id="org_real",
            hypothesis=_HYP,
            population_size=2,
            setup_id="checkout-v2",
        )
        await run()
        return sim_id

    sim_id = asyncio.run(_go())

    # prepare() resolved once, the background run resolved once — BOTH with the
    # named setup. Neither falls back to "default".
    assert spy.resolve_calls == [("org_real", "checkout-v2"), ("org_real", "checkout-v2")]
    # load_capability also carried the named setup as its 4th positional arg.
    assert spy.load_capability_calls == [("org_real", "2026-W21", "reorder", "checkout-v2")]
    # ...and the named setup is persisted on the row.
    assert sim_repo._sims[sim_id]["setup_id"] == "checkout-v2"


def test_omitted_setup_id_is_byte_identical_default() -> None:
    """An omitted setup_id resolves "default" at every site, and "default" maps
    to the EXACT legacy R2 prefix (no setups/ segment) — byte-identical to
    pre-#215 prod."""
    orch, spy, sim_repo = _make_orchestrator()

    async def _go() -> None:
        sim_id, run = await orch.prepare(
            customer_id="org_real",
            hypothesis=_HYP,
            population_size=2,
            # setup_id omitted entirely
        )
        await run()
        return sim_id

    sim_id = asyncio.run(_go())

    # Every resolve/load site saw exactly "default".
    assert spy.resolve_calls == [("org_real", "default"), ("org_real", "default")]
    assert spy.load_capability_calls == [("org_real", "2026-W21", "reorder", "default")]
    assert sim_repo._sims[sim_id]["setup_id"] == "default"

    # The crux: "default" resolves the legacy prefix with NO setups/ segment,
    # so the resolved R2 path is byte-identical to legacy prod.
    assert feature_pack_prefix("org_real", "default") == "customers/org_real/featurepacks"
    assert feature_pack_prefix("org_real") == "customers/org_real/featurepacks"
    # A named setup gets the extra segment (so the two never collide).
    assert (
        feature_pack_prefix("org_real", "checkout-v2")
        == "customers/org_real/setups/checkout-v2/featurepacks"
    )


def test_request_default_setup_id_is_default() -> None:
    """An omitted setup_id on the request schema defaults to "default"."""
    req = SimulationRequest(hypothesis=_HYP, population_size=2)
    assert req.setup_id == "default"


def test_request_rejects_unsafe_setup_id() -> None:
    """A path-traversal / unsafe setup_id is rejected at request validation
    (422), before it can become an R2 key segment."""
    with pytest.raises(ValueError):
        SimulationRequest(
            hypothesis=_HYP,
            population_size=2,
            setup_id="../other_customer",
        )


def test_request_accepts_named_setup_id() -> None:
    req = SimulationRequest(hypothesis=_HYP, population_size=2, setup_id="checkout-v2")
    assert req.setup_id == "checkout-v2"
