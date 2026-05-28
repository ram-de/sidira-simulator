"""CLI — `sidira-simulator serve` for local dev."""

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


if __name__ == "__main__":
    cli()
