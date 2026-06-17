# v1.1 Persona-Pack Pipeline — End-to-End Feasibility (Cookie Cats)

**Date:** 2026-06-17
**Scope:** Plumbing / integration readiness ONLY. No accuracy, directional,
predictive, or scoring result is computed, claimed, or implied. No simulation
run, no LLM elicitation (`no_llm=True`), no Groq/Anthropic/box calls. A negative
result would have been equally valid; this one happens to be positive.

## What this proves (and does not)

It proves that the currently-dormant v1.1 real-data persona-pack pipeline fires
end-to-end on a real dataset: a real per-user table builds a v1.1 producer pack
(with the centroid_full / feature_scale / sample_rows / posterior_mean quad),
that pack translates 1:1 into the simulator's `PersonaPack`, and the consumer's
`render_individual_row` consumes the quad to emit a grounded, per-agent
individual-row behavioral profile that varies by `sample_index`.

It does **not** prove anything about persona quality, causal validity, or
prediction. See caveats.

## Data source

- **Source used:** committed fixture
  `backend/tests/data/cookiecats_sample.csv` (the public DataCamp mirror at
  `raw.githubusercontent.com/datacamp/careerhub-data/.../cookie_cats.csv`
  returned **HTTP 404** — gone from that path — so the fallback was used).
- **Rows:** 400 (header + 400 data rows; full Cookie Cats is ~90k).
- **Columns:** `userid, version (gate_30/gate_40), sum_gamerounds,
  retention_1 (bool), retention_7 (bool)`.

## Config used (feasibility config — `build_pack.py`)

- `user_id_column: userid`
- `feature_groups`:
  - group `engagement`: `{sum_gamerounds, count}`
  - group `retention`: `{retention_1, flag}`, `{retention_7, flag}`
- `encoder`: PCA, `embedding_dim_per_group: 2` (only 1–2 features per group)
- `cluster`: GMM, `k_range [3,6]`, BIC, `random_state 42`, `bootstrap_iters 8`,
  `stability_threshold 0.5`, `holdout_frac 0.2`
- `weights`: `schemes [headcount]` (no orders/revenue column available)
- `sampling`: `n_synthetic_rows 16`, `random_state 42`
- No prefilter, no categorical/json/tenure features (none exist in the data).

These three features are the **only** per-user features Cookie Cats provides and
were chosen purely to exercise the pipeline — see caveats.

## Step results

### 1. Build (producer, sidira-personas venv)

- `run_pipeline(df, cfg, run_id="cookiecats-feasibility", no_llm=True)` ran
  clean (one benign joblib `sysctl` sandbox warning, no functional impact).
- `pack.schema_version == "1.1"`. **v1.1 quad PRESENT.**
- `k_selected = 5`, 5 discovered personas (P01–P05), no FIXED personas.
- Every persona carries a non-empty quad:
  `centroid_full = 3` keys, `feature_scale = 3` keys, `sample_rows = 16`,
  `posterior_mean` present (5-component soft posterior).
- Pack written to `producer_pack.json`.

### 2. Translate (consumer, simulator backend venv, worktree source)

- `translate_producer_pack(producer, version="v_feasibility")` succeeded.
- Result: `PersonaPack(schema_version="1.1", customer_id="cookiecats",
  n_personas=5)`; the quad passes through 1:1 onto each `Persona`
  (`centroid_full`/`feature_scale` keyed on
  `sum_gamerounds, retention_1, retention_7`; 16 `sample_rows`).

### 3. Render (consumer, `render_individual_row`)

For every persona at `sample_index ∈ {0,1,2,3}`:
`grounded = True`, `source_tier = "individual_row_synthetic"`. The grounded
individual-row tier fires (it requires `sample_rows` AND `centroid_full` AND
`feature_scale` all present — all three are).

Per-agent variation is real. Example (P01):

| sample_index | grounded | tier | deltas |
|---|---|---|---|
| 0 | True | individual_row_synthetic | sum_gamerounds z=+0.759 → "somewhat higher" |
| 1 | True | individual_row_synthetic | sum_gamerounds z=−1.318 → "much lower" |
| 2 | True | individual_row_synthetic | (none salient; 1 suppressed) |
| 3 | True | individual_row_synthetic | sum_gamerounds z=+0.787 → "somewhat higher" |

Distinct delta-signatures across idx 0–3: **4 of 4** for P01 and P02, 2 of 4 for
P03 — i.e. different `sample_index` values yield distinct within-cluster
deviations, proving per-agent variation works.

**Observed (expected) behavior on the retention flags:** within each cluster the
`retention_1`/`retention_7` flags are near-constant, so the producer floors
their `feature_scale` to `1e-9` (its zero-floor for constant-in-cluster
features). The consumer's `_DEGENERATE_SCALE` guard (1e-6) correctly skips them
rather than emitting an astronomical bogus z. Only `sum_gamerounds` has genuine
within-cluster variation, so it is the sole rendered delta. This is the
honesty/degradation path behaving exactly as designed — not a break.

## Honest caveats

- **Limited features.** Only 3 per-user features exist; clustering and
  within-agent variation effectively rest on one continuous feature
  (`sum_gamerounds`), with the two flags degenerate within clusters.
- **Post-treatment / mediator.** `sum_gamerounds` is measured AFTER the gate
  (gate_30 vs gate_40) treatment and is a mediator of the outcome. This pack is
  therefore a plumbing exercise, **not** a causal or baseline persona model. The
  personas are not a valid pre-treatment segmentation.
- **No clean pre-treatment covariates.** Cookie Cats ships no baseline
  demographic/behavioral columns, so a causally-valid persona build is not
  possible from this data regardless of pipeline health.
- **Readiness, not accuracy.** Nothing here measures or claims predictive,
  directional, or scoring performance. No simulation/LLM/box was run.

## Verdict

**YES** — the dormant v1.1 persona-pack pipeline fires end-to-end on real data:
real CSV → v1.1 producer pack with non-empty centroid_full/feature_scale/
sample_rows quad → 1:1 translate into the simulator `PersonaPack` →
`render_individual_row` returns `grounded=True`,
`source_tier="individual_row_synthetic"`, with per-agent rows that vary by
`sample_index`. No step broke.

## Artifacts

- `build_pack.py` — producer build (run with sidira-personas venv)
- `consume_pack.py` — translate + render (run with simulator backend venv)
- `producer_pack.json` — the built v1.1 pack
- `FEASIBILITY_REPORT.md` — this file
