"""#3 Document feeder — bounded extractor tests (slice 1).

Pins the prior-echo discipline: the extracted row is CLOSED to the schema
(no model-invented columns), absence reads as null (never fabricated), values
are coerced to the metric-type family the adapter expects, and the output is in
the same `run_query()` shape the rest of the build path consumes.
"""

from __future__ import annotations

import re

import pytest

from sidira_simulator.services.document_extractor import (
    DocumentExtractionError,
    EntityDocument,
    ExtractionField,
    ExtractionSchema,
    _RawExtraction,
    extract_feature_rows,
    profile_feature_rows,
)


class _StubLLM:
    """Returns a scripted extraction per entity (keyed off the prompt's id).

    ``responses`` maps entity_id → list of (field_name, value) the "model"
    returns — including, deliberately, fields outside the schema to prove they
    are dropped. ``fail`` raises instead, to exercise the error path.
    """

    def __init__(self, responses=None, fail=None):
        self.responses = responses or {}
        self.fail = fail
        self.calls = 0

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        self.calls += 1
        assert temperature == 0.0  # deterministic by contract
        if self.fail is not None:
            raise self.fail
        content = messages[-1]["content"]
        m = re.search(r"Documents for entity (\S+):", content)
        eid = m.group(1) if m else ""
        vals = self.responses.get(eid, [])
        # Natural field-keyed object shape — what a real model produces and what
        # the prompt asks for: {"orders_count": 12, ...}.
        return schema({n: v for n, v in vals})


def _schema() -> ExtractionSchema:
    return ExtractionSchema(
        fields=[
            ExtractionField(name="orders_count", type="count"),
            ExtractionField(name="nps", type="score"),
            ExtractionField(name="promo_ratio", type="ratio"),
            ExtractionField(name="is_churned", type="flag"),
            ExtractionField(name="primary_device", type="categorical"),
            ExtractionField(name="basket_mix", type="json_ratios"),
        ]
    )


# ── closed-set discipline ────────────────────────────────────────────────


def test_row_is_closed_to_schema_invented_fields_dropped() -> None:
    schema = _schema()
    llm = _StubLLM(
        {
            "u1": [
                ("orders_count", 12),
                ("nps", 8),
                # a field the model invented — must NOT appear in the row:
                ("secret_persona_trait", "loves discounts"),
            ]
        }
    )
    rows = extract_feature_rows([EntityDocument(entity_id="u1", text="...")], schema, llm)
    assert len(rows) == 1
    expected_keys = {"entity_id", "orders_count", "nps", "promo_ratio",
                     "is_churned", "primary_device", "basket_mix"}
    assert set(rows[0]) == expected_keys
    assert "secret_persona_trait" not in rows[0]


def test_omitted_field_is_null_not_dropped() -> None:
    schema = _schema()
    # model returns only orders_count; every other field must be present + None.
    llm = _StubLLM({"u1": [("orders_count", 3)]})
    rows = extract_feature_rows([EntityDocument(entity_id="u1", text="x")], schema, llm)
    row = rows[0]
    assert row["orders_count"] == 3.0
    assert row["nps"] is None
    assert row["promo_ratio"] is None
    assert row["basket_mix"] is None


def test_all_rows_share_identical_key_set() -> None:
    schema = _schema()
    llm = _StubLLM({"u1": [("nps", 9)], "u2": [("orders_count", 1)]})
    rows = extract_feature_rows(
        [EntityDocument(entity_id="u1", text="a"), EntityDocument(entity_id="u2", text="b")],
        schema,
        llm,
    )
    assert set(rows[0]) == set(rows[1])  # run_query shape: uniform columns


# ── model output shape robustness (P1: silent all-null) ──────────────────


def test_field_keyed_model_output_is_parsed_not_dropped() -> None:
    """Regression: chat_json does no provider-side schema enforcement, so the
    model returns the NATURAL object shape {field: value}. That must populate the
    row — earlier a fixed `values`-list schema validated it to values=[] and
    silently returned every field null with a 200."""

    class _RawObjectLLM:
        """Returns the raw field-keyed object exactly as a real model would."""

        def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
            return schema({"orders_count": 12, "nps": 8, "invented": "drop me"})

    row = extract_feature_rows(
        [EntityDocument(entity_id="u1", text="x")], _schema(), _RawObjectLLM()
    )[0]
    assert row["orders_count"] == 12.0
    assert row["nps"] == 8.0
    assert "invented" not in row  # still closed to the schema


def test_values_list_shape_still_tolerated() -> None:
    """A model that wraps output in the older {"values":[{name,value}]} shape is
    still parsed (back-compat fallback)."""

    class _ListShapeLLM:
        def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
            return schema({"values": [{"name": "orders_count", "value": 5}]})

    row = extract_feature_rows(
        [EntityDocument(entity_id="u1", text="x")], _schema(), _ListShapeLLM()
    )[0]
    assert row["orders_count"] == 5.0


def test_raw_extraction_accepts_arbitrary_object() -> None:
    """The internal LLM schema keeps every returned key (RootModel), rather than
    discarding unknown keys into ignored extras."""
    parsed = _RawExtraction.model_validate({"a": 1, "b": "x"})
    assert parsed.root == {"a": 1, "b": "x"}


# ── absence never fabricated ─────────────────────────────────────────────


def test_empty_text_skips_llm_and_yields_all_null_row() -> None:
    schema = _schema()
    llm = _StubLLM({"u1": [("orders_count", 99)]})  # would be used IF called
    rows = extract_feature_rows([EntityDocument(entity_id="u1", text="   ")], schema, llm)
    assert llm.calls == 0  # no evidence ⇒ no call
    row = rows[0]
    assert row["entity_id"] == "u1"
    assert all(row[f] is None for f in row if f != "entity_id")


def test_empty_entities_returns_empty() -> None:
    assert extract_feature_rows([], _schema(), _StubLLM()) == []


# ── type coercion to the adapter's families ──────────────────────────────


def test_coercion_per_metric_type() -> None:
    schema = _schema()
    llm = _StubLLM(
        {
            "u1": [
                ("orders_count", "12"),          # numeric string → float
                ("nps", 7),                       # int → float
                ("promo_ratio", 0.25),            # float passthrough
                ("is_churned", "yes"),            # truthy string → 1.0
                ("primary_device", 5),            # number → str label
                ("basket_mix", {"grocery": 0.6, "pharmacy": 0.4, "junk": "nope"}),
            ]
        }
    )
    row = extract_feature_rows([EntityDocument(entity_id="u1", text="x")], schema, llm)[0]
    assert row["orders_count"] == 12.0
    assert row["nps"] == 7.0
    assert row["promo_ratio"] == 0.25
    assert row["is_churned"] == 1.0
    assert row["primary_device"] == "5"
    # json field keeps numeric entries, drops the non-numeric one:
    assert row["basket_mix"] == {"grocery": 0.6, "pharmacy": 0.4}


def test_flag_false_and_bad_numeric_become_clean_values() -> None:
    schema = ExtractionSchema(
        fields=[
            ExtractionField(name="is_churned", type="flag"),
            ExtractionField(name="orders_count", type="count"),
        ]
    )
    llm = _StubLLM(
        {
            "u1": [
                ("is_churned", False),       # bool false → 0.0
                ("orders_count", True),      # bool is NOT a valid number → None
            ],
            "u2": [
                ("is_churned", "garbage"),   # unparseable flag → None
                ("orders_count", "lots"),    # unparseable number → None
            ],
        }
    )
    r1, r2 = extract_feature_rows(
        [EntityDocument(entity_id="u1", text="a"), EntityDocument(entity_id="u2", text="b")],
        schema,
        llm,
    )
    assert r1["is_churned"] == 0.0
    assert r1["orders_count"] is None
    assert r2["is_churned"] is None
    assert r2["orders_count"] is None


# ── schema validation (caller error) ─────────────────────────────────────


def test_empty_schema_rejected() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        extract_feature_rows([EntityDocument(entity_id="u1", text="x")],
                             ExtractionSchema(fields=[]), _StubLLM())


def test_unknown_metric_type_rejected() -> None:
    with pytest.raises(ValueError, match="unknown type"):
        extract_feature_rows(
            [EntityDocument(entity_id="u1", text="x")],
            ExtractionSchema(fields=[ExtractionField(name="x", type="vibes")]),
            _StubLLM(),
        )


def test_duplicate_field_name_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        extract_feature_rows(
            [EntityDocument(entity_id="u1", text="x")],
            ExtractionSchema(
                fields=[ExtractionField(name="x", type="count"),
                        ExtractionField(name="x", type="score")]
            ),
            _StubLLM(),
        )


def test_field_colliding_with_entity_key_rejected() -> None:
    with pytest.raises(ValueError, match="entity_key"):
        extract_feature_rows(
            [EntityDocument(entity_id="u1", text="x")],
            ExtractionSchema(fields=[ExtractionField(name="entity_id", type="count")]),
            _StubLLM(),
        )


# ── LLM failure surfaces as a typed error ────────────────────────────────


def test_llm_failure_raises_extraction_error() -> None:
    schema = _schema()
    llm = _StubLLM(fail=RuntimeError("provider down"))
    with pytest.raises(DocumentExtractionError, match="extraction LLM call failed"):
        extract_feature_rows([EntityDocument(entity_id="u1", text="x")], schema, llm)


def test_client_construction_failure_is_wrapped(monkeypatch) -> None:
    """No provider key ⇒ get_chat_client() raises; surface it as the documented
    DocumentExtractionError (→ 502), not an uncaught error (→ 500)."""
    import sidira_simulator.services.document_extractor as de

    def _boom():
        raise RuntimeError("no LLM provider configured")

    monkeypatch.setattr(de, "get_chat_client", _boom)
    with pytest.raises(DocumentExtractionError, match="could not construct extraction LLM client"):
        extract_feature_rows([EntityDocument(entity_id="u1", text="x")], _schema(), llm=None)


def test_all_empty_docs_never_construct_client(monkeypatch) -> None:
    """Lazy construction: when no document has text, no client is built — so a
    no-key environment still returns clean all-null rows instead of failing."""
    import sidira_simulator.services.document_extractor as de

    def _boom():
        raise AssertionError("client must not be constructed when there is no text")

    monkeypatch.setattr(de, "get_chat_client", _boom)
    rows = extract_feature_rows([EntityDocument(entity_id="u1", text="  ")], _schema(), llm=None)
    assert rows[0]["entity_id"] == "u1"
    assert all(rows[0][f] is None for f in rows[0] if f != "entity_id")


# ── profiling into the Snowflake-preview shape ───────────────────────────


def test_profile_feature_rows_matches_preview_shape() -> None:
    schema = _schema()
    rows = [
        {"entity_id": "u1", "orders_count": 12.0, "nps": 8.0, "promo_ratio": None,
         "is_churned": 0.0, "primary_device": "ios", "basket_mix": {"a": 1.0}},
        {"entity_id": "u2", "orders_count": 3.0, "nps": None, "promo_ratio": 0.5,
         "is_churned": 1.0, "primary_device": "ios", "basket_mix": {"b": 1.0}},
    ]
    n, cols = profile_feature_rows(rows, schema)
    assert n == 2
    # One profile per SCHEMA field (entity_id excluded — it's an id, not a feature).
    assert [c.name for c in cols] == [
        "orders_count", "nps", "promo_ratio", "is_churned", "primary_device", "basket_mix"
    ]
    by_name = {c.name: c for c in cols}
    assert by_name["nps"].non_null_count == 1
    assert by_name["nps"].null_fraction == 0.5
    assert by_name["primary_device"].distinct_count == 1   # both "ios"
    assert by_name["orders_count"].dtype == "count"        # declared metric type
    # dict-valued (json) column is profiled without raising on unhashable values.
    assert by_name["basket_mix"].distinct_count == 2


def test_profile_all_null_column_is_stable() -> None:
    schema = ExtractionSchema(fields=[ExtractionField(name="x", type="count")])
    n, cols = profile_feature_rows([{"entity_id": "u1", "x": None}], schema)
    assert n == 1
    assert cols[0].non_null_count == 0
    assert cols[0].null_fraction == 1.0
    assert cols[0].sample_values is None
