"""Simulation request/result schemas — the PM-facing API contract."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sidira_simulator.schemas.feature_pack import ReverseFigma

# agent-behavior-spec §3a / #221: the curated fallback choice set for the
# conversion question when the rendered screen doesn't enumerate the on-screen
# paths. Kept here (not in the elicitor) so it's part of the API contract a
# Hypothesis is validated against. The conversion option itself is prepended by
# the elicitor from `conversion_action_label`; these are the realistic
# *non*-conversion alternatives a real user actually takes.
#
# #275: this remains the conversion metric's default and is now ALSO registered
# in the metric registry (`services.metric_registry`) as that metric's
# `default_choice_set`. The retention metric supplies its own default there. The
# constant is kept here for backwards-compatible imports and because the
# conversion choice set is part of the long-standing API contract.
DEFAULT_CONVERSION_CHOICE_SET: tuple[str, ...] = (
    "keep browsing / decide later",
    "leave without doing anything",
    "compare with a competitor first",
)


class Hypothesis(BaseModel):
    """PM-supplied feature change being validated."""

    capability_name: str
    prose: str
    proposed_prd: str | None = None
    proposed_figma: ReverseFigma | None = None

    # ── Per-metric outcome elicitation (agent-behavior-spec §3a / #221, #275) ──
    # OPTIONAL structured target metric. When `metric_name` is None (the
    # default), the simulator behaves byte-identically to the historical
    # sentiment-only path — these fields are never read. When a metric is set,
    # the runner adds a turn-2 in-character BLINDED decision elicitation and the
    # scorer reports a paired metric-lift delta ALONGSIDE the sentiment
    # confidence_score (never replacing it).
    #
    # #275 generalizes the original conversion-only feature into a metric
    # REGISTRY (`services.metric_registry`): each metric supplies its elicitor,
    # paired-lift aggregator, default choice set, required template fields, regime
    # label, and calibrator. `metric_name` is a CLOSED Literal so an unknown
    # metric fails loudly (no silent degradation to sentiment); a metric routes
    # end-to-end iff it is registered. `retention` is the first sibling (#275);
    # `conversion` keeps its byte-identical behavior; `ctr` (#276) is the
    # on-screen click-through sibling, closest to conversion.
    metric_name: Literal["conversion", "retention", "ctr"] | None = None
    # The metric event + its in-character phrasing. For conversion: the
    # conversion action ("complete checkout") + its label ("check out now"). For
    # retention: the post-experience moment + the "return" label. Required fields
    # per metric are declared by the registry's `required_template_fields`.
    conversion_action: str | None = None
    conversion_action_label: str | None = None
    # The moment the user is at — conversion: "you've added 2 items to your
    # cart"; retention (§275 Decision B): "you've just finished tonight's
    # session". Required for every registered metric.
    decision_point: str | None = None
    # Realistic non-target alternatives, sourced from the rendered screen
    # (treatment-rendering layer). Empty → the metric's registry default choice
    # set (conversion: DEFAULT_CONVERSION_CHOICE_SET; retention: its own).
    choice_set: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_metric(self) -> Hypothesis:
        """When a metric is selected, its template fields must be present.

        Fail loud rather than silently eliciting a malformed metric question
        (§3a no-silent-degradation). The required-field list is DRIVEN BY THE
        REGISTRY per metric (#275): an unregistered metric is already rejected by
        the closed Literal above, and a registered metric missing any of its
        declared template fields raises here. `choice_set` is allowed to be empty
        — the elicitor falls back to the metric's registry default choice set.
        """
        if self.metric_name is None:
            return self
        # Lazy import: services.metric_registry imports schemas (this module), so
        # a module-level import would be circular. The registry is the single
        # source of truth for each metric's required template fields.
        from sidira_simulator.services.metric_registry import required_template_fields

        required = required_template_fields(self.metric_name)
        missing = [name for name in required if not ((getattr(self, name, None) or "").strip())]
        if missing:
            raise ValueError(
                f"metric_name={self.metric_name!r} requires non-empty " f"{', '.join(missing)}"
            )
        return self


class ArmSplit(BaseModel):
    """A/B experiment-mode configuration (Phase 4.6 #88).

    When set on a SimulationRequest, the simulator runs BOTH a treatment
    arm (agents see the proposed change) and a control arm (agents see
    the current product, no change). The lift between arms is computed
    via paired bootstrap on per-agent sentiment delta (#90).

    `treatment_fraction` defines what share of population_size goes to
    treatment vs control. Paired sampling (Phase 4.6 Q3, locked
    2026-05-26) requires identical `(persona_id, sample_index)` across
    arms, so the statistically-optimal fraction is 0.5 — anything else
    leaves unmatched agents in the larger arm with no pair to compare
    against. The field exists for future flexibility (if independent
    sampling ever returns) but the wizard hides the slider and submits
    0.5 in v1.
    """

    model_config = ConfigDict(extra="forbid")

    treatment_fraction: float = Field(
        default=0.5,
        ge=0.5,
        le=0.5,
        description=(
            "Fraction of population_size allocated to the treatment arm. "
            "v1 only supports 0.5 (paired sampling). Codex P2 on PR #95: "
            "non-0.5 splits get silently overridden by the per-arm max "
            "agent cap (treatment_fraction=0.8 with cap=50 still produces "
            "50/50), and #90's paired lift formula needs f=0.5 anyway. "
            "Re-open this range when we have a product reason for "
            "asymmetric arms AND a scorer that supports them."
        ),
    )


class SimulationRequest(BaseModel):
    """PM-submitted simulation request (Phase 2.5).

    `population_size` is the modeled userbase size — the simulator stratifies
    down to at most MAX_AGENTS actual agents using largest-remainder allocation.

    `arm_split` (Phase 4.6 #88) enables A/B mode when present. Single-arm
    sims omit it; backwards-compatible with all pre-#88 requests.
    """

    model_config = ConfigDict(extra="forbid")  # reject the retired persona_sample_size

    hypothesis: Hypothesis
    population_size: int = Field(default=1000, ge=1, le=10_000_000)
    # Bound to signed BIGINT range so over-large values fail at request validation
    # rather than as a Postgres INSERT error after the row is half-built. (codex P2)
    run_seed: int | None = Field(default=None, ge=-(2**63), le=2**63 - 1)
    arm_split: ArmSplit | None = Field(
        default=None,
        description=(
            "When present, runs A/B mode (treatment + control arms with "
            "paired sampling). When None, runs single-arm (today's behavior). "
            "See docs/4.6-ab-experiment-mode.md."
        ),
    )
    selected_personas: list[str] | None = Field(
        default=None,
        description=(
            "Phase 5 #101: optional subset of persona_ids to run the sim "
            "against. When None, runs against ALL personas in the active "
            "Persona Pack (today's behavior, backwards-compatible). When a "
            "non-empty list, the allocator filters to these personas and "
            "re-weights them to sum to 1 before largest-remainder "
            "allocation, so `population_size` is preserved across the "
            "selected cohort. Empty list is rejected. Unknown persona_ids "
            "are rejected at the API layer (the schema can't see the "
            "active pack). A/B mode applies the filter symmetrically to "
            "both arms (the paired-sampling invariant from #89 keeps "
            "working because both arms run the same persona set)."
        ),
    )
    model_id: str | None = Field(
        default=None,
        max_length=64,
        description=(
            "Phase 5 #103: optional LLM model id powering this simulation. "
            "When omitted, the backend resolves its configured default."
        ),
    )
    include_no_persona_control: bool = Field(
        default=False,
        description=(
            "#221 §4.1 persona-lift baseline. When True, a 1:1 shadow panel of "
            "no-persona agents (the base LLM with persona conditioning stripped) "
            "reacts to the SAME proposed change, and the result surfaces "
            "persona_lift = persona − no_persona sentiment delta. The shadows "
            "are ephemeral (never persisted) and don't affect the headline "
            "confidence_score. Default False → byte-identical to today. Only "
            "the single-arm path supports it; A/B mode ignores it for now."
        ),
    )
    include_current_state_control: bool = Field(
        default=False,
        description=(
            "#221 §3.3.1 delta-mode. When True, a 1:1 shadow panel of the SAME "
            "personas reacts to the CURRENT product state (the proposed change "
            "omitted — the existing A/B control framing applied as a paired "
            "shadow in single-arm mode), and the result surfaces "
            "current_state_delta = treatment − current_state sentiment delta in "
            "confidence_score units. A 100%-paired design: every persona is its "
            "own control. The shadows are ephemeral (never persisted) and don't "
            "affect the headline confidence_score in this slice — the delta is "
            "purely additive. Default False → byte-identical to today. Only the "
            "single-arm path supports it; A/B mode ignores it for now."
        ),
    )
    run_as_generic_reception: bool = Field(
        default=False,
        description=(
            "Answerability gate override (#310 / T1). When the pre-flight gate "
            "blocks because no decision metric (OEC) was declared "
            "(metric_name is None), the PM may resubmit with this flag to "
            "proceed anyway — the run is then labeled generic-reception "
            "(sentiment only, NOT OEC-aligned) rather than dead-ended. It does "
            "NOT override the structurally-invisible-change block (there is no "
            "faithful way to simulate a wireframe described as prose). Default "
            "False → today's behavior. Does not touch confidence_score."
        ),
    )

    @field_validator("selected_personas")
    @classmethod
    def _selected_personas_nonempty(cls, v: list[str] | None) -> list[str] | None:
        # None = all personas (today's behavior). Explicit empty list is a
        # PM mistake: "I want to run against zero personas" has no meaning,
        # so we reject it here rather than letting the allocator return
        # zero agents downstream and the run fail at orchestrator time.
        # Unknown persona_id values can't be validated here (the schema
        # doesn't see the active pack); the API layer rejects those.
        if v is None:
            return v
        if len(v) == 0:
            raise ValueError(
                "selected_personas must contain at least one persona_id "
                "(or be omitted entirely to run against all personas)"
            )
        # Dedupe while preserving order — duplicate IDs in the list would
        # otherwise double-count a persona's weight at renormalization time.
        seen: set[str] = set()
        deduped: list[str] = []
        for pid in v:
            if pid not in seen:
                seen.add(pid)
                deduped.append(pid)
        return deduped


class SimulationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class Weakness(BaseModel):
    """One diagnosed weakness in the hypothesis.

    `frequency`/`ci_low`/`ci_high` are optional today; populated by the
    Wilson-CI scoring path (Phase 2.5 issue #6).
    """

    category: Literal[
        "wrong_metric",
        "wrong_cohort",
        "broken_mechanism",
        "untestable_hypothesis",
        "hidden_guardrail_risk",
        "underpowered_design",
    ]
    summary: str
    supporting_agent_ids: list[str] = Field(default_factory=list)
    frequency: float | None = Field(default=None, ge=0.0, le=1.0)
    ci_low: float | None = Field(default=None, ge=0.0, le=1.0)
    ci_high: float | None = Field(default=None, ge=0.0, le=1.0)


class InputFlags(BaseModel):
    """Pre-flight ordinal input-lint result, stamped on an amber/red/abstain run
    (epic #309, T3 / #312).

    CATEGORICAL only — an ordinal `state` + named `reasons` + stable
    `reason_codes`, NEVER a number or score (panel hard constraint: the lint
    ROUTES, it does not discount `confidence_score`). Populated by the runner
    from the pre-flight `services.input_lint.assess_input_lint` verdict (LLM
    judge + deterministic leading-framing lint + paraphrase-abstain). `state` is
    `amber` | `red` | `abstain`; a `green` run carries NO `input_flags` (the
    field stays None) so a clean run and every older `result_json` row load
    byte-identical and this is migration-free (it rides the result JSON blob, NOT
    a DB column). `reason_codes` are the existing weakness-taxonomy categories
    (`scoring._VALID_CATEGORIES`) plus the deterministic `leading_framing` code;
    `fixes` carries auto-neutralize hints for leading framing. The detail page
    surfaces this as an amber disclosure note (DESIGN.md §7.7 cautionary-note
    anatomy); the score is computed and persisted unchanged.
    """

    state: Literal["amber", "red", "abstain"]
    reasons: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    fixes: list[str] = Field(default_factory=list)
    paraphrase_unstable: bool = False


class AgentAnalysisSummary(BaseModel):
    """Per-agent post-run summary (#51 result table).

    Compact projection of `services.scoring.AgentAnalysis` shaped for the
    result-table cell render. Persisted on `SimulationResult.per_agent_analyses`
    so the table can render sentiment chips + top quotes without N R2 reads.

    `top_quote` is a short prefix of the agent's frozen `initial_reaction`,
    trimmed to a clean word boundary. Computed once at score time so a
    20-row table doesn't fan out 20 R2 GETs every page load.
    """

    agent_id: str
    sentiment: Literal["positive", "neutral", "negative"]
    sentiment_confidence: float = Field(ge=0.0, le=1.0)
    top_quote: str = Field(
        description="Short prefix of the agent's initial reaction.",
    )


class SimulationResult(BaseModel):
    confidence_score: float = Field(ge=0, le=100)
    confidence_score_ci: tuple[float, float] | None = None
    weaknesses: list[Weakness] = Field(default_factory=list)
    refinement_suggestions: list[str] = Field(default_factory=list)
    per_agent_analyses: list[AgentAnalysisSummary] = Field(
        default_factory=list,
        description=(
            "Per-agent sentiment + top quote for the result-table render. "
            "Populated by the runner when scoring completes. Empty for sims "
            "that ran before #51 landed (backwards-compatible)."
        ),
    )

    # ── Abstention / instrument-fit (epic #309, T2 / #311) ──
    # The sanctioned "fourth verdict state" carrier. CATEGORICAL only — a state
    # flag + named reasons, NEVER a number or score (panel hard constraint: the
    # abstention does not arithmetically discount confidence_score, it
    # categorically WITHHOLDS the ship/no-ship verdict). Populated by the runner
    # from the deterministic, zero-LLM instrument-fit detector
    # (services.answerability._detect_out_of_scope) when the OEC is unresolvable
    # by a first-exposure single-session panel (long-horizon / network /
    # novelty-decay). Default `False` / empty so a flag-off run and every older
    # `result_json` row load byte-identical and this is migration-free (it rides
    # the result JSON blob, NOT a DB column). When `instrument_scope` is
    # "out_of_scope", `verdictFor()` overrides the numeric verdict to
    # "NOT ANSWERABLE BY THIS INSTRUMENT" and surfaces `out_of_scope_reasons`.
    # The headline confidence_score is still computed and persisted unchanged.
    instrument_scope: Literal["in_scope", "out_of_scope"] = "in_scope"
    out_of_scope_reasons: list[str] = Field(default_factory=list)
    out_of_scope_reason_codes: list[str] = Field(default_factory=list)

    # ── Pre-flight ordinal input lint (epic #309, T3 / #312) ──
    # The degrade-and-disclose carrier for the amber/red/abstain input lint.
    # CATEGORICAL only (ordinal state + named reasons), NEVER a number — the lint
    # ROUTES, it does not discount confidence_score (panel hard constraint).
    # None on a `green` run (and on every older `result_json` row) so a clean run
    # loads byte-identical and this is migration-free (rides the result JSON
    # blob, NOT a DB column). When present, the detail page renders an amber
    # disclosure note (DESIGN.md §7.7) and the refinement queue is populated. The
    # headline confidence_score is computed and persisted unchanged.
    input_flags: InputFlags | None = None

    # ── A/B mode fields (Phase 4.6 #90) ──
    # All None / 0 for single-arm sims so older `result_json` rows load.
    treatment_score: float | None = None
    control_score: float | None = None
    lift: float | None = None
    lift_ci: tuple[float, float] | None = None
    lift_paired_n: int | None = None
    lift_unpaired_treatment: int = 0
    lift_unpaired_control: int = 0
    lift_sentiment_failure_drops: int = 0

    # ── Persona-lift baseline fields (#221 §4.1) ──
    # Populated only when the run requested `include_no_persona_control`.
    # All None / 0 otherwise, so older `result_json` rows load unchanged and
    # the headline confidence_score stays byte-identical to a flag-off run.
    # `persona_lift` is persona − no_persona sentiment delta in
    # confidence_score units ([-100, +100]); a `persona_lift_ci` straddling
    # zero is the falsification signal (personas add no signal over the base
    # model). The unpaired / failure counters surface what the paired
    # bootstrap excluded, matching the A/B lift counters above.
    no_persona_score: float | None = None
    persona_lift: float | None = None
    persona_lift_ci: tuple[float, float] | None = None
    persona_lift_paired_n: int | None = None
    persona_lift_unpaired_persona: int = 0
    persona_lift_unpaired_no_persona: int = 0
    persona_lift_sentiment_failure_drops: int = 0

    # ── Delta-mode fields (#221 §3.3.1) ──
    # Populated only when the run requested `include_current_state_control`.
    # All None / 0 otherwise, so older `result_json` rows load unchanged and
    # the headline confidence_score stays byte-identical to a flag-off run.
    # `current_state_score` is the same personas' standalone score reacting to
    # the CURRENT product state (the proposed change omitted); `current_state_delta`
    # is treatment − current_state sentiment delta in confidence_score units
    # ([-100, +100]). A `current_state_delta_ci` straddling zero is the
    # falsification signal (the proposed change moves no sentiment over leaving
    # the product as-is). The unpaired / failure counters surface what the paired
    # bootstrap excluded, matching the A/B + persona-lift counters above.
    current_state_score: float | None = None
    current_state_delta: float | None = None
    current_state_delta_ci: tuple[float, float] | None = None
    current_state_delta_paired_n: int | None = None
    current_state_delta_unpaired_persona: int = 0
    current_state_delta_unpaired_current_state: int = 0
    current_state_delta_sentiment_failure_drops: int = 0

    # ── Metric-lift fields (agent-behavior-spec §3a / #221; generalized #275) ──
    # Populated only when the run is A/B mode AND the Hypothesis carried a
    # `metric_name` (conversion / retention). All None / 0 otherwise, so older
    # `result_json` rows load unchanged and a non-metric run is byte-identical.
    #
    # #275 Decision A — GENERIC field naming. Exactly ONE `metric_name` is set per
    # simulation, so these are generic `metric_lift_*` fields, NOT parallel
    # per-metric ones. `metric_name` (below) is the discriminator so a consumer
    # knows the native unit (conversion-rate pp vs retention-rate pp). The legacy
    # `conversion_lift_*` keys were verified to have NO real (non-test) reader —
    # no API serializer reads them by name (the whole result rides a JSON blob),
    # no frontend type, no DB column — so the rename is migration-free: an older
    # row's `conversion_lift_*` keys are simply ignored on load and the renamed
    # fields default. The conversion path is otherwise behaviorally byte-identical.
    #
    # `metric_lift_pp` is the paired treatment−control delta in p_metric
    # (`action_counts[label] / total`), expressed in PERCENTAGE POINTS
    # ([-100, +100]); it is the same agent identity (#90 paired seed) deciding
    # against control vs treatment, so the agent's inflated absolute propensity
    # cancels in the delta. PRE-#222 the PM-facing headline is `metric_lift_relative`
    # (rank + direction + CI-excludes-zero), never the bare pp as truth (§5:
    # magnitude is uncalibrated until the shrinkage layer is fit). `metric_regime`
    # names the weak behavioral regime so the card never presents a behavioral
    # metric with the confidence of a copy/CTR test. Drop counters mirror the A/B
    # lift counters.
    #
    # `metric_name`: the native-unit discriminator (None for a non-metric run);
    # mirrors the Hypothesis's metric_name so a consumer reading only the result
    # knows which metric the lift belongs to.
    metric_name: str | None = None
    metric_lift_pp: float | None = None
    metric_lift_ci_pp: tuple[float, float] | None = None
    metric_lift_paired_n: int | None = None
    metric_lift_unpaired_treatment: int = 0
    metric_lift_unpaired_control: int = 0
    metric_lift_elicitation_failure_drops: int = 0
    metric_regime: str | None = None
    metric_lift_relative: str | None = None
    # #221 §3b: True when the metric fell back to the UNBLINDED prompt for at
    # least one treatment agent (the change had no faithful standalone view).
    # Defaults False so non-metric / fully-blinded runs and older rows are
    # byte-identical; `metric_lift_relative` also carries the caveat text.
    metric_lift_unblinded_fallback: bool = False
    # #221 §3e: True when at least one identity's metric propensity (p_metric)
    # moved materially across the K question paraphrases (its answer was
    # wording-driven). Defaults False so non-metric runs, the default K=1
    # single-prompt path, and older rows are byte-identical; `metric_lift_relative`
    # also carries the caveat text.
    metric_lift_paraphrase_unstable: bool = False
    # #221 shrinkage layer: True only when a FITTED calibrator (services.
    # conversion_calibrator) has mapped the raw `metric_lift_pp` onto the
    # real-world effect-size scale. The wired default is the identity no-op, so
    # this is False for every current run and older `result_json` rows load
    # unchanged; while False, `metric_lift_relative` carries the "uncalibrated
    # — read as rank/direction, not effect size" caveat. The fit is #222-gated.
    metric_lift_calibrated: bool = False
    # ── Metric↔sentiment disagreement guardrail (#321) ──
    # True when the metric and the sentiment lift are BOTH separable (their CIs
    # exclude zero) AND point in OPPOSITE directions. The dangerous case is
    # HARM-MISREAD: the uncalibrated metric reads positive-and-separable (it would
    # greenlight the change) while sentiment is negative-and-separable (users hate
    # it) — the validated failure mode where uncalibrated blinded retention gave
    # the WRONG SIGN on a harm (+2.0pp metric vs strongly negative sentiment). The
    # symmetric HIDDEN-IMPROVEMENT case (metric negative-separable, sentiment
    # positive-separable) also sets this flag. This is an HONEST, pre-calibration
    # surfacing: it claims NO magnitude, only a sign contradiction; it does NOT
    # touch `confidence_score`, `lift`, or `metric_lift_pp`. Default False so
    # non-metric runs, runs where either CI is None, and older `result_json` rows
    # load byte-identical and this is migration-free (it rides the result JSON
    # blob, NOT a DB column). Sign convention: positive metric = higher
    # propensity; positive sentiment lift = better-received. Until the metric is
    # calibrated (#222), TRUST SENTIMENT for harm when the two disagree.
    metric_sentiment_disagreement: bool = False
    # The explanation of the disagreement (the actual metric pp + CI and sentiment
    # lift + CI, and the trust-sentiment-for-harm guidance). None when there is no
    # disagreement. SURFACING: on HARM-MISREAD — the dangerous case, the whole
    # motivation — a `hidden_guardrail_risk` Weakness is ALSO appended to
    # `weaknesses`, which the result page already renders, so the harm path is
    # PM-visible today. HIDDEN-IMPROVEMENT (the symmetric, non-risk case) sets the
    # caveat ONLY and appends no weakness; like the `metric_lift_*` honesty flags
    # it rides the result JSON blob and is not yet wired into a dedicated frontend
    # card (a follow-up can render it on the metric panel — no schema change
    # needed, the field is already here).
    metric_sentiment_disagreement_caveat: str | None = None


class Simulation(BaseModel):
    id: str
    customer_id: str
    created_at: datetime
    status: SimulationStatus
    persona_pack_version: str
    feature_pack_version: str
    hypothesis: Hypothesis
    population_size: int | None = None
    sampled_agent_count: int | None = None
    run_seed: int | None = None
    arm_split: ArmSplit | None = None
    # Phase 5 #101: denormalized copy of the filter the PM submitted, so the
    # result-page cohort banner ("This run included N of M personas: …")
    # survives even if the Persona Pack changes after the sim completes.
    # None = all personas (today's behavior).
    selected_personas: list[str] | None = None
    # Phase 5 #103: denormalized model id used for the sim-time agent
    # reactions/classifiers, so result pages remain interpretable later.
    # Legacy rows may be NULL because they predate model tracking.
    model_id: str | None = None
    agent_instance_ids: list[str] = Field(default_factory=list)
    result: SimulationResult | None = None
