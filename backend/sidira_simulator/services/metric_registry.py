"""The metric registry — per-metric outcome elicitation dispatch (#275).

#221 shipped a per-metric outcome elicitation for ONE metric (conversion) via
inline `if metric_name == "conversion"` branches scattered across the schema
validator, the runner, and the scorer. #275 replaces every such branch with a
lookup in this registry, so a new metric routes end-to-end by registering a
`MetricDescriptor` here — no edits to the runner/scorer/validator dispatch.

Each descriptor bundles everything the rest of the pipeline needs for a metric:

  - `required_template_fields` — the Hypothesis fields the validator demands when
    this metric is selected (drives `Hypothesis._validate_metric`);
  - `default_choice_set` — the curated fallback alternatives when the rendered
    screen doesn't ground them;
  - `target_terms(hypothesis)` — the lowercased term(s) that name the metric's
    TARGET action, so the runner can filter them out of the grounded alternatives
    (offering two target-like options would split / undercount p_metric);
  - `elicit(...)` — runs the blinded §3e ensemble for this metric and returns
    `(mean_p_metric, paraphrase_unstable)`;
  - `aggregator` — the paired treatment−control lift fn (mean Δ p_metric ×100 pp);
  - `honesty(lift_result)` — the (regime_label, native-unit relative-statement)
    hook;
  - `calibrator_resolver()` — selects the metric's shrinkage calibrator (identity
    default for every metric pre-#222).

An UNKNOWN metric fails loud: the closed `Hypothesis.metric_name` Literal rejects
it at construction, and `get_metric` raises `KeyError` if a registered-but-unknown
name ever reaches dispatch. This module holds only an immutable registry dict
populated once at import — no mutable module state — so it is thread-safe to read
concurrently across the runner's per-agent fan-out.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

from sidira_simulator.schemas.feature_pack import Capability
from sidira_simulator.schemas.scoring import MetricLiftResult
from sidira_simulator.schemas.simulation import (
    DEFAULT_CONVERSION_CHOICE_SET,
    Hypothesis,
)
from sidira_simulator.services.conversion_calibrator import (
    MetricCalibrator,
    resolve_metric_calibrator,
)

# The honesty hook: (regime_label, relative-statement | None).
HonestyFn = Callable[[MetricLiftResult], tuple[str, str | None]]
# The paired-lift aggregator signature (positional t/c reactions, kw config).
AggregatorFn = Callable[..., MetricLiftResult]
# The per-agent elicitor adapter: returns (mean_p_metric, paraphrase_unstable).
ElicitFn = Callable[..., tuple[float, bool]]
CalibratorResolver = Callable[[], MetricCalibrator]


@dataclass(frozen=True)
class MetricDescriptor:
    """Everything the pipeline needs to route ONE metric end-to-end (#275)."""

    name: str
    required_template_fields: tuple[str, ...]
    default_choice_set: tuple[str, ...]
    aggregator: AggregatorFn
    honesty: HonestyFn
    elicit: ElicitFn
    calibrator_resolver: CalibratorResolver
    # Number of hand-authored §3e paraphrases available — the runner caps its
    # K-scaled per-agent timeout by this so an oversized env can't multiply the
    # budget past the calls that will actually run.
    paraphrase_count: int = 1
    # Given a Hypothesis, the lowercased term(s) naming this metric's TARGET
    # action — filtered out of grounded alternatives so the question never offers
    # two target-like options.
    target_terms: Callable[[Hypothesis], set[str]] = field(default=lambda h: set())


# ── conversion ─────────────────────────────────────────────────────────────


def _conversion_target_terms(hypothesis: Hypothesis) -> set[str]:
    terms = {
        (hypothesis.conversion_action or "").strip().lower(),
        (hypothesis.conversion_action_label or "").strip().lower(),
    }
    terms.discard("")
    return terms


def _conversion_elicit(
    chat_client,
    *,
    system_prompt: str,
    hypothesis: Hypothesis,
    capability: Capability,
    choice_set: Sequence[str] | None,
    paraphrases: int,
    timeout_scale_count: int,
) -> tuple[float, bool]:
    from sidira_simulator.services.conversion_elicitor import elicit_conversion_ensemble

    ensemble = elicit_conversion_ensemble(
        chat_client,
        system_prompt=system_prompt,
        capability_name=capability.name,
        conversion_action=hypothesis.conversion_action or "",
        conversion_action_label=hypothesis.conversion_action_label or "",
        decision_point=hypothesis.decision_point or "",
        choice_set=choice_set,
        paraphrases=paraphrases,
    )
    return ensemble.mean_p_conv, ensemble.paraphrase_unstable


def _conversion_honesty(lift_result: MetricLiftResult) -> tuple[str, str | None]:
    from sidira_simulator.services.scoring import metric_lift_honesty

    return metric_lift_honesty(lift_result)  # conversion defaults


def _conversion_aggregator(*args, **kwargs) -> MetricLiftResult:
    from sidira_simulator.services.scoring import aggregate_conversion_lift

    return aggregate_conversion_lift(*args, **kwargs)


# ── retention (#275 Decision B) ─────────────────────────────────────────────


def _retention_target_terms(hypothesis: Hypothesis) -> set[str]:
    # Retention's target is the "return" label. The PM may name it via
    # conversion_action_label (the generic metric label field) or rely on the
    # registry default. Filter that and the registry's return label out of any
    # grounded alternatives.
    from sidira_simulator.services.retention_elicitor import RETENTION_RETURN_LABEL

    terms = {
        (hypothesis.conversion_action_label or "").strip().lower(),
        RETENTION_RETURN_LABEL.lower(),
    }
    terms.discard("")
    return terms


def _retention_return_label(hypothesis: Hypothesis) -> str:
    from sidira_simulator.services.retention_elicitor import RETENTION_RETURN_LABEL

    label = (hypothesis.conversion_action_label or "").strip()
    return label or RETENTION_RETURN_LABEL


def _retention_elicit(
    chat_client,
    *,
    system_prompt: str,
    hypothesis: Hypothesis,
    capability: Capability,
    choice_set: Sequence[str] | None,
    paraphrases: int,
    timeout_scale_count: int,
) -> tuple[float, bool]:
    from sidira_simulator.services.retention_elicitor import elicit_retention_ensemble

    ensemble = elicit_retention_ensemble(
        chat_client,
        system_prompt=system_prompt,
        capability_name=capability.name,
        return_label=_retention_return_label(hypothesis),
        decision_point=hypothesis.decision_point or "",
        choice_set=choice_set,
        paraphrases=paraphrases,
    )
    return ensemble.mean_p_retention, ensemble.paraphrase_unstable


def _retention_honesty(lift_result: MetricLiftResult) -> tuple[str, str | None]:
    from sidira_simulator.services.scoring import RETENTION_REGIME_WEAK, metric_lift_honesty

    return metric_lift_honesty(
        lift_result,
        regime_label=RETENTION_REGIME_WEAK,
        verb_higher="retains directionally higher than control",
        verb_lower="retains directionally lower than control",
        verb_same="retain at the same directional rate",
        weak_signal_noun="Synthetic retention",
        propensity_noun="retention propensity",
    )


def _retention_aggregator(*args, **kwargs) -> MetricLiftResult:
    from sidira_simulator.services.scoring import aggregate_retention_lift

    return aggregate_retention_lift(*args, **kwargs)


# ── CTR (#276) ──────────────────────────────────────────────────────────────


def _ctr_target_terms(hypothesis: Hypothesis) -> set[str]:
    # CTR's target is the "click" label. The PM may name it via
    # conversion_action_label (the generic metric label field) or rely on the
    # registry default. Filter that and the registry's click label out of any
    # grounded alternatives so the question never offers two click-like options.
    #
    # CTR-specific hazard (codex P2): unlike conversion/retention — whose targets
    # are distinctive PM-named phrases unlikely to recur as a generic transition
    # trigger — CTR's target IS "a click", and a rendered/PM-supplied alternative
    # is very likely to ALSO be a click action (a figma click transition, e.g.
    # "click the headline", "tap to open"). If such a twin survives into the
    # alternatives it is offered alongside the prepended canonical click label but
    # p_metric counts ONLY the canonical label, so agents split click intent into
    # the uncounted twin and p_metric UNDERSTATES the true CTR. To prevent that we
    # filter not just the exact click label but the common click-verb phrasings a
    # grounded trigger uses. The runner matches alternatives against this set by
    # lowercased, stripped equality (`lbl.strip().lower() not in target_terms`);
    # grounded triggers are human phrases ("click the headline", "tap to open"),
    # so the enumerated phrasings below cover the realistic click triggers a crawl
    # or PM supplies. A PM who needs a genuinely distinct NON-click alternative
    # names it without a click verb; a click-action alternative is, by definition,
    # the same CTR event as the target and must not become an uncounted twin.
    from sidira_simulator.services.ctr_elicitor import CTR_CLICK_LABEL

    terms = {
        (hypothesis.conversion_action_label or "").strip().lower(),
        CTR_CLICK_LABEL.lower(),
        "click",
        "click it",
        "click here",
        "click the headline",
        "tap",
        "tap it",
        "tap to open",
        "open it",
    }
    terms.discard("")
    return terms


def _ctr_click_label(hypothesis: Hypothesis) -> str:
    from sidira_simulator.services.ctr_elicitor import CTR_CLICK_LABEL

    label = (hypothesis.conversion_action_label or "").strip()
    return label or CTR_CLICK_LABEL


def _ctr_elicit(
    chat_client,
    *,
    system_prompt: str,
    hypothesis: Hypothesis,
    capability: Capability,
    choice_set: Sequence[str] | None,
    paraphrases: int,
    timeout_scale_count: int,
) -> tuple[float, bool]:
    from sidira_simulator.services.ctr_elicitor import elicit_ctr_ensemble

    ensemble = elicit_ctr_ensemble(
        chat_client,
        system_prompt=system_prompt,
        capability_name=capability.name,
        click_label=_ctr_click_label(hypothesis),
        decision_point=hypothesis.decision_point or "",
        choice_set=choice_set,
        paraphrases=paraphrases,
    )
    return ensemble.mean_p_ctr, ensemble.paraphrase_unstable


def _ctr_honesty(lift_result: MetricLiftResult) -> tuple[str, str | None]:
    from sidira_simulator.services.scoring import CTR_REGIME_STRONG, metric_lift_honesty

    return metric_lift_honesty(
        lift_result,
        regime_label=CTR_REGIME_STRONG,
        verb_higher="clicks through directionally higher than control",
        verb_lower="clicks through directionally lower than control",
        verb_same="click through at the same directional rate",
        weak_signal_noun="Synthetic CTR",
        # CTR is a STRONG regime (§5), so it must NOT inherit the weak-behavioral
        # caveat wording — but its magnitude is still uncalibrated pre-#222, so the
        # read-as-rank/direction caveat stays (codex P2).
        signal_strength_clause=(
            "is a strong behavioral signal whose magnitude is not yet calibrated"
        ),
        propensity_noun="click-through propensity",
    )


def _ctr_aggregator(*args, **kwargs) -> MetricLiftResult:
    from sidira_simulator.services.scoring import aggregate_ctr_lift

    return aggregate_ctr_lift(*args, **kwargs)


def _build_registry() -> dict[str, MetricDescriptor]:
    # Imported lazily inside the descriptor closures above to avoid an import
    # cycle (scoring ← registry ← scoring). Built once at module import.
    from sidira_simulator.services.conversion_elicitor import CONVERSION_PARAPHRASE_COUNT
    from sidira_simulator.services.ctr_elicitor import (
        CTR_PARAPHRASE_COUNT,
        DEFAULT_CTR_CHOICE_SET,
    )
    from sidira_simulator.services.retention_elicitor import (
        DEFAULT_RETENTION_CHOICE_SET,
        RETENTION_PARAPHRASE_COUNT,
    )

    return {
        "conversion": MetricDescriptor(
            name="conversion",
            required_template_fields=(
                "conversion_action",
                "conversion_action_label",
                "decision_point",
            ),
            default_choice_set=DEFAULT_CONVERSION_CHOICE_SET,
            aggregator=_conversion_aggregator,
            honesty=_conversion_honesty,
            elicit=_conversion_elicit,
            calibrator_resolver=lambda: resolve_metric_calibrator("conversion"),
            target_terms=_conversion_target_terms,
            paraphrase_count=CONVERSION_PARAPHRASE_COUNT,
        ),
        "retention": MetricDescriptor(
            name="retention",
            # Retention reuses the generic label field (conversion_action_label)
            # for the "return" label, but it is OPTIONAL (the registry default
            # "return next week" applies when absent). The only hard requirement
            # is decision_point — the post-experience moment (Decision B).
            required_template_fields=("decision_point",),
            default_choice_set=DEFAULT_RETENTION_CHOICE_SET,
            aggregator=_retention_aggregator,
            honesty=_retention_honesty,
            elicit=_retention_elicit,
            calibrator_resolver=lambda: resolve_metric_calibrator("retention"),
            target_terms=_retention_target_terms,
            paraphrase_count=RETENTION_PARAPHRASE_COUNT,
        ),
        "ctr": MetricDescriptor(
            name="ctr",
            # CTR is the closest sibling to conversion: a binary on-screen click,
            # immediate, no temporal framing. Like retention it reuses the generic
            # label field (conversion_action_label) for the click label, but it is
            # OPTIONAL (the registry default "click it" applies when absent). The
            # only hard requirement is decision_point — the on-screen moment the
            # rendered element sits at (#276).
            required_template_fields=("decision_point",),
            default_choice_set=DEFAULT_CTR_CHOICE_SET,
            aggregator=_ctr_aggregator,
            honesty=_ctr_honesty,
            elicit=_ctr_elicit,
            calibrator_resolver=lambda: resolve_metric_calibrator("ctr"),
            target_terms=_ctr_target_terms,
            paraphrase_count=CTR_PARAPHRASE_COUNT,
        ),
    }


# Immutable registry: built once at import, then wrapped in a MappingProxyType so
# it is genuinely read-only (no insert/pop/clear) → safe to read concurrently
# across the runner's per-agent fan-out with no lock (codex).
_REGISTRY: Mapping[str, MetricDescriptor] = MappingProxyType(_build_registry())


def get_metric(metric_name: str) -> MetricDescriptor:
    """Return the descriptor for `metric_name`, or raise loudly (#275).

    The closed `Hypothesis.metric_name` Literal already rejects unknown metrics at
    construction; this is the defense-in-depth dispatch guard — a registered-but-
    unknown name (a Literal/registry drift) raises KeyError rather than silently
    degrading to sentiment.
    """
    try:
        return _REGISTRY[metric_name]
    except KeyError as exc:
        raise KeyError(
            f"unknown metric_name {metric_name!r}; registered metrics: " f"{sorted(_REGISTRY)}"
        ) from exc


def is_registered(metric_name: str | None) -> bool:
    return metric_name in _REGISTRY


def required_template_fields(metric_name: str) -> tuple[str, ...]:
    """The Hypothesis template fields required when `metric_name` is selected.

    Drives `Hypothesis._validate_metric`. Raises (via get_metric) for an unknown
    metric so the validator surfaces a loud failure rather than skipping required
    fields — matching the no-silent-degradation contract.
    """
    return get_metric(metric_name).required_template_fields
