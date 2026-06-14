"""Customer credential encryption.

Envelope encryption pattern:
- A per-customer Data Encryption Key (DEK) is generated, used to encrypt the
  credential blob, then itself encrypted with a Key Encryption Key (KEK) held
  in KMS (AWS KMS / Cloudflare KMS / similar).
- Only the encrypted DEK + encrypted blob are persisted to Postgres.
- At decrypt time, KMS is called to unwrap the DEK; the DEK then unwraps the
  blob in memory. KMS access is logged for audit.

MVP: a local-symmetric-key fallback (env var `SIDIRA_LOCAL_CRED_KEY`, base64
AESGCM key) for dev only. Production MUST use KMS. The KMS code path is
stubbed and intentionally raises until Phase 5 lands.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any

from sidira_simulator.services.runtime_config import resolve_sidira_env


class CredentialError(RuntimeError):
    """Encryption / decryption failure or misconfiguration."""


@dataclass
class EncryptedBlob:
    """Persisted alongside the connection row in Postgres."""

    kek_id: str
    ciphertext: bytes
    nonce: bytes
    wrapped_dek: bytes | None = None  # KMS-only; None for local-key mode


def encrypt(plaintext: dict[str, Any]) -> EncryptedBlob:
    """Encrypt a credentials dict for at-rest storage."""
    mode = resolve_sidira_env("CRED_MODE", "local")
    if mode == "local":
        return _encrypt_local(plaintext)
    if mode == "kms":
        raise NotImplementedError("Phase 5 — KMS-backed envelope encryption")
    raise CredentialError(f"Unknown SIDIRA_CRED_MODE/PYTHIA_CRED_MODE: {mode}")


def decrypt(blob: EncryptedBlob) -> dict[str, Any]:
    """Decrypt a previously-encrypted credentials dict. In-memory only."""
    if blob.kek_id == "local":
        return _decrypt_local(blob)
    if blob.kek_id.startswith("kms:"):
        raise NotImplementedError("Phase 5 — KMS-backed envelope decryption")
    raise CredentialError(f"Unknown kek_id: {blob.kek_id}")


def serialize_blob(blob: EncryptedBlob) -> dict[str, str | None]:
    """Encode an :class:`EncryptedBlob` to a JSON-safe dict for storage in a
    JSON(B) column (its byte fields are base64'd). Round-trips via
    :func:`deserialize_blob`."""
    return {
        "kek_id": blob.kek_id,
        "ciphertext": base64.b64encode(blob.ciphertext).decode("ascii"),
        "nonce": base64.b64encode(blob.nonce).decode("ascii"),
        "wrapped_dek": (
            base64.b64encode(blob.wrapped_dek).decode("ascii") if blob.wrapped_dek else None
        ),
    }


def deserialize_blob(data: dict[str, Any]) -> EncryptedBlob:
    """Reconstruct an :class:`EncryptedBlob` from :func:`serialize_blob` output."""
    try:
        return EncryptedBlob(
            kek_id=data["kek_id"],
            ciphertext=base64.b64decode(data["ciphertext"]),
            nonce=base64.b64decode(data["nonce"]),
            wrapped_dek=base64.b64decode(data["wrapped_dek"]) if data.get("wrapped_dek") else None,
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise CredentialError(f"malformed encrypted blob: {exc}") from exc


# ---------------------------------------------------------------------------
# Local-key fallback (dev only)
# ---------------------------------------------------------------------------


def _local_key() -> bytes:
    raw = resolve_sidira_env("LOCAL_CRED_KEY")
    if not raw:
        raise CredentialError(
            "SIDIRA_LOCAL_CRED_KEY not set. For dev, generate with: "
            "python -c 'import secrets,base64;print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())'"
            ". Legacy PYTHIA_LOCAL_CRED_KEY is still accepted during the rename."
        )
    try:
        key = base64.urlsafe_b64decode(raw)
    except (ValueError, TypeError) as exc:
        # binascii.Error (a ValueError subclass) on a typo'd / non-base64 key.
        # Fail closed with a controlled error so callers 503 rather than 500.
        raise CredentialError(
            "SIDIRA_LOCAL_CRED_KEY is not valid base64 — regenerate it"
        ) from exc
    if len(key) not in (16, 24, 32):
        # AESGCM only accepts 128/192/256-bit keys; a wrong length would raise a
        # bare ValueError from AESGCM(). Catch it here as a misconfiguration.
        raise CredentialError(
            f"SIDIRA_LOCAL_CRED_KEY must decode to 16, 24, or 32 bytes (got {len(key)})"
        )
    return key


def _encrypt_local(plaintext: dict[str, Any]) -> EncryptedBlob:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # type: ignore[import-not-found]

    key = _local_key()
    aes = AESGCM(key)
    nonce = os.urandom(12)
    data = json.dumps(plaintext).encode("utf-8")
    ct = aes.encrypt(nonce, data, associated_data=None)
    return EncryptedBlob(kek_id="local", ciphertext=ct, nonce=nonce)


def _decrypt_local(blob: EncryptedBlob) -> dict[str, Any]:
    from cryptography.exceptions import InvalidTag  # type: ignore[import-not-found]
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # type: ignore[import-not-found]

    aes = AESGCM(_local_key())
    try:
        pt = aes.decrypt(blob.nonce, blob.ciphertext, associated_data=None)
        return json.loads(pt.decode("utf-8"))
    except InvalidTag as exc:
        # Wrong key (e.g. SIDIRA_LOCAL_CRED_KEY rotated after the blob was
        # written) or a tampered ciphertext. Surface as a controlled
        # CredentialError so callers return a 503, not an opaque 500.
        raise CredentialError(
            "cannot decrypt credentials — key mismatch or corrupted ciphertext "
            "(was SIDIRA_LOCAL_CRED_KEY rotated? re-save the crawl setup)"
        ) from exc
    except (ValueError, UnicodeDecodeError) as exc:
        # json.loads / utf-8 decode on a corrupted-but-authentic plaintext.
        raise CredentialError(f"decrypted credential payload is malformed: {exc}") from exc
