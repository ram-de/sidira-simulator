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
import random
import re
import time
from dataclasses import dataclass
from typing import Callable, Literal, Protocol, TypeVar

import structlog
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

log = structlog.get_logger()

Provider = Literal["groq", "anthropic", "openai"]
DEFAULT_MODEL_ID = "llama-3.3-70b-versatile"


@dataclass(frozen=True)
class ModelSpec:
    id: str
    provider: Provider
    label: str
    description: str
    speed_label: str
    cost_label: str


MODEL_SPECS: tuple[ModelSpec, ...] = (
    ModelSpec(
        id=DEFAULT_MODEL_ID,
        provider="groq",
        label="Llama 3.3 70B",
        description="Default model; fast enough for broad simulation runs.",
        speed_label="fast",
        cost_label="default",
    ),
    ModelSpec(
        id="llama-3.1-8b-instant",
        provider="groq",
        label="Llama 3.1 8B Instant",
        description="Lowest-cost Groq option for quick rough cuts.",
        speed_label="fastest",
        cost_label="low",
    ),
    ModelSpec(
        id="claude-opus-4-7",
        provider="anthropic",
        label="Claude Opus 4.7",
        description="Highest-reasoning Claude option for subtle hypotheses.",
        speed_label="moderate",
        cost_label="high",
    ),
    ModelSpec(
        id="claude-sonnet-4-6",
        provider="anthropic",
        label="Claude Sonnet 4.6",
        description="Balanced Claude option for quality and speed.",
        speed_label="fast",
        cost_label="medium",
    ),
    ModelSpec(
        id="claude-haiku-4-5",
        provider="anthropic",
        label="Claude Haiku 4.5",
        description="Fast Claude option for lower-cost iteration.",
        speed_label="fastest",
        cost_label="low",
    ),
    ModelSpec(
        id="gpt-5.5",
        provider="openai",
        label="GPT-5.5",
        description="OpenAI frontier option for strongest reasoning.",
        speed_label="moderate",
        cost_label="high",
    ),
    ModelSpec(
        id="gpt-5.4-mini",
        provider="openai",
        label="GPT-5.4 Mini",
        description="Lower-latency OpenAI option for iteration.",
        speed_label="fast",
        cost_label="medium",
    ),
)

_MODEL_BY_ID = {m.id: m for m in MODEL_SPECS}
_PROVIDER_ENV = {
    "groq": "GROQ_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}
_DEFAULT_PRIORITY = (
    DEFAULT_MODEL_ID,
    "claude-sonnet-4-6",
    "gpt-5.4-mini",
    "llama-3.1-8b-instant",
    "claude-haiku-4-5",
    "gpt-5.5",
    "claude-opus-4-7",
)


def provider_env_var(provider: Provider) -> str:
    return _PROVIDER_ENV[provider]


def provider_is_configured(provider: Provider) -> bool:
    return bool(os.environ.get(provider_env_var(provider)))


def model_is_available(model_id: str) -> bool:
    spec = _MODEL_BY_ID.get(model_id)
    return spec is not None and provider_is_configured(spec.provider)


def configured_model_specs() -> list[ModelSpec]:
    """Return models whose provider API key is configured in this backend process."""
    return [m for m in MODEL_SPECS if provider_is_configured(m.provider)]


def default_model_id() -> str:
    """Backend default for omitted model_id.

    Prefer today's Groq default. If that provider key is absent but another
    provider is configured, fall back to the first available production model
    so local/dev deployments with only Anthropic or OpenAI keys remain usable.
    If no provider keys are configured, return the historical Groq id; the
    first LLM call will raise the same "missing key" class of error as before.
    """
    available = {m.id for m in configured_model_specs()}
    for model_id in _DEFAULT_PRIORITY:
        if model_id in available:
            return model_id
    return DEFAULT_MODEL_ID


def get_model_spec(model_id: str) -> ModelSpec:
    try:
        return _MODEL_BY_ID[model_id]
    except KeyError as exc:
        raise ValueError(f"Unsupported model_id {model_id!r}.") from exc


def resolve_model_id(
    model_id: str | None,
    *,
    require_available: bool = False,
) -> str:
    resolved = model_id or default_model_id()
    spec = get_model_spec(resolved)
    if require_available and not provider_is_configured(spec.provider):
        env_var = provider_env_var(spec.provider)
        raise ValueError(f"model_id {resolved!r} requires {env_var} to be set on the backend.")
    return resolved


# Backoff config -- Phase 2.5 hard constraint (issue #7). Keep small + bounded;
# upstream callers fan out concurrently, so total wall-clock budget per
# request is bounded by base * (2^MAX_RETRIES) ~ 4s.
_BACKOFF_BASE_SECONDS = 0.5
_BACKOFF_MAX_RETRIES = 3
_BACKOFF_JITTER_SECONDS = 0.25


def _retry_on_rate_limit(provider: str, fn: Callable[[], "_R"]) -> "_R":
    """Run fn, retrying on provider rate-limit errors with exponential backoff + jitter.

    Retries up to _BACKOFF_MAX_RETRIES times. Re-raises the final error if every
    attempt fails. Non-rate-limit errors propagate immediately.
    """
    from anthropic import RateLimitError as AnthropicRateLimit
    from openai import RateLimitError as OpenAIRateLimit

    rate_limit_types: tuple[type[Exception], ...] = (OpenAIRateLimit, AnthropicRateLimit)

    last_exc: Exception | None = None
    for attempt in range(_BACKOFF_MAX_RETRIES + 1):
        try:
            return fn()
        except rate_limit_types as exc:
            last_exc = exc
            if attempt == _BACKOFF_MAX_RETRIES:
                break
            delay = _BACKOFF_BASE_SECONDS * (2**attempt) + random.uniform(
                0, _BACKOFF_JITTER_SECONDS
            )
            log.warning(
                "llm.rate_limited",
                provider=provider,
                attempt=attempt + 1,
                max_retries=_BACKOFF_MAX_RETRIES,
                sleep_seconds=round(delay, 3),
            )
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc


_R = TypeVar("_R")


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
        resp = _retry_on_rate_limit("groq", lambda: self._client.chat.completions.create(**kwargs))
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
        resp = _retry_on_rate_limit(
            "anthropic",
            lambda: self._client.messages.create(
                model=self._model,
                system="\n\n".join(system_parts) if system_parts else None,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": m["role"], "content": m["content"]} for m in non_system],
            ),
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


class OpenAIResponsesChat:
    def __init__(self, model: str = "gpt-5.5") -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self._model = model

    def chat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> str:
        # Responses API is the current OpenAI surface for GPT-5.x models.
        # Seed is not exposed here; temperature is intentionally omitted
        # because reasoning-family models can reject unsupported sampling args.
        del temperature, seed
        resp = _retry_on_rate_limit(
            "openai",
            lambda: self._client.responses.create(
                model=self._model,
                input=[{"role": m["role"], "content": m["content"]} for m in messages],
                max_output_tokens=max_tokens,
            ),
        )
        return _extract_openai_response_text(resp)

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


def _extract_openai_response_text(resp) -> str:
    text = getattr(resp, "output_text", None)
    if text:
        return text

    parts: list[str] = []
    for item in getattr(resp, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            candidate = getattr(content, "text", None)
            if candidate:
                parts.append(candidate)
    return "\n".join(parts)


def get_chat_client(model_id: str | None = None) -> ChatClient:
    resolved = resolve_model_id(model_id, require_available=model_id is not None)
    spec = get_model_spec(resolved)
    if not provider_is_configured(spec.provider):
        raise RuntimeError(
            "Set GROQ_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY before running LLM calls."
        )
    if spec.provider == "groq":
        return GroqChat(model=spec.id)
    if spec.provider == "anthropic":
        return AnthropicChat(model=spec.id)
    if spec.provider == "openai":
        return OpenAIResponsesChat(model=spec.id)
    raise RuntimeError(f"Unsupported model provider {spec.provider!r}.")


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
