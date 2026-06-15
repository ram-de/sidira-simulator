"""Persona Builder — orchestrates Snowflake → sidira-personas library → R2.

This is the simulator-side wrapper that the UI talks to. It hides the
producer-library boundary: from the UI's point of view, you submit a build
config and get back a draft pack; under the hood, this service loads creds,
runs the Snowflake query, invokes the sidira-personas pipeline, and writes
the result to R2 + Postgres.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from sidira_simulator.adapters import credentials
from sidira_simulator.adapters.feature_stores.snowflake import SnowflakeCreds, SnowflakeStore
from sidira_simulator.adapters.r2 import ArtifactStore, get_store
from sidira_simulator.adapters.repositories import PersonaBuildRepo
from sidira_simulator.services.column_mapper import FeatureGroup
from sidira_simulator.services.run_state import RunPhase, RunStateStore, SimulationRunState


class BuildConfig(BaseModel):
    """User-supplied config from the wizard."""

    connection_id: str
    source_query: str = Field(description="SELECT statement returning one row per user.")
    column_mapping: dict[str, FeatureGroup | None]
    k: int | Literal["auto"] = "auto"
    stability_threshold: float = 0.65
    llm_provider: Literal["groq", "anthropic"] = "groq"
    weight_schemes: list[Literal["head_count", "order_weighted", "revenue_weighted"]] = Field(
        default_factory=lambda: ["head_count"]
    )


@dataclass
class BuildResult:
    """Outcome of a build run."""

    build_id: str
    pack_version: str
    stability_score: float
    persona_count: int
    artifact_uri: str


@dataclass
class PipelineOutput:
    """Canned output of the sidira-personas pipeline (the injectable seam).

    Keeps the orchestration testable: the real pipeline (encoder → cluster →
    calibrate → compile_prompts) lives in the ``sidira-personas`` library, which
    is NOT installed in this backend's env. Tests monkeypatch
    :func:`run_personas_pipeline` to return a canned instance of this.
    """

    persona_pack: dict[str, Any]
    stability_score: float
    persona_count: int
    prompts: dict[str, str] = field(default_factory=dict)


# ── pipeline-config assembly (pure Python, pandas-free so this module imports
#    in the API image without the ML stack; see run_personas_pipeline) ─────────

#: Wizard weight-scheme vocab → sidira-personas ``compute_weights`` vocab.
_WEIGHT_SCHEME_MAP: dict[str, str] = {
    "head_count": "headcount",
    "order_weighted": "orders",
    "revenue_weighted": "revenue",
}


def _looks_like_date(value: Any) -> bool:
    """True if ``value`` is a date/datetime, or an ISO-ish date string.

    ``date`` catches both native ``datetime.date`` and ``datetime.datetime`` (the
    latter subclasses the former) — the Snowflake connector returns those for
    real DATE/TIMESTAMP columns, while VARCHAR date columns arrive as strings.
    """
    if isinstance(value, date):
        return True
    if not isinstance(value, str):
        return False
    text = value.strip()
    if len(text) < 8:  # too short to be a real date
        return False
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00").split(" ")[0])
        return True
    except ValueError:
        return False


def _parse_json_obj(value: Any) -> dict | None:
    """Return ``value`` as a dict if it is one / parses to one, else None."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _infer_adapter_type(values: list[Any]) -> tuple[str, list[str] | None]:
    """Infer a sidira-personas adapter ``type`` (and JSON ``keys``) for a column.

    Decision (phase-1 heuristic over a sample of raw values; the wizard does not
    yet capture the adapter type — see #268 follow-up for the override):
      json_counts / json_ratios → dict-valued (or JSON-string) columns; ratios
        when every numeric value is in [0, 1], counts otherwise.
      tenure_days → date / ISO-date-string columns (needs a snapshot column).
      flag → values drawn only from {0,1} / {true,false}.
      ratio → numeric and every value in [0, 1].
      count → non-negative integer-valued numeric.
      score → any other numeric.
      categorical → everything else (strings, mixed).
    """
    non_null = [v for v in values if v is not None and v != ""]
    if not non_null:
        return "categorical", None
    sample = non_null[:200]

    # JSON object columns → per-key shares.
    json_objs = [d for d in (_parse_json_obj(v) for v in sample) if d is not None]
    if json_objs and len(json_objs) >= max(1, len(sample) // 2):
        keys = sorted({k for d in json_objs for k in d})
        numeric_vals = [
            float(x) for d in json_objs for x in d.values()
            if isinstance(x, (int, float)) and not isinstance(x, bool)
        ]
        kind = "json_ratios" if numeric_vals and all(0.0 <= x <= 1.0 for x in numeric_vals) else "json_counts"
        return kind, keys

    # Date columns → tenure.
    if all(_looks_like_date(v) for v in sample):
        return "tenure_days", None

    # Numeric family.
    def _num(v: Any) -> float | None:
        if isinstance(v, bool):
            return float(v)
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                return None
        return None

    nums = [_num(v) for v in sample]
    if all(n is not None for n in nums):
        nums = [n for n in nums if n is not None]
        distinct = set(nums)
        if distinct <= {0.0, 1.0}:
            return "flag", None
        if all(0.0 <= n <= 1.0 for n in nums):
            return "ratio", None
        if all(n >= 0 and float(n).is_integer() for n in nums):
            return "count", None
        return "score", None

    # Boolean-ish strings → flag.
    lowered = {str(v).strip().lower() for v in sample}
    if lowered <= {"true", "false", "t", "f", "yes", "no", "0", "1"}:
        return "flag", None

    return "categorical", None


def _detect_column(rows: list[dict[str, Any]], predicate, *, name_hints: tuple[str, ...]) -> str | None:
    """First column whose name matches a hint (in order) and satisfies predicate."""
    if not rows:
        return None
    columns = list(rows[0].keys())
    for hint in name_hints:
        for col in columns:
            if hint in col.lower() and predicate(col):
                return col
    return None


def _build_pipeline_config(
    rows: list[dict[str, Any]],
    column_mapping: dict[str, FeatureGroup | None],
    config: BuildConfig,
    customer_id: str,
) -> dict[str, Any]:
    """Assemble the sidira-personas pipeline config from the wizard inputs.

    Translates the wizard's group-only ``column_mapping`` into the pipeline's
    ``feature_groups`` spec (inferring each column's adapter type), and fills the
    remaining knobs with documented defaults / name-based detection for the bits
    the wizard does not yet capture (snapshot date, user-id, orders/revenue
    columns). These detections are the natural #268 follow-ups to surface in the
    wizard alongside the adapter-type override.
    """
    columns = list(rows[0].keys()) if rows else []
    col_values: dict[str, list[Any]] = {c: [r.get(c) for r in rows] for c in columns}

    # feature_groups: group → [{name, type, keys?}], adapter type inferred per column.
    feature_groups: dict[str, list[dict[str, Any]]] = {}
    snapshot_needed = False
    for column, group in column_mapping.items():
        if group is None or column not in col_values:
            continue
        atype, keys = _infer_adapter_type(col_values[column])
        if atype == "tenure_days":
            snapshot_needed = True
        spec: dict[str, Any] = {"name": column, "type": atype}
        if keys is not None:
            spec["keys"] = keys
        feature_groups.setdefault(group, []).append(spec)

    # Snapshot date column (for tenure_days). Prefer a snapshot/as-of name; else
    # any unmapped date column. If none and tenure cols exist, those cols are
    # silently skipped by the adapter — acceptable for phase 1.
    snapshot_col = None
    if snapshot_needed:
        snapshot_col = _detect_column(
            rows, lambda c: all(_looks_like_date(v) for v in col_values[c] if v not in (None, "")),
            name_hints=("snapshot", "as_of", "asof", "observed", "date"),
        )

    # User-id column for assignments: an id-like, high-cardinality column.
    n = len(rows) or 1
    user_id_col = _detect_column(
        rows,
        lambda c: len({v for v in col_values[c] if v is not None}) >= 0.9 * n,
        name_hints=("user_id", "consumer_id", "customer_id", "_id", "id"),
    )

    # Weight columns (only consulted for the matching schemes).
    orders_col = _detect_column(rows, lambda c: True, name_hints=("orders", "order_count", "purchases"))
    revenue_col = _detect_column(rows, lambda c: True, name_hints=("revenue", "gmv", "spend", "ltv"))

    schemes = [_WEIGHT_SCHEME_MAP[s] for s in config.weight_schemes if s in _WEIGHT_SCHEME_MAP]
    if "headcount" not in schemes:  # PersonaWeights always carries by_headcount
        schemes.insert(0, "headcount")

    # k: "auto" → BIC over a sensible range; an explicit k → a singleton range.
    k_range = [3, 8] if config.k == "auto" else [int(config.k), int(config.k)]

    cfg: dict[str, Any] = {
        "company_id": customer_id,
        "source": {"type": "snowflake", "user_id_column": user_id_col or "user_id"},
        "feature_groups": feature_groups,
        "encoder": {"method": "pca", "embedding_dim_per_group": 4},
        "cluster": {
            "method": "gmm",
            "k_range": k_range,
            "selection": "bic",
            "random_state": 42,
            "bootstrap_iters": 20,
            "stability_threshold": config.stability_threshold,
            "holdout_frac": 0.2,
        },
        "weights": {"schemes": schemes, "orders_column": orders_col, "revenue_column": revenue_col},
        "sampling": {"n_synthetic_rows": 64, "random_state": 42},
        "prompt_compiler": {"top_n_distinctive_features_per_group": 4, "threshold_sigma": 0.3},
    }
    if snapshot_col:
        cfg["snapshot_date_column"] = snapshot_col
    return cfg


def run_personas_pipeline(
    rows: list[dict[str, Any]],
    column_mapping: dict[str, FeatureGroup | None],
    config: BuildConfig,
    customer_id: str,
    run_id: str,
) -> PipelineOutput:
    """The single injectable seam over the ``sidira-personas`` producer library.

    ``rows`` is the raw per-user result of the source query. This builds a
    DataFrame + a pipeline config (translating the wizard's group-only
    ``column_mapping`` into typed ``feature_groups``) and drives the real
    pipeline (encoder → cluster → calibrate → compile_prompts).

    The ML stack (``pandas``, ``sidira_personas`` → numpy/scikit-learn/scipy) is
    imported **lazily** so this module loads in the API image without those heavy
    deps; in the worker model (#268) the import resolves in the worker image.
    Tests monkeypatch THIS function to return a canned :class:`PipelineOutput`,
    so the build orchestration is exercised without real clustering.
    """
    try:
        import pandas as pd

        from sidira_personas import run_pipeline
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "sidira-personas not installed — the persona build pipeline is unavailable "
            "in this environment."
        ) from exc

    cfg = _build_pipeline_config(rows, column_mapping, config, customer_id)
    df = pd.DataFrame(rows)
    result = run_pipeline(df, cfg, run_id=run_id, no_llm=False)

    pack = result.pack
    return PipelineOutput(
        persona_pack=asdict(pack),
        stability_score=float(pack.overall_stability),
        persona_count=len(pack.personas),
        prompts=dict(result.prompts),
    )


class PersonaBuilderService:
    def __init__(
        self,
        store: ArtifactStore | None = None,
        build_repo: PersonaBuildRepo | None = None,
        connection_repo: Any | None = None,
    ) -> None:
        self._store = store or get_store()
        self._run_state = RunStateStore(self._store)
        self._build_repo = build_repo
        self._connection_repo = connection_repo

    async def run(
        self,
        build_id: str,
        customer_id: str,
        config: BuildConfig,
    ) -> BuildResult:
        """Execute a build end-to-end. Persists status via the build repo +
        progress via RunStateStore. The row is created (PENDING) by the route
        before this task is scheduled; this drives it RUNNING → COMPLETE/FAILED.
        """
        state = SimulationRunState(
            simulation_id=build_id,  # JobRun generalization (Phase 4.5) — same shape
            customer_id=customer_id,
            phase=RunPhase.PENDING,
            started_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self._run_state.write_state(state)

        try:
            await self._build_repo.update_status(build_id, customer_id, "running")
            state.mark_phase(RunPhase.LOADING_PACKS)
            self._run_state.write_state(state)
            self._run_state.emit(state, "run.started")

            # 1–2. Load the connection row (customer-scoped) + decrypt creds.
            row = await self._connection_repo.get(config.connection_id, customer_id)
            if row is None:
                raise ValueError(
                    f"Feature-store connection {config.connection_id!r} not found "
                    f"for customer {customer_id!r}"
                )
            store = self._snowflake_store(row, customer_id)

            # 3. Run the source query → raw user rows.
            rows = store.run_query(config.source_query)
            self._run_state.emit(state, "packs.loaded", row_count=len(rows))

            # 4. Invoke the sidira-personas pipeline (injectable seam). The
            #    binding infers each column's adapter type + builds the pipeline
            #    config from the wizard's group-only mapping (#268).
            state.mark_phase(RunPhase.MATERIALIZING_AGENTS)
            self._run_state.write_state(state)
            output = run_personas_pipeline(
                rows, config.column_mapping, config, customer_id, build_id
            )

            # 5. Stability gate. Below threshold → FAILED (no promoted pack).
            state.mark_phase(RunPhase.SCORING)
            self._run_state.write_state(state)
            self._run_state.emit(
                state,
                "score.updated",
                stability_score=output.stability_score,
                persona_count=output.persona_count,
            )
            if output.stability_score < config.stability_threshold:
                msg = (
                    f"stability {output.stability_score:.3f} below threshold "
                    f"{config.stability_threshold:.3f}"
                )
                await self._fail(build_id, customer_id, state, msg)
                raise BuildStabilityError(msg)

            # 6. Write the pack to R2 (v_N auto-bumped, never overwriting).
            pack_version = self._next_version(customer_id)
            artifact_uri = self._write_pack(customer_id, pack_version, output)

            # 7. Update the build row to COMPLETE.
            completed_at = datetime.now(timezone.utc)
            await self._build_repo.update_status(
                build_id,
                customer_id,
                "complete",
                pack_version=pack_version,
                stability_score=output.stability_score,
                persona_count=output.persona_count,
                completed_at=completed_at,
            )

            # 8. Emit run.complete.
            state.mark_phase(RunPhase.COMPLETE)
            self._run_state.write_state(state)
            self._run_state.emit(
                state,
                "run.complete",
                pack_version=pack_version,
                stability_score=output.stability_score,
                persona_count=output.persona_count,
            )

            return BuildResult(
                build_id=build_id,
                pack_version=pack_version,
                stability_score=output.stability_score,
                persona_count=output.persona_count,
                artifact_uri=artifact_uri,
            )
        except BuildStabilityError:
            # Already recorded as FAILED in the gate; don't double-report.
            raise
        except Exception as exc:  # noqa: BLE001 — record any failure on the row
            await self._fail(build_id, customer_id, state, str(exc))
            raise

    async def _fail(
        self,
        build_id: str,
        customer_id: str,
        state: SimulationRunState,
        error: str,
    ) -> None:
        try:
            await self._build_repo.update_status(
                build_id,
                customer_id,
                "failed",
                error=error,
                completed_at=datetime.now(timezone.utc),
            )
        finally:
            state.mark_phase(RunPhase.FAILED)
            state.error = error
            self._run_state.write_state(state)
            self._run_state.emit(state, "run.failed", error=error)

    def _snowflake_store(self, row: dict[str, Any], customer_id: str) -> SnowflakeStore:
        """Decrypt the password blob and build a SnowflakeStore. The cleartext
        password never leaves this method's scope.

        The blob is sealed with AAD ``f"{customer_id}:{connection_id}"`` at save
        time (``feature_stores.create_connection``); decryption MUST supply the
        same AAD or AES-GCM raises InvalidTag. Mirrors ``_store_from_row`` on the
        preview/test path."""
        aad = f"{customer_id}:{row['id']}".encode()
        secrets = credentials.decrypt(
            credentials.deserialize_blob(row["password_enc"]),
            customer_id=customer_id,
            aad=aad,
        )
        creds = SnowflakeCreds(
            account=row["account"],
            user=row["user"],
            password=secrets["password"],
            warehouse=row["warehouse"],
            role=row["role"],
            database=row["database"],
            schema=row["schema"],
        )
        return SnowflakeStore(creds)

    def _write_pack(
        self,
        customer_id: str,
        pack_version: str,
        output: PipelineOutput,
    ) -> str:
        """Write the pack + manifest (+ prompts) under the versioned prefix."""
        base = f"customers/{customer_id}/personas/{pack_version}"
        pack_key = f"{base}/persona_pack.json"
        self._store.write_text(pack_key, json.dumps(output.persona_pack, indent=2))
        manifest = {
            "version": pack_version,
            "customer_id": customer_id,
            "persona_count": output.persona_count,
            "stability_score": output.stability_score,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._store.write_text(f"{base}/manifest.json", json.dumps(manifest, indent=2))
        for name, prompt in output.prompts.items():
            self._store.write_text(f"{base}/prompts/{name}.md", prompt)
        return pack_key

    def _next_version(self, customer_id: str) -> str:
        """Next sequential version tag (``v_1``, ``v_2``, …).

        The :class:`ArtifactStore` Protocol has no list/glob primitive (R2 keys
        are read by exact key, persona packs are otherwise found via a ``latest``
        pointer). To stay portable across the Local + R2 + Fallback stores we
        probe sequentially: a version exists iff its ``persona_pack.json`` reads
        without raising ``FileNotFoundError``. We return ``v_<max+1>`` (the first
        gap), starting at ``v_1``.
        """
        n = 1
        while True:
            key = f"customers/{customer_id}/personas/v_{n}/persona_pack.json"
            try:
                self._store.read_text(key)
            except FileNotFoundError:
                return f"v_{n}"
            n += 1


class BuildStabilityError(RuntimeError):
    """The build's stability score fell below the configured threshold.

    Distinguishes the stability-gate failure (already recorded as FAILED) from
    any other exception so ``run`` doesn't double-report the failure.
    """
