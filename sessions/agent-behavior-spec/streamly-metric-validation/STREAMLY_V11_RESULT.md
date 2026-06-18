# Streamly H-001 — v1.1 blinded higher-fidelity dry-run (READINESS + FACE-VALIDITY, NOT accuracy validation)

> **Streamly is FICTIONAL.** There is no real A/B outcome. This exercise tightens the
> engine dry-run to a higher-confidence, *blinded* run and does a per-persona
> face-validity check against the PM's authored expectations. It is NOT proof of
> correctness and must never be presented as such.

## What changed vs the prior low-confidence run

| | Prior plumbing run | This v1.1 run (`v_2` pack, rendered treatment) |
|---|---|---|
| Persona pack | `v_1` v1.0 (hand-authored, no quad) | `v_2` **v1.1** rebuilt from Snowflake (`STREAMLY.SYNTHETIC.USERS_FEATURE_STORE`, 2500 rows) with the **full quad** on all 7 personas |
| Treatment | prose only (UNBLINDED) | **rendered `proposed_figma`** (Smart Resume hero ReverseFigma) + `proposed_prd` → **blinded** |
| Population | 24 (12/arm) | 40 (20/arm), `treatment_fraction` 0.5, Sonnet, seed 42 |
| `UNBLINDED` flag | **fired** (every agent) | **CLEARED** — `metric_lift_unblinded_fallback=False`, 0 occurrences in log |
| `identity_seed fallback` flag | fired | **STILL FIRES** — see blocker below |
| lift / CI | +1.3 / [−8.2, +9.5] (spans 0) | **−13.3 / [−21.5, −4.6]** (separable, negative) |
| confidence_score | 22 / 100 | **11.7 / 100** |
| treatment vs control | 22.4 vs 59.8 | **11.7 vs 66.9** |

## Headline result (v_2 v1.1 pack, blinded)

- **lift −13.3**, **CI [−21.5, −4.6]** — now **excludes zero** (prior CI straddled it). The sign is unambiguous: sentiment favors the **control** (current product).
- **confidence_score 11.7** (LOWER than the prior 22). This is correct, not a regression: the prior run was a noisy near-null; this run is a *separable negative*, and the engine's confidence reflects "this hypothesis looks bad," not "we're unsure."
- Weaknesses surfaced: `hidden_guardrail_risk` (17/20 agents), `wrong_cohort` (17/20), `broken_mechanism` (10/20), plus a notable engine note:
  > "The conversion metric is positive and separable (+7.5pp), but sentiment is negative and separable (−13.3) … the metric would greenlight a change users dislike. Pre-calibration, trust sentiment for harm: do not ship on the metric alone."

  This metric-vs-sentiment divergence is exactly the honest behavior the campaign relies on.

## One degradation CLEARED, one STILL OPEN (honest blocker)

The prior run flagged TWO degradations. Only one is fixable with the inputs available.

1. **`metric ran UNBLINDED` — FIXED.** Authoring a rendered `proposed_figma` (the Smart Resume hero `ReverseFigma`, `smart_resume_proposed_figma.json`) gave the treatment renderer a faithful standalone view, so `RenderedChange.has_structural_diff()` is True and the metric pass no longer falls back to the demand-inducing unblinded prompt. Verified: `metric_lift_unblinded_fallback=False`.

2. **`identity_seed fallback` — STILL FIRES (BLOCKER, not fixable here).** This warning is governed by `persona.behavioral_seeds`, **NOT** by the v1.1 quad. The `sidira-personas` pipeline (`run_pipeline`) emits the quad (`centroid_full` / `feature_scale` / `sample_rows` / `posterior_mean`) but **never emits `behavioral_seeds`** — and the producer→consumer translator (`persona_pack_translator.py`) explicitly defaults `behavioral_seeds=None`. So a freshly-rebuilt v1.1 pack carries the quad yet still trips the fallback. The prior run's note ("upgrade pack to v1.1") conflated two independent fields; the quad rebuild does not, by itself, silence this warning. Closing it requires the personas pipeline to additionally emit per-persona `behavioral_seeds`.

## STEP A1 — v1.1 re-extraction: SUCCEEDED

- Connected to the live Snowflake table via **key-pair JWT** (the `sidira` connection; `~/.snowflake/connections.toml` + `sidira_snowflake_key.p8`). The `io.read_snowflake` *password* path was bypassed because the table was loaded with JWT auth and no password creds exist; the driver reads via JWT and hands the DataFrame to `run_pipeline`.
- Authored `config/streamly.yaml` (none existed) mapping all 35 columns to the 7 canonical feature groups.
- Ran `run_pipeline(..., require_llm=True, provider="anthropic")` → **schema_version 1.1, k=7 GMM clusters, quad present on all 7**, LLM-named via Sonnet.
- Translated to the consumer `PersonaPack` and installed as `personas/v_2`, repointed `latest`.
- **Caveat:** the rebuild discovered **7** clusters, not the 6 hand-authored archetypes, and per-cluster Jaccard stability is mixed (P03 0.89 highly stable; P06 0.57; several "dissolved" < 0.4). The discovered identities (e.g. "Solo Binge-Laugher On-the-Go", "Family Movie Night Planners") do **not** preserve the PM's persona ids.

## STEP A2 — rendered treatment: AUTHORED

`smart_resume_proposed_figma.json` — a mock `ReverseFigma` for the Smart-Resume-hero home screen mirroring the existing `continue_watching/reverse-figma.json` schema: one large `home.smart_resume_hero` card + big `Resume` button + `home.smart_resume_more_options` expander revealing the legacy multi-tile row; the top-of-home Continue Watching rail removed; `home.editorial_hero` retained for cold-start; `home.my_stuff_tab` as the secondary path. Faithful to `h_001_smart_resume.md`. Wired as `proposed_figma` + `proposed_prd` in `streamly_plumbing_run_v11.py`.

## Verdict

Plumbing ✅ end-to-end on a freshly-rebuilt v1.1 customer pack. UNBLINDED degradation ✅ cleared by the rendered treatment. `identity_seed fallback` ❌ still open (a personas-pipeline gap, not a driver gap). The quantitative read is now a **separable negative** (lift −13.3, CI excludes 0) with an explicit metric-vs-sentiment divergence note — directionally informative, still NOT accuracy-validated (fictional data, no real outcome).
