"""Unit tests for credential envelope encryption (#21).

Covers the local-key fallback and the KMS envelope path (with a faithful fake
KMS client that models GenerateDataKey/Decrypt semantics), plus the audit-log
entry emitted on every write and read.
"""

from __future__ import annotations

import base64
import os

import pytest
from structlog.testing import capture_logs

from sidira_simulator.adapters import credentials

_LOCAL_KEY = "c2lkaXJhLXRlc3QtY3JlZC1rZXktMzJieXRlcyEhISE="  # 32 bytes, base64


@pytest.fixture
def local_mode(monkeypatch):
    monkeypatch.setenv("SIDIRA_CRED_MODE", "local")
    monkeypatch.setenv("SIDIRA_LOCAL_CRED_KEY", _LOCAL_KEY)


class _FakeKMS:
    """Models KMS envelope semantics: GenerateDataKey mints a DEK and returns it
    alongside an opaque wrapped form; Decrypt reverses the wrap. No real AWS."""

    def generate_data_key(self, KeyId, KeySpec, EncryptionContext=None):  # noqa: N803 (boto3 casing)
        assert KeySpec == "AES_256"
        dek = os.urandom(32)
        wrapped = b"wrapped:" + KeyId.encode() + b":" + base64.b64encode(dek)
        return {"Plaintext": dek, "CiphertextBlob": wrapped}

    def decrypt(self, CiphertextBlob, EncryptionContext=None):  # noqa: N803
        assert CiphertextBlob.startswith(b"wrapped:")
        dek = base64.b64decode(CiphertextBlob.rsplit(b":", 1)[1])
        return {"Plaintext": dek}


@pytest.fixture
def kms_mode(monkeypatch):
    monkeypatch.setenv("SIDIRA_CRED_MODE", "kms")
    monkeypatch.setenv("SIDIRA_KMS_KEY_ID", "alias/sidira-test")
    monkeypatch.setattr(credentials, "_kms_client", lambda: _FakeKMS())


# --- local mode ------------------------------------------------------------


def test_local_round_trip(local_mode):
    blob = credentials.encrypt({"admin": "s3cret", "member": "hunter2"})
    assert blob.kek_id == "local"
    assert blob.wrapped_dek is None
    assert credentials.decrypt(blob) == {"admin": "s3cret", "member": "hunter2"}


def test_local_survives_serialize_round_trip(local_mode):
    blob = credentials.encrypt({"admin": "s3cret"})
    restored = credentials.deserialize_blob(credentials.serialize_blob(blob))
    assert credentials.decrypt(restored) == {"admin": "s3cret"}


# --- kms mode --------------------------------------------------------------


def test_kms_round_trip(kms_mode):
    blob = credentials.encrypt({"user": "snowflake-pw"})
    assert blob.kek_id == "kms:alias/sidira-test"
    assert blob.wrapped_dek is not None
    # The plaintext DEK is never persisted — only the wrapped form.
    assert b"snowflake-pw" not in blob.ciphertext
    assert credentials.decrypt(blob) == {"user": "snowflake-pw"}


def test_kms_survives_serialize_round_trip(kms_mode):
    blob = credentials.encrypt({"user": "pw"})
    restored = credentials.deserialize_blob(credentials.serialize_blob(blob))
    assert restored.wrapped_dek == blob.wrapped_dek
    assert credentials.decrypt(restored) == {"user": "pw"}


def test_kms_missing_key_id_raises(monkeypatch):
    monkeypatch.setenv("SIDIRA_CRED_MODE", "kms")
    monkeypatch.delenv("SIDIRA_KMS_KEY_ID", raising=False)
    monkeypatch.delenv("PYTHIA_KMS_KEY_ID", raising=False)
    monkeypatch.setattr(credentials, "_kms_client", lambda: _FakeKMS())
    with pytest.raises(credentials.CredentialError, match="SIDIRA_KMS_KEY_ID"):
        credentials.encrypt({"user": "pw"})


def test_kms_generate_data_key_failure_is_credential_error(monkeypatch):
    monkeypatch.setenv("SIDIRA_CRED_MODE", "kms")
    monkeypatch.setenv("SIDIRA_KMS_KEY_ID", "alias/sidira-test")

    class _Broken:
        def generate_data_key(self, **_):
            raise RuntimeError("AccessDeniedException")

    monkeypatch.setattr(credentials, "_kms_client", lambda: _Broken())
    with pytest.raises(credentials.CredentialError, match="GenerateDataKey"):
        credentials.encrypt({"user": "pw"})


def test_kms_tampered_ciphertext_is_credential_error(kms_mode):
    blob = credentials.encrypt({"user": "pw"})
    blob.ciphertext = b"\x00" * len(blob.ciphertext)  # break AESGCM auth tag
    with pytest.raises(credentials.CredentialError, match="corrupted ciphertext"):
        credentials.decrypt(blob)


# --- associated data (tenant binding) --------------------------------------


def test_local_aad_round_trips_with_matching_aad(local_mode):
    aad = b"org_42:fs-abc123"
    blob = credentials.encrypt({"password": "pw"}, aad=aad)
    assert credentials.decrypt(blob, aad=aad) == {"password": "pw"}


def test_local_aad_mismatch_fails_to_decrypt(local_mode):
    blob = credentials.encrypt({"password": "pw"}, aad=b"org_42:fs-abc123")
    # A blob copied to another connection/customer (different aad) must not open.
    with pytest.raises(credentials.CredentialError):
        credentials.decrypt(blob, aad=b"org_99:fs-zzz999")
    # And decrypting with no aad (the legacy path) also fails for an aad blob.
    with pytest.raises(credentials.CredentialError):
        credentials.decrypt(blob)


def test_local_no_aad_still_round_trips(local_mode):
    """Crawl-cred blobs are written without aad — they must keep decrypting."""
    blob = credentials.encrypt({"password": "pw"})
    assert credentials.decrypt(blob) == {"password": "pw"}


def test_kms_aad_round_trips_with_matching_aad(kms_mode):
    aad = b"org_42:fs-abc123"
    blob = credentials.encrypt({"password": "pw"}, aad=aad)
    assert credentials.decrypt(blob, aad=aad) == {"password": "pw"}


def test_kms_aad_mismatch_fails_to_decrypt(monkeypatch):
    """A faithful fake KMS that enforces EncryptionContext (as real KMS does)
    refuses to unwrap the DEK under a different aad, and the AESGCM layer would
    also reject it."""
    monkeypatch.setenv("SIDIRA_CRED_MODE", "kms")
    monkeypatch.setenv("SIDIRA_KMS_KEY_ID", "alias/sidira-test")

    class _ContextKMS:
        def generate_data_key(self, KeyId, KeySpec, EncryptionContext=None):  # noqa: N803
            dek = os.urandom(32)
            ctx = base64.b64encode(repr(EncryptionContext).encode())
            wrapped = b"wrapped:" + ctx + b":" + base64.b64encode(dek)
            return {"Plaintext": dek, "CiphertextBlob": wrapped}

        def decrypt(self, CiphertextBlob, EncryptionContext=None):  # noqa: N803
            _, ctx_b64, dek_b64 = CiphertextBlob.split(b":", 2)
            expected = base64.b64decode(ctx_b64).decode()
            if repr(EncryptionContext) != expected:
                raise RuntimeError("InvalidCiphertextException: EncryptionContext mismatch")
            return {"Plaintext": base64.b64decode(dek_b64)}

    monkeypatch.setattr(credentials, "_kms_client", lambda: _ContextKMS())
    blob = credentials.encrypt({"password": "pw"}, aad=b"org_42:fs-abc123")
    assert credentials.decrypt(blob, aad=b"org_42:fs-abc123") == {"password": "pw"}
    with pytest.raises(credentials.CredentialError):
        credentials.decrypt(blob, aad=b"org_99:fs-zzz999")


def test_kms_no_aad_still_round_trips(kms_mode):
    """No-aad KMS blobs (e.g. crawl creds) keep their original behavior."""
    blob = credentials.encrypt({"password": "pw"})
    assert credentials.decrypt(blob) == {"password": "pw"}


# --- mode dispatch / errors ------------------------------------------------


def test_unknown_mode_raises(monkeypatch):
    monkeypatch.setenv("SIDIRA_CRED_MODE", "bogus")
    with pytest.raises(credentials.CredentialError, match="Unknown"):
        credentials.encrypt({"user": "pw"})


def test_unknown_kek_id_raises():
    blob = credentials.EncryptedBlob(kek_id="vault:xyz", ciphertext=b"x", nonce=b"y")
    with pytest.raises(credentials.CredentialError, match="Unknown kek_id"):
        credentials.decrypt(blob)


# --- audit log -------------------------------------------------------------


def test_encrypt_emits_audit_with_customer_id(local_mode):
    with capture_logs() as logs:
        credentials.encrypt({"admin": "s3cret"}, customer_id="org_42")
    entry = next(e for e in logs if e["event"] == "credential_access")
    assert entry["action"] == "encrypt"
    assert entry["key_id"] == "local"
    assert entry["customer_id"] == "org_42"
    assert "at" in entry


def test_decrypt_emits_audit_with_customer_id(local_mode):
    blob = credentials.encrypt({"admin": "s3cret"})
    with capture_logs() as logs:
        credentials.decrypt(blob, customer_id="org_42")
    entry = next(e for e in logs if e["event"] == "credential_access")
    assert entry["action"] == "decrypt"
    assert entry["customer_id"] == "org_42"


def test_audit_customer_id_optional(local_mode):
    with capture_logs() as logs:
        credentials.encrypt({"admin": "s3cret"})
    entry = next(e for e in logs if e["event"] == "credential_access")
    assert entry["customer_id"] is None
