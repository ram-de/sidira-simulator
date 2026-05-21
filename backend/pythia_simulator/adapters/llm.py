"""LLM client — Groq primary, Anthropic fallback. Mirrors pythia-personas + pythia-crawler.

Exposes a single `chat(messages)` interface that all simulator services use.
"""

from __future__ import annotations

import os
from typing import Protocol


class ChatClient(Protocol):
    def chat(self, messages: list[dict[str, str]], max_tokens: int = 4096) -> str: ...


class GroqChat:
    def __init__(self, model: str = "llama-3.3-70b-versatile") -> None:
        from openai import OpenAI

        self._client = OpenAI(
            api_key=os.environ["GROQ_API_KEY"],
            base_url="https://api.groq.com/openai/v1",
        )
        self._model = model

    def chat(self, messages: list[dict[str, str]], max_tokens: int = 4096) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""


class AnthropicChat:
    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        from anthropic import Anthropic

        self._client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self._model = model

    def chat(self, messages: list[dict[str, str]], max_tokens: int = 4096) -> str:
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        non_system = [m for m in messages if m["role"] != "system"]
        resp = self._client.messages.create(
            model=self._model,
            system="\n\n".join(system_parts) if system_parts else None,
            max_tokens=max_tokens,
            messages=[{"role": m["role"], "content": m["content"]} for m in non_system],
        )
        return resp.content[0].text


def get_chat_client() -> ChatClient:
    if os.environ.get("GROQ_API_KEY"):
        return GroqChat()
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicChat()
    raise RuntimeError("Set GROQ_API_KEY (preferred) or ANTHROPIC_API_KEY.")
