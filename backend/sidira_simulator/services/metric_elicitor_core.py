"""Shared core for per-metric outcome elicitation (#221 §3a/§3e; factored #275).

The conversion metric (#221) introduced a BLINDED, in-character "10-trial
allocation" elicitation with a §3e paraphrase ensemble. #275 generalizes that
machinery so sibling metrics (retention, CTR-next) reuse the IDENTICAL blinded
call, key resolution, completeness check, validation, ensemble averaging, and
instability flag — only the metric's *question paraphrases*, *target action
label*, and *default choice set* differ.

This module owns the metric-agnostic core. Each per-metric elicitor module
(`conversion_elicitor`, `retention_elicitor`) supplies its own paraphrase
builders + defaults and delegates here, so the conversion path stays
behaviorally byte-identical while retention rides the same code.

Blinding contract (§3b/§4 — "the single most important framing rule"): every
metric pass runs on the BLINDED system prompt (`prompt_composer.compose_metric_prompt`)
and is NEVER conditioned on the agent's turn-1 reaction (no prior assistant turn).
An unblinded metric pass inflates the TREATMENT arm's propensity via demand
characteristics, and that bias does NOT cancel in the treatment−control delta —
it corrupts the headline metric lift.

This module is PURE / STATELESS — it holds no module-level mutable state, so it
is safe to call concurrently across agents/metrics (the runner fans out
per-agent elicitation in threads).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from pydantic import BaseModel

from sidira_simulator.adapters.llm import ChatClient
from sidira_simulator.schemas.elicitation import MetricDecision

# A paraphrase builder: same keyword signature for every metric, returns the
# user-turn question prose for one paraphrase. The blinded system prompt and the
# option set are supplied separately and held byte-identical across paraphrases.
ParaphraseBuilder = Callable[..., str]


class _MetricAllocation(BaseModel):
    """Raw LLM output. Lenient (default extra=ignore) so a chatty model that
    adds keys doesn't fail the elicitation; the public `MetricDecision` enforces
    the real invariants."""

    action_counts: dict[str, int]
    primary_reason: str = ""
    self_reported_confidence: float | None = None


# §3e instability threshold. A run is flagged low-confidence when the agent's
# target share `p_metric` swings by MORE than this (in [0,1]) across the K
# paraphrases — i.e. wording alone moved the propensity by >20pp. Tied to
# `p_metric` itself (the only quantity downstream scoring consumes), so a
# reshuffle among NON-target options that leaves `p_metric` unchanged is
# correctly ignored (codex P2); and unlike a plurality flip it also catches a
# large `p_metric` swing that never crosses the most-likely-action line.
PARAPHRASE_INSTABILITY_P_METRIC_SPREAD = 0.2


def option_bullets(
    options: Sequence[str],
    target_label: str,
    target_tag: str = "   <- the target outcome",
) -> str:
    """Render the offered options as a bullet list, the target action tagged.

    `target_tag` is the inline marker appended to the target option's bullet. It
    is per-metric so the conversion path stays byte-identical to its historical
    "   <- the conversion" wording (#275 keeps conversion's exact prompt), while
    other metrics supply their own.

    json.dumps each label so a value containing a quote/backslash (a PM-supplied
    choice or a crawled transition trigger) renders as a valid, properly-escaped
    JSON string rather than breaking the example / bullet list. The LLM then
    returns the unescaped string as the key; `resolve_count` matches on the raw
    target_label, so display-escaping never affects matching.

    Shared verbatim by every paraphrase (§3e) so the option set the agent sees is
    byte-identical across the ensemble — only the surrounding question prose
    varies, isolating prompt-sensitivity from content variation.
    """
    bullet_lines = []
    for opt in options:
        tag = target_tag if opt == target_label else ""
        bullet_lines.append(f"  - {json.dumps(opt)}{tag}")
    return "\n".join(bullet_lines)


def json_contract(options: Sequence[str]) -> str:
    """The STRICT-JSON return instruction. Identical across all paraphrases (§3e):
    the *contract* is fixed; only the natural-language question is reworded."""
    counts_example = ", ".join(f"{json.dumps(opt)}: <int>" for opt in options)
    return (
        'Return STRICT JSON: {"action_counts": {' + counts_example + "}, "
        '"primary_reason": "<one sentence>", "self_reported_confidence": '
        "0.0..1.0} — use EXACTLY the option labels above as the keys, and make "
        "the counts add up to 10."
    )


def build_options(
    target_label: str, choice_set: Sequence[str] | None, default: Sequence[str]
) -> list[str]:
    """Target option first, then the realistic non-target paths. Dedupe while
    preserving order in case the label is also in the choice set. Built once per
    agent so the option set is byte-identical across the §3e paraphrases."""
    alternatives = list(choice_set) if choice_set else list(default)
    options: list[str] = []
    for opt in [target_label, *alternatives]:
        if opt not in options:
            options.append(opt)
    return options


def resolve_count(allocation: dict[str, int], label: str) -> dict[str, int]:
    """Normalize the LLM's keys (strip whitespace) and remap a case-insensitive
    match of the target label back to the canonical label, so a model that
    re-cased or padded the key doesn't spuriously drop the agent. Raises if the
    target action cannot be located at all (genuine degenerate response)."""
    normalized = {k.strip(): v for k, v in allocation.items()}
    if label in normalized:
        return normalized
    lowered = {k.lower(): k for k in normalized}
    hit = lowered.get(label.lower())
    if hit is None:
        raise ValueError(
            f"metric elicitation omitted the target action {label!r}; "
            f"got keys {sorted(normalized)}"
        )
    normalized[label] = normalized.pop(hit) + normalized.get(label, 0)
    return normalized


def elicit_one(
    chat_client: ChatClient,
    *,
    system_prompt: str,
    user_turn: str,
    target_label: str,
    options: Sequence[str],
    temperature: float,
    seed: int | None,
    max_tokens: int,
) -> MetricDecision:
    """One blinded chat_json call → validated `MetricDecision`.

    Shared by the single-prompt path and the ensemble (every paraphrase), so the
    chat call, key resolution, completeness check and validation are identical
    regardless of how the question was worded or which metric asked it.
    """
    raw = chat_client.chat_json(
        [
            # Blinded standalone pass: system prompt (blinded identity + standalone
            # state) + the decision ask. Deliberately NO prior assistant turn — the
            # unblinded turn-1 reaction must not condition the metric (§3b).
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_turn},
        ],
        _MetricAllocation,
        max_tokens=max_tokens,
        temperature=temperature,
        seed=seed,
    )

    counts = resolve_count(raw.action_counts, target_label)
    # Reject INCOMPLETE allocations (codex P2). The prompt asks for a count on
    # EVERY offered label; a response that omits a non-target option silently
    # shrinks the denominator and inflates p_metric. A missing offered option is
    # a degenerate response → per-agent failure, never a silent inflation.
    # Case-insensitive to mirror resolve_count's leniency; EXTRA keys a chatty
    # model invents are tolerated (they only enlarge the denominator → deflate
    # p_metric, the conservative direction).
    present = {k.lower() for k in counts}
    missing = [opt for opt in options if opt.lower() not in present]
    if missing:
        raise ValueError(
            f"metric allocation omitted offered option(s) {missing}; " f"got keys {sorted(counts)}"
        )
    return MetricDecision(
        action_counts=counts,
        target_label=target_label,
        primary_reason=raw.primary_reason.strip(),
        self_reported_confidence=raw.self_reported_confidence,
    )


@dataclass(frozen=True)
class MetricEnsembleResult:
    """Outcome of a §3e paraphrase ensemble for one agent (metric-agnostic, #275).

    `mean_p_metric` is the per-agent target propensity AVERAGED over the K
    paraphrases that succeeded — the quantity the scorer pairs into the
    treatment−control delta. `paraphrase_unstable` is True when the target share
    `p_metric` swung by more than `PARAPHRASE_INSTABILITY_P_METRIC_SPREAD` across
    the paraphrases, i.e. wording alone materially moved the propensity (§3e). It
    is keyed on `p_metric` (not the plurality action), so a reshuffle among
    non-target options that leaves `p_metric` unchanged does not flag (codex P2).
    `decisions` keeps the per-paraphrase `MetricDecision`s; `k_effective` is how
    many paraphrases produced a usable decision (≤ requested K).
    """

    mean_p_metric: float
    paraphrase_unstable: bool
    decisions: tuple[MetricDecision, ...]
    k_effective: int


def elicit_ensemble(
    chat_client: ChatClient,
    *,
    system_prompt: str,
    paraphrases_builders: Sequence[ParaphraseBuilder],
    paraphrase_count: int,
    target_label: str,
    options: Sequence[str],
    build_user_turn_kwargs: dict,
    paraphrases: int,
    temperature: float,
    seed: int | None,
    max_tokens: int,
) -> MetricEnsembleResult:
    """Run the blinded metric pass under K paraphrases and average p_metric (§3e).

    Only the *question wording* varies across the K calls — the blinded
    `system_prompt` and the option set are held byte-identical, so the ensemble
    isolates prompt-surface sensitivity, not content. `paraphrases` is clamped to
    [1, paraphrase_count]; at K=1 this is byte-identical to the single-prompt
    path (paraphrase 0 is the canonical wording), which is why the feature is
    opt-in.

    Failure posture mirrors the single-prompt path: a paraphrase that yields a
    degenerate allocation is dropped, and the mean is taken over the survivors.
    Only if EVERY paraphrase fails does this re-raise the last error so the caller
    records a per-agent metric failure — never a silent zero.
    """
    k = max(1, min(paraphrases, paraphrase_count))

    decisions: list[MetricDecision] = []
    last_exc: Exception | None = None
    for build_user_turn in paraphrases_builders[:k]:
        user_turn = build_user_turn(**build_user_turn_kwargs)
        try:
            decisions.append(
                elicit_one(
                    chat_client,
                    system_prompt=system_prompt,
                    user_turn=user_turn,
                    target_label=target_label,
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
        assert last_exc is not None
        raise last_exc

    p_metrics = [d.p_metric for d in decisions]
    mean_p_metric = sum(p_metrics) / len(p_metrics)
    paraphrase_unstable = (
        len(p_metrics) >= 2
        and (max(p_metrics) - min(p_metrics)) > PARAPHRASE_INSTABILITY_P_METRIC_SPREAD
    )
    return MetricEnsembleResult(
        mean_p_metric=mean_p_metric,
        paraphrase_unstable=paraphrase_unstable,
        decisions=tuple(decisions),
        k_effective=len(decisions),
    )
