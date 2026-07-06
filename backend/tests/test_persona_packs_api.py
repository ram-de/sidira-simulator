"""GET /persona-packs/{pack_id} endpoint tests + list/promote tests (#25).

The Library's persona-pack detail page (#207) reads this to render each
persona's description / JTBD / weight — the fields the wizard-shaped
`GET /personas` projection deliberately omits. `pack_id="latest"` resolves the
active pack (with the #212 starter fallback for empty tenants); an explicit
version loads that snapshot and 404s when it is genuinely missing.

The list/promote coverage (#25) at the bottom uses an in-memory persona-build
repo (each COMPLETE build with a `pack_version` IS a pack version) and a
`LocalArtifactStore(tmp_path)` so nothing hits real R2; `promote` writes the
same `latest` pointer key the loader reads.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sidira_simulator.adapters.persona_loader import PersonaPackLoader
from sidira_simulator.adapters.r2 import LocalArtifactStore
from sidira_simulator.adapters.repositories import get_in_memory_persona_build_repo
from sidira_simulator.api.deps import (
    current_customer_id,
    get_artifact_store,
    get_persona_loader,
)
from sidira_simulator.main import app

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"


@pytest.fixture(autouse=True)
def _customer() -> None:
    app.dependency_overrides[current_customer_id] = lambda: "demo"
    yield
    app.dependency_overrides.clear()


def test_get_latest_returns_full_pack_with_descriptions() -> None:
    """`latest` resolves the real active pack with the detail fields the page needs."""
    app.dependency_overrides[get_persona_loader] = lambda: PersonaPackLoader(
        LocalArtifactStore(_FIXTURE_ROOT)
    )
    resp = TestClient(app).get("/persona-packs/latest")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_starter"] is False
    assert body["version"] == "v_1"
    assert len(body["personas"]) == 6
    # The whole point of this endpoint over /personas: full persona bodies.
    assert all(p["description"].strip() for p in body["personas"])
    # Weights + stability surface so the detail page can show "% of population".
    assert "head_count" in body["weights"]
    assert isinstance(body["stability_score"], (int, float))


def test_get_explicit_version_matches_latest() -> None:
    """Addressing the version directly returns the same snapshot as `latest`."""
    app.dependency_overrides[get_persona_loader] = lambda: PersonaPackLoader(
        LocalArtifactStore(_FIXTURE_ROOT)
    )
    client = TestClient(app)
    explicit = client.get("/persona-packs/v_1")
    assert explicit.status_code == 200, explicit.text
    assert explicit.json() == client.get("/persona-packs/latest").json()


def test_empty_tenant_latest_returns_starter(tmp_path: Path) -> None:
    """No pack in the store → `latest` serves the #212 starter, not a 404."""
    app.dependency_overrides[get_persona_loader] = lambda: PersonaPackLoader(
        LocalArtifactStore(tmp_path)
    )
    resp = TestClient(app).get("/persona-packs/latest")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_starter"] is True
    assert body["version"] == "starter-v1"
    assert len(body["personas"]) >= 1


def test_unknown_version_404s() -> None:
    """An explicit version that does not exist is a real not-found, not a starter."""
    app.dependency_overrides[get_persona_loader] = lambda: PersonaPackLoader(
        LocalArtifactStore(_FIXTURE_ROOT)
    )
    resp = TestClient(app).get("/persona-packs/v_999")
    assert resp.status_code == 404, resp.text


def test_detail_renders_blocks_and_weight_schemes() -> None:
    """`/{id}/detail` returns the rendered view: centroid block, schemes, honesty."""
    app.dependency_overrides[get_persona_loader] = lambda: PersonaPackLoader(
        LocalArtifactStore(_FIXTURE_ROOT)
    )
    resp = TestClient(app).get("/persona-packs/latest/detail")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["version"] == "v_1"
    assert body["schema_version"] == "1.0"
    assert body["persona_count"] == 6
    # The demo fixture is a v1.0 pack — no individual-row tier, honest empty-state.
    assert body["has_individual_rows"] is False
    # Centroid tier renders for personas with salient centroid_features.
    assert any(p["how_you_compare"] for p in body["personas"])
    assert all(p["distinctive"] is None for p in body["personas"])
    # All three weight schemes are reported (present-or-not), headcount always present.
    schemes = {s["key"]: s for s in body["weight_schemes"]}
    assert schemes["head_count"]["available"] is True
    assert {"head_count", "order_weighted", "revenue_weighted"} == set(schemes)
    # The raw bulky v1.1 arrays are NOT echoed into the view payload.
    first = body["personas"][0]
    assert "sample_rows" not in first and "centroid_full" not in first


def test_detail_unknown_version_404s() -> None:
    """The detail view shares the raw endpoint's not-found semantics."""
    app.dependency_overrides[get_persona_loader] = lambda: PersonaPackLoader(
        LocalArtifactStore(_FIXTURE_ROOT)
    )
    resp = TestClient(app).get("/persona-packs/v_999/detail")
    assert resp.status_code == 404, resp.text


# ── list + promote (#25) ──────────────────────────────────────────────────

_CUSTOMER_ID = "demo"


def _write_pack(store: LocalArtifactStore, version: str) -> None:
    """Write a schema-valid PersonaPack snapshot at `version`.

    Reuses the demo fixture pack (a real, validated PersonaPack) so that a
    follow-up GET can actually load it, just restamping the version field.
    """
    fixture = (
        _FIXTURE_ROOT / "customers" / _CUSTOMER_ID / "personas" / "v_1" / "persona_pack.json"
    )
    pack = json.loads(fixture.read_text())
    pack["version"] = version
    key = f"customers/{_CUSTOMER_ID}/personas/{version}/persona_pack.json"
    store.write_text(key, json.dumps(pack))


def _seed_build(
    *,
    build_id: str,
    status: str,
    pack_version: str | None,
    created_at: datetime,
    stability: float = 0.8,
    persona_count: int = 2,
) -> None:
    repo = get_in_memory_persona_build_repo()
    repo._builds[build_id] = {
        "id": build_id,
        "customer_id": _CUSTOMER_ID,
        "connection_id": "conn",
        "status": status,
        "pack_version": pack_version,
        "stability_score": stability,
        "persona_count": persona_count,
        "error": None,
        "created_at": created_at,
        "completed_at": created_at,
    }


@pytest.fixture
def packs_client(tmp_path: Path):
    """Client wired to a tmp LocalArtifactStore + clean in-memory build repo."""
    get_in_memory_persona_build_repo()._builds.clear()
    store = LocalArtifactStore(tmp_path)
    loader = PersonaPackLoader(store=store)
    app.dependency_overrides[get_artifact_store] = lambda: store
    app.dependency_overrides[get_persona_loader] = lambda: loader
    with TestClient(app) as c:
        c._store = store
        c._loader = loader
        yield c
    app.dependency_overrides.clear()


def test_list_empty_tenant_returns_empty_not_404(packs_client) -> None:
    resp = packs_client.get("/persona-packs")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_newest_first_only_complete(packs_client) -> None:
    base = datetime(2026, 6, 15, tzinfo=timezone.utc)
    _write_pack(packs_client._store, "v_1")
    _write_pack(packs_client._store, "v_2")
    _seed_build(build_id="b1", status="complete", pack_version="v_1", created_at=base)
    _seed_build(
        build_id="b2",
        status="complete",
        pack_version="v_2",
        created_at=base + timedelta(hours=1),
    )
    # Non-complete / version-less builds must NOT appear.
    _seed_build(
        build_id="b3", status="failed", pack_version=None, created_at=base + timedelta(hours=2)
    )
    _seed_build(
        build_id="b4", status="running", pack_version=None, created_at=base + timedelta(hours=3)
    )

    body = packs_client.get("/persona-packs").json()
    assert [p["version"] for p in body] == ["v_2", "v_1"]  # newest first
    assert all(p["id"] == p["version"] for p in body)
    assert all(p["status"] == "draft" for p in body)
    assert all(p["is_latest"] is False for p in body)


def test_promote_writes_pointer_and_flips_status(packs_client) -> None:
    base = datetime(2026, 6, 15, tzinfo=timezone.utc)
    _write_pack(packs_client._store, "v_1")
    _write_pack(packs_client._store, "v_2")
    _seed_build(build_id="b1", status="complete", pack_version="v_1", created_at=base)
    _seed_build(
        build_id="b2",
        status="complete",
        pack_version="v_2",
        created_at=base + timedelta(hours=1),
    )

    resp = packs_client.post("/persona-packs/v_1/promote")
    assert resp.status_code == 200
    promoted = resp.json()
    assert promoted["version"] == "v_1"
    assert promoted["status"] == "promoted"
    assert promoted["is_latest"] is True

    # The pointer was written so the loader resolves latest → v_1.
    assert packs_client._loader.resolve_latest_version(_CUSTOMER_ID) == "v_1"
    # And GET /persona-packs/latest resolves to that snapshot.
    latest = packs_client.get("/persona-packs/latest")
    assert latest.status_code == 200
    assert latest.json()["customer_id"] == _CUSTOMER_ID

    # A follow-up list reflects the flip.
    by_version = {p["version"]: p for p in packs_client.get("/persona-packs").json()}
    assert by_version["v_1"]["status"] == "promoted"
    assert by_version["v_1"]["is_latest"] is True
    assert by_version["v_2"]["status"] == "draft"
    assert by_version["v_2"]["is_latest"] is False


def test_promote_unknown_version_404(packs_client) -> None:
    base = datetime(2026, 6, 15, tzinfo=timezone.utc)
    _write_pack(packs_client._store, "v_1")
    _seed_build(build_id="b1", status="complete", pack_version="v_1", created_at=base)

    assert packs_client.post("/persona-packs/v_9/promote").status_code == 404


def test_promote_latest_sentinel_rejected(packs_client) -> None:
    assert packs_client.post("/persona-packs/latest/promote").status_code == 400


def test_promote_version_beyond_recent_page_resolves_metadata(packs_client) -> None:
    """A complete version older than the 50-row recent page still promotes with
    its real metadata (stability/persona_count), not a zeroed PackSummary.

    Seed >50 newer builds so the target falls off `list_recent`'s default page;
    `get_by_pack_version` must still find it.
    """
    base = datetime(2026, 6, 15, tzinfo=timezone.utc)
    # The old target version, with a readable snapshot + populated metadata.
    _write_pack(packs_client._store, "v_old")
    _seed_build(
        build_id="b-old",
        status="complete",
        pack_version="v_old",
        created_at=base,
        stability=0.91,
        persona_count=5,
    )
    # 60 newer complete builds bury it past the default 50-row recent page.
    for i in range(60):
        _seed_build(
            build_id=f"b{i}",
            status="complete",
            pack_version=f"v_new_{i}",
            created_at=base + timedelta(hours=i + 1),
        )

    resp = packs_client.post("/persona-packs/v_old/promote")
    assert resp.status_code == 200, resp.text
    promoted = resp.json()
    assert promoted["version"] == "v_old"
    assert promoted["status"] == "promoted"
    assert promoted["is_latest"] is True
    # Metadata is the real build's, not a zeroed fallback.
    assert promoted["stability_score"] == 0.91
    assert promoted["persona_count"] == 5


# ── estimability lever cards (#565) ───────────────────────────────────────


def _write_manifest(store: LocalArtifactStore, version: str, candidates: list[dict]) -> None:
    """Write an estimability_manifest.json beside the pack at `version`."""
    manifest = {
        "manifest_version": "1",
        "customer_id": _CUSTOMER_ID,
        "setup_id": "default",
        "pack_version": version,
        "feature_store": "STREAMLY.SYNTHETIC.USERS_FEATURE_STORE",
        "columns": [],
        "capability_links": [],
        "candidate_effects": candidates,
        "built_at": "2026-07-01T00:00:00Z",
    }
    key = f"customers/{_CUSTOMER_ID}/personas/{version}/estimability_manifest.json"
    store.write_text(key, json.dumps(manifest))


def test_estimability_returns_lever_cards(packs_client) -> None:
    """A seeded manifest projects to review cards: direction + guard tri-state."""
    _write_pack(packs_client._store, "v_1")
    _write_manifest(
        packs_client._store,
        "v_1",
        [
            {
                "treatment": "autoplay_enabled",
                "outcome": "completion_rate",
                "covariates": ["weekly_sessions", "genre_concentration"],
                "supportable": True,
                "support_reasons": ["overlap ok"],
                "n_treat": 900,
                "n_control": 1100,
                "overlap_fraction": 0.82,
                # Magnitudes present in the artifact — must be stripped from the view.
                "naive_ate": 0.13,
                "t_learner_ate": 0.11,
                "ipw_ate": 0.12,
                "sign_adjusted": "positive",
                "guard_trips": False,
                "guard_floor": 0.05,
                "guard_ratio": 1.5,
                "guard_confidence": "high",
                "guard_reason": "no NC exceeds floor",
                "neg_control_effect": 0.01,
                "neg_control_effects": {"age": 0.01, "household_size": 0.004},
            },
            {
                # A candidate with NC evidence NOT precomputed → not-validated card.
                "treatment": "ad_supported_flag",
                "outcome": "plan_upgrade_propensity",
                "supportable": True,
                "sign_adjusted": "negative",
                "guard_trips": None,
            },
        ],
    )
    resp = packs_client.get("/persona-packs/v_1/estimability")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["pack_version"] == "v_1"
    assert body["feature_store"].startswith("STREAMLY")
    assert len(body["levers"]) == 2

    first, second = body["levers"]
    assert first["treatment"] == "autoplay_enabled"
    assert first["direction"] == "positive"
    assert first["guard_trips"] is False
    assert first["guard_floor"] == 0.05 and first["guard_ratio"] == 1.5
    assert first["neg_control_effects"] == {"age": 0.01, "household_size": 0.004}
    # The tri-state None survives round-trip as the honest "not validated" state.
    assert second["guard_trips"] is None
    assert second["direction"] == "negative"


def test_estimability_omits_effect_magnitudes(packs_client) -> None:
    """The view is direction-only: no treatment→outcome ATE ever reaches the client."""
    _write_pack(packs_client._store, "v_1")
    _write_manifest(
        packs_client._store,
        "v_1",
        [
            {
                "treatment": "autoplay_enabled",
                "outcome": "completion_rate",
                "supportable": True,
                "naive_ate": 0.13,
                "t_learner_ate": 0.11,
                "ipw_ate": 0.12,
                "naive_adjusted_gap": 0.09,
                "sign_adjusted": "positive",
            }
        ],
    )
    lever = packs_client.get("/persona-packs/v_1/estimability").json()["levers"][0]
    for banned in ("naive_ate", "t_learner_ate", "ipw_ate", "naive_adjusted_gap"):
        assert banned not in lever, f"{banned} leaked into the lever card view"
    # But the direction and NC-guard evidence ARE present.
    assert lever["direction"] == "positive"
    assert "guard_trips" in lever and "neg_control_effects" in lever


def test_estimability_latest_resolves_pointer(packs_client) -> None:
    """`latest` reads the manifest of the version the pointer resolves to."""
    _write_pack(packs_client._store, "v_1")
    _seed_build(
        build_id="b1",
        status="complete",
        pack_version="v_1",
        created_at=datetime(2026, 6, 15, tzinfo=timezone.utc),
    )
    _write_manifest(
        packs_client._store,
        "v_1",
        [{"treatment": "t", "outcome": "y", "supportable": True, "sign_adjusted": "positive"}],
    )
    packs_client.post("/persona-packs/v_1/promote")

    resp = packs_client.get("/persona-packs/latest/estimability")
    assert resp.status_code == 200, resp.text
    assert resp.json()["pack_version"] == "v_1"


def test_estimability_absent_manifest_404(packs_client) -> None:
    """A pack with no manifest (pre-precompute) is a real 404 empty-state, not 500."""
    _write_pack(packs_client._store, "v_1")
    assert packs_client.get("/persona-packs/v_1/estimability").status_code == 404


def test_estimability_latest_empty_tenant_404(packs_client) -> None:
    """No `latest` pointer → 404 (no pack, so no lever data)."""
    assert packs_client.get("/persona-packs/latest/estimability").status_code == 404


def test_estimability_malformed_manifest_404(packs_client) -> None:
    """A corrupt manifest degrades to 404 rather than 500-ing the detail page."""
    _write_pack(packs_client._store, "v_1")
    key = f"customers/{_CUSTOMER_ID}/personas/v_1/estimability_manifest.json"
    packs_client._store.write_text(key, "{ not valid json ]")
    assert packs_client.get("/persona-packs/v_1/estimability").status_code == 404


def test_estimability_orphan_manifest_without_pack_404(packs_client) -> None:
    """A manifest whose pack version does not exist is an orphan → 404, not a 200.

    Mirrors the sibling routes' existence semantics: an unknown version is a real
    not-found even if a stray manifest happens to sit at that key.
    """
    _write_manifest(
        packs_client._store,
        "v_ghost",
        [{"treatment": "t", "outcome": "y", "supportable": True}],
    )
    assert packs_client.get("/persona-packs/v_ghost/estimability").status_code == 404


def test_estimability_mismatched_manifest_404(packs_client) -> None:
    """A manifest whose own customer_id/pack_version disagree with the key → 404.

    A misplaced/stale artifact must not return another pack's metadata; the
    integrity guard rejects it rather than serving a mismatched pack_version.
    """
    _write_pack(packs_client._store, "v_1")
    key = f"customers/{_CUSTOMER_ID}/personas/v_1/estimability_manifest.json"
    manifest = {
        "manifest_version": "1",
        "customer_id": _CUSTOMER_ID,
        "setup_id": "default",
        "pack_version": "v_somewhere_else",  # disagrees with the v_1 key
        "feature_store": "FS",
        "candidate_effects": [{"treatment": "t", "outcome": "y", "supportable": True}],
    }
    packs_client._store.write_text(key, json.dumps(manifest))
    assert packs_client.get("/persona-packs/v_1/estimability").status_code == 404


# ── lever review: vouch / override / clear (#565 parts 2 & 3) ─────────────

_LEVER = {
    "treatment": "autoplay_enabled",
    "outcome": "completion_rate",
    "supportable": True,
    "sign_adjusted": "positive",
    "guard_trips": False,
    "guard_floor": 0.05,
    "guard_ratio": 1.5,
}


def _seed_reviewable_pack(client, version: str = "v_1") -> None:
    """A pack + manifest with one known lever, ready to be reviewed."""
    _write_pack(client._store, version)
    _write_manifest(client._store, version, [dict(_LEVER)])


def test_lever_review_vouch_records_and_shows_on_card(packs_client) -> None:
    """A vouch persists and folds back onto the lever card via the GET."""
    _seed_reviewable_pack(packs_client)
    resp = packs_client.post(
        "/persona-packs/v_1/lever-review",
        json={
            "treatment": "autoplay_enabled",
            "outcome": "completion_rate",
            "decision": "vouched",
            "note": "matches the launch readout",
            "guard_trips_at_review": False,
        },
    )
    assert resp.status_code == 200, resp.text
    stored = resp.json()["review"]
    assert stored["decision"] == "vouched"
    assert stored["reviewer"] == "demo-user"  # current_user_id fallback
    assert stored["reviewed_at"]  # ISO timestamp stamped server-side
    assert stored["guard_trips_at_review"] is False

    # The card now carries the review.
    card = packs_client.get("/persona-packs/v_1/estimability").json()["levers"][0]
    assert card["review"]["decision"] == "vouched"
    assert card["review"]["note"] == "matches the launch readout"


def test_lever_review_reject_records_override(packs_client) -> None:
    """A reject is stored verbatim — the frontend renders the force-abstain."""
    _seed_reviewable_pack(packs_client)
    resp = packs_client.post(
        "/persona-packs/v_1/lever-review",
        json={
            "treatment": "autoplay_enabled",
            "outcome": "completion_rate",
            "decision": "rejected",
            "note": "confounded by tenure — guard missed it",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["review"]["decision"] == "rejected"
    card = packs_client.get("/persona-packs/v_1/estimability").json()["levers"][0]
    # The machine verdict is untouched; only the human layer is added.
    assert card["guard_trips"] is False
    assert card["review"]["decision"] == "rejected"


def test_lever_review_upsert_replaces_prior_decision(packs_client) -> None:
    """Re-reviewing the same lever replaces, never duplicates."""
    _seed_reviewable_pack(packs_client)
    base = {"treatment": "autoplay_enabled", "outcome": "completion_rate"}
    packs_client.post("/persona-packs/v_1/lever-review", json={**base, "decision": "vouched"})
    packs_client.post("/persona-packs/v_1/lever-review", json={**base, "decision": "rejected"})
    card = packs_client.get("/persona-packs/v_1/estimability").json()["levers"][0]
    assert card["review"]["decision"] == "rejected"


def test_lever_review_clear_removes_review(packs_client) -> None:
    """`cleared` deletes the stored decision; the card returns to unreviewed."""
    _seed_reviewable_pack(packs_client)
    base = {"treatment": "autoplay_enabled", "outcome": "completion_rate"}
    packs_client.post("/persona-packs/v_1/lever-review", json={**base, "decision": "vouched"})
    resp = packs_client.post(
        "/persona-packs/v_1/lever-review", json={**base, "decision": "cleared"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["review"] is None
    card = packs_client.get("/persona-packs/v_1/estimability").json()["levers"][0]
    assert card["review"] is None


def test_lever_review_snapshot_persisted(packs_client) -> None:
    """The guard state the reviewer saw is snapshotted for a later calibration join."""
    _seed_reviewable_pack(packs_client)
    packs_client.post(
        "/persona-packs/v_1/lever-review",
        json={
            "treatment": "autoplay_enabled",
            "outcome": "completion_rate",
            "decision": "rejected",
            "guard_trips_at_review": False,
            "decisive_nc_at_review": "household_size",
        },
    )
    card = packs_client.get("/persona-packs/v_1/estimability").json()["levers"][0]
    assert card["review"]["guard_trips_at_review"] is False
    assert card["review"]["decisive_nc_at_review"] == "household_size"


def test_lever_review_unknown_lever_404(packs_client) -> None:
    """Reviewing a (treatment, outcome) not in the manifest is a 404, not an orphan."""
    _seed_reviewable_pack(packs_client)
    resp = packs_client.post(
        "/persona-packs/v_1/lever-review",
        json={"treatment": "nope", "outcome": "nope", "decision": "vouched"},
    )
    assert resp.status_code == 404, resp.text
    # And nothing was written for it.
    assert packs_client.get("/persona-packs/v_1/estimability").json()["levers"][0][
        "review"
    ] is None


def test_lever_review_unknown_pack_404(packs_client) -> None:
    """Reviewing a lever on a nonexistent pack version 404s (no orphan sidecar)."""
    resp = packs_client.post(
        "/persona-packs/v_999/lever-review",
        json={"treatment": "t", "outcome": "y", "decision": "vouched"},
    )
    assert resp.status_code == 404, resp.text


def test_lever_review_absent_manifest_404(packs_client) -> None:
    """A pack with no manifest has no levers to review → 404, not a 500."""
    _write_pack(packs_client._store, "v_1")
    resp = packs_client.post(
        "/persona-packs/v_1/lever-review",
        json={"treatment": "t", "outcome": "y", "decision": "vouched"},
    )
    assert resp.status_code == 404, resp.text


def test_lever_review_note_too_long_422(packs_client) -> None:
    """The note is bounded (max 2000 chars) — an overlong note is a 422."""
    _seed_reviewable_pack(packs_client)
    resp = packs_client.post(
        "/persona-packs/v_1/lever-review",
        json={
            "treatment": "autoplay_enabled",
            "outcome": "completion_rate",
            "decision": "vouched",
            "note": "x" * 2001,
        },
    )
    assert resp.status_code == 422, resp.text


def test_lever_review_latest_resolves_pointer(packs_client) -> None:
    """`latest` reviews the lever on the version the pointer resolves to."""
    _seed_reviewable_pack(packs_client)
    _seed_build(
        build_id="b1",
        status="complete",
        pack_version="v_1",
        created_at=datetime(2026, 6, 15, tzinfo=timezone.utc),
    )
    packs_client.post("/persona-packs/v_1/promote")
    resp = packs_client.post(
        "/persona-packs/latest/lever-review",
        json={
            "treatment": "autoplay_enabled",
            "outcome": "completion_rate",
            "decision": "vouched",
        },
    )
    assert resp.status_code == 200, resp.text
    card = packs_client.get("/persona-packs/latest/estimability").json()["levers"][0]
    assert card["review"]["decision"] == "vouched"


def test_lever_review_written_to_sidecar_key(packs_client) -> None:
    """The review lands in the pack-versioned sidecar, beside the manifest."""
    _seed_reviewable_pack(packs_client)
    packs_client.post(
        "/persona-packs/v_1/lever-review",
        json={
            "treatment": "autoplay_enabled",
            "outcome": "completion_rate",
            "decision": "vouched",
        },
    )
    raw = packs_client._store.read_text(
        f"customers/{_CUSTOMER_ID}/personas/v_1/lever_review.json"
    )
    doc = json.loads(raw)
    assert doc["pack_version"] == "v_1"
    assert len(doc["reviews"]) == 1
    assert doc["reviews"][0]["treatment"] == "autoplay_enabled"


def test_get_by_pack_version_ignores_incomplete_and_other_customers() -> None:
    """Unit coverage for the new repo method: only this customer's COMPLETE build
    with the exact version is returned."""
    import asyncio

    repo = get_in_memory_persona_build_repo()
    repo._builds.clear()
    base = datetime(2026, 6, 15, tzinfo=timezone.utc)
    repo._builds["x1"] = {
        "id": "x1",
        "customer_id": _CUSTOMER_ID,
        "connection_id": "c",
        "status": "running",
        "pack_version": "v_x",
        "stability_score": 0.5,
        "persona_count": 1,
        "error": None,
        "created_at": base,
        "completed_at": None,
    }
    repo._builds["x2"] = {
        "id": "x2",
        "customer_id": "other",
        "connection_id": "c",
        "status": "complete",
        "pack_version": "v_x",
        "stability_score": 0.5,
        "persona_count": 1,
        "error": None,
        "created_at": base,
        "completed_at": base,
    }
    repo._builds["x3"] = {
        "id": "x3",
        "customer_id": _CUSTOMER_ID,
        "connection_id": "c",
        "status": "complete",
        "pack_version": "v_x",
        "stability_score": 0.77,
        "persona_count": 4,
        "error": None,
        "created_at": base,
        "completed_at": base,
    }

    found = asyncio.run(repo.get_by_pack_version(_CUSTOMER_ID, "v_x"))
    assert found is not None and found["id"] == "x3"
    assert asyncio.run(repo.get_by_pack_version(_CUSTOMER_ID, "v_missing")) is None
