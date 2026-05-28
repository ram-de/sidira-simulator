"""Unit tests for memory.feedback_log (#56).

Pin the append-only-with-latest-wins contract independently of the API
tests. The clear-thumb case (realistic_flag=None overwriting prior 👍/👎)
is the load-bearing one for the third-state toggle UX.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from sidira_simulator.adapters.r2 import LocalArtifactStore
from sidira_simulator.memory.feedback_log import FeedbackLog
from sidira_simulator.schemas.feedback import FeedbackEvent, FeedbackTargetKind


@pytest.fixture
def store(tmp_path: Path) -> LocalArtifactStore:
    return LocalArtifactStore(tmp_path)


def _ev(
    target_kind: FeedbackTargetKind,
    target_id: str,
    turn_index: int,
    realistic_flag: bool | None,
    *,
    when: datetime | None = None,
) -> FeedbackEvent:
    return FeedbackEvent(
        target_kind=target_kind,
        target_id=target_id,
        turn_index=turn_index,
        realistic_flag=realistic_flag,
        created_at=when or datetime.now(timezone.utc),
    )


def test_empty_log_reads_empty(store) -> None:
    flog = FeedbackLog(store)
    assert flog.read_all(customer_id="demo", simulation_id="s1") == []
    assert (
        flog.latest_flags(
            customer_id="demo",
            simulation_id="s1",
            target_kind=FeedbackTargetKind.AGENT,
            target_id="a1",
        )
        == {}
    )


def test_single_event_round_trips(store) -> None:
    flog = FeedbackLog(store)
    flog.append(
        customer_id="demo",
        simulation_id="s1",
        event=_ev(FeedbackTargetKind.AGENT, "a1", 0, True),
    )
    flags = flog.latest_flags(
        customer_id="demo",
        simulation_id="s1",
        target_kind=FeedbackTargetKind.AGENT,
        target_id="a1",
    )
    assert flags == {0: True}


def test_latest_event_wins_for_same_turn(store) -> None:
    flog = FeedbackLog(store)
    # 👍 then 👎 — second wins.
    flog.append(
        customer_id="demo",
        simulation_id="s1",
        event=_ev(FeedbackTargetKind.AGENT, "a1", 2, True),
    )
    flog.append(
        customer_id="demo",
        simulation_id="s1",
        event=_ev(FeedbackTargetKind.AGENT, "a1", 2, False),
    )
    flags = flog.latest_flags(
        customer_id="demo",
        simulation_id="s1",
        target_kind=FeedbackTargetKind.AGENT,
        target_id="a1",
    )
    assert flags == {2: False}


def test_clear_thumb_overwrites_prior_flag(store) -> None:
    """The third-state toggle (👍 → clear) must surface as "no thumb",
    not as the prior 👍. Without this the UI would show stale state."""
    flog = FeedbackLog(store)
    flog.append(
        customer_id="demo",
        simulation_id="s1",
        event=_ev(FeedbackTargetKind.AGENT, "a1", 0, True),
    )
    flog.append(
        customer_id="demo",
        simulation_id="s1",
        event=_ev(FeedbackTargetKind.AGENT, "a1", 0, None),
    )
    flags = flog.latest_flags(
        customer_id="demo",
        simulation_id="s1",
        target_kind=FeedbackTargetKind.AGENT,
        target_id="a1",
    )
    assert flags == {0: None}


def test_different_turns_tracked_independently(store) -> None:
    flog = FeedbackLog(store)
    flog.append(
        customer_id="demo",
        simulation_id="s1",
        event=_ev(FeedbackTargetKind.AGENT, "a1", 0, True),
    )
    flog.append(
        customer_id="demo",
        simulation_id="s1",
        event=_ev(FeedbackTargetKind.AGENT, "a1", 2, False),
    )
    flog.append(
        customer_id="demo",
        simulation_id="s1",
        event=_ev(FeedbackTargetKind.AGENT, "a1", 4, None),
    )
    flags = flog.latest_flags(
        customer_id="demo",
        simulation_id="s1",
        target_kind=FeedbackTargetKind.AGENT,
        target_id="a1",
    )
    assert flags == {0: True, 2: False, 4: None}


def test_different_targets_isolated(store) -> None:
    """An event on agent a1 must not leak into agent a2's flags."""
    flog = FeedbackLog(store)
    flog.append(
        customer_id="demo",
        simulation_id="s1",
        event=_ev(FeedbackTargetKind.AGENT, "a1", 0, True),
    )
    flog.append(
        customer_id="demo",
        simulation_id="s1",
        event=_ev(FeedbackTargetKind.AGENT, "a2", 0, False),
    )
    flags_a1 = flog.latest_flags(
        customer_id="demo",
        simulation_id="s1",
        target_kind=FeedbackTargetKind.AGENT,
        target_id="a1",
    )
    flags_a2 = flog.latest_flags(
        customer_id="demo",
        simulation_id="s1",
        target_kind=FeedbackTargetKind.AGENT,
        target_id="a2",
    )
    assert flags_a1 == {0: True}
    assert flags_a2 == {0: False}


def test_agent_and_persona_group_kinds_isolated(store) -> None:
    """Same simulation, same turn_index, different kinds: each tracked
    on its own. Cross-kind contamination would scramble Phase 9's join."""
    flog = FeedbackLog(store)
    flog.append(
        customer_id="demo",
        simulation_id="s1",
        event=_ev(FeedbackTargetKind.AGENT, "shared-id", 0, True),
    )
    flog.append(
        customer_id="demo",
        simulation_id="s1",
        event=_ev(FeedbackTargetKind.PERSONA_GROUP, "shared-id", 0, False),
    )
    agent_flags = flog.latest_flags(
        customer_id="demo",
        simulation_id="s1",
        target_kind=FeedbackTargetKind.AGENT,
        target_id="shared-id",
    )
    group_flags = flog.latest_flags(
        customer_id="demo",
        simulation_id="s1",
        target_kind=FeedbackTargetKind.PERSONA_GROUP,
        target_id="shared-id",
    )
    assert agent_flags == {0: True}
    assert group_flags == {0: False}


def test_read_all_preserves_append_order(store) -> None:
    """Phase 9 may want the full event history (not just latest). Verify
    read_all returns events in append order so flip-flops are visible."""
    flog = FeedbackLog(store)
    flog.append(
        customer_id="demo",
        simulation_id="s1",
        event=_ev(FeedbackTargetKind.AGENT, "a1", 0, True),
    )
    flog.append(
        customer_id="demo",
        simulation_id="s1",
        event=_ev(FeedbackTargetKind.AGENT, "a1", 0, False),
    )
    flog.append(
        customer_id="demo",
        simulation_id="s1",
        event=_ev(FeedbackTargetKind.AGENT, "a1", 0, True),
    )
    events = flog.read_all(customer_id="demo", simulation_id="s1")
    flags = [e.realistic_flag for e in events]
    assert flags == [True, False, True]


def test_isolated_per_simulation(store) -> None:
    """An event in sim s1 must not surface when reading sim s2."""
    flog = FeedbackLog(store)
    flog.append(
        customer_id="demo",
        simulation_id="s1",
        event=_ev(FeedbackTargetKind.AGENT, "a1", 0, True),
    )
    s2_flags = flog.latest_flags(
        customer_id="demo",
        simulation_id="s2",
        target_kind=FeedbackTargetKind.AGENT,
        target_id="a1",
    )
    assert s2_flags == {}
