"""FallbackArtifactStore — read primary-first, fall back to secondary, write to secondary.

Models the prod Feature Pack read path (#208 + sample-workspace fix): the
read-only R2 pack bucket is the primary, the writable bind-mount store the
secondary, so a sample-workspace clone written only to the bind-mount is still
served.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sidira_simulator.adapters.r2 import FallbackArtifactStore, LocalArtifactStore


@pytest.fixture
def stores(
    tmp_path: Path,
) -> tuple[LocalArtifactStore, LocalArtifactStore, FallbackArtifactStore]:
    primary = LocalArtifactStore(tmp_path / "primary")
    secondary = LocalArtifactStore(tmp_path / "secondary")
    return primary, secondary, FallbackArtifactStore(primary=primary, secondary=secondary)


def test_read_prefers_primary(stores) -> None:
    primary, secondary, fb = stores
    primary.write_text("k", "from-primary")
    secondary.write_text("k", "from-secondary")
    assert fb.read_text("k") == "from-primary"
    assert fb.read_lines("k") == ["from-primary"]


def test_read_falls_back_to_secondary_on_primary_miss(stores) -> None:
    _, secondary, fb = stores
    secondary.write_text("k", "line-a\nline-b")
    assert fb.read_text("k") == "line-a\nline-b"
    assert fb.read_lines("k") == ["line-a", "line-b"]


def test_read_missing_in_both_raises(stores) -> None:
    _, _, fb = stores
    with pytest.raises(FileNotFoundError):
        fb.read_text("nope")
    with pytest.raises(FileNotFoundError):
        fb.read_lines("nope")


def test_writes_go_to_secondary_only(stores) -> None:
    primary, secondary, fb = stores
    fb.write_text("w", "body")
    fb.append_line("log", "line1")
    assert secondary.read_text("w") == "body"
    assert secondary.read_lines("log") == ["line1"]
    # The primary (read-only pack bucket in prod) is never written.
    with pytest.raises(FileNotFoundError):
        primary.read_text("w")
    with pytest.raises(FileNotFoundError):
        primary.read_text("log")
