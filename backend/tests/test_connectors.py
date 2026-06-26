"""Tests for the experiment-onboarding connector framework (#19).

Covers the three things the ticket calls out for tests:
- the CSV parse,
- the field mapping (the two-table firewall boundary), and
- the connector registry,

plus the import write-path, the honest needs-credentials states for Statsig/SQL,
and the Statsig/SQL row normalization (with the network/DB calls stubbed — no
test hits a live key or database).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from sidira_simulator.main import app
from sidira_simulator.schemas.connector import (
    ConnectorKind,
    ConnectorState,
    FieldMapping,
)
from sidira_simulator.schemas.experiment_memory import (
    ExperimentCategory,
    ExperimentResult,
)
from sidira_simulator.services.connectors import (
    csv_connector,
    sql_connector,
    statsig_connector,
)
from sidira_simulator.services.connectors.ingestion_store import get_ingestion_store
from sidira_simulator.services.connectors.mapping import (
    map_row,
    map_rows,
    missing_required,
    suggest_mapping,
)
from sidira_simulator.services.connectors.registry import (
    describe_connectors,
    get_descriptor,
)
from sidira_simulator.services.experiment_ingest import run_import, validate_connector
from sidira_simulator.schemas.connector import (
    ImportRequest,
    ValidateConnectorRequest,
)


@pytest.fixture
def client():
    get_ingestion_store().clear()
    with TestClient(app) as c:
        yield c
    get_ingestion_store().clear()


# A canonical mapping where the source column names equal the Experiment fields.
def _identity_mapping(delimiter: str = "|") -> FieldMapping:
    fields = (
        "change_description",
        "variants",
        "primary_metric",
        "category",
        "winner",
        "result",
        "effect_size_pct",
        "n",
        "date",
    )
    return FieldMapping(columns={f: f for f in fields}, variant_delimiter=delimiter)


# ── registry ─────────────────────────────────────────────────────────────────


def test_registry_lists_csv_active_and_credentialed_inactive() -> None:
    connectors = describe_connectors()
    by_kind = {c.kind: c for c in connectors}
    assert set(by_kind) == {ConnectorKind.CSV, ConnectorKind.STATSIG, ConnectorKind.SQL}
    # CSV first, then the credentialed ones.
    assert connectors[0].kind is ConnectorKind.CSV

    assert by_kind[ConnectorKind.CSV].state is ConnectorState.ACTIVE
    assert by_kind[ConnectorKind.CSV].credential_fields == []
    assert by_kind[ConnectorKind.CSV].needs_message is None

    statsig = by_kind[ConnectorKind.STATSIG]
    assert statsig.state is ConnectorState.NEEDS_CREDENTIALS
    assert "api_key" in statsig.credential_fields
    assert statsig.needs_message  # an honest "what to supply" message

    sql = by_kind[ConnectorKind.SQL]
    assert sql.state is ConnectorState.NEEDS_CREDENTIALS
    assert {"connection_string", "query"} <= set(sql.credential_fields)


def test_registry_endpoint(client: TestClient) -> None:
    res = client.get("/connectors")
    assert res.status_code == 200
    kinds = [c["kind"] for c in res.json()["connectors"]]
    assert kinds == ["csv", "statsig", "sql"]


def test_get_descriptor_returns_copy() -> None:
    a = get_descriptor(ConnectorKind.CSV)
    a.name = "MUTATED"
    b = get_descriptor(ConnectorKind.CSV)
    assert b.name != "MUTATED"


# ── CSV parse ─────────────────────────────────────────────────────────────────


def test_parse_csv_normalizes_rows() -> None:
    raw = b"change_description,result\nRaise price,win\nShorten CTA,flat\n"
    columns, rows = csv_connector.parse_csv(raw)
    assert columns == ["change_description", "result"]
    assert rows == [
        {"change_description": "Raise price", "result": "win"},
        {"change_description": "Shorten CTA", "result": "flat"},
    ]


def test_parse_csv_strips_bom_and_whitespace() -> None:
    raw = "﻿ change_description , result \nRaise price , win \n".encode("utf-8")
    columns, rows = csv_connector.parse_csv(raw)
    assert columns == ["change_description", "result"]
    assert rows[0]["change_description"] == "Raise price"
    assert rows[0]["result"] == "win"


def test_parse_csv_rejects_non_utf8() -> None:
    with pytest.raises(csv_connector.CsvParseError):
        csv_connector.parse_csv(b"\xff\xfe not text")


def test_parse_csv_rejects_headerless() -> None:
    with pytest.raises(csv_connector.CsvParseError):
        csv_connector.parse_csv(b"")


def test_sample_csv_roundtrips_into_valid_experiments() -> None:
    columns, rows = csv_connector.parse_csv(csv_connector.sample_csv().encode("utf-8"))
    assert columns == list(csv_connector.TEMPLATE_COLUMNS)
    mapping = suggest_mapping(columns)
    experiments, errors = map_rows(rows, mapping, id_prefix="sample")
    assert errors == []
    assert len(experiments) == 3
    # spans win / loss / flat — counter-intuitive outcomes survive the round-trip
    assert {e.result for e in experiments} == {
        ExperimentResult.WIN,
        ExperimentResult.LOSS,
        ExperimentResult.FLAT,
    }


def test_template_csv_is_header_only() -> None:
    text = csv_connector.template_csv()
    lines = [ln for ln in text.splitlines() if ln.strip()]
    assert lines == [",".join(csv_connector.TEMPLATE_COLUMNS)]


# ── field mapping (the firewall boundary) ──────────────────────────────────────


def test_suggest_mapping_matches_synonyms() -> None:
    columns = ["Hypothesis", "Arms", "KPI", "Type", "Won", "Outcome", "Lift", "Users", "Ended"]
    mapping = suggest_mapping(columns)
    assert mapping.columns["change_description"] == "Hypothesis"
    assert mapping.columns["variants"] == "Arms"
    assert mapping.columns["primary_metric"] == "KPI"
    assert mapping.columns["category"] == "Type"
    assert mapping.columns["effect_size_pct"] == "Lift"
    assert mapping.columns["n"] == "Users"
    assert mapping.columns["date"] == "Ended"


def test_suggest_mapping_leaves_unknown_unmapped() -> None:
    mapping = suggest_mapping(["foo", "bar"])
    assert mapping.columns == {}
    assert set(missing_required(mapping))  # everything required is missing


def test_map_row_builds_experiment_with_coercion() -> None:
    row = {
        "change_description": "Raise the Pro price",
        "variants": "$29|$39",
        "primary_metric": "revenue per visitor",
        "category": "Pricing",
        "winner": "$39",
        "result": "Won",
        "effect_size_pct": "18.5%",
        "n": "12,700",
        "date": "2024-03-28",
    }
    out = map_row(row, _identity_mapping(), row_index=1, id_prefix="t")
    assert not hasattr(out, "message"), out  # not a RowError
    assert out.id == "t-0001"
    assert out.variants == ["$29", "$39"]
    assert out.category is ExperimentCategory.PRICING
    assert out.result is ExperimentResult.WIN
    assert out.effect_size_pct == 18.5  # % stripped
    assert out.n == 12700  # thousands separator stripped


def test_map_row_errors_are_honest_not_fabricated() -> None:
    base = {
        "change_description": "x",
        "variants": "a|b",
        "primary_metric": "m",
        "category": "ui",
        "winner": "a",
        "result": "win",
        "effect_size_pct": "1.0",
        "n": "100",
        "date": "2024-01-01",
    }
    m = _identity_mapping()

    bad_result = map_row({**base, "result": "banana"}, m, row_index=2, id_prefix="t")
    assert getattr(bad_result, "row", None) == 2 and "result" in bad_result.message

    bad_n = map_row({**base, "n": "-5"}, m, row_index=3, id_prefix="t")
    assert "n" in bad_n.message

    bad_date = map_row({**base, "date": "March 2024"}, m, row_index=4, id_prefix="t")
    assert "date" in bad_date.message

    one_arm = map_row({**base, "variants": "only-one"}, m, row_index=5, id_prefix="t")
    assert "variants" in one_arm.message


def test_mapping_missing_required_field_blocks_all_rows() -> None:
    # Drop the result column from the mapping — every row must error, none fabricate.
    cols = {f: f for f in ("change_description", "variants", "primary_metric", "category", "winner", "effect_size_pct", "n", "date")}
    mapping = FieldMapping(columns=cols)
    assert "result" in missing_required(mapping)
    out = map_row({"change_description": "x"}, mapping, row_index=1, id_prefix="t")
    assert "missing required fields" in out.message
    assert "result" in out.message


def test_firewall_input_and_outcome_read_from_distinct_columns() -> None:
    # change_description (input) and winner (outcome) come from different source
    # columns; mapping never crosses them.
    mapping = FieldMapping(
        columns={
            "change_description": "desc",
            "variants": "arms",
            "primary_metric": "metric",
            "category": "cat",
            "winner": "win_col",
            "result": "res_col",
            "effect_size_pct": "eff",
            "n": "size",
            "date": "day",
        }
    )
    row = {
        "desc": "input side text",
        "arms": "a|b",
        "metric": "rate",
        "cat": "copy",
        "win_col": "b",
        "res_col": "win",
        "eff": "3.2",
        "size": "500",
        "day": "2024-02-02",
    }
    out = map_row(row, mapping, row_index=1, id_prefix="t")
    assert out.change_description == "input side text"
    assert out.winner == "b"  # outcome read independently from its own column


# ── CSV preview endpoint ───────────────────────────────────────────────────────


def test_csv_preview_endpoint(client: TestClient) -> None:
    csv_bytes = csv_connector.sample_csv().encode("utf-8")
    res = client.post(
        "/connectors/csv/preview",
        files={"file": ("sample.csv", csv_bytes, "text/csv")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["row_count"] == 3
    assert len(body["preview"]) == 3
    assert body["errors"] == []
    assert body["suggested_mapping"]["columns"]["change_description"] == "change_description"


def test_csv_template_and_sample_download(client: TestClient) -> None:
    t = client.get("/connectors/csv/template")
    assert t.status_code == 200
    assert "text/csv" in t.headers["content-type"]
    assert "attachment" in t.headers["content-disposition"]
    assert t.text.splitlines()[0] == ",".join(csv_connector.TEMPLATE_COLUMNS)

    s = client.get("/connectors/csv/sample")
    assert s.status_code == 200
    assert len(s.text.splitlines()) == 4  # header + 3 rows


def test_csv_preview_rejects_bad_upload(client: TestClient) -> None:
    res = client.post(
        "/connectors/csv/preview",
        files={"file": ("x.csv", b"\xff\xfe", "text/csv")},
    )
    assert res.status_code == 400


# ── CSV import write-path ──────────────────────────────────────────────────────


def test_csv_import_writes_to_archive(client: TestClient) -> None:
    columns, rows = csv_connector.parse_csv(csv_connector.sample_csv().encode("utf-8"))
    mapping = suggest_mapping(columns)
    payload = ImportRequest(mapping=mapping, rows=rows).model_dump()
    res = client.post("/connectors/csv/import", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["state"] == "active"
    assert body["imported"] == 3
    assert body["failed"] == 0
    assert len(body["experiments"]) == 3

    # archive is now populated and the import is logged
    imports = client.get("/connectors/imports").json()
    assert imports["archive_size"] == 3
    assert len(imports["imports"]) == 1
    assert imports["imports"][0]["kind"] == "csv"


def test_csv_import_reports_failed_rows_without_fabricating(client: TestClient) -> None:
    mapping = _identity_mapping()
    rows = [
        {  # good
            "change_description": "good", "variants": "a|b", "primary_metric": "m",
            "category": "ui", "winner": "a", "result": "win",
            "effect_size_pct": "1.0", "n": "100", "date": "2024-01-01",
        },
        {  # bad result
            "change_description": "bad", "variants": "a|b", "primary_metric": "m",
            "category": "ui", "winner": "a", "result": "???",
            "effect_size_pct": "1.0", "n": "100", "date": "2024-01-01",
        },
    ]
    payload = ImportRequest(mapping=mapping, rows=rows).model_dump()
    body = client.post("/connectors/csv/import", json=payload).json()
    assert body["imported"] == 1
    assert body["failed"] == 1
    assert body["errors"][0]["row"] == 2


# ── Statsig: honest needs-credentials + stubbed pull ───────────────────────────


def test_statsig_validate_needs_credentials() -> None:
    out = validate_connector(ConnectorKind.STATSIG, ValidateConnectorRequest(config={}))
    assert out.ok is False
    assert out.state is ConnectorState.NEEDS_CREDENTIALS
    assert out.message  # clear "supply your key" message


def test_statsig_import_without_key_returns_needs_credentials(client: TestClient) -> None:
    payload = ImportRequest(mapping=_identity_mapping(), config={}).model_dump()
    body = client.post("/connectors/statsig/import", json=payload).json()
    assert body["state"] == "needs_credentials"
    assert body["imported"] == 0
    assert body["experiments"] == []
    # nothing was written to the archive
    assert client.get("/connectors/imports").json()["archive_size"] == 0


def test_statsig_import_with_key_maps_pulled_rows(client: TestClient, monkeypatch) -> None:
    # Stub the network pull — no live key, no live call.
    def _fake_fetch(api_key: str, *, timeout: float = 20.0):
        assert api_key == "secret-key"
        return [
            {
                "description": "Raise the Pro price",
                "groups": [{"name": "$29"}, {"name": "$39"}],
                "primaryMetrics": [{"name": "revenue per visitor"}],
                "category": "pricing",
                "decision": {"winningGroup": "$39", "result": "win", "effectSizePct": 18.5},
                "sampleSize": 12700,
                "endTime": "2024-03-28",
            }
        ]

    monkeypatch.setattr(statsig_connector, "_fetch_experiments", _fake_fetch)
    mapping = suggest_mapping(list(csv_connector.TEMPLATE_COLUMNS))
    payload = ImportRequest(mapping=mapping, config={"api_key": "secret-key"}).model_dump()
    body = client.post("/connectors/statsig/import", json=payload).json()
    assert body["state"] == "active"
    assert body["imported"] == 1
    exp = body["experiments"][0]
    assert exp["variants"] == ["$29", "$39"]
    assert exp["result"] == "win"
    assert exp["effect_size_pct"] == 18.5


# ── SQL: honest needs-credentials + read-only guard + stubbed query ─────────────


def test_sql_validate_needs_credentials() -> None:
    out = validate_connector(ConnectorKind.SQL, ValidateConnectorRequest(config={}))
    assert out.ok is False
    assert out.state is ConnectorState.NEEDS_CREDENTIALS


def test_sql_query_guard_rejects_writes() -> None:
    for bad in ("DELETE FROM experiments", "DROP TABLE t", "SELECT 1; DROP TABLE t", "UPDATE t SET x=1"):
        with pytest.raises(sql_connector.SqlQueryError):
            sql_connector.validate_query(bad)
    # a read-only SELECT / CTE is accepted
    assert sql_connector.validate_query("SELECT * FROM experiments")
    assert sql_connector.validate_query("WITH x AS (SELECT 1) SELECT * FROM x")


def test_sql_validate_rejects_write_query() -> None:
    out = validate_connector(
        ConnectorKind.SQL,
        ValidateConnectorRequest(config={"connection_string": "sqlite://", "query": "DELETE FROM t"}),
    )
    assert out.ok is False


def test_sql_import_with_stubbed_query_maps_rows(client: TestClient, monkeypatch) -> None:
    def _fake_run(connection_string: str, query: str):
        assert query.lower().startswith("select")
        columns = list(csv_connector.TEMPLATE_COLUMNS)
        row = (
            "Move checkout to a single page", "3-step|single-page",
            "checkout completion rate", "flow", "single-page", "win",
            10.4, 14600, "2024-03-21",
        )
        return columns, [row]

    monkeypatch.setattr(sql_connector, "_run_query", _fake_run)
    mapping = suggest_mapping(list(csv_connector.TEMPLATE_COLUMNS))
    payload = ImportRequest(
        mapping=mapping,
        config={"connection_string": "sqlite://", "query": "SELECT * FROM experiments"},
    ).model_dump()
    body = client.post("/connectors/sql/import", json=payload).json()
    assert body["state"] == "active"
    assert body["imported"] == 1
    assert body["experiments"][0]["category"] == "flow"


# ── ingestion store isolation ──────────────────────────────────────────────────


def test_imports_are_scoped_per_customer(client: TestClient) -> None:
    from sidira_simulator.api.deps import current_customer_id

    columns, rows = csv_connector.parse_csv(csv_connector.sample_csv().encode("utf-8"))
    payload = ImportRequest(mapping=suggest_mapping(columns), rows=rows).model_dump()

    app.dependency_overrides[current_customer_id] = lambda: "cust-A"
    try:
        client.post("/connectors/csv/import", json=payload)
        assert client.get("/connectors/imports").json()["archive_size"] == 3
    finally:
        app.dependency_overrides.pop(current_customer_id, None)

    app.dependency_overrides[current_customer_id] = lambda: "cust-B"
    try:
        # B sees an empty archive — no cross-tenant bleed
        assert client.get("/connectors/imports").json()["archive_size"] == 0
    finally:
        app.dependency_overrides.pop(current_customer_id, None)
