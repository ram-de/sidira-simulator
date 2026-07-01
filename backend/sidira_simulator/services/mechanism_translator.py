"""LLM-as-translator: hypothesis → structured mechanism spec (Epic #538, #539).

Phase-1a of the engine rewire (Epic #538). The LLM here does **not** predict — it
*translates* a `Hypothesis` (free prose + a named capability) plus the set of
column names available in the customer's feature-store data into a structured
:class:`MechanismSpec`. That spec is what the (later) grounded g-formula
estimator (#540) and the negative-control watchdog (#541) compute on; the router
(#542) wires it into a live request. THIS ticket builds only the translator + its
schema + tests, and ships INERT — nothing in a request path imports it.

The client-resolution + structured-parse shape mirrors
``services/input_lint.py``'s LLM judge: resolve a vendor-agnostic
:class:`~sidira_simulator.adapters.llm.ChatClient` lazily (an explicit
`chat_client` short-circuits, so the suite injects a stub and never constructs a
real client), build a system + user prompt, call ``chat_json`` for a strict-JSON
structured verdict, and validate it into a pydantic model.

Failure posture mirrors ``refinement.suggest`` / ``assess_input_lint``: a
translator that can't ground the treatment or outcome to a real column, that
references a column not in the data, or whose LLM call / JSON parse fails NEVER
raises into the caller — it returns a `mappable=False` spec carrying an
`unmapped_reason`. The router reads `mappable=False` and falls back to LLM
simulation. Direction-only: the spec names the mechanism, never a predicted
number.
"""

from __future__ import annotations

import structlog
from pydantic import BaseModel, ConfigDict, Field

from sidira_simulator.adapters.llm import ChatClient, get_chat_client
from sidira_simulator.schemas.mechanism import (
    AVAILABLE_COLUMNS_CONTEXT_KEY,
    MechanismSpec,
)
from sidira_simulator.schemas.simulation import Hypothesis

log = structlog.get_logger()


class _TranslatorOutput(BaseModel):
    """Strict-JSON contract for ONE translator call — the LLM's raw decomposition.

    Deliberately forgiving (``extra="ignore"``) where :class:`MechanismSpec` is
    strict: an LLM that emits a stray key here is tolerated at parse time, then
    the value is re-validated into the strict, referential-integrity-checked
    `MechanismSpec`. The LLM does NOT report `mappable` — that flag is DERIVED by
    the spec validator, never trusted from the model. `null` is the LLM's signal
    that it could not ground the treatment or outcome to a real column.
    """

    model_config = ConfigDict(extra="ignore")

    treatment_column: str | None = None
    treatment_contrast: str = ""
    outcome_column: str | None = None
    mediator: str | None = None
    covariates: list[str] = Field(default_factory=list)
    negative_controls: list[str] = Field(default_factory=list)
    sibling_metric: str | None = None
    estimand: str = "ATE on outcome"
    confidence: str = "low"
    notes: str | None = None


_SYSTEM = """You are a causal-inference translator. You do NOT predict outcomes and you
NEVER return a number. Given a product-change hypothesis and the exact list of
columns available in the customer's dataset, decompose the hypothesis into a
structured mechanism the downstream estimator can compute:

- treatment_column: the column that encodes the lever (the thing being changed /
  the A-vs-B assignment). Choose EXACTLY ONE column name from the available list.
  If NOTHING in the list can serve as the treatment, return null.
- treatment_contrast: a short human-readable description of the baseline -> treatment
  contrast (e.g. "gate at level 30 vs gate at level 40"). Prose, never a number.
- outcome_column: the column that measures the outcome the hypothesis is about.
  EXACTLY ONE name from the available list, or null if none fits.
- mediator: the column the change is theorized to work THROUGH (a real column), or null.
- covariates: pre-treatment confounders to adjust for. A subset of the available
  columns (may be empty). Do NOT include the treatment or the outcome.
- negative_controls: columns the treatment should NOT plausibly cause but which
  share the same confounding (e.g. pre-treatment behaviours). A subset of the
  available columns (may be empty).
- sibling_metric: an optional co-moving / cannibalization outcome column to watch,
  or null.
- estimand: the estimand in words, e.g. "ATE on <outcome>".
- confidence: "high" or "low" — your confidence that the grounding is faithful.
- notes: brief assumptions or caveats, or null.

HARD RULES:
- Every column name you emit MUST be copied VERBATIM from the provided available-columns
  list. Never invent, pluralize, or reword a column name.
- If you cannot ground BOTH a treatment and an outcome to real available columns,
  return null for the one(s) you cannot ground.
- Return STRICT JSON with exactly these keys. No prose outside the JSON. No numbers
  in any field except as part of a contrast description string."""


def _user_turn(hypothesis: Hypothesis, available_columns: list[str]) -> str:
    """The translator's user turn: the hypothesis surface + the column allow-list."""
    parts = [
        f"Capability: {hypothesis.capability_name}",
        f"Hypothesis prose:\n{hypothesis.prose}",
    ]
    if hypothesis.proposed_prd:
        parts.append(f"Proposed PRD:\n{hypothesis.proposed_prd}")
    if hypothesis.metric_name:
        parts.append(f"Declared decision metric: {hypothesis.metric_name}")
    cols = ", ".join(available_columns) if available_columns else "(none)"
    parts.append(f"Available columns in the customer's dataset:\n{cols}")
    parts.append(
        "Decompose this into the mechanism JSON. Use ONLY column names from the "
        "available list; return null for any anchor you cannot ground."
    )
    return "\n\n".join(parts)


def _unmapped_spec(hypothesis: Hypothesis, reason: str) -> MechanismSpec:
    """A NOT-mappable spec (no anchors) carrying the reason the router will read.

    Built with no allowed-set context: the None treatment/outcome alone forces
    ``mappable=False`` via the schema validator, and the explicit
    ``unmapped_reason`` is preserved.
    """
    return MechanismSpec(
        capability_name=hypothesis.capability_name,
        treatment_column=None,
        treatment_contrast="(unmapped)",
        outcome_column=None,
        confidence="low",
        unmapped_reason=reason,
    )


def translate_hypothesis(
    hypothesis: Hypothesis,
    available_columns: list[str],
    *,
    chat_client: ChatClient | None = None,
    model_id: str | None = None,
) -> MechanismSpec:
    """Translate a `Hypothesis` into a grounded :class:`MechanismSpec`.

    Args:
        hypothesis: the PM-supplied product change (prose + capability, no columns).
        available_columns: the exact column names in the customer's feature-store
            data. The translator may only ground to these; anything else is a
            dangling reference and downgrades the spec to NOT mappable.
        chat_client: an explicit vendor-agnostic client (short-circuits lazy
            resolution — this is how the suite injects a stub). When None, resolved
            lazily via ``get_chat_client`` exactly as ``input_lint`` does.
        model_id: optional model override forwarded to ``get_chat_client``.

    Returns:
        A `MechanismSpec`. On a clean grounding, `mappable=True` with the
        treatment/outcome/covariates/negative-controls populated. On ANY failure
        — ungroundable anchor, a column not in `available_columns` (referential
        integrity), an LLM transport error, or unparseable JSON — a
        `mappable=False` spec with an `unmapped_reason`. NEVER raises into the
        caller (a router decision, not an exception).
    """
    columns = [c for c in available_columns if isinstance(c, str) and c.strip()]

    client = chat_client if chat_client is not None else get_chat_client(model_id)

    # 1) One translator call. A transport / JSON-repair failure degrades to a
    #    NOT-mappable spec — never hard-fails the (later) run.
    try:
        raw = client.chat_json(
            [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": _user_turn(hypothesis, columns)},
            ],
            _TranslatorOutput,
        )
    except Exception as exc:  # noqa: BLE001 — degrade to fallback; never raise into caller
        log.warning(
            "mechanism_translator.llm_failed",
            error=str(exc),
            exc_type=type(exc).__name__,
        )
        return _unmapped_spec(hypothesis, reason=f"translator call failed: {exc}")

    # 2) Re-validate into the strict spec WITH the allowed-set in context so the
    #    schema validator enforces referential integrity and derives `mappable`.
    #    `confidence` is coerced to the ordinal Literal (an off-taxonomy value
    #    from the LLM degrades to "low" rather than raising).
    confidence = raw.confidence if raw.confidence in ("high", "low") else "low"
    try:
        spec = MechanismSpec.model_validate(
            {
                "capability_name": hypothesis.capability_name,
                "treatment_column": raw.treatment_column,
                "treatment_contrast": raw.treatment_contrast or "(unspecified)",
                "outcome_column": raw.outcome_column,
                "mediator": raw.mediator,
                "covariates": raw.covariates,
                "negative_controls": raw.negative_controls,
                "sibling_metric": raw.sibling_metric,
                "estimand": raw.estimand or "ATE on outcome",
                "confidence": confidence,
                "notes": raw.notes,
            },
            context={AVAILABLE_COLUMNS_CONTEXT_KEY: columns},
        )
    except Exception as exc:  # noqa: BLE001 — a malformed decomposition is a fallback, not a crash
        log.warning(
            "mechanism_translator.spec_invalid",
            error=str(exc),
            exc_type=type(exc).__name__,
        )
        return _unmapped_spec(hypothesis, reason=f"translated spec invalid: {exc}")

    return spec


__all__ = ["translate_hypothesis"]
