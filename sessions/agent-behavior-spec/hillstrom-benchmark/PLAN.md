# Hillstrom Email-Uplift Directional Benchmark — Implementation Plan

> Status: PLANNED (2026-06-16). Pivot target after Upworthy CTR-magnitude came back a
> confirmed null and was shown panel-unimprovable (no reader-level data).
> This is the path to a **sellable directional-accuracy claim**, and is already named
> as an alternate anchor in the #222 Tier-0 benchmark epic.

## Why this benchmark
Hillstrom (MineThatData 2008 e-mail challenge) is a **real RCT**: 64,000 customers,
8 pre-treatment features, randomized 3-arm email A/B (Mens E-Mail / Womens E-Mail /
No E-Mail), outcomes visit/conversion/spend. It is the first benchmark with BOTH
real per-customer features (→ build a TRUE v1.1 persona pack) AND randomized
directional ground-truth (→ score winner-picking). Unlike Upworthy (synthetic panel,
observational CTR magnitude — null) and Streamly (synthetic, internal-only).

## 1. Dataset obtainability — VERDICT: usable, fetch-don't-redistribute
- Canonical CSV: `http://www.minethatdata.com/Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv`
- Schema (12 cols): recency, history_segment, history, mens, womens, zip_code, newbie,
  channel (= 8 features); segment (arm); visit, conversion, spend (outcomes). 64k rows, ~3-4 MiB.
- **No explicit license.** De-facto public (bundled by TFDS, scikit-uplift, causeinfer);
  author explicitly invited analysis + sharing findings. Grey area is *re-hosting*, not analysis.
- PLAN: gated runtime fetcher (refuses under pytest/CI) + local-CSV loader, mirroring Upworthy.
  Do NOT commit raw CSV. DO commit the DERIVED persona pack JSON (it is statistics, not raw data).
- Before publishing results: one permission email to Kevin Hillstrom = cheap insurance.

## 2. Ground-truth definition (RCT → unbiased difference-in-means)
`uplift_arm(Y) = E[Y|arm] − E[Y|No E-Mail]`, arm ∈ {Mens, Womens}, Y ∈ {visit, conversion[, spend]}.
- Binary visit/conversion: two-proportion CI (or bootstrap). spend: bootstrap-percentile (zero-inflated).
- **Three nested scoring endpoints (weak→strong):**
  1. Sign agreement (null-integrity floor) = `direction_accuracy`.
  2. Arm ranking (Mens vs Womens vs No-Email) by predicted outcome = `rank_rho` PRIMARY.
  3. **Heterogeneity (the Kohavi-grade claim):** rank-ρ of predicted-vs-real PER-SEGMENT
     uplift across pre-registered strata — does the sim know men respond to men's email?
     **This is the only endpoint that isn't trivially guessable. Pre-register as headline secondary.**

## 3. Integration seams (reuse runner/cert/honesty; add adapter/loader/archive)
- (a) v1.1 pack: build ONCE offline from CSV via sidira-personas GMM (`run_personas_pipeline`,
  persona_builder.py:280). Mirror the Upworthy panel-loader: persist a committed
  `hillstrom_panel_v1.json` (derived stats). Column→FeatureGroup map:
  recency→loyalty_lifecycle(count); history→value_sensitivity(score);
  history_segment→value_sensitivity(categorical); mens/womens→motivations_jtbd(flag);
  zip_code→demographic_identity(categorical); newbie→loyalty_lifecycle(flag);
  channel→channel_tech_behavior(categorical). Outcomes EXCLUDED from clustering.
  → pack carries centroid_full/feature_scale/sample_rows → render_individual_row()
  fires the `individual_row_synthetic` tier (FIRST benchmark to exercise it with real data).
- (b) Each arm = A/B case: control="No E-Mail", treatment=promo email as CHANGED copy delta,
  metric_name="conversion" (registered), reverse_figma inbox→site `click_email` transition.
  GroundTruth = RCT per-arm uplift. treatment_fraction=0.5 paired split (as Upworthy).
- (c) Run engine: `eval_engine_blind`/`run_blind_eval` reused — BUT `eval_engine_blind` hardcodes
  `_ENGINE_METRIC_NAME="ctr"` (benchmark_runner.py:77) + `_ctr_hypothesis_for_case` (line 104).
  **PARAMETERIZE the metric (default "ctr" preserves Upworthy byte-for-byte).**
  ⚠️ HIGH-BLAST-RADIUS shared fn — run `gitnexus_impact({target:"eval_engine_blind"})` first;
  existing test suite = regression gate.
- (d) Score: run_blind_eval already emits rank_rho/direction_accuracy/CI/baselines/null-cert.
  Add `by_arm`/`by_segment` stratifier to benchmark_honesty.

### Files
ADD: adapters/hillstrom_panel_loader.py; adapters/hillstrom_panel_v1.json (derived pack);
services/hillstrom_archive.py (gated fetcher+offline build script); services/hillstrom_adapter.py
(rows→cases+ground-truth math); tests/test_hillstrom_*.py.
TOUCH: services/benchmark_runner.py (parameterize metric — IMPACT-ANALYZE FIRST);
services/metric_registry.py (register `visit`); schemas/simulation.py:56 (metric_name Literal +="visit");
services/benchmark_honesty.py (by_arm/by_segment); cli.py (benchmark-hillstrom command).

## 4. Cost + probe design (cost is NEGLIGIBLE)
A/B: population_size is PER-ARM; ~3.5 LLM calls/agent; 2 arms/case; Groq llama-3.3-70b.
| Run | cases | pop/arm | calls | Groq $ |
|---|---|---|---|---|
| Smoke (CI-off) | 2 | 5 | 140 | <$0.05 |
| Scoped probe (conversion only, no strata) | 2 | 30 | 840 | ~$0.20-0.40 |
| Pre-reg full (2 arms × ~4 strata, conversion+visit) | ~16 | 100 | 11,200 | ~$3-6 |
Anthropic robustness run ≈ 10-20× → still <~$100. Binding constraint = wall-clock/rate-limit, not $.
Discipline (mirror Upworthy): pre-register (canonical-JSON SHA-256, git-commit hash) BEFORE run;
freeze the feature-mapping in the pre-reg (researcher-DOF); probe first; then sealed full run.
EC2: ONE process, per-case fresh SimulationRunner (bounded mem), checkpoint prediction_cache to
bind-mount (resumable across redeploy), Groq default, per-run user approval. **Could also run LOCALLY
with Groq keys (avoids the shared-prod-box storm/OOM risk entirely) — prefer local for the probe.**

## 5. Risks / blockers (honest)
- `visit`/`spend` not registered metrics (metric_name is a CLOSED Literal). conversion works today;
  visit needs 1 registry+Literal addition; **spend is continuous/zero-inflated — sim has no elicitor → DROP from v1.** Scope v1 = conversion + visit (discrete-choice uplift, not revenue).
- `eval_engine_blind` CTR-hardcoded → default-preserving refactor + impact analysis + tests.
- **The sellability crux:** a positive ARM-RANKING result is NOT Kohavi-proof (trivial email>no-email;
  baselines expose it). The credible claim is endpoint #3 heterogeneity — and it CAN legitimately fail.
  Pre-register #3 as headline and report honestly even if null (Upworthy discipline).
- Conversion effect is small (~0.5-1pp) → may come back `underpowered`; power for it (pop may need >100).
- One RCT = one data point. Generality needs a 2nd anchor (Criteo uplift) — natural follow-up.
- **Sellable framing:** "the simulator reproduces the DIRECTION and ORDERING of real
  randomized-experiment outcomes, including who responds most — validated blind, pre-registered,
  on a public RCT." Magnitude/CTR prediction stays explicitly out of scope (honest-null on that).

## Execution sequence
1. PR-A (plumbing, no LLM run, fully offline-testable): parameterize metric in eval_engine_blind
   (impact-analyze first) + register `visit` + hillstrom_archive (gated fetcher) + hillstrom_adapter
   (cases + ground-truth math) + tests. Build+typecheck+tests green → codex review → merge.
2. PR-B (pack): offline GMM build of hillstrom_panel_v1.json from fetched CSV (needs sidira-personas
   env, Python 3.11) + loader + by_arm/by_segment honesty stratifier + tests.
3. Pre-register + scoped probe (LOCAL, Groq, ~$0.30) → confirm null-cert PASS + non-degenerate.
4. Pre-register + sealed full run → score endpoints #2/#3 → honest result artifact.
5. Feed into the benchmark report / whitepaper (honest-null on magnitude + directional result here).
</content>
</invoke>
