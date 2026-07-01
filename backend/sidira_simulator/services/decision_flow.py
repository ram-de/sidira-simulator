"""Decision-flow orchestrator — the §5e runtime router (Epic #538, ticket #542).

Phase-1d of the engine rewire — the piece that WIRES the three inert modules
into one authoritative decision:

    LLM-as-translator (#539) → grounded predictor (#540) →
    negative-control watchdog (#541) → **decision-flow router (#542, THIS)**.

The router runs the §5e two-step flow:

**Step 1 (always).** LLM-translate the hypothesis → grounded-compute its sign →
watchdog-validate that sign. When the watchdog stamps the empirical answer
TRUSTWORTHY (CONFIRMS / CONTRADICTS) the grounded sign is the **authoritative
verdict** and we are done — no caution, arrow shown.

**Step 2 (only on grounded-abstain).** When the watchdog CAN'T_VALIDATE (not
covered / not supportable / no NC evidence / guard tripped) the grounded answer
abstains, and we fall back to the LLM **calibrated by the council**:

  - council DISAGREEMENT ⇒ **hard caution** — no arrow, "inconclusive — test it".
  - council AGREEMENT     ⇒ **moderate caution** — surface the LLM direction but
    labelled "unverified — hypothesis, not verdict".

**Precedence:** trustworthy-empirical > LLM > untrustworthy-empirical. The
grounded answer is NEVER gated by the council — only the LLM-fallback confidence
is council-calibrated, and caution is driven by council **disagreement**, never
by unanimity.

**The council seam.** A :class:`Council` is a structural Protocol with one method,
``assess`` — the SINGLE source of both the LLM's fluent take (``llm_direction``,
fed to the watchdog for the CONFIRMS/CONTRADICTS comparison) AND the agreement
signal that calibrates the Step-2 fallback. The default :class:`NullCouncil`
returns ``agreement=True, llm_direction=None`` — degrade-safe: Step-2 falls to a
moderate-caution unverified-hypothesis with no arrow. The real 3-model council is
ticket **#543**, which plugs into this EXACT seam (pass ``council=...`` to
:func:`decide`); nothing else in this module changes.

**Off by default.** Reading the router into a live request path is gated by
``SIDIRA_DECISION_FLOW_ENABLED`` (see :func:`decision_flow_enabled`), default OFF.
With the flag off the orchestrator does zero extra work and the customer-facing
response shape is untouched (the response-shape change is #545).

:func:`decide` NEVER raises: any unexpected failure degrades to a safe
hard-caution "inconclusive — test it" result carrying the trace.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

import structlog

from sidira_simulator.schemas.estimability import EstimabilityManifest
from sidira_simulator.schemas.mechanism import MechanismSpec
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.schemas.verdict import DirectionVerdict, GuardrailMetric

if TYPE_CHECKING:
    from sidira_simulator.adapters.r2 import ArtifactStore
from sidira_simulator.services.grounded_predictor import (
    GroundedPrediction,
    grounded_predict,
    load_estimability_manifest,
)
from sidira_simulator.services.mechanism_translator import translate_hypothesis
from sidira_simulator.services.negative_control_watchdog import watchdog_classify

log = structlog.get_logger()

Direction = Literal["positive", "negative"]
Source = Literal["grounded", "llm_fallback"]
Caution = Literal["none", "moderate", "hard"]


class _Unset:
    """Sentinel type: distinguishes an omitted ``manifest`` from an injected None."""


# The default for :func:`decide`'s ``manifest`` param. An explicit ``manifest=None``
# means "already resolved — the manifest is ABSENT, do NOT load" (so a caller that
# pre-checked R2 and found nothing does not trigger a second blocking read); the
# sentinel means "not injected — load it from R2."
_UNSET: _Unset = _Unset()


@dataclass(frozen=True)
class CouncilAssessment:
    """The council's read on a hypothesis: the LLM take + whether it agrees.

    - ``agreement``: True iff the council's members concur on a direction.
      DISAGREEMENT (False) is what drives hard caution in Step 2 — never
      unanimity. The default :class:`NullCouncil` reports ``True`` (no
      disagreement to flag).
    - ``llm_direction``: the council's single fluent take, fed to the watchdog for
      the CONFIRMS/CONTRADICTS comparison AND surfaced (labelled "unverified") in
      the Step-2 agreement branch. None when the council abstains on a direction
      (the NullCouncil default).
    - ``votes``: the per-member votes (opaque here; the real #543 council fills
      them). Carried for the audit trail.
    - ``rationale``: human-readable justification threaded into the decision log.
    """

    agreement: bool
    llm_direction: Direction | None
    votes: list = field(default_factory=list)
    rationale: str = ""


@runtime_checkable
class Council(Protocol):
    """Structural interface for the model council (real implementation = #543).

    One method, ``assess``, is the SINGLE source of the LLM take AND the agreement
    signal — :func:`decide` never makes a separate LLM call for the direction.
    #543 supplies a 3-model implementation that satisfies this Protocol; pass it
    as ``council=`` to :func:`decide` and nothing else changes.
    """

    def assess(self, hypothesis: str, spec: MechanismSpec) -> CouncilAssessment: ...


class NullCouncil:
    """The degrade-safe default council: agrees, abstains on a direction.

    Returns ``agreement=True, llm_direction=None`` so Step-2 grounded-abstain falls
    to the **moderate-caution unverified-hypothesis** branch with no arrow — never
    a hard caution and never a fabricated direction. This is the seam #543 replaces
    with the real 3-model council.
    """

    def assess(self, hypothesis: str, spec: MechanismSpec) -> CouncilAssessment:
        return CouncilAssessment(
            agreement=True,
            llm_direction=None,
            votes=[],
            rationale="NullCouncil default — no council configured (real council is #543)",
        )


@dataclass(frozen=True)
class DecisionResult:
    """The whole audit trail for one §5e decision.

    - ``source``: "grounded" (Step-1 trustworthy empirical verdict) or
      "llm_fallback" (Step-2 grounded-abstain).
    - ``direction``: "positive" / "negative", or None = no arrow / inconclusive
      (hard caution, or an agreeing council with no direction).
    - ``caution``: "none" (trustworthy grounded), "moderate" (Step-2 agreement),
      "hard" (Step-2 disagreement / defensive error).
    - ``label``: the customer-facing framing string.
    - ``watchdog_verdict``: CONFIRMS / CONTRADICTS / CANT_VALIDATE, or None if the
      watchdog never ran (defensive error path).
    - ``mechanism_spec``: the translator's decomposition (always present).
    - ``grounded``: the grounded prediction, or None when no manifest / defensive.
    - ``reason``: the full trace — translate → grounded → watchdog → council.
    """

    source: Source
    direction: Direction | None
    caution: Caution
    label: str
    watchdog_verdict: str | None
    mechanism_spec: MechanismSpec
    grounded: GroundedPrediction | None
    reason: str


# Customer-facing framing strings — kept as named constants so #545 (the response
# shape) and any UI copy reference one source of truth.
LABEL_VERIFIED = "verified verdict"
LABEL_CONTRADICTS = "verified — data overrides intuition"
LABEL_UNVERIFIED = "unverified — hypothesis, not verdict"
LABEL_INCONCLUSIVE = "inconclusive — test it"


def _fallback_spec(hypothesis: Hypothesis) -> MechanismSpec:
    """A minimal NOT-mappable spec for the defensive error path (never raises)."""
    capability = getattr(hypothesis, "capability_name", "(unknown)")
    return MechanismSpec(
        capability_name=capability,
        treatment_column=None,
        treatment_contrast="(error)",
        outcome_column=None,
        confidence="low",
        unmapped_reason="decision flow errored before a spec was translated",
    )


def decide(
    hypothesis: Hypothesis,
    available_columns: list[str],
    customer_id: str,
    pack_version: str,
    *,
    chat_client=None,
    model_id: str | None = None,
    council: Council | None = None,
    manifest: EstimabilityManifest | None | _Unset = _UNSET,
) -> DecisionResult:
    """Run the §5e two-step decision flow for one hypothesis. NEVER raises.

    Args:
        hypothesis: the PM-supplied product change (prose + capability).
        available_columns: the exact column names in the customer's feature-store
            data (the translator may only ground to these).
        customer_id / pack_version: locate the estimability manifest beside the
            customer's persona pack (``pack_version`` is the persona-pack version).
        chat_client / model_id: forwarded to the translator (a stub short-circuits
            lazy client resolution — how tests inject a fake).
        council: the model council (structural Protocol). Defaults to
            :class:`NullCouncil` (degrade-safe). #543 plugs the real one here.
        manifest: an already-loaded estimability manifest (injectable so tests skip
            R2). Omit it (the default) to load it via ``load_estimability_manifest``.
            Pass ``manifest=None`` to assert it is KNOWN-ABSENT — a caller that
            already checked R2 and found nothing passes None so this does NOT read
            R2 a second time. Either way, an absent manifest → not-covered → Step 2.

    Returns:
        A :class:`DecisionResult` audit trail. Any unexpected failure degrades to a
        safe hard-caution "inconclusive — test it" result.
    """
    council = council or NullCouncil()
    try:
        # 1) LLM-translate the hypothesis → structured mechanism spec.
        spec = translate_hypothesis(
            hypothesis, available_columns, chat_client=chat_client, model_id=model_id
        )

        # 2) The council is the SINGLE source of the LLM take (fed to the watchdog)
        #    AND the agreement signal (calibrates Step-2). No separate LLM call.
        assessment = council.assess(hypothesis.prose, spec)

        # 3) Load the manifest (unless injected). A caller that already resolved it
        #    to absent injects None → we DON'T re-read R2. Absent → not covered.
        if isinstance(manifest, _Unset):
            manifest = load_estimability_manifest(customer_id, pack_version)
        if manifest is None:
            prediction = GroundedPrediction(
                covered=False,
                direction=None,
                supportable=False,
                candidate=None,
                reason=(
                    f"no estimability manifest for customer={customer_id!r} "
                    f"pack_version={pack_version!r} — not covered"
                ),
            )
        else:
            prediction = grounded_predict(spec, manifest)

        # 4) Watchdog-validate the grounded sign against the LLM take.
        watchdog = watchdog_classify(prediction, llm_direction=assessment.llm_direction)

        trace = (
            f"translate[mappable={spec.mappable}] → "
            f"grounded[covered={prediction.covered}, direction={prediction.direction}, "
            f"supportable={prediction.supportable}: {prediction.reason}] → "
            f"watchdog[{watchdog.verdict}, trustworthy={watchdog.trustworthy}: {watchdog.reason}] → "
            f"council[agreement={assessment.agreement}, "
            f"llm_direction={assessment.llm_direction}: {assessment.rationale}]"
        )

        # 5) Decide. trustworthy-empirical > LLM > untrustworthy-empirical.
        if watchdog.trustworthy:
            # Step-1 authoritative grounded verdict — NEVER gated by the council.
            grounded_direction = watchdog.grounded_direction or prediction.direction
            if watchdog.verdict == "CONTRADICTS":
                label = LABEL_CONTRADICTS
            else:
                label = LABEL_VERIFIED
            result = DecisionResult(
                source="grounded",
                direction=grounded_direction,
                caution="none",
                label=label,
                watchdog_verdict=watchdog.verdict,
                mechanism_spec=spec,
                grounded=prediction,
                reason=trace,
            )
        elif assessment.agreement is False:
            # Step-2 grounded-abstain + council DISAGREEMENT → hard caution, no arrow.
            result = DecisionResult(
                source="llm_fallback",
                direction=None,
                caution="hard",
                label=LABEL_INCONCLUSIVE,
                watchdog_verdict=watchdog.verdict,
                mechanism_spec=spec,
                grounded=prediction,
                reason=trace,
            )
        else:
            # Step-2 grounded-abstain + council AGREEMENT → moderate caution,
            # surface the (unverified) LLM direction.
            result = DecisionResult(
                source="llm_fallback",
                direction=assessment.llm_direction,
                caution="moderate",
                label=LABEL_UNVERIFIED,
                watchdog_verdict=watchdog.verdict,
                mechanism_spec=spec,
                grounded=prediction,
                reason=trace,
            )

        log.info(
            "decision_flow.decided",
            customer_id=customer_id,
            pack_version=pack_version,
            capability=spec.capability_name,
            source=result.source,
            direction=result.direction,
            caution=result.caution,
            label=result.label,
            watchdog_verdict=result.watchdog_verdict,
            covered=prediction.covered,
            council_agreement=assessment.agreement,
        )
        return result

    except Exception as exc:  # noqa: BLE001 — a router must never break a request.
        log.warning(
            "decision_flow.failed",
            customer_id=customer_id,
            pack_version=pack_version,
            error=str(exc),
            exc_type=type(exc).__name__,
        )
        return DecisionResult(
            source="llm_fallback",
            direction=None,
            caution="hard",
            label=LABEL_INCONCLUSIVE,
            watchdog_verdict=None,
            mechanism_spec=_fallback_spec(hypothesis),
            grounded=None,
            reason=f"decision flow errored defensively ({type(exc).__name__}: {exc})",
        )


def verdict_from_decision(decision: DecisionResult) -> DirectionVerdict:
    """Map a :class:`DecisionResult` → the customer-facing :class:`DirectionVerdict`.

    Direction-only by construction: ``direction`` / ``caution`` / ``label`` /
    ``source`` / ``watchdog_verdict`` cross straight over; NO magnitude is read
    from the decision's grounded ``candidate`` (it never reaches this contract).

    - ``unverified`` = ``source == "llm_fallback"`` (a hypothesis, not a verdict).
    - ``confidence`` = ``"high"`` iff ``caution == "none"`` (a trustworthy grounded
      verdict), else ``"low"`` — the coarse two-level chip #545 documents.
    - ``guardrails`` = the mechanism spec's ``sibling_metric`` (role ``sibling``)
      + each ``negative_controls`` name (role ``negative_control``) — NAMES only.

    **No-arrow normalization.** A verdict with NO direction is ALWAYS surfaced as
    the canonical abstain (``caution="hard"``, ``LABEL_INCONCLUSIVE``). The Step-2
    council-agreement branch can produce ``direction=None`` with ``caution="moderate"``
    and the "unverified — hypothesis" label (e.g. the NullCouncil default agrees but
    supplies no ``llm_direction``); surfacing a directionless "hypothesis" to the PM
    contradicts the contract (abstain ⇔ no arrow + hard caution — an "unverified
    hypothesis" needs an arrow to be one). So we collapse any no-direction result to
    a clean inconclusive abstain (codex #545). A directioned unverified take
    (council supplied an arrow) is kept as-is — that IS a legitimate hypothesis.

    Pure — never raises. Every field it constructs is a fixed literal or normalized
    to a contract-valid shape, so the ``DirectionVerdict`` validator cannot trip on
    any :class:`DecisionResult` input (``decide`` always returns a ``mechanism_spec``).
    """
    guardrails: list[GuardrailMetric] = []
    spec = decision.mechanism_spec
    if spec is not None:
        if spec.sibling_metric:
            guardrails.append(GuardrailMetric(name=spec.sibling_metric, role="sibling"))
        for name in spec.negative_controls:
            guardrails.append(GuardrailMetric(name=name, role="negative_control"))

    unverified = decision.source == "llm_fallback"

    # No arrow → canonical abstain (hard caution, inconclusive), regardless of the
    # internal caution the router carried. Keeps the customer-facing contract clean.
    if decision.direction is None:
        return DirectionVerdict(
            direction=None,
            caution="hard",
            confidence="low",
            label=LABEL_INCONCLUSIVE,
            source=decision.source,
            watchdog_verdict=decision.watchdog_verdict,
            unverified=unverified,
            guardrails=guardrails,
        )

    return DirectionVerdict(
        direction=decision.direction,
        caution=decision.caution,
        confidence="high" if decision.caution == "none" else "low",
        label=decision.label,
        source=decision.source,
        watchdog_verdict=decision.watchdog_verdict,
        unverified=unverified,
        guardrails=guardrails,
    )


# ── Sidecar persistence for the decision verdict (#545) ──────────────────────
# The #542 hook runs AFTER the run's result_json is already persisted-complete (a
# deliberate safety property — the shadow router must never delay or fail the run).
# So we persist the verdict BESIDE the run as its own R2 artifact rather than
# mutating the already-written result. The key matches the established per-sim
# artifact convention (`customers/{customer_id}/simulations/{sim_id}/…`, cf.
# services.run_state), so the verdict lives in the same prefix as state.json /
# events.jsonl. The GET detail handler reads it back best-effort (#545 §4).


def decision_verdict_key(customer_id: str, sim_id: str) -> str:
    """R2 key for a sim's decision-verdict sidecar (per-sim artifact convention)."""
    return f"customers/{customer_id}/simulations/{sim_id}/decision_verdict.json"


def write_decision_verdict(
    store: ArtifactStore, customer_id: str, sim_id: str, verdict: DirectionVerdict
) -> None:
    """Write the verdict sidecar. Raises on a store failure — the CALLER (the #542
    hook) guards it so a write failure logs + continues, never breaking the run."""
    store.write_text(
        decision_verdict_key(customer_id, sim_id),
        verdict.model_dump_json(indent=2),
    )


def read_decision_verdict(
    store: ArtifactStore, customer_id: str, sim_id: str
) -> DirectionVerdict | None:
    """Best-effort read of the verdict sidecar. Returns None on a miss OR a
    malformed body — NEVER raises — so the GET handler can populate the additive
    field when present and leave it None otherwise (never a 500)."""
    try:
        raw = store.read_text(decision_verdict_key(customer_id, sim_id))
    except FileNotFoundError:
        return None
    except Exception:  # noqa: BLE001 — a best-effort read must never break GET.
        return None
    try:
        return DirectionVerdict.model_validate_json(raw)
    except Exception:  # noqa: BLE001 — a malformed sidecar is treated as absent.
        return None


def decision_flow_enabled() -> bool:
    """True iff ``SIDIRA_DECISION_FLOW_ENABLED`` is a truthy string. Default OFF.

    Plain-env read (the repo convention — no central Settings). Off by default so
    prod behaviour is unchanged until a live consumer (#545 / founder) flips it.
    """
    return os.environ.get("SIDIRA_DECISION_FLOW_ENABLED", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


__all__ = [
    "Direction",
    "Source",
    "Caution",
    "CouncilAssessment",
    "Council",
    "NullCouncil",
    "DecisionResult",
    "decide",
    "verdict_from_decision",
    "decision_verdict_key",
    "write_decision_verdict",
    "read_decision_verdict",
    "decision_flow_enabled",
    "LABEL_VERIFIED",
    "LABEL_CONTRADICTS",
    "LABEL_UNVERIFIED",
    "LABEL_INCONCLUSIVE",
]
