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
    """Cloudflare R2 via the S3-compatible API.

    Credentials default to the canonical ``R2_*`` env vars, but every field can
    be passed explicitly so a second, differently-scoped store (e.g. the
    read-only Feature Pack reader in :func:`get_featurepack_store`) can point at
    its own bucket/keys without colliding with the general store's env.
    """

    def __init__(
        self,
        bucket: str | None = None,
        *,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
    ) -> None:
        import boto3

        self._bucket = bucket or os.environ["R2_BUCKET"]
        self._s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url or os.environ["R2_ENDPOINT_URL"],
            aws_access_key_id=access_key_id or os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=secret_access_key or os.environ["R2_SECRET_ACCESS_KEY"],
        )

    def read_text(self, key: str) -> str:
        from botocore.exceptions import ClientError

        try:
            obj = self._s3.get_object(Bucket=self._bucket, Key=key)
        except self._s3.exceptions.NoSuchKey as exc:
            raise FileNotFoundError(key) from exc
        except ClientError as exc:
            # R2's S3-compat surface can return a bare 404 as a generic
            # ClientError rather than the modeled NoSuchKey. Map a missing key to
            # FileNotFoundError so read-through fallback (FallbackArtifactStore /
            # get_featurepack_store) treats it as a miss, not a hard error. A
            # missing *bucket* or any other code still propagates — that's config,
            # not an absent artifact.
            code = exc.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404", "NotFound"):
                raise FileNotFoundError(key) from exc
            raise
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


class FallbackArtifactStore:
    """Read-through store: reads try ``primary`` first, fall back to ``secondary``
    on a miss; writes go to ``secondary``.

    This is what lets the seeded sample Feature Pack be served in prod. After
    #208, Feature Pack reads moved to the read-only R2 pack bucket
    (``get_featurepack_store``), but the sample-workspace clone can only *write*
    to the writable general store (``get_store`` — the bind-mount), since the
    pack-bucket creds are read-only. Without a fallback the clone wrote the
    feature pack where the loader never looked, so a freshly seeded tenant showed
    a persona pack but "no feature pack". Reading R2 first, bind-mount second,
    closes that gap.

    A given tenant's pack lives entirely in ONE backend — a crawled tenant only
    in R2, a seeded tenant only on the bind-mount — so a read never stitches one
    tenant's ``latest`` pointer onto another store's manifest/capability body.
    Where a tenant exists in both (a real crawl landed over an old sample clone),
    the primary wins for every key, so the live crawled pack is served whole.
    """

    def __init__(self, primary: ArtifactStore, secondary: ArtifactStore) -> None:
        self._primary = primary
        self._secondary = secondary

    def read_text(self, key: str) -> str:
        try:
            return self._primary.read_text(key)
        except FileNotFoundError:
            return self._secondary.read_text(key)

    def read_lines(self, key: str) -> list[str]:
        try:
            return self._primary.read_lines(key)
        except FileNotFoundError:
            return self._secondary.read_lines(key)

    def write_text(self, key: str, body: str) -> None:
        # The primary is read-only; the only writable backend is the secondary.
        self._secondary.write_text(key, body)

    def append_line(self, key: str, line: str) -> None:
        self._secondary.append_line(key, line)


def get_store() -> ArtifactStore:
    if os.environ.get("R2_BUCKET"):
        return R2ArtifactStore()
    root = resolve_sidira_env("LOCAL_ARTIFACTS", "local-artifacts")
    assert root is not None
    return LocalArtifactStore(root)


def get_featurepack_store() -> ArtifactStore:
    """Read store for crawler-published Feature Packs (#208).

    Prefers a dedicated R2 store configured via ``R2_PACK_*`` so a customer's
    latest pack can be served live from the crawler's bucket WITHOUT flipping
    the entire artifact layer to R2: ``get_store()`` (agent memory, feedback,
    run-state, persona-group logs, the seeded persona packs) stays on the local
    bind-mount. This is the surgical alternative to setting ``R2_BUCKET``, which
    is a global switch that would also route every *write* path to R2 and so
    demand read-write creds.

    The gate is ``R2_PACK_BUCKET``; the endpoint/keys fall back to the canonical
    ``R2_*`` vars when their pack-scoped twin is unset. With nothing configured
    (dev + the test suite) this falls back to :func:`get_store`, keeping packs
    fully local.

    When the pack bucket *is* configured the result is a
    :class:`FallbackArtifactStore` reading R2 first and the writable general
    store (:func:`get_store`) second, so a sample-workspace clone — which can
    only write to the bind-mount, not the read-only pack bucket — is still
    served. See that class for why mixing across tenants can't happen.
    """
    bucket = os.environ.get("R2_PACK_BUCKET")
    if not bucket:
        return get_store()
    pack_store = R2ArtifactStore(
        bucket=bucket,
        endpoint_url=os.environ.get("R2_PACK_ENDPOINT_URL") or os.environ.get("R2_ENDPOINT_URL"),
        access_key_id=os.environ.get("R2_PACK_ACCESS_KEY_ID")
        or os.environ.get("R2_ACCESS_KEY_ID"),
        secret_access_key=os.environ.get("R2_PACK_SECRET_ACCESS_KEY")
        or os.environ.get("R2_SECRET_ACCESS_KEY"),
    )
    return FallbackArtifactStore(primary=pack_store, secondary=get_store())
