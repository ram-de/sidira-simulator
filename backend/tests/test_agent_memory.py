"""Tests for memory.agent_memory (Phase 2.5, issue #5, T4).

Covers the new R2 identity_seed sidecar: write_identity_seed persists it,
load() round-trips it, and load() of a pre-#5 simulation (no sidecar)
returns identity_seed=None for back-compat.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pythia_simulator.memory.agent_memory import AgentMemory
from pythia_simulator.schemas.agent import AgentInstanceMetadata
from pythia_simulator.schemas.identity import IdentitySeed


class _FakeArtifactStore:
    """In-memory ArtifactReader+Writer for tests."""

    def __init__(self) -> None:
        self._blobs: dict[str, str] = {}
        self._lines: dict[str, list[str]] = {}

    def write_text(self, key: str, body: str) -> None:
        self._blobs[key] = body

    def append_line(self, key: str, line: str) -> None:
        self._lines.setdefault(key, []).append(line)

    def read_text(self, key: str) -> str:
        if key not in self._blobs:
            raise FileNotFoundError(key)
        return self._blobs[key]

    def read_lines(self, key: str) -> list[str]:
        if key not in self._lines:
            raise FileNotFoundError(key)
        return list(self._lines[key])


def _metadata() -> AgentInstanceMetadata:
    now = datetime(2026, 5, 22, tzinfo=timezone.utc)
    return AgentInstanceMetadata(
        id="agent-1",
        simulation_id="sim-1",
        customer_id="acme",
        persona_id="p_test",
        persona_pack_version="v1.0",
        persona_name="P",
        created_at=now,
        last_active_at=now,
    )


def _seed() -> IdentitySeed:
    return IdentitySeed(
        age_band="25-34",
        locale_band="sf_bay",
        tenure_band="3-5y",
        current_state="commuting home",
        recent_gripe="late delivery last Tuesday",
    )


def test_identity_seed_persists_to_r2_and_loads_back() -> None:
    store = _FakeArtifactStore()
    memory = AgentMemory(reader=store, writer=store)
    metadata = _metadata()
    seed = _seed()

    memory.write_identity(metadata, "identity prompt body")
    memory.write_initial_reaction(metadata, "initial reaction body")
    memory.write_identity_seed(metadata, seed)

    loaded = memory.load(metadata)

    assert loaded.identity_seed == seed
    # Other layers still load correctly.
    assert loaded.identity_prompt == "identity prompt body"
    assert loaded.initial_reaction == "initial reaction body"


def test_load_without_seed_artifact_returns_none() -> None:
    """Back-compat: pre-#5 simulations have no identity_seed.json sidecar."""
    store = _FakeArtifactStore()
    memory = AgentMemory(reader=store, writer=store)
    metadata = _metadata()

    memory.write_identity(metadata, "identity prompt body")
    memory.write_initial_reaction(metadata, "initial reaction body")
    # No write_identity_seed call.

    loaded = memory.load(metadata)

    assert loaded.identity_seed is None
