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

    def generate_data_key(self, KeyId, KeySpec):  # noqa: N803 (boto3 casing)
        assert KeySpec == "AES_256"
        dek = os.urandom(32)
        wrapped = b"wrapped:" + KeyId.encode() + b":" + base64.b64encode(dek)
        return {"Plaintext": dek, "CiphertextBlob": wrapped}

    def decrypt(self, CiphertextBlob):  # noqa: N803
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
