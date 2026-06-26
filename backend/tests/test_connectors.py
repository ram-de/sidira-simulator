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


def test_parse_csv_rejects_duplicate_headers() -> None:
    """Duplicate headers make the field mapping ambiguous — reject up front
    instead of silently collapsing (csv.DictReader keeps only the last) (MAJOR 6)."""
    with pytest.raises(csv_connector.CsvParseError) as exc:
        csv_connector.parse_csv(b"result,result,n\nwin,loss,100\n")
    assert "duplicate" in str(exc.value).lower()


def test_parse_csv_rejects_case_insensitive_duplicate_headers() -> None:
    with pytest.raises(csv_connector.CsvParseError):
        csv_connector.parse_csv(b"Result,result\nwin,loss\n")


def test_parse_csv_rejects_blank_header() -> None:
    """A blank column header is un-addressable in a mapping — reject it (MAJOR 6)."""
    with pytest.raises(csv_connector.CsvParseError) as exc:
        csv_connector.parse_csv(b"change_description,,result\nx,y,win\n")
    assert "blank" in str(exc.value).lower()


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


def test_sql_query_guard_rejects_function_call_selects() -> None:
    """A 'SELECT' that calls a side-effecting function (or has no FROM) is NOT a
    read — the keyword filter alone would wave these through, so the guard
    rejects function-call SELECTs and bare expression SELECTs (BLOCKER 1)."""
    bypass_attempts = (
        "SELECT nextval('my_seq')",
        "SELECT setval('my_seq', 999)",
        "SELECT dblink_exec('UPDATE t SET x=1')",
        "SELECT pg_sleep(10)",
        "SELECT my_proc()",  # no FROM → rejected as not-a-table-read
        "SELECT 1",  # bare expression, no FROM
        "SELECT pg_read_file('/etc/passwd')",
    )
    for bad in bypass_attempts:
        with pytest.raises(sql_connector.SqlQueryError):
            sql_connector.validate_query(bad)


def test_sql_query_guard_rejects_proc_and_volatile_func_bypasses() -> None:
    """Defense-in-depth: function/proc-style SELECTs and CALL/DO statements must
    not slip past validate_query even when a FROM clause is bolted on, and the
    broader volatile-function families (currval/lo_*/pg_*/advisory locks/dblink*)
    are rejected anywhere in the statement (P1)."""
    bypass_attempts = (
        # CALL / DO statement forms (not a SELECT at all)
        "CALL do_something()",
        "DO $$ BEGIN PERFORM 1; END $$",
        # select-list IS a proc/function call, even with a FROM bolted on
        "SELECT my_proc() FROM experiments",
        "SELECT public.run_job(1) FROM dual",
        "SELECT f(x) AS y FROM t",
        # volatile / side-effecting funcs anywhere in the statement
        "SELECT * FROM t WHERE id = currval('s')",
        "SELECT * FROM t WHERE x = pg_advisory_lock(1)",
        "SELECT * FROM t WHERE y = lo_import('/etc/passwd')",
        "SELECT * FROM t WHERE z = dblink_connect('x')",
        "SELECT * FROM t WHERE q = pg_terminate_backend(1)",
        "SELECT * FROM t WHERE q = pg_read_file('/etc/passwd')",
    )
    for bad in bypass_attempts:
        with pytest.raises(sql_connector.SqlQueryError):
            sql_connector.validate_query(bad)


def test_sql_query_guard_allows_read_aggregates() -> None:
    """A select-list led by a pure read aggregate (count/sum/…) over a real table
    is still a legitimate read and must NOT be rejected by the proc-call guard."""
    assert sql_connector.validate_query("SELECT count(*) FROM experiments")
    assert sql_connector.validate_query("SELECT MAX(effect_size) FROM experiments")
    assert sql_connector.validate_query(
        "SELECT coalesce(name, 'n/a') FROM experiments"
    )


def test_sql_query_guard_rejects_select_into() -> None:
    with pytest.raises(sql_connector.SqlQueryError):
        sql_connector.validate_query("SELECT * INTO new_table FROM experiments")


def test_sql_fetch_rejects_unsupported_backend() -> None:
    """We only advertise/enforce read-only on PostgreSQL. A MySQL or SQLite URL is
    refused rather than falling back to the keyword filter alone (BLOCKER 1)."""
    for url in ("mysql://u:p@h/db", "sqlite:///local.db", "sqlite://"):
        with pytest.raises(sql_connector.SqlUnsupportedBackendError):
            sql_connector.fetch_rows(
                {"connection_string": url, "query": "SELECT * FROM t"}
            )


def test_sql_unsupported_backend_message_is_generic_no_secret() -> None:
    """A no-scheme / ODBC-style connection string (which carries a password) must
    NOT be reflected back in the unsupported-backend message (P2)."""
    secret = "Driver={PostgreSQL};Server=h;Pwd=hunter2;"
    with pytest.raises(sql_connector.SqlUnsupportedBackendError) as exc:
        sql_connector.fetch_rows(
            {"connection_string": secret, "query": "SELECT * FROM t"}
        )
    assert "hunter2" not in str(exc.value)
    assert "Pwd" not in str(exc.value)
    assert "PostgreSQL only" in str(exc.value)


def test_sql_execution_error_is_sanitized_in_import(client: TestClient, monkeypatch) -> None:
    """A raw driver exception (with the connection string / host) must NOT echo
    back to the caller — the import returns a generic message (MAJOR 3)."""
    def _boom(connection_string: str, query: str):
        raise sql_connector.SqlExecutionError(
            "could not connect to server at secret-host:5432 password=hunter2"
        )

    monkeypatch.setattr(sql_connector, "_run_query", _boom)
    payload = ImportRequest(
        mapping=suggest_mapping(list(csv_connector.TEMPLATE_COLUMNS)),
        config={"connection_string": "postgresql://u:p@h/db", "query": "SELECT * FROM t"},
    ).model_dump()
    res = client.post("/connectors/sql/import", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["imported"] == 0
    assert "secret-host" not in res.text
    assert "hunter2" not in res.text
    assert "read-only import policy" in body["message"]


def test_sql_validate_rejects_write_query() -> None:
    out = validate_connector(
        ConnectorKind.SQL,
        ValidateConnectorRequest(
            config={"connection_string": "postgresql://u:p@h/db", "query": "DELETE FROM t"}
        ),
    )
    assert out.ok is False


def test_sql_validate_rejects_unsupported_backend_early() -> None:
    """A MySQL URL must be reported NOT ready on validate (not 'ready' then refused
    at import) and the message must be the generic supported-backends string with
    no connection-string text echoed back (P2)."""
    out = validate_connector(
        ConnectorKind.SQL,
        ValidateConnectorRequest(
            config={"connection_string": "mysql://u:p@h/db", "query": "SELECT * FROM t"}
        ),
    )
    assert out.ok is False
    assert out.state is ConnectorState.NEEDS_CREDENTIALS
    assert "PostgreSQL only" in out.message


def test_sql_validate_unsupported_backend_does_not_echo_secret() -> None:
    """A no-scheme ODBC-style string carries a password; the validate response
    must not reflect it (P2)."""
    out = validate_connector(
        ConnectorKind.SQL,
        ValidateConnectorRequest(
            config={
                "connection_string": "Driver={PostgreSQL};Server=h;Pwd=hunter2;",
                "query": "SELECT * FROM t",
            }
        ),
    )
    assert out.ok is False
    assert "hunter2" not in out.message
    assert "Pwd" not in out.message


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
        config={"connection_string": "postgresql://u:p@h/db", "query": "SELECT * FROM experiments"},
    ).model_dump()
    body = client.post("/connectors/sql/import", json=payload).json()
    assert body["state"] == "active"
    assert body["imported"] == 1
    assert body["experiments"][0]["category"] == "flow"


# ── credential redaction on validation errors (BLOCKER 2) ───────────────────────


def test_validate_error_does_not_leak_sql_connection_string(client: TestClient) -> None:
    """A malformed credentialed body 422s. The connector routes are secret-body
    paths, so the rejected value (which carries the SQL connection string) is
    redacted — the secret never echoes back (BLOCKER 2)."""
    secret = "postgresql://admin:sup3r-s3cret@db.internal:5432/prod"
    # `config` must be a dict[str,str]; send it as the wrong type so Pydantic
    # rejects the field and would normally echo the whole body as the error input.
    res = client.post(
        "/connectors/sql/validate",
        json={"config": secret},  # str, not the required object
    )
    assert res.status_code == 422
    assert secret not in res.text
    assert "sup3r-s3cret" not in res.text


def test_import_error_does_not_leak_statsig_key(client: TestClient) -> None:
    secret = "statsig-secret-server-key-abc123"
    res = client.post(
        "/connectors/statsig/import",
        json={"mapping": "not-an-object", "config": {"api_key": secret}},
    )
    assert res.status_code == 422
    assert secret not in res.text


def test_preview_error_does_not_leak_credentials(client: TestClient) -> None:
    secret = "postgresql://u:leak-me@h/db"
    res = client.post(
        "/connectors/sql/preview",
        json={"config": secret},
    )
    assert res.status_code == 422
    assert "leak-me" not in res.text


# ── credentialed dry-run preview persists nothing (MAJOR 5) ──────────────────────


def test_sql_preview_maps_rows_without_persisting(client: TestClient, monkeypatch) -> None:
    """The /preview dry-run pulls + maps rows but NEVER writes to the archive —
    the customer confirms via /import afterward (MAJOR 5)."""
    def _fake_run(connection_string: str, query: str):
        columns = list(csv_connector.TEMPLATE_COLUMNS)
        row = (
            "Move checkout to a single page", "3-step|single-page",
            "checkout completion rate", "flow", "single-page", "win",
            10.4, 14600, "2024-03-21",
        )
        return columns, [row]

    monkeypatch.setattr(sql_connector, "_run_query", _fake_run)
    payload = ImportRequest(
        mapping=suggest_mapping(list(csv_connector.TEMPLATE_COLUMNS)),
        config={"connection_string": "postgresql://u:p@h/db", "query": "SELECT * FROM experiments"},
    ).model_dump()

    body = client.post("/connectors/sql/preview", json=payload).json()
    assert body["state"] == "active"
    assert len(body["experiments"]) == 1  # the mapped row is shown
    # ...but nothing was written to the archive.
    assert client.get("/connectors/imports").json()["archive_size"] == 0
    assert "nothing imported" in body["message"].lower()


def test_statsig_preview_does_not_persist(client: TestClient, monkeypatch) -> None:
    def _fake_fetch(api_key: str, *, timeout: float = 20.0):
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
    payload = ImportRequest(
        mapping=suggest_mapping(list(csv_connector.TEMPLATE_COLUMNS)),
        config={"api_key": "secret-key"},
    ).model_dump()
    body = client.post("/connectors/statsig/preview", json=payload).json()
    assert len(body["experiments"]) == 1
    assert client.get("/connectors/imports").json()["archive_size"] == 0


def test_preview_without_credentials_is_needs_credentials(client: TestClient) -> None:
    payload = ImportRequest(mapping=_identity_mapping(), config={}).model_dump()
    body = client.post("/connectors/sql/preview", json=payload).json()
    assert body["state"] == "needs_credentials"
    assert body["imported"] == 0


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
