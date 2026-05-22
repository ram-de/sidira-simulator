"""Tests for SimulationRunner identity_seed wiring (Phase 2.5, issue #5, T2).

Covers the runner-level acceptance:
- After run() completes, every materialized agent has a non-None identity_seed
  persisted to R2 and reachable via AgentMemory.load().
- The runner threads run_seed + sample_index correctly: the seeds it persists
  match what draw_identity_seed produces for the same (persona, sample_index,
  run_seed) triples -- i.e. the reproducibility acceptance criterion from #5.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pythia_simulator.adapters.feature_pack_loader import FeaturePackLoader
from pythia_simulator.adapters.persona_loader import PersonaPackLoader
from pythia_simulator.adapters.r2 import LocalArtifactStore
from pythia_simulator.memory.agent_memory import AgentMemory
from pythia_simulator.schemas.agent import AgentInstanceMetadata
from pythia_simulator.schemas.simulation import Hypothesis
from pythia_simulator.services.identity_seed import draw_identity_seed
from pythia_simulator.services.population_sampler import allocate
from pythia_simulator.services.simulation_runner import SimulationRunner


_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"


class _StubChat:
    """Minimal chat stub -- canned reaction text, canned classifications."""

    def __init__(self) -> None:
        self.calls: list[list[dict]] = []

    def chat(self, messages, max_tokens=4096, temperature=0.0, seed=None):
        self.calls.append(messages)
        return "Stubbed reaction prose."

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        from pythia_simulator.schemas.scoring import (
            RefinementOutput,
            Sentiment,
            SentimentClassification,
            WeaknessClassification,
        )

        if schema is WeaknessClassification:
            return WeaknessClassification(
                categories=["wrong_cohort"], primary_reason="stub"
            )
        if schema is SentimentClassification:
            return SentimentClassification(
                sentiment=Sentiment.POSITIVE, confidence=0.8, one_line_summary="stub"
            )
        if schema is RefinementOutput:
            return RefinementOutput(suggestions=[])
        raise NotImplementedError(schema)


def _load_pack_and_capability():
    store = LocalArtifactStore(_FIXTURE_ROOT)
    persona_pack = PersonaPackLoader(store).load_latest("demo")
    feature_loader = FeaturePackLoader(store)
    feature_pack_version = feature_loader.resolve_latest_version("demo")
    capability = feature_loader.load_capability("demo", feature_pack_version, "reorder")
    return store, persona_pack, capability, feature_pack_version


def _hypothesis() -> Hypothesis:
    return Hypothesis(
        capability_name="reorder",
        prose="Add a one-tap reorder button to the home tab.",
    )


def _agent_metadata(record, *, simulation_id, persona_pack_version) -> AgentInstanceMetadata:
    return AgentInstanceMetadata(
        id=record.agent_id,
        customer_id="demo",
        simulation_id=simulation_id,
        persona_id=record.persona_id,
        persona_pack_version=persona_pack_version,
        persona_name=record.persona_name,
        created_at=record.created_at,
        last_active_at=record.created_at,
    )


@pytest.mark.asyncio
async def test_materialize_agent_attaches_identity_seed() -> None:
    """Every agent produced by run() must have identity_seed persisted in R2,
    and the rendered identity_prompt must contain the splice."""
    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()
    runner = SimulationRunner(store=store, chat_client=_StubChat())

    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_hypothesis(),
        population_size=3,
        run_seed=12345,
    )

    assert len(simulation.agent_instance_ids) == 3

    memory = AgentMemory(store, store)
    for record in runner._last_run_agent_records:
        metadata = _agent_metadata(
            record,
            simulation_id=simulation.id,
            persona_pack_version=persona_pack.version,
        )
        loaded = memory.load(metadata)
        seed = loaded.identity_seed
        assert seed is not None, f"agent {record.agent_id} missing seed"
        assert seed.age_band and seed.locale_band and seed.tenure_band
        assert seed.current_state and seed.recent_gripe
        assert "## About you specifically" in loaded.identity_prompt


@pytest.mark.asyncio
async def test_run_seed_propagates_into_agent_seeds() -> None:
    """The runner threads run_seed + sample_index into draw_identity_seed
    exactly. We re-derive the expected seeds with the same allocate() +
    draw_identity_seed and assert the runner's persisted seeds match.
    """
    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()
    run_seed = 999_111

    runner = SimulationRunner(store=store, chat_client=_StubChat())
    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_hypothesis(),
        population_size=5,
        run_seed=run_seed,
    )

    # Group runner-produced records by persona_id, preserving creation order =
    # sample_index (the runner enumerates 0..count-1 within each persona slot).
    by_persona: dict[str, list] = {}
    for record in runner._last_run_agent_records:
        by_persona.setdefault(record.persona_id, []).append(record)

    memory = AgentMemory(store, store)
    pack_by_id = {p.id: p for p in persona_pack.personas}
    allocation = allocate(persona_pack, 5)

    for persona_id, count in allocation:
        records = by_persona.get(persona_id, [])
        assert len(records) == count, f"persona {persona_id} count mismatch"
        for sample_index, record in enumerate(records):
            expected = draw_identity_seed(
                pack_by_id[persona_id], sample_index, run_seed
            )
            metadata = _agent_metadata(
                record,
                simulation_id=simulation.id,
                persona_pack_version=persona_pack.version,
            )
            loaded = memory.load(metadata)
            assert loaded.identity_seed == expected, (
                f"runner-persisted seed != re-derived for "
                f"persona={persona_id} sample_index={sample_index}"
            )
