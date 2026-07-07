# M4 dry-run readout — Streamly, separate-table join + estimability (EPIC #572)

**Run:** 2026-07-07, against live prod (api.sidira.ai @ 17dbb49, flag default-ON).
**Prereg:** `M4_DRYRUN_PREREG.md` in this folder, sealed BEFORE the build
(sha256 `d1888451a48a47b83265650e231ae3e2b81ba64428ae49863d3e310c135a0b95`).
**Role discipline:** plumbing dry-run with designed ground truth. NOT accuracy
evidence; nothing here feeds the accuracy scorecard.

## Verdict

The white-glove chain works end-to-end on real prod infrastructure — separate
table → join view → build-time manifest → lever cards → promote → sim →
watchdog verdict sidecar — and every customer-facing verdict it produced was
**honest** (abstains, never a false CONFIRMS). Three prereg expectations held;
one deviated for a diagnosable product reason (a real bug the dry-run exists
to catch), and the run surfaced two more prerequisites the runbook was silent
about. Findings filed as #586, #587, #588; runbook updated in this PR.

## Prereg scorecard

| # | Expectation | Result |
|---|---|---|
| 1 | T1 (confounded, true effect 0) → guard **TRIPS**, no grounded CONFIRMS | ✅ **HELD** — NC residual **+225.03** > floor; lever card `guard_trips: true`; runtime watchdog `CANT_VALIDATE`; verdict "inconclusive — test it", no direction shown |
| 2 | T2 (randomized, true effect +60) → guard **PASSES**, direction UP, sim CONFIRMS | ❌ **DEVIATED** — guard trips on NC residual **−13.17**; runtime honest-abstains (`CANT_VALIDATE`) instead of CONFIRMS. Root cause below (#586) |
| 3 | Coverage present + `grounding_complete: true` on both levers | ✅ **HELD** — all 4 candidates `grounding_complete: true`, `grounding_gaps: []`, vouched NC bound with policy floor 0.05 / ratio 1.5 (after the outcome-keying fix, see deviation D1) |
| 4 | Lever cards + grounding sources render | ✅ **API level** — `GET /persona-packs/v_4/estimability` 200 with 4 cards (guard evidence carried, treatment magnitudes stripped per direction-only law); sim verdict sidecar carries `guardrails` + `unverified: true`. Founder eyeball of the frontend pages is the remaining M4 human step |

## Why Expectation 2 deviated (#586 — the run's most valuable finding)

The guard's `hidden` test compares the NC residual in **raw outcome units**
against `floor=0.05`. Our outcome is minutes (sd ≈ 240), so T2's chance
imbalance of −13.2 raw minutes (~0.055σ, ~1.4 se at n=2500) trips a floor that
was validated on ~unit-scale outcomes. The **ratio rule alone would have passed
T2** (main +59 > 1.5 × 13.2 = 19.8) — the trip is entirely the un-scaled floor.

Direction of failure is **safe** (over-abstain, never false trust), but until
the floor is scale-aware, no lever on a raw-count/minutes/revenue column can
ever earn a CONFIRMS. Interim mitigation is in the runbook: vouch NCs on
~unit-scale columns. Fix (standardize the residual, re-validated against the
campaign fixtures) is founder-gated in #586.

Per the prereg failure rule: reported as-is, DGP not regenerated, expectation
not re-authored.

## Runtime trace (verbatim, `decide()` on pack v_4)

- **Translator: perfect on both.** T1 → `offline_downloads_enabled`, T2 →
  `skip_intro_default_on`, both → `minutes_watched_next_30d`, from prose alone.
- **Grounded predictor:** `covered=True, supportable=True, direction=positive`
  on both (T2's designed sign recovered; T1's spurious positive present — which
  is exactly what the guard then refused to trust).
- **Watchdog:** `CANT_VALIDATE` via NC-guard trip on both (T1 correctly, T2 per
  #586).
- **Council:** degraded — `usable=1, dropped=2` every run (opus-4-7 rejects
  `temperature`; second drop unexplained) → consensus never certifiable →
  always the hard-caution abstain-siren path. Filed #588.

Sims (2 per lever across the run, `retention` OEC, 6 agents each) completed
with the sidecar verdict: `direction: null, caution: hard, label: "inconclusive
— test it", watchdog_verdict: CANT_VALIDATE, unverified: true`, plus translator
`guardrails` suggestions. `grounding_gap_reason: null` — correct, the levers
are grounding-complete; the abstain is the guard, not a data gap.

## Deviations & findings beyond the prereg

- **D1 (#587):** the prereg's build declaration keyed `neg_control_map` by
  treatment, copied from the runbook's example — the producer consumes it keyed
  by **outcome**. The v_3 build silently shipped every lever
  `no_vouched_negative_control`; rebuilt as v_4 with outcome keying. Runbook
  example fixed in this PR. (Declared-block deviation from the sealed prereg:
  the map's *keys* changed to what the producer actually reads; the vouched NC
  itself — `pre_minutes_30d` — is unchanged.)
- **D2:** the prod worker's vendored `sidira_personas` wheel predated the
  estimability producer entirely — no manifest could ever have been built.
  Wheel bumped to personas main 75b650e (PR #585, merged + deployed) before the
  build.
- **D3:** completed builds do **not** advance the `latest` pointer — sims kept
  resolving v_2 (`grounded_predictor.manifest_absent pack_version=v_2`) until
  `POST /persona-packs/v_4/promote`. Deliberate human gate, but the runbook
  never said so; documented now.
- **D4:** sim hypotheses require a **crawled capability** (`reverse-PRD`);
  warehouse rollouts have none, so both sims ran under the crawled `account`
  capability with the lever named in prose. Translator grounded correctly
  regardless. Documented in the runbook.
- **Cosmetic:** manifest `feature_store: "None.None.None"`, `built_at: null` on
  view-backed builds — producer doesn't stamp source metadata. Not filed as a
  ticket; worth folding into the next producer change.

## What remains for M4 proper (founder steps)

1. Eyeball the lever cards at `app.sidira.ai` (pack **v_4**, Streamly org) and
   record the vouch/reject on each lever (`POST .../lever-review` backs the UI;
   the pre-period-minutes NC argument is in the prereg).
2. Decide #586 (guard floor scaling) — it is the only thing between this chain
   and a legitimate grounded CONFIRMS on a clean lever.
3. #588 (council panel) — restores the moderate-caution unverified path.

## Artifacts

- Pack `v_4` (promoted `latest`) + `estimability_manifest.json`, Streamly org.
- Sims on v_4: `0c0531b8` (T1), `f26a55e4` (T2); earlier v_2-resolved pair
  `81feeb8c`/`913cb9db` (the D3 witnesses).
- Substrate: `STREAMLY.SYNTHETIC.FEATURE_ROLLOUTS` + `PERSONA_SOURCE_V1` view.
- Tickets: #586 (guard floor), #587 (runbook keying), #588 (council).
