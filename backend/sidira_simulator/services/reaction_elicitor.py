"""Reaction elicitation (agent-behavior-spec Item B / ticket #221).

Elicits a per-agent reaction *distribution* instead of a single point reaction,
fixing the documented mode-collapse recipe (`temperature=0` + one sample/agent).

Two regimes, both default-safe:

- ``samples == 1`` (default): a single plain ``chat()`` call at the configured
  temperature. At the default ``temperature=0.0`` this is byte-identical to the
  historical single-reaction path — same call, same arguments — so turning the
  feature "off" reproduces prior behavior exactly. The result is a one-sample
  distribution with probability 1.0.

- ``samples > 1``: ONE raised-temperature ``chat_json()`` call using *verbalized
  sampling* — the agent enumerates k distinct plausible reactions it might have,
  each with a self-assessed probability. Capturing within-agent variance in a
  single call is cheaper than k independent calls AND is not subject to the
  ``temperature=0`` mode-collapse that k point samples would still suffer.

The caller persists `distribution.modal.text` as the canonical frozen reaction
(identity-continuity contract) and the full distribution as a separate artifact;
the scorer consumes the modal sample today, so the default path is unchanged.
"""

from __future__ import annotations

from pydantic import BaseModel

from sidira_simulator.adapters.llm import ChatClient
from sidira_simulator.schemas.elicitation import ReactionDistribution, ReactionSample


class _VerbalizedSample(BaseModel):
    """One LLM-emitted candidate reaction. Lenient (default extra=ignore) so a
    chatty model that adds keys doesn't fail the whole elicitation."""

    reaction: str
    probability: float


class _VerbalizedSampling(BaseModel):
    reactions: list[_VerbalizedSample]


def _verbalized_sampling_user_turn(base_user_turn: str, samples: int) -> str:
    """Append the verbalized-sampling instruction to the base reaction prompt.

    Keeps the base task framing (which already diverges by arm in the runner)
    intact and only adds the "give k weighted reactions" wrapper, so treatment /
    control framing is untouched by the distribution layer.
    """
    return (
        f"{base_user_turn}\n\n"
        "You are not perfectly certain how you'd react — your mood, attention, and "
        f"recent experience vary from moment to moment. Give {samples} DISTINCT "
        "plausible reactions you might genuinely have, spanning that range (not "
        f"{samples} rephrasings of a single take). For each, estimate the probability "
        "that it is the reaction you'd actually have; the probabilities should reflect "
        "relative likelihood.\n\n"
        'Return STRICT JSON: {"reactions": [{"reaction": "<first-person prose>", '
        '"probability": 0.0..1.0}, ...]} '
        f"with exactly {samples} entries."
    )


def elicit_reaction_distribution(
    chat_client: ChatClient,
    *,
    system_prompt: str,
    user_turn: str,
    samples: int,
    temperature: float,
    seed: int | None = None,
    max_tokens: int = 4096,
) -> ReactionDistribution:
    """Elicit a within-agent reaction distribution.

    Raises ValueError if `samples < 1`, or if a verbalized-sampling call returns
    no usable reaction (all blank or non-positive probability) — a degenerate
    response that must surface as a per-agent failure rather than a silently
    empty distribution.
    """
    if samples < 1:
        raise ValueError(f"samples must be >= 1, got {samples}")

    messages = [
        {"role": "system", "content": system_prompt},
    ]

    if samples == 1:
        # Default/off path: one plain reaction. Explicit max_tokens/temperature/
        # seed match the adapter defaults at temperature=0.0, so this is the exact
        # historical call.
        text = chat_client.chat(
            [*messages, {"role": "user", "content": user_turn}],
            max_tokens=max_tokens,
            temperature=temperature,
            seed=seed,
        )
        return ReactionDistribution(
            samples=[ReactionSample(text=text, probability=1.0)],
            temperature=temperature,
        )

    raw = chat_client.chat_json(
        [
            *messages,
            {"role": "user", "content": _verbalized_sampling_user_turn(user_turn, samples)},
        ],
        _VerbalizedSampling,
        max_tokens=max_tokens,
        temperature=temperature,
        seed=seed,
    )

    valid = [
        ReactionSample(text=s.reaction.strip(), probability=s.probability)
        for s in raw.reactions
        if s.reaction.strip() and s.probability > 0
    ]
    if not valid:
        raise ValueError("verbalized sampling returned no usable reactions")

    return ReactionDistribution(samples=valid, temperature=temperature)
