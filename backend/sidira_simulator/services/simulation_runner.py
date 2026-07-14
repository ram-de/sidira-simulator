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
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    # Type-only import: input_lint pulls scoring (LLM-adjacent), which the runner
    # otherwise imports lazily in _score. Keep it off the module-load path.
    from sidira_simulator.services.input_lint import InputLintVerdict

from sidira_simulator.adapters.llm import ChatClient, get_chat_client
from sidira_simulator.adapters.r2 import ArtifactStore, get_store
from sidira_simulator.memory.agent_memory import AgentMemory

from sidira_simulator.schemas.agent import AgentInstanceMetadata
from sidira_simulator.schemas.feature_pack import Capability
from sidira_simulator.schemas.persona import Persona, PersonaPack
from sidira_simulator.schemas.simulation import (
    AgentAnalysisSummary,
    Hypothesis,
    InputFlags,
    Simulation,
    SimulationResult,
    SimulationStatus,
    Weakness,
)
from sidira_simulator.services.metric_registry import get_metric
from sidira_simulator.services.identity_seed import draw_identity_seed
from sidira_simulator.services.population_sampler import allocate
from sidira_simulator.services.prompt_composer import (
    compose_comparative_metric_prompt,
    compose_identity_prompt,
    compose_metric_prompt,
)
from sidira_simulator.services.reaction_elicitor import elicit_reaction_distribution
from sidira_simulator.services.visit_elicitor import elicit_visit_delta
from sidira_simulator.services.run_state import (
    RunPhase,
    RunStateStore,
    SimulationRunState,
)
from sidira_simulator.services.runtime_config import (
    resolve_conversion_paraphrases,
    resolve_activity_weight,
    resolve_elicitation_mode,
    resolve_elicitation_samples,
    resolve_elicitation_temperature,
    resolve_metric_comparative,
)
from sidira_simulator.services.treatment_renderer import (
    extract_choice_set,
    render_state_diff,
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
    # #221 §3a / #275 metric outcome: the agent's elicited target propensity
    # (p_metric) from the turn-2 allocation, when the Hypothesis carried a
    # registered `metric_name` (conversion / retention) and this is a persona arm.
    # None when no metric was set OR the per-agent elicitation failed (the run
    # stays alive; the pair is dropped honestly at aggregation). Scored only as a
    # paired treatment−control delta, never as an absolute level. (#275 Decision
    # A: generic name — exactly one metric per sim.)
    metric_p: float | None = None
    # #221 §3b blinding: True when the metric pass ran on the UNBLINDED fallback
    # prompt (treatment change had no faithful standalone view — removal /
    # pure-mechanic / prose-only). The pass still produces a p_metric, but the
    # treatment side is exposed to change framing, so the resulting lift is
    # low-confidence and is flagged downstream. Always False for control and for
    # blinded treatment passes; never set on a failed/None elicitation.
    metric_unblinded: bool = False
    # #221 §3e paraphrase ensemble: True when the agent's target propensity
    # (p_metric) moved materially across the K question paraphrases (spread >
    # threshold) — the answer is prompt-driven, so the pair's delta is
    # low-confidence and is flagged downstream. Always False at the default K=1
    # and on a failed/None elicitation. Set on EITHER arm.
    metric_paraphrase_unstable: bool = False
    # #342 comparative-delta: the directly-elicited treatment−control metric delta
    # from a single comparative pass, set ONLY on treatment agents in comparative
    # forecaster mode (SIDIRA_METRIC_COMPARATIVE on). None everywhere else → the
    # historical two-pass subtraction path is used. Threaded onto the AgentReaction
    # so `aggregate_metric_lift` delegates to the comparative aggregator.
    metric_comparative_delta: float | None = None
    # Variance-collapse honesty flag: True when this agent's persona lacked
    # per-persona v1.1 `behavioral_seeds`, so `draw_identity_seed` fell back to the
    # shared default identity seed (cross-agent variance degraded). Captured at the
    # draw site (`persona.behavioral_seeds is None`) and threaded onto the
    # AgentReaction so `aggregate_metric_lift` can surface the collapse. Set on
    # EITHER arm; never affects any numeric output.
    behavioral_seeds_fallback: bool = False


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
        include_no_persona_control: bool = False,
        include_current_state_control: bool = False,
        input_lint: "InputLintVerdict | None" = None,
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
        # #221 §3e / #275: number of question paraphrases to ensemble for the
        # per-metric outcome pass. One shared knob across all metrics
        # (SIDIRA_CONVERSION_PARAPHRASES; the env name is kept for back-compat).
        # Default 1 reproduces the historical single-prompt pass; resolved once per
        # run so the whole population shares one K and it is observable in
        # run.started.
        metric_paraphrases = resolve_conversion_paraphrases()
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
            metric_paraphrases=metric_paraphrases,
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
            # #221 §4.1 persona-lift baseline: add a 1:1 shadow panel of
            # "no_persona" agents over the SAME (persona_id, sample_index)
            # allocation. Each shadow reacts to the identical proposed change
            # via the base LLM with NO persona conditioning, so the paired-lift
            # aggregator can attribute any sentiment delta to persona
            # conditioning alone (the "Funhouse Mirrors" guard). Shadows are
            # ephemeral — never persisted to R2/DB — and only the no-arm panel
            # gets them; A/B mode is out of scope for this slice. Default off:
            # when the flag is unset the spec list is byte-identical to today.
            if include_no_persona_control:
                for persona_id, count in allocation:
                    persona = pack_by_id[persona_id]
                    for sample_index in range(count):
                        agent_specs.append((persona, sample_index, "no_persona"))
            # #221 §3.3.1 delta-mode baseline: add a 1:1 shadow panel of the
            # SAME personas reacting to the CURRENT product state — the existing
            # A/B control framing (proposed change omitted) applied as a paired
            # shadow in single-arm mode. Each shadow shares its persona twin's
            # (persona_id, sample_index), so the paired-delta aggregator can
            # attribute any sentiment movement to the proposed change alone.
            # Every persona is its own control (a 100%-paired design). Shadows
            # are ephemeral — never persisted to R2/DB — and only the single-arm
            # panel gets them; A/B mode is out of scope for this slice. Default
            # off: when unset the spec list is byte-identical to today.
            if include_current_state_control:
                for persona_id, count in allocation:
                    persona = pack_by_id[persona_id]
                    for sample_index in range(count):
                        agent_specs.append((persona, sample_index, "current_state"))
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
                    metric_paraphrases=metric_paraphrases,
                )
                for persona, sample_index, arm in agent_specs
            ),
            return_exceptions=True,
        )
        agent_records: list[AgentRecord] = [r for r in results if isinstance(r, AgentRecord)]
        # #221 persona-lift / delta-mode: no_persona AND current_state shadows
        # are ephemeral. They feed the scorer (for the paired baselines) but are
        # NOT persisted — the orchestrator reads `_last_run_agent_records` to
        # write agent_instances rows and to populate `agent_instance_ids`, both
        # of which must contain only the real persona agents (no phantom rows,
        # no A/B mislabel).
        persisted_records = [
            r for r in agent_records if r.arm not in ("no_persona", "current_state")
        ]
        agent_ids = [r.agent_id for r in persisted_records]
        self._last_run_agent_records = persisted_records  # caller reads for repo persistence

        state.mark_phase(RunPhase.SCORING)
        self._run_state.write_state(state)
        # Pass the FULL record set (persona + shadows) so _score can compute the
        # persona-lift and delta-mode baselines; it splits the arms internally.
        result = await self._score(
            state,
            sim_id,
            hypothesis,
            agent_records,
            persona_pack,
            resolved_run_seed,
            chat_client,
            include_no_persona_control=include_no_persona_control,
            include_current_state_control=include_current_state_control,
            input_lint=input_lint,
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
        metric_paraphrases: int = 1,
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

            # Variance-collapse honesty: a persona without per-persona v1.1
            # behavioral_seeds gets the shared default seed inside
            # draw_identity_seed (cross-agent variance degraded). Capture the
            # condition here — the same predicate draw_identity_seed branches on —
            # and thread it onto the AgentRecord so aggregation can flag a metric
            # that flattened from collapse rather than a true null.
            behavioral_seeds_fallback = persona.behavioral_seeds is None
            identity_seed = draw_identity_seed(persona, sample_index, run_seed)
            # Phase 4.6 #89: thread arm into the composer so treatment/control
            # diverge ONLY in the task block (preamble stays byte-identical,
            # which is the paired-comparison invariant pinned by
            # test_control_arm_keeps_identity_preamble_byte_equivalent).
            # #221 delta-mode: the current_state shadow reuses the existing A/B
            # "control" framing — the FULL persona reacting to the CURRENT
            # product state (proposed change omitted) — so it composes with
            # arm="control". Only the task block differs from its treatment
            # twin; the persona preamble stays byte-identical (paired invariant).
            composer_arm = (
                "control"
                if arm == "current_state"
                else (arm if arm in ("treatment", "control") else "treatment")
            )
            # #221 persona-lift: the no_persona shadow reacts to the SAME
            # proposed change (treatment task framing) but with the persona
            # conditioning stripped out of the preamble. Everything else —
            # the user turn, the elicitation config, the change view — is
            # byte-identical to its persona twin, so the only difference is
            # persona identity. The current_state shadow KEEPS the persona
            # (use_persona stays True) — it ablates the change, not the persona.
            use_persona = arm != "no_persona"
            identity_prompt = compose_identity_prompt(
                customer_id=customer_id,
                persona=persona,
                capability=capability,
                hypothesis=hypothesis,
                identity_seed=identity_seed,
                arm=composer_arm,
                use_persona=use_persona,
                # agent-behavior-spec §2 layer 4: same per-agent index
                # identity_seed is keyed on, so the individual behavioral row is
                # selected deterministically and pairs across arms (treatment and
                # control twins share sample_index → draw the same row).
                sample_index=sample_index,
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

            # #221 §3a / #275: per-metric outcome elicitation. Only when the
            # Hypothesis carried a REGISTERED metric (conversion / retention) AND
            # this is a persona arm that feeds the paired A/B comparison
            # (treatment/control). The ephemeral shadows (no_persona /
            # current_state) drive sentiment baselines only, never the metric
            # headline, so we don't spend a metric call on them. The metric pass is
            # BLINDED (§3b): it runs on a separate blinded system prompt
            # (compose_metric_prompt — standalone state, no change framing) and is
            # NOT conditioned on the unblinded turn-1 reaction, so demand
            # characteristics can't inflate the treatment arm and bias the
            # treatment−control delta. A failure here is per-agent: metric_p stays
            # None, the agent (and its sentiment contribution) survives, and the
            # pair is dropped honestly at aggregation (elicitation_failure_drops) —
            # never imputed to zero. The metric is dispatched through the registry,
            # so retention routes here exactly as conversion does.
            metric_p: float | None = None
            metric_unblinded = False
            metric_paraphrase_unstable = False
            comparative_delta: float | None = None  # #342, set below in comparative mode
            # Dispatch is FAIL-LOUD (codex P2): metric_name=None is the legacy
            # sentiment-only path (skip elicitation); ANY non-None metric_name
            # MUST resolve to a registered descriptor via get_metric — which
            # raises KeyError on registry/Literal drift (e.g. a value that
            # reached here via model_construct or stale data) rather than
            # silently degrading to sentiment. We never check is_registered and
            # skip: an unknown metric is a programming error, not a no-op.
            if hypothesis.metric_name is not None and arm in ("treatment", "control"):
                descriptor = get_metric(hypothesis.metric_name)
                # §3a choice set (spec §"the on-screen options"): prefer the
                # PM-supplied choice_set; otherwise ground the alternatives in the
                # actual reachable actions at the decision point in the rendered
                # proposed state (treatment_renderer.extract_choice_set), so the
                # question reflects the screen the agent saw rather than generic
                # fallbacks. The SAME proposed-state option set is used for both
                # arms so p_metric is comparable across the paired seed. The
                # elicitor still falls back to the metric's registry default choice
                # set when nothing grounds (prose-only change, thin crawl).
                #
                # The metric's TARGET action term(s) are filtered out of the
                # ALTERNATIVES regardless of source (PM-supplied or extracted): the
                # elicitor always prepends the canonical target label, so any
                # alternative equal to the target would offer two target-like
                # options while p_metric counts only the canonical one — agents
                # could split target intent into the unlabeled twin and undercount
                # the lift. The terms are supplied per-metric by the registry.
                target_terms = descriptor.target_terms(hypothesis)
                grounded_choice_set: list[str] | None = None
                if hypothesis.choice_set:
                    grounded_choice_set = [
                        lbl
                        for lbl in hypothesis.choice_set
                        if lbl.strip().lower() not in target_terms
                    ] or None
                elif hypothesis.proposed_figma is not None:
                    rendered = render_state_diff(capability, hypothesis)
                    extracted = extract_choice_set(rendered, hypothesis.decision_point or "")
                    # Only forward GROUNDED choices. When the decision point has no
                    # reachable transitions, extract_choice_set substitutes its own
                    # fallback set — which includes a generic "convert" option — so
                    # on fallback we leave it None and let the elicitor use its
                    # curated default choice set.
                    if extracted.grounded:
                        grounded_choice_set = [
                            c.action
                            for c in extracted.choices
                            if c.action.strip().lower() not in target_terms
                        ] or None
                # Blinded metric prompt (§3b): standalone state, no change
                # framing — NOT the unblinded identity_prompt used for the
                # reaction. `blinded` is False only on the treatment fallback
                # (no faithful standalone view); we then flag the result
                # low-confidence rather than report a clean blinded delta.
                metric_prompt, metric_blinded = compose_metric_prompt(
                    customer_id=customer_id,
                    persona=persona,
                    capability=capability,
                    hypothesis=hypothesis,
                    identity_seed=identity_seed,
                    arm=arm,
                    use_persona=use_persona,
                    sample_index=sample_index,
                )
                if not metric_blinded:
                    log.warning(
                        "agent.metric.unblinded_fallback",
                        sim_id=sim_id,
                        agent_id=agent_id,
                        persona=persona.name,
                        metric=hypothesis.metric_name,
                        note=(
                            "no faithful standalone view; metric ran UNBLINDED "
                            "— lift is low-confidence"
                        ),
                    )
                try:
                    # §3e: K-paraphrase ensemble (K=metric_paraphrases, default 1 →
                    # byte-identical to the historical single-prompt pass). Only the
                    # question wording varies across the K calls; the blinded metric
                    # prompt and option set are held byte-identical. The registry's
                    # `elicit` adapter runs the metric's ensemble and returns
                    # (mean_p_metric, paraphrase_unstable).
                    mean_p, unstable = await asyncio.wait_for(
                        asyncio.to_thread(
                            descriptor.elicit,
                            chat_client,
                            system_prompt=metric_prompt,
                            hypothesis=hypothesis,
                            capability=capability,
                            choice_set=grounded_choice_set,
                            paraphrases=metric_paraphrases,
                            timeout_scale_count=descriptor.paraphrase_count,
                        ),
                        # §3e: the ensemble runs K paraphrases SEQUENTIALLY, so the
                        # per-call budget must scale by K — otherwise a K>1 run that
                        # completes each call within the normal budget can still
                        # exceed a single-call window and spuriously drop the whole
                        # metric (metric_p=None) for that agent (codex P2). K=1 is
                        # unchanged. Scale by the EFFECTIVE call count (capped to the
                        # metric's paraphrase_count) so an oversized env can't
                        # multiply the budget past the calls that actually run.
                        timeout=(
                            self._per_agent_timeout_s
                            * min(metric_paraphrases, descriptor.paraphrase_count)
                        ),
                    )
                    metric_p = mean_p
                    # Only treatment can be unblinded (control is always blinded);
                    # flag rides only on a successful elicitation.
                    metric_unblinded = not metric_blinded
                    # §3e: flag rides on EITHER arm (a control flip is just as
                    # corrupting to the pair's delta as a treatment flip).
                    metric_paraphrase_unstable = unstable
                except Exception as exc:
                    # Per-agent metric failure — do NOT fail the agent. We log
                    # (rather than emit a RunEvent) because the SSE event contract
                    # has no metric-failure type and the agent's sentiment
                    # contribution still stands; the dropped pair is surfaced
                    # honestly downstream via metric_lift_elicitation_failure_drops.
                    log.warning(
                        "agent.metric.failed",
                        sim_id=sim_id,
                        agent_id=agent_id,
                        persona=persona.name,
                        metric=hypothesis.metric_name,
                        error=str(exc)[:500],
                    )

                # #342 comparative-delta forecaster pass (opt-in, default OFF). When
                # enabled, elicit the treatment−control delta directly in ONE
                # comparative pass (both versions shown to the forecaster) for the
                # treatment agent — recovering the directional signal the two-pass
                # subtraction loses. Visit-only for now (the metric with a delta
                # elicitor). Non-fatal on failure: comparative_delta stays None and
                # the pair drops honestly at aggregation. The per-arm pass above
                # still ran (its flags stand); only the LIFT statistic changes when
                # deltas are present (aggregate_metric_lift delegates).
                if (
                    resolve_metric_comparative()
                    and arm == "treatment"
                    and resolve_elicitation_mode() == "forecaster"
                    and hypothesis.metric_name == "visit"
                ):
                    try:
                        comparative_system_prompt = compose_comparative_metric_prompt(
                            customer_id=customer_id,
                            persona=persona,
                            capability=capability,
                            hypothesis=hypothesis,
                            identity_seed=identity_seed,
                            use_persona=use_persona,
                            sample_index=sample_index,
                        )
                        comparative_delta = elicit_visit_delta(
                            chat_client,
                            system_prompt=comparative_system_prompt,
                            capability_name=capability.name,
                            decision_point=hypothesis.decision_point or "",
                            temperature=elicitation_temperature,
                            seed=run_seed,
                        )
                    except Exception as exc:
                        log.warning(
                            "agent.metric.comparative_failed",
                            sim_id=sim_id,
                            agent_id=agent_id,
                            persona=persona.name,
                            error=str(exc)[:500],
                        )

            now = datetime.now(timezone.utc)

            # #221 persona-lift / delta-mode: both shadow arms (no_persona and
            # current_state) are ephemeral. They exist only to feed the scorer's
            # paired baselines this run, so we skip ALL R2 persistence (identity,
            # initial reaction, seed, distribution) and never build the
            # AgentInstanceMetadata. There is no chat replay for a shadow and no
            # DB row, so the identity-continuity guarantee does not apply. The
            # AgentRecord returned below still carries the reaction so _score can
            # use it. (current_state keeps use_persona=True, so we gate
            # persistence on the arm tag, not use_persona.)
            persist = arm not in ("no_persona", "current_state")
            if persist:
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
                metric_p=metric_p,
                metric_unblinded=metric_unblinded,
                metric_paraphrase_unstable=metric_paraphrase_unstable,
                metric_comparative_delta=comparative_delta,
                behavioral_seeds_fallback=behavioral_seeds_fallback,
            )

    async def _score(
        self,
        state: SimulationRunState,
        sim_id: str,
        hypothesis: Hypothesis,
        agent_records: list[AgentRecord],
        persona_pack: PersonaPack,
        run_seed: int,
        chat_client: ChatClient,
        include_no_persona_control: bool = False,
        include_current_state_control: bool = False,
        input_lint: "InputLintVerdict | None" = None,
    ) -> SimulationResult:
        """Call ScoringService + RefinementService over the agent reactions.

        Degenerate fast-path: zero successful agents → return placeholder result
        without firing LLM calls. This is what makes the "no LLM key set" demo
        path complete cleanly instead of failing.
        """
        if not agent_records:
            self._run_state.emit(state, "score.updated", score=0.0, note="no successful agents")
            # Degenerate fast-path: still stamp the pre-flight input lint (T3)
            # and the instrument-fit abstention (T2) — both are pre-run / OEC
            # signals independent of whether any agent reacted.
            return _stamp_screen_verdict(
                _stamp_instrument_scope(
                    _stamp_input_flags(
                        SimulationResult(
                            confidence_score=0.0,
                            weaknesses=[
                                Weakness(
                                    category="underpowered_design",
                                    summary="No agent reactions completed successfully.",
                                )
                            ],
                            refinement_suggestions=[],
                        ),
                        input_lint,
                    ),
                    hypothesis,
                )
            )

        # Lazy import to avoid pulling LLM modules at module load.
        from sidira_simulator.schemas.scoring import RefinementInput, ScoringConfig
        from sidira_simulator.services.activity_weight import normalize_activity_weights
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
                metric_p=r.metric_p,
                metric_unblinded=r.metric_unblinded,
                metric_paraphrase_unstable=r.metric_paraphrase_unstable,
                metric_comparative_delta=r.metric_comparative_delta,
                behavioral_seeds_fallback=r.behavioral_seeds_fallback,
            )
            for r in agent_records
        ]

        # #5 (MiroFish-borrow): when activity weighting is enabled, derive each
        # agent's cohort-activity weight from Persona.activity_signal, normalized
        # ONCE across the whole run (both arms + baselines share one constant, so
        # the lift comparison stays on a single weighting basis). Default OFF →
        # reactions keep weight 1.0 and the scoring config stays None, so the
        # score path is byte-identical to before.
        scoring_cfg: "ScoringConfig | None" = None
        if resolve_activity_weight():
            signal_by_persona = {p.id: p.activity_signal for p in persona_pack.personas}
            weights = normalize_activity_weights(
                [signal_by_persona.get(r.persona_id) for r in reactions]
            )
            for rx, w in zip(reactions, weights):
                rx.activity_weight = w
            scoring_cfg = ScoringConfig(use_activity_weight=True)

        # #221 §4.1 persona-lift / §3.3.1 delta-mode: split off the ephemeral
        # shadows BEFORE the A/B-mode detection below. The persona arms
        # (treatment / control / single-arm None) drive the headline score
        # exactly as before; the no_persona + current_state shadows only feed
        # their paired baselines at the end, so they must NOT leak into
        # is_ab_mode or the persona scoring path (a shadow record carries a
        # non-None arm that would otherwise trip the A/B branch).
        no_persona_reactions = [r for r in reactions if r.arm == "no_persona"]
        current_state_reactions = [r for r in reactions if r.arm == "current_state"]
        persona_reactions = [r for r in reactions if r.arm not in ("no_persona", "current_state")]

        # Phase 4.6 #90: A/B mode → run the paired-lift aggregator over the
        # treatment + control split. Detect dual-arm via any persona record
        # carrying an `arm` tag; single-arm sims keep `arm=None` everywhere
        # and fall through to the existing `score()` path unchanged.
        is_ab_mode = any(r.arm is not None for r in persona_reactions)
        if is_ab_mode:
            # #221 (deferred slice): the A/B path does NOT yet consume
            # `reaction_distribution`. `score_ab()` → `analyze()` reads only
            # `reaction_text` (the modal/frozen reaction), so multi-sample A/B
            # runs keep modal-only per-arm CIs and lift — byte-identical to
            # pre-#221 behavior. Hierarchical CIs for the paired-lift bootstrap
            # are tracked as a follow-up; the single-arm `score()` path below is
            # the only consumer of within-agent variance in this slice.
            treatment_reactions = [r for r in persona_reactions if r.arm == "treatment"]
            control_reactions = [r for r in persona_reactions if r.arm == "control"]
            result, analyses = await scoring.score_ab(
                hypothesis,
                treatment_reactions,
                control_reactions,
                config=scoring_cfg,
                run_seed=run_seed,
            )
        else:
            result, analyses = await scoring.score(
                hypothesis, persona_reactions, config=scoring_cfg, run_seed=run_seed
            )
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

        # Refinement runs when there's meaningful room to improve. The trigger
        # has TWO arms:
        #   • post-run score<80 (today's path), AND
        #   • #312 / T3: the pre-flight ordinal lint flagged the INPUT
        #     (amber/red/abstain) — refinement fires regardless of score, so a
        #     leading-framing / vague-prose run still gets a rewrite offer even
        #     when the agents happened to score it ≥80. This is the ticket's
        #     "move the refinement trigger earlier" — we REUSE RefinementService
        #     verbatim, only widening WHEN it fires.
        # Phase 4.6 #90 (codex R6-P2): when A/B mode short-circuited on a
        # missing-arm run, `analyses` is empty and the placeholder result
        # has confidence_score=0 only because lift is uncomputable, not
        # because the surviving arm tanked. Running refinement on the
        # surviving arm's reactions would burn an LLM call to "improve"
        # a run that's genuinely broken upstream — skip it.
        ab_missing_arm = is_ab_mode and not analyses
        input_flagged = input_lint is not None and input_lint.is_flagged
        if (result.confidence_score < 80.0 or input_flagged) and not ab_missing_arm:
            # Sample from the persona records only — the shadow arms
            # (no_persona, current_state) are baselines, not material the PM
            # should see paraphrased back as refinement evidence.
            sample_reactions = [
                r.reaction_text
                for r in agent_records
                if r.arm not in ("no_persona", "current_state")
            ][:3]
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

        # #221 §4.1 persona-lift baseline: if no_persona shadows ran and the
        # persona arm actually produced analyses, classify the shadows and
        # compute the paired persona − no_persona lift. This is purely ADDITIVE:
        # it populates the persona_lift* / no_persona_score fields and leaves
        # confidence_score, weaknesses, per_agent_analyses, and refinement
        # untouched, so a run with the flag off is byte-identical. `analyses`
        # (the persona modal analyses) is paired by (persona_id, sample_index)
        # against the freshly-classified no_persona analyses.
        #
        # A/B mode IGNORES the flag entirely (docs: single-arm only). Shadows
        # are appended only on the single-arm allocation path, so an A/B run
        # has no no_persona_reactions; gating both branches on `not is_ab_mode`
        # keeps the persona_lift* fields at their flag-off defaults rather than
        # falsely recording the run as "requested but uncomputable" (paired_n=0)
        # for an unsupported path. (codex P2)
        if include_no_persona_control and not is_ab_mode and analyses and no_persona_reactions:
            from sidira_simulator.services.scoring import aggregate_persona_lift

            np_analyses = await asyncio.gather(
                *(scoring.analyze(hypothesis, r) for r in no_persona_reactions),
                return_exceptions=False,
            )
            no_persona_result, lift = aggregate_persona_lift(
                analyses, np_analyses, config=scoring_cfg, run_seed=run_seed
            )
            result = result.model_copy(
                update={
                    "no_persona_score": no_persona_result.confidence_score,
                    "persona_lift": lift.lift,
                    "persona_lift_ci": lift.lift_ci,
                    "persona_lift_paired_n": lift.paired_n,
                    # _paired_lift's "treatment" side is the persona arm, so its
                    # unpaired_treatment / unpaired_control counters map onto
                    # persona / no_persona here.
                    "persona_lift_unpaired_persona": lift.unpaired_treatment,
                    "persona_lift_unpaired_no_persona": lift.unpaired_control,
                    "persona_lift_sentiment_failure_drops": lift.sentiment_failure_drops,
                }
            )
            self._run_state.emit(
                state,
                "persona_lift.computed",
                persona_lift=lift.lift,
                no_persona_score=no_persona_result.confidence_score,
                paired_n=lift.paired_n,
            )
        elif include_no_persona_control and not is_ab_mode and analyses:
            # The baseline was REQUESTED but no no-persona shadow produced a
            # usable reaction (every shadow timed out or failed materialization),
            # so the lift is uncomputable. Record paired_n=0 + every persona
            # agent as unpaired so the persisted result is distinguishable from a
            # flag-off run (where these fields stay None / 0). Honesty gate: a
            # requested-but-uncomputable baseline must not masquerade as "never
            # requested". persona_lift / ci / no_persona_score stay None.
            result = result.model_copy(
                update={
                    "persona_lift_paired_n": 0,
                    "persona_lift_unpaired_persona": len(analyses),
                }
            )
            self._run_state.emit(
                state,
                "persona_lift.computed",
                persona_lift=None,
                no_persona_score=None,
                paired_n=0,
            )

        # #221 §3.3.1 delta-mode baseline: if current_state shadows ran and the
        # persona arm actually produced analyses, classify the shadows and
        # compute the paired treatment − current_state delta. Purely ADDITIVE,
        # exactly like the persona-lift block above: it populates the
        # current_state_delta* / current_state_score fields and leaves
        # confidence_score, weaknesses, per_agent_analyses, and refinement
        # untouched, so a run with the flag off is byte-identical. `analyses`
        # (the persona modal analyses, here the proposed-change "treatment"
        # side) is paired by (persona_id, sample_index) against the
        # freshly-classified current_state analyses.
        #
        # A/B mode IGNORES the flag entirely (single-arm only). Shadows are
        # appended only on the single-arm allocation path, so an A/B run has no
        # current_state_reactions; gating both branches on `not is_ab_mode`
        # keeps the current_state_delta* fields at their flag-off defaults rather
        # than falsely recording the run as "requested but uncomputable"
        # (paired_n=0) for an unsupported path. (mirrors the persona-lift gate)
        if (
            include_current_state_control
            and not is_ab_mode
            and analyses
            and current_state_reactions
        ):
            from sidira_simulator.services.scoring import aggregate_current_state_delta

            cs_analyses = await asyncio.gather(
                *(scoring.analyze(hypothesis, r) for r in current_state_reactions),
                return_exceptions=False,
            )
            current_state_result, delta = aggregate_current_state_delta(
                analyses, cs_analyses, config=scoring_cfg, run_seed=run_seed
            )
            result = result.model_copy(
                update={
                    "current_state_score": current_state_result.confidence_score,
                    "current_state_delta": delta.lift,
                    "current_state_delta_ci": delta.lift_ci,
                    "current_state_delta_paired_n": delta.paired_n,
                    # _paired_lift's "treatment" side is the proposed-change arm,
                    # so its unpaired_treatment / unpaired_control counters map
                    # onto persona / current_state here.
                    "current_state_delta_unpaired_persona": delta.unpaired_treatment,
                    "current_state_delta_unpaired_current_state": delta.unpaired_control,
                    "current_state_delta_sentiment_failure_drops": delta.sentiment_failure_drops,
                }
            )
            self._run_state.emit(
                state,
                "current_state_delta.computed",
                current_state_delta=delta.lift,
                current_state_score=current_state_result.confidence_score,
                paired_n=delta.paired_n,
            )
        elif include_current_state_control and not is_ab_mode:
            # The baseline was REQUESTED but the delta is uncomputable. Two ways
            # to land here, both gated only on (flag + single-arm) — NOT on
            # `analyses` — so the honesty signal survives every degenerate run:
            #   - every current-state shadow timed out / failed materialization
            #     (current_state_reactions empty), while persona agents scored, OR
            #   - every real persona agent failed but a shadow survived, so
            #     `analyses` is empty and there is no treatment side to pair
            #     against (codex P2 — without dropping `and analyses` this case
            #     would leave paired_n=None, indistinguishable from flag-off).
            # Record paired_n=0 + the persona agents (if any) as unpaired so the
            # persisted result is distinguishable from a flag-off run (where these
            # fields stay None / 0). A requested-but-uncomputable baseline must not
            # masquerade as "never requested". delta / ci / score stay None.
            result = result.model_copy(
                update={
                    "current_state_delta_paired_n": 0,
                    "current_state_delta_unpaired_persona": len(analyses),
                }
            )
            self._run_state.emit(
                state,
                "current_state_delta.computed",
                current_state_delta=None,
                current_state_score=None,
                paired_n=0,
            )

        # #312 / T3: stamp the pre-flight ordinal input lint (amber/red/abstain)
        # categorically. No-op (byte-identical) for a green / absent lint; never
        # touches confidence_score. Stamped before the T2 abstention so both
        # categorical carriers ride the same result_json blob independently.
        result = _stamp_input_flags(result, input_lint)

        # #311 / T2: stamp the categorical instrument-fit abstention LAST, after
        # every additive baseline has populated, so it composes with (never
        # overwrites) the lift/delta fields. No-op (byte-identical) for in-scope
        # OECs; never touches confidence_score.
        return _stamp_screen_verdict(_stamp_instrument_scope(result, hypothesis))


def _stamp_input_flags(
    result: SimulationResult, input_lint: "InputLintVerdict | None"
) -> SimulationResult:
    """Stamp the T3 (#312) pre-flight ordinal input lint onto the result.

    Categorical only — an ordinal state + named reasons; NEVER a number and NEVER
    a `confidence_score` discount (panel hard constraint). A `green` or absent
    lint is a no-op (returns the result unchanged, so a clean run and every older
    `result_json` row load byte-identical and this is migration-free — the flag
    rides the result JSON blob, not a DB column). The verdict was computed ONCE
    pre-flight in `api/simulations.py` (the LLM judge runs at create time, not
    here) and threaded through the orchestrator, so scoring spends no extra
    tokens. A `model_copy` keeps the in-scope path byte-identical.
    """
    if input_lint is None or not input_lint.is_flagged:
        return result
    return result.model_copy(
        update={
            "input_flags": InputFlags(
                state=input_lint.state,
                reasons=list(input_lint.reasons),
                reason_codes=list(input_lint.reason_codes),
                fixes=list(input_lint.fixes),
                paraphrase_unstable=input_lint.paraphrase_unstable,
            )
        }
    )


def _stamp_instrument_scope(result: SimulationResult, hypothesis: Hypothesis) -> SimulationResult:
    """Stamp the T2 (#311) abstention onto the result, categorically.

    Re-runs the deterministic, zero-LLM instrument-fit detector
    (services.answerability._detect_out_of_scope) on the hypothesis and, when the
    OEC is unresolvable by a first-exposure single-session panel, sets
    `instrument_scope="out_of_scope"` + the named reasons so `verdictFor()` can
    WITHHOLD the ship/no-ship verdict ("NOT ANSWERABLE BY THIS INSTRUMENT").

    Re-running the (pure) detector here — rather than threading a flag from the
    create-time gate through the orchestrator — keeps the plumbing minimal: the
    detector is deterministic, so create-time and score-time agree exactly, and
    the abstention rides into the persisted result_json blob with no DB column /
    migration. This NEVER touches `confidence_score` (panel hard constraint): the
    headline number is computed as today; only the verdict is overridden. A
    `model_copy` keeps the in-scope path byte-identical (defaults unchanged).
    """
    # Lazy import: answerability imports schemas, and keeping it local mirrors the
    # runner's other lazy service imports (no LLM/heavy module pulled at load).
    from sidira_simulator.services.answerability import _detect_out_of_scope

    codes, reasons = _detect_out_of_scope(hypothesis)
    if not codes:
        return result
    return result.model_copy(
        update={
            "instrument_scope": "out_of_scope",
            "out_of_scope_reasons": reasons,
            "out_of_scope_reason_codes": codes,
        }
    )


def screen_v2_enabled() -> bool:
    """Opt-in flag for the pivot's live KILL/PASS/ABSTAIN screen (rewire-C).

    Default OFF (unlike the removed decision-flow, which defaulted ON): the screen
    verdict stays dormant until the frontend renders ``source="calibrated"``
    correctly (PR1b). Any on-token (``1``/``true``/``yes``/``on``) enables it.
    """
    import os

    return os.getenv("SIDIRA_SCREEN_V2", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _stamp_screen_verdict(result: SimulationResult) -> SimulationResult:
    """Stamp the KILL/PASS/ABSTAIN screen verdict onto the result (rewire-C).

    OPT-IN via ``SIDIRA_SCREEN_V2`` (default OFF): off ⇒ a single env read then the
    result unchanged, so ``decision_verdict`` stays None and every run is
    byte-identical to today. On ⇒ derive the verdict from the panel's signed
    ``lift`` plus the structural abstain carriers already stamped above, via the
    pure ``screen_verdict`` producer. Runs LAST so ``instrument_scope`` /
    ``input_flags`` are populated when it reads them. NEVER touches
    ``confidence_score`` (panel hard constraint) — additive, on the result JSON blob.

    Pre-partner there is no fitted calibrator and no operating-point threshold, so
    ``screen_verdict`` can only PASS/ABSTAIN — it CANNOT KILL. Loading a per-client
    calibrator + threshold (#609) is the future hook that turns KILL on.
    """
    if not screen_v2_enabled():
        return result
    from sidira_simulator.services.screen import screen_verdict

    # Direction signal: prefer the explicit two-arm A/B `lift`; fall back to
    # `current_state_delta` (treatment vs the current product state — the natural
    # "ship this change vs the status quo" comparison). Whichever is present
    # carries the sign the screen reads. (Surfaced by the first live end-to-end
    # run: an include_current_state_control sim populates current_state_delta, not
    # lift, so the screen was abstaining on a run that had a clear directional
    # signal.) NOTE: the two live on different scales — `lift` is a fraction,
    # `current_state_delta` is in [-100, +100] — and only the SIGN is used here
    # (direction-only, pre-partner). A fitted calibrator (#609) must be trained on
    # whichever signal a client's runs actually produce.
    signal = result.lift if result.lift is not None else result.current_state_delta

    verdict = screen_verdict(
        lift=signal,
        out_of_scope=result.instrument_scope == "out_of_scope",
        input_abstain=(
            result.input_flags is not None and result.input_flags.state == "abstain"
        ),
        calibrator=None,  # TODO(#609): load the per-client fitted calibrator
        kill_threshold=None,  # TODO(#609): the operating point; None ⇒ KILL disabled
    )
    return result.model_copy(update={"decision_verdict": verdict})


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
