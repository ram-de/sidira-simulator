"""Smoke test for the `benchmark-hillstrom` CLI (#222 PR-B).

The CLI drives the LIVE engine (GATED under pytest), so this test does NOT run
the real engine: it monkeypatches `score_with_engine` with a fake that records
its inputs, then asserts the command WIRES the pieces together — load CSV → adapt
to cases → load the REAL panel → call the scorer with those cases + panel + the
conversion/visit metric builder — emits the pre-registration + result + honesty
sections, and that the resumable checkpoint round-trips through the bind-mount.
The eval math + the per-arm/segment stratifiers are covered by their own tests.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from sidira_simulator.adapters.hillstrom_panel_loader import load_hillstrom_panel
from sidira_simulator.cli import cli
from sidira_simulator.schemas.benchmark import BenchmarkCase
from sidira_simulator.schemas.persona import PersonaPack
from sidira_simulator.schemas.scoring import (
    BenchmarkCaseResult,
    BenchmarkRunResult,
    NullIntegrityCertificate,
)

# A tiny valid Hillstrom CSV: all three arms present, both purchase-history
# segments, binary outcomes — enough for the adapter to enumerate cases.
_CSV = """recency,history_segment,history,mens,womens,zip_code,newbie,channel,segment,visit,conversion,spend
1,1) $0 - $100,50.0,1,0,Urban,1,Web,Mens E-Mail,1,1,30.0
2,2) $100 - $200,150.0,1,0,Rural,0,Phone,Mens E-Mail,1,0,0.0
3,1) $0 - $100,40.0,0,1,Urban,1,Web,Womens E-Mail,1,1,25.0
4,2) $100 - $200,160.0,0,1,Surburban,0,Web,Womens E-Mail,0,0,0.0
5,1) $0 - $100,45.0,1,0,Urban,1,Phone,No E-Mail,0,0,0.0
6,2) $100 - $200,155.0,0,1,Rural,0,Web,No E-Mail,1,0,0.0
"""


def _fake_result(cases: list[BenchmarkCase]) -> BenchmarkRunResult:
    case_results = [
        BenchmarkCaseResult(
            case_id=c.case_id,
            source=c.source,
            observed_lift=c.ground_truth.observed_lift,
            prediction=0.01,
        )
        for c in cases
    ]
    cert = NullIntegrityCertificate(
        n_experiments=len(cases),
        passed=True,
        certifying=True,
        n_permutations=10,
        seed=0,
        integrity_hash="deadbeef",
    )
    return BenchmarkRunResult(
        rank_rho=0.5,
        direction_accuracy=1.0,
        certificate=cert,
        n_cases=len(cases),
        case_results=case_results,
        seed=0,
    )


def test_benchmark_hillstrom_wires_load_adapt_call(tmp_path: Path, monkeypatch):
    csv_path = tmp_path / "hillstrom.csv"
    csv_path.write_text(_CSV, encoding="utf-8")

    captured: dict = {}

    def fake_score_with_engine(cases, *, persona_pack, **kwargs):
        captured["cases"] = list(cases)
        captured["persona_pack"] = persona_pack
        captured["kwargs"] = kwargs
        return _fake_result(list(cases))

    monkeypatch.setattr(
        "sidira_simulator.services.benchmark_runner.score_with_engine",
        fake_score_with_engine,
    )

    result = CliRunner().invoke(
        cli,
        [
            "benchmark-hillstrom",
            "--csv-path",
            str(csv_path),
            "--metric",
            "conversion",
            "--population-size",
            "4",
            "--max-agents",
            "2",
            "--seed",
            "7",
        ],
    )

    assert result.exit_code == 0, result.output
    # load → adapt: one case per treatment arm (Mens + Womens = 2).
    cases = captured["cases"]
    assert len(cases) == 2
    assert all(isinstance(c, BenchmarkCase) for c in cases)
    assert {c.case_id for c in cases} == {
        "hillstrom:mens_email:conversion",
        "hillstrom:womens_email:conversion",
    }
    # The REAL pre-registered panel was passed through.
    assert isinstance(captured["persona_pack"], PersonaPack)
    # Metric + run params threaded through.
    assert captured["kwargs"]["metric_name"] == "conversion"
    assert captured["kwargs"]["population_size"] == 4
    assert captured["kwargs"]["max_agents"] == 2
    assert captured["kwargs"]["seed"] == 7
    # The conversion hypothesis builder was wired (callable forwarded).
    assert callable(captured["kwargs"]["hypothesis_builder"])
    # Emitted sections, including the arm stratifier.
    assert "Pre-registration / run config" in result.output
    assert "Blind-eval result" in result.output
    assert "Null-integrity certificate" in result.output
    assert "by arm" in result.output


def test_benchmark_hillstrom_by_segment(tmp_path: Path, monkeypatch):
    csv_path = tmp_path / "hillstrom.csv"
    csv_path.write_text(_CSV, encoding="utf-8")

    captured: dict = {"calls": []}

    def fake_score_with_engine(cases, *, persona_pack, **kwargs):
        cs = list(cases)
        captured["calls"].append({"cases": cs, "panel": persona_pack})
        captured["cases"] = cs
        # Warm-up runs populate the cache (so the conditioning-integrity check on
        # the final run passes) — mirrors the real scorer.
        cache = kwargs.get("prediction_cache")
        if cache is not None:
            for c in cs:
                cache.setdefault(c.case_id, 0.01)
        return _fake_result(cs)

    monkeypatch.setattr(
        "sidira_simulator.services.benchmark_runner.score_with_engine",
        fake_score_with_engine,
    )

    result = CliRunner().invoke(
        cli,
        ["benchmark-hillstrom", "--csv-path", str(csv_path), "--by-segment"],
    )
    assert result.exit_code == 0, result.output
    # AUDIENCE CONDITIONING (the endpoint-#3 validity crux): each segment's warm-up
    # call must run against a stratum-CONDITIONED sub-panel (a strict subset of the
    # full pack), not the full panel — otherwise the blind engine can't tell strata
    # apart. The two test strata (mens_buyer / womens_buyer) each condition on
    # a different, smaller cohort.
    full_n = len(load_hillstrom_panel().personas)
    warm_panels = [c["panel"] for c in captured["calls"][:-1]]  # all but the final full-set run
    assert warm_panels, "expected per-segment warm-up runs"
    for p in warm_panels:
        assert len(p.personas) < full_n, "segment warm-up must use a conditioned sub-panel"
        assert p.version != load_hillstrom_panel().version  # stratum-suffixed version
    # The two strata condition on DIFFERENT cohorts (men's-buyers vs women's-buyers).
    cohorts = {tuple(sorted(pp.id for pp in c["panel"].personas)) for c in captured["calls"][:-1]}
    assert len(cohorts) >= 2
    # Per-(arm × segment) cases carry the 4-component case_id the by_segment
    # stratifier reads; the segment honesty table is rendered.
    assert all(len(c.case_id.split(":")) == 4 for c in captured["cases"])
    assert "by segment" in result.output


def test_benchmark_hillstrom_segment_warmup_miss_fails_loud(tmp_path: Path, monkeypatch):
    """If a segment warm-up leaves a case OUT of the cache (engine drop), the
    command must FAIL rather than let the final full-panel run re-score it against
    the wrong (undifferentiated) audience and contaminate endpoint #3 (codex P2)."""
    csv_path = tmp_path / "hillstrom.csv"
    csv_path.write_text(_CSV, encoding="utf-8")

    def fake_score_with_engine(cases, *, persona_pack, **kwargs):
        cache = kwargs.get("prediction_cache")
        # Warm only SOME cases (simulate a drop): populate all but one case_id, so
        # the final-run integrity check finds a hole.
        if cache is not None:
            for c in list(cases)[1:]:
                cache[c.case_id] = 0.01
        return _fake_result(list(cases))

    monkeypatch.setattr(
        "sidira_simulator.services.benchmark_runner.score_with_engine",
        fake_score_with_engine,
    )

    result = CliRunner().invoke(
        cli,
        ["benchmark-hillstrom", "--csv-path", str(csv_path), "--by-segment"],
    )
    assert result.exit_code != 0
    assert "segment warm-up failed to score" in result.output


def test_benchmark_hillstrom_checkpoint_resumes(tmp_path: Path, monkeypatch):
    """The bind-mount checkpoint round-trips: a pre-seeded checkpoint file is
    loaded into the prediction_cache passed to the scorer, and the cache is
    re-written after the run (PLAN §4 resumability)."""
    csv_path = tmp_path / "hillstrom.csv"
    csv_path.write_text(_CSV, encoding="utf-8")
    ckpt = tmp_path / "sub" / "ckpt.json"
    ckpt.parent.mkdir()
    # The pre-seeded checkpoint carries the run_config matching the defaults below
    # (metric=conversion, seed=0, model_id=None, population_size=10, max_agents=None,
    # use_segments=False) PLUS the committed panel version, so the resume is accepted.
    panel_version = load_hillstrom_panel().version
    ckpt.write_text(
        json.dumps(
            {
                "run_config": {
                    "metric": "conversion",
                    "seed": 0,
                    "model_id": None,
                    "population_size": 10,
                    "max_agents": None,
                    "use_segments": False,
                    "panel_version": panel_version,
                },
                "predictions": {"hillstrom:mens_email:conversion": 0.02},
            }
        )
    )

    captured: dict = {}

    def fake_score_with_engine(cases, *, persona_pack, **kwargs):
        captured["prediction_cache"] = kwargs.get("prediction_cache")
        # Simulate the scorer warming the cache with a new prediction.
        cache = kwargs.get("prediction_cache")
        if cache is not None:
            cache["hillstrom:womens_email:conversion"] = 0.03
        return _fake_result(list(cases))

    monkeypatch.setattr(
        "sidira_simulator.services.benchmark_runner.score_with_engine",
        fake_score_with_engine,
    )

    result = CliRunner().invoke(
        cli,
        [
            "benchmark-hillstrom",
            "--csv-path",
            str(csv_path),
            "--checkpoint-path",
            str(ckpt),
        ],
    )
    assert result.exit_code == 0, result.output
    # The prior checkpoint was loaded into the cache handed to the scorer.
    assert captured["prediction_cache"]["hillstrom:mens_email:conversion"] == 0.02
    assert "resumed 1 cached prediction" in result.output
    # The cache (now including the scorer's new prediction) was re-checkpointed
    # under the predictions key, alongside the run_config.
    persisted = json.loads(ckpt.read_text())
    assert persisted["predictions"]["hillstrom:mens_email:conversion"] == 0.02
    assert persisted["predictions"]["hillstrom:womens_email:conversion"] == 0.03
    assert persisted["run_config"]["seed"] == 0


def test_benchmark_hillstrom_refuses_checkpoint_config_drift(tmp_path: Path, monkeypatch):
    """A checkpoint written for a DIFFERENT run config (e.g. another seed) is
    REFUSED rather than silently serving stale predictions (codex P2)."""
    csv_path = tmp_path / "hillstrom.csv"
    csv_path.write_text(_CSV, encoding="utf-8")
    ckpt = tmp_path / "ckpt.json"
    ckpt.write_text(
        json.dumps(
            {
                "run_config": {
                    "metric": "conversion",
                    "seed": 999,  # different seed than the run below (seed=0 default)
                    "model_id": None,
                    "population_size": 10,
                    "max_agents": None,
                    "use_segments": False,
                },
                "predictions": {"hillstrom:mens_email:conversion": 0.02},
            }
        )
    )

    def must_not_run(*a, **k):  # pragma: no cover - must not be reached
        raise AssertionError("score_with_engine must not run on a config-drift checkpoint")

    monkeypatch.setattr(
        "sidira_simulator.services.benchmark_runner.score_with_engine", must_not_run
    )

    result = CliRunner().invoke(
        cli,
        ["benchmark-hillstrom", "--csv-path", str(csv_path), "--checkpoint-path", str(ckpt)],
    )
    assert result.exit_code != 0
    assert "DIFFERENT run config" in result.output
