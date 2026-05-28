"""Tests for the Groq 429 backoff (Phase 2.5, issue #7).

Hard constraint: the 50-agent Phase 2.5 run will hit Groq's free-tier rate
limit on first burst (3 LLM calls × 50 agents = 150 concurrent). Without
backoff the run fails on the first 429.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest
from openai import APIError, RateLimitError

from sidira_simulator.adapters import llm as llm_module
from sidira_simulator.adapters.llm import GroqChat


def _rate_limit_error() -> RateLimitError:
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(429, request=request)
    return RateLimitError("Too Many Requests", response=response, body=None)


def _auth_error() -> APIError:
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    return APIError("invalid api key", request=request, body=None)


def _successful_completion(text: str = "ok") -> Any:
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.fixture
def groq_with_fake_client(monkeypatch: pytest.MonkeyPatch) -> tuple[GroqChat, MagicMock]:
    """Construct GroqChat with a stubbed OpenAI client; return both for assertions."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(llm_module.time, "sleep", lambda _: None)  # no real waits

    chat = GroqChat()
    fake_client = MagicMock()
    chat._client = fake_client
    return chat, fake_client


def test_groq_retries_on_429_then_succeeds(
    groq_with_fake_client: tuple[GroqChat, MagicMock],
) -> None:
    chat, fake = groq_with_fake_client
    fake.chat.completions.create.side_effect = [
        _rate_limit_error(),
        _rate_limit_error(),
        _successful_completion("after retries"),
    ]

    out = chat.chat([{"role": "user", "content": "hi"}])

    assert out == "after retries"
    assert fake.chat.completions.create.call_count == 3


def test_groq_gives_up_after_max_retries(
    groq_with_fake_client: tuple[GroqChat, MagicMock],
) -> None:
    chat, fake = groq_with_fake_client
    fake.chat.completions.create.side_effect = [_rate_limit_error()] * 10

    with pytest.raises(RateLimitError):
        chat.chat([{"role": "user", "content": "hi"}])

    # 1 initial attempt + 3 retries = 4 total
    assert fake.chat.completions.create.call_count == 4


def test_groq_does_not_retry_on_non_429(
    groq_with_fake_client: tuple[GroqChat, MagicMock],
) -> None:
    chat, fake = groq_with_fake_client
    fake.chat.completions.create.side_effect = _auth_error()

    with pytest.raises(APIError):
        chat.chat([{"role": "user", "content": "hi"}])

    assert fake.chat.completions.create.call_count == 1


def test_groq_backoff_grows_exponentially(
    monkeypatch: pytest.MonkeyPatch,
    groq_with_fake_client: tuple[GroqChat, MagicMock],
) -> None:
    """Each retry's sleep should be at least twice the previous (modulo jitter floor)."""
    chat, fake = groq_with_fake_client
    fake.chat.completions.create.side_effect = [
        _rate_limit_error(),
        _rate_limit_error(),
        _rate_limit_error(),
        _successful_completion("ok"),
    ]

    sleeps: list[float] = []
    monkeypatch.setattr(llm_module.time, "sleep", lambda s: sleeps.append(s))
    # Pin jitter to 0 so we can assert clean exponential growth.
    monkeypatch.setattr(llm_module.random, "uniform", lambda _a, _b: 0.0)

    chat.chat([{"role": "user", "content": "hi"}])

    assert len(sleeps) == 3
    assert sleeps[1] >= 2 * sleeps[0]
    assert sleeps[2] >= 2 * sleeps[1]
