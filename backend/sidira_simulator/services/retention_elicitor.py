"""Per-metric outcome elicitation — the retention question (#275 / §3a, Decision B).

The retention sibling of `conversion_elicitor`, riding the SAME blinded core
(`services.metric_elicitor_core`): a BLINDED, in-character verbalized allocation
elicited on the standalone-state metric prompt (`prompt_composer.compose_metric_prompt`),
NEVER conditioned on the agent's turn-1 reaction. The blinding rule is identical
to conversion (§3b/§4) — an unblinded metric pass inflates the TREATMENT arm and
the bias does not cancel in the treatment−control delta.

Decision B — retention's TEMPORAL framing (vs conversion's on-screen action):
retention is a future-return event, not an action on the current screen. So:

  - the `decision_point` describes the post-experience moment — the default
    in-product phrasing is "you've just finished tonight's session" (the PM may
    override per-product);
  - the BLINDED `standalone_state_view` renders the steady-state product a
    RETURNING user re-encounters (control = current steady state; treatment =
    proposed steady state's standalone view) — the agent never sees change
    framing, exactly as conversion;
  - the agent allocates 10 trials across the retention choice set
    `{"return next week", "return but less often", "stop using it",
    "switch to an alternative"}`, where the FIRST option is the retention
    ("return") event;
  - `p_metric = counts["return next week"] / total` is the retention propensity.

Native unit: retention-rate lift in percentage points. Reuses the §3e paraphrase
ensemble, the #90 paired-delta, and the §3b unblindable-fallback flag verbatim.

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

# Decision B: the retention choice set. The FIRST option is the retention
# ("return") event — `RETENTION_RETURN_LABEL` — counted as the metric target;
# the rest are the realistic non-return alternatives. Used as the default when
# the Hypothesis supplies no grounded choice_set.
RETENTION_RETURN_LABEL = "return next week"
DEFAULT_RETENTION_CHOICE_SET: tuple[str, ...] = (
    "return but less often",
    "stop using it",
    "switch to an alternative",
)

# Decision B: the default post-experience moment. Retention is temporal (a future
# return), so the decision point names the moment AFTER the experience, not an
# on-screen action. The PM may override via Hypothesis.decision_point; this is the
# in-product default the runner passes when none is set is NOT done here — the
# Hypothesis.decision_point is required by the registry validator — but this
# constant documents the canonical Decision-B phrasing the spec ships.
DEFAULT_RETENTION_DECISION_POINT = "you've just finished tonight's session"


def _retention_user_turn(
    *,
    capability_name: str,
    decision_point: str,
    return_label: str,
    options: Sequence[str],
) -> str:
    """Paraphrase 0 — the CANONICAL retention decision question (Decision B).

    Temporal framing: the agent has just FINISHED using the product and is asked
    how often, across 10 such evenings, they come BACK. Stays blinded — no "the
    change", no "you just saw", nothing that presumes a prior reaction or signals
    an intervention is under test (§3b)."""
    bullets = option_bullets(options, return_label)
    return (
        "## What you do after\n\n"
        f"Think about how you actually use the {capability_name} over time — not "
        'how a "committed" user is supposed to behave, but what YOU really do, '
        "given your behavioral snapshot above. Be honest: most people do NOT keep "
        "coming back to most things; they drift off, get busy, or move on to "
        "something else. Hold yourself to that bar.\n\n"
        f"You're at this moment: {decision_point}\n\n"
        "Picture this exact moment happening 10 separate times in your normal "
        "life. Across those 10 times, how do the next few days play out for you? "
        "Put a whole number on each (they add up to 10):\n\n"
        f"{bullets}\n\n"
        "Then give, in one sentence, the single biggest reason your split looks "
        "the way it does — tied to something specific about you or the product, "
        "not a generic reason.\n\n" + json_contract(options)
    )


def _retention_user_turn_v2(
    *,
    capability_name: str,
    decision_point: str,
    return_label: str,
    options: Sequence[str],
) -> str:
    """Paraphrase 1 (§3e). Same blinded temporal ask, same options, same JSON
    contract — only the question prose is reworded."""
    bullets = option_bullets(options, return_label)
    return (
        "## Whether you come back\n\n"
        f"Picture your real relationship with the {capability_name} over the "
        "coming days, behaving the way you normally behave (see your snapshot "
        'above) — not the way an idealized, "loyal" user would. The honest truth '
        "is that most people do NOT keep returning; they lose the habit, get "
        "distracted, or switch to something else. Judge yourself by that "
        "reality.\n\n"
        f"The situation: {decision_point}\n\n"
        "Imagine reaching this exact moment 10 separate times. Across those 10, "
        "how does the next stretch break down for you? Assign a whole number to "
        "each option (the numbers total 10):\n\n"
        f"{bullets}\n\n"
        "In one sentence, name the single biggest driver of that breakdown — "
        "something concrete about you or the product, not a generic platitude.\n\n"
        + json_contract(options)
    )


def _retention_user_turn_v3(
    *,
    capability_name: str,
    decision_point: str,
    return_label: str,
    options: Sequence[str],
) -> str:
    """Paraphrase 2 (§3e). A third wording of the identical blinded temporal ask.
    Reserved for K=3 ensembles; never used at the default K=1."""
    bullets = option_bullets(options, return_label)
    return (
        "## What the next few days look like\n\n"
        f"Be real about how you, specifically, keep using (or stop using) the "
        f"{capability_name} over time, based on your usual behavior above — set "
        'aside what a "dedicated" user is supposed to do. Remember: the common '
        "case is that people do NOT stick around; they drift, forget, or move on "
        "to an alternative. Hold yourself honestly to that.\n\n"
        f"Right now you are here: {decision_point}\n\n"
        "Out of 10 times you land in exactly this spot in everyday life, count how "
        "many lead to each outcome below over the following days. Give every "
        "option a whole number, and make them sum to 10:\n\n"
        f"{bullets}\n\n"
        "Then, in a single sentence, give the one reason that most shapes those "
        "counts — specific to you or to the product, never a generic answer.\n\n"
        + json_contract(options)
    )


# §3e paraphrase set. Index 0 is the canonical wording (K=1 is byte-identical to
# the single-prompt path). Every entry keeps the SAME blinding, the SAME options,
# and the SAME JSON contract, rewording ONLY the natural-language question.
_RETENTION_PARAPHRASES = (
    _retention_user_turn,
    _retention_user_turn_v2,
    _retention_user_turn_v3,
)

RETENTION_PARAPHRASE_COUNT = len(_RETENTION_PARAPHRASES)


def _build_options(return_label: str, choice_set: Sequence[str] | None) -> list[str]:
    """Return option first, then the realistic non-return paths (shared core, with
    the retention default choice set)."""
    return build_options(return_label, choice_set, DEFAULT_RETENTION_CHOICE_SET)


def elicit_retention_decision(
    chat_client: ChatClient,
    *,
    system_prompt: str,
    capability_name: str,
    return_label: str = RETENTION_RETURN_LABEL,
    decision_point: str,
    choice_set: Sequence[str] | None = None,
    temperature: float = 0.0,
    seed: int | None = None,
    max_tokens: int = 1024,
) -> MetricDecision:
    """Elicit a per-agent retention decision on a BLINDED system prompt (Decision B).

    Single-prompt path (canonical paraphrase, index 0). For the K-paraphrase
    ensemble (§3e) see `elicit_retention_ensemble`; this is the K=1 case. Raises
    ValueError on a degenerate allocation — surfaced by the caller as a per-agent
    retention failure, never a silent zero.
    """
    options = _build_options(return_label, choice_set)
    user_turn = _retention_user_turn(
        capability_name=capability_name,
        decision_point=decision_point,
        return_label=return_label,
        options=options,
    )
    return elicit_one(
        chat_client,
        system_prompt=system_prompt,
        user_turn=user_turn,
        target_label=return_label,
        options=options,
        temperature=temperature,
        seed=seed,
        max_tokens=max_tokens,
    )


@dataclass(frozen=True)
class RetentionEnsembleResult:
    """Outcome of a §3e paraphrase ensemble for one retention agent.

    A thin retention-named view over the shared `MetricEnsembleResult` (#275):
    `mean_p_retention` exposes the core's `mean_p_metric`.
    """

    mean_p_retention: float
    paraphrase_unstable: bool
    decisions: tuple[MetricDecision, ...]
    k_effective: int


def elicit_retention_ensemble(
    chat_client: ChatClient,
    *,
    system_prompt: str,
    capability_name: str,
    return_label: str = RETENTION_RETURN_LABEL,
    decision_point: str,
    choice_set: Sequence[str] | None = None,
    paraphrases: int = 1,
    temperature: float = 0.0,
    seed: int | None = None,
    max_tokens: int = 1024,
) -> RetentionEnsembleResult:
    """Run the blinded retention pass under K paraphrases and average p_retention (§3e).

    Only the *question wording* varies across the K calls — the blinded
    `system_prompt` and the option set are held byte-identical. `paraphrases` is
    clamped to [1, RETENTION_PARAPHRASE_COUNT]; at K=1 this is byte-identical to
    `elicit_retention_decision`. A degenerate paraphrase is dropped; only if EVERY
    paraphrase fails does this raise so the caller records a per-agent failure.
    """
    options = _build_options(return_label, choice_set)
    core = elicit_ensemble(
        chat_client,
        system_prompt=system_prompt,
        paraphrases_builders=_RETENTION_PARAPHRASES,
        paraphrase_count=RETENTION_PARAPHRASE_COUNT,
        target_label=return_label,
        options=options,
        build_user_turn_kwargs=dict(
            capability_name=capability_name,
            decision_point=decision_point,
            return_label=return_label,
            options=options,
        ),
        paraphrases=paraphrases,
        temperature=temperature,
        seed=seed,
        max_tokens=max_tokens,
    )
    return RetentionEnsembleResult(
        mean_p_retention=core.mean_p_metric,
        paraphrase_unstable=core.paraphrase_unstable,
        decisions=core.decisions,
        k_effective=core.k_effective,
    )
