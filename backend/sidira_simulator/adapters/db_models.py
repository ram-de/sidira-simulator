"""SQLAlchemy declarative models — Postgres source of truth.

Heavy artifact contents (identity prompts, conversation logs, full pack JSON) live
in R2. Postgres holds metadata + relationships + audit signals. Schema-version
columns let the simulator tolerate one minor version of pack drift (Phase 2 spec).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
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
    # #215/#245 PR 3a: which crawl setup's Feature Pack this sim resolved its
    # capability from. NOT NULL with a server default so migration 017 backfills
    # every existing sim to the "default" setup (no data loss) and the loader
    # resolves the EXACT legacy prefix for them — byte-identical to pre-#215. A
    # sim built from a named setup persists that setup_id so re-runs / detail
    # resolve the same pack the PM authored against.
    setup_id: Mapped[str] = mapped_column(String(64), server_default="default")
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
    """Saved crawl setup for one customer (#171, #215/#245) — the inputs the
    crawler's MVP contract asks the customer to supply (capabilities + entry
    URLs, sandbox tenant, test users per role, cadence, depth). The config
    itself is JSONB validated by schemas/crawl.py:CrawlSetup at the API
    boundary. Crawl *runs* are not modeled here — they arrive with the walker
    (sidira-crawler #1–#3) alongside the trigger endpoint.

    Keyed by ``(customer_id, setup_id)``: an org may hold multiple crawl
    targets ("setups"), each a separate product. Every existing endpoint
    operates on the ``"default"`` setup (migration 015 backfilled the prior
    single row to ``setup_id="default"``); multi-setup CRUD + dispatch
    threading land in later PRs of the #215/#245 epic.
    """

    __tablename__ = "crawl_configs"

    customer_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("customers.id", ondelete="CASCADE"), primary_key=True
    )
    # A product/crawl target within the org. Existing single-target tenants use
    # the reserved "default" setup; later PRs mint additional ids for extra
    # products. NOT NULL with a server default so old single-key callers and the
    # backfilled prod row both resolve to "default".
    setup_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, server_default="default"
    )
    # Human-readable label for the setup (used by the PR2 CRUD/list UI).
    # Nullable: the backfilled default row gets "Default"; otherwise optional.
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
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


class ExperimentConnection(Base):
    """A persisted, admin-managed experiment SOURCE (#46). One row per source the
    admin connects (Statsig / SQL / CSV). Mirrors ``FeatureStoreConnection``: the
    non-secret display config (host/database/project/query + the confirmed field
    mapping) lives in ``display_config``; the source credentials are NEVER stored
    in cleartext — only the serialized envelope-encrypted blob in
    ``credentials_enc``, AAD-bound to ``customer_id:id`` (see
    adapters/credentials.py). GET/list never returns the credentials or the blob.

    Refresh model (admin-console council): one-time import on connect + on-demand
    "Re-import" using the stored creds — NEVER live per-query. Each re-import
    writes an ``ExperimentImportRun`` row.
    """

    __tablename__ = "experiment_connections"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(256))
    kind: Mapped[str] = mapped_column(String(32))
    # Non-secret display config (host/database/project/query/delimiter + the
    # confirmed FieldMapping). NEVER a credential.
    display_config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # Serialized credentials.EncryptedBlob (base64'd byte fields). NULL for the
    # CSV kind (no secret). Never the cleartext credentials.
    credentials_enc: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(16), server_default="connected")
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_import_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    import_runs: Mapped[list["ExperimentImportRun"]] = relationship(
        back_populates="connection", cascade="all, delete-orphan"
    )


class ExperimentImportRun(Base):
    """One import run against an :class:`ExperimentConnection` (#46) — the initial
    import on connect or an on-demand re-import. Records the start/finish, the
    imported/failed row counts, the terminal status, and a CUSTOMER-SAFE error
    (never a raw driver/transport string that could carry a credential — #488).
    Cascades when its parent connection is deleted.
    """

    __tablename__ = "experiment_import_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    connection_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("experiment_connections.id", ondelete="CASCADE"),
        index=True,
    )
    customer_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(16))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    imported_count: Mapped[int] = mapped_column(Integer, server_default="0")
    failed_count: Mapped[int] = mapped_column(Integer, server_default="0")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    connection: Mapped["ExperimentConnection"] = relationship(back_populates="import_runs")


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


class ArchivedFeaturePack(Base):
    """A soft-delete marker hiding one Feature Pack VERSION from the Library (#214).

    Feature packs live in R2 (``customers/<id>/featurepacks/<version>/``), not in a
    DB row — they are GENERATED, NEVER AUTHORED. This table is the ONLY DB presence
    a pack version gets, and it carries a single fact: "this customer archived this
    version." Archiving is a soft-delete — it HIDES the version from the Library, it
    NEVER deletes the R2 artifacts and NEVER changes pack content (that would corrupt
    the control arm).

    Critically, this marker is read ONLY by the Library-listing endpoints. Pack
    resolution for RUNNING a simulation (``FeaturePackLoader.load_manifest_at_version``
    / ``load_capability``) NEVER consults it, so a historical simulation that froze an
    archived version still resolves and replays. Archive hides; it does not break.

    One row per (customer, version): the presence of the row means archived, its
    absence means visible. Unarchiving deletes the row.
    """

    __tablename__ = "archived_feature_packs"

    customer_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("customers.id", ondelete="CASCADE"), primary_key=True
    )
    pack_version: Mapped[str] = mapped_column(String(64), primary_key=True)
    archived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
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


class Conversation(Base):
    """One persistent "Ask the archive" thread (#41).

    A multi-turn conversation the PM holds with the fused archive. Tenant-scoped
    via ``customer_id`` (CASCADE on tenant delete, mirroring every other per-
    tenant table). ``title`` is Claude-style: NULL until the first turn lands,
    then auto-derived from the first question (and editable via PATCH). Ordered
    turns live in ``conversation_turns`` (Q + A + per-answer citations); the
    PREDICTED/MEASURED firewall lives in the persisted citation JSON, untouched.
    """

    __tablename__ = "conversations"
    # Composite unique on (id, customer_id) so a child turn's composite FK can
    # target it — the DB backstop that a turn can never cross tenants.
    __table_args__ = (
        UniqueConstraint(
            "id", "customer_id", name="uq_conversations_id_customer_id"
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    # Per-USER (private) scope (#42): the Clerk session `sub`, distinct from the
    # org-level customer_id. Conversations are scoped by BOTH (customer_id is the
    # outer tenant boundary; user_id is the inner private boundary), so a user can
    # never see another user's thread even within the same org. NULLABLE only for
    # back-compat with legacy rows created before #42 (a pre-#42 demo thread);
    # every NEW row always stamps a concrete user_id. Legacy NULL-user rows are
    # treated as ORG-VISIBLE (visible to any user in the owning tenant) so the
    # pre-existing demo thread isn't orphaned — see ConversationRepo for the
    # read/write predicate that encodes this.
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # NULL until the first turn auto-titles it (or the user renames). The UI shows
    # a placeholder ("New conversation") for an untitled, empty thread.
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Bumped on every appended turn + on rename, so list-newest-first surfaces the
    # most recently touched thread at the top (the "restore last-active" anchor).
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    turns: Mapped[list["ConversationTurn"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationTurn.turn_index",
        # conversation_turns has TWO FK paths to conversations — the single-column
        # conversation_id FK AND the composite (conversation_id, customer_id) FK
        # added for tenant integrity. Pin the ORM join to conversation_id so the
        # mapper can configure (otherwise: AmbiguousForeignKeysError → every
        # conversation op 500s). The composite FK stays as a DB-level guard.
        foreign_keys="[ConversationTurn.conversation_id]",
    )


class ConversationTurn(Base):
    """One (question, answer) exchange persisted in a thread (#41).

    ``citations_json`` stores the per-answer fused citations verbatim (the
    MEASURED/PREDICTED source word + pre-formatted effect label) so a reloaded
    thread re-renders byte-identical evidence without re-querying — the firewall
    state rides the stored JSON. ``turn_index`` is a 0-based per-conversation
    ordinal so history replays in the exact order it was asked.
    """

    __tablename__ = "conversation_turns"
    __table_args__ = (
        # Composite FK: (conversation_id, customer_id) MUST match a real
        # (id, customer_id) on conversations, so a turn can never reference a
        # conversation of another tenant at the DB level.
        ForeignKeyConstraint(
            ["conversation_id", "customer_id"],
            ["conversations.id", "conversations.customer_id"],
            ondelete="CASCADE",
            name="fk_conversation_turns_conversation_customer",
        ),
        # At most one turn per (conversation_id, turn_index): concurrent appends
        # can't persist ambiguous ordering. next_index is computed in Python, so
        # a rare collision surfaces as an IntegrityError (clean retry) not a dup.
        UniqueConstraint(
            "conversation_id",
            "turn_index",
            name="uq_conversation_turns_conversation_id_turn_index",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    # Denormalized tenant id so a turn read can be customer-scoped without a join.
    customer_id: Mapped[str] = mapped_column(String(64), index=True)
    turn_index: Mapped[int] = mapped_column(Integer)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    # Per-answer fused citations (list of {id, source, change_description, metric,
    # effect_label}); [] when the answer cited nothing.
    citations_json: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    used_llm: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    conversation: Mapped[Conversation] = relationship(
        back_populates="turns",
        # Same disambiguation as Conversation.turns: join on the single-column FK,
        # not the composite (conversation_id, customer_id) integrity constraint.
        foreign_keys="[ConversationTurn.conversation_id]",
    )
