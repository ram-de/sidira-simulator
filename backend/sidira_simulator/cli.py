"""CLI — `sidira-simulator serve` for local dev, plus the Upworthy benchmark run."""

from __future__ import annotations

import click
import uvicorn


@click.group()
def cli() -> None:
    """sidira-simulator — Sidira simulation backend."""


@cli.command()
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=8000, type=int)
@click.option("--reload/--no-reload", default=True)
def serve(host: str, port: int, reload: bool) -> None:
    """Run the FastAPI app with uvicorn."""
    uvicorn.run("sidira_simulator.main:app", host=host, port=port, reload=reload)


@cli.command("benchmark-upworthy")
@click.option(
    "--csv-path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Path to a pre-downloaded Upworthy archive CSV (exploratory-packages split).",
)
@click.option(
    "--limit",
    default=None,
    type=int,
    help="Bounded pilot: cap the number of benchmark CASES scored (after adaptation).",
)
@click.option(
    "--max-tests",
    default=None,
    type=int,
    help="Bounded pilot: cap the number of source TESTS adapted (before --limit).",
)
@click.option("--model-id", default=None, help="LLM model id to drive the engine.")
@click.option(
    "--population-size",
    default=10,
    type=int,
    help="Agents per arm (engine population_size).",
)
@click.option(
    "--max-agents",
    default=None,
    type=int,
    help="Bounded pilot: hard cap on agents per arm (engine max_agents).",
)
@click.option(
    "--seed", default=0, type=int, help="Base seed (per-case seeds + null/bootstrap RNG)."
)
@click.option("--n-permutations", default=1000, type=int, help="Null-integrity label permutations.")
@click.option("--baseline-index", default=0, type=int, help="Control variant index per test.")
def benchmark_upworthy(
    csv_path: str,
    limit: int | None,
    max_tests: int | None,
    model_id: str | None,
    population_size: int,
    max_agents: int | None,
    seed: int,
    n_permutations: int,
    baseline_index: int,
) -> None:
    """Run the Tier-0 Upworthy CTR benchmark against the LIVE engine (#222).

    End-to-end: load a local Upworthy archive CSV → adapt to BenchmarkCases →
    load the pre-registered Upworthy panel → score the live engine as the blind
    predictor (`score_with_engine`) → emit the run result, the stratified honesty
    table, the null-integrity certificate, and the pre-registration metadata.

    This is the GATED live path: it builds the real SimulationRunner and needs
    live LLM keys at runtime (it refuses to run under pytest / CI). Use the
    bounded-pilot flags (`--max-agents`, `--population-size`, `--limit`,
    `--max-tests`) to keep a first run small and cheap.

    Honest output: rank-ρ is the PRIMARY endpoint; magnitude stays
    rank/directional (uncalibrated, pre-#222 shrinkage).
    """
    # Imports are local so the CLI module stays import-light (and so the engine
    # is only pulled in when this command actually runs, behind the gate).
    from sidira_simulator.adapters.upworthy_panel_loader import (
        load_upworthy_panel,
        upworthy_panel_registration,
    )
    from sidira_simulator.services.benchmark_adapter import upworthy_test_to_cases
    from sidira_simulator.services.benchmark_honesty import (
        by_source,
        render,
        stratify,
    )
    from sidira_simulator.services.benchmark_runner import score_with_engine
    from sidira_simulator.services.upworthy_archive import load_upworthy_archive

    # ── 1. Load + adapt the archive into benchmark cases. ──
    tests, summary = load_upworthy_archive(csv_path)
    if max_tests is not None:
        tests = tests[:max_tests]
    cases = []
    n_skipped = 0
    for test in tests:
        adaptation = upworthy_test_to_cases(test, baseline_index=baseline_index)
        cases.extend(adaptation.cases)
        n_skipped += len(adaptation.skipped)
    if limit is not None:
        cases = cases[:limit]

    if not cases:
        raise click.ClickException(
            "No benchmark cases produced from the archive "
            f"({summary.tests_built} tests built, {n_skipped} pairs skipped). "
            "Check --csv-path / --baseline-index / --max-tests / --limit."
        )

    # ── 2. Pre-registration metadata (panel + run config). ──
    registration = upworthy_panel_registration()
    panel = load_upworthy_panel()

    click.echo("== Pre-registration / run config ==")
    click.echo(f"panel_id:           {registration.panel_id}")
    click.echo(f"panel_version:      {registration.version}")
    click.echo(f"panel_persona_n:    {registration.persona_count}")
    click.echo(f"panel_weight:       {registration.weight_scheme}")
    click.echo(f"panel_synthetic:    {registration.is_synthetic_generic}")
    click.echo("primary_endpoint:   rank_rho (§5)")
    click.echo("metric:             ctr (raw probability delta)")
    click.echo(f"model_id:           {model_id}")
    click.echo(f"seed:               {seed}")
    click.echo(f"n_permutations:     {n_permutations}")
    click.echo(f"population_size:    {population_size}")
    click.echo(f"max_agents:         {max_agents}")
    click.echo("treatment_fraction: 0.5 (locked)")
    click.echo("paraphrase_K:       env SIDIRA_CONVERSION_PARAPHRASES (default 1)")
    click.echo(
        f"cases_scored_input: {len(cases)} "
        f"(from {summary.tests_built} tests, {n_skipped} pairs skipped)"
    )
    click.echo("")

    # ── 3. Run the live engine as the blind predictor (GATED). ──
    result = score_with_engine(
        cases,
        persona_pack=panel,
        customer_id="benchmark",
        model_id=model_id,
        population_size=population_size,
        max_agents=max_agents,
        seed=seed,
        n_permutations=n_permutations,
    )

    # ── 4. Emit the run result + null certificate. ──
    click.echo("== Blind-eval result ==")
    click.echo(f"n_cases:            {result.n_cases}")
    click.echo(f"n_dropped:          {result.n_dropped}")
    if result.dropped_case_ids:
        click.echo(f"dropped_case_ids:   {result.dropped_case_ids}")
    click.echo(f"rank_rho (PRIMARY): {result.rank_rho}")
    click.echo(f"direction_accuracy: {result.direction_accuracy}")
    click.echo(f"dir_delta_vs_flat:  {result.direction_delta_vs_flat}")
    click.echo(f"dir_delta_ci:       {result.direction_delta_ci}")
    for b in result.baselines:
        click.echo(f"baseline[{b.name}]: dir_acc={b.direction_accuracy} rank_rho={b.rank_rho}")
    click.echo(f"VOID:               {result.void}")
    if result.void_reason:
        click.echo(f"void_reason:        {result.void_reason}")
    click.echo("")

    cert = result.certificate
    if cert is not None:
        click.echo("== Null-integrity certificate (§4) ==")
        click.echo(f"certifying:         {cert.certifying}")
        click.echo("structurally_blinded: True (predictor reads only capability+hypothesis)")
        click.echo(f"passed:             {cert.passed}")
        click.echo(f"observed_rank_rho:  {cert.observed_rank_rho}")
        click.echo(f"rank_rho_p_value:   {cert.rank_rho_p_value}")
        click.echo(f"direction_p_value:  {cert.direction_accuracy_p_value}")
        click.echo(f"marginal_chance:    {cert.marginal_chance_accuracy}")
        click.echo(f"underpowered:       {cert.underpowered}")
        if cert.caveat:
            click.echo(f"caveat:             {cert.caveat}")
        click.echo(f"integrity_hash:     {cert.integrity_hash}")
        click.echo("")

    # ── 5. Stratified honesty table (by source). ──
    table = stratify(result, by_source, stratifier_name="source")
    click.echo(render(table))


# ── Hillstrom directional-uplift benchmark (#222 PR-B) ────────────────────────


def _hillstrom_hypothesis_builder(metric_name: str):
    """Build the Hillstrom metric `hypothesis_builder` for a scorable metric.

    Mirrors `benchmark_runner._ctr_hypothesis_for_case` but for the e-mail-uplift
    metrics. `conversion` (the v1 primary) needs the full conversion template
    (`conversion_action` + `conversion_action_label` + `decision_point`); `visit`
    needs only `decision_point` (the touchpoint moment). The builder takes the
    case's hypothesis verbatim, forces the metric + its required template fields,
    and RE-VALIDATES via `Hypothesis.model_validate` (not `model_copy`, which would
    skip the registry's required-field check). It reads ONLY `case.hypothesis` —
    `case.ground_truth` is never touched (structural blindness).
    """
    from sidira_simulator.schemas.simulation import Hypothesis

    # The on-screen decision moment is ARM-NEUTRAL (it must not name the men's vs
    # women's campaign, or the control arm would be exposed to treatment copy).
    decision_point = "the customer is reading the promotional e-mail in their inbox"

    def _build(case):
        data = case.hypothesis.model_dump()
        if metric_name == "conversion":
            data.update(
                {
                    "metric_name": "conversion",
                    "conversion_action": "click through the e-mail and complete a purchase",
                    "conversion_action_label": "buy from the store",
                    "decision_point": decision_point,
                }
            )
        elif metric_name == "visit":
            data.update(
                {
                    "metric_name": "visit",
                    "conversion_action_label": "go to the store site",
                    "decision_point": decision_point,
                }
            )
        else:  # pragma: no cover - guarded by the CLI choice list
            raise click.ClickException(
                f"unsupported Hillstrom metric {metric_name!r}; v1 scores conversion / visit"
            )
        return Hypothesis.model_validate(data)

    return _build


@cli.command("benchmark-hillstrom")
@click.option(
    "--csv-path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Path to a pre-downloaded Hillstrom RCT CSV (fetch with hillstrom_archive).",
)
@click.option(
    "--metric",
    type=click.Choice(["conversion", "visit"]),
    default="conversion",
    help="Scored metric (v1: conversion [primary] or visit). Spend is out of scope.",
)
@click.option(
    "--by-segment/--by-arm",
    "use_segments",
    default=False,
    help="Score per heterogeneity SEGMENT (endpoint #3) instead of per ARM (#1/#2).",
)
@click.option("--model-id", default=None, help="LLM model id to drive the engine.")
@click.option(
    "--population-size", default=10, type=int, help="Agents per arm (engine population_size)."
)
@click.option(
    "--max-agents", default=None, type=int, help="Bounded pilot: hard cap on agents per arm."
)
@click.option("--seed", default=0, type=int, help="Base seed (per-case + null/bootstrap RNG).")
@click.option("--n-permutations", default=1000, type=int, help="Null-integrity label permutations.")
@click.option(
    "--chunk-size",
    default=None,
    type=int,
    help="Run cases in chunks of this size (resumable). None = one chunk.",
)
@click.option(
    "--checkpoint-path",
    default=None,
    type=click.Path(dir_okay=False),
    help="Bind-mount JSON checkpoint of {case_id: prediction}; resumes across redeploy (PLAN §4).",
)
def benchmark_hillstrom(
    csv_path: str,
    metric: str,
    use_segments: bool,
    model_id: str | None,
    population_size: int,
    max_agents: int | None,
    seed: int,
    n_permutations: int,
    chunk_size: int | None,
    checkpoint_path: str | None,
) -> None:
    """Run the Hillstrom email-uplift DIRECTIONAL benchmark vs the LIVE engine (#222).

    End-to-end: load a local Hillstrom RCT CSV → adapt to BenchmarkCases (per arm,
    or per heterogeneity segment with --by-segment) → load the REAL v1.1 Hillstrom
    persona panel → score the live engine as the blind predictor for `--metric`
    (conversion primary, or visit) → emit the run result, the stratified honesty
    table (by arm or by segment), the null-integrity certificate, and the
    pre-registration metadata.

    GATED live path: builds the real SimulationRunner and needs live LLM keys; it
    refuses under pytest / CI. Use --population-size / --max-agents to keep a first
    run small. --chunk-size + --checkpoint-path make it RESUMABLE across redeploy
    (PLAN §4): predictions are checkpointed to a bind-mount JSON and a restarted
    run skips already-scored cases. Honest output: rank-ρ is PRIMARY; the
    by-segment endpoint (#3) is the only non-trivially-guessable claim.
    """
    import json
    from pathlib import Path

    from sidira_simulator.adapters.hillstrom_panel_loader import (
        hillstrom_panel_registration,
        load_hillstrom_panel,
    )
    from sidira_simulator.services.benchmark_honesty import (
        by_arm,
        by_segment,
        render,
        stratify,
    )
    from sidira_simulator.services.benchmark_runner import score_with_engine
    from sidira_simulator.services.hillstrom_adapter import (
        hillstrom_rows_to_cases,
        hillstrom_segment_cases,
    )
    from sidira_simulator.services.hillstrom_archive import load_hillstrom_csv

    # ── 1. Load + adapt the RCT into benchmark cases. ──
    rows, summary = load_hillstrom_csv(csv_path)
    if not rows:
        raise click.ClickException(f"no Hillstrom rows loaded from {csv_path}")
    if use_segments:
        cases = hillstrom_segment_cases(rows, metric_name=metric, seed=seed)
    else:
        cases = hillstrom_rows_to_cases(rows, metric_name=metric, seed=seed)

    # ── 2. Pre-registration metadata (panel + run config). ──
    registration = hillstrom_panel_registration()
    panel = load_hillstrom_panel()

    click.echo("== Pre-registration / run config ==")
    click.echo(f"panel_id:           {registration.panel_id}")
    click.echo(f"panel_version:      {registration.version}")
    click.echo(f"panel_persona_n:    {registration.persona_count}")
    click.echo(f"panel_schema:       {registration.schema_version}")
    click.echo(f"panel_synthetic:    {registration.is_synthetic_generic}")
    click.echo(f"individual_row_cap: {registration.is_individual_row_capable}")
    click.echo("primary_endpoint:   rank_rho (§5)")
    click.echo(f"metric:             {metric}")
    click.echo(f"stratifier:         {'segment (endpoint #3)' if use_segments else 'arm (#1/#2)'}")
    click.echo(f"model_id:           {model_id}")
    click.echo(f"seed:               {seed}")
    click.echo(f"population_size:    {population_size}")
    click.echo(f"max_agents:         {max_agents}")
    click.echo(f"rows_kept:          {summary.rows_kept}")
    click.echo(f"cases:              {len(cases)}")
    click.echo(f"chunk_size:         {chunk_size}")
    click.echo(f"checkpoint_path:    {checkpoint_path}")
    click.echo("")

    # ── 3. Resumable checkpoint: load any prior predictions from the bind-mount. ──
    # The checkpoint is keyed to the FULL run configuration, not just case_ids:
    # predictions depend on seed / model_id / population_size / max_agents / metric
    # (none of which are encoded in a Hillstrom case_id), so reusing a checkpoint
    # after changing ANY of them would silently serve stale predictions for a
    # different config. We store the config in the file and REFUSE to resume on a
    # mismatch — a config change forces a fresh run rather than a quiet wrong answer.
    # The panel version is part of the run config: predictions depend on the
    # persona_pack the engine ran against, so a checkpoint written before the
    # committed pack (or the subpack mapping) changed must NOT be silently reused —
    # mixing old-panel and new-panel predictions in one result is invalid.
    run_config = {
        "metric": metric,
        "seed": seed,
        "model_id": model_id,
        "population_size": population_size,
        "max_agents": max_agents,
        "use_segments": use_segments,
        "panel_version": registration.version,
    }
    prediction_cache: dict[str, float] = {}
    ckpt = Path(checkpoint_path) if checkpoint_path else None
    if ckpt is not None and ckpt.exists():
        stored = json.loads(ckpt.read_text())
        stored_config = stored.get("run_config")
        if stored_config != run_config:
            raise click.ClickException(
                f"checkpoint {ckpt} was written for a DIFFERENT run config "
                f"({stored_config}) than this run ({run_config}); its cached "
                "predictions would be stale. Use a fresh --checkpoint-path or "
                "delete the stale file."
            )
        prediction_cache = {str(k): float(v) for k, v in (stored.get("predictions") or {}).items()}
        click.echo(f"resumed {len(prediction_cache)} cached prediction(s) from {ckpt}")

    def _checkpoint() -> None:
        if ckpt is not None:
            ckpt.parent.mkdir(parents=True, exist_ok=True)
            ckpt.write_text(
                json.dumps(
                    {"run_config": run_config, "predictions": prediction_cache},
                    indent=2,
                    sort_keys=True,
                )
            )

    # ── 4. Run the live engine as the blind predictor (GATED), chunked + resumable. ──
    #
    # AUDIENCE CONDITIONING (the validity crux of endpoint #3). In --by-segment
    # mode each segment's cases MUST run against an audience CONDITIONED on that
    # stratum — else every segment case for an arm reuses the identical full panel
    # + identical stimulus and the blind engine cannot tell mens_history from
    # womens_history (its predictions would be seed noise, not heterogeneous
    # response). So we group the cases by their per-case panel: arm mode uses the
    # full panel for everything; segment mode uses a stratum sub-pack per group.
    #
    # We WARM the prediction_cache by running each panel-group separately (the
    # engine prediction is structurally determined by (case, panel)); the FINAL
    # score_with_engine over ALL cases then computes the null-cert + rank-ρ on the
    # full set as all cache hits, so the cert reads the segment-conditioned
    # predictions, not a single-panel re-run.
    panel_groups: list[tuple[str, object, list]] = []  # (stratum, panel, cases)
    if use_segments:
        from sidira_simulator.adapters.hillstrom_panel_loader import hillstrom_segment_subpack

        by_stratum: dict[str, list] = {}
        for c in cases:
            stratum = c.case_id.split(":")[3]
            by_stratum.setdefault(stratum, []).append(c)
        for stratum, group in by_stratum.items():
            subpack = hillstrom_segment_subpack(panel, stratum)
            click.echo(
                f"segment {stratum}: {len(group)} case(s) conditioned on "
                f"{len(subpack.personas)} persona(s) → {subpack.version}"
            )
            panel_groups.append((stratum, subpack, group))
    else:
        panel_groups.append(("__all__", panel, list(cases)))

    def _warm(group_cases: list, group_panel) -> None:
        """Warm the shared cache for one panel-group, optionally in chunks."""
        step = chunk_size if (chunk_size and chunk_size > 0) else len(group_cases) or 1
        for start in range(0, len(group_cases), step):
            chunk = group_cases[start : start + step]
            score_with_engine(
                chunk,
                persona_pack=group_panel,
                customer_id="benchmark",
                model_id=model_id,
                population_size=population_size,
                max_agents=max_agents,
                seed=seed,
                n_permutations=1,  # warm-up only; the real cert is the final full run
                metric_name=metric,
                hypothesis_builder=_hillstrom_hypothesis_builder(metric),
                prediction_cache=prediction_cache,
            )
            _checkpoint()

    for _stratum, group_panel, group_cases in panel_groups:
        _warm(group_cases, group_panel)

    # CONDITIONING INTEGRITY (segment mode). The final full-set run below treats a
    # cache MISS as a fresh engine call against the FULL panel — which for a
    # segment case would score it against the WRONG (undifferentiated) audience and
    # silently contaminate endpoint #3. So in --by-segment mode every case MUST be
    # in the cache after warm-up; if a warm-up dropped one (engine failure), FAIL
    # LOUD rather than let the final run recompute it on the full panel.
    if use_segments:
        missing = [c.case_id for c in cases if c.case_id not in prediction_cache]
        if missing:
            raise click.ClickException(
                "segment warm-up failed to score "
                f"{len(missing)} case(s) against their conditioned sub-panel "
                f"({missing[:5]}{'…' if len(missing) > 5 else ''}); refusing the "
                "final run because a cache miss would re-score them against the "
                "full panel and invalidate the heterogeneity endpoint. Re-run "
                "(the bind-mount checkpoint resumes the scored cases)."
            )

    # Final scoring over ALL cases. Every prediction is already cached (warmed
    # against the correct per-segment panel), so the panel passed here only labels
    # the run; the cached, segment-conditioned predictions are what get scored.
    result = score_with_engine(
        cases,
        persona_pack=panel,
        customer_id="benchmark",
        model_id=model_id,
        population_size=population_size,
        max_agents=max_agents,
        seed=seed,
        n_permutations=n_permutations,
        metric_name=metric,
        hypothesis_builder=_hillstrom_hypothesis_builder(metric),
        prediction_cache=prediction_cache,
    )
    _checkpoint()

    # ── 5. Emit the run result + null certificate. ──
    click.echo("== Blind-eval result ==")
    click.echo(f"n_cases:            {result.n_cases}")
    click.echo(f"n_dropped:          {result.n_dropped}")
    if result.dropped_case_ids:
        click.echo(f"dropped_case_ids:   {result.dropped_case_ids}")
    click.echo(f"rank_rho (PRIMARY): {result.rank_rho}")
    click.echo(f"direction_accuracy: {result.direction_accuracy}")
    click.echo(f"VOID:               {result.void}")
    if result.void_reason:
        click.echo(f"void_reason:        {result.void_reason}")
    click.echo("")

    cert = result.certificate
    if cert is not None:
        click.echo("== Null-integrity certificate (§4) ==")
        click.echo(f"passed:             {cert.passed}")
        click.echo(f"observed_rank_rho:  {cert.observed_rank_rho}")
        click.echo(f"rank_rho_p_value:   {cert.rank_rho_p_value}")
        click.echo(f"underpowered:       {cert.underpowered}")
        if cert.caveat:
            click.echo(f"caveat:             {cert.caveat}")
        click.echo("")

    # ── 6. Stratified honesty table (by arm, or by segment for endpoint #3). ──
    if use_segments:
        table = stratify(result, by_segment, stratifier_name="segment")
    else:
        table = stratify(result, by_arm, stratifier_name="arm")
    click.echo(render(table))


# ── Cookie Cats gate-move benchmark (in-scope product-change directional test) ──


# The engine's retention metric returns metric_name="retention" (the in-scope
# deliberative-return class). The Cookie Cats `--metric` flag selects which DATA
# column anchors ground truth (retention_7 primary / retention_1 secondary) and
# how the post-experience moment is phrased; both score through the engine's
# single `retention` metric. This is the engine metric_name passed to the scorer.
_COOKIECATS_ENGINE_METRIC = "retention"


def _cookiecats_hypothesis_builder(metric_name: str):
    """Build the Cookie Cats retention `hypothesis_builder` for a day-window.

    Mirrors `_hillstrom_hypothesis_builder` but for the gate-move retention
    metrics. `metric_name` is the DATA-layer selector (`retention_7` /
    `retention_1`); the engine metric is always `retention` (which requires only
    `decision_point`). The builder takes the case's hypothesis verbatim, forces
    metric_name="retention" + a day-windowed decision_point, and RE-VALIDATES via
    `Hypothesis.model_validate`. It reads ONLY `case.hypothesis` —
    `case.ground_truth` is never touched (structural blindness).
    """
    from sidira_simulator.schemas.simulation import Hypothesis

    if metric_name == "retention_7":
        horizon = "over the next 7 days after installing the game"
    elif metric_name == "retention_1":
        horizon = "the day after installing the game"
    else:  # pragma: no cover - guarded by the CLI choice list
        raise click.ClickException(
            f"unsupported Cookie Cats metric {metric_name!r}; v1 scores "
            "retention_7 / retention_1"
        )
    # The post-experience moment is GATE-NEUTRAL (it must not name which gate
    # level the player saw, or the control arm would be exposed to treatment copy).
    decision_point = f"you just installed the game and played your first session; {horizon}"

    def _build(case):
        data = case.hypothesis.model_dump()
        data.update(
            {
                "metric_name": _COOKIECATS_ENGINE_METRIC,
                "conversion_action_label": "come back and keep playing",
                "decision_point": decision_point,
            }
        )
        return Hypothesis.model_validate(data)

    return _build


@cli.command("benchmark-cookiecats")
@click.option(
    "--csv-path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Path to a pre-downloaded Cookie Cats CSV (fetch with cookiecats_archive).",
)
@click.option(
    "--metric",
    type=click.Choice(["retention_7", "retention_1"]),
    default="retention_7",
    help="Scored data outcome (v1: retention_7 [primary] or retention_1 [secondary]).",
)
@click.option(
    "--by-segment/--by-arm",
    "use_segments",
    default=False,
    help=(
        "Score per engagement SEGMENT (>=8 cases, DESCRIPTIVE/non-causal: "
        "sum_gamerounds is post-treatment) instead of the clean single A/B (--by-arm)."
    ),
)
@click.option("--model-id", default=None, help="LLM model id to drive the engine.")
@click.option(
    "--population-size", default=10, type=int, help="Agents per arm (engine population_size)."
)
@click.option(
    "--max-agents", default=None, type=int, help="Bounded pilot: hard cap on agents per arm."
)
@click.option("--seed", default=0, type=int, help="Base seed (per-case + null/bootstrap RNG).")
@click.option("--n-permutations", default=1000, type=int, help="Null-integrity label permutations.")
@click.option(
    "--chunk-size",
    default=None,
    type=int,
    help="Run cases in chunks of this size (resumable). None = one chunk.",
)
@click.option(
    "--checkpoint-path",
    default=None,
    type=click.Path(dir_okay=False),
    help="Bind-mount JSON checkpoint of {case_id: prediction}; resumes across redeploy.",
)
def benchmark_cookiecats(
    csv_path: str,
    metric: str,
    use_segments: bool,
    model_id: str | None,
    population_size: int,
    max_agents: int | None,
    seed: int,
    n_permutations: int,
    chunk_size: int | None,
    checkpoint_path: str | None,
) -> None:
    """Run the Cookie Cats gate-move DIRECTIONAL benchmark vs the LIVE engine.

    The in-scope mirror of `benchmark-hillstrom`: the product change is moving the
    first progress gate from level 30 to level 40 — a deliberative reaction to a
    PRODUCT change, the class Sidira actually sells. The real RCT's COUNTER-
    INTUITIVE ground truth is that gate_30 (the earlier gate) OUTPERFORMS gate_40
    on 7-day retention, so a sim that just parrots priors gets the SIGN wrong.

    End-to-end: load a local Cookie Cats CSV → adapt to BenchmarkCases (one A/B,
    or >=8 engagement-octile cases with --by-segment) → load the v1.1 Cookie Cats
    engagement panel → score the live engine as the blind predictor for the
    selected retention horizon (through the engine `retention` metric) → emit the
    run result, the stratified honesty table, the null-integrity certificate, and
    the pre-registration metadata.

    GATED live path: builds the real SimulationRunner and needs live LLM keys; it
    refuses under pytest / CI. --chunk-size + --checkpoint-path make it RESUMABLE.

    HONESTY CAVEAT: the gate-timing → retention effect is PARTLY behavioral /
    sub-deliberative, so introspective agent simulation may get it wrong too — this
    is a HARD test, not a guaranteed positive (see PREREG_COOKIECATS.json).
    """
    import json
    from pathlib import Path

    from sidira_simulator.adapters.cookiecats_panel_loader import (
        cookiecats_panel_registration,
        load_cookiecats_panel,
    )
    from sidira_simulator.services.benchmark_honesty import (
        by_engagement,
        by_source,
        render,
        stratify,
    )
    from sidira_simulator.services.benchmark_runner import score_with_engine
    from sidira_simulator.services.cookiecats_adapter import (
        cookiecats_rows_to_cases,
        cookiecats_segment_cases,
    )
    from sidira_simulator.services.cookiecats_archive import load_cookiecats_csv

    # ── 1. Load + adapt the A/B into benchmark cases. ──
    rows, summary = load_cookiecats_csv(csv_path)
    if not rows:
        raise click.ClickException(f"no Cookie Cats rows loaded from {csv_path}")
    if use_segments:
        cases = cookiecats_segment_cases(rows, metric_name=metric, seed=seed)
    else:
        cases = cookiecats_rows_to_cases(rows, metric_name=metric, seed=seed)

    # ── 2. Pre-registration metadata (panel + run config). ──
    registration = cookiecats_panel_registration()
    panel = load_cookiecats_panel()

    click.echo("== Pre-registration / run config ==")
    click.echo(f"panel_id:           {registration.panel_id}")
    click.echo(f"panel_version:      {registration.version}")
    click.echo(f"panel_persona_n:    {registration.persona_count}")
    click.echo(f"panel_schema:       {registration.schema_version}")
    click.echo(f"panel_synthetic:    {registration.is_synthetic_generic}")
    click.echo(f"individual_row_cap: {registration.is_individual_row_capable}")
    click.echo("primary_endpoint:   rank_rho")
    click.echo(f"metric:             {metric}")
    click.echo(f"engine_metric:      {_COOKIECATS_ENGINE_METRIC}")
    click.echo(
        "stratifier:         "
        + (
            "engagement segment (>=8, DESCRIPTIVE/non-causal: post-treatment covariate)"
            if use_segments
            else "single A/B (clean causal endpoint)"
        )
    )
    click.echo(f"model_id:           {model_id}")
    click.echo(f"seed:               {seed}")
    click.echo(f"population_size:    {population_size}")
    click.echo(f"max_agents:         {max_agents}")
    click.echo(f"rows_kept:          {summary.rows_kept}")
    click.echo(f"cases:              {len(cases)}")
    click.echo(f"chunk_size:         {chunk_size}")
    click.echo(f"checkpoint_path:    {checkpoint_path}")
    click.echo("")

    # ── 3. Resumable checkpoint: load any prior predictions from the bind-mount. ──
    # Keyed to the FULL run configuration (incl. panel_version): a config change
    # forces a fresh run rather than silently serving stale predictions.
    run_config = {
        "metric": metric,
        "seed": seed,
        "model_id": model_id,
        "population_size": population_size,
        "max_agents": max_agents,
        "use_segments": use_segments,
        "panel_version": registration.version,
    }
    prediction_cache: dict[str, float] = {}
    ckpt = Path(checkpoint_path) if checkpoint_path else None
    if ckpt is not None and ckpt.exists():
        stored = json.loads(ckpt.read_text())
        stored_config = stored.get("run_config")
        if stored_config != run_config:
            raise click.ClickException(
                f"checkpoint {ckpt} was written for a DIFFERENT run config "
                f"({stored_config}) than this run ({run_config}); its cached "
                "predictions would be stale. Use a fresh --checkpoint-path or "
                "delete the stale file."
            )
        prediction_cache = {str(k): float(v) for k, v in (stored.get("predictions") or {}).items()}
        click.echo(f"resumed {len(prediction_cache)} cached prediction(s) from {ckpt}")

    def _checkpoint() -> None:
        if ckpt is not None:
            ckpt.parent.mkdir(parents=True, exist_ok=True)
            ckpt.write_text(
                json.dumps(
                    {"run_config": run_config, "predictions": prediction_cache},
                    indent=2,
                    sort_keys=True,
                )
            )

    # ── 4. Run the live engine as the blind predictor (GATED), chunked + resumable. ──
    #
    # AUDIENCE CONDITIONING (the validity crux of the heterogeneity endpoint). In
    # --by-segment mode each engagement octile's case MUST run against an audience
    # CONDITIONED on that engagement tier — else every octile case reuses the
    # identical full panel + identical stimulus and the blind engine cannot tell
    # one engagement band from another. So we group the cases by their per-case
    # panel: A/B mode uses the full panel; segment mode uses an engagement sub-pack
    # per group. We WARM the prediction_cache per panel-group, then the FINAL
    # score_with_engine over ALL cases computes the cert/rank-ρ as cache hits.
    builder = _cookiecats_hypothesis_builder(metric)
    panel_groups: list[tuple[str, object, list]] = []  # (stratum, panel, cases)
    if use_segments:
        from sidira_simulator.adapters.cookiecats_panel_loader import (
            cookiecats_segment_subpack,
        )

        by_stratum: dict[str, list] = {}
        for c in cases:
            stratum = c.case_id.split(":")[3]
            by_stratum.setdefault(stratum, []).append(c)
        for stratum, group in by_stratum.items():
            subpack = cookiecats_segment_subpack(panel, stratum)
            click.echo(
                f"segment {stratum}: {len(group)} case(s) conditioned on "
                f"{len(subpack.personas)} persona(s) → {subpack.version}"
            )
            panel_groups.append((stratum, subpack, group))
    else:
        panel_groups.append(("__all__", panel, list(cases)))

    def _warm(group_cases: list, group_panel) -> None:
        step = chunk_size if (chunk_size and chunk_size > 0) else len(group_cases) or 1
        for start in range(0, len(group_cases), step):
            chunk = group_cases[start : start + step]
            score_with_engine(
                chunk,
                persona_pack=group_panel,
                customer_id="benchmark",
                model_id=model_id,
                population_size=population_size,
                max_agents=max_agents,
                seed=seed,
                n_permutations=1,  # warm-up only; the real cert is the final full run
                metric_name=_COOKIECATS_ENGINE_METRIC,
                hypothesis_builder=builder,
                prediction_cache=prediction_cache,
            )
            _checkpoint()

    for _stratum, group_panel, group_cases in panel_groups:
        _warm(group_cases, group_panel)

    # CONDITIONING INTEGRITY (segment mode). A cache MISS on the final full-set run
    # would re-score a segment case against the FULL panel (wrong audience). So in
    # --by-segment mode every case MUST be in the cache after warm-up; FAIL LOUD
    # otherwise rather than silently contaminate the heterogeneity endpoint.
    if use_segments:
        missing = [c.case_id for c in cases if c.case_id not in prediction_cache]
        if missing:
            raise click.ClickException(
                "segment warm-up failed to score "
                f"{len(missing)} case(s) against their conditioned sub-panel "
                f"({missing[:5]}{'…' if len(missing) > 5 else ''}); refusing the "
                "final run because a cache miss would re-score them against the "
                "full panel and invalidate the heterogeneity endpoint. Re-run "
                "(the bind-mount checkpoint resumes the scored cases)."
            )

    # Final scoring over ALL cases. Every prediction is already cached (warmed
    # against the correct per-segment panel), so the panel passed here only labels
    # the run; the cached, segment-conditioned predictions are what get scored.
    result = score_with_engine(
        cases,
        persona_pack=panel,
        customer_id="benchmark",
        model_id=model_id,
        population_size=population_size,
        max_agents=max_agents,
        seed=seed,
        n_permutations=n_permutations,
        metric_name=_COOKIECATS_ENGINE_METRIC,
        hypothesis_builder=builder,
        prediction_cache=prediction_cache,
    )
    _checkpoint()

    # ── 5. Emit the run result + null certificate. ──
    click.echo("== Blind-eval result ==")
    click.echo(f"n_cases:            {result.n_cases}")
    click.echo(f"n_dropped:          {result.n_dropped}")
    if result.dropped_case_ids:
        click.echo(f"dropped_case_ids:   {result.dropped_case_ids}")
    click.echo(f"rank_rho (PRIMARY): {result.rank_rho}")
    click.echo(f"direction_accuracy: {result.direction_accuracy}")
    click.echo(f"VOID:               {result.void}")
    if result.void_reason:
        click.echo(f"void_reason:        {result.void_reason}")
    click.echo("")

    cert = result.certificate
    if cert is not None:
        click.echo("== Null-integrity certificate ==")
        click.echo(f"passed:             {cert.passed}")
        click.echo(f"observed_rank_rho:  {cert.observed_rank_rho}")
        click.echo(f"rank_rho_p_value:   {cert.rank_rho_p_value}")
        click.echo(f"underpowered:       {cert.underpowered}")
        if cert.caveat:
            click.echo(f"caveat:             {cert.caveat}")
        click.echo("")

    # ── 6. Stratified honesty table (by engagement segment, or by source for A/B). ──
    if use_segments:
        table = stratify(result, by_engagement, stratifier_name="engagement")
    else:
        table = stratify(result, by_source, stratifier_name="source")
    click.echo(render(table))


if __name__ == "__main__":
    cli()
