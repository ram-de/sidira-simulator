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

## Lifecycle & refresh (decided)

The persona pack and the manifest have DIFFERENT dependencies — only the manifest needs the
crawl. Gate accordingly; don't over-mandate.

- **Persona pack** = feature-store only (clusters users; doesn't read the crawl). **No
  crawl gate** — build on feature-store connect (#212 starter fallback already assumes packs
  exist independently). Onboarding *guides* the sequence; it doesn't hard-block.
- **Estimability manifest** = feature-store × crawled capabilities. **Hard prerequisite: a
  completed crawl** — it cannot link capabilities that don't exist. Mandate THIS step only.
  Principle: *mandate hard data dependencies, guide soft sequencing.*

- **Refresh cadence** — feature-store connection gets a configurable `cadence`
  (`weekly`/`on_demand`, mirroring `CrawlSetup.cadence`). Each refresh rebuilds pack +
  manifest as a NEW version; `latest` pointer flips atomically (same as v_1/v_2 today).
  Feature-store cadence is INDEPENDENT of crawl cadence (data vs features drift differently);
  the manifest rebuilds when EITHER moves. Customer-configurable — refreshes cost Snowflake
  credits.

- **New crawled feature → trigger (decided: notify + on-demand/cadence):**
  1. *Auto + free:* update the manifest's capability↔column LINK map immediately (metadata
     match against the cached column catalog — no feature-store query). The manifest always
     knows what's pending.
  2. *Deferred + paid:* the feature-store query + effect FIT runs on the next scheduled
     refresh OR an explicit "refresh now". Pending features are flagged.
  3. **Honesty rail:** a feature whose effect hasn't been extracted yet **routes to LLM** —
     the manifest NEVER claims empirical coverage it hasn't actually computed. (This also
     happens to be the safe default: auto-claiming coverage pre-extraction is the only
     dangerous path.)

## Confidence gate — the negative-control guard (validated iter0→iter2)
Overlap/positivity is necessary but **NOT sufficient**: in the iter0 self-blind challenge the
overlap-based confidence signal flagged **0 of its 3 errors** — unobserved confounding leaves
*observed*-covariate overlap looking healthy, so the estimator was confidently wrong exactly
when it was wrong. The fix that replicated held-out (iter2, LEAD):

- For each (T→Y) estimate, also estimate **T → a negative-control outcome** (a metric the
  change should NOT cause but which shares the confounding). A non-zero effect there is residual
  confounding the overlap diagnostic can't see.
- **Trip → abstain → route to LLM when `|neg_control effect| > 0.05`.** On fresh held-out data
  this caught **both** unobserved-confounder errors with **zero** false alarms on the
  observed-confounding wins (including the sign-flip case the empirical core exists to win).
- **Use a SET of candidate negative controls and trip on consensus (max |residual|).** A single
  control is a gamble on coupling strength — a weakly-coupled one under-trips (iter3: real
  Hillstrom `newbie` missed the bias). Consensus over several controls recovered full sensitivity
  with no specificity loss (iter4 held-out 4/4 + 4/4; corroborated by the real Hillstrom sweep).
  `negative_control_guard()` accepts the set and returns per-control effects.
- **Known limit (pre-registered, confirmed):** a negative control does NOT catch a *true-null*
  estimator residual on *observed* confounding — that needs a separate guard. Negative controls
  are a necessary gate, not a full certificate.
- **Router job:** identifying *which* feature-store metric is a valid negative control for a
  given hypothesis is a domain/LLM task (the LLM earns its keep here even on the empirical path).

## Honesty rails
- Empirical estimate ALWAYS ships with overlap/positivity diagnostics + the naive-vs-
  adjusted gap (big gap = strong confounding correction = read carefully) **+ the negative-
  control check above**.
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
