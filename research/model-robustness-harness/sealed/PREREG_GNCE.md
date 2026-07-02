# PRE-REGISTRATION — Grounded Novel-Counterfactual Extrapolation (GNCE)

**Sealed before any estimator or LLM call runs. sha256 committed separately.
No re-tuning of the harness to these predictions. Public + synthetic data only —
no partner data, numbers, or identity appear here or in any downstream artifact.**

Author: main loop. Date: 2026-06-30. Caps: synthetic = MECH-ONLY; Hillstrom = LEAD.

---

## The question this experiment answers

The founder's thesis: the product must **simulate and answer NOVEL questions** —
ones the customer can't already read off their own dashboards — and let them
**talk to the simulated users about *why*.** The prior bake-off (Waves 1–3) tested
the *wrong* thing for that thesis: it tested whether causal adjustment recovers a
KNOWN effect on an ALREADY-ESTIMABLE lever. It never tested whether a model
**fit without the treatment's outcome** can extrapolate to a **novel counterfactual.**

This experiment tests exactly that, and pits it against the failure mode we measured
(ungrounded LLM guessing tracks intuition → wrong on counter-intuitive cases).

### The mechanism that makes "simulate a novel feature" tractable

A truly novel feature has no historical variation, so it cannot be estimated by
comparison. The only honest path: **decompose the feature into a behavioral
mechanism whose proxy IS observed in the data.**

> Novel feature → shifts an observed mediator M (a leading indicator) → M drives the
> outcome Y. Fit Y = g(M, covariates) on data that never saw the feature; observe /
> posit how the feature shifts M; **simulate** ΔY = E[g(M_shifted) − g(M)].

This is structural / mediation extrapolation — the same logic by which demand models
predict prices never tested. **Grounded simulation never touches the treated outcome.**

### The deepest risk, registered up front

Grounded simulation does not make the hard problem disappear — it **relocates** it from
"T → Y" to "T → M" + "M → Y is policy-invariant (transfers from observed variation to
feature-induced variation)." If that relocation buys nothing — if M → Y learned on
organic variation does not transfer to feature-induced variation — grounded sim has no
edge. **The real test of transfer is the Hillstrom arm (P5).**

---

## ARM A — Synthetic mechanism battery (controlled, MECH-ONLY)

Deterministic seeded DGP, n = 8000 / case. Each case:
- Observed confounder `C ~ N(0,1)`; optional hidden `U ~ N(0,1)`.
- Treatment `T`: RCT p=0.5 (clean) OR `P(T=1)=σ(a·C + h·U)` (confounded).
- **Observed mediator** `M = bM·T + gM·C + ε` (the leading indicator).
- Outcome `Y = direct·T + lam·M + dC·C + (hid·U) + ε`; binarized at its median.
- Net true ATE sign on Y = sign(direct + lam·bM) [+ confounding contamination].

Four estimators per case, each emitting a **sign** (and abstain flag where defined):
- **GROUNDED-SIM** — fit g=Ŷ(M, C) on the **control arm only**; estimate T→M shift
  from observed M (M is a leading indicator, observed for all — NOT the novel outcome);
  simulate ΔY via the g-formula over M. Never sees treated Y.
- **LLM** — Groq call on the case's *narrative only* (no numbers): salient framing of
  direct effect + mechanism, asked for a sign + confidence. Sealed, graded blind. If
  Groq is unavailable, fall back to the documented **intuition-prior proxy** = sign of
  the *salient/direct* framing, and label the arm PROXY.
- **ORACLE** — causal adjustment (X-learner / DR) using treated Y. Upper bound.
- **TRUTH** — DGP sign.

### Archetypes (≥2 seeds each)

| id | direct | mediated (lam·bM) | net | M observed? | confounding |
|----|--------|-------------------|-----|-------------|-------------|
| MED-FLIP+   | − (intuition: bad) | + (dominant) | **+** | yes | none |
| MED-FLIP−   | + (intuition: good)| − (dominant) | **−** | yes | none |
| DIRECT-DOM  | + (dominant)       | + small      | **+** | yes | none |
| NULL        | 0                  | ~0 (cancels) | **0** | yes | none |
| MED-HIDDEN+ | − (intuition: bad) | + (dominant) | **+** | **NO** | none |
| MED-CONF    | − salient          | + dominant   | **+** | yes | observed C |
| MED-HIDCONF | − salient          | + dominant   | **+** | yes | **hidden U** |

### SEALED PREDICTIONS — Arm A

- **P1 (the USP claim).** On MED-FLIP± (mediator observed, counter-intuitive net):
  GROUNDED-SIM sign-accuracy **≥ 0.80**; LLM sign-accuracy **≤ 0.40**; grounded beats
  LLM by **≥ 3 cells.** This is the case the founder wants to win: intuition (LLM) is
  wrong, the grounded mechanism is right.
- **P2.** On DIRECT-DOM (intuitive): GROUNDED-SIM and LLM **both ≥ 0.70** — no grounded
  edge where intuition is already correct. (Honest: grounded sim's value is concentrated
  in counter-intuitive cases, not everywhere.)
- **P3.** On NULL: GROUNDED-SIM (abstain-or-correct) **≥ 0.70**; LLM invents a directional
  sign more often → LLM correct-or-abstain **< GROUNDED-SIM**.
- **P4 (the honest limit — the swipe-delete case).** On MED-HIDDEN+ (mediator UNOBSERVED):
  GROUNDED-SIM forced-guess **≤ 0.55** (≈ chance) AND, when allowed to abstain, abstain-rate
  **≥ 0.75**; ORACLE **≥ 0.80**. When the mechanism's proxy is not in the data, grounded
  simulation has NO edge — it must abstain. This is the boundary of the USP.
- **P5a.** On MED-CONF (observed confounding): GROUNDED-SIM that adjusts for C holds the
  correct net sign **≥ 0.70**; the *unadjusted* grounded sim flips on ≥1 cell (shows the
  adjustment inside the structural fit is load-bearing).
- **P6 (hidden confounding breaks grounded sim too).** On MED-HIDCONF: GROUNDED-SIM
  sign-accuracy **≤ 0.55** — hidden confounding contaminates the structural fit exactly as
  it contaminates plain adjustment; the NC-guard is the only protection (consistent with the
  engine-strength campaign). Grounded sim is NOT magic against hidden U.

---

## ARM B — Hillstrom mediation (real data, LEAD)

Real public RCT, 42,693 customers. Chain: **email `segment` (T) → `visit` (M) →
`conversion` (Y).** Covariates X = recency, history, mens, womens, newbie, channel, zip.

**Grounded protocol (never sees treated conversion):**
1. Fit `g = P(conversion | visit, X)` on the **No-E-Mail arm only**.
2. Observe `P(visit | T, X)` from both arms (visit is a leading indicator, observed for all).
3. Simulate email→conversion lift via the mediation g-formula using g (control-fit) and the
   email-induced visit shift. Compare to the **measured** email→conversion effect (both
   email arms pooled vs control).
4. **Placebo:** run the same machinery predicting an effect on a covariate the email cannot
   have caused (e.g. `mens`/`recency` treated as a pseudo-outcome) → must land ≈ 0.

### SEALED PREDICTIONS — Arm B

- **P7 (sign transfers).** Grounded structural extrapolation recovers the **POSITIVE** sign
  of the email→conversion effect. (Email strongly raises visit; visit→conversion is strongly
  positive even among organic visitors → predicted lift positive.)
- **P8 (magnitude is biased UP).** Predicted lift **OVER-estimates** the measured lift
  (ratio predicted/measured **> 1.2**), because organic (no-email) visitors are
  self-selected higher-intent than email-induced visitors, so the control-fit g over-credits
  email-induced visits. **Direction of the bias is the falsifiable call** — if it
  under-estimates instead, P8 is wrong.
- **P9 (placebo clean).** The placebo pseudo-outcome lift is within ±1 measured SE of 0.

---

## Grading

Per arm, a SCORECARD_GNCE.md tabulates sign-accuracy per archetype, the GROUNDED-vs-LLM
delta, abstain behavior, and Hillstrom predicted/measured ratio. Each Pn marked
HELD / REFUTED / PARTIAL against these sealed thresholds. Append all runs to LEDGER.md.

## What each outcome means for the founder's thesis

- **P1 holds + P4 holds** → the USP is real *and bounded*: grounded simulation answers novel
  counter-intuitive questions where intuition (LLM alone) fails — **but only when the
  mechanism's proxy is in the data.** "Simulate + talk to users" works through grounded
  mechanisms; it abstains honestly when there's no signal. This is the buildable version of
  the vision.
- **P1 refuted** → grounded simulation does NOT beat intuition even with an observed
  mechanism; the novel-question USP has no empirical foundation and we say so.
- **P7 holds** → the M→Y relationship transfers on real data — the relocation (T→Y into
  T→M + M→Y) actually buys something. **P7 refuted** → the policy-invariance assumption
  fails on real data and grounded sim is fragile outside synthetic control.
