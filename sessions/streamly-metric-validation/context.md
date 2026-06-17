---
type: session
domain: streamly-metric-validation
status: complete
started: 2026-06-16
owner: ram-de
---

# Streamly metric-validation — first live exercise of per-metric outcome elicitation

## Goal

First end-to-end exercise of the per-metric outcome-elicitation feature
(registry + retention/CTR, shipped 2026-06-16 via #275/#276/#279/#280) against a
REAL org's live packs — not a unit test. Run a deliberately-positive and a
deliberately-negative hypothesis through the `retention` metric and read whether
the simulator ranks them correctly, and how blinding (§3b) changes the estimate.

- **Org:** `org_3F9pXzqFStz5NyPkazXW1o47NzE` (Streamly).
- **Packs:** persona pack `v_2` (8 personas: Engaged Viewer, Family Co-Viewer,
  Frequent Rewatcher, Trial Enthusiast, High Risk Trial Users, Inactive High
  Churn, …), feature pack `2026-W25`. Capabilities: browse, search, my_list,
  kids, account, profiles. Ran against **browse** (the home/landing screen;
  has a reverse_figma → grounds well).
- **Model:** Groq `llama-3.3-70b-versatile` (the prod default). Cost: a few
  cents total across 5 runs.
- **Repos:** in-memory (NOT persisted to the org's prod Postgres / sim history).
  Real pipeline, real packs, throwaway result rows.

## Hypotheses (both `metric_name=retention`, capability=browse, same `decision_point`)

`decision_point` = "you've just finished tonight's session on Streamly and
you're deciding whether you'll open it again next week".

- **Positive:** lead the returning-user home with a "Continue Watching" row
  (one-tap resume) + a personalized "Top Picks for You" rail, replacing the
  generic "Trending Now" grid.
- **Negative:** mandatory unskippable 30-second ad before every title (incl.
  resumes), no paid ad-free option.

Blinded runs attach a `proposed_figma` (a faithful standalone view of the
treatment) so the metric pass runs BLINDED instead of the unblinded fallback.
The positive figma = clone browse figma + insert the two rails. The negative
figma = clone + add a pre-playback "Advertisement" screen (skip disabled) + a
home-screen ad-policy notice + a play→ad transition, all phrased as steady-state
product FACT (no "we added"/"now" change-framing, to keep it blinded).

## Results — 5 runs (paired bootstrap, run_seed=42)

| run | design | n | sentiment | retention lift | 90% CI (pp) | separable | blinded |
|-----|--------|---|----------:|---------------:|-------------|-----------|---------|
| 1 | Positive | 16 | 83.0 | +5.0 pp | [−1.2, 10.0] | no | fallback (unblinded) |
| 2 | **Positive** | 50 | 79.4 | **+3.6 pp** | **[1.6, 5.6]** | **yes** | **blinded** |
| 3 | Negative | 16 | 2.0 | −3.1 pp | [−8.8, 1.2] | no | fallback (unblinded) |
| 4 | Negative | 50 | 0.7 | +1.0 pp | [0.0, 2.2] | no | blinded |
| 5 | **Negative (salient ad-gate)** | 50 | 0.7 | **+2.0 pp** | **[0.4, 4.0]** | **yes (WRONG sign)** | **blinded** |

All metrics `weak_behavioral`, `metric_lift_calibrated=false` (uncalibrated —
pre-#222). Blinded runs confirmed `has_standalone_view=true` (2–3 changes
detected); unblinded_fallback=false.

## Findings

1. **Sentiment is the robust, correctly-signed signal in every design** —
   ~80 for the good change, ~1 for the ad change. Unambiguous and intuition-
   matching across all 5 runs. (Sentiment is unblinded in both arms by design;
   only the metric pass is blinded.)

2. **Blinding de-biases the POSITIVE change and confirms it.** Unblinded +5.0
   (not separable) → blinded +3.6, **CI [1.6, 5.6] excludes zero** at n=50. The
   ~1.4 pp drop is exactly the §3b prediction: the unblinded arm let agents
   "smell the improvement" and inflated treatment; blinding removed the demand
   characteristic. The personalization win is a REAL steady-state behavioral
   retention lever.

3. **Blinded retention FAILS on the NEGATIVE change — and this is the headline
   caution.** Unblinded it read −3.1 pp (right direction, not separable, but
   that was largely loss-aversion to "taking ad-free away"). Blinded, the
   steady-state retention signal is +1.0 (not separable); made the ad-gate MORE
   salient and it became **+2.0 pp, separable POSITIVE — the WRONG sign**.
   Meanwhile sentiment stayed 0.7. So the uncalibrated synthetic-retention
   metric, on this model/pack, **cannot be trusted to detect harm on its own**:
   without the change framing the model treats "30s pre-roll" as an ordinary
   streaming feature (every real service has ads) and, with a longer/more-
   detailed standalone view, even nudges return-intent UP. More salience made it
   MORE confidently wrong, not less.

## Takeaways for the product / roadmap

- **Read the metric ALONGSIDE sentiment, never alone** — exactly the spec's
  design (metric never replaces `confidence_score`). When they DISAGREE (run 4/5:
  brutal sentiment, flat/positive blinded retention), trust sentiment for harm
  detection until the metric is calibrated.
- **This is the strongest possible argument for #222 calibration.** A fitted
  calibrator (Upworthy CTR first; retention later) is what would correct the
  wrong-signed blinded retention on harms. Until `metric_lift_calibrated=true`,
  the "read as rank/direction, not magnitude" caveat is generous — for HARMS the
  direction itself is unreliable here.
- **Blinding salience is a knob with teeth.** How forcefully the treatment is
  rendered in the standalone figma materially moves the blinded metric (run 4 vs
  5: +1.0→+2.0, non-sep→sep). Treatment-rendering fidelity (#225) is load-bearing
  for metric trustworthiness, not just cosmetics.

## Caveats

- Construction: the ad-gate is a SYNTHETIC figma I hand-built on `browse`; a real
  pre-roll lives on the playback path and a production crawl might render it
  differently. The positive run had no such issue (home-screen rail renders
  natively).
- Small panel (8 personas, n≤50 paired), Groq synthetic agents, single seed.
  Directional evidence, not production-grade.

## How these were run (server-side recipe)

See memory [[reference-run-sim-on-ec2-box]]. In-process on the prod box via
`SimulationOrchestrator.prepare()` → `await run()` → `orchestrator.get()` with
in-memory repos + the real `PersonaPackLoader`/`FeaturePackLoader` (which resolve
the org's live pack from R2/bind-mount). Default Groq model. Findings distilled
to [[project-metric-blinded-retention-unreliable-for-harm]].

## Status

COMPLETE — 5 runs done, feature validated end-to-end on a real org. The pipeline
ranks the good change correctly on both sentiment and (blinded) retention; the
negative case surfaced the uncalibrated-metric harm-detection failure that #222
is meant to fix. No prod DB writes. Follow-on lives in #222 (calibration).
