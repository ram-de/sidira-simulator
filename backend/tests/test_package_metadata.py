from pathlib import Path
import tomllib

from click.testing import CliRunner

from sidira_simulator.cli import cli


def test_backend_package_metadata_uses_sidira_names() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    metadata = tomllib.loads(pyproject.read_text())

    assert metadata["project"]["name"] == "sidira-simulator"
    assert metadata["project"]["scripts"]["sidira-simulator"] == "sidira_simulator.cli:cli"
    assert metadata["project"]["scripts"]["pythia-simulator"] == "sidira_simulator.cli:cli"
    assert metadata["tool"]["setuptools"]["packages"]["find"]["include"] == ["sidira_simulator*"]


def test_cli_serve_targets_renamed_asgi_module(monkeypatch) -> None:
    calls = []

    def fake_run(app: str, **kwargs: object) -> None:
        calls.append((app, kwargs))

    monkeypatch.setattr("sidira_simulator.cli.uvicorn.run", fake_run)

    result = CliRunner().invoke(
        cli, ["serve", "--host", "0.0.0.0", "--port", "9000", "--no-reload"]
    )

    assert result.exit_code == 0
    assert calls == [
        (
            "sidira_simulator.main:app",
            {"host": "0.0.0.0", "port": 9000, "reload": False},
        )
    ]
