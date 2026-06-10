---
type: session
domain: sample-workspace
status: active
started: 2026-06-09
owner: ram-de
---

# Session: sample-workspace — per-org sample workspace seeding

## Goal
Let any org seed its empty workspace with the Streamly sample persona pack + feature pack via an explicit button click, so new tenants have something to play with post-cutover.

## In Progress
- [ ] PR as ram-de → squash-merge → ExitWorktree

## Completed
- [x] Backend: `POST /sample-workspace` (api/sample_workspace.py) — tenant-scoped clone, source hardcoded `streamly_sample`, 409 no-clobber, pointers written last; registered in main.py; `get_artifact_store` dep added to deps.py
- [x] Tests: 13 in test_sample_workspace.py (201 summary, loader round-trip, customer_id rewrite in pack + manifest, source untouched, 409 ×3, 503 ×3, retry-after-partial ×2, marker stamping) — full suite 444 passed; route-walk tenant guard passes
- [x] Frontend: `components/SampleWorkspaceCard.tsx` (DESIGN.md-compliant: 4px radius, ink button, hairline rule, monochrome) — wizard shows it only when BOTH /capabilities and /personas 404; personas page uses `detectEmpty` dual-probe mode
- [x] Codex round 1: 2×P1 (half-seeded retry deadlock → `cloned_from` marker recovery; check-then-write race → re-check immediately before pointer writes), P2 (source corruption → 503 not 500), P3 (UI offered card to partially-seeded tenants → both-404 gating) — all fixed + pinned by tests
- [x] Codex round 2: P2 (manifest valid-JSON-but-not-object → TypeError 500 → now ArtifactSchemaError → 503) fixed + test; residual P1 re-check window accepted (store protocol has no CAS — documented in module docstring)
- [x] Verify: pytest 444 passed / ruff clean / black clean / next build clean

## Next Steps
1. PR as ram-de, squash-merge, ExitWorktree

## Key Files
- `backend/sidira_simulator/api/sample_workspace.py` — the clone endpoint (new)
- `backend/tests/test_sample_workspace.py` — coverage (new)
- `frontend/components/SampleWorkspaceCard.tsx` — the button UI (new)
- `local-artifacts/customers/streamly_sample/` — the source fixture (committed; prod copy already in R2)

## Key Context
- **Tenancy decision:** the endpoint takes NO source-customer parameter — `streamly_sample` is hardcoded server-side. A caller-supplied source would be a tenant-isolation hole (read any org's packs by id).
- **No-clobber decision:** 409 if the target tenant already has a personas or featurepacks `latest` pointer. The sample never overwrites real data.
- **Atomicity:** content artifacts are written first, `latest` pointers last. A mid-clone failure leaves no pointer, so a retry POST passes the 409 check and re-clones cleanly.
- Clone works purely through the `ArtifactStore` protocol (read_text/write_text) — identical behavior on LocalArtifactStore (dev) and R2 (prod). Prod R2 already contains the streamly_sample tree (beta sims ran on it).
- `customer_id` fields inside persona_pack.json and both manifests are rewritten to the target tenant.
- Streamly fixture has no `prompts/*.md` and nothing reads them at runtime — not cloned. `hypotheses/` also skipped (not API-served).

## For my cofounder
Post-cutover, new orgs land in an empty workspace ("No capabilities found"). This session adds a one-click sample seeding flow: the Streamly streaming-vertical fixture (6 personas, 2 capabilities) cloned into the org's own tenant prefix. Button-only — never automatic.
