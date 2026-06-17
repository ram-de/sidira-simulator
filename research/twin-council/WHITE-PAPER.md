# Directionally-Correct Behavioral Simulation as a Precursor to Experimentation

**A joint white paper of the Claude Council and the Codex Council.**
Ratified unanimously, both councils, no objections. Working repo:
`research/twin-council/` (BRIEF, per-round papers, arbitration, merged ledger,
ratifications, and the evaluation harness).

---

## 0. How this document was produced

Two independent expert councils — one instantiated on Claude, one on Codex — were
each convened as the same five seats: causal inference & experimentation (S1),
LLM silicon-sampling / generative agents (S2), computational social science /
agent-based modeling (S3), survey methodology & measurement (S4), and ML
evaluation & metrics (S5). They wrote independent position papers (Round 1),
cross-critiqued and resolved five open items (Round 2), and then ratified a
single arbiter-merged ledger (Round 3). Both councils signed the identical
claims ledger and certification gate with zero remaining objections. The
agreement is therefore not a single model talking to itself; it is two different
model families, reasoning separately, converging on the same methodology.

The convergence itself is the headline finding: with no prompting toward a
conclusion, both councils independently rejected the framing the product name
invites.

---

## 1. Thesis

**Stop calling it a digital twin.** A "twin" implies a faithful clone of a person
whose behavior you read off directly. That goal is neither achievable nor
necessary, and chasing it is the main way these systems fail. The defensible
object is a **calibrated causal prior over a backlog of product changes**: a
machine whose job is to *rank* candidate experiments and estimate the
*probability that each is positive, flat, or harmful* on a named business metric.
The live randomized experiment stays the ground truth. The simulator's only
legitimate claim is to be **measured-to-be directionally correct on a held-out
backtest of the product's own historical experiments** — and to say
"uncalibrated" and claim nothing quantitative when that backtest does not exist
or does not cover the change in front of it.

"Directionally correct" is not a property of how realistic the personas sound. It
is a property of the calibration set. A simulator earns the word only by passing
a gate (§7); until then it is an interview prop, not evidence.

---

## 2. What "directionally correct" means, precisely

### 2.1 The estimand
For a product change *j*, define a treatment *T_j* and control *C_j* (usually the
current product). For user *i*, let *Y_i(t, h, m)* be the outcome on target metric
*m* over horizon *h* under product state *t*. The causal estimand is the
population ATE/ITT:

> τ_j = E_{i∼P}[ Y_i(T_j, h, m) − Y_i(C_j, h, m) ]

This is the Neyman–Rubin potential-outcomes contrast, not a free-floating
opinion. The simulator cannot observe the counterfactual; it predicts a
*distribution* over τ_j. A change with no specified metric, population,
treatment, control, horizon, randomization unit, and **practical-null band δ** has
no estimand and cannot be "directionally correct" in any testable sense (M1).

### 2.2 The target and why magnitude is a non-goal
The product claim is the **sign and rank** of τ_j against a pre-registered primary
metric, with effects inside ±δ classed as *flat* (M2). Magnitude is explicitly
out of scope: raw LLM-elicited effect sizes are inflated and unstable, and the
decision the PM makes — *which of these N ideas deserve a scarce experiment
slot* — needs ordering, not unbiased lift.

The key statistical permission: **sign and rank survive badly biased magnitude.**
If the raw simulator signal *g* is related to the true effect by any monotone
(even wildly nonlinear) transform plus mean-zero-ish noise, then sign and rank
are recoverable through a fitted monotone calibration even though the magnitude
is hopeless (M4). This is what makes the whole enterprise tractable. It is also
why the calibration layer, not the LLM, is the scientific instrument.

### 2.3 The decision and its loss
The PM runs a triage policy: park, redesign, or experiment. The loss is
**asymmetric** — a *false red* (the simulator parks a real winner) is the most
dangerous error precisely because it is **unobservable**: you never run the
experiment, so you never learn you were wrong (M16). Therefore the system must be
permitted to **abstain**, must **re-rank/redesign rather than auto-kill**, and is
gated on tail-winner recall (§7, G9).

---

## 3. The method

A five-stage pipeline. The LLM is one stage, deliberately boxed.

1. **Estimand binding.** Every simulation is tied to a concrete future
   experiment's estimand (metric, population, T/C, horizon, unit, δ). No estimand,
   no run.

2. **Population construction (M8–M9).** Start from *real* pre-treatment user rows
   (tenure, plan, device, geography, usage intensity, adoption, recency/frequency,
   lifecycle, prior pain points, metric-relevant history). Assign **soft** segment
   membership per row — `z_i = [p(persona_1),…,p(persona_K)]`, hard assignment
   banned. Condition each agent on *both* its row-level facts and its full soft
   membership vector (including its entropy). Then **rake / post-stratify** the
   weighted agent panel to the *real joint covariate distribution*. Accept the
   panel only if `|SMD| ≤ 0.10` on primary covariates, `≤ 0.15` on key
   interactions, joint PSI ≤ 0.10, no weight > 5× median, and **between-agent
   response variance ≥ 0.5× target heterogeneity** (this last check rejects
   mode-collapsed runs where every agent says the same thing).

3. **Elicitation (M6–M7).** Show each agent a *paired* control-vs-treatment delta,
   **blinded** to which is the proposed change, **order-randomized**, and ask for
   a **behavioral choice/action** keyed to the metric — not a Likert liking score.
   Elicit a distribution, not a point. Sycophancy, prompt-format sensitivity, and
   mode collapse are treated as measured nuisances, not assumed away.

4. **Calibration & shrinkage (M5).** The raw signal *g* (an aggregate of the
   agent distribution) is **never shown to the user**. A fitted calibration layer
   — isotonic/Platt for the sign probability, plus aggressive shrinkage of any
   magnitude — is trained on the product's real past experiments and maps *g* to
   an honest sign-class probability. This layer absorbs the stated→revealed
   preference gap and the LLM's systematic inflation.

5. **Decision & abstention (M16–M19).** Output a calibrated sign-class
   probability *only inside the validated regime*; otherwise output
   "uncalibrated" and fall back to qualitative interview/redesign support. Never
   auto-kill.

**Why it would be directionally correct.** Not because the agents are realistic.
Because (a) the target requires only stochastic ordering, which is robust to
monotone distortion (§2.2); (b) the ordering signal is *learned to be* present by
beating a no-persona baseline on held-out experiments (M10); and (c) every claim
is wrapped in a calibration fitted to the product's own outcome history, so the
confidence number means what it says. Realism is a means to a sign-informative
feature, not the product.

---

## 4. Failure modes & mitigations

| # | Failure mode | Mitigation (claim) |
|---|---|---|
| F1 | Stated ≠ revealed preference | Behavioral elicitation + calibration to real outcomes (M5, M6) |
| F2 | LLM sycophancy / demand effects | Blinded, order-randomized paired deltas; demand-effect bias test (M6, M7, G2) |
| F3 | Prompt-format instability | Paraphrase sign-flip rate caps confidence / triggers abstention (M7, G2) |
| F4 | Mode collapse / lost heterogeneity | Between-agent response-variance floor ≥ 0.5× target; reject collapsed runs (M9) |
| F5 | Population not representative | Rake to real joint distribution; SMD/PSI balance gates (M8, M9) |
| F6 | Personas add noise, not signal | No-persona baseline is mandatory; personas must *earn* lift (M10, G11) |
| F7 | Network / equilibrium effects | Out of scope, flagged, routed straight to experiment (M11) |
| F8 | Backtest leakage (model "knows" the famous launch) | Hash-commit predictions before unblinding; label-permutation collapses to chance; famous-vs-obscure gap test (M13, G3) |
| F9 | Manufactured signal from nothing | A/A placebo is a disqualifying gate (M12, G1) |
| F10 | Noisy ground truth | Quality-weight experiments; downweight SRM failures, peeking, low power (M14) |
| F11 | Over-claiming on thin data | Sample-sufficiency gate; "uncalibrated" below floor (M19, G0) |
| F12 | Magnitude taken seriously | Magnitude is a non-goal; shrink hard; separate validation if ever claimed (M2) |
| F13 | Calibration drift (weekly product changes) | Rolling, time-decayed re-fit with expiry; PSI drift monitor; version pinning + golden-set rerun (M20) |
| F14 | Auto-killing a real winner | Asymmetric loss; abstain; re-rank not kill; tail-recall ≥ 0.80 side-constraint (M16, G9) |

---

## 5. Validation protocol

**Backtest design.** Assemble the product's historical experiments with their
true sign labels (positive / flat / negative after δ) and quality weights. For
each, reconstruct the pre-treatment state, run the simulator **blind**, and
**hash-commit** the predictions before unblinding the outcomes. Score by
cross-fitting / out-of-fold so the calibration layer is never evaluated on its
own training experiments.

**Mandatory integrity tests before any accuracy is reported:**
- **A/A placebo (G1):** feed identical arms; an actionable call (confidence ≥
  0.70) in > 5% of runs disqualifies the system.
- **Label permutation (G3):** shuffle outcome labels; balanced SMR must collapse
  to [0.40, 0.60], MCC to ~0. If it doesn't, you have leakage.
- **Robustness (G2):** paraphrase/order perturbations; sign-flip rate > 10% caps
  confidence.

**Sample sufficiency (G0, the math).** Using Wilson 90% intervals on an observed
balanced SMR of 0.70:

| n (sign-decisive experiments) | 90% CI | half-width |
|---|---|---|
| 50  | [0.585, 0.794] | ±0.10 |
| 100 | ~[0.622, 0.766] | ±0.075 |
| 150 | [0.635, 0.758] | ±0.06 |
| 200 | [0.644, 0.750] | ±0.05 |

Power to *pass* the SMR gate (0.70 with 90% LB > 0.55) when the simulator is
genuinely 0.70: ≈ 0.68 at n=50, ≈ 0.92 at n=100. So **50 is the hard floor**
(below it: "uncalibrated", qualitative only), **100 is the credible target for
the sign gate**, and **150–200 is required for the harder 3-class MCC-beats-
baseline gate** (paired-bootstrap difference test, more cases). Below the
credible-n, hierarchical partial pooling across products/treatment-classes is
mandatory and the *pooled effective-n* is what the gate reads (M21).

**Confidence-score semantics (M18–M19).** The number reported to the PM is the
calibrated empirical reliability of the predicted sign class, conditional on
validated regime, input quality, backtest coverage, and pinned version. It does
**not** report LLM certainty, individual-user truth, statistical significance,
expected magnitude, or permission to skip the experiment. It reads
**"uncalibrated"** off-support, below floor, prompt-unstable, networked, or
drift-expired.

---

## 6. The honest confidence contract

What the product is allowed to tell a PM, in plain terms:

> "Among changes like this one, where I have enough past experiments to know how
> well I predict, I'm right about the direction X% of the time. This idea looks
> like a [winner / wash / loser]. That is a reason to [prioritize / redesign /
> deprioritize-but-not-kill] it — not a substitute for the test."

And what it must refuse to say: any numeric confidence on a change it has no
calibration coverage for, any magnitude, and any "you can skip the experiment."

---

## 7. The certification gate (the operating contract)

The full ledger is `MERGED-LEDGER.md`; the gate is implemented and tested in
`harness/`. GO as a quantitative triage aid requires ALL of:

- **G0 Sample sufficiency** — `n_dir ≥ 50` floor (each sign ≥ 10); ≥ 100 for the
  SMR gate; ≥ 150 (≈200 sliced) for the MCC gate.
- **G1 A/A null** — actionable call on identical arms ≤ 5% of runs.
- **G2 Robustness** — sign-flip rate ≤ 10%; demand-effect bias CI contains 0.
- **G3 Leakage** — label permutation collapses SMR to [0.40,0.60], MCC to ~0.
- **G4 Direction** — balanced SMR ≥ 0.70, 90% LB > 0.55.
- **G5 Classification** — 3-class MCC beats best non-LLM baseline by ≥ 0.10
  (paired-bootstrap 90% LB > 0).
- **G6 Ranking** — Kendall τ_b ≥ 0.30 (90% LB > 0).
- **G7 Calibration** — ECE ≤ 0.08 (GO), 0.08–0.15 CONDITIONAL, > 0.15 NO-GO;
  Brier beats climatology by ≥ 10%.
- **G8 Decision value (PRIMARY)** — ΔU = U(π_sim) − U(π₀) > 0, bootstrap 90% LB
  > 0, at the pre-registered slot budget and false-green/false-red cost ratio.
- **G9 Tail safety** — top-decile true-winner recall ≥ 0.80 among deprioritized
  ideas.
- **G10 Abstention quality** — covered predictions strictly lower error than the
  full set; risk falls monotonically as coverage narrows.
- **G11 Persona value** — persona+row beats no-persona on ≥ 1 primary metric, no
  primary metric worse by > 0.02.

**NO-GO** (numeric confidence forbidden): G0 fail; G1 or G3 fail; SMR 90% LB ≤
0.50; ΔU 90% LB ≤ 0; ECE > 0.15; Brier no better than climatology; tail recall <
0.70 while recommending deprioritization; sign-flip > 20%. Between GO and NO-GO is
**CONDITIONAL**: qualitative aid only, no numeric confidence, no auto-kill.

---

## 8. What this means for Sidira (recommendations)

1. **Reframe the public claim** from "digital twins of your users" to "a
   calibrated pre-experiment triage that tells you which ideas are worth a test
   slot — and abstains when it doesn't know." The honest claim is more defensible
   *and* more valuable to a PM.
2. **Build the historical-experiment backtest before the persona realism work.**
   The calibration set is the asset; the personas are scaffolding. A customer with
   < 50 labeled past experiments gets "uncalibrated" + qualitative interviews,
   not a confidence score. This should be explicit in onboarding.
3. **Ship the confidence score gated on G0–G11.** Wire the harness in `harness/`
   into CI so a model/prompt/snapshot change cannot ship a confidence number
   without re-passing the gate on the golden set (M20).
4. **Make abstention and "redesign, don't kill" first-class product states**, not
   error states. The agent-chat interview surface is the right home for the
   CONDITIONAL regime.
5. **Pool across customers** (hierarchical) to bootstrap new/low-data customers,
   and read the pooled effective-n into the gate.

---

## 9. Open questions the councils did not close

- The exact form of the cost model in ΔU (false-green vs false-red ratio) is
  customer-specific and must be elicited per customer; the gate assumes it exists.
- Long-horizon and habit-formation metrics sit uneasily between "first-order"
  (in scope) and "adaptation" (out of scope); the boundary needs an empirical
  rule, not a definitional one.
- Whether verbalized distribution elicitation actually beats sampling-temperature
  ensembling as the source of *g* is an empirical question for the backtest, not
  settled here.

---

*Artifacts: `BRIEF.md`, `rounds/r1–r3` (both councils), `ROUND1-ARBITRATION.md`,
`MERGED-LEDGER.md`, `rounds/r3-*` ratifications, and `harness/` (runnable gate).*
