"""Per-metric outcome elicitation — the CTR (click-through) question (#276 / §3a).

The CTR sibling of `conversion_elicitor`, riding the SAME blinded core
(`services.metric_elicitor_core`): a BLINDED, in-character verbalized allocation
elicited on the standalone-state metric prompt (`prompt_composer.compose_metric_prompt`),
NEVER conditioned on the agent's turn-1 reaction. The blinding rule is identical
to conversion (§3b/§4) — an unblinded metric pass inflates the TREATMENT arm and
the bias does not cancel in the treatment−control delta.

CTR is the CLOSEST sibling to conversion: a binary CLICK decision on a rendered
element, ON-SCREEN and IMMEDIATE, with NO temporal framing (unlike retention's
future-return event). So:

  - the `decision_point` describes the on-screen moment the rendered element sits
    at (e.g. "the new banner is on your home feed") — an immediate, present-tense
    ask, never a future-return one;
  - the BLINDED `standalone_state_view` renders the proposed element as a
    standalone screen the agent encounters with NO change framing — exactly as
    conversion;
  - the agent allocates 10 trials across the CTR choice set
    `{"click it", "keep scrolling", "skip it", "leave"}`, where the FIRST option
    is the click event (`CTR_CLICK_LABEL`);
  - `p_metric = counts["click it"] / total` is the click-through propensity.

Native unit: click-through-rate lift in percentage points. Reuses the §3e
paraphrase ensemble, the #90 paired-delta, the #269 shrinkage/calibration seam,
and the §3b unblindable-fallback flag verbatim.

This module is PURE / STATELESS (the shared core holds no mutable state), so it
is safe to call concurrently across agents.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sidira_simulator.adapters.llm import ChatClient
from sidira_simulator.schemas.elicitation import MetricDecision
from sidira_simulator.services.metric_elicitor_core import (
    build_options,
    elicit_ensemble,
    elicit_one,
    json_contract,
    option_bullets,
)

# The CTR choice set. The FIRST option is the click event — `CTR_CLICK_LABEL` —
# counted as the metric target; the rest are the realistic non-click paths a real
# user actually takes when an on-screen element is presented. Used as the default
# when the Hypothesis supplies no grounded choice_set. The PM may override the
# click label via the generic label field (`conversion_action_label`); the default
# applies when absent.
CTR_CLICK_LABEL = "click it"
DEFAULT_CTR_CHOICE_SET: tuple[str, ...] = (
    "keep scrolling",
    "skip it",
    "leave",
)


def _ctr_user_turn(
    *,
    capability_name: str,
    click_label: str,
    decision_point: str,
    options: Sequence[str],
) -> str:
    """Paraphrase 0 — the CANONICAL CTR decision question (on-screen, immediate).

    Present-tense framing: the element is in front of the agent RIGHT NOW and the
    ask is whether, across 10 such moments, they click it. Stays blinded — no "the
    change", no "you just saw", nothing that presumes a prior reaction or signals
    an intervention is under test (§3b)."""
    bullets = option_bullets(options, click_label)
    return (
        "## What you do with it\n\n"
        f"Think about how you actually use the {capability_name} — not how an "
        '"engaged" user is supposed to behave, but what YOU really do, given your '
        "behavioral snapshot above. Be honest: most of the time, on most screens, "
        "people do NOT tap the thing in front of them — they scroll past it, "
        "ignore it, or move on. Hold yourself to that bar.\n\n"
        f"Right now: {decision_point}\n\n"
        "Picture this exact moment happening 10 separate times in your normal "
        "life. Across those 10 times, what do you do with it? Put a whole number "
        "on each (they add up to 10):\n\n"
        f"{bullets}\n\n"
        "Then give, in one sentence, the single biggest reason your split looks "
        "the way it does — tied to something specific about you or the product, "
        "not a generic reason.\n\n" + json_contract(options)
    )


def _ctr_user_turn_v2(
    *,
    capability_name: str,
    click_label: str,
    decision_point: str,
    options: Sequence[str],
) -> str:
    """Paraphrase 1 (§3e). Same blinded on-screen ask, same options, same JSON
    contract — only the question prose is reworded."""
    bullets = option_bullets(options, click_label)
    return (
        "## Whether you tap it\n\n"
        f"Picture yourself actually using the {capability_name}, behaving the way "
        "you normally behave (see your snapshot above) — not the way some "
        'idealized, "attentive" user would. The honest truth is that on most '
        "screens people do NOT tap what's put in front of them; they keep "
        "scrolling, ignore it, or close out. Judge yourself by that reality.\n\n"
        f"The situation: {decision_point}\n\n"
        "Imagine hitting this exact moment 10 separate times. Across those 10, how "
        "does it break down? Assign a whole number to each option (the numbers "
        "total 10):\n\n"
        f"{bullets}\n\n"
        "In one sentence, name the single biggest driver of that breakdown — "
        "something concrete about you or the product, not a generic platitude.\n\n"
        + json_contract(options)
    )


def _ctr_user_turn_v3(
    *,
    capability_name: str,
    click_label: str,
    decision_point: str,
    options: Sequence[str],
) -> str:
    """Paraphrase 2 (§3e). A third wording of the identical blinded on-screen ask.
    Reserved for K=3 ensembles; never used at the default K=1."""
    bullets = option_bullets(options, click_label)
    return (
        "## What happens when you see it\n\n"
        f"Be real about how you, specifically, move through the {capability_name}, "
        'based on your usual behavior above — set aside what a "diligent" user is '
        "supposed to do. Remember: the common case is that people do NOT tap the "
        "element in front of them; they scroll past, skip it, or leave. Hold "
        "yourself honestly to that.\n\n"
        f"Right now you are here: {decision_point}\n\n"
        "Out of 10 times you land in exactly this spot in everyday life, count how "
        "many lead to each outcome below. Give every option a whole number, and "
        "make them sum to 10:\n\n"
        f"{bullets}\n\n"
        "Then, in a single sentence, give the one reason that most shapes those "
        "counts — specific to you or to the product, never a generic answer.\n\n"
        + json_contract(options)
    )


# §3e paraphrase set. Index 0 is the canonical wording (K=1 is byte-identical to
# the single-prompt path). Every entry keeps the SAME blinding, the SAME options,
# and the SAME JSON contract, rewording ONLY the natural-language question.
_CTR_PARAPHRASES = (
    _ctr_user_turn,
    _ctr_user_turn_v2,
    _ctr_user_turn_v3,
)

CTR_PARAPHRASE_COUNT = len(_CTR_PARAPHRASES)


def _build_options(click_label: str, choice_set: Sequence[str] | None) -> list[str]:
    """Click option first, then the realistic non-click paths (shared core, with
    the CTR default choice set)."""
    return build_options(click_label, choice_set, DEFAULT_CTR_CHOICE_SET)


def elicit_ctr_decision(
    chat_client: ChatClient,
    *,
    system_prompt: str,
    capability_name: str,
    click_label: str = CTR_CLICK_LABEL,
    decision_point: str,
    choice_set: Sequence[str] | None = None,
    temperature: float = 0.0,
    seed: int | None = None,
    max_tokens: int = 1024,
) -> MetricDecision:
    """Elicit a per-agent CTR decision on a BLINDED system prompt (on-screen click).

    Single-prompt path (canonical paraphrase, index 0). For the K-paraphrase
    ensemble (§3e) see `elicit_ctr_ensemble`; this is the K=1 case. Raises
    ValueError on a degenerate allocation — surfaced by the caller as a per-agent
    CTR failure, never a silent zero.
    """
    options = _build_options(click_label, choice_set)
    user_turn = _ctr_user_turn(
        capability_name=capability_name,
        click_label=click_label,
        decision_point=decision_point,
        options=options,
    )
    return elicit_one(
        chat_client,
        system_prompt=system_prompt,
        user_turn=user_turn,
        target_label=click_label,
        options=options,
        temperature=temperature,
        seed=seed,
        max_tokens=max_tokens,
    )


@dataclass(frozen=True)
class CtrEnsembleResult:
    """Outcome of a §3e paraphrase ensemble for one CTR agent.

    A thin CTR-named view over the shared `MetricEnsembleResult` (#275):
    `mean_p_ctr` exposes the core's `mean_p_metric`.
    """

    mean_p_ctr: float
    paraphrase_unstable: bool
    decisions: tuple[MetricDecision, ...]
    k_effective: int


def elicit_ctr_ensemble(
    chat_client: ChatClient,
    *,
    system_prompt: str,
    capability_name: str,
    click_label: str = CTR_CLICK_LABEL,
    decision_point: str,
    choice_set: Sequence[str] | None = None,
    paraphrases: int = 1,
    temperature: float = 0.0,
    seed: int | None = None,
    max_tokens: int = 1024,
) -> CtrEnsembleResult:
    """Run the blinded CTR pass under K paraphrases and average p_ctr (§3e).

    Only the *question wording* varies across the K calls — the blinded
    `system_prompt` and the option set are held byte-identical. `paraphrases` is
    clamped to [1, CTR_PARAPHRASE_COUNT]; at K=1 this is byte-identical to
    `elicit_ctr_decision`. A degenerate paraphrase is dropped; only if EVERY
    paraphrase fails does this raise so the caller records a per-agent failure.
    """
    options = _build_options(click_label, choice_set)
    core = elicit_ensemble(
        chat_client,
        system_prompt=system_prompt,
        paraphrases_builders=_CTR_PARAPHRASES,
        paraphrase_count=CTR_PARAPHRASE_COUNT,
        target_label=click_label,
        options=options,
        build_user_turn_kwargs=dict(
            capability_name=capability_name,
            click_label=click_label,
            decision_point=decision_point,
            options=options,
        ),
        paraphrases=paraphrases,
        temperature=temperature,
        seed=seed,
        max_tokens=max_tokens,
    )
    return CtrEnsembleResult(
        mean_p_ctr=core.mean_p_metric,
        paraphrase_unstable=core.paraphrase_unstable,
        decisions=core.decisions,
        k_effective=core.k_effective,
    )
