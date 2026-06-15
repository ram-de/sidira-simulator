"""Customer credential encryption.

Envelope encryption pattern:
- A per-customer Data Encryption Key (DEK) is generated, used to encrypt the
  credential blob, then itself encrypted with a Key Encryption Key (KEK) held
  in KMS (AWS KMS / Cloudflare KMS / similar).
- Only the encrypted DEK + encrypted blob are persisted to Postgres.
- At decrypt time, KMS is called to unwrap the DEK; the DEK then unwraps the
  blob in memory. KMS access is logged for audit.

Modes (``SIDIRA_CRED_MODE`` / legacy ``PYTHIA_CRED_MODE``):
- ``local`` (default): a local-symmetric-key fallback (env var
  ``SIDIRA_LOCAL_CRED_KEY``, base64 AESGCM key) for dev only.
- ``kms``: production envelope encryption. A fresh 256-bit DEK is minted per
  blob via ``KMS:GenerateDataKey``; the plaintext DEK encrypts the credential
  blob (AESGCM) and is then discarded, and only the KMS-wrapped DEK is
  persisted (``wrapped_dek``). At decrypt time ``KMS:Decrypt`` unwraps the DEK
  in memory. The CMK is referenced by id/alias via ``SIDIRA_KMS_KEY_ID``;
  **key rotation is transparent** — KMS selects the right backing key from the
  wrapped-DEK ciphertext, so rotating (or auto-rotating) the CMK never strands
  previously-written blobs.

Every write (:func:`encrypt`) and read (:func:`decrypt`) emits a structured
audit log entry (``customer_id``, ``key_id``, ``action``, ``at`` timestamp) so
credential access is traceable. Pass ``customer_id`` to attribute the access.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import structlog

from sidira_simulator.services.runtime_config import resolve_sidira_env

#: Dedicated channel so credential access can be shipped to an audit sink
#: independently of application logs.
_audit_log = structlog.get_logger("sidira.credentials.audit")


class CredentialError(RuntimeError):
    """Encryption / decryption failure or misconfiguration."""


@dataclass
class EncryptedBlob:
    """Persisted alongside the connection row in Postgres."""

    kek_id: str
    ciphertext: bytes
    nonce: bytes
    wrapped_dek: bytes | None = None  # KMS-only; None for local-key mode


def encrypt(
    plaintext: dict[str, Any],
    *,
    customer_id: str | None = None,
    aad: bytes | None = None,
) -> EncryptedBlob:
    """Encrypt a credentials dict for at-rest storage.

    ``customer_id`` is optional and used only to attribute the audit-log entry;
    it is never persisted in the blob.

    ``aad`` (associated data) cryptographically binds the blob to a context
    (e.g. ``customer_id:connection_id``). When set, the same ``aad`` MUST be
    supplied to :func:`decrypt` or decryption fails — this prevents a blob
    copied to another tenant/row from decrypting. ``aad=None`` preserves the
    original behavior (so existing crawl-credential blobs keep decrypting).
    """
    mode = resolve_sidira_env("CRED_MODE", "local")
    if mode == "local":
        blob = _encrypt_local(plaintext, aad=aad)
    elif mode == "kms":
        blob = _encrypt_kms(plaintext, aad=aad)
    else:
        raise CredentialError(f"Unknown SIDIRA_CRED_MODE/PYTHIA_CRED_MODE: {mode}")
    _audit("encrypt", blob.kek_id, customer_id)
    return blob


def decrypt(
    blob: EncryptedBlob,
    *,
    customer_id: str | None = None,
    aad: bytes | None = None,
) -> dict[str, Any]:
    """Decrypt a previously-encrypted credentials dict. In-memory only.

    ``customer_id`` is optional and used only to attribute the audit-log entry.

    ``aad`` must match the value passed to :func:`encrypt`; a mismatch (or a
    blob written under a different binding) raises ``CredentialError``.
    """
    if blob.kek_id == "local":
        plaintext = _decrypt_local(blob, aad=aad)
    elif blob.kek_id.startswith("kms:"):
        plaintext = _decrypt_kms(blob, aad=aad)
    else:
        raise CredentialError(f"Unknown kek_id: {blob.kek_id}")
    _audit("decrypt", blob.kek_id, customer_id)
    return plaintext


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


def _encrypt_local(plaintext: dict[str, Any], *, aad: bytes | None = None) -> EncryptedBlob:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # type: ignore[import-not-found]

    key = _local_key()
    aes = AESGCM(key)
    nonce = os.urandom(12)
    data = json.dumps(plaintext).encode("utf-8")
    ct = aes.encrypt(nonce, data, associated_data=aad)
    return EncryptedBlob(kek_id="local", ciphertext=ct, nonce=nonce)


def _decrypt_local(blob: EncryptedBlob, *, aad: bytes | None = None) -> dict[str, Any]:
    from cryptography.exceptions import InvalidTag  # type: ignore[import-not-found]
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # type: ignore[import-not-found]

    aes = AESGCM(_local_key())
    try:
        pt = aes.decrypt(blob.nonce, blob.ciphertext, associated_data=aad)
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


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


def _audit(action: str, kek_id: str, customer_id: str | None) -> None:
    """Emit one structured audit entry per credential access.

    Records ``action`` (encrypt/decrypt), ``key_id`` (the KEK that wrapped the
    blob — ``local`` or ``kms:<cmk>``), the attributed ``customer_id``, and an
    ISO-8601 ``at`` timestamp. Never raises — auditing must not break the
    credential path.
    """
    try:
        _audit_log.info(
            "credential_access",
            action=action,
            key_id=kek_id,
            customer_id=customer_id,
            at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception:  # pragma: no cover - logging must never break encryption
        pass


# ---------------------------------------------------------------------------
# KMS envelope encryption (production)
# ---------------------------------------------------------------------------


def _kms_key_id() -> str:
    key_id = resolve_sidira_env("KMS_KEY_ID")
    if not key_id:
        raise CredentialError(
            "SIDIRA_KMS_KEY_ID not set — required for SIDIRA_CRED_MODE=kms "
            "(a KMS key id, ARN, or alias/<name>)"
        )
    return key_id


def _kms_client():  # type: ignore[no-untyped-def]
    """Build a KMS client. Region comes from the standard AWS env
    (``AWS_REGION`` / ``AWS_DEFAULT_REGION``) or instance metadata."""
    try:
        import boto3  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - boto3 is a runtime dep
        raise CredentialError("boto3 is required for SIDIRA_CRED_MODE=kms") from exc
    return boto3.client("kms")


def _encrypt_kms(plaintext: dict[str, Any], *, aad: bytes | None = None) -> EncryptedBlob:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # type: ignore[import-not-found]

    key_id = _kms_key_id()
    client = _kms_client()
    # KMS requires the same EncryptionContext on GenerateDataKey + Decrypt; bind
    # the aad into it (and into the AESGCM layer) so the wrapped DEK is itself
    # scoped to the context. None preserves the original (unscoped) behavior.
    gdk_kwargs: dict[str, Any] = {"KeyId": key_id, "KeySpec": "AES_256"}
    if aad is not None:
        gdk_kwargs["EncryptionContext"] = {"aad": aad.hex()}
    try:
        resp = client.generate_data_key(**gdk_kwargs)
    except Exception as exc:
        # botocore ClientError (auth / key disabled / throttling) — surface as a
        # controlled CredentialError so callers 503 rather than 500.
        raise CredentialError(f"KMS GenerateDataKey failed: {exc}") from exc
    dek = resp["Plaintext"]
    wrapped_dek = resp["CiphertextBlob"]
    try:
        nonce = os.urandom(12)
        data = json.dumps(plaintext).encode("utf-8")
        ct = AESGCM(dek).encrypt(nonce, data, associated_data=aad)
    finally:
        # Best-effort scrub of the plaintext DEK reference.
        del dek
    return EncryptedBlob(
        kek_id=f"kms:{key_id}", ciphertext=ct, nonce=nonce, wrapped_dek=wrapped_dek
    )


def _decrypt_kms(blob: EncryptedBlob, *, aad: bytes | None = None) -> dict[str, Any]:
    from cryptography.exceptions import InvalidTag  # type: ignore[import-not-found]
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # type: ignore[import-not-found]

    if not blob.wrapped_dek:
        raise CredentialError("kms blob is missing wrapped_dek")
    client = _kms_client()
    # The same EncryptionContext used on GenerateDataKey must be supplied here,
    # or KMS refuses to unwrap the DEK. None preserves the original behavior.
    decrypt_kwargs: dict[str, Any] = {"CiphertextBlob": blob.wrapped_dek}
    if aad is not None:
        decrypt_kwargs["EncryptionContext"] = {"aad": aad.hex()}
    try:
        # KMS picks the right backing key from the ciphertext, so rotation is
        # transparent and we do not pass KeyId on decrypt.
        resp = client.decrypt(**decrypt_kwargs)
    except Exception as exc:
        raise CredentialError(f"KMS Decrypt failed: {exc}") from exc
    dek = resp["Plaintext"]
    try:
        pt = AESGCM(dek).decrypt(blob.nonce, blob.ciphertext, associated_data=aad)
        return json.loads(pt.decode("utf-8"))
    except InvalidTag as exc:
        raise CredentialError(
            "cannot decrypt credentials — corrupted ciphertext or DEK mismatch"
        ) from exc
    except (ValueError, UnicodeDecodeError) as exc:
        raise CredentialError(f"decrypted credential payload is malformed: {exc}") from exc
    finally:
        del dek
