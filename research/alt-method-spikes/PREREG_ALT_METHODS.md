# PREREG — alt-method battery (think-differently loop, iteration 1)

Sealed BEFORE any run. sha256 of this file is recorded in the runstore to prove the
predictions + method specs were committed before results existed. The case `real_winner`
fields are PUBLIC (published narratives), so the integrity guard here is: **the methods and
the leaned hypothesis below are frozen now and will NOT be tuned against the scores.** One
run, score once, report whatever it gives — including NULL.

Date: 2026-06-28. Model: Groq `llama-3.3-70b-versatile`, temp 0.0 (+ k samples at temp 0.4
for the agreement signal), fixed seeds. Cases: `sessions/agent-behavior-spec/portfolio-benchmark/
PORTFOLIO_CASES.json` (14, mixed winners) — the same set the council/comparative scored ~0.50 on.
Blinded stimulus = domain + control + treatment + metric ONLY (never `real_winner`/`effect`/
`source`/`counter_intuitive`). Scoring = directional accuracy (predicted winner == real_winner).

## Why this exists
Every LLM-narrative method tried (per-arm roleplay 0.286, comparative 0.50, council worse, naive
retracted) lands at/below chance on this set. This battery asks whether a STRUCTURALLY different
use of the LLM moves it — and registers the genuine bet that it does NOT at the object level, but
that a META-level reliability signal does.

## Methods (frozen)

**M0 — holistic baseline (anchor).** Replicate the comparative forecaster: ask "which version wins
on the metric?", k=5 votes (seeds 6000..6004), majority. Expected ≈ chance; this is the anchor the
others are judged against, not a bet.

**M1 — hypothesis decomposition (LLM as feature-extractor).** The LLM never predicts the winner.
For the TREATMENT (vs control), on the stated metric, it rates each mechanism in [0,1] (blinded,
temp 0.0):
  - `relevance_gain` — treatment better matches the user's actual need/intent
  - `salience_gain` — treatment makes the value/CTA more prominent
  - `friction_add` — treatment adds steps/effort/cost/latency
  - `reactance_add` — treatment feels pushy/intrusive/controlling/surveilling
  - `overload_add` — treatment adds options/decisions/cognitive load
  - `loss_salience_add` — treatment surfaces a price/loss/risk the user would rather not face
A FROZEN rule maps ratings → a treatment-favorability score:
  `s = relevance_gain + salience_gain − friction_add − reactance_add − overload_add − loss_salience_add`
The LLM also returns `metric_polarity` ∈ {higher_better, lower_better} for the metric (a factual
classification, not a prediction). Predict: if `higher_better` → treatment wins iff `s > 0`; if
`lower_better` → treatment wins iff `s < 0` (a treatment that adds friction/reactance REDUCES a
lower-is-better metric like churn, so it "wins"). Ties (`s == 0`) → predict control (status-quo).

**M2 — leave-one-out few-shot analogy (reference-class, degenerate corpus).** For each held-out
case, put the OTHER 13 cases (control/treatment/metric/real_winner) in-context as labeled examples,
then ask the model to predict the held-out winner "by analogy to the examples." k=1, temp 0.0.
(There is no external A/B corpus; the 14 cases are the only reference class — this is acknowledged
as weak.)

**M3 — selective prediction (meta-reliability).** Reuse M0's k=5 votes. Define `agreement` =
(max vote share) ∈ {3/5, 4/5, 5/5}. Rank cases by agreement; measure accuracy on the high-agreement
subset (agreement ≥ 4/5) vs the full set. Also report the accuracy-coverage curve (accuracy among
the top-X% most-agreed cases). NO new LLM calls beyond M0.

## Pre-registered hypotheses (genuine, leaned — sealed)

- **H1 (decomposition):** does NOT beat M0. Predicted M1 accuracy ≤ M0 + 1 case (≤ ~1/14 over
  baseline). Rationale: the mechanism ratings are themselves narrative-derived and inherit the
  same bias the holistic call has. **Expected verdict: NULL.**
- **H2 (analogy):** does NOT beat M0. Predicted M2 ≈ chance (5–8 / 14). Rationale: 13 dissimilar
  cases are not a real reference class; analogy has nothing to grip. **Expected verdict: NULL.**
- **H3 (selective — THE BET):** the meta signal SEPARATES right from wrong. Predicted: accuracy on
  the agreement ≥ 4/5 subset is **strictly higher** than accuracy on the full set, AND the
  accuracy-coverage curve is downward-sloping (more selective → more accurate). If the high-agreement
  subset has ≥ 3 cases and its accuracy ≥ full-set accuracy + 0.15, that's a **LEAD**. Rationale:
  abstention/confidence is the only mechanism that has worked (negative-control guard); the value is
  knowing WHEN you're right, not being right more often.
- **Meta-claim:** if H1+H2 NULL and H3 holds → the registered conclusion is "the path is selective
  prediction (abstain when unsure), not better object-level prediction." If H3 ALSO fails (no
  agreement→accuracy link), the registered conclusion is "even the meta signal fails at n=14 → the
  binding constraint is validation DATA, not method," which redirects the loop to the data wall.

## Honesty rails
- n=14 is underpowered: a 1–2 case swing is noise. No verdict stronger than LEAD/NULL is claimable.
- The frozen M1 rule will NOT be edited after seeing scores. If it scores poorly, that's the result.
- All methods score on the SAME 14 cases; report per-case predictions so the cofounder can audit.
