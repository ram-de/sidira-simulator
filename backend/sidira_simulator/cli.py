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


if __name__ == "__main__":
    cli()
