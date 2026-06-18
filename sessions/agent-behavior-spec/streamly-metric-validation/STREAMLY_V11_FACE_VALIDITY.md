# Streamly H-001 — per-persona FACE-VALIDITY vs PM's authored expectations

> **Face-validity only.** Matching the PM means the simulator shares a human's
> *prior* about who reacts how — it is NOT evidence the simulator is correct.
> Streamly is fictional; there is no real A/B outcome to validate against.

Method: join `per_agent_analyses` (agent_id → sentiment) to the agent records
(agent_id → persona_name + arm), aggregate the **treatment-arm** per-persona
sentiment direction, and compare to the PM's authored predicted-reaction table in
`h_001_smart_resume.md`. PM's 4 labels are collapsed to 3 bands for direction
matching (STRONG POSITIVE/POSITIVE → positive; NEGATIVE/SLIGHTLY NEGATIVE →
negative; NEUTRAL → neutral).

## PM's authored table (the prior under test)

| Persona | PM prediction |
|---|---|
| `alex_binge_marathoner` | STRONG POSITIVE |
| `marco_background_player` | POSITIVE |
| `tess_new_trialer` | SLIGHTLY NEGATIVE |
| `rivka_weekend_movie_night` | NEGATIVE |
| `noor_niche_genre_loyalist` | NEUTRAL |
| `ken_price_sensitive_lapser` | NEUTRAL |

## Result A — clean comparison on the `v_1` pack (PM persona identities preserved)

The rebuilt `v_2` pack replaces the PM's named personas with GMM-discovered
clusters, so the **cleanest** 6-way comparison is on the `v_1` hand-authored pack
(same blinded rendered treatment, population 24, seed 42). This run had better
per-persona n and a direct id match.

| Persona | PM | sim direction (treatment arm, n) | match |
|---|---|---|---|
| `alex_binge_marathoner` | positive | **positive** (+4 ~1 −0, n=5) | AGREE |
| `marco_background_player` | positive | **positive** (+4 ~1 −0, n=5) | AGREE |
| `tess_new_trialer` | negative | **negative** (+0 ~1 −1, n=2) | AGREE |
| `rivka_weekend_movie_night` | negative | **negative** (+0 ~0 −5, n=5) | AGREE |
| `noor_niche_genre_loyalist` | neutral | negative (+0 ~0 −3, n=3) | DISAGREE |
| `ken_price_sensitive_lapser` | neutral | negative (+0 ~0 −4, n=4) | DISAGREE |

**Tally: 4 / 6 match.** lift +1.7, CI [−7.1, +10.7], confidence 22.3.

## Result B — rebuilt `v_2` pack (7 clusters → best-effort archetype mapping)

The headline v1.1 run uses the rebuilt `v_2` pack. Its 7 clusters were mapped to
the PM's 6 archetypes by a **documented best-effort** mapping (grounded in cluster
descriptions + the `gen_streamly_feature_store.py` segment design). Per-cluster n
is thin and uneven (GMM cluster sizes vary), so this is the weaker comparison.

| PM archetype | PM | mapped cluster | sim direction (n) | match |
|---|---|---|---|---|
| `alex_binge_marathoner` | positive | Solo Binge-Laugher On-the-Go | **positive** (n=3) | AGREE |
| `marco_background_player` | positive | Binge-Focused Serial Devotees | negative (n=8) | DISAGREE |
| `tess_new_trialer` | negative | Mobile Casual Reality Browsers | **negative** (n=1) | AGREE |
| `rivka_weekend_movie_night` | negative | Family Movie Night Planners | **negative** (n=3) | AGREE |
| `noor_niche_genre_loyalist` | neutral | Family Couch Comedy Night | **neutral** (n=1) | AGREE |
| `ken_price_sensitive_lapser` | neutral | Lapsed Casual News Grazers | negative (n=3) | DISAGREE |

Unmapped extra cluster: "Binge-Hooked Solo Streamer" (no clean PM counterpart) — negative (n=1).

**Tally: 4 / 6 match.** (Different 4, owing to the lossy cluster mapping + thin n.)

## Overall face-validity read

- **Both runs independently land 4 / 6.**
- The **four directional personas the PM cared most about** — the binge-lovers
  (alex, marco) positive and the browse/movie-night ritualists (tess, rivka)
  negative — **match on the clean `v_1` comparison**. The PM explicitly wanted the
  sim to surface the alex-vs-rivka conflict; it does.
- The two **disagreements on `v_1` are the two NEUTRAL personas** (noor, ken): the
  sim reads them as **negative** where the PM expected neutral. This is consistent
  with the run's overall negative-sentiment finding — removing the visible rail
  reads as a *loss* even to low-engagement / niche cohorts, rather than a non-event.
  Defensible as a genuine simulator disagreement, not an obvious error.
- **Caveats (do not over-read):** per-persona n is small (1–5 in the treatment
  arm); the `v_2` cluster→archetype mapping is lossy (7 discovered clusters ≠ 6
  authored archetypes, and noor/marco mappings are weak); and the whole exercise
  is on FICTIONAL data. Agreement with the PM = shared human prior (face-validity),
  **NOT** evidence of correctness. Real calibration needs a real A/B outcome.

Artifacts: `streamly_v11_face_validity_v1pack.json` (Result A),
`streamly_v11_face_validity.json` (Result B).
