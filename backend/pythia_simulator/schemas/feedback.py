"""Calibration feedback schemas (#56).

A PM can flag any reply turn 👍/👎. The signal is what closes the loop on
synthesis/collective quality — the rubric tests catch templating drift,
calibration thumbs catch "is the agent actually helpful?"  Phase 9
consumes this for Layer-3 calibration.

Storage: append-only JSONL at
  `customers/<id>/simulations/<sim_id>/feedback.jsonl`
Latest entry per (target, turn_index) wins on read. `realistic_flag=None`
means the PM cleared their thumb (third-state toggle).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class FeedbackTargetKind(str, Enum):
    """Which reply surface a feedback event applies to.

    `agent`: the per-agent conversation log (`/agents/[id]`). turn_index
      points into that agent's `conversation.jsonl`.
    `persona_group`: the persona-group turn log
      (`/simulations/[id]/personas/[id]/turns.jsonl`). turn_index points
      into that log. Covers BOTH synthesis (fan-out) and collective
      turns — the role lives on the turn itself, not on the feedback.
    """

    AGENT = "agent"
    PERSONA_GROUP = "persona_group"


class FeedbackEvent(BaseModel):
    """One PM 👍/👎 action on a specific reply turn.

    `target_id`:
      - For `agent`: the agent_id (uuid).
      - For `persona_group`: `f"{sim_id}/{persona_id}"`. (We embed sim_id
        + persona_id together so the on-disk JSONL can sit at the sim
        scope and the join key is self-contained.)

    `realistic_flag`:
      - `True`: PM said the reply is realistic / useful (👍).
      - `False`: PM said the reply is off (👎).
      - `None`: PM cleared their thumb. We persist the clear so a later
        replay shows "no feedback" instead of stale 👍/👎.
    """

    target_kind: FeedbackTargetKind
    target_id: str
    turn_index: int = Field(ge=0)
    realistic_flag: bool | None
    created_at: datetime


class FeedbackRequest(BaseModel):
    """PM sets / clears feedback on a turn."""

    realistic_flag: bool | None = Field(
        description=(
            "True = 👍, False = 👎, null = clear. The clear path persists "
            "an event with realistic_flag=null so the latest-wins read "
            "shows no thumb after the user un-flags."
        ),
    )


class FeedbackResponse(BaseModel):
    """Echoed back to the client after a successful POST."""

    target_kind: FeedbackTargetKind
    target_id: str
    turn_index: int
    realistic_flag: bool | None
    created_at: datetime
