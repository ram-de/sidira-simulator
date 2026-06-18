# Streamly H-001 — engine plumbing + face-validity dry-run (NOT accuracy validation)

Ran the REAL engine (`SimulationRunner`) on the Snowflake-extracted `streamly_sample` persona
pack + crawled `continue_watching` capability + the H-001 Smart-Resume hypothesis, bypassing the
DB repos. Streamly is fictional → no real outcome. This is a readiness + face-validity exercise.

## What ran
- 24 agents (12/arm, treatment_fraction 0.5), conversion metric, Sonnet, run_seed 42. Engine
  loaded pack + capability, materialized both arms, produced a structured result. **Plumbing: OK.**

## The quantitative result is UNTRUSTWORTHY — and the engine says so
- lift **+1.3**, CI **[−8.2, +9.5]** (spans zero), confidence_score **22/100**.
- treatment_score 22.4 vs control_score 59.8 (underlying scores favored control; +1.3 is noise).
- Engine guards fired on every agent: **`metric ran UNBLINDED — low-confidence`** (H-001 is a
  removal/restructure with no rendered treatment design — prose only) and **`identity_seed
  fallback — upgrade pack to v1.1`** (extracted pack lacks the v1.1 quad → degraded variance).
- Reading: do NOT treat +1.3 as "ship it." The engine correctly down-weighted itself — the same
  honest behavior the campaign relies on.

## The weakness-surfacing WORKED (the case-1 value)
- **12/12 agents flagged `hidden_guardrail_risk`**; **6/12 flagged `wrong_cohort`** — matching the
  PM's own authored concern (removing the visible rail risks browse/diversity for some cohorts).
- This is concrete, actionable, and on-point — the defensible "directional-hypothesis + weakness-
  surfacing" mode, demonstrated. (Still face-validity vs a human's obvious prior, not proof of
  correctness.)

## The lesson for the real pilot (added to the scorecard)
A high-confidence engine run needs the design partner to provide: **(1) a v1.1 persona pack** (rich
per-user features, not just centroids) and **(2) a RENDERED treatment design** (figma/screens), not
a prose change description — otherwise the engine runs unblinded and self-flags low-confidence.

## Verdict
Plumbing ✅ readiness confirmed end-to-end on a customer-shaped pack; weakness-surfacing ✅ useful;
quantitative lift ❌ untrustworthy (engine-flagged). Mock data did its job: a clean dry-run that
exercised the real path and surfaced the exact input requirements — it did NOT and cannot validate
accuracy.
