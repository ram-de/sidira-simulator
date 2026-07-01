"""Grounded talk-to-your-users chat — spokesperson for the numbers (Epic #538, #544).

Phase-1e of the engine rewire. The persona chat surface
(:mod:`sidira_simulator.services.agent_chat`) let a PM interrogate the SAME agent
that reacted in the simulation — but that agent answered by **free role-play**:
the LLM continued in-character from a frozen identity, inventing whatever the
prose suggested. That is exactly the disproven "LLM persona predictor" the whole
epic is retiring.

This module RE-GROUNDS the conversation. Once the §5e decision flow (#542) has
computed an authoritative :class:`~sidira_simulator.services.decision_flow.DecisionResult`
(real features → mechanism shift → grounded counterfactual → watchdog verdict),
the persona becomes a **spokesperson for that record, not a role-play predictor**:

- It narrates ONLY from the computed record (mechanism shift + computed direction +
  counterfactual + segment context) — never free invention.
- **The boundary rule (the core).** A question that *explains/explores the EXISTING
  computed change* ("why did it help?", "which feature drove it?", "who moved most?")
  is answered, grounded in the record. A question that proposes a **NEW what-if** — a
  *different* change than the one computed — is NEVER answered with a chat guess: it
  is routed back to the grounded sim for a recompute.
- **Interaction-label discipline.** Segment cross-arm comparison is trustworthy;
  an individual's actual-arm reaction is grounded; a *same-individual cross-arm*
  claim ("what would YOU personally have done in the other arm?") is **calibrated
  fiction — labelled** as unverified. And every persona surface is true *on average
  / per-segment, not literally per-person*.

**Off by default.** The grounded mode is gated by the SAME flag as the decision
flow — :func:`~sidira_simulator.services.decision_flow.decision_flow_enabled`
(``SIDIRA_DECISION_FLOW_ENABLED``) — so the whole engine rewire flips on one
coherent switch. With the flag OFF, :meth:`GroundedAgentChatService.send_message`
delegates to the UNCHANGED :class:`AgentChatService` role-play path (byte-identical).

**Scope boundary (#545).** WHERE the :class:`GroundedRecord` comes from at live
chat time — persisting the ``DecisionResult`` beside the run and threading it into
the chat route — is #545's output-contract territory. This ticket builds the
re-grounding MECHANICS with the record INJECTED by the caller; tests supply a
fixture record. No live route is wired here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import structlog
from pydantic import BaseModel, ConfigDict

from sidira_simulator.adapters.llm import ChatClient, get_chat_client
from sidira_simulator.memory.agent_memory import AgentMemory
from sidira_simulator.schemas.agent import AgentChatTurn, AgentInstanceMetadata, AgentRole
from sidira_simulator.services.agent_chat import _CHAT_GUARD_PREFIX, AgentChatService
from sidira_simulator.services.decision_flow import DecisionResult

log = structlog.get_logger()

Boundary = Literal["explain", "new_whatif"]

# ── Interaction labels (single source of truth) ─────────────────────────────────
# Every persona surface is an average, never a literal person; any same-individual
# cross-arm / estimated claim is calibrated fiction, not a measured fact. Both
# strings are injected verbatim into the grounding supplement so the LLM cannot
# strip the caveat.
LABEL_PER_SEGMENT = "true on average / per-segment, not literally per-person"
LABEL_CALIBRATED_FICTION = "calibrated fiction — unverified"


class GroundedRecord(BaseModel):
    """The computed record the grounded conversation speaks FROM (injected, #544).

    A frozen projection of a :class:`DecisionResult` (+ its matched grounded
    prediction) into just the fields the spokesperson narrates from: the mechanism
    shift, the computed direction and its trust framing, a plain-language
    counterfactual, and whatever point-estimate / segment context the matched
    ``CandidateEffect`` carries. It holds NO free-text persona prose — the persona
    supplies the voice, this supplies the (only) facts.

    Build it with :meth:`from_decision`. Tests construct it directly.
    """

    model_config = ConfigDict(extra="forbid")

    capability_name: str
    # ── mechanism shift (from MechanismSpec) ──
    treatment_column: str | None = None
    treatment_contrast: str = ""
    outcome_column: str | None = None
    mediator: str | None = None
    # ── computed verdict (from DecisionResult) ──
    direction: str | None = None
    label: str = ""
    caution: str = "hard"
    watchdog_verdict: str | None = None
    # True iff the direction is the Step-1 trustworthy EMPIRICAL verdict
    # (source == "grounded"); False on an LLM-fallback / abstain record.
    is_grounded_verdict: bool = False
    # ── narrative + segment context ──
    counterfactual_summary: str = ""
    segment_context: str = ""
    # Whether a precomputed effect matched at all / could support an estimate.
    covered: bool = False
    supportable: bool = False
    # Carried point context (per-segment sizes) — narratable but never per-person.
    n_treat: int | None = None
    n_control: int | None = None

    @classmethod
    def from_decision(cls, decision: DecisionResult) -> GroundedRecord:
        """Project a :class:`DecisionResult` into the record the chat speaks from."""
        spec = decision.mechanism_spec
        grounded = decision.grounded
        candidate = grounded.candidate if grounded is not None else None

        is_grounded = decision.source == "grounded"
        covered = bool(grounded.covered) if grounded is not None else False
        supportable = bool(grounded.supportable) if grounded is not None else False

        return cls(
            capability_name=spec.capability_name,
            treatment_column=spec.treatment_column,
            treatment_contrast=spec.treatment_contrast,
            outcome_column=spec.outcome_column,
            mediator=spec.mediator,
            direction=decision.direction,
            label=decision.label,
            caution=decision.caution,
            watchdog_verdict=decision.watchdog_verdict,
            is_grounded_verdict=is_grounded,
            counterfactual_summary=_counterfactual_summary(spec, decision.direction, is_grounded),
            segment_context=_segment_context(candidate),
            covered=covered,
            supportable=supportable,
            n_treat=getattr(candidate, "n_treat", None),
            n_control=getattr(candidate, "n_control", None),
        )


def _counterfactual_summary(spec, direction: str | None, is_grounded: bool) -> str:
    """One plain-language line: the change, the mechanism, the computed direction."""
    lever = spec.treatment_contrast or spec.treatment_column or "the change"
    outcome = spec.outcome_column or "the outcome"
    via = f" (working through {spec.mediator})" if spec.mediator else ""
    if direction is None:
        return (
            f"The grounded sim could not settle a direction for {lever} on {outcome}{via}; "
            "the record abstains."
        )
    frame = "computed empirically" if is_grounded else "an unverified hypothesis"
    return f"{lever} moves {outcome}{via} in a {direction} direction ({frame})."


def _segment_context(candidate) -> str:
    """Narratable per-segment context from the matched candidate (never per-person)."""
    if candidate is None:
        return "No precomputed per-segment effect matched this change."
    parts: list[str] = []
    if getattr(candidate, "n_treat", None) is not None:
        parts.append(f"treated n={candidate.n_treat}")
    if getattr(candidate, "n_control", None) is not None:
        parts.append(f"control n={candidate.n_control}")
    covariates = getattr(candidate, "covariates", None) or []
    if covariates:
        parts.append("adjusted for " + ", ".join(covariates))
    if not getattr(candidate, "supportable", True):
        reasons = getattr(candidate, "support_reasons", None) or []
        note = ": " + "; ".join(reasons) if reasons else ""
        parts.append(f"NOT supportable{note}")
    return "; ".join(parts) if parts else "matched, no extra segment context"


# ── boundary classifier (LLM judge, mirrors mechanism_translator) ───────────────


class _BoundaryOutput(BaseModel):
    """Strict-JSON verdict for ONE boundary-classification call.

    ``extra="ignore"`` (forgiving parse, mirrors the translator): a stray key from
    the LLM is tolerated. The only load-bearing field is ``boundary``.
    """

    model_config = ConfigDict(extra="ignore")

    boundary: Literal["explain", "new_whatif"] = "new_whatif"
    rationale: str = ""


_CLASSIFIER_SYSTEM = """You are a routing classifier for a product-analytics chat. A product
manager just received a COMPUTED result about ONE specific product change, and is now
asking a follow-up. Decide which of two buckets the follow-up falls in:

- "explain": the PM is asking WHY / WHO / WHICH-FEATURE / HOW-MUCH about the SAME change
  that was already computed — explaining, exploring, or drilling into the EXISTING result.
- "new_whatif": the PM is proposing a DIFFERENT change, a different lever, a different
  magnitude, or a different outcome than the one that was computed — i.e. a new
  counterfactual that would require re-running the grounded simulation to answer.

When in doubt, or if the follow-up mixes an explanation with a new proposed change,
choose "new_whatif" — it is never safe to answer a new change from the existing result.

Return STRICT JSON: {"boundary": "explain" | "new_whatif", "rationale": "<short reason>"}.
No prose outside the JSON."""


def _classifier_user_turn(pm_message: str, record: GroundedRecord) -> str:
    """The classifier's user turn: the computed change + the PM's follow-up."""
    return (
        "The change that was ALREADY computed:\n"
        f"- capability: {record.capability_name}\n"
        f"- lever / contrast: {record.treatment_contrast or record.treatment_column or '(unknown)'}\n"
        f"- outcome measured: {record.outcome_column or '(unknown)'}\n"
        f"- computed direction: {record.direction or '(abstained)'}\n\n"
        f"The PM's follow-up:\n{pm_message}\n\n"
        'Classify the follow-up. Return {"boundary": "...", "rationale": "..."}.'
    )


def classify_pm_message(
    pm_message: str,
    record: GroundedRecord,
    *,
    chat_client: ChatClient | None = None,
    model_id: str | None = None,
) -> Boundary:
    """Route a PM follow-up: ``"explain"`` the existing result vs a ``"new_whatif"``.

    An LLM judge mirroring :func:`~sidira_simulator.services.mechanism_translator.translate_hypothesis`:
    resolve the client lazily (an explicit ``chat_client`` short-circuits, so the
    suite injects a stub), one ``chat_json`` call, strict schema.

    **NEVER raises.** On ANY failure — client unavailable, transport error,
    unparseable JSON — it degrades to the SAFE branch ``"new_whatif"``. That is
    the no-guess posture: a mis- or un-classified follow-up is treated as a new
    change and routed to a recompute, so an ambiguous question can never be
    answered with a fabricated numeric / directional guess off the existing record.
    """
    try:
        client = chat_client if chat_client is not None else get_chat_client(model_id)
    except Exception as exc:  # noqa: BLE001 — degrade to the safe branch; never raise
        log.warning(
            "grounded_agent_chat.classifier_client_unavailable",
            error=str(exc),
            exc_type=type(exc).__name__,
        )
        return "new_whatif"

    try:
        raw = client.chat_json(
            [
                {"role": "system", "content": _CLASSIFIER_SYSTEM},
                {"role": "user", "content": _classifier_user_turn(pm_message, record)},
            ],
            _BoundaryOutput,
        )
    except Exception as exc:  # noqa: BLE001 — degrade to the safe branch; never raise
        log.warning(
            "grounded_agent_chat.classifier_failed",
            error=str(exc),
            exc_type=type(exc).__name__,
        )
        return "new_whatif"

    return raw.boundary if raw.boundary in ("explain", "new_whatif") else "new_whatif"


# ── grounding supplement ────────────────────────────────────────────────────────

_GROUNDING_HEADER = (
    "GROUNDING CONTRACT — you are now a SPOKESPERSON FOR A COMPUTED RESULT, not a "
    "free predictor. Answer the PM's question using ONLY the computed record below. "
    "Do NOT invent numbers, directions, or effects that are not in the record. If the "
    "record abstains or does not contain what is being asked, say so plainly — never "
    "fill the gap with a guess."
)


def _grounding_supplement(record: GroundedRecord) -> str:
    """The system-supplement that pins the persona to the record + carries the labels.

    (a) pins the agent to narrate ONLY from the record; (b) injects the record
    (mechanism shift + computed direction + counterfactual + segment context);
    (c) carries the two interaction labels; (d) keeps the anti-drift guard spirit.
    """
    return "\n".join(
        [
            _GROUNDING_HEADER,
            "",
            "THE COMPUTED RECORD:",
            f"- capability: {record.capability_name}",
            f"- mechanism shift: {record.treatment_contrast or record.treatment_column or '(unknown lever)'}"
            + (f" → through {record.mediator}" if record.mediator else "")
            + f" → {record.outcome_column or '(unknown outcome)'}",
            f"- computed direction: {record.direction or 'abstained (no direction)'}",
            f"- trust framing: {record.label} (caution={record.caution}, "
            f"watchdog={record.watchdog_verdict or 'n/a'}, "
            f"{'trustworthy empirical verdict' if record.is_grounded_verdict else 'unverified fallback'})",
            f"- counterfactual: {record.counterfactual_summary}",
            f"- segment context: {record.segment_context}",
            "",
            "INTERACTION LABELS you MUST honour when you speak:",
            f"- You speak for a segment average. Every claim is {LABEL_PER_SEGMENT}. Never "
            "present yourself as a single literal person whose exact behaviour is known.",
            "- A segment cross-arm comparison is trustworthy; your own actual-arm reaction "
            "is grounded; but any claim about what YOU PERSONALLY would have done in the "
            f"OTHER arm is {LABEL_CALIBRATED_FICTION} — label it as such and never present "
            "a same-individual cross-arm or estimated figure as a measured fact.",
        ]
    )


# ── result wrapper ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class GroundedChatResult:
    """The outcome of one grounded chat turn.

    A small wrapper (chosen over adding fields to the persisted ``AgentChatTurn``
    schema, which would pollute the append-only ``conversation.jsonl`` and every
    other reader of that model):

    - ``turn``: the persisted agent turn (the reply, or the recompute nudge).
    - ``recompute_needed``: True iff the PM proposed a NEW change that must be
      routed back to the grounded sim — the reply is a nudge, NOT a prediction.
    - ``boundary``: the classifier's route (``"explain"`` / ``"new_whatif"``), or
      ``"disabled"`` when the flag is off and the base role-play path ran.
    """

    turn: AgentChatTurn
    recompute_needed: bool
    boundary: Literal["explain", "new_whatif", "disabled"]


# The in-character nudge returned for a NEW what-if — NEVER a prediction.
_RECOMPUTE_MESSAGE = (
    "That's a different change from the one we actually measured, so I'd only be "
    "guessing if I answered it from here — and I won't guess. To get a real answer "
    "we'd need to re-run the grounded simulation on that new change. I can only "
    "speak to the result we already computed."
)


class GroundedAgentChatService:
    """Grounded talk-to-users chat — wraps :class:`AgentChatService` (#544).

    Composes the base role-play service (reusing its store, chat client and
    :class:`AgentMemory`) so the flag-OFF path is literally the unchanged service.
    When the flag is ON, :meth:`send_message` re-grounds the turn on the injected
    :class:`GroundedRecord` via the boundary rule.
    """

    def __init__(
        self,
        store=None,
        chat_client: ChatClient | None = None,
        model_id: str | None = None,
    ) -> None:
        # The base service owns store + chat + memory; reuse them so the flag-off
        # delegation is byte-identical and the grounded path shares one client.
        self._base = AgentChatService(store=store, chat_client=chat_client, model_id=model_id)
        self._store = self._base._store
        self._chat = self._base._chat
        self._memory: AgentMemory = self._base._memory
        self._model_id = model_id

    def send_message(
        self,
        metadata: AgentInstanceMetadata,
        pm_message: str,
        record: GroundedRecord,
    ) -> GroundedChatResult:
        """Answer a PM follow-up as a spokesperson for ``record`` (or nudge a recompute).

        Flag OFF (``SIDIRA_DECISION_FLOW_ENABLED`` unset) → delegate to the
        UNCHANGED :class:`AgentChatService.send_message` role-play path; the record
        is ignored and ``boundary="disabled"``.

        Flag ON → classify the follow-up:
          - ``"explain"``: build the replay stack + the grounding supplement and
            call the LLM, narrating ONLY from the record.
          - ``"new_whatif"``: do NOT call the role-play LLM for a prediction; persist
            a short in-character recompute nudge and signal ``recompute_needed=True``.

        Persistence mirrors the base service's codex-#52 ordering: the LLM call (when
        any) happens FIRST, and only on success are the PM turn and agent turn
        appended (PM first, then agent) — so an LLM failure leaves nothing
        half-written. NEVER raises beyond what the underlying store / LLM already do.
        """
        # Import here to avoid a hard module-load coupling; the flag is the single
        # coherent switch shared with the decision flow (#542).
        from sidira_simulator.services.decision_flow import decision_flow_enabled

        if not decision_flow_enabled():
            # Unchanged role-play path — the record is not consulted.
            turn = self._base.send_message(metadata, pm_message)
            return GroundedChatResult(turn=turn, recompute_needed=False, boundary="disabled")

        boundary = classify_pm_message(
            pm_message, record, chat_client=self._chat, model_id=self._model_id
        )

        if boundary == "new_whatif":
            # NEVER call the role-play LLM for a prediction on a new change.
            return self._persist_pair(metadata, pm_message, _RECOMPUTE_MESSAGE, True, "new_whatif")

        # boundary == "explain": narrate from the record.
        agent = self._memory.load(metadata)
        messages = AgentMemory.build_replay_messages(agent)
        messages.append({"role": "system", "content": _CHAT_GUARD_PREFIX})
        messages.append({"role": "system", "content": _grounding_supplement(record)})
        messages.append({"role": "user", "content": pm_message})

        # LLM FIRST — a failure here persists nothing (codex #52 ordering).
        agent_text = self._chat.chat(messages=messages)
        return self._persist_pair(metadata, pm_message, agent_text, False, "explain")

    def _persist_pair(
        self,
        metadata: AgentInstanceMetadata,
        pm_message: str,
        agent_text: str,
        recompute_needed: bool,
        boundary: Literal["explain", "new_whatif"],
    ) -> GroundedChatResult:
        """Append the PM turn then the agent turn (base-service ordering) + wrap."""
        pm_turn = AgentMemory.new_turn(AgentRole.PM, pm_message)
        self._memory.append_turn(metadata, pm_turn)

        agent_turn = AgentMemory.new_turn(AgentRole.AGENT, agent_text)
        self._memory.append_turn(metadata, agent_turn)

        return GroundedChatResult(
            turn=agent_turn, recompute_needed=recompute_needed, boundary=boundary
        )


__all__ = [
    "GroundedRecord",
    "GroundedChatResult",
    "GroundedAgentChatService",
    "classify_pm_message",
    "Boundary",
    "LABEL_PER_SEGMENT",
    "LABEL_CALIBRATED_FICTION",
]
