"""Canonical serialization + SHA-256 hash-commit (ablation-protocol §5).

The shared hash-commit discipline behind the §4 null-integrity certificate AND
the §5 pre-registration artifact: "write down, hash-commit, and only then run."
A commitment is tamper-evident only if the SAME inputs ALWAYS serialize to the
SAME bytes (so the hash is reproducible) and ANY change to a committed field
moves the hash (so a retrofit is detectable).

`canonical_json` is the one canonicalization both call sites share:

* ``sort_keys=True`` — key order is irrelevant to the commitment, so dict
  iteration order can never change the hash.
* ``separators=(",", ":")`` — no insignificant whitespace, so a pretty-printer
  can never change the hash.
* the float ``repr`` json emits round-trips exactly on CPython, so a numeric
  field moves the hash iff its value changes — no float-formatting ambiguity.

Keeping this in one place means the pre-registration hash uses the EXACT same
approach as the null certificate, byte-for-byte, rather than a second hand-rolled
copy that could quietly drift.

Pure and dependency-free (stdlib `json` + `hashlib`), matching `statistics.py`.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(payload: Any) -> str:
    """Deterministic, order-stable JSON over a hashable payload (§5).

    `sort_keys` + fixed separators make the serialization reproducible: the same
    payload ALWAYS produces the same string, and any value/structure change
    produces a different one. The caller is responsible for putting only
    hash-relevant, JSON-serializable fields into `payload` (no floats with
    ambiguous formatting, no non-deterministic ordering).
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def canonical_hash(payload: Any) -> str:
    """SHA-256 hex digest of `canonical_json(payload)` — the §5 hash-commit.

    This is the tamper-evident commitment string: pre-register it before any run,
    recompute it later, and a mismatch proves a committed field was edited.
    """
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
