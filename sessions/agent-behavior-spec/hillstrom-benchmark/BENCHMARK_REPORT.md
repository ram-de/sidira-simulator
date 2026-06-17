# Sidira Accuracy Benchmark — Living Report

> **Status: IN PROGRESS** (last updated 2026-06-17 — Hillstrom certified + fix attempt #1 null). This is the working draft that
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

**The sealed, powered run — DONE, and the finding is now CERTIFIED.** We pre-registered the
full configuration *and* our prediction (canonical-JSON SHA-256
`59dab05c…dce3`, committed to version control before any result existed), then ran the
benchmark at adequate power: **8 segment-cases** (a persona-aligned stratification of the
audience — men's-buyer, women's-buyer, high-spender, mid-tier — each scored against its own
sub-audience), **50 simulated respondents per arm**, on **both** outcomes. Both runs cleared
the certification floor and **earned a passing null-integrity certificate** — the numbers are
trustworthy, not artifacts of leakage or under-powering:

| outcome | null-certificate | direction accuracy | heterogeneity rank-ρ (p) |
|---|---|---|---|
| **conversion** | **PASSED** | **0.0** | −0.36 (p = 0.82) — at chance |
| **visit** | **PASSED** | **0.0** | −0.29 (p = 0.77) — at chance |

Two things are now established with confidence, on real randomized ground truth:

1. **The advertising-as-harm bias is certified.** Direction accuracy is **0.0 on both
   outcomes** — *every* per-segment prediction has the wrong sign. The simulator predicts the
   promotional emails *reduce* both visits and conversions; the real experiment shows they
   *increase* both. This is no longer a hint from an under-powered probe — it is a
   pre-registered, blind, null-certified result.

2. **The "who-responds-more" claim does not hold today — and we say so plainly.** The
   per-segment heterogeneity rank correlation is slightly *negative* and statistically
   indistinguishable from chance on both outcomes (p = 0.82, p = 0.77). Our pre-registered
   prediction was *positive* gender-matched heterogeneity; that prediction is **refuted**.
   The encouraging +0.24 ranking the small probe hinted at did **not** survive at power — the
   same small-sample-mirage lesson Upworthy taught us (§3), caught again by the same
   discipline. We do not get to claim the headline heterogeneity result on this dataset.

This is, deliberately, a hard result to report — and reporting it cleanly is the entire
point of the program. We have now found, on fully external real-world ground truth, the
*precise* condition under which the simulator is wrong (promotional/advertising content,
both outcomes, sign-inverted) and the *precise* claim it cannot yet support (per-segment
heterogeneity ranking on this dataset). Both are pre-registered, both are null-certified,
neither is hidden.

**Status: COMPLETE and certified.** The next move is not another benchmark — it is the
*fix*: correct the advertising-as-harm bias at the outcome-elicitation / calibration layer,
then re-run this exact pre-registered benchmark to measure the improvement. The benchmark has
done its job: it converted a vague worry ("is the simulator accurate?") into a specific,
reproducible, certified engineering target.

### Fix attempt #1 — affordance rendering (an honest null, and a sharper diagnosis)

The first hypothesis for *why* the simulator reads a promotional email as harmful: the blinded
view it gives each simulated respondent showed the email as a static object, while omitting the
one fact that makes a marketing email matter — that it is a *clickable prompt that leads back
into the product*. So we built a fix (gated, off by default) that renders any interactive
element together with where it leads ("opens: Site"), derived purely from the product's own
navigation structure — a general fidelity improvement, not a promo-specific rule.

We pre-registered a fresh prediction (hash `1e2e3150…7598`) — that this would move direction
accuracy off 0.0 — and re-ran the **exact** certified benchmark with only that one setting
changed:

| outcome | direction accuracy (before → after) | heterogeneity rank-ρ (before → after) |
|---|---|---|
| conversion | 0.0 → **0.0** | −0.36 → −0.22 (both at chance) |
| visit | 0.0 → **0.0** | −0.29 → −0.38 (both at chance) |

**The fix did not work, and we say so.** Direction accuracy stayed pinned at 0.0 on both
outcomes; the small rank-ρ wobble is statistical noise (both ends sit at chance). Our
pre-registered prediction was disconfirmed. The fix remains in the codebase as a defensible
rendering improvement but is **left switched off** — it is not the cure.

**What the null taught us (this is the value).** The bias is *not* an information gap in the
rendering — the agent had the navigation fact and still predicted harm. The more likely
mechanism is deeper: a simulated respondent asked to introspect "how often would you visit?"
reasons deliberately ("an email doesn't *make* me visit; I visit when I want to") and so cannot
capture a marketing **nudge** — an effect that, in the real world, operates *below* conscious
deliberation. That is a genuine boundary of verbalized, introspective simulation, and it
reframes the next experiment: the question is no longer "does the agent have the right facts?"
but "can this *class* of model reason about sub-deliberative effects at all, or is a more
capable model required?" The immediate next test is therefore a **model comparison** — re-run
this identical pre-registered benchmark with a stronger model — which cleanly separates "a
weaker model's reasoning failure" (fixable by model choice) from "an intrinsic limit of
introspective elicitation" (which would redefine the product's honest scope).

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
- 2026-06-17: Hillstrom **powered run complete and certified** (prereg SHA-256
  `59dab05c…dce3`; 8 segment-cases, 50/arm, both outcomes). Both arms earned a PASSING
  null-integrity certificate. **Certified findings:** (1) advertising-as-harm sign
  inversion — direction accuracy 0.0 on both conversion and visit; (2) per-segment
  heterogeneity ranking at chance on both (ρ −0.36 p=0.82 / −0.29 p=0.77) → the
  pre-registered positive-heterogeneity prediction is refuted. §4 updated; "pending"
  status retired. Next: fix the bias at elicitation/calibration, then re-run this exact
  pre-registered benchmark to measure the delta.
- 2026-06-17: **Fix attempt #1 (affordance rendering) — pre-registered (`1e2e3150…`) and
  re-run; HONEST NULL.** Direction accuracy stayed 0.0 on both conversion and visit; prediction
  disconfirmed. Fix left in codebase but gated OFF. Sharper diagnosis: the bias is not a
  rendering information-gap but a deeper limit of introspective elicitation (can't capture a
  sub-deliberative marketing nudge). Next lever: model comparison (re-run with a stronger model).
</content>
