# Wizard estimability declaration — metric registry first, then levers

**Status: SHIPPED + DEPLOYED 2026-07-08** (backend PR #605 → SSM deploy → frontend PR #606 → Amplify). Tickets: #596 (wizard), #597 (metric registry). Strategy context: the semantic-contract council verdict — grow a minimal semantic contract from the estimability manifest; registry metadata may only enable resolution or force abstain, never upgrade a guard verdict.

## What shipped

### Backend (PR #605, merged f723f46, deployed + verified in-container)

`EstimabilityBuildConfig` (persona_builder.py) gains two registries, both `extra="forbid"`:

- `MetricRegistryEntry`: `column`, `display_name?`, `semantic_type?` (rate/duration/cumulative/count), `description?`, `synonyms?`, `pre_period_column?`
- `LeverRegistryEntry`: `column`, `display_name?`, `description?`

`compiled()` replaces the verbatim `model_dump(exclude_none=True)` in `_build_pipeline_config` and folds the registries into the keys the producer already consumes:

- registry metric columns append to `outcomes` (explicit order preserved, deduped)
- lever columns append to `treatments`
- `pre_period_column` contributes `{column: [pre]}` to `neg_control_map` — **explicit declarations always win**
- registries ride the compiled dict + `config_json` verbatim (producer ignores unknown keys — verified: `pipeline.py` parses `cfg["estimability"]` with named `dict.get()`)

Guarantees: registry-less config compiles **byte-identically** to the old dump; empty `[]` registries normalize away (wizard-default safety); duplicate columns and `pre_period_column == column` rejected by name. Tests 25 → 36 in `test_persona_builder_binding.py` (compile paths, explicit-wins, byte-identity incl. empty-list edge, compiled-dict aliasing isolation, JSON round-trip).

### Frontend (PR #606, merged 27410ec)

New opt-in **Ground** step at position 3: Connect / Map / **Ground** / Build / Evaluate / Promote (all downstream step numbers, labels, `canContinue`, `documentsTerminal`, rerun targets renumbered — audited exhaustively).

Ordering is deliberate (#597): **01 · Outcome metrics** (numeric columns; declaring a pre-period column compiles a negative control) → **02 · Levers** (binary exposure flags: bool dtype or ≤2 distinct sampled values) → **03 · Guard review** (read-only GUARDED ✓ / UNGUARDED · / DECLARED ✓, mono words carry state per DESIGN.md §8.2; UNGUARDED is allowed but stated honestly — it never blocks). Compact manifest rail rides steps 3–4 on the feature-store path (§7.4 posture, sticky, collapses ≤1023px). Documents packs get a preview-only note (no build for a declaration to ride).

Payload law: toggle off (default) ⇒ no `estimability` key — byte-identical to the pre-Ground wizard. Toggle on ⇒ `enabled: true` + non-empty registries only + `nc_diagnostics: true`; optional entry fields omitted when empty. Selections are read *through* the live candidate lists (stale drafts can never ride); any source change resets Ground state. Opted-in Continue requires ≥1 metric AND ≥1 lever.

## Verification chain

1. Backend: 72 tests green re-run independently from the worktree; codex review no P1/P2, both P3s fixed (empty-registry normalization + aliasing test).
2. Deploy: SSM Success; in-container: prod `EstimabilityBuildConfig` carries both registries; `compiled()` smoke correct.
3. Frontend: `tsc --noEmit` clean + `next build` green re-run independently; codex P1 = stale-worktree false positive (registry contract already deployed — the point of backend-first merge order), P2 (mapping-ignored column declarable) judged intentional — estimability declarations are orthogonal to persona feature-group mapping, outcome/lever columns need not be persona features; P3s fixed (documents note, toggle a11y name, rail feature-store-only).
4. End-to-end contract smoke **in the prod container**: the exact wizard-emitted JSON parses as `BuildConfig` and compiles to `outcomes=[watch_hours_wk]`, `treatments=[offline_downloads]`, `neg_control_map={watch_hours_wk: [watch_hours_pre]}`; toggle-off payload round-trips with no estimability key. Producer side of the chain (folded keys → manifest + NC guards) was proven live in the v_5 richness test (9/9 true effects, 3/3 confounded trips) with identical key shapes.

## Deliberate scope cuts / follow-ups

- Pre-period column picker offers other numeric columns; no dtype-compatibility or naming heuristics yet.
- Lever candidacy uses sampled `distinct_count ≤ 2` — a low-cardinality non-flag column can qualify; the copy states the 1/0 exposure contract instead of enforcing it.
- Temporal roles (#598), drift-diff (#600), and covariate temporal eligibility (#599) remain open — the registry is the substrate they attach to.
- No wizard UI yet for explicit `treatments`/`outcomes`/`neg_control_map` overrides (white-glove API still works; explicit-wins semantics already in place).
