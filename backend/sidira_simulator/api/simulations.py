"""Simulation routes — submit a hypothesis, fetch a simulation, poll live state."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from sidira_simulator.adapters.base import ArtifactNotFound
from sidira_simulator.adapters.llm import resolve_model_id
from sidira_simulator.adapters.r2 import get_store
from sidira_simulator.adapters.repositories import AgentInstanceRepo
from sidira_simulator.api.deps import (
    current_customer_id,
    get_agent_repo,
    get_input_lint_chat_client,
    get_orchestrator,
)
from sidira_simulator.schemas.simulation import (
    ArmSplit,
    Hypothesis,
    LineageEntry,
    Simulation,
    SimulationComparison,
    SimulationRef,
    SimulationRequest,
    SimulationResult,
    SimulationStatus,
    WeaknessCategoryDiff,
)
from sidira_simulator.services.answerability import assess_answerability
from sidira_simulator.services.decision_flow import (
    decision_flow_enabled,
    read_decision_verdict,
)
from sidira_simulator.services.input_lint import _detect_leading_framing, assess_input_lint
from sidira_simulator.services.runtime_config import resolve_max_agents_per_simulation
from sidira_simulator.services.run_state import RunStateStore, SimulationRunState
from sidira_simulator.services.simulation_orchestrator import SimulationOrchestrator

router = APIRouter(prefix="/simulations", tags=["simulations"])


class CreateSimulationResponse(BaseModel):
    id: str
    status: SimulationStatus
    poll_url: str


class PreflightRequest(BaseModel):
    """Lightweight authoring-time pre-flight check (epic #309, T4 / #313).

    Carries just the `Hypothesis` the wizard is composing — no population,
    personas, model, or arm config — because the pre-flight verdict depends
    only on the hypothesis surface. `run_as_generic_reception` mirrors the
    POST /simulations override so the wizard can preview "would this still
    block if I run as generic-reception?" without resubmitting the real run.
    """

    hypothesis: Hypothesis
    run_as_generic_reception: bool = False


class PreflightResponse(BaseModel):
    """The deterministic, zero-LLM pre-flight verdict (T4 / #313).

    A read-only mirror of the SAME `assess_answerability` (T1) verdict the
    POST path routes on, plus the SEPARABLE deterministic leading-framing
    lint (`input_lint._detect_leading_framing`). It lets the wizard catch
    `needs_input` / `out_of_scope` / leading-framing AT THE KEYBOARD, before
    submit, so the PM never hits the POST 422 cold.

    Crucially it does NOT run the simulation, does NOT spend an LLM token, and
    does NOT call the T3 LLM judge (`assess_input_lint`) — only the two cheap
    deterministic checks. It carries NO number and never touches
    `confidence_score` (panel hard constraint): it ROUTES, exactly like T1.

    `state` / `reasons` / `fixes` / `reason_codes` / `allow_override` are the
    `AnswerabilityVerdict` verbatim; `override_field` matches the POST 422
    payload so the wizard reuses one override affordance. `leading_framing_*`
    carry the deterministic framing lint (advisory, NOT a block — the T3 LLM
    judge that finalizes amber/red runs at submit time, never here).
    """

    state: str
    reasons: list[str]
    fixes: list[str]
    reason_codes: list[str]
    allow_override: bool
    override_field: str = "run_as_generic_reception"
    leading_framing_reasons: list[str]
    leading_framing_fixes: list[str]


class SimulationListItem(BaseModel):
    id: str
    status: SimulationStatus
    created_at: datetime
    completed_at: datetime | None = None
    hypothesis_prose: str
    capability_name: str
    confidence_score: float | None = None


@router.get("", response_model=list[SimulationListItem])
async def list_simulations(
    customer_id: str = Depends(current_customer_id),
    orchestrator: SimulationOrchestrator = Depends(get_orchestrator),
    limit: int = 50,
) -> list[SimulationListItem]:
    """Recent simulations for the current customer, newest first."""
    rows = await orchestrator.list_recent(customer_id, limit=limit)
    items: list[SimulationListItem] = []
    for row in rows:
        hyp = row.get("hypothesis_json") or {}
        result = row.get("result_json") or {}
        items.append(
            SimulationListItem(
                id=row["id"],
                status=(
                    SimulationStatus(row["status"])
                    if row.get("status")
                    else SimulationStatus.PENDING
                ),
                created_at=row.get("created_at") or datetime.utcnow(),
                completed_at=row.get("completed_at"),
                hypothesis_prose=hyp.get("prose", ""),
                capability_name=hyp.get("capability_name", ""),
                confidence_score=result.get("confidence_score"),
            )
        )
    return items


@router.post("/preflight", response_model=PreflightResponse)
async def preflight_simulation(
    payload: PreflightRequest,
    customer_id: str = Depends(current_customer_id),
) -> PreflightResponse:
    """Authoring-time pre-flight check (epic #309, T4 / #313).

    Deterministic, zero-LLM, synchronous. Runs the SAME `assess_answerability`
    (T1) gate the POST path routes on, plus the SEPARABLE deterministic
    leading-framing lint, and returns the verdict WITHOUT persisting or running
    a simulation and WITHOUT calling the T3 LLM judge. The wizard calls this
    live as the PM authors so `needs_input` / `out_of_scope` / leading framing
    are caught at the keyboard, not at the POST 422.

    It reuses `assess_answerability` and `_detect_leading_framing` VERBATIM — no
    forked vocabulary — so the preview can never drift from the POST gate. It
    ROUTES on a categorical verdict and never touches `confidence_score` (panel
    hard constraint). Auth-gated like every route so it can't be probed
    anonymously, but it reads nothing customer-specific (the verdict depends
    only on the supplied hypothesis).
    """
    verdict = assess_answerability(
        payload.hypothesis,
        allow_generic_reception=payload.run_as_generic_reception,
    )
    framing_reasons, framing_fixes = _detect_leading_framing(payload.hypothesis.prose)
    return PreflightResponse(
        state=verdict.state,
        reasons=verdict.reasons,
        fixes=verdict.fixes,
        reason_codes=verdict.reason_codes,
        allow_override=verdict.allow_override,
        leading_framing_reasons=framing_reasons,
        leading_framing_fixes=framing_fixes,
    )


@router.post(
    "",
    response_model=CreateSimulationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_simulation(
    payload: SimulationRequest,
    background_tasks: BackgroundTasks,
    customer_id: str = Depends(current_customer_id),
    orchestrator: SimulationOrchestrator = Depends(get_orchestrator),
    input_lint_chat_client=Depends(get_input_lint_chat_client),
) -> CreateSimulationResponse:
    """Accepts a hypothesis. Returns 202 + simulation_id; runs after the response is sent."""
    # #310 / T1: deterministic, zero-LLM pre-flight answerability gate. Runs
    # PRE-PERSIST, before orchestrator.prepare and before any LLM token is
    # spent. On `needs_input` (and no override set) we 422 with a
    # refinement-shaped payload (reasons + fixes) so the wizard can guide the
    # PM to a one-field fix, signalling whether a generic-reception override is
    # available. It ROUTES on a categorical verdict and never touches
    # confidence_score. See services/answerability.py for the two checks.
    verdict = assess_answerability(
        payload.hypothesis,
        allow_generic_reception=payload.run_as_generic_reception,
    )
    if verdict.state == "needs_input":
        raise HTTPException(
            status_code=422,
            detail={
                "error": "needs_input",
                "reasons": verdict.reasons,
                "fixes": verdict.fixes,
                "reason_codes": verdict.reason_codes,
                # When True, the PM can resubmit with run_as_generic_reception=true
                # to proceed (sentiment-only, not OEC-aligned). False means the
                # blocking defect (structural-invisibility) must be fixed first.
                "allow_override": verdict.allow_override,
                "override_field": "run_as_generic_reception",
            },
        )
    # #311 / T2: `out_of_scope` ABSTAINS — it does NOT block and does NOT 422.
    # The run proceeds and the score is still computed; the ship/no-ship verdict
    # is categorically WITHHELD at result time ("NOT ANSWERABLE BY THIS
    # INSTRUMENT"). The detector is deterministic and re-run inside the runner's
    # `_score` so the abstention rides into the persisted SimulationResult
    # (`instrument_scope` / `out_of_scope_reasons`) with no orchestrator
    # threading and no DB column. There is NO confidence_score discount — the
    # override is categorical (panel hard constraint). We deliberately fall
    # through to the normal run path here.

    # Cheap synchronous validation (model_id) runs BEFORE the LLM input lint so an
    # unsupported explicit model returns 400 without spending judge tokens.
    try:
        model_id = resolve_model_id(
            payload.model_id,
            require_available=payload.model_id is not None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # #312 / T3: pre-flight ORDINAL input lint (LLM judge + deterministic
    # leading-framing lint + paraphrase-abstain). Runs AFTER the T1/T2 gate and
    # the cheap model_id check so a structural `needs_input` 422 or a 400 bad
    # model short-circuits before any token is spent. NEVER 422s — semantic
    # judgments are disclose-and-run: green runs silently; amber/red/abstain
    # stamp `input_flags` on the result card and offer refinement (the run always
    # proceeds). The verdict is threaded through the orchestrator into the runner,
    # which stamps `input_flags` onto SimulationResult and moves the refinement
    # trigger earlier. It ROUTES and never touches confidence_score (panel hard
    # constraint). On any judge failure the lint degrades to the deterministic
    # framing lint alone — a paying user is never blocked on a semantic judgment.
    input_lint = await assess_input_lint(
        payload.hypothesis, chat_client=input_lint_chat_client
    )

    # Phase 2.5: population_size is the modeled userbase; the materialized
    # sample is capped by the backend's effective max-agent setting. Phase 4.6
    # #100 shares this resolver with /config/limits so the wizard preview
    # cannot drift from the POST path.
    max_agents = resolve_max_agents_per_simulation()
    # The env cap stays the hard cost ceiling. An optional per-request
    # `sampled_agent_count` lets the user LOWER the realized agent count below
    # the cap (a second knob alongside population_size); it can never raise the
    # run above the env ceiling. None reproduces the historical derive-from-
    # population behavior. min() over all three keeps the realized sample bounded
    # by the smallest of: modeled population, user request, env cap.
    requested_agents = payload.sampled_agent_count
    effective_cap = (
        min(requested_agents, max_agents) if requested_agents is not None else max_agents
    )
    derived_sample_size = max(1, min(payload.population_size, effective_cap))

    # Phase 4.6 #88: A/B mode persistence. The arm_split is only RECORDED in
    # this PR (#88) — the dual-arm execution path lives in #89. Persisting
    # without using lets the row tell the truth from day one and avoids a
    # subsequent migration when #89 lands.
    treatment_fraction = payload.arm_split.treatment_fraction if payload.arm_split else None

    # Phase 8 #43: a refinement run links to its parent. Validate OWNERSHIP
    # before create — the column is a plain FK to simulations.id, so an unchecked
    # parent would (a) succeed for an existing foreign id but fail the FK insert
    # for a missing one, leaking cross-customer existence by timing/outcome, and
    # (b) persist a lineage edge to a sim this customer can't see. Same
    # non-leaking 404 as /compare: missing and foreign both 404 identically
    # (codex P1).
    if payload.parent_simulation_id is not None:
        parent_row = await orchestrator.get(payload.parent_simulation_id, customer_id)
        if parent_row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Parent simulation {payload.parent_simulation_id} not found",
            )

    try:
        sim_id, run = await orchestrator.prepare(
            customer_id=customer_id,
            hypothesis=payload.hypothesis,
            population_size=payload.population_size,
            sampled_agent_count=derived_sample_size,
            run_seed=payload.run_seed,
            treatment_fraction=treatment_fraction,
            selected_personas=payload.selected_personas,
            model_id=model_id,
            # #215/#245 PR 3a: thread the chosen crawl setup so the orchestrator
            # resolves THAT setup's pack (already validated by the request schema's
            # is_safe_setup_id field validator). Omitted → "default" → legacy path.
            setup_id=payload.setup_id,
            # Phase 8 #43: link this run into a refinement-loop lineage. None for
            # fresh runs; the lineage chain is walked at GET /simulations/{id}.
            parent_simulation_id=payload.parent_simulation_id,
            include_no_persona_control=payload.include_no_persona_control,
            include_current_state_control=payload.include_current_state_control,
            input_lint=input_lint,
        )
    except ArtifactNotFound as exc:
        # No persona pack or feature pack for this customer yet.
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        # Phase 5 #101: selected_personas referenced unknown persona_ids.
        # Eager-validated in orchestrator.prepare() against the active pack.
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    background_tasks.add_task(run)
    return CreateSimulationResponse(
        id=sim_id,
        status=SimulationStatus.PENDING,
        poll_url=f"/simulations/{sim_id}/state",
    )


# Phase 8 #42: refinement-loop compare. Constants + helpers for the weakness-
# category and refinement-suggestion diffs.

# The closed set of completed states a sim must be in to be comparable. A
# pending/running/failed sim has no stable result to diff, so compare 404s on it
# (matching the "either sim doesn't exist, isn't owned, or isn't completed"
# contract) rather than diffing a half-built result.
_COMPARABLE_STATUSES = {SimulationStatus.COMPLETE.value}


def _weakness_counts_by_category(result_json: dict | None) -> dict[str, dict]:
    """Aggregate a result's weaknesses BY CATEGORY.

    Returns {category -> {"agent_count": int, "frequency": float | None}}.
    `agent_count` sums each row's TRUE backing count (`support_count`, falling
    back to `len(supporting_agent_ids)` for legacy rows without it) across every
    weakness row of the category (a category can surface as multiple rows).
    `supporting_agent_ids` is capped for display, so summing its length would
    under-report and could mark a materially-changed weakness as "unchanged"
    (codex P2). `frequency` is the max
    observed frequency for the category (None when no row carried one — e.g. the
    structural `underpowered_design` flag). The diff is keyed on `category`
    (the closed Weakness Literal), so "the wrong_cohort weakness got fixed" is a
    stable, machine-comparable signal.
    """
    counts: dict[str, dict] = {}
    for w in (result_json or {}).get("weaknesses") or []:
        if not isinstance(w, dict):
            continue
        category = w.get("category")
        if not category:
            continue
        entry = counts.setdefault(category, {"agent_count": 0, "frequency": None})
        support_count = w.get("support_count")
        if support_count is None:
            support_count = len(w.get("supporting_agent_ids") or [])
        entry["agent_count"] += support_count
        freq = w.get("frequency")
        if freq is not None:
            entry["frequency"] = freq if entry["frequency"] is None else max(entry["frequency"], freq)
    return counts


def _positive_sentiment_share(result_json: dict | None) -> float | None:
    """Share of per-agent analyses with positive sentiment, or None.

    None when the result carries no per_agent_analyses (e.g. a pre-#51
    result_json), so the comparison's sentiment shift is omitted rather than
    fabricated from missing data.
    """
    analyses = (result_json or {}).get("per_agent_analyses") or []
    if not analyses:
        return None
    positive = sum(1 for a in analyses if isinstance(a, dict) and a.get("sentiment") == "positive")
    return positive / len(analyses)


def _comparison_ref(row: dict) -> SimulationRef:
    """Build the compact SimulationRef header for one side of a comparison."""
    return SimulationRef(
        id=row["id"],
        status=(
            SimulationStatus(row["status"]) if row.get("status") else SimulationStatus.PENDING
        ),
        confidence_score=_row_confidence_score(row),
        hypothesis_label=_hypothesis_label(row.get("hypothesis_json")),
    )


@router.get("/compare", response_model=SimulationComparison)
async def compare_simulations(
    old: str,
    new: str,
    customer_id: str = Depends(current_customer_id),
    orchestrator: SimulationOrchestrator = Depends(get_orchestrator),
) -> SimulationComparison:
    """Structured old→new diff for the refinement loop (Phase 8 #42).

    Both sims must be owned by the requesting customer AND completed, else 404
    (we never disclose whether a foreign id exists). The diff is purely
    descriptive — score delta + weakness-category diff (appeared / disappeared /
    changed) + refinement-suggestion deltas + an optional sentiment shift — built
    from the two persisted results. Nothing is re-run and no new score computed.

    Registered BEFORE `/{simulation_id}` so "compare" is matched as this route,
    not captured as a simulation_id path param.
    """
    old_row = await orchestrator.get(old, customer_id)
    new_row = await orchestrator.get(new, customer_id)
    # Customer-scoped 404: a missing OR not-owned sim returns None from
    # orchestrator.get (it enforces the customer match). We 404 without saying
    # which side failed, so a cross-customer probe can't enumerate ids.
    for row in (old_row, new_row):
        if row is None or row.get("status") not in _COMPARABLE_STATUSES:
            raise HTTPException(
                status_code=404,
                detail="Both simulations must exist, be owned by you, and be completed.",
            )

    old_result = old_row.get("result_json") or {}
    new_result = new_row.get("result_json") or {}

    # ── Headline score movement ──
    old_score = _row_confidence_score(old_row)
    new_score = _row_confidence_score(new_row)
    score_delta = (
        new_score - old_score if old_score is not None and new_score is not None else None
    )

    # ── Weakness diff BY CATEGORY ──
    old_counts = _weakness_counts_by_category(old_result)
    new_counts = _weakness_counts_by_category(new_result)
    diffs: list[WeaknessCategoryDiff] = []
    appeared: list[str] = []
    disappeared: list[str] = []
    changed: list[str] = []
    for category in sorted(set(old_counts) | set(new_counts)):
        old_entry = old_counts.get(category)
        new_entry = new_counts.get(category)
        old_n = old_entry["agent_count"] if old_entry else 0
        new_n = new_entry["agent_count"] if new_entry else 0
        if old_entry is None and new_entry is not None:
            change = "appeared"
            appeared.append(category)
        elif old_entry is not None and new_entry is None:
            change = "disappeared"
            disappeared.append(category)
        elif old_n != new_n:
            change = "changed"
            changed.append(category)
        else:
            change = "unchanged"
        diffs.append(
            WeaknessCategoryDiff(
                category=category,
                change=change,
                old_agent_count=old_n,
                new_agent_count=new_n,
                agent_count_delta=new_n - old_n,
                old_frequency=old_entry["frequency"] if old_entry else None,
                new_frequency=new_entry["frequency"] if new_entry else None,
            )
        )

    # ── Refinement-suggestion deltas (set-diffed on the raw strings) ──
    old_suggestions = list(old_result.get("refinement_suggestions") or [])
    new_suggestions = list(new_result.get("refinement_suggestions") or [])
    old_set = set(old_suggestions)
    new_set = set(new_suggestions)
    added = [s for s in new_suggestions if s not in old_set]
    resolved = [s for s in old_suggestions if s not in new_set]

    # ── Optional overall sentiment shift ──
    old_pos = _positive_sentiment_share(old_result)
    new_pos = _positive_sentiment_share(new_result)
    sentiment_delta = (
        new_pos - old_pos if old_pos is not None and new_pos is not None else None
    )

    return SimulationComparison(
        old=_comparison_ref(old_row),
        new=_comparison_ref(new_row),
        old_confidence_score=old_score,
        new_confidence_score=new_score,
        confidence_score_delta=score_delta,
        weakness_category_diffs=diffs,
        weakness_categories_appeared=appeared,
        weakness_categories_disappeared=disappeared,
        weakness_categories_changed=changed,
        old_refinement_suggestions=old_suggestions,
        new_refinement_suggestions=new_suggestions,
        refinement_suggestions_added=added,
        refinement_suggestions_resolved=resolved,
        old_sentiment_positive_share=old_pos,
        new_sentiment_positive_share=new_pos,
        sentiment_positive_share_delta=sentiment_delta,
    )


# Phase 8 #43: refinement-loop lineage. The chain is bounded on two axes so a
# self-referential or accidentally-circular parent pointer (or a maliciously
# crafted one) can never spin the request handler: a hard depth cap AND a
# seen-set cycle guard. The cap is the customer-facing promise of how many
# refinement iterations a single GET surfaces; deeper history is reachable by
# fetching an ancestor directly.
_LINEAGE_MAX_DEPTH = 10

# Short prose prefix length for a timeline node label. Long enough to recognise
# the hypothesis, short enough for a compact node; trimmed to a word boundary.
_HYPOTHESIS_LABEL_CHARS = 80


def _hypothesis_label(hypothesis_json: dict | None) -> str | None:
    """Trim a hypothesis's prose to a short, word-boundary timeline label."""
    if not hypothesis_json:
        return None
    prose = (hypothesis_json.get("prose") or "").strip()
    if not prose:
        return None
    if len(prose) <= _HYPOTHESIS_LABEL_CHARS:
        return prose
    clipped = prose[:_HYPOTHESIS_LABEL_CHARS].rsplit(" ", 1)[0].rstrip()
    return f"{clipped}…"


def _row_confidence_score(row: dict) -> float | None:
    """Pull the headline confidence_score off a persisted sim row, if scored."""
    result = row.get("result_json") or {}
    return result.get("confidence_score")


async def _walk_lineage(
    row: dict,
    customer_id: str,
    orchestrator: SimulationOrchestrator,
) -> list[LineageEntry]:
    """Walk a sim's `parent_simulation_id` chain upward into a lineage list.

    Nearest-ancestor-first (the direct parent at index 0). Customer-scoped: an
    ancestor not owned by / visible to the requesting customer terminates the
    walk (orchestrator.get already enforces the customer match and returns None
    for a foreign or missing row). Depth-capped at `_LINEAGE_MAX_DEPTH` and
    cycle-safe via a seen-set so a circular parent pointer stops gracefully
    instead of looping forever. The starting row itself is NOT included.
    """
    lineage: list[LineageEntry] = []
    seen: set[str] = {row["id"]}
    parent_id = row.get("parent_simulation_id")

    while parent_id is not None and len(lineage) < _LINEAGE_MAX_DEPTH:
        if parent_id in seen:
            # Cycle: a sim points (directly or transitively) back at one we've
            # already visited. Stop gracefully rather than looping forever.
            break
        seen.add(parent_id)
        ancestor = await orchestrator.get(parent_id, customer_id)
        if ancestor is None:
            # Dangling pointer or an ancestor owned by another customer — the
            # walk ends here, never leaking a foreign sim into the chain.
            break
        lineage.append(
            LineageEntry(
                id=ancestor["id"],
                parent_simulation_id=ancestor.get("parent_simulation_id"),
                status=(
                    SimulationStatus(ancestor["status"])
                    if ancestor.get("status")
                    else SimulationStatus.PENDING
                ),
                confidence_score=_row_confidence_score(ancestor),
                hypothesis_label=_hypothesis_label(ancestor.get("hypothesis_json")),
            )
        )
        parent_id = ancestor.get("parent_simulation_id")

    return lineage


@router.get("/{simulation_id}", response_model=Simulation)
async def get_simulation(
    simulation_id: str,
    customer_id: str = Depends(current_customer_id),
    orchestrator: SimulationOrchestrator = Depends(get_orchestrator),
) -> Simulation:
    row = await orchestrator.get(simulation_id, customer_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} not found")

    # Phase 8 #43: walk the refinement-loop lineage upward (depth-capped,
    # cycle-safe, customer-scoped). Empty for un-parented runs.
    lineage = await _walk_lineage(row, customer_id, orchestrator)

    result = SimulationResult(**row["result_json"]) if row.get("result_json") else None

    # #545: surface the direction-only decision verdict when its sidecar exists.
    # ADDITIVE + off-by-default: only read the sidecar when the decision flow is
    # enabled (the same flag that writes it), so a flag-off run does ZERO extra
    # work here and the response is byte-identical to today — no R2 GET, field
    # stays None. Best-effort: a missing/malformed sidecar → None (never a 500).
    # The read (and R2 store construction) is a blocking network call, so it is
    # offloaded to a worker thread to keep it off the event loop (codex P2, mirrors
    # the orchestrator hook's asyncio.to_thread). read_decision_verdict never raises.
    if result is not None and decision_flow_enabled():
        verdict = await asyncio.to_thread(
            lambda: read_decision_verdict(get_store(), customer_id, simulation_id)
        )
        if verdict is not None:
            result.decision_verdict = verdict

    # Phase 4.6 #88: surface arm_split on GET so the frontend can branch
    # on "was this an A/B run" without inspecting result_json.
    arm_split = (
        ArmSplit(treatment_fraction=row["treatment_fraction"])
        if row.get("treatment_fraction") is not None
        else None
    )

    return Simulation(
        id=row["id"],
        customer_id=row["customer_id"],
        created_at=row["created_at"] or datetime.utcnow(),
        status=SimulationStatus(row["status"]) if row["status"] else SimulationStatus.PENDING,
        persona_pack_version=row["persona_pack_version"],
        feature_pack_version=row["feature_pack_version"],
        # #215/#245 PR 3a: surface which crawl setup this sim resolved its pack
        # from. Legacy rows backfilled to "default" (migration 017); `.get` with a
        # default keeps the in-memory repo + any pre-migration dict resilient.
        setup_id=row.get("setup_id", "default"),
        hypothesis=row["hypothesis_json"],
        # Phase 8 #43: refinement-loop lineage (parent pointer + walked chain).
        parent_simulation_id=row.get("parent_simulation_id"),
        lineage=lineage,
        population_size=row.get("population_size"),
        sampled_agent_count=row.get("sampled_agent_count"),
        run_seed=row.get("run_seed"),
        arm_split=arm_split,
        # Phase 5 #101: surface the persisted persona filter on GET so the
        # result-page cohort banner can render. None = unfiltered (today's
        # behavior); the frontend branches on null to hide the banner.
        selected_personas=row.get("selected_personas"),
        model_id=row.get("model_id"),
        agent_instance_ids=row.get("agent_instance_ids", []),
        result=result,
    )


class AgentSummary(BaseModel):
    """Lightweight per-agent row for the simulation detail page.

    Just enough for the persona-grouped table (#51). Full agent state +
    conversation history lives behind GET /agents/{id}, which lands with
    Phase 4 chat. Pulling the summary directly off the metadata repo means
    the frontend makes one call instead of N=50.

    `sentiment` + `top_quote` join the metadata row against
    `simulation.result_json.per_agent_analyses`, which the runner populates
    at score time. Both are None for agents whose simulation hasn't
    completed yet, OR for sims that ran before #51 landed (the field is
    backwards-compatible — empty `per_agent_analyses` means "data not
    available", not "agent didn't react").
    """

    agent_id: str
    persona_id: str
    persona_name: str
    sentiment: Literal["positive", "neutral", "negative"] | None = None
    sentiment_confidence: float | None = None
    top_quote: str | None = None
    # Phase 4.6 #91: arm tag for A/B-mode result-table render. None for
    # single-arm sims and for legacy pre-#89 rows (backwards-compatible).
    # The frontend treats the table as A/B whenever ANY row has a non-None
    # arm, so legacy sims keep their original single-arm layout.
    arm: Literal["treatment", "control"] | None = None


@router.get("/{simulation_id}/agents", response_model=list[AgentSummary])
async def list_simulation_agents(
    simulation_id: str,
    customer_id: str = Depends(current_customer_id),
    orchestrator: SimulationOrchestrator = Depends(get_orchestrator),
    agent_repo: AgentInstanceRepo = Depends(get_agent_repo),
) -> list[AgentSummary]:
    """Persona-grouped table feed (Phase 2.5 #51).

    Order matches the runner's materialization order (largest-remainder
    allocator, largest persona first). InMemory preserves insertion order;
    Postgres sorts by the persisted materialization index for stable reloads.
    """
    sim_row = await orchestrator.get(simulation_id, customer_id)
    if sim_row is None:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} not found")
    rows = await agent_repo.list_for_simulation(simulation_id, customer_id)

    # Build a {agent_id -> AgentAnalysisSummary} map from the persisted
    # result so we can join in one pass without N R2 reads.
    analyses_by_id: dict[str, dict] = {}
    result_json = sim_row.get("result_json") or {}
    for entry in result_json.get("per_agent_analyses") or []:
        if isinstance(entry, dict) and "agent_id" in entry:
            analyses_by_id[entry["agent_id"]] = entry

    out: list[AgentSummary] = []
    for r in rows:
        analysis = analyses_by_id.get(r["id"])
        out.append(
            AgentSummary(
                agent_id=r["id"],
                persona_id=r["persona_id"],
                persona_name=r["persona_name"],
                sentiment=analysis.get("sentiment") if analysis else None,
                sentiment_confidence=(analysis.get("sentiment_confidence") if analysis else None),
                top_quote=analysis.get("top_quote") if analysis else None,
                arm=r.get("arm"),
            )
        )
    return out


@router.get("/{simulation_id}/state", response_model=SimulationRunState)
async def get_simulation_state(
    simulation_id: str,
    customer_id: str = Depends(current_customer_id),
) -> SimulationRunState:
    """Live progress state. Frontend polls this every 5s until phase=complete."""
    store = get_store()
    rs = RunStateStore(store)
    try:
        return rs.read_state(customer_id, simulation_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No state recorded yet for simulation {simulation_id}",
        )
