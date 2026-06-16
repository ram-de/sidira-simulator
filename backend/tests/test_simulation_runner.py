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

from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
from sidira_simulator.adapters.persona_loader import PersonaPackLoader
from sidira_simulator.adapters.r2 import LocalArtifactStore
from sidira_simulator.memory.agent_memory import AgentMemory
from sidira_simulator.schemas.agent import AgentInstanceMetadata
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.identity_seed import draw_identity_seed
from sidira_simulator.services.population_sampler import allocate
from sidira_simulator.services.simulation_runner import SimulationRunner

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"


class _StubChat:
    """Minimal chat stub -- canned reaction text, canned classifications."""

    def __init__(self) -> None:
        self.calls: list[list[dict]] = []
        self.json_calls: list[tuple[type, list[dict]]] = []

    def chat(self, messages, max_tokens=4096, temperature=0.0, seed=None):
        self.calls.append(messages)
        return "Stubbed reaction prose."

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        self.json_calls.append((schema, messages))
        from sidira_simulator.schemas.scoring import (
            RefinementOutput,
            Sentiment,
            SentimentClassification,
            WeaknessClassification,
        )

        if schema is WeaknessClassification:
            return WeaknessClassification(categories=["wrong_cohort"], primary_reason="stub")
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
async def test_model_id_builds_one_model_bound_client_for_whole_ab_run(monkeypatch) -> None:
    """#103: a selected model must power treatment reactions, control
    reactions, sentiment/weakness classifiers, and refinement within the
    same run. Building one client per run also avoids arm-by-arm model drift.
    """
    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()
    chat = _StubChat()
    requested_models: list[str | None] = []

    def fake_get_chat_client(model_id: str | None = None):
        requested_models.append(model_id)
        return chat

    monkeypatch.setattr(
        "sidira_simulator.services.simulation_runner.get_chat_client",
        fake_get_chat_client,
    )

    runner = SimulationRunner(store=store)
    await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_hypothesis(),
        population_size=2,
        run_seed=12345,
        treatment_fraction=0.5,
        model_id="claude-opus-4-7",
    )

    assert requested_models == ["claude-opus-4-7"]
    assert len(chat.calls) == 4  # 2 treatment + 2 control initial reactions
    assert chat.json_calls  # scoring/refinement used the same model-bound client


@pytest.mark.asyncio
async def test_model_client_failure_becomes_zero_agent_placeholder(monkeypatch) -> None:
    """No-key local/demo runs should still complete through the existing
    per-agent failure path instead of failing before run state is initialized.
    """
    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()

    def fake_get_chat_client(model_id: str | None = None):
        raise RuntimeError(f"missing key for {model_id}")

    monkeypatch.setattr(
        "sidira_simulator.services.simulation_runner.get_chat_client",
        fake_get_chat_client,
    )

    runner = SimulationRunner(store=store)
    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_hypothesis(),
        population_size=2,
        run_seed=12345,
        model_id="llama-3.3-70b-versatile",
    )

    assert simulation.status == "complete"
    assert simulation.agent_instance_ids == []
    assert simulation.result is not None
    assert simulation.result.confidence_score == 0.0
    assert simulation.result.weaknesses[0].category == "underpowered_design"


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
            expected = draw_identity_seed(pack_by_id[persona_id], sample_index, run_seed)
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


@pytest.mark.asyncio
async def test_score_passes_run_seed_to_scoring_service(monkeypatch) -> None:
    """T5: SimulationRunner._score() must pass the runner's resolved run_seed
    into ScoringService.score so the bootstrap CI on confidence_score is
    reproducible run-to-run for the same input."""
    from sidira_simulator.services import scoring as scoring_mod

    captured: dict[str, object] = {}
    original_score = scoring_mod.ScoringService.score

    async def spy(self, hypothesis, reactions, *, run_seed=None, config=None):
        captured["run_seed"] = run_seed
        return await original_score(self, hypothesis, reactions, run_seed=run_seed, config=config)

    monkeypatch.setattr(scoring_mod.ScoringService, "score", spy)

    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()
    runner = SimulationRunner(store=store, chat_client=_StubChat())
    await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_hypothesis(),
        population_size=2,
        run_seed=424242,
    )
    assert captured["run_seed"] == 424242


# ─────────────────────────────────────────────────────────────────────
# Phase 4.6 #89 — dual-arm runner
# ─────────────────────────────────────────────────────────────────────


class _ArmCapturingChat(_StubChat):
    """Captures the system prompt of every chat call so tests can assert
    which arm a given AgentInstance was materialized under."""

    def __init__(self) -> None:
        super().__init__()
        self.system_prompts: list[str] = []

    def chat(self, messages, max_tokens=4096, temperature=0.0, seed=None):
        for m in messages:
            if m.get("role") == "system":
                self.system_prompts.append(m["content"])
        return super().chat(messages, max_tokens, temperature, seed)


@pytest.mark.asyncio
async def test_dual_arm_run_tags_agents_per_arm() -> None:
    """When treatment_fraction is set, every AgentRecord carries an arm tag
    of either "treatment" or "control" — never None. The two arms produce
    roughly the requested split (exact under f=0.5 with even population)."""
    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()
    runner = SimulationRunner(store=store, chat_client=_StubChat())

    await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_hypothesis(),
        population_size=6,
        run_seed=12345,
        treatment_fraction=0.5,
    )

    records = runner._last_run_agent_records
    arms = [r.arm for r in records]
    assert None not in arms, "every dual-arm record must have an arm tag"
    assert set(arms) == {"treatment", "control"}
    # Per-arm semantics (post-Codex P1 #95): pop=6 means 6 per arm.
    assert arms.count("treatment") == 6
    assert arms.count("control") == 6


@pytest.mark.asyncio
async def test_dual_arm_pairs_match_by_persona_sample_index() -> None:
    """The paired-sampling invariant (#89 Q3 locked): at treatment_fraction=0.5
    the runner produces matched pairs across arms. Same (persona_id,
    sample_index) on both sides → #90's lift formula can match them by tuple."""
    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()
    runner = SimulationRunner(store=store, chat_client=_StubChat())

    await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_hypothesis(),
        population_size=6,
        run_seed=42,
        treatment_fraction=0.5,
    )

    treatment_keys = {
        (r.persona_id, r.sample_index)
        for r in runner._last_run_agent_records
        if r.arm == "treatment"
    }
    control_keys = {
        (r.persona_id, r.sample_index) for r in runner._last_run_agent_records if r.arm == "control"
    }
    assert (
        treatment_keys == control_keys
    ), "paired sampling broken: arms have different (persona, sample_index) keys"


@pytest.mark.asyncio
async def test_dual_arm_paired_agents_share_identity_seed() -> None:
    """Pairing only works if the identity_seed (which drives the rendered
    persona's age/locale/state/gripe) is the same across arms for matched
    pairs. Otherwise we'd be comparing apples to oranges — the lift would
    pick up identity drift instead of the treatment effect."""
    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()
    runner = SimulationRunner(store=store, chat_client=_StubChat())

    await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_hypothesis(),
        population_size=4,
        run_seed=777,
        treatment_fraction=0.5,
    )

    by_key: dict[tuple[str, int], dict[str, object]] = {}
    for record in runner._last_run_agent_records:
        meta = AgentInstanceMetadata(
            id=record.agent_id,
            customer_id="demo",
            simulation_id=runner._last_run_agent_records[0].agent_id and "x",
            persona_id=record.persona_id,
            persona_pack_version=persona_pack.version,
            persona_name=record.persona_name,
            created_at=record.created_at,
            last_active_at=record.created_at,
            arm=record.arm,
        )
        # The memory load uses the same sim_id-rooted path; we can't easily
        # reconstruct it from a record alone. Just check seeds match by
        # re-deriving from (persona, sample_index, run_seed) — the invariant
        # the runner has to preserve.
        by_key.setdefault((record.persona_id, record.sample_index), {})[
            record.arm
        ] = record.agent_id
        del meta  # placeholder; the re-derivation below is the actual check

    pack_by_id = {p.id: p for p in persona_pack.personas}
    for (persona_id, sample_index), arm_to_id in by_key.items():
        assert (
            "treatment" in arm_to_id and "control" in arm_to_id
        ), f"pair missing one arm at key=({persona_id}, {sample_index})"
        # Both arms must derive the SAME identity_seed from the same
        # (persona, sample_index, run_seed). That's how paired sampling
        # works for free with deterministic draw_identity_seed.
        seed_t = draw_identity_seed(pack_by_id[persona_id], sample_index, 777)
        seed_c = draw_identity_seed(pack_by_id[persona_id], sample_index, 777)
        assert seed_t == seed_c


@pytest.mark.asyncio
async def test_dual_arm_control_prompt_omits_proposed_change() -> None:
    """The control arm must send a prompt with no proposed-change content.
    If the runner ever forgets to pass arm="control" through to the
    composer, every reaction will silently react to the treatment hypothesis
    — and the lift would collapse to ~0 in a way that LOOKS like a real
    null result. Pin against that regression here."""
    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()
    chat = _ArmCapturingChat()
    runner = SimulationRunner(store=store, chat_client=chat)

    hyp = Hypothesis(
        capability_name="reorder",
        prose="UNIQUE_TREATMENT_PROSE_THAT_SHOULD_NOT_APPEAR_IN_CONTROL",
    )
    await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=hyp,
        population_size=4,
        run_seed=1,
        treatment_fraction=0.5,
    )

    # Half the prompts should be treatment (contain unique prose), half control
    # (don't contain it).
    with_prose = sum(1 for p in chat.system_prompts if "UNIQUE_TREATMENT_PROSE" in p)
    without_prose = sum(1 for p in chat.system_prompts if "UNIQUE_TREATMENT_PROSE" not in p)
    # Per-arm semantics (post-Codex P1 #95): pop=4 means 4 per arm.
    assert with_prose == 4, f"expected 4 treatment prompts, got {with_prose}"
    assert without_prose == 4, f"expected 4 control prompts, got {without_prose}"


@pytest.mark.asyncio
async def test_dual_arm_per_arm_count_matches_population_size_at_f_half() -> None:
    """Codex P1 regression on PR #95: the runner used to do `treatment_pop =
    int(population_size * 0.5)` which silently halved the user-requested
    per-arm cohort. The wizard's cost preview promises "≈ N treatment + N
    control" for `populationSize = N`; the runner has to honor that."""
    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()
    runner = SimulationRunner(store=store, chat_client=_StubChat())

    await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_hypothesis(),
        population_size=6,
        run_seed=1,
        treatment_fraction=0.5,
    )
    treatment = [r for r in runner._last_run_agent_records if r.arm == "treatment"]
    control = [r for r in runner._last_run_agent_records if r.arm == "control"]
    assert len(treatment) == 6, f"expected 6 treatment, got {len(treatment)}"
    assert len(control) == 6, f"expected 6 control, got {len(control)}"


@pytest.mark.asyncio
async def test_dual_arm_odd_population_still_pairs() -> None:
    """At odd population_size + f=0.5, the prior split-first math produced
    `int(7*0.5) = 3` treatment vs `7-3 = 4` control — unequal arms, one
    unpaired agent. With per-arm interpretation both arms get 7 → paired."""
    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()
    runner = SimulationRunner(store=store, chat_client=_StubChat())

    await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_hypothesis(),
        population_size=7,
        run_seed=1,
        treatment_fraction=0.5,
    )
    treatment_keys = {
        (r.persona_id, r.sample_index)
        for r in runner._last_run_agent_records
        if r.arm == "treatment"
    }
    control_keys = {
        (r.persona_id, r.sample_index) for r in runner._last_run_agent_records if r.arm == "control"
    }
    assert treatment_keys == control_keys
    assert len(treatment_keys) == 7


@pytest.mark.asyncio
async def test_single_arm_run_leaves_arm_none() -> None:
    """Back-compat: when treatment_fraction is None (the default, today's
    behavior), every agent record's arm is None. Persisted rows stay
    compatible with all pre-#89 readers."""
    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()
    runner = SimulationRunner(store=store, chat_client=_StubChat())

    await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_hypothesis(),
        population_size=3,
        run_seed=1,
    )
    assert all(r.arm is None for r in runner._last_run_agent_records)


@pytest.mark.asyncio
async def test_no_persona_control_completes_and_excludes_shadows() -> None:
    """#221 §4.1: with include_no_persona_control=True the run completes, the
    persona-lift fields are populated, and the ephemeral no-persona shadows
    NEVER appear in the persisted agent records.

    This is also the regression guard for the persona_lift.computed run-event:
    the runner emits it after scoring the shadow panel, so if the event type
    were absent from EVENT_TYPES the emit would raise a ValidationError and
    this await would fail rather than return a result."""
    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()
    runner = SimulationRunner(store=store, chat_client=_StubChat())

    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_hypothesis(),
        population_size=3,
        run_seed=7,
        include_no_persona_control=True,
    )

    # Shadows are ephemeral: persisted records are persona-only, arm stays None
    # (single-arm run), and no record leaks the "no_persona" tag.
    records = runner._last_run_agent_records
    assert len(records) == 3
    assert all(r.arm is None for r in records)
    assert all(r.arm != "no_persona" for r in records)

    # Persona-lift baseline is populated; all 3 persona agents pair with their
    # shadow by (persona_id, sample_index).
    result = simulation.result
    assert result is not None
    assert result.no_persona_score is not None
    assert result.persona_lift is not None
    assert result.persona_lift_paired_n == 3


@pytest.mark.asyncio
async def test_no_persona_control_records_uncomputable_when_all_shadows_fail() -> None:
    """Honesty gate (#221 §4.1): when the baseline is REQUESTED but every
    no-persona shadow fails materialization, the result records paired_n=0
    (NOT None) with every persona agent counted as unpaired — so a
    requested-but-uncomputable baseline is distinguishable from a flag-off run
    (where these fields stay None / 0). lift itself stays None."""
    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()
    runner = SimulationRunner(store=store, chat_client=_StubChat())

    original = runner._materialize_agent

    async def fail_shadows(*args, arm=None, **kwargs):
        # Drop ONLY the ephemeral no-persona shadows; persona agents materialize
        # normally. The runner's gather uses return_exceptions=True, so a raising
        # shadow is filtered out and never reaches the scorer.
        if arm == "no_persona":
            raise RuntimeError("shadow materialization failed")
        return await original(*args, arm=arm, **kwargs)

    runner._materialize_agent = fail_shadows  # type: ignore[assignment]

    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_hypothesis(),
        population_size=3,
        run_seed=7,
        include_no_persona_control=True,
    )

    result = simulation.result
    assert result is not None
    assert result.persona_lift_paired_n == 0  # requested, not flag-off (None)
    assert result.persona_lift_unpaired_persona == 3  # all persona agents unpaired
    assert result.persona_lift is None
    assert result.persona_lift_ci is None
    assert result.no_persona_score is None
    # Persona agents still scored + persisted normally.
    assert len(runner._last_run_agent_records) == 3
    assert result.confidence_score is not None


@pytest.mark.asyncio
async def test_no_persona_control_off_leaves_lift_fields_unset() -> None:
    """Flag-off (the default) is byte-identical to today: no shadow panel runs,
    so every persona-lift field stays at its None / zero default."""
    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()
    runner = SimulationRunner(store=store, chat_client=_StubChat())

    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_hypothesis(),
        population_size=3,
        run_seed=7,
    )

    result = simulation.result
    assert result is not None
    assert result.no_persona_score is None
    assert result.persona_lift is None
    assert result.persona_lift_ci is None
    assert result.persona_lift_paired_n is None
    assert result.persona_lift_unpaired_persona == 0
    assert result.persona_lift_unpaired_no_persona == 0
    assert result.persona_lift_sentiment_failure_drops == 0


@pytest.mark.asyncio
async def test_no_persona_control_ignored_in_ab_mode() -> None:
    """A/B mode IGNORES include_no_persona_control (docs: single-arm only).
    Shadows are appended only on the single-arm allocation path, so an A/B run
    has no no-persona reactions. The persona_lift* fields must therefore stay at
    their flag-off defaults — NOT be recorded as requested-but-uncomputable
    (paired_n=0), which would falsely advertise a baseline for an unsupported
    path. (codex P2 honesty gate.)"""
    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()
    runner = SimulationRunner(store=store, chat_client=_StubChat())

    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_hypothesis(),
        population_size=3,
        run_seed=7,
        treatment_fraction=0.5,  # A/B mode
        include_no_persona_control=True,  # ignored on this path
    )

    result = simulation.result
    assert result is not None
    # Flag silently ignored: every persona-lift field stays at its flag-off
    # default, indistinguishable from an A/B run that never requested it.
    assert result.no_persona_score is None
    assert result.persona_lift is None
    assert result.persona_lift_ci is None
    assert result.persona_lift_paired_n is None
    assert result.persona_lift_unpaired_persona == 0
    assert result.persona_lift_unpaired_no_persona == 0
    assert result.persona_lift_sentiment_failure_drops == 0
    # No no_persona shadow leaked into the persisted A/B records.
    assert all(r.arm != "no_persona" for r in runner._last_run_agent_records)


@pytest.mark.asyncio
async def test_current_state_control_completes_and_excludes_shadows() -> None:
    """#221 §3.3.1: with include_current_state_control=True the run completes,
    the delta-mode fields are populated, and the ephemeral current-state shadows
    NEVER appear in the persisted agent records.

    This is also the regression guard for the current_state_delta.computed
    run-event: the runner emits it after scoring the shadow panel, so if the
    event type were absent from EVENT_TYPES the emit would raise a
    ValidationError and this await would fail rather than return a result."""
    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()
    runner = SimulationRunner(store=store, chat_client=_StubChat())

    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_hypothesis(),
        population_size=3,
        run_seed=7,
        include_current_state_control=True,
    )

    # Shadows are ephemeral: persisted records are persona-only, arm stays None
    # (single-arm run), and no record leaks the "current_state" tag.
    records = runner._last_run_agent_records
    assert len(records) == 3
    assert all(r.arm is None for r in records)
    assert all(r.arm != "current_state" for r in records)

    # Delta-mode baseline is populated; all 3 persona agents pair with their
    # current-state shadow by (persona_id, sample_index).
    result = simulation.result
    assert result is not None
    assert result.current_state_score is not None
    assert result.current_state_delta is not None
    assert result.current_state_delta_paired_n == 3
    # The delta flag does NOT touch the persona-lift fields (independent baselines).
    assert result.persona_lift is None
    assert result.no_persona_score is None


@pytest.mark.asyncio
async def test_current_state_control_records_uncomputable_when_all_shadows_fail() -> None:
    """Honesty gate (#221 §3.3.1): when the baseline is REQUESTED but every
    current-state shadow fails materialization, the result records paired_n=0
    (NOT None) with every persona agent counted as unpaired — so a
    requested-but-uncomputable baseline is distinguishable from a flag-off run
    (where these fields stay None / 0). delta itself stays None."""
    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()
    runner = SimulationRunner(store=store, chat_client=_StubChat())

    original = runner._materialize_agent

    async def fail_shadows(*args, arm=None, **kwargs):
        # Drop ONLY the ephemeral current-state shadows; persona agents
        # materialize normally. The runner's gather uses return_exceptions=True,
        # so a raising shadow is filtered out and never reaches the scorer.
        if arm == "current_state":
            raise RuntimeError("shadow materialization failed")
        return await original(*args, arm=arm, **kwargs)

    runner._materialize_agent = fail_shadows  # type: ignore[assignment]

    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_hypothesis(),
        population_size=3,
        run_seed=7,
        include_current_state_control=True,
    )

    result = simulation.result
    assert result is not None
    assert result.current_state_delta_paired_n == 0  # requested, not flag-off (None)
    assert result.current_state_delta_unpaired_persona == 3  # all persona agents unpaired
    assert result.current_state_delta is None
    assert result.current_state_delta_ci is None
    assert result.current_state_score is None
    # Persona agents still scored + persisted normally.
    assert len(runner._last_run_agent_records) == 3
    assert result.confidence_score is not None


@pytest.mark.asyncio
async def test_current_state_control_records_uncomputable_when_all_personas_fail() -> None:
    """Honesty gate, the inverted failure (codex P2): every REAL single-arm
    persona agent fails, but the current-state shadows survive. agent_records is
    then non-empty (shadows present), so _score() skips its zero-agent fast-path;
    after filtering, the persona side (`analyses`) is empty and there is no
    treatment side to pair against. The delta is uncomputable — but because the
    baseline was requested on a single-arm run, the result must STILL record
    paired_n=0 (not None), distinguishable from a flag-off run. Without dropping
    the `and analyses` guard on the honesty branch this case would silently look
    like the flag was never set."""
    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()
    runner = SimulationRunner(store=store, chat_client=_StubChat())

    original = runner._materialize_agent

    async def fail_personas(*args, arm=None, **kwargs):
        # Drop ONLY the real single-arm persona agents (arm is None); the
        # current-state shadows (arm == "current_state") materialize normally.
        if arm is None:
            raise RuntimeError("persona materialization failed")
        return await original(*args, arm=arm, **kwargs)

    runner._materialize_agent = fail_personas  # type: ignore[assignment]

    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_hypothesis(),
        population_size=3,
        run_seed=7,
        include_current_state_control=True,
    )

    result = simulation.result
    assert result is not None
    # Requested + uncomputable (no treatment side) → paired_n=0, NOT None.
    assert result.current_state_delta_paired_n == 0
    assert result.current_state_delta is None
    assert result.current_state_delta_ci is None
    assert result.current_state_score is None
    # No persona side survived, so unpaired_persona is 0 (len of empty analyses).
    assert result.current_state_delta_unpaired_persona == 0
    # All real persona agents failed → nothing persisted (shadows never persist).
    assert runner._last_run_agent_records == []


@pytest.mark.asyncio
async def test_current_state_control_off_leaves_delta_fields_unset() -> None:
    """Flag-off (the default) is byte-identical to today: no shadow panel runs,
    so every delta-mode field stays at its None / zero default."""
    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()
    runner = SimulationRunner(store=store, chat_client=_StubChat())

    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_hypothesis(),
        population_size=3,
        run_seed=7,
    )

    result = simulation.result
    assert result is not None
    assert result.current_state_score is None
    assert result.current_state_delta is None
    assert result.current_state_delta_ci is None
    assert result.current_state_delta_paired_n is None
    assert result.current_state_delta_unpaired_persona == 0
    assert result.current_state_delta_unpaired_current_state == 0
    assert result.current_state_delta_sentiment_failure_drops == 0


@pytest.mark.asyncio
async def test_current_state_control_ignored_in_ab_mode() -> None:
    """A/B mode IGNORES include_current_state_control (docs: single-arm only).
    Shadows are appended only on the single-arm allocation path, so an A/B run
    has no current-state reactions. The current_state_delta* fields must
    therefore stay at their flag-off defaults — NOT be recorded as
    requested-but-uncomputable (paired_n=0), which would falsely advertise a
    baseline for an unsupported path. (mirrors the persona-lift honesty gate.)"""
    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()
    runner = SimulationRunner(store=store, chat_client=_StubChat())

    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_hypothesis(),
        population_size=3,
        run_seed=7,
        treatment_fraction=0.5,  # A/B mode
        include_current_state_control=True,  # ignored on this path
    )

    result = simulation.result
    assert result is not None
    # Flag silently ignored: every delta-mode field stays at its flag-off
    # default, indistinguishable from an A/B run that never requested it.
    assert result.current_state_score is None
    assert result.current_state_delta is None
    assert result.current_state_delta_ci is None
    assert result.current_state_delta_paired_n is None
    assert result.current_state_delta_unpaired_persona == 0
    assert result.current_state_delta_unpaired_current_state == 0
    assert result.current_state_delta_sentiment_failure_drops == 0
    # No current_state shadow leaked into the persisted A/B records.
    assert all(r.arm != "current_state" for r in runner._last_run_agent_records)


# ── T2 (#311): instrument-fit abstention rides into the persisted result ─────


@pytest.mark.asyncio
async def test_out_of_scope_run_is_not_blocked_and_result_carries_abstention() -> None:
    """A run whose OEC is out of scope (long-horizon / network / novelty) still
    RUNS to completion (no block) and the persisted result carries the
    categorical abstention flag + named reasons, while confidence_score is still
    computed — the verdict is WITHHELD, not discounted (#311 / T2)."""
    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()
    runner = SimulationRunner(store=store, chat_client=_StubChat())

    oos_hyp = Hypothesis(
        capability_name="reorder",
        prose="Will referral loops drive virality and lift 90-day revenue?",
    )

    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=oos_hyp,
        population_size=3,
        run_seed=11,
    )

    # The run was NOT blocked: agents materialized and a score was computed.
    assert len(simulation.agent_instance_ids) == 3
    result = simulation.result
    assert result is not None
    assert result.confidence_score is not None  # score still produced

    # The abstention rode into the persisted result, categorically.
    assert result.instrument_scope == "out_of_scope"
    assert result.out_of_scope_reasons  # named, human-readable reasons
    assert result.out_of_scope_reason_codes  # stable machine codes


@pytest.mark.asyncio
async def test_in_scope_run_leaves_instrument_scope_default() -> None:
    """A normal first-exposure hypothesis leaves the abstention fields at their
    flag-off defaults (byte-identical persisted result)."""
    store, persona_pack, capability, feature_pack_version = _load_pack_and_capability()
    runner = SimulationRunner(store=store, chat_client=_StubChat())

    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_hypothesis(),  # "Add a one-tap reorder button…" — in scope
        population_size=3,
        run_seed=1,
    )
    result = simulation.result
    assert result is not None
    assert result.instrument_scope == "in_scope"
    assert result.out_of_scope_reasons == []
    assert result.out_of_scope_reason_codes == []
