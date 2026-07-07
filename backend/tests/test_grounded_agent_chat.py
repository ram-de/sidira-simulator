"""Grounded talk-to-users chat tests (Epic #538, ticket #544).

Pure: no R2, no live LLM. A fake in-memory ArtifactStore backs the AgentMemory
(mirrors test_agent_memory._FakeArtifactStore), a fake ChatClient drives both the
boundary classifier (``chat_json``) and the role-play reply (``chat``), and a
hand-built :class:`GroundedRecord` is injected (the live record-source wiring is
#545, deferred). Covers:

- explain → grounded answer; the record's mechanism/direction context reaches the
  LLM and the per-segment + calibrated-fiction labels are in the supplement.
- new-change → recompute signal, NO fabricated prediction.
- classifier NEVER raises on an exploding client → safe ``new_whatif`` branch.
- persistence ordering preserved (LLM-fail → nothing half-written, codex #52).
- flag OFF → the unchanged AgentChatService role-play path is used, byte-identical.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sidira_simulator.memory.agent_memory import AgentMemory
from sidira_simulator.schemas.agent import AgentInstanceMetadata, AgentRole
from sidira_simulator.services import grounded_agent_chat as mod
from sidira_simulator.services.agent_chat import _CHAT_GUARD_PREFIX
from sidira_simulator.services.grounded_agent_chat import (
    LABEL_CALIBRATED_FICTION,
    LABEL_PER_SEGMENT,
    GroundedAgentChatService,
    GroundedRecord,
    classify_pm_message,
)

FLAG = "SIDIRA_DECISION_FLOW_ENABLED"


# ── fakes ───────────────────────────────────────────────────────────────────────


class _FakeArtifactStore:
    """In-memory ArtifactReader+Writer (mirrors test_agent_memory)."""

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


class _FakeChat:
    """A fake ChatClient. ``chat_json`` returns a preset boundary output; ``chat``
    returns a canned role-play reply. Both record their inbound messages so tests
    can assert what reached the LLM."""

    def __init__(self, boundary: str = "explain", reply: str = "Grounded reply.") -> None:
        self._boundary = boundary
        self._reply = reply
        self.chat_calls: list[list[dict]] = []
        self.json_calls: list[list[dict]] = []

    def chat_json(self, messages, schema, **kwargs):  # noqa: ANN001 — test double
        self.json_calls.append(messages)
        return schema(boundary=self._boundary, rationale="stub")

    def chat(self, messages, **kwargs):  # noqa: ANN001 — test double
        self.chat_calls.append(messages)
        return self._reply


class _ExplodingChat:
    """chat_json / chat always raise — exercises the never-raise contracts."""

    def chat_json(self, messages, schema, **kwargs):  # noqa: ANN001 — test double
        raise RuntimeError("boom-json")

    def chat(self, messages, **kwargs):  # noqa: ANN001 — test double
        raise RuntimeError("boom-chat")


# ── fixtures ─────────────────────────────────────────────────────────────────────


def _metadata() -> AgentInstanceMetadata:
    now = datetime(2026, 6, 27, tzinfo=timezone.utc)
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


def _record() -> GroundedRecord:
    """A fixture record standing in for #545's live-sourced DecisionResult projection."""
    return GroundedRecord(
        capability_name="onboarding_gate",
        treatment_column="gate_level",
        treatment_contrast="gate at level 30 vs gate at level 40",
        outcome_column="day7_retention",
        mediator="early_session_count",
        direction="negative",
        label="verified — data overrides intuition",
        caution="none",
        watchdog_verdict="CONTRADICTS",
        is_grounded_verdict=True,
        counterfactual_summary=(
            "gate at level 30 vs gate at level 40 moves day7_retention in a negative direction"
        ),
        segment_context="treated n=900; control n=910; adjusted for recency",
        covered=True,
        supportable=True,
        n_treat=900,
        n_control=910,
    )


def _seed_agent(store: _FakeArtifactStore, metadata: AgentInstanceMetadata) -> AgentMemory:
    """Write the frozen identity + initial reaction so AgentMemory.load succeeds."""
    memory = AgentMemory(reader=store, writer=store)
    memory.write_identity(metadata, "You are P, a returning player.")
    memory.write_initial_reaction(metadata, "I liked the change when I first saw it.")
    return memory


@pytest.fixture(autouse=True)
def _flag_off(monkeypatch):
    """Default the flag OFF for this file; individual tests opt in with "1".

    The flag now defaults ON in prod, so isolating these gate tests to a known-OFF
    baseline requires setting the explicit off-token — an unset var reads as ON."""
    monkeypatch.setenv(FLAG, "0")


# ── tests ────────────────────────────────────────────────────────────────────────


def test_explain_narrates_from_record_with_labels(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    store = _FakeArtifactStore()
    metadata = _metadata()
    _seed_agent(store, metadata)
    chat = _FakeChat(boundary="explain", reply="It hurt retention because the gate stalled early play.")

    svc = GroundedAgentChatService(store=store, chat_client=chat)
    result = svc.send_message(metadata, "Why did the gate hurt retention?", _record())

    assert result.boundary == "explain"
    assert result.recompute_needed is False
    assert result.turn.role == AgentRole.AGENT
    assert result.turn.content == "It hurt retention because the gate stalled early play."

    # The record's mechanism + direction context reached the LLM, and the two
    # interaction labels are present in the system-supplement.
    supplement = next(
        m["content"]
        for m in chat.chat_calls[0]
        if m["role"] == "system" and "GROUNDING CONTRACT" in m["content"]
    )
    assert "gate at level 30 vs gate at level 40" in supplement  # mechanism shift
    assert "day7_retention" in supplement  # outcome
    assert "negative" in supplement  # computed direction
    assert LABEL_PER_SEGMENT in supplement
    assert LABEL_CALIBRATED_FICTION in supplement
    # Anti-drift guard spirit is preserved alongside the supplement.
    assert any(m["content"] == _CHAT_GUARD_PREFIX for m in chat.chat_calls[0])

    # Persistence: PM turn then agent turn, both written.
    lines = store.read_lines(f"{AgentMemory._base_key(metadata)}/conversation.jsonl")
    assert len(lines) == 2


def test_new_whatif_signals_recompute_without_fabricating(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    store = _FakeArtifactStore()
    metadata = _metadata()
    _seed_agent(store, metadata)
    chat = _FakeChat(boundary="new_whatif", reply="SHOULD NOT BE USED")

    svc = GroundedAgentChatService(store=store, chat_client=chat)
    result = svc.send_message(
        metadata, "What if we moved the gate to level 50 instead?", _record()
    )

    assert result.boundary == "new_whatif"
    assert result.recompute_needed is True
    # The role-play LLM was NEVER called for a prediction (only the classifier ran).
    assert chat.chat_calls == []
    assert len(chat.json_calls) == 1
    # No fabricated number/direction — just the recompute nudge.
    assert "re-run the grounded simulation" in result.turn.content
    assert "won't guess" in result.turn.content
    # Still persisted consistently (PM + agent nudge).
    lines = store.read_lines(f"{AgentMemory._base_key(metadata)}/conversation.jsonl")
    assert len(lines) == 2


def test_classifier_never_raises_on_exploding_client_defaults_safe():
    # No env / client resolution needed — the exploding client short-circuits.
    boundary = classify_pm_message(
        "anything at all", _record(), chat_client=_ExplodingChat()
    )
    assert boundary == "new_whatif"  # SAFE branch — never a guessed what-if answer


def test_explain_llm_failure_persists_nothing(monkeypatch):
    """LLM-fail on the role-play call → nothing half-written (codex #52 ordering)."""
    monkeypatch.setenv(FLAG, "1")
    store = _FakeArtifactStore()
    metadata = _metadata()
    _seed_agent(store, metadata)

    class _ClassifyExplainThenExplode:
        # classifier succeeds → "explain"; the role-play chat() explodes.
        def chat_json(self, messages, schema, **kwargs):  # noqa: ANN001
            return schema(boundary="explain", rationale="stub")

        def chat(self, messages, **kwargs):  # noqa: ANN001
            raise RuntimeError("boom-roleplay")

    svc = GroundedAgentChatService(store=store, chat_client=_ClassifyExplainThenExplode())
    with pytest.raises(RuntimeError):
        svc.send_message(metadata, "Why did it help?", _record())

    # Nothing persisted — the conversation.jsonl was never written.
    with pytest.raises(FileNotFoundError):
        store.read_lines(f"{AgentMemory._base_key(metadata)}/conversation.jsonl")


def test_flag_off_uses_unchanged_roleplay_path(monkeypatch):
    """Flag OFF → delegates to AgentChatService; record ignored; no grounding supplement.

    Explicit off-token (not delenv): an unset var now reads as ON by default."""
    monkeypatch.setenv(FLAG, "0")
    store = _FakeArtifactStore()
    metadata = _metadata()
    _seed_agent(store, metadata)
    chat = _FakeChat(boundary="explain", reply="Plain role-play answer.")

    svc = GroundedAgentChatService(store=store, chat_client=chat)
    result = svc.send_message(metadata, "Why did it help?", _record())

    assert result.boundary == "disabled"
    assert result.recompute_needed is False
    assert result.turn.content == "Plain role-play answer."
    # The classifier never ran, and NO grounding supplement reached the LLM.
    assert chat.json_calls == []
    assert len(chat.chat_calls) == 1
    assert all("GROUNDING CONTRACT" not in m["content"] for m in chat.chat_calls[0])
    # The base guard prefix is still there (unchanged path).
    assert any(m["content"] == _CHAT_GUARD_PREFIX for m in chat.chat_calls[0])


def test_from_decision_projects_record():
    """GroundedRecord.from_decision pulls mechanism + verdict + candidate context."""
    from sidira_simulator.schemas.estimability import CandidateEffect
    from sidira_simulator.schemas.mechanism import MechanismSpec
    from sidira_simulator.services.decision_flow import DecisionResult
    from sidira_simulator.services.grounded_predictor import GroundedPrediction

    spec = MechanismSpec(
        capability_name="onboarding_gate",
        treatment_column="gate_level",
        treatment_contrast="gate 30 vs gate 40",
        outcome_column="day7_retention",
        mediator="early_session_count",
    )
    candidate = CandidateEffect(
        treatment="gate_level",
        outcome="day7_retention",
        covariates=["recency"],
        supportable=True,
        n_treat=900,
        n_control=910,
        sign_adjusted="negative",
    )
    grounded = GroundedPrediction(
        covered=True, direction="negative", supportable=True, candidate=candidate, reason="matched"
    )
    decision = DecisionResult(
        source="grounded",
        direction="negative",
        caution="none",
        label="verified — data overrides intuition",
        watchdog_verdict="CONTRADICTS",
        mechanism_spec=spec,
        grounded=grounded,
        reason="trace",
    )

    record = GroundedRecord.from_decision(decision)
    assert record.capability_name == "onboarding_gate"
    assert record.treatment_column == "gate_level"
    assert record.outcome_column == "day7_retention"
    assert record.mediator == "early_session_count"
    assert record.direction == "negative"
    assert record.is_grounded_verdict is True
    assert record.covered is True
    assert record.supportable is True
    assert record.n_treat == 900 and record.n_control == 910
    assert "negative" in record.counterfactual_summary
    assert "treated n=900" in record.segment_context


def test_classify_explain_vs_whatif_routes(monkeypatch):
    """The classifier returns whatever the judge decides (both branches)."""
    monkeypatch.delenv(FLAG, raising=False)  # classifier is flag-independent
    assert (
        classify_pm_message("why did it help?", _record(), chat_client=_FakeChat(boundary="explain"))
        == "explain"
    )
    assert (
        classify_pm_message(
            "what if we changed the outcome?", _record(), chat_client=_FakeChat(boundary="new_whatif")
        )
        == "new_whatif"
    )


def test_module_exports():
    assert hasattr(mod, "GroundedAgentChatService")
    assert hasattr(mod, "GroundedChatResult")
