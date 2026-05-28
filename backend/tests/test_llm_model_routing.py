"""Model registry and provider routing tests for #103 model selection."""

from __future__ import annotations

import pytest

from pythia_simulator.adapters import llm as llm_module


class _FakeChat:
    def __init__(self, model: str) -> None:
        self.model = model


class _FakeGroqChat(_FakeChat):
    pass


class _FakeAnthropicChat(_FakeChat):
    pass


class _FakeOpenAIResponsesChat(_FakeChat):
    pass


@pytest.mark.parametrize(
    ("model_id", "expected_type"),
    [
        ("llama-3.3-70b-versatile", _FakeGroqChat),
        ("claude-sonnet-4-6", _FakeAnthropicChat),
        ("gpt-5.5", _FakeOpenAIResponsesChat),
    ],
)
def test_get_chat_client_routes_supported_model_to_provider(
    monkeypatch: pytest.MonkeyPatch,
    model_id: str,
    expected_type: type[_FakeChat],
) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-groq")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    monkeypatch.setattr(llm_module, "GroqChat", _FakeGroqChat)
    monkeypatch.setattr(llm_module, "AnthropicChat", _FakeAnthropicChat)
    monkeypatch.setattr(llm_module, "OpenAIResponsesChat", _FakeOpenAIResponsesChat)

    chat = llm_module.get_chat_client(model_id)

    assert isinstance(chat, expected_type)
    assert chat.model == model_id


def test_get_chat_client_rejects_explicit_model_without_provider_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        llm_module.get_chat_client("gpt-5.5")


def test_resolve_model_id_rejects_unknown_model_id() -> None:
    with pytest.raises(ValueError, match="Unsupported model_id"):
        llm_module.resolve_model_id("not-a-model")
