"""Artifact store adapter — Cloudflare R2 in prod, local filesystem in dev.

Implements the ArtifactReader + ArtifactWriter protocols used by AgentMemory.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from sidira_simulator.services.runtime_config import resolve_sidira_env


class ArtifactStore(Protocol):
    def read_text(self, key: str) -> str: ...
    def read_lines(self, key: str) -> list[str]: ...
    def write_text(self, key: str, body: str) -> None: ...
    def append_line(self, key: str, line: str) -> None: ...


class LocalArtifactStore:
    """Filesystem-backed store for dev. Keys are paths under `root`."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        p = self.root / key
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def read_text(self, key: str) -> str:
        p = self._path(key)
        if not p.exists():
            raise FileNotFoundError(key)
        return p.read_text()

    def read_lines(self, key: str) -> list[str]:
        p = self._path(key)
        if not p.exists():
            raise FileNotFoundError(key)
        return p.read_text().splitlines()

    def write_text(self, key: str, body: str) -> None:
        self._path(key).write_text(body)

    def append_line(self, key: str, line: str) -> None:
        with self._path(key).open("a") as f:
            f.write(line.rstrip("\n") + "\n")


class R2ArtifactStore:
    """Cloudflare R2 via the S3-compatible API."""

    def __init__(self, bucket: str | None = None) -> None:
        import boto3

        self._bucket = bucket or os.environ["R2_BUCKET"]
        self._s3 = boto3.client(
            "s3",
            endpoint_url=os.environ["R2_ENDPOINT_URL"],
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        )

    def read_text(self, key: str) -> str:
        try:
            obj = self._s3.get_object(Bucket=self._bucket, Key=key)
        except self._s3.exceptions.NoSuchKey as exc:
            raise FileNotFoundError(key) from exc
        return obj["Body"].read().decode("utf-8")

    def read_lines(self, key: str) -> list[str]:
        return self.read_text(key).splitlines()

    def write_text(self, key: str, body: str) -> None:
        self._s3.put_object(Bucket=self._bucket, Key=key, Body=body.encode("utf-8"))

    def append_line(self, key: str, line: str) -> None:
        # R2/S3 has no native append. MVP: read-modify-write. Phase 2: switch
        # the conversation log to a per-turn-object layout to make this O(1).
        try:
            existing = self.read_text(key)
        except FileNotFoundError:
            existing = ""
        self.write_text(key, existing + line.rstrip("\n") + "\n")


def get_store() -> ArtifactStore:
    if os.environ.get("R2_BUCKET"):
        return R2ArtifactStore()
    root = resolve_sidira_env("LOCAL_ARTIFACTS", "local-artifacts")
    assert root is not None
    return LocalArtifactStore(root)
