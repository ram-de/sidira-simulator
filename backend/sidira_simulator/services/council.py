"""3-model heterogeneous-bias council — the abstain-siren (Epic #538, ticket #543).

Phase-1e of the engine rewire. This is the real :class:`~sidira_simulator.services
.decision_flow.Council` implementation the #542 router leaves a seam for. It is
consulted ONLY in the Step-2 grounded-abstain branch (the router enforces this —
the council NEVER gates a grounded verdict). It supplies exactly two things the
router calibrates on: an ``agreement`` signal and a single ``llm_direction``.

**Why a bias-DIVERSE panel.** The engine-strength campaign measured that models
which share a prior agree-*and-are-wrong*: a degenerate all-same-bias panel
produced 0/12 useful disagreement flags on the counter-intuitive cases — its
unanimity was empty (no independent evidence, just a shared blind spot). Genuine
disagreement is only informative when the panelists carry *different* measured
biases. So the panel is assembled from models with DISTINCT measured priors
(``BIAS_PROFILE``) — the campaign's read: **llama optimist · Opus pessimist ·
gpt-5.5 balanced** — and :func:`assert_bias_diversity` REFUSES to build a panel
that spans fewer than two distinct profiles.

**Aggregation (the abstain-siren errs toward caution).** Collect the directional
votes (positive/negative) from the usable models; drop abstains, unavailable
providers, errors, and timeouts. Then:

  - ``< 2`` usable directional votes → ``agreement=False`` (can't certify a panel
    consensus from a single voice → conservative hard caution).
  - all usable directional votes share ONE direction → ``agreement=True`` with
    that ``llm_direction`` (unverified hypothesis → moderate caution).
  - votes split → ``agreement=False`` (any-of-N disagree ⇒ hard caution — this is
    the "flip cell" the campaign flagged).

Every council output is *unverified* — the router labels it; the council only
supplies agreement + direction.

**Failure posture** mirrors the translator (#539): the per-model ``chat_json``
calls are blocking, so they fan out on a ``ThreadPoolExecutor`` bounded by a
per-model timeout; a model that is unavailable (no provider key), errors, or
times out is DROPPED (logged), never fatal. :meth:`HeterogeneousCouncil.assess`
NEVER raises — any unexpected failure degrades to a conservative
``agreement=False`` assessment.

Off by default: nothing imports this into a live request path except the flag-
gated orchestrator hook (#542), which builds the real council via
:func:`build_default_council` only when ``SIDIRA_DECISION_FLOW_ENABLED`` is on.
"""

from __future__ import annotations

import concurrent.futures as _futures
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field

from sidira_simulator.adapters.llm import ChatClient, get_chat_client, model_is_available
from sidira_simulator.schemas.mechanism import MechanismSpec
from sidira_simulator.services.decision_flow import CouncilAssessment, Direction

log = structlog.get_logger()


# ── the bias-diverse panel ──────────────────────────────────────────────────

# Each panelist's MEASURED prior (from the engine-strength campaign). Documented
# here because it is load-bearing: :func:`assert_bias_diversity` reads it to
# refuse a degenerate panel whose members share a prior (they agree-and-are-wrong,
# so their unanimity carries no independent evidence — the campaign's 0/12 result).
BIAS_PROFILE: dict[str, str] = {
    "llama-3.1-8b-instant": "optimist",  # skews toward predicting lift / positive
    "claude-opus-4-7": "pessimist",  # skews toward predicting decline / negative
    "gpt-5.5": "balanced",  # no measured directional skew
}

# The default 3-model panel: one optimist, one pessimist, one balanced — spans
# three distinct profiles, so a single dropped member still leaves a diverse pair.
DEFAULT_PANEL: tuple[str, ...] = (
    "llama-3.1-8b-instant",
    "claude-opus-4-7",
    "gpt-5.5",
)

_UNKNOWN_PROFILE = "unknown"

# Per-model latency/cost bounds. Direction-only, so a short answer suffices.
_DEFAULT_PER_MODEL_TIMEOUT_S = 20.0
_MAX_TOKENS = 256
_TEMPERATURE = 0.0
_SEED = 7


def _profile_of(model_id: str) -> str:
    """The measured bias profile of a model, or ``"unknown"`` if undocumented."""
    return BIAS_PROFILE.get(model_id, _UNKNOWN_PROFILE)


class CouncilDiversityError(ValueError):
    """Raised when a panel does not span ≥2 distinct measured bias profiles."""


def assert_bias_diversity(panel: Sequence[str]) -> None:
    """Assert the panel spans ≥2 distinct MEASURED bias profiles. Raise otherwise.

    A council is only informative when its members carry *different* priors:
    shared-prior models agree-and-are-wrong (the campaign measured 0/12 useful
    flags from a degenerate all-same-bias panel — the unanimity was an empty
    shared blind spot, not evidence). So a panel that is all-optimist (or spans
    only one documented profile), or that has fewer than two members, is
    degenerate and rejected here.

    ``"unknown"`` profiles (undocumented models) do NOT count toward diversity —
    an undocumented model's bias is unmeasured, so it cannot be relied on to
    diversify the panel.

    Raises:
        CouncilDiversityError: on a degenerate panel, with the reason.
    """
    if len(panel) < 2:
        raise CouncilDiversityError(
            f"panel has {len(panel)} member(s); need ≥2 for a council that can disagree"
        )
    profiles = {_profile_of(m) for m in panel}
    known = profiles - {_UNKNOWN_PROFILE}
    if len(known) < 2:
        raise CouncilDiversityError(
            f"panel spans only {sorted(profiles)} — need ≥2 distinct measured bias "
            "profiles; shared-prior models agree-and-are-wrong (campaign: 0/12)"
        )


# ── per-member audit record ─────────────────────────────────────────────────

MemberStatus = Literal["voted", "abstained", "unavailable", "error"]


@dataclass(frozen=True)
class CouncilMemberResult:
    """One panelist's outcome — carried in ``CouncilAssessment.votes`` for audit.

    ``status``: ``voted`` (a usable positive/negative), ``abstained`` (the model
    declined a direction), ``unavailable`` (provider key absent / model down —
    never queried), or ``error`` (raised or timed out). Only ``voted`` members
    with a positive/negative ``direction`` feed the aggregation.
    """

    model_id: str
    bias_profile: str
    status: MemberStatus
    direction: Direction | None = None
    rationale: str = ""
    error: str | None = None


# ── the strict-JSON vote contract ───────────────────────────────────────────


class CouncilVote(BaseModel):
    """Strict-JSON contract for ONE model's directional vote (via ``chat_json``).

    Forgiving (``extra="ignore"``): a stray key from a chatty model is tolerated.
    ``direction`` is a closed Literal — ``abstain`` is a first-class option so a
    genuinely-unsure model does not pollute the panel with a coin-flip guess.
    """

    model_config = ConfigDict(extra="ignore")

    direction: Literal["positive", "negative", "abstain"]
    rationale: str = Field(default="", description="one short sentence naming the dominant mechanism")


_SYSTEM = """You are one member of a bias-diverse forecasting council. Your ONLY job is
to predict the DIRECTION of a proposed product change's effect on its target
outcome. You do NOT estimate magnitudes and you NEVER return a number.

Answer with STRICT JSON, exactly these keys:
- direction: "positive" if the change most plausibly INCREASES the outcome,
  "negative" if it most plausibly DECREASES it, or "abstain" if you are
  genuinely unsure of the sign.
- rationale: ONE short sentence naming the dominant mechanism behind your call.

Abstain honestly — a false-confident guess pollutes the panel and is worse than
silence. Return ONLY the JSON object, no prose around it."""


def _user_turn(hypothesis: str, spec: MechanismSpec) -> str:
    """The panelist's user turn: the hypothesis surface + the mechanism spec."""
    return "\n".join(
        [
            f"Capability: {spec.capability_name}",
            f"Hypothesis: {hypothesis}",
            f"Treatment contrast: {spec.treatment_contrast}",
            f"Outcome measured: {spec.outcome_column or '(the hypothesis target metric)'}",
            f"Theorized channel (mediator): {spec.mediator or '(unspecified)'}",
            "",
            "Predict the DIRECTION of the effect on the outcome. Return the JSON.",
        ]
    )


class HeterogeneousCouncil:
    """A bias-diverse panel implementing the :class:`Council` Protocol (#543).

    Consulted ONLY in the router's grounded-abstain branch. Validates bias
    diversity at construction (:func:`assert_bias_diversity`), queries the panel
    CONCURRENTLY on ``assess``, drops any unavailable/errored/timed-out member,
    and aggregates the usable directional votes into a
    :class:`~sidira_simulator.services.decision_flow.CouncilAssessment`. NEVER
    raises out of :meth:`assess`.
    """

    def __init__(
        self,
        panel: Sequence[str] = DEFAULT_PANEL,
        *,
        client_factory: Callable[[str], ChatClient] | None = None,
        per_model_timeout: float = _DEFAULT_PER_MODEL_TIMEOUT_S,
    ) -> None:
        """Build a council over ``panel``, validating bias diversity up front.

        Args:
            panel: the model IDs to consult. Must span ≥2 distinct measured bias
                profiles (:func:`assert_bias_diversity`) or construction RAISES.
            client_factory: per-model ``ChatClient`` factory — injected by tests to
                avoid real LLM calls. Defaults to ``get_chat_client`` (lazy, per
                model, resolved INSIDE the assess guard so a missing key degrades).
            per_model_timeout: wall-clock seconds bounding each panelist's blocking
                call; a slower member is dropped (the panel fans out concurrently).

        Raises:
            CouncilDiversityError: if ``panel`` is degenerate (all-same-profile).
        """
        assert_bias_diversity(panel)
        self._panel: tuple[str, ...] = tuple(panel)
        self._per_model_timeout = per_model_timeout
        # The DEFAULT factory bounds the underlying SDK HTTP call with a real
        # request timeout so a hung provider call RAISES (and its worker thread
        # terminates) rather than stranding the thread past the pool wait — the
        # ThreadPoolExecutor wait only stops us *waiting*, it can't kill a blocked
        # call. An injected factory (tests) is used verbatim.
        if client_factory is not None:
            self._client_factory = client_factory
        else:
            self._client_factory = lambda model_id: get_chat_client(
                model_id, request_timeout=per_model_timeout
            )

    def _query_model(self, model_id: str, hypothesis: str, spec: MechanismSpec) -> CouncilMemberResult:
        """Query ONE panelist for a directional vote. Never raises (returns a record).

        Resolves the client lazily INSIDE the guard (mirrors the translator): a
        missing key / transport error / unparseable JSON degrades to an ``error``
        record rather than raising into the thread pool.
        """
        profile = _profile_of(model_id)
        try:
            client = self._client_factory(model_id)
            vote = client.chat_json(
                [
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": _user_turn(hypothesis, spec)},
                ],
                CouncilVote,
                max_tokens=_MAX_TOKENS,
                temperature=_TEMPERATURE,
                seed=_SEED,
            )
        except Exception as exc:  # noqa: BLE001 — a dropped member is not fatal
            log.warning(
                "council.member_failed",
                model_id=model_id,
                bias_profile=profile,
                error=str(exc),
                exc_type=type(exc).__name__,
            )
            return CouncilMemberResult(
                model_id=model_id,
                bias_profile=profile,
                status="error",
                error=f"{type(exc).__name__}: {exc}",
            )

        if vote.direction == "abstain":
            return CouncilMemberResult(
                model_id=model_id,
                bias_profile=profile,
                status="abstained",
                rationale=vote.rationale,
            )
        return CouncilMemberResult(
            model_id=model_id,
            bias_profile=profile,
            status="voted",
            direction=vote.direction,
            rationale=vote.rationale,
        )

    def assess(self, hypothesis: str, spec: MechanismSpec) -> CouncilAssessment:
        """Poll the panel and aggregate into a ``CouncilAssessment``. NEVER raises.

        Skips members whose provider is unavailable, fans the rest out on a thread
        pool bounded by ``per_model_timeout``, drops abstains/errors/timeouts, then
        applies the abstain-siren aggregation (see the module docstring).
        """
        try:
            return self._assess(hypothesis, spec)
        except Exception as exc:  # noqa: BLE001 — the council must never break the router
            log.warning(
                "council.assess_failed",
                error=str(exc),
                exc_type=type(exc).__name__,
            )
            return CouncilAssessment(
                agreement=False,
                llm_direction=None,
                votes=[],
                rationale=f"council errored defensively ({type(exc).__name__}: {exc})",
            )

    def _assess(self, hypothesis: str, spec: MechanismSpec) -> CouncilAssessment:
        results: list[CouncilMemberResult] = []
        to_query: list[str] = []

        # Graceful degradation: a model whose provider key is absent (or which is
        # otherwise unavailable) is never queried — recorded, not fatal.
        for model_id in self._panel:
            try:
                available = model_is_available(model_id)
            except Exception:  # noqa: BLE001 — treat an availability error as unavailable
                available = False
            if available:
                to_query.append(model_id)
            else:
                results.append(
                    CouncilMemberResult(
                        model_id=model_id,
                        bias_profile=_profile_of(model_id),
                        status="unavailable",
                        error="provider not configured / model unavailable",
                    )
                )

        if to_query:
            executor = _futures.ThreadPoolExecutor(max_workers=len(to_query))
            try:
                future_to_model = {
                    executor.submit(self._query_model, m, hypothesis, spec): m for m in to_query
                }
                # The members run concurrently, so one wall-clock deadline bounds
                # each of them by ~per_model_timeout. Whatever hasn't returned by
                # then is dropped as a timeout.
                done, not_done = _futures.wait(
                    future_to_model, timeout=self._per_model_timeout
                )
                for fut in done:
                    model_id = future_to_model[fut]
                    try:
                        results.append(fut.result())
                    except Exception as exc:  # noqa: BLE001 — belt-and-braces; _query_model guards
                        results.append(
                            CouncilMemberResult(
                                model_id=model_id,
                                bias_profile=_profile_of(model_id),
                                status="error",
                                error=f"{type(exc).__name__}: {exc}",
                            )
                        )
                for fut in not_done:
                    model_id = future_to_model[fut]
                    log.warning("council.member_timeout", model_id=model_id)
                    results.append(
                        CouncilMemberResult(
                            model_id=model_id,
                            bias_profile=_profile_of(model_id),
                            status="error",
                            error="timeout",
                        )
                    )
            finally:
                # Don't block the caller (the router hook is itself timeout-bounded):
                # cancel the not-yet-started futures and let any running ones finish
                # in the pool without us waiting on them.
                executor.shutdown(wait=False, cancel_futures=True)

        assessment = self._aggregate(results)
        log.info(
            "council.assessed",
            panel=list(self._panel),
            agreement=assessment.agreement,
            llm_direction=assessment.llm_direction,
            usable=sum(1 for r in results if r.status == "voted"),
            abstained=sum(1 for r in results if r.status == "abstained"),
            dropped=sum(1 for r in results if r.status in ("unavailable", "error")),
        )
        return assessment

    @staticmethod
    def _aggregate(results: list[CouncilMemberResult]) -> CouncilAssessment:
        """Apply the abstain-siren policy to the per-member records."""
        directional = [
            r for r in results if r.status == "voted" and r.direction in ("positive", "negative")
        ]
        positives = [r for r in directional if r.direction == "positive"]
        negatives = [r for r in directional if r.direction == "negative"]
        n_usable = len(directional)

        if n_usable < 2:
            rationale = (
                f"only {n_usable} usable directional vote(s) — cannot certify a panel "
                "consensus; conservative hard caution (abstain-siren)"
            )
            return CouncilAssessment(
                agreement=False, llm_direction=None, votes=results, rationale=rationale
            )

        if positives and negatives:
            rationale = (
                f"panel SPLIT ({len(positives)} positive / {len(negatives)} negative) — "
                "any-of-N disagreement ⇒ hard caution (flip cell)"
            )
            return CouncilAssessment(
                agreement=False, llm_direction=None, votes=results, rationale=rationale
            )

        direction: Direction = "positive" if positives else "negative"
        rationale = (
            f"panel unanimous ({n_usable} usable votes) on {direction} — unverified "
            "hypothesis, moderate caution"
        )
        return CouncilAssessment(
            agreement=True, llm_direction=direction, votes=results, rationale=rationale
        )


def build_default_council() -> HeterogeneousCouncil:
    """Construct the default 3-model heterogeneous council (:data:`DEFAULT_PANEL`).

    The factory the flag-gated orchestrator hook (#542) calls when
    ``SIDIRA_DECISION_FLOW_ENABLED`` is on. Construction validates bias diversity;
    the default panel always passes, but the caller still guards this so any
    failure degrades to :class:`NullCouncil` rather than breaking the run.
    """
    return HeterogeneousCouncil(DEFAULT_PANEL)


__all__ = [
    "BIAS_PROFILE",
    "DEFAULT_PANEL",
    "CouncilDiversityError",
    "assert_bias_diversity",
    "CouncilVote",
    "CouncilMemberResult",
    "HeterogeneousCouncil",
    "build_default_council",
]
