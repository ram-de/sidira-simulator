"""Pre-registration hash-commit + verification (ablation-protocol §5).

§5: *write down, hash-commit, and only then run.* This module is the engine
behind the `PreRegistration` artifact — it computes the SHA-256 hash-commit over
the canonical serialization of every committed field, builds a sealed artifact,
round-trips it to/from JSON, and `verify()`s that a (possibly re-loaded) artifact
has not been tampered with.

Design (mirrors `services.null_integrity`):

* The hashing/verification CORE is pure and deterministic. `build()` accepts the
  `created_at` timestamp as a PARAMETER — it never reads a clock — so the same
  inputs always produce the same hash and the function is trivially testable.
* The canonicalization is shared, byte-for-byte, with the null-integrity
  certificate via `services.canonical_hash`, so the two §5 commitments use the
  EXACT same tamper-evident discipline (stable key order, no whitespace, exact
  float repr).
* File I/O is isolated in two thin wrappers (`save`/`load`) that just move bytes;
  the hash math never touches the filesystem.

The hash covers EVERY committed field EXCEPT `integrity_hash` itself (you can't
commit a hash over its own value). So `verify()` strips the stored hash,
recomputes over the rest, and compares — catching any post-hoc edit to a
committed field, including a reordering of one of the predicted orderings.
"""

from __future__ import annotations

from pathlib import Path

from sidira_simulator.schemas.preregistration import (
    ComponentDecisionRule,
    PreRegistration,
    RunConfig,
)
from sidira_simulator.services.canonical_hash import canonical_hash

# The artifact field that holds the commitment itself — excluded from the
# payload the commitment is computed over (a hash can't cover its own value).
_HASH_FIELD = "integrity_hash"


def _commit_payload(artifact_dict: dict) -> dict:
    """The committed-field payload the hash is computed over (everything but the hash).

    Takes the artifact's `model_dump()` dict and drops `integrity_hash`. Pydantic
    `model_dump()` is deterministic for a given model, and `canonical_hash` then
    sorts keys + strips whitespace, so the result is stable regardless of field
    declaration order. Every other field — including `created_at`, `schema_version`,
    the orderings, the decision rules, and the full run config + blockers — IS
    part of the commitment, so any edit to any of them moves the hash.
    """
    return {k: v for k, v in artifact_dict.items() if k != _HASH_FIELD}


def compute_hash(artifact: PreRegistration) -> str:
    """SHA-256 hash-commit over the artifact's committed fields (§5).

    Pure: derived solely from the artifact's values. Recomputable by anyone with
    the artifact, which is what makes it tamper-evident.
    """
    return canonical_hash(_commit_payload(artifact.model_dump(mode="json")))


def build(
    *,
    primary_datasets: tuple[str, ...],
    predicted_identity_depth_ordering: tuple[str, ...],
    predicted_value_ladder_ordering: tuple[str, ...],
    decision_rules: tuple[ComponentDecisionRule, ...],
    run_config: RunConfig,
    created_at: str,
) -> PreRegistration:
    """Build a SEALED `PreRegistration` (§5): assemble the fields, then hash-commit.

    `created_at` is a PARAMETER, not a clock read, so this stays pure and
    deterministic (same inputs + same timestamp → same hash) and testable. The
    returned artifact's `integrity_hash` is the commitment over everything else;
    feed the result straight to `verify()` and it returns True.

    Raises (via Pydantic) on a structurally invalid artifact — empty
    primary_datasets / orderings / decision_rules, a duplicate ordering element,
    or a decision-rule set that doesn't cover EXACTLY the value-ladder components
    — so a malformed or inconsistent commitment can never be sealed.
    """
    # Build with a placeholder hash so the model validates, then re-create sealed
    # with the real hash computed over the committed fields (which exclude the
    # hash itself, so the placeholder never influences the commitment).
    draft = PreRegistration(
        primary_datasets=primary_datasets,
        predicted_identity_depth_ordering=predicted_identity_depth_ordering,
        predicted_value_ladder_ordering=predicted_value_ladder_ordering,
        decision_rules=decision_rules,
        run_config=run_config,
        created_at=created_at,
        integrity_hash="",
    )
    return draft.model_copy(update={_HASH_FIELD: compute_hash(draft)})


def verify(artifact: PreRegistration) -> bool:
    """Self-consistency check: does the stored hash match the artifact's body?

    Returns True iff the embedded `integrity_hash` equals the hash recomputed
    over the committed fields — i.e. nobody edited a field while leaving the hash
    stale. Returns False if ANY committed field was edited after sealing without
    updating the hash (a reordered ordering, a flipped blocker, …).

    TRUST BOUNDARY (codex P1 — by design, mirroring null_integrity): this alone
    is NOT sufficient tamper-evidence. A SHA-256 over public data is not a
    secret, so an attacker who edits a committed field can ALSO recompute and
    overwrite `integrity_hash` with this same public logic, and `verify()` would
    then return True on the forged body. Self-consistency only catches an
    incomplete edit (body changed, hash not). Genuine §5 tamper-evidence comes
    from committing the digest EXTERNALLY *before the run* — git-committing the
    artifact (its hash is then in the immutable git history) or recording the
    hash in a separate registry — and later checking the loaded artifact against
    THAT externally-held digest with `verify_against`. Use `verify` for the
    cheap "is this file internally intact" read; use `verify_against` for the
    real "is this the artifact we pre-registered" gate.
    """
    return artifact.integrity_hash == compute_hash(artifact)


def verify_against(artifact: PreRegistration, expected_hash: str) -> bool:
    """Tamper-evident check against an EXTERNALLY-committed digest (§5 gate).

    `expected_hash` is the digest recorded BEFORE the run — from git history, a
    registry, or a notarized log — i.e. the one place an attacker editing the
    artifact file cannot also rewrite. Returns True iff the artifact is
    self-consistent (`verify`) AND its recomputed hash equals `expected_hash`.

    This closes the gap in `verify` alone: a forger who edits a committed field
    and recomputes the embedded hash passes `verify`, but the recomputed hash no
    longer equals the pre-run `expected_hash`, so this returns False. The
    externally-held digest is the trust anchor; this function just compares the
    loaded artifact to it.
    """
    return verify(artifact) and compute_hash(artifact) == expected_hash


def to_json(artifact: PreRegistration) -> str:
    """Serialize a sealed artifact to a canonical JSON string (pure, no I/O).

    Uses Pydantic's deterministic JSON dump. Round-trips through `from_json`
    preserving every field — including `integrity_hash` — so a re-loaded artifact
    `verify()`s exactly as the original did.
    """
    return artifact.model_dump_json()


def from_json(raw: str) -> PreRegistration:
    """Deserialize a sealed artifact from a JSON string (pure, no I/O).

    Does NOT recompute or trust the hash — it returns exactly what was stored, so
    the CALLER must run `verify()` to confirm integrity. (A tampered file whose
    hash was also edited to match would still need a full re-hash of the forged
    body to pass `verify`; the point is that `from_json` is a faithful loader, not
    a validator.)
    """
    return PreRegistration.model_validate_json(raw)


# ── Thin file I/O (isolated from the pure hash/verify core) ──


def save(artifact: PreRegistration, path: str | Path) -> None:
    """Write a sealed artifact to `path` as canonical JSON (thin I/O wrapper)."""
    Path(path).write_text(to_json(artifact), encoding="utf-8")


def load(path: str | Path) -> PreRegistration:
    """Read a sealed artifact from `path` (thin I/O wrapper).

    Like `from_json`, this does NOT verify; the caller runs `verify()` on the
    result to detect tampering.
    """
    return from_json(Path(path).read_text(encoding="utf-8"))
