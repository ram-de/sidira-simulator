# PoC runbook — turnkey self-run A/B (survey + task designs + sealed win-rule)

Hand this to whoever runs the PoC. Builds on POC_SELF_RUN_AB_SPEC.md + POC_VENDOR_SHORTLIST.md.
Goal: cheap GO/NO-GO on "given a pack built from a panel, can the engine predict that panel's
behavior on NON-OBVIOUS changes." ~$2–3k, ~750 participants, between-subjects.

## 1. Profiling micro-survey (asked of every participant; → persona-pack features)
Keep ~8 items, all multiple-choice/Likert so they map cleanly to features. Key on participant ID.
1. Age band (18–24 / 25–34 / 35–44 / 45–54 / 55+).
2. Country / locale.
3. Device right now (phone / tablet / desktop).
4. **Decision style:** "When buying online I usually…" (decide fast on gut ↔ research thoroughly first) — 5-pt.
5. **Deal/price sensitivity:** "A visible discount makes me…" (much more likely to buy ↔ suspicious of quality) — 5-pt.
6. **Patience / present-bias:** "If something can be done later, I…" (do it now ↔ put it off, often forget) — 5-pt.
7. **Attention/effort tolerance:** "If a page feels cluttered or slow I…" (push through ↔ give up quickly) — 5-pt.
8. **Skepticism / reactance:** "Countdown timers and 'only X left' make me…" (act faster ↔ distrust and slow down) — 5-pt.
(Map: 4–8 become per-persona behavioral features; 1–3 demographics. These feed the pack build.)

## 2. The three A/B tasks (NON-OBVIOUS by design — between-subjects, one arm each)
Each is a short self-contained task with ONE binary behavioral outcome. Neutral wording, no leak.

**T1 — deadline/scarcity backfire.** Offer a free reward (e.g. a $5 voucher) redeemable by clicking "Claim".
- Control: "expires in 3 weeks."  Treatment: "expires in 3 days."
- Outcome: did they click Claim *now*? (binary)
- Non-obvious truth: the SHORTER deadline usually wins (long deadline → procrastinate → never act). Naive prior says "more time = more redemptions" → wrong.

**T2 — choice overload.** "Pick a title to watch tonight."
- Control: 24 options.  Treatment: 6 options.
- Outcome: did they make a choice (vs "skip / can't decide")? (binary)
- Non-obvious truth: FEWER options usually wins (overload → deferral). Naive prior says "more choice is better" → wrong.

**T3 — urgency/countdown reactance.** Identical limited offer.
- Control: with a live countdown timer + "Only 3 left!".  Treatment: no timer, no scarcity text.
- Outcome: did they accept the offer? (binary)
- Non-obvious truth: NO-urgency can win for skeptical/autonomy-valuing users (reactance/distrust). Naive prior says "urgency lifts conversion" → wrong.

Per arm ~125–150 (target a ≥15pp effect at 80% power). ~300/test × 3 ≈ 900 (or run 2 of 3 for ~600 to hit ~$2k).

## 3. Run order
1. Build the 3 tasks (Gorilla / jsPsych / Testable) with the profiling survey FIRST, keyed on participant ID.
2. **SEAL the win-rule** (below) — commit it before fielding.
3. Field on Prolific (cross-check one test on CloudResearch). Hard attention checks; drop failers, re-recruit.
4. Compute each task's real winner (two-proportion test + 95% CI per arm).
5. Build the persona pack from the profiling data; run the engine BLINDED (winner stripped) on each task → predicted direction.
6. Score against the sealed rule.

## 4. Sealed win-rule (commit BEFORE any result)
- **Primary:** direction accuracy across the 3 tasks vs the naive "obvious wins" prior (which is WRONG on all 3 by construction).
- **GO** (→ scale to the $12–18k powered benchmark): engine predicts the real winner on **≥2 of 3** AND each task produced a clean per-arm winner (CI excludes zero) AND the engine beats a **placebo "always-pick-simpler" control** (it must be right for persona-grounded reasons, not a blanket simpler-bias).
- **NO-GO:** ≤1 of 3 → cheap early confirmation the capability isn't there; do not spend the benchmark budget.
- Record: chance ≈ 1.5/3; 3/3 ≈ p=0.125 (suggestive at this n); the PoC GATES the powered test, it doesn't confirm.
- Register the per-task predicted direction + confidence BEFORE seeing outcomes (a wrong-but-confident call in the un-flattering direction is the credible kind).

## 5. Honest limits (carry into the writeup)
Panel-task behavior ≠ real-stakes behavior; n=3 tasks is proof-of-life not confirmation; validates the
capability on a consistent population, not deployment to a specific customer's audience. See
[[directional-sim-campaign-standing]].
