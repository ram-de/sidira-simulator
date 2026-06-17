# Council Brief — Directionally-Correct Behavioral Simulation as a Precursor to Experimentation

## The question

How do you build a simulation of a product's userbase that is **directionally
correct** — reliable enough to use as a *precursor to* (not a replacement for)
live experimentation? "Directionally correct" means: when the simulation says a
proposed change will help / hurt / not move a target metric, it is right about
the **sign and the ranking** often enough to be decision-useful, even if it is
wrong about the magnitude.

Take a fresh, first-principles perspective. Do not anchor on any particular
vendor architecture or on what is currently fashionable in LLM-agent demos.
Assume nothing about prior art being correct.

## The setting (grounding, not constraint)

Sidira lets a PM submit a feature hypothesis (a PRD + design). The system
simulates how that product's real userbase would react — using personas
extracted from real user data plus a weekly snapshot of how the product works
today — and returns a confidence score plus diagnosed weaknesses. The PM then
interviews the individual simulated agents to understand *why*. The explicit
goal is **pre-experiment hypothesis validation**: deciding what is worth
A/B testing, and catching obviously-bad ideas before they consume an experiment
slot.

You are NOT being asked to design Sidira's UI. You are being asked the hard
methodological question underneath it.

## What a good answer must contain

1. **A precise definition** of "directionally correct" as a measurable target
   (the estimand, the loss function, the decision the PM actually makes).
2. **The method** — an architecture / methodology for producing simulations that
   are directionally correct, and an account of *why* it would be, grounded in
   statistics / ML / behavioral science rather than vibes.
3. **The failure modes** — where this class of method is known to break (e.g.
   stated vs. revealed preference, LLM sycophancy/mode-collapse, missing
   heterogeneity, interaction/network effects, distribution shift) and the
   specific mitigations.
4. **A validation protocol** — how you would *prove* a given simulator is
   directionally correct before trusting it: the metrics (e.g. sign-match rate,
   rank correlation, calibration, decision regret), the backtest design against
   historical experiments, the go/no-go thresholds, and what an honest
   confidence score should and should not claim.
5. **Concrete, runnable tests** — the evaluation harness you would build to
   gate the system. Specify inputs, outputs, and the exact statistics.

## Council composition (5 seats — both councils share these)

- **S1 — Causal inference & experimentation.** Estimands, sign-consistency,
  decision theory, the relationship between a simulated effect and an ATE.
- **S2 — LLM silicon-sampling / generative agents.** Whether and when LLMs can
  stand in for human respondents; documented biases and their corrections.
- **S3 — Computational social science / agent-based modeling.** Population
  heterogeneity, interaction and network effects, emergence, calibration of
  agent populations to real distributions.
- **S4 — Survey methodology, measurement & calibration.** Construct validity,
  response bias, stated vs. revealed preference, how to calibrate elicited
  intentions to real behavior.
- **S5 — ML evaluation & metrics.** How to *measure* directional correctness,
  backtesting, leakage, the statistics of small-sample experiment ground truth.

## Ground rules for the council

- Convene the five seats. Let them disagree. **Surface dissent explicitly** —
  do not paper over it with false consensus.
- Be concrete. Name metrics, thresholds, estimators, and tests.
- Distinguish what is **known** (cite the lineage of the idea), what is
  **defensible inference**, and what is **speculation**.
- The deliverable is a position paper, not a literature review.

## Required output structure (both councils, every round)

```
# Position Paper — <Council name>, Round <n>

## 1. Thesis (≤200 words)
## 2. Definition of directional correctness (the estimand + loss + decision)
## 3. The method
## 4. Failure modes & mitigations
## 5. Validation protocol (metrics, backtest, thresholds)
## 6. The test harness (concrete, runnable spec)
## 7. Dissents & open questions (named, per-seat where relevant)
## 8. Claims ledger — a numbered list of falsifiable claims this council commits to
```

Section 8 is mandatory and machine-comparable: each claim one line, numbered,
stated so the other council can mark AGREE / DISAGREE / REFINE against it.
