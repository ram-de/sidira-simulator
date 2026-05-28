"""SQLAlchemy declarative models — Postgres source of truth.

Heavy artifact contents (identity prompts, conversation logs, full pack JSON) live
in R2. Postgres holds metadata + relationships + audit signals. Schema-version
columns let the simulator tolerate one minor version of pack drift (Phase 2 spec).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Single declarative base for the simulator."""


class Customer(Base):
    """Placeholder until Clerk wires up — Phase 5 populates clerk_org_id."""

    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    clerk_org_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    name: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Simulation(Base):
    """One simulation run. Hypothesis + result_json carry full schemas as JSONB."""

    __tablename__ = "simulations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), index=True)
    persona_pack_version: Mapped[str] = mapped_column(String(64))
    feature_pack_version: Mapped[str] = mapped_column(String(64))
    hypothesis_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    parent_simulation_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("simulations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # Phase 2.5: modeled userbase + cap-derived sample count. Nullable so legacy
    # rows pre-dating the migration round-trip cleanly.
    population_size: Mapped[int | None] = mapped_column(nullable=True)
    sampled_agent_count: Mapped[int | None] = mapped_column(nullable=True)
    # Phase 2.5 (#5): identity_seed RNG seed pinned per run for reproducibility.
    run_seed: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Phase 4.6 (#88): A/B mode treatment fraction. NULL = single-arm sim
    # (today's default). Float in (0, 1) when A/B mode is on; v1 wizard
    # always sends 0.5 (paired sampling makes other values statistically
    # wasteful, but the field stays flexible for future indep-sampling).
    treatment_fraction: Mapped[float | None] = mapped_column(nullable=True)
    # Phase 5 (#101): optional persona-filter applied to this sim. NULL =
    # ran against all personas (today's default). When a non-empty JSON array
    # of persona_ids, the allocator restricted + re-weighted to those before
    # largest-remainder. Denormalized so the result-page cohort banner
    # survives even if the active Persona Pack version changes after the run.
    selected_personas: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=True
    )
    # Phase 5 (#103): model that powered sim-time agent reasoning and
    # classifiers. Nullable so legacy rows round-trip as "backend default".
    model_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    agents: Mapped[list["AgentInstance"]] = relationship(
        back_populates="simulation", cascade="all, delete-orphan"
    )


class AgentInstance(Base):
    """Metadata for one AgentInstance. Identity + reaction + chat live in R2.

    Identity-continuity guarantee (see memory/agent_memory.py): the
    persona_pack_version + persona_id pin this row to a specific frozen identity
    in R2. Re-instantiation from a different pack version produces a different
    AgentInstance — by design.
    """

    __tablename__ = "agent_instances"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    simulation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("simulations.id", ondelete="CASCADE"), index=True
    )
    persona_id: Mapped[str] = mapped_column(String(64), index=True)
    persona_pack_version: Mapped[str] = mapped_column(String(64))
    persona_name: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_active_at: Mapped[datetime] = mapped_column(server_default=func.now())
    message_count: Mapped[int] = mapped_column(default=0)
    # Phase 4.6 #89: A/B mode arm tag. NULL = single-arm sim (today's
    # default; pre-#89 rows round-trip with NULL). "treatment" / "control"
    # for A/B sims. Persisted at materialization time and never changes
    # for the lifetime of the AgentInstance — re-instantiation with a
    # different arm produces a different agent (identity-continuity
    # invariant per memory/agent_memory.py).
    arm: Mapped[str | None] = mapped_column(String(16), nullable=True)

    simulation: Mapped[Simulation] = relationship(back_populates="agents")
    feedback: Mapped[list["AgentFeedback"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )


class AgentFeedback(Base):
    """PM-supplied "realistic / not realistic" flags. Layer-3 training signal."""

    __tablename__ = "agent_feedback"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("agent_instances.id", ondelete="CASCADE"), index=True
    )
    turn_index: Mapped[int] = mapped_column()
    realistic_flag: Mapped[bool] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    agent: Mapped[AgentInstance] = relationship(back_populates="feedback")
