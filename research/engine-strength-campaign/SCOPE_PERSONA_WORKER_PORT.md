# Scope — port the estimability manifest + negative-control guard into sidira-personas

**Goal:** at persona-pack build time, emit `estimability_manifest.json` next to `persona_pack.json`
in R2. It pre-computes, per candidate (treatment → outcome) pair in the customer's feature store,
the causal effect AND the validated negative-control confidence gate — so at hypothesis runtime the
router just MATCHES + RETRIEVES (no Snowflake re-query, no model refit for the common case).

**Target repo:** `~/Projects/sidira-personas` (Python ≥3.11; sklearn/pandas/numpy/snowflake-connector
already deps ✓). Build on a FRESH branch off `main` (repo currently on `ram-de/friends-family-pack-443`).

### Architecture (corrected from the repo map)
- The persona-build dataframe is **already in memory** in `sidira_personas/pipeline.py::run_pipeline(df, cfg)`.
  So the manifest's `load_frame([cols])` is just **`df[cols]` — no Snowflake re-query at build time.**
- **R2 write + pack versioning are in the BACKEND** (`sidira-simulator/backend/sidira_simulator/
  services/persona_builder.py::_write_pack`, key prefix `customers/{cid}/personas/{version}/`), NOT in
  the personas library. Split the work: **BUILD the manifest in sidira-personas, WRITE it in the backend.**
- **Capabilities are NOT reachable** in the personas library (only in the backend crawler/column_mapper).
  So NO capability linkage here: treatment candidates come purely from feature-store columns
  (low-cardinality flag/categorical levers). Honest consequence: a feature store with no exposure/
  treatment column yields an EMPTY effect grid → "route everything to LLM" (correct, not a bug).
- The manifest build is PURE + offline (operates on the in-memory df + cfg), so it is fully testable
  with the existing `fixtures/synthetic_company.py` — no Snowflake/R2 needed for tests.

**What we are porting (already built + validated in research/empirical-uplift-spike/):**
- `causal_estimator.py` — `support_check`, `estimate`, and the campaign's validated
  `negative_control_guard(floor=0.05, ratio=1.5)` (3-part gate: floor + consensus + ratio).
- `manifest_builder.py` — repo-agnostic join of ColumnProfiles × Capabilities + (T→Y) effect grid.
  **Must be extended** to attach a `negative_control` verdict per candidate effect (the research
  version predates iter1-5).

---

## Phased build (the loop)

### Phase 1 — vendor the cores + guard-into-manifest (PURE, fully offline-testable)
- Add `sidira_personas/estimability/causal_estimator.py` and `.../manifest_builder.py` (verbatim
  port; drop the `__main__` self-tests, convert them to pytest).
- **Extend `CandidateEffect`** with negative-control fields: `neg_controls: list[str]`,
  `neg_control_effect: float | None`, `guard_trips: bool`, `guard_confidence: str`, `guard_reason`.
- In `build_manifest`, for each supportable (T→Y), choose negative-control candidates = other
  outcome-like columns NOT equal to Y (a pre-treatment/should-not-react metric set), call
  `negative_control_guard(df, T, Y, ncs, X)`, attach the verdict. If no NC candidates exist, record
  `guard_confidence="unverified"` (router treats unverified as low-confidence → LLM).
- Tests: port the Hillstrom-as-store self-test into `tests/` as real pytest cases (reproduce
  +4.54pp visit, womens-email linked, guard does-not-trip on the clean store; novel capability
  unlinked → LLM route). ruff + pytest must pass.
- **Gate:** ruff + pytest green, then codex review. PR #1 (cores + tests, no I/O wiring) — mergeable
  on its own, zero behaviour change to existing builds.

### Phase 2 — wire into the pipeline output (sidira-personas, confirmed seams)
- **Build call:** in `sidira_personas/pipeline.py::run_pipeline` (lines 98–466), after the pack is
  assembled, call `build_manifest(df, cfg, load_frame=lambda cols: df[cols])`; attach to a new
  `PipelineResult.estimability_manifest` field (dataclass at pipeline.py:80–95). The CLI
  (`cli.py::run`, after line 54) serializes it to a local artifact for local runs.
- **column_profiles** derived from the in-memory `df`: name, dtype, distinct_count, null_fraction —
  no separate profiling pass needed.
- **treatment candidates** from cfg `feature_groups` metrics typed `flag`/`categorical` (low-
  cardinality levers) + any df column with ≤10 distinct non-null values; **outcomes** by name hint.
  **Cap the grid** (e.g. ≤8 treatments × ≤8 outcomes); if capped, record it in the manifest (no
  silent truncation). Empty grid is a valid, expected outcome.
- **knob:** config `estimability: {enabled: bool}` (default FALSE) — additive, off by default.
- **robustness:** wrap the whole manifest build in try/except so it can NEVER fail or slow the pack;
  on error attach `estimability_manifest = {"status": "error", "reason": ...}` and continue.
- Tests use `fixtures/synthetic_company.py` (no Snowflake). **Gate:** ruff + pytest + codex → PR #2.

### Phase 3 — write it in the backend (sidira-simulator, my current worktree)
- In `backend/.../persona_builder.py::_write_pack` (lines 283–303), after writing `persona_pack.json`,
  if `output.estimability_manifest` is present write it to
  `customers/{customer_id}/personas/{pack_version}/estimability_manifest.json` via `self._store.write_text`.
  Reuses the pack's `pack_version` verbatim → manifest and pack versioned together.
- Guard with the same additive discipline (skip if absent/None; never fail the pack write).
- **Gate:** backend tests + codex → PR #3. Then a founder-gated guarded enable on one real build
  (manifest written but unused until the router reads it — a later sidira-simulator epic).

---

## Guardrails
- **Money path is untouchable.** Manifest build is wrapped so it cannot break or slow the pack
  build; OFF by default; additive R2 artifact only.
- ruff + pytest are the gates (black is not). Run `/opt/homebrew/bin/python3.11 -m pytest`.
- Every PR: ruff+pytest green → codex review → merge as `ram-de`. Codex may be flaky — if it idles,
  proceed on green tests + self-review and note codex was unavailable.
- Heavy implementation delegated to a fresh general-purpose agent in an isolated git worktree of
  sidira-personas (not a fork); one agent per phase, reviewed before merge.
- Backend deploy NOT triggered by this (persona-worker has its own deploy path; founder-gated).

## Done =
manifest builds beside the pack in R2 for a real build, includes the negative-control verdict per
candidate effect, OFF-by-default knob, full test coverage, both PRs merged. Promotion to the router
(reading the manifest at hypothesis time) is the NEXT epic, in sidira-simulator backend.
