---
type: session
domain: sample_creations
status: active
started: 2026-05-21
owner: rmkmar
---

# Session: sample_creations — build a second sample customer end-to-end

## Goal
Create a second sample customer (`streamly_sample`, a video streaming product) with a full Persona Pack, Feature Pack, and a sample PR + hypothesis — so we can demo the simulator on a domain that isn't food delivery and exercise the "different vertical" code path.

## In Progress
(none — sample verified end-to-end through real loaders)

## Completed
- [x] Pick a second vertical distinct from `demo` (DoorDash-style). Chose video streaming → `streamly_sample`.
- [x] Authored 6 personas covering heavy / weekend / lapsing / trialer / niche / background usage modes.
- [x] Authored Feature Pack snapshot `2026-W21` with two capabilities: `continue_watching`, `browse_recommendations`.
- [x] Authored sample PR + testable hypothesis: "Smart Resume hero tile replaces Continue Watching rail."
- [x] Added `featurepacks/latest` (= `2026-W21`) and `personas/latest` (= `v_1`) pointer files.
- [x] Fixed `reverse-figma.json` transitions schema — must be `from_screen` / `to_screen` / `role_gated` with screen IDs (not component IDs); trigger names the component.
- [x] Verified loading via real `PersonaPackLoader` + `FeaturePackLoader`: 6 personas; weights sum to 1.000 across head_count / order_weighted / revenue_weighted; both capabilities parse with surfaces, roles, transitions, and reverse-PRD intact.

## Next Steps
1. Wire one simulation through the orchestrator using the new persona pack + feature pack + hypothesis (`h_001_smart_resume.md`).
2. Decide whether to fold a doc into `docs/` describing the figma transition schema (Transition.from_screen / to_screen / role_gated) — fixture authoring kept guessing this wrong.
3. `/pythia-session save` to push for cofounder.

## Key Files
- `local-artifacts/customers/streamly_sample/personas/v_1/persona_pack.json`
- `local-artifacts/customers/streamly_sample/personas/v_1/manifest.json`
- `local-artifacts/customers/streamly_sample/featurepacks/2026-W21/manifest.json`
- `local-artifacts/customers/streamly_sample/featurepacks/2026-W21/capabilities/continue_watching/{reverse-prd.md, reverse-figma.json}`
- `local-artifacts/customers/streamly_sample/featurepacks/2026-W21/capabilities/browse_recommendations/{reverse-prd.md, reverse-figma.json}`
- `local-artifacts/customers/streamly_sample/hypotheses/h_001_smart_resume.md`

## Key Context
- The existing `demo` customer's persona pack uses behavioral fields like `orders_per_week`, `dashpass_active`, `avg_order_value_usd` — clearly food-delivery-shaped. A second sample in a different vertical is a useful pressure test on whether the simulator treats `behavioral_snapshot` as a free-form dict (good) or hard-codes those keys somewhere (bad).
- I kept the Persona Pack schema fields identical (`id`, `name`, `description`, `jtbd`, `behavioral_snapshot`, `centroid_features`, plus top-level `weights` with head_count / order_weighted / revenue_weighted). For streaming I renamed the third weight slot to `revenue_weighted` still (subscription revenue), and kept `order_weighted` to mean "session-weighted" — noted in the pack so we don't quietly redefine schema.
- Feature Pack `customer_id` field in `demo` is actually `"acme"` (manifest mismatch — a pre-existing quirk, not introduced here). For the new sample I set `customer_id: "streamly_sample"` consistently.

## For my cofounder
This is purely additive sample data — no code changes, no schema changes. If you want to demo the simulator on something other than DoorDash, pass `customer_id=streamly_sample` and the local artifact store should resolve everything. The sample hypothesis at `hypotheses/h_001_smart_resume.md` is the one I'd run first — it's designed to provoke disagreement across personas (binge user loves it; weekend family hates losing the rail).
