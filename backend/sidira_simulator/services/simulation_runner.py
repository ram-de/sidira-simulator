"""Simulation runner — orchestrates one simulation end-to-end.

Flow:
1. Load latest Persona Pack + Feature Pack capability (caller supplies)
2. Materialize N AgentInstances (one per sampled persona) — each gets a FROZEN
   identity prompt and FROZEN initial reaction. These are the agents the PM
   will chat with later. See identity-continuity guarantee in
   sidira_simulator/memory/agent_memory.py.
3. Aggregate reactions → confidence score + weaknesses (stubbed; Phase 3 scoring).
4. Persist results + live state via RunStateStore (event log + state.json).

Parallelism: agent reactions run concurrently via `asyncio.gather`. Adapted
from mirofish oasis_profile_generator.py:851-1014 (ThreadPoolExecutor with
progress callbacks); we use async-native primitives because our LLM SDKs are
async and FastAPI already runs an event loop.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock

import structlog

from sidira_simulator.adapters.llm import ChatClient, get_chat_client
from sidira_simulator.adapters.r2 import ArtifactStore, get_store
from sidira_simulator.memory.agent_memory import AgentMemory

from sidira_simulator.schemas.agent import AgentInstanceMetadata
from sidira_simulator.schemas.feature_pack import Capability
from sidira_simulator.schemas.persona import Persona, PersonaPack
from sidira_simulator.schemas.simulation import (
    AgentAnalysisSummary,
    Hypothesis,
    Simulation,
    SimulationResult,
    SimulationStatus,
    Weakness,
)
from sidira_simulator.services.identity_seed import draw_identity_seed
from sidira_simulator.services.population_sampler import allocate
from sidira_simulator.services.prompt_composer import compose_identity_prompt
from sidira_simulator.services.reaction_elicitor import elicit_reaction_distribution
from sidira_simulator.services.run_state import (
    RunPhase,
    RunStateStore,
    SimulationRunState,
)
from sidira_simulator.services.runtime_config import (
    resolve_elicitation_samples,
    resolve_elicitation_temperature,
)

log = structlog.get_logger()


@dataclass
class AgentRecord:
    """Lightweight record returned from _materialize_agent for repo persistence.

    `reaction_text` is the verbatim LLM output — needed by the scoring service.
    The same text is also persisted to R2 as `initial_reaction.md` (the frozen
    artifact that backs the identity-continuity guarantee).
    """

    agent_id: str
    persona_id: str
    persona_name: str
    created_at: datetime
    reaction_text: str = ""
    sample_index: int = 0
    # Phase 4.6 #89: A/B mode arm tag. None for single-arm sims. "treatment"
    # or "control" for A/B. #90's lift formula matches pairs by
    # (persona_id, sample_index) across arms; this field tells the matcher
    # which side of the comparison each record belongs to.
    arm: str | None = None
    # #221 hierarchical scoring: the agent's full elicited reaction
    # distribution as (text, probability) pairs. Populated from
    # `ReactionDistribution.samples`; at the default samples=1 it is a single
    # entry whose text equals `reaction_text` (the modal/frozen reaction), so
    # the scorer's hierarchical path stays dormant. With samples>1 the scorer
    # classifies every reaction and folds within-agent variance into the CI.
    reaction_distribution: list[tuple[str, float]] = field(default_factory=list)


class _LazyModelChatClient:
    """One per-run model-bound client, resolved on first LLM call.

    Keeping resolution lazy preserves the no-key demo path: missing credentials
    are counted as per-agent reaction failures instead of failing the run before
    the existing zero-agent placeholder result can be produced.
    """

    def __init__(self, model_id: str | None) -> None:
        self._model_id = model_id
        self._client: ChatClient | None = None
        self._lock = Lock()

    def _resolve(self) -> ChatClient:
        if self._client is None:
            with self._lock:
                if self._client is None:
                    self._client = get_chat_client(self._model_id)
        return self._client

    def chat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> str:
        return self._resolve().chat(
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
            seed=seed,
        )

    def chat_json(
        self,
        messages: list[dict[str, str]],
        schema: type,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        seed: int | None = None,
    ):
        return self._resolve().chat_json(
            messages,
            schema,
            max_tokens=max_tokens,
            temperature=temperature,
            seed=seed,
        )


class SimulationRunner:
    def __init__(
        self,
        store: ArtifactStore | None = None,
        chat_client: ChatClient | None = None,
        max_concurrent_agents: int = 5,
        per_agent_timeout_s: float = 60.0,
    ) -> None:
        self._store = store or get_store()
        # Lazy chat client — don't crash app startup when no LLM key is set.
        # The first .chat() call will raise RuntimeError with a clear message.
        self._chat_explicit = chat_client
        self._memory = AgentMemory(self._store, self._store)
        self._run_state = RunStateStore(self._store)
        self._semaphore = asyncio.Semaphore(max_concurrent_agents)
        self._per_agent_timeout_s = per_agent_timeout_s

    def _chat_for_model(self, model_id: str | None) -> ChatClient:
        if self._chat_explicit is not None:
            return self._chat_explicit
        return _LazyModelChatClient(model_id)

    async def run(
        self,
        customer_id: str,
        persona_pack: PersonaPack,
        capability: Capability,
        feature_pack_version: str,
        hypothesis: Hypothesis,
        population_size: int = 10,
        run_seed: int | None = None,
        max_agents: int | None = None,
        sim_id: str | None = None,
        treatment_fraction: float | None = None,
        selected_personas: list[str] | None = None,
        model_id: str | None = None,
    ) -> Simulation:
        sim_id = sim_id or str(uuid.uuid4())
        chat_client = self._chat_for_model(model_id)
        # run_seed pinned per simulation. Unset means caller didn't fix it -- mint a
        # fresh time-based seed so every default run gets distinct identities. The
        # resolved seed flows out via SimulationRunState (observable) and is used
        # for every draw_identity_seed call below.
        resolved_run_seed = run_seed if run_seed is not None else time.time_ns()
        # #221 distribution elicitation: resolve once per run (not per agent) so
        # the whole population shares one config and it is observable in
        # run.started. Defaults (1, 0.0) reproduce the historical single-reaction
        # path byte-for-byte.
        elicitation_samples = resolve_elicitation_samples()
        elicitation_temperature = resolve_elicitation_temperature()
        now = datetime.now(timezone.utc)

        state = SimulationRunState(
            simulation_id=sim_id,
            customer_id=customer_id,
            phase=RunPhase.LOADING_PACKS,
            started_at=now,
            updated_at=now,
        )
        self._run_state.write_state(state)
        self._run_state.emit(
            state,
            "run.started",
            population_size=population_size,
            run_seed=resolved_run_seed,
            elicitation_samples=elicitation_samples,
            elicitation_temperature=elicitation_temperature,
        )

        # Phase 2.5 (#5): largest-remainder allocation across personas, capped at
        # max_agents (caller-supplied, derived by the API from SIDIRA_MAX_AGENTS
        # so the runner and the persisted sampled_agent_count never disagree).
        # When None, allocate() falls back to env/default. sample_index is
        # per-persona (0..count-1) and feeds into draw_identity_seed's RNG seed.
        #
        # Phase 4.6 #89: in A/B mode, both arms get their own allocate() call.
        # When treatment_fraction=0.5 (wizard's locked v1 default), the two
        # allocations are byte-identical because allocate() is deterministic
        # on (persona_pack, total, max_agents). That means treatment + control
        # share the same (persona_id, sample_index) tuples, which means
        # draw_identity_seed produces matching identity_seeds across arms —
        # paired sampling for free (Q3 locked in docs/4.6). For asymmetric
        # fractions (schema-allowed for future flexibility), the arms diverge
        # and #90's lift formula handles unpaired agents via the matched-pair
        # bookkeeping.
        pack_by_id = {p.id: p for p in persona_pack.personas}
        agent_specs: list[tuple[Persona, int, str | None]] = []
        if treatment_fraction is None:
            # Single-arm: today's behavior, no arm tag.
            allocation = allocate(
                persona_pack,
                population_size,
                max_agents=max_agents,
                selected_personas=selected_personas,
            )
            for persona_id, count in allocation:
                persona = pack_by_id[persona_id]
                for sample_index in range(count):
                    agent_specs.append((persona, sample_index, None))
        else:
            # A/B mode: in A/B mode `population_size` is the PER-ARM target
            # (matches the wizard's cost-preview math, which uses the
            # backend-reported max_agents_per_arm from /config/limits). Each
            # arm calls
            # allocate() with the SAME (persona_pack, target, max_agents)
            # triple at the wizard's locked f=0.5 — that's what makes
            # treatment_alloc byte-identical to control_alloc, which is
            # what makes (persona_id, sample_index) pairs match across
            # arms, which is what makes draw_identity_seed produce
            # identical seeds per pair (paired sampling for free).
            #
            # Codex P1 on PR #95 caught the earlier "split the population
            # first" math: for pop=50 + max=50, that produced 25 vs 25
            # instead of the 50/50 the wizard's "≈ 50 + 50 = 100 agents"
            # preview promised, AND broke pair matching for odd pops.
            # The fix is to NOT pre-split — treat population_size as
            # per-arm target, then derive treatment_target / control_target
            # symmetrically from treatment_fraction.
            if abs(treatment_fraction - 0.5) < 1e-9:
                # Locked v1 default. Both arms get the same target → paired.
                treatment_target = population_size
                control_target = population_size
            else:
                # Asymmetric split. The wizard does not currently expose
                # this path (schema accepts it for future flexibility), so
                # the trade-off is documented but not heavily exercised:
                # at f != 0.5 the arms diverge in size, the byte-equivalent
                # allocation invariant is lost, and #90's pair matcher
                # falls back to per-(persona, sample_index) intersection.
                treatment_target = int(round(population_size * 2 * treatment_fraction))
                control_target = int(round(population_size * 2 * (1 - treatment_fraction)))
            # Phase 5 #101: persona-filter applies symmetrically across arms.
            # Same `selected_personas` to both allocate() calls preserves the
            # paired-sampling invariant from #89: at f=0.5 both arms still
            # produce byte-identical allocations because the filter + reweight
            # happens deterministically before largest-remainder.
            treatment_alloc = allocate(
                persona_pack,
                treatment_target,
                max_agents=max_agents,
                selected_personas=selected_personas,
            )
            control_alloc = allocate(
                persona_pack,
                control_target,
                max_agents=max_agents,
                selected_personas=selected_personas,
            )
            for persona_id, count in treatment_alloc:
                persona = pack_by_id[persona_id]
                for sample_index in range(count):
                    agent_specs.append((persona, sample_index, "treatment"))
            for persona_id, count in control_alloc:
                persona = pack_by_id[persona_id]
                for sample_index in range(count):
                    agent_specs.append((persona, sample_index, "control"))

        state.agents_total = len(agent_specs)
        state.mark_phase(RunPhase.MATERIALIZING_AGENTS)
        self._run_state.write_state(state)

        # Fan out: each spec gets its own AgentInstance with frozen identity + reaction.
        state.mark_phase(RunPhase.AGENTS_REACTING)
        self._run_state.write_state(state)

        # N-of-M handling: a single agent failure / timeout MUST NOT crash the whole
        # simulation. return_exceptions=True keeps the gather alive; failed agents
        # surface via agent.reaction.failed events that the frontend already renders.
        results = await asyncio.gather(
            *(
                self._materialize_agent(
                    state,
                    customer_id,
                    sim_id,
                    persona,
                    capability,
                    hypothesis,
                    persona_pack.version,
                    sample_index,
                    resolved_run_seed,
                    chat_client,
                    arm=arm,
                    elicitation_samples=elicitation_samples,
                    elicitation_temperature=elicitation_temperature,
                )
                for persona, sample_index, arm in agent_specs
            ),
            return_exceptions=True,
        )
        agent_records: list[AgentRecord] = [r for r in results if isinstance(r, AgentRecord)]
        agent_ids = [r.agent_id for r in agent_records]
        self._last_run_agent_records = agent_records  # caller can read for repo persistence

        state.mark_phase(RunPhase.SCORING)
        self._run_state.write_state(state)
        result = await self._score(
            state, sim_id, hypothesis, agent_records, resolved_run_seed, chat_client
        )

        state.mark_phase(RunPhase.COMPLETE)
        self._run_state.emit(state, "run.complete", score=result.confidence_score)

        return Simulation(
            id=sim_id,
            customer_id=customer_id,
            created_at=now,
            status=SimulationStatus.COMPLETE,
            persona_pack_version=persona_pack.version,
            feature_pack_version=feature_pack_version,
            hypothesis=hypothesis,
            model_id=model_id,
            agent_instance_ids=list(agent_ids),
            result=result,
        )

    async def _materialize_agent(
        self,
        state: SimulationRunState,
        customer_id: str,
        sim_id: str,
        persona: Persona,
        capability: Capability,
        hypothesis: Hypothesis,
        persona_pack_version: str,
        sample_index: int,
        run_seed: int,
        chat_client: ChatClient,
        arm: str | None = None,
        elicitation_samples: int = 1,
        elicitation_temperature: float = 0.0,
    ) -> AgentRecord:
        async with self._semaphore:
            agent_id = str(uuid.uuid4())
            self._run_state.emit(
                state,
                "agent.reaction.started",
                agent_id=agent_id,
                persona=persona.name,
                arm=arm,
            )

            identity_seed = draw_identity_seed(persona, sample_index, run_seed)
            # Phase 4.6 #89: thread arm into the composer so treatment/control
            # diverge ONLY in the task block (preamble stays byte-identical,
            # which is the paired-comparison invariant pinned by
            # test_control_arm_keeps_identity_preamble_byte_equivalent).
            composer_arm = arm if arm in ("treatment", "control") else "treatment"
            identity_prompt = compose_identity_prompt(
                customer_id=customer_id,
                persona=persona,
                capability=capability,
                hypothesis=hypothesis,
                identity_seed=identity_seed,
                arm=composer_arm,
            )

            # The "user turn" reaction prompt also has to diverge: in the
            # control arm there's no proposed change to react to, so the
            # status-quo framing in the system prompt would be undercut if
            # the user turn still said "React to the proposed change".
            if composer_arm == "control":
                user_turn = (
                    "React to the **current** product experience as yourself. Give your "
                    "honest, specific take in first-person prose. Reference the current "
                    "product flows and copy where relevant. Do not speculate about "
                    "hypothetical changes."
                )
            else:
                user_turn = (
                    "React to the proposed change as yourself. Give your honest, "
                    "specific reaction in first-person prose. Reference the current "
                    "product flows and copy where relevant."
                )

            try:
                distribution = await asyncio.wait_for(
                    asyncio.to_thread(
                        elicit_reaction_distribution,
                        chat_client,
                        system_prompt=identity_prompt,
                        user_turn=user_turn,
                        samples=elicitation_samples,
                        temperature=elicitation_temperature,
                    ),
                    timeout=self._per_agent_timeout_s,
                )
            except asyncio.TimeoutError:
                state.agents_failed += 1
                self._run_state.emit(
                    state,
                    "agent.reaction.failed",
                    agent_id=agent_id,
                    persona=persona.name,
                    error=f"timeout_after_{int(self._per_agent_timeout_s)}s",
                )
                raise
            except Exception as exc:
                state.agents_failed += 1
                self._run_state.emit(
                    state,
                    "agent.reaction.failed",
                    agent_id=agent_id,
                    persona=persona.name,
                    error=str(exc)[:500],
                )
                raise

            # Modal sample is the canonical frozen reaction (identity-continuity
            # contract); the full distribution is persisted alongside for #221's
            # hierarchical scoring slice. At the default samples=1 this is exactly
            # the single reaction the historical path produced.
            initial_reaction = distribution.modal.text

            now = datetime.now(timezone.utc)
            metadata = AgentInstanceMetadata(
                id=agent_id,
                customer_id=customer_id,
                simulation_id=sim_id,
                persona_id=persona.id,
                persona_pack_version=persona_pack_version,
                persona_name=persona.name,
                created_at=now,
                last_active_at=now,
                message_count=0,
                arm=arm,
            )

            # FROZEN — the identity-continuity guarantee starts here.
            self._memory.write_identity(metadata, identity_prompt)
            self._memory.write_initial_reaction(metadata, initial_reaction)
            self._memory.write_identity_seed(metadata, identity_seed)
            self._memory.write_reaction_distribution(metadata, distribution)

            state.agents_complete += 1
            self._run_state.emit(
                state,
                "agent.reaction.completed",
                agent_id=agent_id,
                persona=persona.name,
                reaction_length=len(initial_reaction),
            )
            log.info(
                "agent.materialized",
                sim_id=sim_id,
                agent_id=agent_id,
                persona=persona.name,
            )
            return AgentRecord(
                agent_id=agent_id,
                persona_id=persona.id,
                persona_name=persona.name,
                created_at=now,
                reaction_text=initial_reaction,
                sample_index=sample_index,
                arm=arm,
                reaction_distribution=[(s.text, s.probability) for s in distribution.samples],
            )

    async def _score(
        self,
        state: SimulationRunState,
        sim_id: str,
        hypothesis: Hypothesis,
        agent_records: list[AgentRecord],
        run_seed: int,
        chat_client: ChatClient,
    ) -> SimulationResult:
        """Call ScoringService + RefinementService over the agent reactions.

        Degenerate fast-path: zero successful agents → return placeholder result
        without firing LLM calls. This is what makes the "no LLM key set" demo
        path complete cleanly instead of failing.
        """
        if not agent_records:
            self._run_state.emit(state, "score.updated", score=0.0, note="no successful agents")
            return SimulationResult(
                confidence_score=0.0,
                weaknesses=[
                    Weakness(
                        category="underpowered_design",
                        summary="No agent reactions completed successfully.",
                    )
                ],
                refinement_suggestions=[],
            )

        # Lazy import to avoid pulling LLM modules at module load.
        from sidira_simulator.schemas.scoring import RefinementInput
        from sidira_simulator.services.refinement import RefinementService
        from sidira_simulator.services.scoring import AgentReaction, ScoringService

        scoring = ScoringService(chat_client=chat_client)
        refinement = RefinementService(chat_client=chat_client)

        reactions = [
            AgentReaction(
                agent_id=r.agent_id,
                persona_id=r.persona_id,
                persona_name=r.persona_name,
                reaction_text=r.reaction_text,
                sample_index=r.sample_index,
                arm=r.arm,
                reaction_distribution=r.reaction_distribution or None,
            )
            for r in agent_records
        ]

        # Phase 4.6 #90: A/B mode → run the paired-lift aggregator over the
        # treatment + control split. Detect dual-arm via any record carrying
        # an `arm` tag; single-arm sims keep `arm=None` everywhere and fall
        # through to the existing `score()` path unchanged.
        is_ab_mode = any(r.arm is not None for r in reactions)
        if is_ab_mode:
            # #221 (deferred slice): the A/B path does NOT yet consume
            # `reaction_distribution`. `score_ab()` → `analyze()` reads only
            # `reaction_text` (the modal/frozen reaction), so multi-sample A/B
            # runs keep modal-only per-arm CIs and lift — byte-identical to
            # pre-#221 behavior. Hierarchical CIs for the paired-lift bootstrap
            # are tracked as a follow-up; the single-arm `score()` path below is
            # the only consumer of within-agent variance in this slice.
            treatment_reactions = [r for r in reactions if r.arm == "treatment"]
            control_reactions = [r for r in reactions if r.arm == "control"]
            result, analyses = await scoring.score_ab(
                hypothesis,
                treatment_reactions,
                control_reactions,
                run_seed=run_seed,
            )
        else:
            result, analyses = await scoring.score(hypothesis, reactions, run_seed=run_seed)
        # #51: persist per-agent sentiment + top-quote on the result so the
        # detail page can render the table without N extra R2 reads. Pair
        # analyses with their reaction text by agent_id (same len + same order
        # in practice, but defensive join keeps us correct if scoring ever
        # reorders or drops rows).
        reaction_by_id = {r.agent_id: r.reaction_text for r in agent_records}
        result.per_agent_analyses = [
            AgentAnalysisSummary(
                agent_id=a.agent_id,
                sentiment=a.sentiment.sentiment.value,
                sentiment_confidence=a.sentiment.confidence,
                top_quote=_derive_top_quote(reaction_by_id.get(a.agent_id, "")),
            )
            for a in analyses
        ]
        self._run_state.emit(state, "score.updated", score=result.confidence_score)

        # Refinement runs only when there's meaningful room to improve.
        # Phase 4.6 #90 (codex R6-P2): when A/B mode short-circuited on a
        # missing-arm run, `analyses` is empty and the placeholder result
        # has confidence_score=0 only because lift is uncomputable, not
        # because the surviving arm tanked. Running refinement on the
        # surviving arm's reactions would burn an LLM call to "improve"
        # a run that's genuinely broken upstream — skip it.
        ab_missing_arm = is_ab_mode and not analyses
        if result.confidence_score < 80.0 and not ab_missing_arm:
            sample_reactions = [r.reaction_text for r in agent_records[:3]]
            suggestions = await refinement.suggest(
                RefinementInput(
                    hypothesis_prose=hypothesis.prose,
                    capability_name=hypothesis.capability_name,
                    confidence_score=result.confidence_score,
                    top_weaknesses=result.weaknesses,
                    sample_reactions=sample_reactions,
                )
            )
            result.refinement_suggestions = suggestions

        return result


# Max length of a single-line quote shown in the result table. Tuned for the
# table cell — long enough to carry voice, short enough to fit on one line.
_TOP_QUOTE_MAX = 120


def _derive_top_quote(reaction_text: str) -> str:
    """Pick a short, voice-y quote from an agent's initial reaction for the
    result-table cell. Strategy: take the first sentence (up to the first
    ".", "!", or "?"); if that's longer than `_TOP_QUOTE_MAX`, fall back to
    a hard truncation at a word boundary with an ellipsis suffix.

    The spec calls "first sentence vs longest vs highest-attention span" an
    open question. First-sentence wins on signal-per-effort: the opener
    pattern enforced by #77's prompt-composer fix means the first sentence
    is the most persona-specific anchor in the reaction.
    """
    text = (reaction_text or "").strip()
    if not text:
        return ""
    end = len(text)
    for ch in (".", "!", "?"):
        i = text.find(ch)
        if 0 <= i < end:
            end = i + 1
    first_sentence = text[:end].strip() or text
    if len(first_sentence) <= _TOP_QUOTE_MAX:
        return first_sentence
    truncated = first_sentence[: _TOP_QUOTE_MAX - 1]
    cut = truncated.rfind(" ")
    # Codex #84 round-1 P2: prefer ANY positive word boundary over a
    # mid-token slice. The earlier `cut > _TOP_QUOTE_MAX // 2` gate
    # silently fell back to mid-token truncation when the only available
    # space was near the start of a very long single token ("Short " +
    # huge_word would slice the huge_word mid-character). The spec calls
    # for word-boundary truncation; only fall back to a hard cut when
    # the truncated prefix contains literally no spaces.
    if cut > 0:
        truncated = truncated[:cut]
    return truncated.rstrip() + "…"
