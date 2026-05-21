"""LLM client — Groq primary, Anthropic fallback. Mirrors pythia-personas + pythia-crawler.

Exposes:
- `chat(messages)` — plain text completion
- `chat_json(messages, schema)` — JSON output with forgiving repair pass

The repair logic is adapted from mirofish's `_try_fix_json`
(oasis_profile_generator.py:606-670). See docs/mirofish-prior-art.md.
"""

from __future__ import annotations

import json
import os
import re
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class JSONRepairError(RuntimeError):
    """Raised when an LLM JSON response can't be coerced into the schema."""


class ChatClient(Protocol):
    def chat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> str: ...

    def chat_json(
        self,
        messages: list[dict[str, str]],
        schema: type[T],
        max_tokens: int = 4096,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> T: ...


class GroqChat:
    def __init__(self, model: str = "llama-3.3-70b-versatile") -> None:
        from openai import OpenAI

        self._client = OpenAI(
            api_key=os.environ["GROQ_API_KEY"],
            base_url="https://api.groq.com/openai/v1",
        )
        self._model = model

    def chat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> str:
        kwargs: dict = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if seed is not None:
            kwargs["seed"] = seed
        resp = self._client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    def chat_json(
        self,
        messages: list[dict[str, str]],
        schema: type[T],
        max_tokens: int = 4096,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> T:
        raw = self.chat(messages, max_tokens=max_tokens, temperature=temperature, seed=seed)
        return parse_llm_json(raw, schema)


class AnthropicChat:
    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        from anthropic import Anthropic

        self._client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self._model = model

    def chat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> str:
        # Anthropic doesn't expose seed; temperature only.
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        non_system = [m for m in messages if m["role"] != "system"]
        resp = self._client.messages.create(
            model=self._model,
            system="\n\n".join(system_parts) if system_parts else None,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": m["role"], "content": m["content"]} for m in non_system],
        )
        return resp.content[0].text

    def chat_json(
        self,
        messages: list[dict[str, str]],
        schema: type[T],
        max_tokens: int = 4096,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> T:
        raw = self.chat(messages, max_tokens=max_tokens, temperature=temperature, seed=seed)
        return parse_llm_json(raw, schema)


def get_chat_client() -> ChatClient:
    if os.environ.get("GROQ_API_KEY"):
        return GroqChat()
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicChat()
    raise RuntimeError("Set GROQ_API_KEY (preferred) or ANTHROPIC_API_KEY.")


# ---------------------------------------------------------------------------
# JSON repair — adapted from mirofish oasis_profile_generator.py:606-670
# ---------------------------------------------------------------------------

_CODE_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_TRAILING_COMMA = re.compile(r",(\s*[}\]])")


def repair_json(raw: str) -> str:
    """Best-effort cleanup of common LLM JSON failure modes.

    Handles: code fences, trailing commas, leading/trailing prose, truncation
    that left unbalanced braces.
    """
    text = _CODE_FENCE.sub("", raw).strip()

    # Drop any leading/trailing prose around the JSON body
    first_open = next((i for i, ch in enumerate(text) if ch in "{["), -1)
    if first_open > 0:
        text = text[first_open:]
    last_close = max(text.rfind("}"), text.rfind("]"))
    if 0 <= last_close < len(text) - 1:
        text = text[: last_close + 1]

    text = _TRAILING_COMMA.sub(r"\1", text)

    # Best-effort brace balance if the LLM was truncated mid-object
    opens = text.count("{") - text.count("}")
    if opens > 0:
        text = text + "}" * opens
    opens = text.count("[") - text.count("]")
    if opens > 0:
        text = text + "]" * opens

    return text


def parse_llm_json(raw: str, schema: type[T]) -> T:
    """Parse + validate, with one repair attempt before giving up."""
    try:
        return schema.model_validate_json(raw)
    except (ValidationError, json.JSONDecodeError):
        pass
    repaired = repair_json(raw)
    try:
        return schema.model_validate_json(repaired)
    except (ValidationError, json.JSONDecodeError) as exc:
        raise JSONRepairError(
            f"Could not coerce LLM output to {schema.__name__}. Raw: {raw[:500]!r}"
        ) from exc
