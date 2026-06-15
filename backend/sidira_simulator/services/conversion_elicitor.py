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
"""

from __future__ import annotations

import json
from collections.abc import Sequence

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


def _conversion_user_turn(
    *,
    capability_name: str,
    conversion_action: str,
    conversion_action_label: str,
    decision_point: str,
    options: Sequence[str],
) -> str:
    """Build the §3a decision question. The blinded identity + standalone state
    live in the system prompt; this adds ONLY the decision ask. It must stay
    blinded too — no "the change", no "you just saw", nothing that presumes a
    prior reaction or signals an intervention is under test (§3b)."""
    # json.dumps each label so a value containing a quote/backslash (a PM-supplied
    # choice or a crawled transition trigger) renders as a valid, properly-escaped
    # JSON string rather than breaking the example / bullet list. The LLM then
    # returns the unescaped string as the key; `_resolve_count` matches on the raw
    # conversion_action_label, so display-escaping never affects matching.
    bullet_lines = []
    for opt in options:
        tag = "   <- the conversion" if opt == conversion_action_label else ""
        bullet_lines.append(f"  - {json.dumps(opt)}{tag}")
    bullets = "\n".join(bullet_lines)
    # A valid JSON object example: one `"label": <int>` entry per option. (Not a
    # bare key list — that would render `{"a", "b": <int>}`, invalid JSON whose
    # first option has no value, raising per-agent failures on weaker adapters.)
    counts_example = ", ".join(f"{json.dumps(opt)}: <int>" for opt in options)
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
        "not a generic reason.\n\n"
        'Return STRICT JSON: {"action_counts": {' + counts_example + "}, "
        '"primary_reason": "<one sentence>", "self_reported_confidence": '
        "0.0..1.0} — use EXACTLY the option labels above as the keys, and make "
        "the counts add up to 10."
    )


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

    Raises ValueError on a degenerate allocation (no positive total, or the
    conversion action absent) — surfaced by the caller as a per-agent
    conversion failure, never a silent zero.
    """
    alternatives = list(choice_set) if choice_set else list(DEFAULT_CONVERSION_CHOICE_SET)
    # Conversion option first, then the realistic non-conversion paths. Dedupe
    # while preserving order in case the label is also in the choice set.
    options: list[str] = []
    for opt in [conversion_action_label, *alternatives]:
        if opt not in options:
            options.append(opt)

    user_turn = _conversion_user_turn(
        capability_name=capability_name,
        conversion_action=conversion_action,
        conversion_action_label=conversion_action_label,
        decision_point=decision_point,
        options=options,
    )

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
