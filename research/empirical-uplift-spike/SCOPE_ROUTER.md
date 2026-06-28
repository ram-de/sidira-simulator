# Scope — the feature-expressibility ROUTER (productizing the survivor)

## Why
The spikes settled it: the **empirical/causal route** is the only mechanism that beats
chance, validated on two real datasets (Cookie Cats, Hillstrom). LLM-prompting (persona /
no-persona / council) sits at/below chance. So the product move is not "replace the LLM"
— it's a **router** that sends each hypothesis to the engine that can actually answer it,
and labels confidence honestly. This carves out a *provably accurate, sellable slice* now.

## The decision
For a customer hypothesis + their connected data, decide EMPIRICAL vs LLM by one question:
**can the change be expressed as a measurable contrast (treatment T → outcome Y) whose
variation already exists in the data, with enough support to estimate it?**

```
hypothesis + data schema
        │
        ▼
 (1) MAP  ── LLM-assisted: hypothesis → {treatment T, contrast, outcome Y, covariates X}
        │     (LLM as TRANSLATOR, not predictor; human-confirmable)
        ▼
 (2) SUPPORT CHECK ── pure data/stats, no LLM:
        • T exists & varies in the data?        • Y measured?
        • both arms have ≥ N samples?           • covariate overlap / positivity ok?
        ▼
   supportable? ──── yes ──► EMPIRICAL: causal_estimator → ATE, sign, CI, overlap warnings
        │                                  (provably accurate; the DashPass case)
        └──── no ──► LLM ENGINE (current): directional, FLAGGED low-confidence
                                  (the novel-feature case)
```

## Build pieces
1. **`causal_estimator.py` (FOUNDATION — build first).** Route-agnostic core extracted +
   generalized from `realdata_uplift.py` / `realdata_hillstrom.py`:
   `estimate(df, treatment, outcome, covariates) -> {naive, t_learner, ipw, overlap
   diagnostics, naive_vs_adjusted_gap}` + `support_check(...) -> {supportable, reasons}`.
   Validated against both real datasets. No LLM, no customer dependency — buildable now.
2. **Hypothesis→spec mapper.** NL hypothesis + schema → {T, contrast, Y, X}. LLM-assisted,
   returns a structured, user-confirmable spec. (Reuses the existing chat client.)
3. **Router + pre-flight surface.** Glue: run mapper → support_check → route. Extends the
   existing **answerability pre-flight (epic #309)** with an "empirically estimable from
   your data?" branch + a card showing route taken, why, and confidence.
4. **Wire empirical output into the result + the #222 calibrator slot.** The empirical
   estimate is a natural ground-truth anchor for the `conversion_calibrator` (currently a
   no-op IdentityCalibrator).

## Build-time precompute architecture (grounded in the real code)

The router should NOT re-scan the feature store per hypothesis. The feature store and the
crawl are both available at pack-build time, so we precompute an **estimability manifest**
— the router's lookup table + pre-fit candidate effects — and ship it as a pack artifact.
Runtime becomes match + retrieve, not ingest + fit.

**The seam that's missing today** (confirmed by code read): there is *no* link from
feature-store columns to crawled product surfaces. Column metadata is discovered on-demand
via `FeatureStore.preview()` → `ColumnProfile` (`adapters/feature_stores/__init__.py`); no
precomputed index exists. Building that join IS the router's "MAP" phase, done once.

### What precomputes (new build step, emitted next to the persona pack)
Reads two existing build outputs and joins them:
- feature-store `ColumnProfile`s (name/dtype/null_fraction/distinct_count) — the T/Y/X
  inventory with variation;
- the feature pack's `Capability.surfaces` / `capability_name` (`schemas/crawl.py`) — the
  crawled product levers.

Emits `estimability_manifest.json`, keyed by `(customer_id, setup_id, pack_version)` and
stored beside `persona_pack.json` in R2
(`customers/<id>/personas/<version>/…`, mirroring `adapters/persona_loader.py`):
1. **column catalog** — role-tagged (treatment-candidate / outcome / covariate), with support.
2. **capability ↔ column linkage** — which crawled levers are actually represented as data.
3. **candidate (T → Y) grid** — finite, enumerated from the crawled capabilities × metrics.
4. **pre-fit causal effects** for that grid via `causal_estimator.estimate()` (queries the
   feature store ONCE at build, stores effect + `support_check` diagnostics). This is the
   part bigger than caching the router — the runtime stops fitting models at all for the
   common case. (Also avoids re-billing Snowflake credits per hypothesis.)

### What stays at runtime (now cheap)
Hooks into `SimulationOrchestrator.prepare()` (`services/simulation_orchestrator.py`), which
already loads the persona pack + feature pack + capability and knows `hypothesis` +
`setup_id`:
- **MAP** — `hypothesis.prose` → catalog entry (LLM-as-translator), matched against the
  *prebuilt* catalog, not raw data.
- **ROUTE + retrieve** — matched & supportable → return the precomputed effect instantly →
  empirical result. Unmatched/novel lever → existing `SimulationRunner.run()` LLM path, flagged.
- **fallback fit** — only for novel conditioning (subgroups) not in the grid: one fit on the
  cached design matrix.

### Staleness
The manifest is a pack artifact, so it rebuilds on every data refresh and rides the existing
pack version (v_1, v_2 by week). No new staleness class.

## Honesty rails
- Empirical estimate ALWAYS ships with overlap/positivity diagnostics + the naive-vs-
  adjusted gap (big gap = strong confounding correction = read carefully).
- Empirical only claims the slice it can support; everything else is LLM + low-confidence
  label. Never silently treat an LLM directional guess as if it were data.
- Off-support / novel changes (spike S2): empirical must ABSTAIN, not extrapolate.

## Order
1. `causal_estimator.py` foundation (this PR — DONE).
2. **Build step → `estimability_manifest.json`** (the precompute): column catalog +
   capability↔column linkage + candidate (T→Y) grid + pre-fit effects, emitted beside the
   persona pack. The heavy lift; everything downstream is lookups.
3. Manifest loader + **MAP** (hypothesis→catalog entry) in `SimulationOrchestrator.prepare`.
4. **Router + pre-flight surface** (extends answerability #309): match → retrieve → route;
   card showing route taken, why, confidence.
5. Wire empirical estimate into the `MetricCalibrator` seam (#222 — replace the no-op
   `IdentityCalibrator` in `services/conversion_calibrator.py`).
```
