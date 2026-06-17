# Sidira Accuracy Benchmark — Living Report

> **Status: IN PROGRESS** (last updated 2026-06-16). This is the working draft that
> grows as each benchmark result lands. It is the source for the eventual public
> technical report on sidira.ai/research. Design principle: **publish the science of
> measurement, conceal the science of prediction** — this document explains *what we
> measure and how rigorously*, never the internals of how the simulator predicts.

---

## 1. What this report is, and why it exists

Sidira simulates how a real audience reacts to a product change *before* you ship it.
The obvious question any serious buyer (think: a Ron-Kohavi-class experimentation
leader) asks is: **how do you know it's right?** This report is our answer. It is
deliberately built to be *disconfirmable* — we pre-commit to predictions, we test
against real-world ground truth, and we publish the results whether they flatter us
or not.

We make a sharp, honest distinction up front between two very different claims:

- **Magnitude prediction** — "this change will lift CTR by 1.3 points." We do **not**
  claim this, and this report shows *why* we're right not to.
- **Directional prediction** — "version A beats version B," and "segment X responds
  more than segment Y." This is what the product actually sells, and it is what we
  set out to validate.

A directional simulator that is honest about its limits is worth far more to a
decision-maker than a magnitude simulator that quietly overpromises.

---

## 2. The measurement discipline (the part we're proud of)

Every benchmark in this report runs under the same four guardrails. These are the
methodology; they don't change between datasets.

1. **Pre-registration.** Before a run, we hash-commit (canonical-JSON SHA-256) the
   full configuration *and our predicted result* — direction, expected ranking — so
   we cannot retrofit a story to the outcome afterward. The hash is recorded in git
   before any result exists. (This discipline already paid for itself once — see §3.)

2. **Blind evaluation.** The predictor never sees the answer key. By construction, the
   thing that produces the prediction derives its inputs *only* from the scenario, not
   from the real-world outcome being predicted. The outcome is not an input to the run.

3. **Null-integrity certificate.** After a run we re-score the predictor against
   *scrambled* labels many times. If the predictor is genuinely blind, its score on
   shuffled answers must center at chance. A run that cannot demonstrate this is marked
   **VOID** and explicitly not to be trusted — no exceptions. This catches the single
   most common way benchmark numbers lie: subtle label leakage.

4. **No silent truncation.** Every case and every stratum is reported — including the
   ones that look bad, score negatively, or are underpowered. If a run is too small to
   certify, we say so rather than reporting a number that looks clean.

The primary endpoint everywhere is **rank correlation** (Spearman ρ) between predicted
and actual effects; directional sign-accuracy is secondary. Magnitudes are treated as
**uncalibrated** and are not reported as effect sizes.

---

## 3. Benchmark 1 — Upworthy headline CTR (an honest null)

**The dataset.** The Upworthy Research Archive: thousands of real headline A/B tests
with measured click-through rates — a genuine, large, public record of what actually
got clicks.

**The question.** Can the simulator *rank* headlines by their real CTR lift?

**The result: no — and we can prove it cleanly.** A fully pre-registered run on 60
fresh, held-out, de-noised headline tests (committed prediction hash
`bbe0c160…8661`) returned:

- **rank-ρ = −0.110** (p = 0.81) — squarely at chance.
- **direction accuracy = 0.45** — also at chance.
- **null-integrity certificate: PASSED** (the null is trustworthy).

**The story behind it — why pre-registration mattered.** An earlier exploratory probe
(n = 20) had shown an encouraging rank-ρ of **+0.386** (p = 0.045). It was tempting.
But it was pre-registered and then tested on fresh cases at larger scale — and it
**did not replicate**. It was a small-sample false positive, and our own discipline
caught it before it ever became a published claim. This is exactly what the method is
for.

**Why the ceiling is genuine, not a fixable artifact.** The natural objection is
"your synthetic audience just wasn't good enough — build a better panel." We
investigated this directly and the objection does not hold *for this dataset*: the
Upworthy archive is **headline-level only** — it records headlines and their click
rates, but nothing about *who* the readers were. There is no per-reader data from
which a realistic audience panel could ever be built. A better panel is not
sourceable here, so the ceiling is a property of the problem, not of our current
implementation.

**What we conclude (and will publish).** The simulator does **not** predict the
magnitude-ranking of real headline CTR above chance, and we say so plainly. This is
not a weakness we hide — it is the boundary of the directional claim, drawn honestly.
A buyer learns more from a vendor who shows them a clean null than from one who only
ever shows wins.

---

## 4. Benchmark 2 — Hillstrom email uplift (the directional test, in progress)

Upworthy answered "can we rank magnitude?" (no). Benchmark 2 asks the question the
product is actually built around: **does the simulator get the *direction* and the
*who-responds-more* right, against a real randomized experiment?**

**The dataset.** The Hillstrom MineThatData e-mail challenge: 64,000 real customers,
each with real pre-treatment attributes (purchase recency, spend history, whether
they previously bought men's vs women's merchandise, location, acquisition channel),
randomly assigned to one of three arms — a men's-merchandise promotional email, a
women's-merchandise promotional email, or no email — with measured outcomes (site
visit, purchase conversion). Because the arms are *randomized*, the real causal effect
of each email is simply the difference in outcomes between arms — an actual controlled
experiment to test against. This is the strongest kind of ground truth there is.

**Why this dataset is the right test.** Unlike Upworthy, Hillstrom has real
per-customer attributes — so we *can* build a realistic audience from real data — *and*
it has randomized directional outcomes. It lets us test not just "did email help?"
(too easy — email almost always beats no-email) but the genuinely hard, genuinely
valuable question: **does the simulator know that customers who buy men's merchandise
respond more to the men's email?** That "who responds more" question — heterogeneity —
is the only claim a sophisticated buyer can't trivially guess, so it is our headline.

**The three nested endpoints (weakest → strongest):**
1. *Sign agreement* — does the simulator get the direction of each effect right?
2. *Arm ranking* — does it rank the arms in the right order? (Largely the trivial
   email > no-email gradient; necessary but not sufficient.)
3. **Heterogeneity (the headline)** — does the simulator's *per-segment* predicted
   uplift rank-correlate with the *real* per-segment uplift? I.e. does it know which
   audience responds most? This is the Kohavi-proof claim.

**Prerequisite check — PASSED (the pivotal early result).** A directional heterogeneity
claim is only possible if the audience model actually distinguishes men's-buyers from
women's-buyers in the first place. We built the audience from the real Hillstrom
attributes and checked. It separates cleanly:

| audience segment | gender signal |
|---|---|
| a **pure men's-buyer** segment | men's-merchandise = 100%, women's = 0% |
| a **pure women's-buyer** segment | women's-merchandise = 100%, men's = 0% |
| a high-spender segment | both |
| a mid-tier segment | both |

The audience genuinely contains the structure the headline claim depends on. *(Honest
caveat: the clustering's stability score at this setting is 0.52 — above our floor but
modest; it is the only setting that keeps the gender separation without collapsing, and
we will disclose it as a limitation.)*

**Pre-registered prediction (committed before any run).** We predict the simulator
will show *gender-matched* heterogeneity — the men's-buyer segment responds more to the
men's email, the women's-buyer segment more to the women's email — i.e. positive
per-segment rank correlation with the real experiment, with a passing null certificate.
We also pre-commit to the two honest failure modes: (a) the real experiment may not
actually show clean gender-matched heterogeneity, in which case we score against
whatever it *does* show; (b) the simulator may simply not capture it, in which case we
report the null.

**Probe (plumbing dry-run) — done.** A small, deliberately under-powered probe (6
segment-cases) confirmed the entire measurement pipeline runs end-to-end against real
data: zero cases dropped, the audience-conditioning (running each segment against its
own sub-audience) works, and the null-certificate and per-segment reporting machinery
all function. As designed for a run this small, it is **VOID — underpowered** (6 cases
is below our certification floor of 8), so its numbers are *not* trusted; it exists
only to validate the harness. It did surface three concrete things to settle before the
real run:
1. the full run needs finer stratification to clear the ≥8-case certification floor;
2. **a genuine, important finding (now classified, not a bug).** The probe's predicted
   conversion *directions* ran opposite the real experiment — *every* sign flipped —
   while the *ranking* correlated positively. We confirmed it is real, not a
   sign-convention error: the real experiment shows both emails *raise* conversion
   (men's +0.68pp, women's +0.31pp), but the simulator predicts both emails *lower* it
   (−0.01 to −0.03). The simulator systematically reads a promotional email as mildly
   off-putting for conversion. This matches a prior independent internal finding that
   the simulator can read advertising as harm. Two honest consequences: (a) a
   *direction/sign* claim on conversion does **not** hold today — this is a real,
   nameable limitation, and a fixable one (it points squarely at the outcome-elicitation
   and calibration work on our roadmap); (b) the *relative ranking* survived the sign
   error — the simulator still ranked the men's email above the women's email, matching
   the experiment, which is why the rank correlation came out positive. The full run
   will establish whether that ranking signal is real with adequate power, and will also
   test the *visit* outcome (a stronger, larger real signal that may be less biased than
   conversion);
3. a minor audience-texture degradation to tidy up.

**Second probe — the visit outcome (is the bias outcome-specific?).** We ran the same
small dry-run against the *visit* outcome (did the customer come to the site), a larger,
stronger real signal than conversion. The bias is **not** outcome-specific: the
simulator again predicted every email *lowers* visits (−0.015 to −0.027) while the real
experiment shows emails strongly *raise* them (≈ +5–7 points). Direction accuracy was
again 0.0, and the relative ranking did *not* survive here (it came out negative). Both
dry-runs are under-powered (6 cases, VOID) so the numbers are not trusted — but the
sign inversion is robust across both outcomes.

**What the two dry-runs establish (the campaign's central finding so far).** The
simulator carries a **systematic "advertising-as-harm" bias**: on a real randomized
email campaign it predicts that promotional emails *reduce* both site visits and
conversions, when in reality they *increase* both. This is the second independent
confirmation of the pattern — we first saw it internally on a retention metric, and now
on a fully external, real randomized experiment. Two independent datasets pointing at
the same failure mode makes it a real, named, **fixable** property of the current
outcome-elicitation, not a fluke. It is, bluntly, *the* accuracy problem to solve — and
finding it precisely, on real ground truth, is exactly what this benchmarking program
is for.

**Why this is good news, not bad.** A vendor who can point to the specific, reproducible
condition under which their tool errs — and is already instrumenting the fix — is far
more credible than one who claims uniform accuracy. The path from here is concrete:
(1) a sealed, powered run (in progress) to certify the finding with a passing
null-integrity certificate and quantify the bias precisely; (2) correct the bias at the
outcome-elicitation / calibration layer; (3) re-run the same pre-registered benchmark to
measure the improvement. The benchmark doesn't just grade the product — it now defines
the next accuracy milestone.

**Status: sealed, powered run pending** (awaiting a finer-stratification change so the
run clears the certification floor and earns a PASSING null certificate). Result and
verdict appended here when it lands.

---

## 5. What this report will and won't ever claim

- **Will:** that the simulator reproduces the *direction* and *ordering* of real
  outcomes — including *who responds most* — validated blind, pre-registered, against
  public real-world experiments, with the failures shown alongside the wins.
- **Won't:** that it predicts the *magnitude* of an effect. Magnitude stays explicitly
  out of scope until (and unless) a future calibration layer earns it, on its own
  pre-registered evidence.
- **Generality caveat:** one experiment, however clean, is one data point. A second
  independent real-world experiment is the natural next anchor before any claim of
  generality.

---

## Appendix — running changelog
- 2026-06-16: Report started. Upworthy null finalized (§3). Hillstrom design,
  heterogeneity-prerequisite PASS, pre-registered prediction, and probe dry-run
  recorded (§4). Sealed full run pending.
</content>
