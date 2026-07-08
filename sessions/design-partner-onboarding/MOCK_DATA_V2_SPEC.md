# Streamly mock warehouse v2 — designed ground truth (seeded 2026-07-08)

All deterministic (hash-seeded, no RNG state), 2,500 users keyed to
`USERS_FEATURE_STORE."user_id"`. Latent taste `u = 0.6·z(weekly_viewing_hours)
+ 0.8·hash-noise` drives every engagement outcome, the pre-period metrics, and
the two confounded assignments. Seeder: `seed_mock_v2.py` (same directory;
rerunnable CREATE OR REPLACE — run in-container via `docker exec sidira-api
python`, it decrypts the saved feature-store connection at runtime).

## Tables

| table | contents |
|---|---|
| `FEATURE_ROLLOUTS` (v1, existing) | `offline_downloads_enabled` (confounded, true 0), `skip_intro_default_on` (randomized, +60 min), `pre_minutes_30d`, `minutes_watched_next_30d` |
| `FEATURE_ROLLOUTS_V2` | 8 new lever flags (below) |
| `ENGAGEMENT_OUTCOMES` | `pre_sessions_30d`, `pre_completion_rate_30d` (NCs) + `watch_minutes_next_30d`, `sessions_next_30d`, `completion_rate_next_30d`, `kids_hours_next_30d` |
| `SUBSCRIPTION_SNAPSHOT` | `plan_tier`, `monthly_price`, `payment_failures_90d`, `churned_90d`, `upgraded_plan_90d` |
| `EXPERIMENT_HISTORY` | 12 past A/B tests (metadata + results consistent with the designed effects; feeds a future #525 ingest) |
| `CONTENT_CATALOG` | 15 titles (realism garnish; not consumed by the build) |
| `PERSONA_SOURCE_V2` (view) | feature store ⨝ rollouts v1 ⨝ rollouts v2 ⨝ engagement ⨝ subscription — the build's `source_query` |

## True-effect registry (the answer key — NOT visible to the product)

| lever | assignment | true effects |
|---|---|---|
| `new_recs_algorithm` | randomized 50% | watch_minutes **+45**, completion **+0.05** |
| `mobile_preview_clips` | randomized 50% | watch_minutes **+40**, sessions **+1.2** |
| `profile_onboarding_quiz` | randomized 30% | sessions **+1.5** |
| `password_sharing_crackdown` | randomized 40% | watch_minutes **−50**, churned_90d **≈ +9pp** |
| `kids_profile_nudge` | randomized 25% | kids_hours **+1.5** |
| `ui_dark_mode_default` | randomized 50% | **ZERO everywhere** (true null → ratio-rule abstain expected) |
| `premium_upsell_banner` | **confounded** (high-u) | **ZERO** (pure selection; naive read +444 min) |
| `dormant_winback_email` | **confounded** (low-u) | sessions **+1.0** real, naive read **−8.1** (sign-masked) |

`EXPERIMENT_HISTORY` mirrors these: the winback RCT shows the true +0.9; the
upsell banner's RCT was flat and its targeted re-launch was never re-tested —
exactly why the observational read is spurious.

## Seeding-time verification (naive diffs, in-container 2026-07-08)

new_recs → minutes **+40.6** (design +45) · preview_clips → sessions **+1.54**
(+1.2) · crackdown → minutes **−39.8** (−50) · dark_mode → minutes **+5.98**
(0, chance) · upsell → minutes **+444.3** (spurious, true 0) · winback →
sessions **−8.05** (true +1.0). Adoption rates 23.6%–50.3%; churn 15.1%;
upgrades 7.7%. View: 2500 rows / 2500 distinct users.

## v_5 build declaration (outcome-keyed NC map)

Treatments: all 10 levers. Outcomes: both minutes columns, sessions,
completion, kids_hours, churned_90d. NCs: `pre_minutes_30d` (raw scale — the
#586 fix's proving ground), `pre_sessions_30d`, `pre_completion_rate_30d`
(unit scale). `nc_diagnostics: true`, `max_treatments: 12`, `max_outcomes: 8`.

## Expected lever-card outcomes (with the #586 standardized guard)

- 5 randomized levers with real effects → guard PASS on their designed
  (treatment, outcome) pairs → CONFIRMS-eligible.
- `ui_dark_mode_default` → true null → `indistinct` (ratio rule) abstain.
- `premium_upsell_banner`, `dormant_winback_email`, `offline_downloads_enabled`
  → guard TRIP via NC residual (selection on u shows up on the pre-period NCs).
- `skip_intro_default_on` → the M4 T2 lever: chance NC imbalance 0.055σ now
  passes (effective floor 0.08σ at n=2500) → CONFIRMS-eligible at last.
