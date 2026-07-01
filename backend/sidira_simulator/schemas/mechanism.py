"""Mechanism spec — the LLM-as-translator output (Epic #538, ticket #539 / Phase-1a).

The engine is being rewired (Epic #538) away from disproven LLM persona role-play
into a grounded, direction-only pipeline:

    LLM-as-translator → grounded g-formula predictor → negative-control watchdog
    → LLM fallback.

This schema is the CONTRACT at the FRONT of that pipeline. The LLM does **not**
predict here — it *translates* a `Hypothesis` (free prose + a named capability)
into a structured :class:`MechanismSpec`: which column is the treatment/lever
(T), the human-readable treatment contrast (baseline → treatment), the outcome
column (Y), the mediator the change works through, the covariates/confounders to
adjust (X), the candidate negative-control columns (for the watchdog), and an
optional sibling/cannibalization metric.

The spec carries NO predicted number (direction-only philosophy). It names the
mechanism; the grounded estimator (#540) and the negative-control guard (#541)
compute on it. The field names/shapes are deliberately aligned with
``research/empirical-uplift-spike/causal_estimator.py`` —
``estimate(df, treatment, outcome, covariates)`` and
``negative_control_guard(df, treatment, outcome, neg_controls, covariates, ...)``
— so the downstream tickets can consume a `MechanismSpec` directly:

    estimate(df, spec.treatment_column, spec.outcome_column, spec.covariates)
    negative_control_guard(df, spec.treatment_column, spec.outcome_column,
                           spec.negative_controls, spec.covariates)

**Mappability.** A spec is only usable by the grounded estimator if the treatment
and the outcome both ground to real columns in the customer's feature store. The
`mappable` flag is DERIVED (never trusted from the LLM): a `model_validator`
forces it False when the treatment or outcome column is None, or when any named
column is not in a provided allowed-set (referential integrity — a spec must
never reference a column that doesn't exist in the data). The router (#542) uses
`mappable=False` to fall back to LLM simulation.

This ships INERT: nothing in a live request path imports it (only the translator
service and the test suite do), so it is safe in prod.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationInfo, model_validator

# The validation-context key the translator passes so the model_validator can
# enforce referential integrity (a named column must exist in the data). When the
# context is absent (e.g. a spec constructed directly in a unit test without an
# allowed-set), the referential check is skipped — only the None-column check
# runs. Mirrors the "provided allowed-set" wording in the ticket.
AVAILABLE_COLUMNS_CONTEXT_KEY = "available_columns"


class MechanismSpec(BaseModel):
    """Structured mechanism decomposition of a `Hypothesis` (ticket #539).

    Migration-free, ``extra="forbid"`` (an LLM that invents a field fails loudly
    rather than smuggling a parallel vocabulary), mirroring the house style of the
    other schemas. Carries no predicted number — it describes the mechanism the
    grounded estimator will compute on, never the answer.

    Column fields (`treatment_column`, `outcome_column`, `mediator`,
    `sibling_metric`, and the `covariates` / `negative_controls` lists) name
    columns in the customer's feature store. `mappable` is DERIVED by the
    validator, never trusted from the LLM: a spec that can't ground its treatment
    or outcome — or that references a column outside the provided allowed-set — is
    marked NOT mappable, which the router later reads to fall back to LLM
    simulation.
    """

    model_config = ConfigDict(extra="forbid")

    capability_name: str
    # The lever (T). None when the LLM could not ground the treatment to a real
    # column → forces mappable=False.
    treatment_column: str | None = None
    # Human-readable baseline → treatment description (e.g. "gate at level 30 vs
    # gate at level 40"). Prose, not a column — it documents the contrast the
    # binary treatment encodes; never a predicted number.
    treatment_contrast: str
    # The outcome (Y). None when ungroundable → forces mappable=False.
    outcome_column: str | None = None
    # The mediator the change is theorized to work through (a column, optional).
    mediator: str | None = None
    # Confounders/covariates to adjust (X) — feeds estimate()/guard() directly.
    covariates: list[str] = []
    # Candidate negative-control columns for the watchdog — outcomes the treatment
    # should NOT cause but which share the confounding. Feeds
    # negative_control_guard()'s `neg_controls`.
    negative_controls: list[str] = []
    # Optional sibling / cannibalization metric (a column) — a co-moving outcome to
    # watch for a lift that merely shifts volume from a sibling surface.
    sibling_metric: str | None = None
    # The estimand in words (e.g. "ATE on outcome"). Direction-only — no number.
    estimand: str = "ATE on outcome"
    # DERIVED by the validator (do NOT trust from the LLM). False when the
    # treatment or outcome is ungrounded, or a named column violates referential
    # integrity against the provided allowed-set.
    mappable: bool = True
    # The translator's self-reported grounding confidence. Ordinal, never a score.
    confidence: Literal["high", "low"] = "low"
    # Populated when mappable is False, naming why the spec couldn't be grounded.
    unmapped_reason: str | None = None
    # Optional free-text translator notes (assumptions, caveats). Never a number.
    notes: str | None = None

    @model_validator(mode="after")
    def _derive_mappability(self, info: ValidationInfo) -> MechanismSpec:
        """Force `mappable=False` on any grounding failure (referential integrity).

        Two independent failure modes, either of which downgrades the spec:

        1. **Missing anchor.** `treatment_column` or `outcome_column` is None — the
           grounded estimator has nothing to estimate.
        2. **Dangling reference.** When an allowed-set of real columns is supplied
           via validation context (`AVAILABLE_COLUMNS_CONTEXT_KEY`), any named
           column — treatment, outcome, mediator, sibling, or any covariate /
           negative control — that is not in the set means the spec references a
           column that doesn't exist in the data.

        `mappable` is derived here, not trusted from the LLM. On a downgrade an
        `unmapped_reason` is stamped (a caller-provided reason is preserved). The
        referential check is skipped when no allowed-set is provided.
        """
        reasons: list[str] = []

        if self.treatment_column is None or self.outcome_column is None:
            missing = [
                name
                for name, val in (
                    ("treatment_column", self.treatment_column),
                    ("outcome_column", self.outcome_column),
                )
                if val is None
            ]
            reasons.append(f"unmapped required column(s): {', '.join(missing)}")

        allowed = (info.context or {}).get(AVAILABLE_COLUMNS_CONTEXT_KEY)
        if allowed is not None:
            allowed_set = set(allowed)
            named: list[str] = []
            for col in (
                self.treatment_column,
                self.outcome_column,
                self.mediator,
                self.sibling_metric,
            ):
                if col is not None:
                    named.append(col)
            named.extend(self.covariates)
            named.extend(self.negative_controls)
            # Preserve order, de-dup, keep only the ones that dangle.
            seen: set[str] = set()
            dangling = [c for c in named if c not in allowed_set and not (c in seen or seen.add(c))]
            if dangling:
                reasons.append(f"column(s) not in available data: {', '.join(dangling)}")

        if reasons:
            self.mappable = False
            if self.unmapped_reason is None:
                self.unmapped_reason = "; ".join(reasons)

        return self


__all__ = ["MechanismSpec", "AVAILABLE_COLUMNS_CONTEXT_KEY"]
