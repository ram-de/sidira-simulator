"""Per-metric outcome elicitation — the VISIT question (#222 Hillstrom / §3a).

The VISIT sibling of `ctr_elicitor`, riding the SAME blinded core
(`services.metric_elicitor_core`): a BLINDED, in-character verbalized allocation
elicited on the standalone-state metric prompt
(`prompt_composer.compose_metric_prompt`), NEVER conditioned on the agent's
turn-1 reaction. The blinding rule is identical to CTR/conversion (§3b/§4) — an
unblinded metric pass inflates the TREATMENT arm and the bias does not cancel in
the treatment−control delta.

VISIT is the site-visit sibling of CTR: a binary "did you come to the site" event
in a SHORT WINDOW AFTER the touchpoint (the Hillstrom RCT measures whether a
customer visited the website in the two weeks after the email). So:

  - the `decision_point` describes the touchpoint moment (e.g. "you just got an
    email from a store you've shopped at"), with the visit framed as the
    next-couple-weeks follow-through — a near-future event, between CTR's
    on-screen immediacy and retention's recurring return;
  - the BLINDED `standalone_state_view` renders the proposed touchpoint as a
    standalone screen the agent encounters with NO change framing — as CTR;
  - the agent allocates 10 trials across the VISIT choice set
    `{"go to the site", "ignore it", "unsubscribe / mark spam", "do nothing"}`,
    where the FIRST option is the visit event (`VISIT_LABEL`);
  - `p_metric = counts["go to the site"] / total` is the site-visit propensity.

Native unit: site-visit-rate lift in percentage points. Reuses the §3e
paraphrase ensemble, the #90 paired-delta, the #269 shrinkage/calibration seam,
and the §3b unblindable-fallback flag verbatim.

This module is PURE / STATELESS (the shared core holds no mutable state), so it
is safe to call concurrently across agents.
"""

from __future__ import annotations

import json
import re
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

# The VISIT choice set. The FIRST option is the visit event — `VISIT_LABEL` —
# counted as the metric target; the rest are the realistic non-visit paths a real
# user actually takes after a touchpoint. Used as the default when the Hypothesis
# supplies no grounded choice_set. The PM may override the visit label via the
# generic label field (`conversion_action_label`); the default applies when absent.
VISIT_LABEL = "go to the site"
DEFAULT_VISIT_CHOICE_SET: tuple[str, ...] = (
    "ignore it",
    "unsubscribe or mark it spam",
    "do nothing",
)


def _visit_user_turn(
    *,
    capability_name: str,
    visit_label: str,
    decision_point: str,
    options: Sequence[str],
) -> str:
    """Paraphrase 0 — the CANONICAL VISIT decision question (near-future follow-up).

    Frames the visit as the next-couple-weeks follow-through after the touchpoint.
    Stays blinded — no "the change", no "you just saw", nothing that presumes a
    prior reaction or signals an intervention is under test (§3b)."""
    bullets = option_bullets(options, visit_label)
    return (
        "## Whether you go look\n\n"
        f"Think about how you actually deal with the {capability_name} — not how "
        'an "engaged" customer is supposed to behave, but what YOU really do, '
        "given your behavioral snapshot above. Be honest: most of the time, most "
        "people do NOT go out of their way to visit a site after a nudge — they "
        "ignore it, let it sit, or move on. Hold yourself to that bar.\n\n"
        f"The situation: {decision_point}\n\n"
        "Picture this exact moment happening 10 separate times in your normal "
        "life. Across those 10 times, in the next couple of weeks, what do you "
        "actually do? Put a whole number on each (they add up to 10):\n\n"
        f"{bullets}\n\n"
        "Then give, in one sentence, the single biggest reason your split looks "
        "the way it does — tied to something specific about you or the product, "
        "not a generic reason.\n\n" + json_contract(options)
    )


def _visit_user_turn_v2(
    *,
    capability_name: str,
    visit_label: str,
    decision_point: str,
    options: Sequence[str],
) -> str:
    """Paraphrase 1 (§3e). Same blinded near-future ask, same options, same JSON
    contract — only the question prose is reworded."""
    bullets = option_bullets(options, visit_label)
    return (
        "## Do you end up visiting\n\n"
        f"Picture yourself actually dealing with the {capability_name}, behaving "
        "the way you normally behave (see your snapshot above) — not the way some "
        'idealized, "attentive" customer would. The honest truth is that most '
        "nudges do NOT pull people back to a site; they get ignored, deleted, or "
        "forgotten. Judge yourself by that reality.\n\n"
        f"The situation: {decision_point}\n\n"
        "Imagine hitting this exact moment 10 separate times. Across those 10, in "
        "the following couple of weeks, how does it break down? Assign a whole "
        "number to each option (the numbers total 10):\n\n"
        f"{bullets}\n\n"
        "In one sentence, name the single biggest driver of that breakdown — "
        "something concrete about you or the product, not a generic platitude.\n\n"
        + json_contract(options)
    )


def _visit_user_turn_v3(
    *,
    capability_name: str,
    visit_label: str,
    decision_point: str,
    options: Sequence[str],
) -> str:
    """Paraphrase 2 (§3e). A third wording of the identical blinded near-future
    ask. Reserved for K=3 ensembles; never used at the default K=1."""
    bullets = option_bullets(options, visit_label)
    return (
        "## What you do afterwards\n\n"
        f"Be real about how you, specifically, deal with the {capability_name}, "
        'based on your usual behavior above — set aside what a "diligent" customer '
        "is supposed to do. Remember: the common case is that people do NOT go "
        "visit a site after a prompt; they ignore it, delete it, or do nothing. "
        "Hold yourself honestly to that.\n\n"
        f"Right now you are here: {decision_point}\n\n"
        "Out of 10 times you land in exactly this spot in everyday life, count how "
        "many lead to each outcome below over the next couple of weeks. Give every "
        "option a whole number, and make them sum to 10:\n\n"
        f"{bullets}\n\n"
        "Then, in a single sentence, give the one reason that most shapes those "
        "counts — specific to you or to the product, never a generic answer.\n\n"
        + json_contract(options)
    )


# §3e paraphrase set. Index 0 is the canonical wording (K=1 is byte-identical to
# the single-prompt path). Every entry keeps the SAME blinding, the SAME options,
# and the SAME JSON contract, rewording ONLY the natural-language question.
_VISIT_PARAPHRASES = (
    _visit_user_turn,
    _visit_user_turn_v2,
    _visit_user_turn_v3,
)

VISIT_PARAPHRASE_COUNT = len(_VISIT_PARAPHRASES)


def _build_options(visit_label: str, choice_set: Sequence[str] | None) -> list[str]:
    """Visit option first, then the realistic non-visit paths (shared core, with
    the VISIT default choice set)."""
    return build_options(visit_label, choice_set, DEFAULT_VISIT_CHOICE_SET)


def elicit_visit_decision(
    chat_client: ChatClient,
    *,
    system_prompt: str,
    capability_name: str,
    visit_label: str = VISIT_LABEL,
    decision_point: str,
    choice_set: Sequence[str] | None = None,
    temperature: float = 0.0,
    seed: int | None = None,
    max_tokens: int = 1024,
) -> MetricDecision:
    """Elicit a per-agent VISIT decision on a BLINDED system prompt (site visit).

    Single-prompt path (canonical paraphrase, index 0). For the K-paraphrase
    ensemble (§3e) see `elicit_visit_ensemble`; this is the K=1 case. Raises
    ValueError on a degenerate allocation — surfaced by the caller as a per-agent
    VISIT failure, never a silent zero.
    """
    options = _build_options(visit_label, choice_set)
    user_turn = _visit_user_turn(
        capability_name=capability_name,
        visit_label=visit_label,
        decision_point=decision_point,
        options=options,
    )
    return elicit_one(
        chat_client,
        system_prompt=system_prompt,
        user_turn=user_turn,
        target_label=visit_label,
        options=options,
        temperature=temperature,
        seed=seed,
        max_tokens=max_tokens,
    )


_DELTA_OBJ = re.compile(r"\{[^{}]*\}")


def elicit_visit_delta(
    chat_client: ChatClient,
    *,
    system_prompt: str,
    capability_name: str,
    decision_point: str,
    temperature: float = 0.0,
    seed: int | None = None,
    max_tokens: int = 512,
) -> float:
    """#342 comparative-delta forecaster pass: ONE call on a comparative system
    prompt (both versions shown) asking for the directional visit-rate difference
    directly, instead of two independent absolute passes subtracted. Returns the
    signed lift as a fraction (delta_per_100 / 100), e.g. +0.07 = 7 more visits per
    100. Raises ValueError if no parseable delta after retries (caller drops it).
    """
    user_turn = (
        f"For this audience, consider 100 people who {decision_point}. Forecast how "
        f"many MORE (positive) or FEWER (negative) of them would {VISIT_LABEL} under "
        "Version B (the proposed change) than under Version A (current) — base it on "
        "how real audiences respond to this kind of change, not on your own reaction. "
        'Respond with ONLY one JSON object: {"delta_per_100": <signed integer between '
        '-100 and 100>, "reason": "<one sentence>"}'
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_turn},
    ]
    for attempt in range(3):
        raw = chat_client.chat(
            messages, max_tokens=max_tokens,
            temperature=0.0 if attempt else temperature, seed=seed,
        )
        for cand in reversed(_DELTA_OBJ.findall(raw)):
            try:
                obj = json.loads(cand)
            except Exception:
                continue
            if isinstance(obj, dict) and "delta_per_100" in obj:
                try:
                    d = float(obj["delta_per_100"])
                except (TypeError, ValueError):
                    continue
                return max(-100.0, min(100.0, d)) / 100.0
        m = re.search(r'delta_per_100"?\s*[:=]\s*(-?\d+(?:\.\d+)?)', raw)
        if m:
            return max(-100.0, min(100.0, float(m.group(1)))) / 100.0
    raise ValueError("comparative visit-delta elicitation produced no parseable delta")


@dataclass(frozen=True)
class VisitEnsembleResult:
    """Outcome of a §3e paraphrase ensemble for one VISIT agent.

    A thin VISIT-named view over the shared `MetricEnsembleResult` (#275):
    `mean_p_visit` exposes the core's `mean_p_metric`.
    """

    mean_p_visit: float
    paraphrase_unstable: bool
    decisions: tuple[MetricDecision, ...]
    k_effective: int


def elicit_visit_ensemble(
    chat_client: ChatClient,
    *,
    system_prompt: str,
    capability_name: str,
    visit_label: str = VISIT_LABEL,
    decision_point: str,
    choice_set: Sequence[str] | None = None,
    paraphrases: int = 1,
    temperature: float = 0.0,
    seed: int | None = None,
    max_tokens: int = 1024,
) -> VisitEnsembleResult:
    """Run the blinded VISIT pass under K paraphrases and average p_visit (§3e).

    Only the *question wording* varies across the K calls — the blinded
    `system_prompt` and the option set are held byte-identical. `paraphrases` is
    clamped to [1, VISIT_PARAPHRASE_COUNT]; at K=1 this is byte-identical to
    `elicit_visit_decision`. A degenerate paraphrase is dropped; only if EVERY
    paraphrase fails does this raise so the caller records a per-agent failure.
    """
    options = _build_options(visit_label, choice_set)
    core = elicit_ensemble(
        chat_client,
        system_prompt=system_prompt,
        paraphrases_builders=_VISIT_PARAPHRASES,
        paraphrase_count=VISIT_PARAPHRASE_COUNT,
        target_label=visit_label,
        options=options,
        build_user_turn_kwargs=dict(
            capability_name=capability_name,
            visit_label=visit_label,
            decision_point=decision_point,
            options=options,
        ),
        paraphrases=paraphrases,
        temperature=temperature,
        seed=seed,
        max_tokens=max_tokens,
    )
    return VisitEnsembleResult(
        mean_p_visit=core.mean_p_metric,
        paraphrase_unstable=core.paraphrase_unstable,
        decisions=core.decisions,
        k_effective=core.k_effective,
    )
