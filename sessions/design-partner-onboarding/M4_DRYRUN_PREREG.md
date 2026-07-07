# M4 dry-run prereg — Streamly, separate-table join + estimability (EPIC #572)

**Sealed:** 2026-07-07, BEFORE the pack build and before any verdict is produced.
**Role discipline:** this is a **plumbing dry-run with designed ground truth** — it vets the
end-to-end chain (view join → build-time manifest → lever card → vouch → runtime watchdog →
grounding UI). It is **NOT accuracy evidence**: the data is synthetic and the author knows the
DGP. Nothing here feeds the accuracy scorecard.

## Substrate (created 2026-07-07, deterministic hash-seeded — no RNG state)

`STREAMLY.SYNTHETIC.FEATURE_ROLLOUTS` (2,500 rows, keyed to `USERS_FEATURE_STORE.user_id`),
joined one-row-per-user by `STREAMLY.SYNTHETIC.PERSONA_SOURCE_V1` (#568 separate-table pattern).

Latent taste `u = 0.6·z(weekly_viewing_hours) + 0.8·n_lat`, where `n_lat` is hash-noise
**unobserved by any feature column** → covariate adjustment cannot fully remove it.

| column | construction | role |
|---|---|---|
| `offline_downloads_enabled` (T1) | `1[u + 0.3·n_adopt > 0.15]` → 41.4% adoption | **confounded lever, TRUE EFFECT = 0** |
| `skip_intro_default_on` (T2) | `hash(user_id) % 2` → 50.6% | **randomized lever, TRUE EFFECT = +60** on outcome |
| `pre_minutes_30d` | `600 + 300·u + 80·n_pre` | **pre-treatment NC** (rollout cannot cause the past; shares `u`) |
| `minutes_watched_next_30d` | `610 + 300·u + 60·T2 + 0·T1 + 80·n_post` | outcome |

**Pre-build sanity (measured in SQL before sealing):** T2 naive effect on outcome **+59.2**
(true +60), T2 effect on pre-period **−8.0** (≈0, balanced); T1 spurious outcome effect
**+364.7**, T1 "effect" on the NC **+365.9** (the confounding signature).

## Build declaration (to be passed verbatim on the build request)

```json
"estimability": {
  "enabled": true,
  "treatments": ["offline_downloads_enabled", "skip_intro_default_on"],
  "outcomes": ["minutes_watched_next_30d"],
  "neg_control_map": {
    "offline_downloads_enabled": ["pre_minutes_30d"],
    "skip_intro_default_on": ["pre_minutes_30d"]
  },
  "nc_diagnostics": true
}
```

The vouch to be made on the lever cards (founder judgment, the M3/M4 human step): the
pre-period minutes NC is valid because **a rollout cannot change what a user watched before it
existed**, while pre-period minutes share the engagement confounder.

## Preregistered expectations

1. **T1 `offline_downloads_enabled` → `minutes_watched_next_30d`:** the NC guard **TRIPS**
   (|NC residual| ≫ 0.05 floor) → `CANT_VALIDATE` / untrustworthy on the lever card; at sim
   time the watchdog must NOT return a grounded CONFIRMS. The naive/adjusted estimate will be
   large and positive — the whole point is that the instrument refuses to trust it.
2. **T2 `skip_intro_default_on` → `minutes_watched_next_30d`:** guard **PASSES** (NC residual
   ≈ 0, ratio rule satisfied) → trustworthy, direction **UP**; a sim hypothesizing the lever
   increases watch time gets **CONFIRMS**; a sim hypothesizing it decreases watch time gets
   **CONTRADICTS**.
3. **Coverage/#564:** both declared treatments + outcome resolve as `present`; the levers carry
   `grounding_complete: true` (they have treatment, outcome, covariates, and a vouched NC).
4. **UI (#566/#565):** both levers render on the pack lever card with NC diagnostics; the sim
   grounding-sources panel shows T1's abstain with its reason and T2's grounded route.

**Failure readout rule:** any deviation from 1–4 is reported as-is in the readout (no
post-hoc redesign of the DGP or the NC map to make the expectation land; if the DGP itself is
found buggy, that is stated and the whole run relabeled, not silently regenerated).

**Deliberate exclusion:** no per-lever magnitude claims anywhere (direction-only law), and no
claim that T2's CONFIRMS validates engine accuracy — a designed effect being recovered is a
plumbing check.
