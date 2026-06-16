"""SQLAlchemy declarative models — Postgres source of truth.

Heavy artifact contents (identity prompts, conversation logs, full pack JSON) live
in R2. Postgres holds metadata + relationships + audit signals. Schema-version
columns let the simulator tolerate one minor version of pack drift (Phase 2 spec).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Single declarative base for the simulator."""


class Customer(Base):
    """One tenant. ``id`` is an opaque internal key and is permanent; for
    webhook-provisioned tenants its value equals the Clerk org id (globally
    unique, doubles as the R2 prefix root), but nothing may parse it or assume
    the auth provider can resolve it. ``clerk_org_id`` is the provider mapping
    column that keeps an auth-provider swap a backfill instead of a data
    migration — see docs/auth-provider-portability.md before changing either.
    """

    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    clerk_org_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    name: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    selected_personas: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    # Phase 5 (#103): model that powered sim-time agent reasoning and
    # classifiers. Nullable so legacy rows round-trip as "backend default".
    model_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    agents: Mapped[list["AgentInstance"]] = relationship(
        back_populates="simulation", cascade="all, delete-orphan"
    )


class CrawlConfig(Base):
    """Saved crawl setup for one customer (#171) — the inputs the crawler's
    MVP contract asks the customer to supply (capabilities + entry URLs, sandbox
    tenant, test users per role, cadence, depth). One row per customer; the
    config itself is JSONB validated by schemas/crawl.py:CrawlSetup at the API
    boundary. Crawl *runs* are not modeled here — they arrive with the walker
    (sidira-crawler #1–#3) alongside the trigger endpoint.
    """

    __tablename__ = "crawl_configs"

    customer_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("customers.id", ondelete="CASCADE"), primary_key=True
    )
    config_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CrawlRun(Base):
    """One product-triggered crawl (#193). The crawl itself executes in
    sidira-crawler CI (dispatched via the GitHub API — R2/Groq secrets never
    touch this backend); this row is the dispatch record plus the last
    observed status. ``run_id`` is the GitHub Actions run, correlated after
    dispatch by the ``crawl_id``-bearing run name (workflow_dispatch returns
    no run id). Terminal status/error/snapshot are persisted on the poll
    that first observes them; non-terminal rows refresh from GitHub on read.
    """

    __tablename__ = "crawl_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="pending")
    crawl_date: Mapped[str] = mapped_column(String(10))
    run_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    run_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    snapshot_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FeatureStoreConnection(Base):
    """A saved feature-store connection (#22). One row per connection the
    customer's wizard creates (today: Snowflake only). Sanitized connection
    fields live in their own columns; the password is NEVER stored in
    cleartext — only the serialized envelope-encrypted blob in
    ``password_enc`` (see adapters/credentials.py). GET/list never returns
    the password or the blob.
    """

    __tablename__ = "feature_store_connections"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(256))
    kind: Mapped[str] = mapped_column(String(32))
    account: Mapped[str] = mapped_column(String(256))
    user: Mapped[str] = mapped_column(String(256))
    warehouse: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(256))
    database: Mapped[str] = mapped_column(String(256))
    schema: Mapped[str | None] = mapped_column(String(256), nullable=True)
    # Serialized credentials.EncryptedBlob (base64'd byte fields). Never the
    # cleartext password.
    password_enc: Mapped[dict[str, Any]] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    # Per-connection HEALTH (#328). Persisted outcome of the last connectivity
    # test (POST /{id}/test) so the saved-connections register (#327) can show a
    # last-known state in words. All NULLABLE: a row that has never been tested
    # reads as UNTESTED. ``last_test_status`` is 'ok' | 'failed';
    # ``last_error_kind`` mirrors the connectivity-error classification
    # ('auth' | 'permission' | 'network' | 'unknown'). Never a credential.
    last_tested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_test_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_error_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class PersonaBuildRun(Base):
    """One persona-pack build (#24). The build executes as a BackgroundTask:
    load the saved feature-store connection's creds, run the source query,
    invoke the sidira-personas pipeline, and write the resulting pack to R2 at
    ``customers/<id>/personas/v_<N>/persona_pack.json``. This row is the
    dispatch record plus the last observed status; the live progress + JSONL
    event log live alongside the artifacts in R2 (RunStateStore). ``pack_version``
    is set only on success; ``error`` carries the failure reason (including a
    stability-gate failure below ``stability_threshold``).
    """

    __tablename__ = "persona_build_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    connection_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    pack_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stability_score: Mapped[float | None] = mapped_column(nullable=True)
    persona_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Serialized BuildConfig (#268 Phase 2): the dispatch payload the worker
    # reconstructs to run the build. Nullable so pre-worker rows stay valid.
    config_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    message_count: Mapped[int] = mapped_column(default=0)
    # Phase 5a #68: total materialization order within a simulation. This
    # preserves the runner/allocation order when Postgres returns agent lists.
    materialization_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    agent: Mapped[AgentInstance] = relationship(back_populates="feedback")
