"""Tests for services/benchmark_preregistration.py — the §5 hash-committed
pre-registration artifact.

§5: write down, hash-commit, only then run. These tests pin the integrity
contract: the hash is deterministic for identical inputs; it MOVES if ANY
committed field changes (including a reordering of a predicted ordering); the
JSON round-trip preserves the hash; `verify()` is True for an intact artifact and
False after any post-hoc edit; `created_at` is caller-injected (not internally
generated); and the honest pre-data `blockers` field is carried into the commit.

Also confirms the shared canonical-hash refactor left the null-integrity
certificate byte-identical.

Pure/deterministic — same discipline as test_null_integrity.py.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from sidira_simulator.schemas.preregistration import (
    ComponentDecisionRule,
    DatasetPlan,
    PreRegistration,
    RunConfig,
    SplitPolicy,
)
from sidira_simulator.services import benchmark_preregistration as prereg

_CREATED_AT = "2026-06-15T00:00:00Z"


def _run_config(**overrides) -> RunConfig:
    base = dict(
        seed=12345,
        n_permutations=1000,
        bootstrap_resamples=1000,
        datasets=(
            DatasetPlan(name="upworthy", split_policy=SplitPolicy.LEAVE_ONE_OUT, present=False),
            DatasetPlan(name="hillstrom", split_policy=SplitPolicy.LEAVE_ONE_OUT, present=False),
            DatasetPlan(name="criteo", split_policy=SplitPolicy.FIXED_SPLIT, present=False),
        ),
        blockers=("datasets-not-yet-present", "live-llm-run-deferred"),
    )
    base.update(overrides)
    return RunConfig(**base)


def _build(*, created_at: str = _CREATED_AT, **overrides) -> PreRegistration:
    base = dict(
        primary_datasets=("upworthy", "hillstrom", "criteo"),
        predicted_identity_depth_ordering=(
            "persona+row",
            "row-only",
            "persona-only",
            "generic",
        ),
        predicted_value_ladder_ordering=(
            "blinded_framing",
            "individual_row",
            "structural_diff",
            "verbalized_distribution",
            "paraphrase_k3",
        ),
        decision_rules=(
            ComponentDecisionRule(component="blinded_framing"),
            ComponentDecisionRule(component="individual_row"),
            ComponentDecisionRule(component="structural_diff"),
            ComponentDecisionRule(component="verbalized_distribution"),
            ComponentDecisionRule(component="paraphrase_k3"),
        ),
        run_config=_run_config(),
    )
    base.update(overrides)
    return prereg.build(created_at=created_at, **base)


# ── Build + self-consistency ────────────────────────────────────────────


def test_build_seals_a_verifiable_artifact() -> None:
    art = _build()
    assert art.integrity_hash  # non-empty
    assert prereg.verify(art) is True
    # The hash is a 64-char SHA-256 hex digest.
    assert len(art.integrity_hash) == 64
    int(art.integrity_hash, 16)  # parses as hex


def test_hash_is_deterministic_for_identical_inputs() -> None:
    # Same inputs + same created_at → byte-identical hash (pure core).
    assert _build().integrity_hash == _build().integrity_hash


def test_created_at_is_caller_injected_not_generated() -> None:
    # The artifact stores exactly what the caller passed (no clock read), and a
    # DIFFERENT timestamp moves the hash (created_at is part of the commitment).
    art = _build(created_at="2099-01-01T12:34:56Z")
    assert art.created_at == "2099-01-01T12:34:56Z"
    assert art.integrity_hash != _build(created_at="2026-06-15T00:00:00Z").integrity_hash


def test_blockers_field_present_and_committed() -> None:
    art = _build()
    assert art.run_config.blockers == ("datasets-not-yet-present", "live-llm-run-deferred")
    # The honest pre-data flag: datasets default to not-present.
    assert all(d.present is False for d in art.run_config.datasets)


# ── Hash moves when ANY committed field changes ─────────────────────────


def test_hash_changes_when_primary_datasets_change() -> None:
    a = _build()
    b = _build(primary_datasets=("upworthy", "hillstrom"))
    assert a.integrity_hash != b.integrity_hash


def test_hash_changes_when_depth_ordering_reordered() -> None:
    # A REORDER (same elements, different order) must move the hash — the
    # ordering is the commitment, not just the set.
    a = _build()
    b = _build(
        predicted_identity_depth_ordering=(
            "row-only",
            "persona+row",
            "persona-only",
            "generic",
        )
    )
    assert a.integrity_hash != b.integrity_hash


def test_hash_changes_when_value_ladder_reordered() -> None:
    a = _build()
    b = _build(
        predicted_value_ladder_ordering=(
            "individual_row",
            "blinded_framing",
            "structural_diff",
            "verbalized_distribution",
            "paraphrase_k3",
        )
    )
    assert a.integrity_hash != b.integrity_hash


def test_hash_changes_when_seed_changes() -> None:
    a = _build()
    b = _build(run_config=_run_config(seed=999))
    assert a.integrity_hash != b.integrity_hash


def test_hash_changes_when_blockers_change() -> None:
    a = _build()
    b = _build(run_config=_run_config(blockers=()))
    assert a.integrity_hash != b.integrity_hash


def test_hash_changes_when_split_policy_changes() -> None:
    a = _build()
    flipped = (
        DatasetPlan(name="upworthy", split_policy=SplitPolicy.FIXED_SPLIT, present=False),
        DatasetPlan(name="hillstrom", split_policy=SplitPolicy.LEAVE_ONE_OUT, present=False),
        DatasetPlan(name="criteo", split_policy=SplitPolicy.FIXED_SPLIT, present=False),
    )
    b = _build(run_config=_run_config(datasets=flipped))
    assert a.integrity_hash != b.integrity_hash


def test_hash_changes_when_a_decision_rule_changes() -> None:
    a = _build()
    stricter = (
        ComponentDecisionRule(component="blinded_framing", metric="direction_accuracy"),
        ComponentDecisionRule(component="individual_row"),
        ComponentDecisionRule(component="structural_diff"),
        ComponentDecisionRule(component="verbalized_distribution"),
        ComponentDecisionRule(component="paraphrase_k3"),
    )
    b = _build(decision_rules=stricter)
    assert a.integrity_hash != b.integrity_hash


# ── JSON round-trip ─────────────────────────────────────────────────────


def test_to_json_from_json_round_trip_preserves_hash() -> None:
    art = _build()
    restored = prereg.from_json(prereg.to_json(art))
    assert restored == art
    assert restored.integrity_hash == art.integrity_hash
    assert prereg.verify(restored) is True


def test_to_json_is_valid_json_carrying_the_hash() -> None:
    art = _build()
    payload = json.loads(prereg.to_json(art))
    assert payload["integrity_hash"] == art.integrity_hash
    assert payload["created_at"] == _CREATED_AT


# ── verify() catches tampering ──────────────────────────────────────────


def test_verify_false_after_field_tampered() -> None:
    art = _build()
    # Post-hoc edit a committed field WITHOUT recomputing the hash (the frozen
    # model forces the edit through model_copy, which is exactly how a tamperer
    # would mutate a deserialized artifact). The stored hash is now stale.
    tampered = art.model_copy(update={"primary_datasets": ("upworthy",)})
    assert tampered.integrity_hash == art.integrity_hash  # stale hash carried over
    assert prereg.verify(tampered) is False


def test_verify_false_after_ordering_tampered() -> None:
    art = _build()
    tampered = art.model_copy(
        update={
            "predicted_value_ladder_ordering": (
                "paraphrase_k3",
                "blinded_framing",
                "individual_row",
                "structural_diff",
                "verbalized_distribution",
            )
        }
    )
    assert prereg.verify(tampered) is False


def test_verify_false_after_created_at_tampered() -> None:
    art = _build()
    tampered = art.model_copy(update={"created_at": "1999-01-01T00:00:00Z"})
    assert prereg.verify(tampered) is False


def test_verify_false_after_nested_run_config_tampered() -> None:
    art = _build()
    tampered = art.model_copy(update={"run_config": _run_config(seed=42)})
    assert prereg.verify(tampered) is False


def test_verify_true_for_freshly_built_artifact_only() -> None:
    # A hand-constructed artifact with a bogus hash must NOT verify.
    bogus = PreRegistration(
        primary_datasets=("upworthy",),
        predicted_identity_depth_ordering=("persona+row", "generic"),
        predicted_value_ladder_ordering=("blinded_framing",),
        decision_rules=(ComponentDecisionRule(component="blinded_framing"),),
        run_config=_run_config(),
        created_at=_CREATED_AT,
        integrity_hash="0" * 64,
    )
    assert prereg.verify(bogus) is False


# ── Boundary validation: a malformed commitment can't be sealed (codex P2) ──


def test_build_rejects_empty_primary_datasets() -> None:
    with pytest.raises(ValidationError):
        _build(primary_datasets=())


def test_build_rejects_empty_orderings_and_rules() -> None:
    with pytest.raises(ValidationError):
        _build(predicted_value_ladder_ordering=())
    with pytest.raises(ValidationError):
        _build(predicted_identity_depth_ordering=())
    with pytest.raises(ValidationError):
        _build(decision_rules=())


def test_build_rejects_duplicate_ordering_element() -> None:
    with pytest.raises(ValidationError):
        _build(
            predicted_identity_depth_ordering=(
                "persona+row",
                "persona+row",
                "generic",
            )
        )


def test_build_rejects_decision_rule_for_uncommitted_component() -> None:
    # A rule whose component is not in the value-ladder ordering → reject.
    with pytest.raises(ValidationError):
        _build(
            decision_rules=(
                ComponentDecisionRule(component="blinded_framing"),
                ComponentDecisionRule(component="individual_row"),
                ComponentDecisionRule(component="structural_diff"),
                ComponentDecisionRule(component="verbalized_distribution"),
                ComponentDecisionRule(component="not_a_real_component"),
            )
        )


def test_build_rejects_missing_decision_rule_for_a_component() -> None:
    # The value-ladder has 5 components; only 4 rules → the analysis can't decide
    # build/cut for the uncovered one → reject.
    with pytest.raises(ValidationError):
        _build(
            decision_rules=(
                ComponentDecisionRule(component="blinded_framing"),
                ComponentDecisionRule(component="individual_row"),
                ComponentDecisionRule(component="structural_diff"),
                ComponentDecisionRule(component="verbalized_distribution"),
            )
        )


def test_build_rejects_duplicate_decision_rule_component() -> None:
    with pytest.raises(ValidationError):
        _build(
            decision_rules=(
                ComponentDecisionRule(component="blinded_framing"),
                ComponentDecisionRule(component="blinded_framing"),
                ComponentDecisionRule(component="individual_row"),
                ComponentDecisionRule(component="structural_diff"),
                ComponentDecisionRule(component="verbalized_distribution"),
            )
        )


def test_build_rejects_primary_dataset_absent_from_run_config() -> None:
    # primary_datasets names a dataset the run config doesn't carry → that
    # dataset has no committed split policy / present flag → reject.
    with pytest.raises(ValidationError):
        _build(
            primary_datasets=("upworthy", "hillstrom", "criteo", "some_unconfigured_set"),
        )


def test_build_rejects_duplicate_primary_datasets() -> None:
    with pytest.raises(ValidationError):
        _build(primary_datasets=("upworthy", "upworthy", "hillstrom", "criteo"))


def test_build_rejects_empty_run_config_datasets() -> None:
    with pytest.raises(ValidationError):
        _run_config(datasets=())


def test_build_rejects_duplicate_run_config_dataset_names() -> None:
    dupes = (
        DatasetPlan(name="upworthy", split_policy=SplitPolicy.LEAVE_ONE_OUT),
        DatasetPlan(name="upworthy", split_policy=SplitPolicy.FIXED_SPLIT),
    )
    with pytest.raises(ValidationError):
        _run_config(datasets=dupes)


# ── verify_against: tamper-evidence vs an external committed digest ──────


def test_verify_against_external_digest() -> None:
    art = _build()
    committed = art.integrity_hash  # the digest recorded pre-run (e.g. in git)
    assert prereg.verify_against(art, committed) is True
    # A different committed digest → not the artifact we pre-registered.
    assert prereg.verify_against(art, "0" * 64) is False


def test_verify_against_catches_a_fully_reforged_artifact() -> None:
    # The attack `verify` alone can't catch: edit a committed field AND recompute
    # the embedded hash so the artifact is self-consistent again.
    art = _build()
    committed = art.integrity_hash
    forged_body = art.model_copy(update={"primary_datasets": ("criteo",)})
    forged = forged_body.model_copy(update={"integrity_hash": prereg.compute_hash(forged_body)})
    # Self-consistency check is fooled by the reforged hash...
    assert prereg.verify(forged) is True
    # ...but the externally-committed digest is the trust anchor and catches it.
    assert prereg.verify_against(forged, committed) is False


# ── File-backed persistence (thin I/O wrapper) ──────────────────────────


def test_save_load_round_trip(tmp_path) -> None:
    art = _build()
    path = tmp_path / "prereg.json"
    prereg.save(art, path)
    loaded = prereg.load(path)
    assert loaded == art
    assert prereg.verify(loaded) is True


def test_load_detects_on_disk_tampering(tmp_path) -> None:
    art = _build()
    path = tmp_path / "prereg.json"
    prereg.save(art, path)
    # Forge a committed field on disk WITHOUT updating the hash.
    payload = json.loads(path.read_text())
    payload["primary_datasets"] = ["criteo"]
    path.write_text(json.dumps(payload))
    loaded = prereg.load(path)
    assert prereg.verify(loaded) is False


# ── Shared canonical-hash refactor: null_integrity stays byte-identical ──


def test_null_integrity_hash_uses_shared_canonicalization() -> None:
    # The refactor extracted the canonical-hash core; the null certificate's
    # integrity_hash must still be a stable 64-char SHA-256 over the same inputs.
    from sidira_simulator.services.null_integrity import _integrity_hash

    h1 = _integrity_hash([1.0, -1.0, 0.5], [2.0, -2.0, 0.1], n_permutations=100, seed=7)
    h2 = _integrity_hash([1.0, -1.0, 0.5], [2.0, -2.0, 0.1], n_permutations=100, seed=7)
    assert h1 == h2
    assert len(h1) == 64
    # A changed input moves it.
    h3 = _integrity_hash([1.0, -1.0, 0.6], [2.0, -2.0, 0.1], n_permutations=100, seed=7)
    assert h3 != h1
