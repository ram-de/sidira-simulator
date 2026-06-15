"""Tests for the column → feature-group mapper service (issue #23).

The LLM is never called: a fake ``ChatClient`` returns a canned ``_RawMapping``
from ``chat_json``. Covers the happy path (columns spread across groups with
confidences), the unmapped bucket (omitted column + out-of-canon group label),
determinism (temperature=0, one-shot), and graceful failure.
"""

from __future__ import annotations

import pytest

from sidira_simulator.adapters.feature_stores import ColumnProfile
from sidira_simulator.adapters.llm import JSONRepairError
from sidira_simulator.services import column_mapper
from sidira_simulator.services.column_mapper import (
    CANONICAL_GROUPS,
    ColumnMappingError,
    MappingSuggestion,
    suggest_mapping,
)

# ── fakes ─────────────────────────────────────────────────────────────────────


class _FakeChat:
    """ChatClient stub: records chat_json kwargs, returns a canned result.

    ``result`` is what ``chat_json`` returns; pass an Exception instance to
    ``raises`` to have the call blow up instead.
    """

    def __init__(self, *, result=None, raises: Exception | None = None) -> None:
        self.result = result
        self.raises = raises
        self.calls: list[dict] = []

    def chat(self, messages, max_tokens=4096, temperature=0.0, seed=None):  # pragma: no cover
        raise AssertionError("mapper must use chat_json, not chat")

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        self.calls.append(
            {
                "messages": messages,
                "schema": schema,
                "temperature": temperature,
                "seed": seed,
            }
        )
        if self.raises is not None:
            raise self.raises
        # Coerce the canned dict through the real LLM-response schema, like prod.
        return schema.model_validate(self.result)


def _col(name: str, dtype: str = "TEXT", samples=None) -> ColumnProfile:
    return ColumnProfile(
        name=name,
        dtype=dtype,
        non_null_count=100,
        null_fraction=0.0,
        sample_values=samples or [],
    )


# ── happy path ──────────────────────────────────────────────────────────────


def test_columns_distributed_across_groups_with_confidences():
    columns = [
        _col("age", "INT", [34, 41]),
        _col("order_count", "INT", [3, 12]),
        _col("churn_risk", "FLOAT", [0.1, 0.8]),
    ]
    chat = _FakeChat(
        result={
            "suggestions": [
                {"column": "age", "group": "demographic_identity", "confidence": "high"},
                {"column": "order_count", "group": "behavioral_patterns", "confidence": "med"},
                {"column": "churn_risk", "group": "loyalty_lifecycle", "confidence": "low"},
            ]
        }
    )

    result = suggest_mapping(columns, llm=chat)

    assert isinstance(result, MappingSuggestion)
    assert [a.column for a in result.demographic_identity] == ["age"]
    assert result.demographic_identity[0].confidence == "high"
    assert [a.column for a in result.behavioral_patterns] == ["order_count"]
    assert result.behavioral_patterns[0].confidence == "med"
    assert [a.column for a in result.loyalty_lifecycle] == ["churn_risk"]
    assert result.unmapped == []


def test_call_is_one_shot_and_deterministic():
    chat = _FakeChat(result={"suggestions": []})
    suggest_mapping([_col("x")], llm=chat)
    assert len(chat.calls) == 1
    call = chat.calls[0]
    assert call["temperature"] == 0.0
    assert [m["role"] for m in call["messages"]] == ["system", "user"]


# ── unmapped bucket ───────────────────────────────────────────────────────────


def test_omitted_and_junk_group_columns_go_to_unmapped():
    columns = [_col("user_id"), _col("created_at"), _col("mystery")]
    chat = _FakeChat(
        result={
            "suggestions": [
                # user_id explicitly nulled, mystery tagged with a junk group,
                # created_at omitted entirely.
                {"column": "user_id", "group": None, "confidence": "low"},
                {"column": "mystery", "group": "not_a_real_group", "confidence": "high"},
            ]
        }
    )

    result = suggest_mapping(columns, llm=chat)

    unmapped = {a.column for a in result.unmapped}
    assert unmapped == {"user_id", "created_at", "mystery"}
    # nothing leaked into a canonical bucket
    for group in CANONICAL_GROUPS:
        assert getattr(result, group) == []


def test_every_input_column_appears_exactly_once():
    columns = [_col("a"), _col("b"), _col("c")]
    chat = _FakeChat(
        result={
            "suggestions": [
                {"column": "a", "group": "demographic_identity", "confidence": "high"},
                {"column": "b", "group": "bogus", "confidence": "med"},
                # c omitted
            ]
        }
    )
    result = suggest_mapping(columns, llm=chat)
    all_cols = [
        a.column
        for group in (*CANONICAL_GROUPS, "unmapped")
        for a in getattr(result, group)
    ]
    assert sorted(all_cols) == ["a", "b", "c"]


def test_confidence_aliases_normalized():
    chat = _FakeChat(
        result={
            "suggestions": [
                {"column": "a", "group": "demographic_identity", "confidence": "medium"},
                {"column": "b", "group": "demographic_identity", "confidence": "HIGH"},
                {"column": "c", "group": "demographic_identity", "confidence": "garbage"},
            ]
        }
    )
    result = suggest_mapping([_col("a"), _col("b"), _col("c")], llm=chat)
    confs = {a.column: a.confidence for a in result.demographic_identity}
    assert confs == {"a": "med", "b": "high", "c": "low"}


# ── short-circuits + failures ──────────────────────────────────────────────────


def test_empty_columns_skips_llm():
    chat = _FakeChat(result={"suggestions": []})
    result = suggest_mapping([], llm=chat)
    assert chat.calls == []
    assert result == MappingSuggestion()


def test_unparseable_llm_output_raises_mapping_error():
    chat = _FakeChat(raises=JSONRepairError("nope"))
    with pytest.raises(ColumnMappingError):
        suggest_mapping([_col("a")], llm=chat)


def test_provider_failure_raises_mapping_error():
    chat = _FakeChat(raises=RuntimeError("ANTHROPIC_API_KEY missing"))
    with pytest.raises(ColumnMappingError):
        suggest_mapping([_col("a")], llm=chat)


def test_defaults_to_get_chat_client(monkeypatch):
    chat = _FakeChat(result={"suggestions": []})
    monkeypatch.setattr(column_mapper, "get_chat_client", lambda model_id=None: chat)
    suggest_mapping([_col("a")])
    assert len(chat.calls) == 1
