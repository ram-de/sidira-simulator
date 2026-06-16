"""Per-metric outcome elicitation — the conversion question (#221 / §3a).

BLINDED in-character decision elicitation. This is a SEPARATE pass from the
free-text reaction (`reaction_elicitor`): it runs on a blinded system prompt
(`prompt_composer.compose_metric_prompt`) where the agent sees the state it faces
as a standalone product with NO change framing, and it is NOT conditioned on the
agent's turn-1 reaction. That blinding is the single most important framing rule
(agent-behavior-spec §3b/§4): an unblinded metric pass inflates the TREATMENT
arm's propensity via demand characteristics, and that bias does NOT cancel in the
treatment−control delta — it corrupts the headline conversion lift. The free-text
reaction still feeds sentiment/chat unblinded; only this metric pass is blinded.

The agent allocates "10 trials in your normal life" across the conversion action
and the realistic non-conversion alternatives (verbalized allocation, one
`chat_json` call). The conversion propensity is the share allocated to the
conversion action: `p_conv = counts[label] / total`.

#275: the blinded call, key resolution, completeness check, validation, and the
§3e ensemble are factored into `services.metric_elicitor_core` and shared with
the sibling `retention_elicitor`. This module owns ONLY the conversion-specific
question paraphrases + defaults and delegates the mechanics — so the conversion
path stays behaviorally byte-identical while retention rides the same core.

§3e paraphrase ensemble. `elicit_conversion_ensemble` runs the SAME blinded pass
under K hand-authored paraphrases of the *question wording only* (the system
prompt — blinded identity + standalone state — and the option set are held
byte-identical), then averages `p_conv` over the K answers. This isolates
prompt-surface sensitivity from content: if the agent's choice flips when the
question is merely reworded, that answer is wording-driven and the ensemble flags
it low-confidence. Paraphrase index 0 is the canonical wording, so K=1 is
byte-identical to `elicit_conversion_decision` and the feature is opt-in
(`runtime_config.resolve_conversion_paraphrases`, default 1).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sidira_simulator.adapters.llm import ChatClient
from sidira_simulator.schemas.elicitation import MetricDecision
from sidira_simulator.schemas.simulation import DEFAULT_CONVERSION_CHOICE_SET
from sidira_simulator.services.metric_elicitor_core import (
    MetricEnsembleResult,
    _MetricAllocation,
    build_options,
    elicit_ensemble,
    elicit_one,
    json_contract,
    option_bullets,
    resolve_count,
)

# Backwards-compatible aliases: the conversion-named symbols some tests/imports
# still use. #275 factored the mechanics into the shared core; the public
# conversion surface is preserved verbatim.
_ConversionAllocation = _MetricAllocation
ConversionDecision = MetricDecision
PARAPHRASE_INSTABILITY_P_CONV_SPREAD = 0.2  # mirrors core's threshold; kept for back-compat


def _resolve_count(allocation: dict[str, int], label: str) -> dict[str, int]:
    """Back-compat shim for the shared `resolve_count` (#275)."""
    return resolve_count(allocation, label)


def _option_bullets(options: Sequence[str], conversion_action_label: str) -> str:
    # Pass conversion's historical tag verbatim so the default conversion prompt
    # stays byte-identical after the #275 core factor-out (codex P2).
    return option_bullets(options, conversion_action_label, target_tag="   <- the conversion")


def _json_contract(options: Sequence[str]) -> str:
    return json_contract(options)


def _conversion_user_turn(
    *,
    capability_name: str,
    conversion_action: str,
    conversion_action_label: str,
    decision_point: str,
    options: Sequence[str],
) -> str:
    """Paraphrase 0 — the CANONICAL §3a decision question. The blinded identity +
    standalone state live in the system prompt; this adds ONLY the decision ask.
    It must stay blinded too — no "the change", no "you just saw", nothing that
    presumes a prior reaction or signals an intervention is under test (§3b).

    This is the byte-for-byte historical wording: `elicit_conversion_decision`
    and the ensemble at K=1 both use it, so the default path is unchanged."""
    bullets = _option_bullets(options, conversion_action_label)
    return (
        "## What you do next\n\n"
        f"Think about how you use the {capability_name}. Forget what a "
        '"reasonable" person would do — think about what YOU actually do next, '
        "given how you normally behave (your behavioral snapshot above). Be "
        "honest with yourself: most of the time, on most visits, people do NOT "
        f"{conversion_action} — they get distracted, put it off, or just keep "
        "browsing. Hold yourself to that bar.\n\n"
        f"You're at this moment: {decision_point}\n\n"
        "If you hit this exact moment 10 separate times in your normal life, how "
        "would those 10 times split across what you'd do? Put a whole number on "
        "each (they add up to 10):\n\n"
        f"{bullets}\n\n"
        "Then give, in one sentence, the single biggest reason your split looks "
        "the way it does — tied to something specific about you or the product, "
        "not a generic reason.\n\n" + _json_contract(options)
    )


def _conversion_user_turn_v2(
    *,
    capability_name: str,
    conversion_action: str,
    conversion_action_label: str,
    decision_point: str,
    options: Sequence[str],
) -> str:
    """Paraphrase 1 (§3e). Same blinded ask, same options, same JSON contract —
    only the question prose is reworded, to surface answers that depend on phrasing
    rather than on the agent's actual behavior. Stays blinded: no change framing,
    no presumed prior reaction."""
    bullets = _option_bullets(options, conversion_action_label)
    return (
        "## Your next move\n\n"
        f"Picture yourself actually using the {capability_name}, behaving the way "
        "you normally behave (see your snapshot above) — not the way some "
        'idealized, "sensible" user would. The honest truth is that on most '
        f"visits people do NOT {conversion_action}; they get sidetracked, leave it "
        "for later, or just keep looking around. Judge yourself by that "
        "reality.\n\n"
        f"The situation: {decision_point}\n\n"
        "Imagine living through this exact situation 10 separate times. Across "
        "those 10 times, how does your behavior break down? Assign a whole number "
        "to each option (the numbers total 10):\n\n"
        f"{bullets}\n\n"
        "In one sentence, name the single biggest driver of that breakdown — "
        "something concrete about you or the product, not a generic platitude.\n\n"
        + _json_contract(options)
    )


def _conversion_user_turn_v3(
    *,
    capability_name: str,
    conversion_action: str,
    conversion_action_label: str,
    decision_point: str,
    options: Sequence[str],
) -> str:
    """Paraphrase 2 (§3e). A third wording of the identical blinded ask. Reserved
    for K=3 ensembles; never used at the default K=1."""
    bullets = _option_bullets(options, conversion_action_label)
    return (
        "## What happens next for you\n\n"
        f"Be real about how you, specifically, move through the {capability_name}, "
        'based on your usual behavior above — set aside what a "rational" user is '
        f"supposed to do. Remember: the common case is that people do NOT "
        f"{conversion_action}; they get distracted, postpone it, or carry on "
        "browsing. Hold yourself honestly to that.\n\n"
        f"Right now you are here: {decision_point}\n\n"
        "Out of 10 times you land in exactly this spot in everyday life, count how "
        "many end in each outcome below. Give every option a whole number, and "
        "make them sum to 10:\n\n"
        f"{bullets}\n\n"
        "Then, in a single sentence, give the one reason that most shapes those "
        "counts — specific to you or to the product, never a generic answer.\n\n"
        + _json_contract(options)
    )


# §3e paraphrase set. Index 0 is the canonical historical wording (K=1 is
# byte-identical). Hand-authored and reviewed (spec §3e Q3: meaning-stability over
# diversity) — every entry must keep the SAME blinding, the SAME options, and the
# SAME JSON contract, rewording ONLY the natural-language question.
_QUESTION_PARAPHRASES = (
    _conversion_user_turn,
    _conversion_user_turn_v2,
    _conversion_user_turn_v3,
)

# Public: the number of hand-authored paraphrases the ensemble can actually run.
CONVERSION_PARAPHRASE_COUNT = len(_QUESTION_PARAPHRASES)


def _build_options(conversion_action_label: str, choice_set: Sequence[str] | None) -> list[str]:
    """Conversion option first, then the realistic non-conversion paths (#275
    delegates to the shared core, with the conversion default choice set)."""
    return build_options(conversion_action_label, choice_set, DEFAULT_CONVERSION_CHOICE_SET)


def _elicit_one(
    chat_client: ChatClient,
    *,
    system_prompt: str,
    user_turn: str,
    conversion_action_label: str,
    options: Sequence[str],
    temperature: float,
    seed: int | None,
    max_tokens: int,
) -> ConversionDecision:
    """One blinded chat_json call → validated decision (#275: shared core)."""
    return elicit_one(
        chat_client,
        system_prompt=system_prompt,
        user_turn=user_turn,
        target_label=conversion_action_label,
        options=options,
        temperature=temperature,
        seed=seed,
        max_tokens=max_tokens,
    )


def elicit_conversion_decision(
    chat_client: ChatClient,
    *,
    system_prompt: str,
    capability_name: str,
    conversion_action: str,
    conversion_action_label: str,
    decision_point: str,
    choice_set: Sequence[str] | None = None,
    temperature: float = 0.0,
    seed: int | None = None,
    max_tokens: int = 1024,
) -> ConversionDecision:
    """Elicit a per-agent conversion decision on a BLINDED system prompt.

    A standalone pass — NOT conditioned on the agent's turn-1 reaction (§3b): the
    `system_prompt` must be the blinded metric prompt from
    `prompt_composer.compose_metric_prompt` (standalone state, no change framing).

    Single-prompt path (the canonical paraphrase, index 0). For the K-paraphrase
    ensemble (§3e) see `elicit_conversion_ensemble`; this function is the K=1 case.

    Raises ValueError on a degenerate allocation (no positive total, or the
    conversion action absent) — surfaced by the caller as a per-agent conversion
    failure, never a silent zero.
    """
    options = _build_options(conversion_action_label, choice_set)
    user_turn = _conversion_user_turn(
        capability_name=capability_name,
        conversion_action=conversion_action,
        conversion_action_label=conversion_action_label,
        decision_point=decision_point,
        options=options,
    )
    return _elicit_one(
        chat_client,
        system_prompt=system_prompt,
        user_turn=user_turn,
        conversion_action_label=conversion_action_label,
        options=options,
        temperature=temperature,
        seed=seed,
        max_tokens=max_tokens,
    )


@dataclass(frozen=True)
class ConversionEnsembleResult:
    """Outcome of a §3e paraphrase ensemble for one conversion agent.

    A thin conversion-named view over the shared `MetricEnsembleResult` (#275):
    `mean_p_conv` exposes the core's `mean_p_metric`. Construct via
    `elicit_conversion_ensemble`.
    """

    mean_p_conv: float
    paraphrase_unstable: bool
    decisions: tuple[ConversionDecision, ...]
    k_effective: int


def elicit_conversion_ensemble(
    chat_client: ChatClient,
    *,
    system_prompt: str,
    capability_name: str,
    conversion_action: str,
    conversion_action_label: str,
    decision_point: str,
    choice_set: Sequence[str] | None = None,
    paraphrases: int = 1,
    temperature: float = 0.0,
    seed: int | None = None,
    max_tokens: int = 1024,
) -> ConversionEnsembleResult:
    """Run the blinded conversion pass under K paraphrases and average p_conv (§3e).

    Only the *question wording* varies across the K calls — the `system_prompt`
    (blinded identity + standalone state, §3b) and the option set are held
    byte-identical. `paraphrases` is clamped to [1, CONVERSION_PARAPHRASE_COUNT];
    at K=1 this is byte-identical to `elicit_conversion_decision`.

    Failure posture mirrors the single-prompt path: a degenerate paraphrase is
    dropped; only if EVERY paraphrase fails does this raise (the last error), so
    the caller records a per-agent conversion failure — never a silent zero.
    """
    options = _build_options(conversion_action_label, choice_set)
    core = elicit_ensemble(
        chat_client,
        system_prompt=system_prompt,
        paraphrases_builders=_QUESTION_PARAPHRASES,
        paraphrase_count=CONVERSION_PARAPHRASE_COUNT,
        target_label=conversion_action_label,
        options=options,
        build_user_turn_kwargs=dict(
            capability_name=capability_name,
            conversion_action=conversion_action,
            conversion_action_label=conversion_action_label,
            decision_point=decision_point,
            options=options,
        ),
        paraphrases=paraphrases,
        temperature=temperature,
        seed=seed,
        max_tokens=max_tokens,
    )
    return ConversionEnsembleResult(
        mean_p_conv=core.mean_p_metric,
        paraphrase_unstable=core.paraphrase_unstable,
        decisions=core.decisions,
        k_effective=core.k_effective,
    )


__all__ = [
    "_ConversionAllocation",
    "ConversionDecision",
    "ConversionEnsembleResult",
    "CONVERSION_PARAPHRASE_COUNT",
    "PARAPHRASE_INSTABILITY_P_CONV_SPREAD",
    "_QUESTION_PARAPHRASES",
    "_build_options",
    "_conversion_user_turn",
    "_elicit_one",
    "_json_contract",
    "_option_bullets",
    "_resolve_count",
    "elicit_conversion_decision",
    "elicit_conversion_ensemble",
    "MetricEnsembleResult",
]
