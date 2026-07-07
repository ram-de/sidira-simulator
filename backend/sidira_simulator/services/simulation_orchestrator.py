"""Simulation orchestrator — the seam between the API route and SimulationRunner.

Owns: ID assignment, customer scoping, repo persistence, background task fire,
and the bridge between SimulationRunner's in-memory return value and the DB row.

Why this exists:
- SimulationRunner is producer-of-AgentInstances (knows R2 + LLM, doesn't know DB).
- API route is HTTP-shaped (knows requests + responses, doesn't know LLM).
- This class glues them so neither needs to know about the other.
"""

from __future__ import annotations

import secrets
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import AsyncContextManager

import structlog

from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
from sidira_simulator.adapters.persona_loader import PersonaPackLoader
from sidira_simulator.adapters.repositories import (
    DEFAULT_SETUP_ID,
    AgentInstanceRepo,
    CustomerRepo,
    SimulationRepo,
)
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.input_lint import InputLintVerdict
from sidira_simulator.services.simulation_runner import SimulationRunner

log = structlog.get_logger()

BackgroundOrchestratorFactory = Callable[[], AsyncContextManager["SimulationOrchestrator"]]

# Upper bound (seconds) on the flag-gated §5e decision-flow shadow hook (#542). It
# runs AFTER the sim is already persisted-complete, so this only bounds how long
# the best-effort log may linger — the run itself is never affected.
_DECISION_FLOW_HOOK_TIMEOUT_S = 30.0


class SimulationOrchestrator:
    def __init__(
        self,
        *,
        customer_repo: CustomerRepo,
        simulation_repo: SimulationRepo,
        agent_repo: AgentInstanceRepo,
        persona_loader: PersonaPackLoader | None = None,
        feature_pack_loader: FeaturePackLoader | None = None,
        runner: SimulationRunner | None = None,
        background_orchestrator_factory: BackgroundOrchestratorFactory | None = None,
    ) -> None:
        self._customers = customer_repo
        self._simulations = simulation_repo
        self._agents = agent_repo
        self._personas = persona_loader or PersonaPackLoader()
        self._features = feature_pack_loader or FeaturePackLoader()
        self._runner = runner or SimulationRunner()
        self._background_orchestrator_factory = background_orchestrator_factory

    async def prepare(
        self,
        *,
        customer_id: str,
        hypothesis: Hypothesis,
        population_size: int | None = None,
        sampled_agent_count: int | None = None,
        run_seed: int | None = None,
        treatment_fraction: float | None = None,
        selected_personas: list[str] | None = None,
        model_id: str | None = None,
        setup_id: str = DEFAULT_SETUP_ID,
        parent_simulation_id: str | None = None,
        sample_size: int = 10,
        include_no_persona_control: bool = False,
        include_current_state_control: bool = False,
        input_lint: InputLintVerdict | None = None,
    ):
        """Persist a pending simulation row. Returns sim_id and the run-coroutine.

        The HTTP route is responsible for scheduling the coroutine — via
        FastAPI's BackgroundTasks or asyncio.create_task. Keeping scheduling
        out of the orchestrator means this class stays HTTP-agnostic and is
        trivially testable without TestClient event-loop choreography.
        """
        await self._customers.ensure_exists(customer_id, name=customer_id)

        persona_pack = self._personas.load_latest(customer_id)
        # #215/#245 PR 3a: resolve the latest pack version for the CHOSEN crawl
        # setup. setup_id defaults to "default" → the exact legacy R2 prefix, so
        # an omitted setup_id is byte-identical to pre-#215 prod. A named setup
        # resolves THAT setup's `latest` pointer.
        feature_pack_version = self._features.resolve_latest_version(customer_id, setup_id)

        # Phase 5 #101: eager validation of selected_personas against the
        # active pack. Catches unknown persona_ids at submit time with a
        # clean 400 (POST handler maps ValueError -> 400) instead of failing
        # the background run after the sim row is already persisted. The
        # allocator does the same check defensively, but doing it here means
        # the sim row never even gets created for a bad request.
        if selected_personas is not None:
            pack_ids = {p.id for p in persona_pack.personas}
            unknown = sorted(set(selected_personas) - pack_ids)
            if unknown:
                raise ValueError(
                    f"selected_personas references persona_ids not present "
                    f"in the active Persona Pack ({persona_pack.version}): "
                    f"{unknown}. Known ids: {sorted(pack_ids)}"
                )

        # Phase 2.5 (#5): the runner now does its own allocate()-based stratification
        # over population_size, so we just thread it (plus run_seed for identity
        # reproducibility) through. Legacy `sample_size` is no longer consulted by
        # the runner but kept on this signature as a defaulted no-op so older direct
        # callers don't break at import time.
        effective_population_size = population_size if population_size is not None else sample_size
        # Resolve run_seed BEFORE persisting so the DB row matches the seed the
        # runner will actually use. If we let the runner mint its own default, the
        # row stores NULL while the simulation uses a time-derived seed -- and the
        # caller can never replay it. (codex review P1)
        # Use a 53-bit range so the JSON-encoded value round-trips losslessly
        # through JavaScript clients (Number.MAX_SAFE_INTEGER = 2**53 - 1). A
        # browser reading back time.time_ns() (~1.7e18) and resubmitting it for
        # replay would round the value and hash a different RNG seed. (codex P2)
        resolved_run_seed = run_seed if run_seed is not None else secrets.randbits(53)

        sim_id = str(uuid.uuid4())
        await self._simulations.create(
            sim_id=sim_id,
            customer_id=customer_id,
            persona_pack_version=persona_pack.version,
            feature_pack_version=feature_pack_version,
            hypothesis_json=hypothesis.model_dump(mode="json"),
            population_size=population_size,
            sampled_agent_count=sampled_agent_count,
            run_seed=resolved_run_seed,
            treatment_fraction=treatment_fraction,
            selected_personas=selected_personas,
            model_id=model_id,
            setup_id=setup_id,
            # Phase 8 #43: link this run into a refinement-loop lineage. The
            # column already exists (001_initial); the value is not validated for
            # existence here — a dangling parent simply yields a single-element
            # lineage when GET /simulations/{id} walks upward.
            parent_simulation_id=parent_simulation_id,
        )

        async def run() -> None:
            background_orchestrator = self
            if self._background_orchestrator_factory is not None:
                async with self._background_orchestrator_factory() as orchestrator:
                    await orchestrator._run_in_background(
                        sim_id=sim_id,
                        customer_id=customer_id,
                        hypothesis=hypothesis,
                        population_size=effective_population_size,
                        run_seed=resolved_run_seed,
                        # Pass the API-derived cap so allocate() uses the same number
                        # the row recorded. Otherwise SIDIRA_MAX_AGENTS=0 makes the API
                        # clamp to 1 while allocate() falls back to default 50. (codex P2)
                        max_agents=sampled_agent_count,
                        treatment_fraction=treatment_fraction,
                        selected_personas=selected_personas,
                        model_id=model_id,
                        setup_id=setup_id,
                        include_no_persona_control=include_no_persona_control,
                        include_current_state_control=include_current_state_control,
                        input_lint=input_lint,
                    )
                return

            await background_orchestrator._run_in_background(
                sim_id=sim_id,
                customer_id=customer_id,
                hypothesis=hypothesis,
                population_size=effective_population_size,
                run_seed=resolved_run_seed,
                # Pass the API-derived cap so allocate() uses the same number
                # the row recorded. Otherwise SIDIRA_MAX_AGENTS=0 makes the API
                # clamp to 1 while allocate() falls back to default 50. (codex P2)
                max_agents=sampled_agent_count,
                treatment_fraction=treatment_fraction,
                selected_personas=selected_personas,
                model_id=model_id,
                setup_id=setup_id,
                include_no_persona_control=include_no_persona_control,
                include_current_state_control=include_current_state_control,
                input_lint=input_lint,
            )

        return sim_id, run

    async def get(self, sim_id: str, customer_id: str) -> dict | None:
        """Return the simulation row plus the list of agent_instance_ids."""
        sim = await self._simulations.get(sim_id, customer_id)
        if sim is None:
            return None
        agents = await self._agents.list_for_simulation(sim_id, customer_id)
        sim["agent_instance_ids"] = [a["id"] for a in agents]
        return sim

    async def list_recent(self, customer_id: str, limit: int = 50) -> list[dict]:
        return await self._simulations.list_recent(customer_id, limit)

    async def _run_in_background(
        self,
        *,
        sim_id: str,
        customer_id: str,
        hypothesis: Hypothesis,
        population_size: int,
        run_seed: int | None,
        max_agents: int | None = None,
        treatment_fraction: float | None = None,
        selected_personas: list[str] | None = None,
        model_id: str | None = None,
        setup_id: str = DEFAULT_SETUP_ID,
        include_no_persona_control: bool = False,
        include_current_state_control: bool = False,
        input_lint: InputLintVerdict | None = None,
    ) -> None:
        try:
            await self._simulations.update_status(sim_id, customer_id, "running")

            persona_pack = self._personas.load_latest(customer_id)
            # #215/#245 PR 3a: resolve + load the capability from the SAME crawl
            # setup the request named (and the pending row recorded). Both calls
            # take setup_id so a named-setup sim never silently falls back to the
            # default pack; setup_id defaults to "default" → the legacy prefix,
            # byte-identical to today for every existing internal caller.
            feature_pack_version = self._features.resolve_latest_version(customer_id, setup_id)
            capability = self._features.load_capability(
                customer_id, feature_pack_version, hypothesis.capability_name, setup_id
            )

            # SimulationRunner already mints its own sim_id; we override here so the DB
            # row, agent_instances rows, and R2 paths all share the same id.
            await self._run_with_id(
                sim_id=sim_id,
                customer_id=customer_id,
                persona_pack=persona_pack,
                capability=capability,
                feature_pack_version=feature_pack_version,
                hypothesis=hypothesis,
                population_size=population_size,
                run_seed=run_seed,
                max_agents=max_agents,
                treatment_fraction=treatment_fraction,
                selected_personas=selected_personas,
                model_id=model_id,
                include_no_persona_control=include_no_persona_control,
                include_current_state_control=include_current_state_control,
                input_lint=input_lint,
            )

            # §5e decision-flow router (#542). ADDITIVE + ON BY DEFAULT: unless
            # SIDIRA_DECISION_FLOW_ENABLED is set to an off-token, compute a
            # grounded-first DecisionResult and emit it as a structured decision log
            # ALONGSIDE the existing run. The result is not threaded into the sim or
            # the runner; it is surfaced only as the read-side decision_verdict
            # sidecar (#545). Deliberately run AFTER the sim is already
            # persisted-complete and bounded by a timeout, so this log-only hook can
            # NEVER delay the run or keep it 'running' (codex P2). When the flag is
            # disabled (kill-switch) this is a single cheap env read that returns
            # immediately: no extra work, no extra imports, no thread offload.
            await self._maybe_log_decision_flow(
                sim_id=sim_id,
                customer_id=customer_id,
                hypothesis=hypothesis,
                pack_version=persona_pack.version,
                setup_id=setup_id,
                model_id=model_id,
            )

        except Exception as exc:
            log.exception("simulation.failed", sim_id=sim_id, error=str(exc))
            await self._simulations.update_status(
                sim_id,
                customer_id,
                "failed",
                error=str(exc)[:1000],
                completed_at=datetime.now(timezone.utc),
            )

    async def _maybe_log_decision_flow(
        self,
        *,
        sim_id: str,
        customer_id: str,
        hypothesis: Hypothesis,
        pack_version: str,
        setup_id: str,
        model_id: str | None,
    ) -> None:
        """Flag-gated §5e decision-flow hook (#542). Never affects the run.

        On by default (``SIDIRA_DECISION_FLOW_ENABLED``); an off-token disables it,
        making this a single env read then an immediate return. When on (default),
        load the estimability manifest beside the persona pack, run the
        grounded-first router (`decide`), and structlog the result. Deliberately additive: the
        `DecisionResult` is only logged — it is NOT written to the sim row, passed
        to the runner, or surfaced in the API response (response-shape wiring is
        #545). Wrapped so any failure here can never break the simulation.

        The synchronous work — a blocking R2 manifest read and the translator's
        blocking LLM ``chat_json`` call inside ``decide`` — is offloaded via
        ``asyncio.to_thread`` so it never stalls the event loop this coroutine runs
        on (codex P2). When the flag is off nothing is offloaded: the env read and
        return happen inline and cost nothing.
        """
        # Lazy import + cheap env read stay inline: return immediately when off so
        # the default (prod) path imports nothing extra and touches no thread pool.
        try:
            from sidira_simulator.services.decision_flow import decision_flow_enabled

            if not decision_flow_enabled():
                return
        except Exception as exc:  # noqa: BLE001 — a shadow hook must never break a run.
            log.warning(
                "simulation.decision_flow_hook_failed",
                customer_id=customer_id,
                error=str(exc),
                exc_type=type(exc).__name__,
            )
            return

        # Offload the blocking manifest read + LLM translate/decide to a worker
        # thread (so the event loop is never stalled) AND bound it with a timeout
        # (so a slow/hanging manifest read or LLM call can never keep this shadow
        # hook — or the background job — alive indefinitely). codex P2.
        import asyncio

        try:
            await asyncio.wait_for(
                asyncio.to_thread(
                    self._run_decision_flow_sync,
                    sim_id=sim_id,
                    customer_id=customer_id,
                    hypothesis=hypothesis,
                    pack_version=pack_version,
                    setup_id=setup_id,
                    model_id=model_id,
                ),
                timeout=_DECISION_FLOW_HOOK_TIMEOUT_S,
            )
        except TimeoutError:
            # The worker thread keeps running to completion in the pool; we simply
            # stop waiting on it. A shadow log timing out never affects the run.
            log.warning(
                "simulation.decision_flow_hook_timeout",
                customer_id=customer_id,
                timeout_s=_DECISION_FLOW_HOOK_TIMEOUT_S,
            )
        except Exception as exc:  # noqa: BLE001 — a shadow hook must never break a run.
            log.warning(
                "simulation.decision_flow_hook_failed",
                customer_id=customer_id,
                error=str(exc),
                exc_type=type(exc).__name__,
            )

    def _run_decision_flow_sync(
        self,
        *,
        sim_id: str,
        customer_id: str,
        hypothesis: Hypothesis,
        pack_version: str,
        setup_id: str,
        model_id: str | None,
    ) -> None:
        """Blocking body of the decision-flow hook (runs in a worker thread).

        Never raises (mirrors ``decide``'s contract); the async wrapper also guards.

        The estimability manifest is persona-pack-scoped (it sits beside the persona
        pack in R2, keyed by ``pack_version`` — #540), but it records the crawl
        ``setup_id`` it was BUILT from. This run may target a DIFFERENT setup whose
        feature store has different columns/effects; logging a decision against a
        wrong-setup manifest would be misleading. So we guard: on a setup mismatch
        we treat the manifest as ABSENT (pass ``manifest=None``) → the router
        abstains (Step 2) rather than deciding on the wrong setup's data.
        """
        try:
            from sidira_simulator.services.decision_flow import (
                decide,
                verdict_from_decision,
                write_decision_verdict,
            )
            from sidira_simulator.services.grounded_predictor import (
                load_estimability_manifest,
            )

            manifest = load_estimability_manifest(customer_id, pack_version)
            if manifest is not None and manifest.setup_id != setup_id:
                log.info(
                    "simulation.decision_flow_setup_mismatch",
                    customer_id=customer_id,
                    pack_version=pack_version,
                    run_setup_id=setup_id,
                    manifest_setup_id=manifest.setup_id,
                )
                manifest = None  # abstain rather than decide on the wrong setup
            available_columns = (
                [c.name for c in manifest.columns] if manifest is not None else []
            )
            # The real 3-model heterogeneous council (#543) plugs into the router's
            # council seam. Building it validates bias diversity and may resolve
            # provider clients lazily, so guard it: a diversity-assertion failure or
            # a missing key degrades to the router's default NullCouncil (logged),
            # never breaks this shadow hook. Only reached when the flag is already on.
            council = None
            try:
                from sidira_simulator.services.council import build_default_council

                council = build_default_council()
            except Exception as exc:  # noqa: BLE001 — degrade to NullCouncil; never break the run
                log.warning(
                    "simulation.decision_flow_council_unavailable",
                    customer_id=customer_id,
                    error=str(exc),
                    exc_type=type(exc).__name__,
                )
            # Best-effort read of the human lever-review sidecar (beside the pack in
            # R2, same store as the verdict write below). A 'rejected' review
            # force-abstains its lever inside `decide`; a 'vouched' one never
            # upgrades. Guarded so a sidecar read failure NEVER breaks the run.
            reviews = None
            try:
                from sidira_simulator.adapters.r2 import get_store
                from sidira_simulator.services.lever_review_store import (
                    read_lever_reviews,
                )

                reviews = read_lever_reviews(get_store(), customer_id, pack_version)
            except Exception as exc:  # noqa: BLE001 — an optional read must never break the run.
                log.warning(
                    "simulation.lever_reviews_read_failed",
                    customer_id=customer_id,
                    pack_version=pack_version,
                    error=str(exc),
                )
            result = decide(
                hypothesis,
                available_columns,
                customer_id,
                pack_version,
                model_id=model_id,
                council=council,
                manifest=manifest,
                lever_reviews=reviews,
            )
            log.info(
                "simulation.decision_flow",
                customer_id=customer_id,
                pack_version=pack_version,
                capability=hypothesis.capability_name,
                source=result.source,
                direction=result.direction,
                caution=result.caution,
                label=result.label,
                watchdog_verdict=result.watchdog_verdict,
            )

            # #545: persist the direction-only verdict as a SIDECAR artifact beside
            # the run (NOT into result_json). The run's result_json was already
            # persisted-complete before this hook ran (the #542 no-critical-path
            # guarantee), so we write the verdict as its own R2 object rather than
            # mutating the finished result. Best-effort: a store failure logs and
            # continues — this shadow hook must never affect the run. The GET detail
            # handler reads it back (also best-effort) to populate the additive
            # `decision_verdict` field. Only reached when the flag is already on.
            try:
                from sidira_simulator.adapters.r2 import get_store

                write_decision_verdict(
                    get_store(), customer_id, sim_id, verdict_from_decision(result)
                )
            except Exception as exc:  # noqa: BLE001 — sidecar persist must never break a run.
                log.warning(
                    "simulation.decision_flow_verdict_persist_failed",
                    sim_id=sim_id,
                    customer_id=customer_id,
                    error=str(exc),
                    exc_type=type(exc).__name__,
                )
        except Exception as exc:  # noqa: BLE001 — a shadow hook must never break a run.
            log.warning(
                "simulation.decision_flow_hook_failed",
                customer_id=customer_id,
                error=str(exc),
                exc_type=type(exc).__name__,
            )

    async def _run_with_id(
        self,
        *,
        sim_id: str,
        customer_id: str,
        persona_pack,
        capability,
        feature_pack_version: str,
        hypothesis: Hypothesis,
        population_size: int,
        run_seed: int | None,
        max_agents: int | None = None,
        treatment_fraction: float | None = None,
        selected_personas: list[str] | None = None,
        model_id: str | None = None,
        include_no_persona_control: bool = False,
        include_current_state_control: bool = False,
        input_lint: InputLintVerdict | None = None,
    ) -> None:
        """Call SimulationRunner with a pre-assigned sim_id; persist agents + result."""
        simulation = await self._runner.run(
            customer_id=customer_id,
            persona_pack=persona_pack,
            capability=capability,
            feature_pack_version=feature_pack_version,
            hypothesis=hypothesis,
            population_size=population_size,
            run_seed=run_seed,
            max_agents=max_agents,
            sim_id=sim_id,
            treatment_fraction=treatment_fraction,
            selected_personas=selected_personas,
            model_id=model_id,
            include_no_persona_control=include_no_persona_control,
            include_current_state_control=include_current_state_control,
            input_lint=input_lint,
        )

        # Persist agent_instances rows using the records the runner exposed.
        for materialization_index, record in enumerate(
            getattr(self._runner, "_last_run_agent_records", [])
        ):
            await self._agents.create(
                {
                    "id": record.agent_id,
                    "customer_id": customer_id,
                    "simulation_id": sim_id,
                    "persona_id": record.persona_id,
                    "persona_pack_version": persona_pack.version,
                    "persona_name": record.persona_name,
                    "created_at": record.created_at,
                    "last_active_at": record.created_at,
                    "message_count": 0,
                    "materialization_index": materialization_index,
                    "arm": record.arm,
                }
            )

        await self._simulations.update_status(
            sim_id,
            customer_id,
            simulation.status.value,
            result_json=simulation.result.model_dump(mode="json") if simulation.result else None,
            completed_at=datetime.now(timezone.utc),
        )
