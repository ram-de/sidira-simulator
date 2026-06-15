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

Why allocation, not "would you buy? (yes/no)" — the four documented pathologies
(acquiescence, hyper-rationality, mode collapse, uncalibrated magnitude) and the
five design responses are in `sessions/agent-behavior-spec/elicitation-conversion.md`.
The scorer never trusts the absolute level; it scores the paired treatment−control
DELTA, where the agent's per-agent inflation cancels (§3a.5 / #90).

Failure posture mirrors `reaction_elicitor`: a degenerate response (counts that
don't sum to a positive total, or no conversion-action key) raises so the caller
records a per-agent conversion failure rather than a silent p_conv.

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

import json
from collections.abc import Sequence
from dataclasses import dataclass

from pydantic import BaseModel

from sidira_simulator.adapters.llm import ChatClient
from sidira_simulator.schemas.elicitation import ConversionDecision
from sidira_simulator.schemas.simulation import DEFAULT_CONVERSION_CHOICE_SET


class _ConversionAllocation(BaseModel):
    """Raw LLM output. Lenient (default extra=ignore) so a chatty model that
    adds keys doesn't fail the elicitation; the public `ConversionDecision`
    enforces the real invariants."""

    action_counts: dict[str, int]
    primary_reason: str = ""
    self_reported_confidence: float | None = None


def _option_bullets(options: Sequence[str], conversion_action_label: str) -> str:
    """Render the offered options as a bullet list, conversion tagged.

    json.dumps each label so a value containing a quote/backslash (a PM-supplied
    choice or a crawled transition trigger) renders as a valid, properly-escaped
    JSON string rather than breaking the example / bullet list. The LLM then
    returns the unescaped string as the key; `_resolve_count` matches on the raw
    conversion_action_label, so display-escaping never affects matching.

    Shared verbatim by every paraphrase (§3e) so the option set the agent sees is
    byte-identical across the ensemble — only the surrounding question prose
    varies, isolating prompt-sensitivity from content variation.
    """
    bullet_lines = []
    for opt in options:
        tag = "   <- the conversion" if opt == conversion_action_label else ""
        bullet_lines.append(f"  - {json.dumps(opt)}{tag}")
    return "\n".join(bullet_lines)


def _json_contract(options: Sequence[str]) -> str:
    """The STRICT-JSON return instruction. Identical across all paraphrases (§3e):
    the *contract* is fixed; only the natural-language question is reworded."""
    # A valid JSON object example: one `"label": <int>` entry per option. (Not a
    # bare key list — that would render `{"a", "b": <int>}`, invalid JSON whose
    # first option has no value, raising per-agent failures on weaker adapters.)
    counts_example = ", ".join(f"{json.dumps(opt)}: <int>" for opt in options)
    return (
        'Return STRICT JSON: {"action_counts": {' + counts_example + "}, "
        '"primary_reason": "<one sentence>", "self_reported_confidence": '
        "0.0..1.0} — use EXACTLY the option labels above as the keys, and make "
        "the counts add up to 10."
    )


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
# `elicit_conversion_ensemble` caps the requested K to this, so callers (e.g. the
# runner sizing a K-scaled timeout) must cap by the SAME value rather than the raw
# env request — otherwise an oversized `SIDIRA_CONVERSION_PARAPHRASES` scales a
# budget far beyond the calls that will run.
CONVERSION_PARAPHRASE_COUNT = len(_QUESTION_PARAPHRASES)


def _resolve_count(allocation: dict[str, int], label: str) -> dict[str, int]:
    """Normalize the LLM's keys (strip whitespace) and remap a case-insensitive
    match of the conversion label back to the canonical label, so a model that
    re-cased or padded the key doesn't spuriously drop the agent. Raises if the
    conversion action cannot be located at all (genuine degenerate response)."""
    normalized = {k.strip(): v for k, v in allocation.items()}
    if label in normalized:
        return normalized
    lowered = {k.lower(): k for k in normalized}
    hit = lowered.get(label.lower())
    if hit is None:
        raise ValueError(
            f"conversion elicitation omitted the conversion action {label!r}; "
            f"got keys {sorted(normalized)}"
        )
    # Remap the matched variant key to the canonical label (combine if both
    # somehow present).
    normalized[label] = normalized.pop(hit) + normalized.get(label, 0)
    return normalized


def _build_options(conversion_action_label: str, choice_set: Sequence[str] | None) -> list[str]:
    """Conversion option first, then the realistic non-conversion paths. Dedupe
    while preserving order in case the label is also in the choice set. Built once
    per agent so the option set is byte-identical across the §3e paraphrases."""
    alternatives = list(choice_set) if choice_set else list(DEFAULT_CONVERSION_CHOICE_SET)
    options: list[str] = []
    for opt in [conversion_action_label, *alternatives]:
        if opt not in options:
            options.append(opt)
    return options


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
    """One blinded chat_json call → validated `ConversionDecision`.

    Shared by `elicit_conversion_decision` (paraphrase 0) and
    `elicit_conversion_ensemble` (every paraphrase), so the chat call, key
    resolution, completeness check and validation are identical regardless of how
    the question was worded.
    """
    raw = chat_client.chat_json(
        [
            # Blinded standalone pass: system prompt (blinded identity + standalone
            # state) + the decision ask. Deliberately NO prior assistant turn — the
            # unblinded turn-1 reaction must not condition the metric (§3b).
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_turn},
        ],
        _ConversionAllocation,
        max_tokens=max_tokens,
        temperature=temperature,
        seed=seed,
    )

    counts = _resolve_count(raw.action_counts, conversion_action_label)
    # Reject INCOMPLETE allocations (codex P2). The prompt asks for a count on
    # EVERY offered label; a response that omits a non-conversion option silently
    # shrinks the denominator and inflates p_conv (e.g. `{"check out now": 6}`
    # alone → p_conv 1.0 instead of a malformed allocation). A missing offered
    # option is a degenerate response → per-agent failure, never a silent
    # inflation. Case-insensitive to mirror `_resolve_count`'s leniency; EXTRA
    # keys a chatty model invents are still tolerated (they only enlarge the
    # denominator → deflate p_conv, the conservative direction).
    present = {k.lower() for k in counts}
    missing = [opt for opt in options if opt.lower() not in present]
    if missing:
        raise ValueError(
            f"conversion allocation omitted offered option(s) {missing}; "
            f"got keys {sorted(counts)}"
        )
    # ConversionDecision validates non-negativity, label presence, positive
    # total; raises (→ per-agent failure) otherwise.
    return ConversionDecision(
        action_counts=counts,
        conversion_action_label=conversion_action_label,
        primary_reason=raw.primary_reason.strip(),
        self_reported_confidence=raw.self_reported_confidence,
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
    Conditioning on the unblinded reaction would re-introduce the change framing
    the blinding exists to remove and inflate the treatment arm.

    Single-prompt path (the canonical paraphrase, index 0). For the K-paraphrase
    ensemble (§3e) see `elicit_conversion_ensemble`; this function is the K=1 case.

    Raises ValueError on a degenerate allocation (no positive total, or the
    conversion action absent) — surfaced by the caller as a per-agent
    conversion failure, never a silent zero.
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
    """Outcome of a §3e paraphrase ensemble for one agent.

    `mean_p_conv` is the per-agent conversion propensity AVERAGED over the K
    paraphrases that succeeded — the quantity the scorer pairs into the
    treatment−control delta. `paraphrase_unstable` is True when the conversion
    share `p_conv` swung by more than `PARAPHRASE_INSTABILITY_P_CONV_SPREAD` across
    the paraphrases, i.e. wording alone materially moved the conversion propensity
    (§3e); that taints the pair's delta as low-confidence downstream. It is keyed
    on `p_conv` (not the plurality action), so a reshuffle among non-conversion
    options that leaves `p_conv` unchanged does not flag (codex P2). `decisions`
    keeps the per-paraphrase `ConversionDecision`s (for provenance / tests);
    `k_effective` is how many paraphrases produced a usable decision (≤ requested K).
    """

    mean_p_conv: float
    paraphrase_unstable: bool
    decisions: tuple[ConversionDecision, ...]
    k_effective: int


# §3e instability threshold. A run is flagged low-confidence when the agent's
# conversion share `p_conv` swings by MORE than this (in [0,1]) across the K
# paraphrases — i.e. wording alone moved the conversion propensity by >20pp. Tied
# to `p_conv` itself (the only quantity downstream scoring consumes), so a reshuffle
# among NON-conversion options that leaves `p_conv` unchanged is correctly ignored
# (codex P2); and unlike a plurality flip it also catches a large `p_conv` swing
# that never crosses the most-likely-action line.
PARAPHRASE_INSTABILITY_P_CONV_SPREAD = 0.2


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
    byte-identical, so the ensemble isolates prompt-surface sensitivity, not
    content. `paraphrases` is clamped to [1, len(_QUESTION_PARAPHRASES)]; at K=1
    this is byte-identical to `elicit_conversion_decision` (paraphrase 0 is the
    canonical wording), which is why the feature is opt-in.

    Failure posture mirrors the single-prompt path: a paraphrase that yields a
    degenerate allocation is dropped, and the mean is taken over the survivors.
    Only if EVERY paraphrase fails does this raise (re-raising the last error) so
    the caller records a per-agent conversion failure — never a silent zero. At
    K=1 that is exactly the historical raise-on-failure behavior.
    """
    options = _build_options(conversion_action_label, choice_set)
    k = max(1, min(paraphrases, CONVERSION_PARAPHRASE_COUNT))

    decisions: list[ConversionDecision] = []
    last_exc: Exception | None = None
    for build_user_turn in _QUESTION_PARAPHRASES[:k]:
        user_turn = build_user_turn(
            capability_name=capability_name,
            conversion_action=conversion_action,
            conversion_action_label=conversion_action_label,
            decision_point=decision_point,
            options=options,
        )
        try:
            decisions.append(
                _elicit_one(
                    chat_client,
                    system_prompt=system_prompt,
                    user_turn=user_turn,
                    conversion_action_label=conversion_action_label,
                    options=options,
                    temperature=temperature,
                    seed=seed,
                    max_tokens=max_tokens,
                )
            )
        except Exception as exc:  # noqa: BLE001 — drop this paraphrase, keep the rest
            last_exc = exc
            continue

    if not decisions:
        # Every paraphrase produced a degenerate allocation → per-agent conversion
        # failure, identical to the single-prompt path raising.
        assert last_exc is not None
        raise last_exc

    p_convs = [d.p_conv for d in decisions]
    mean_p_conv = sum(p_convs) / len(p_convs)
    # Instability-under-paraphrase (§3e): unstable iff ≥2 paraphrases ran and the
    # conversion share `p_conv` swung by more than the threshold across them.
    # Measured on `p_conv` (the only quantity scoring consumes), so a non-conversion
    # reshuffle that leaves `p_conv` flat is not flagged (codex P2).
    paraphrase_unstable = (
        len(p_convs) >= 2 and (max(p_convs) - min(p_convs)) > PARAPHRASE_INSTABILITY_P_CONV_SPREAD
    )
    return ConversionEnsembleResult(
        mean_p_conv=mean_p_conv,
        paraphrase_unstable=paraphrase_unstable,
        decisions=tuple(decisions),
        k_effective=len(decisions),
    )
