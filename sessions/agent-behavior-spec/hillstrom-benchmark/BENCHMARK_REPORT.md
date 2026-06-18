# Sidira Accuracy Benchmark — Living Report

> **Status: IN PROGRESS** (last updated 2026-06-17 — Hillstrom certified; fix attempt #1 null; **fix attempt #2 FIXES the sign inversion at power (visit direction accuracy 0.0 → 1.0)** via elicitation reframing; **fix attempt #3 CERTIFIES who-responds-more heterogeneity for visits (ρ +0.42, p=0.010, both models; gender-match differential +0.75, p=0.0004) — the Kohavi-proof claim now holds**; conversion heterogeneity still not certified; fix attempt #4 / engine integration: the standalone wins did NOT initially transfer through the production engine pass (roleplay dir-acc 0.00, forecaster 0.12); **fix attempt #5 RESOLVES it — a comparative-delta elicitation recovers the lift through the engine (0.12 → 1.0 direction accuracy) and is validated END-TO-END through the production runner (+10pp, 90% CI clear of zero, matching the RCT), flag-gated/default-off; **fix attempt #6 — the powered run CERTIFIES who-responds-more heterogeneity through the comparative engine pass GIVEN segment-rich personas (Spearman ρ +0.385, p=0.015), confirming the lever is the comparative pass AND audience richness together — the generic production persona pack is the remaining gap; **fix attempt #7 closes that gap — a persona enricher that turns the segment stats the personas already carry into readable descriptions lets the comparative pass recover heterogeneity even better than hand-written text (ρ +0.457, p=0.004), validated from real feature stats. The two production levers (comparative pass + persona enrichment) are now both proven AND shipped: the enricher service is in the engine (the benchmark persona pack is enriched), and the comparative metric pass is flipped **default-ON** (no customers, post-validation); the upstream persona-build naming integration (sidira-personas) for real-customer packs + the customer backtest pilot remain**). This is the working draft that
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

> **✅ RE-EXAMINED AND CONFIRMED — the ad-aversion SURVIVES de-confounding (2026-06-17).** After
> the portfolio reversal (§7) — where a "certified" negative turned out to be a self-inflicted
> stimulus-construction artifact — we applied the same audit lens here and found a real harness
> confound: the elicitation `decision_point` was hardcoded to *"the customer is reading the
> promotional e-mail in their inbox"* and fed to **both** arms, including the **No-E-Mail
> control** — so the control agent was told it was reading the very email the treatment adds.
> We fixed it (PR #361: decision_point → *"the customer is looking at their inbox"*, email-free;
> the treatment email is carried only by the already-arm-correct per-arm structural spec; guarded
> by `test_hillstrom_decision_point_deconfound`) and ran a **pre-registered, single-variable clean
> re-run** (PREREG_FIX1, canonical SHA `f2947b39…` committed before the result; Groq, same 8
> cases, both outcomes). **Result: `direction_accuracy` stayed at exactly 0.0 on BOTH conversion
> and visit** (cert PASSED, not VOID; rank_ρ conv −0.16 / visit +0.19, both at chance). The
> pre-registered prediction (dir_acc would move off 0.0) was **wrong in the un-flattering
> direction** — the strongest evidence the verdict is real. So §4/§5.1 **STAND, strengthened**:
> the decision_point confound was a genuine bug worth fixing but was **not** load-bearing for the
> sign inversion; the ad-aversion is intrinsic to introspective elicitation of a sub-deliberative
> nudge, not a rendering artifact. **One narrowing:** "model-independent" originally rested on
> Groq==Sonnet==0.0 on the *confounded* harness (= shared-stimulus agreement, not a true model
> property); the clean re-run re-establishes the bias for **Groq** only — a Sonnet clean re-run is
> an optional confirmation, no longer the load-bearing evidence. (Contrast §7: there, de-leaking
> *flipped* the score — that one WAS an artifact. The discipline distinguished the two.)

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

### Fix attempt #2 — elicitation reframing (the sign inversion is FIXED, at power)

The diagnosis above pointed at the elicitation *mode*, not the facts: an agent asked to
introspect "how often would I visit?" reasons deliberately and misses a sub-deliberative
nudge. So fix attempt #2 changed a single variable — **the outcome is elicited as an
expert forecast of how the campaign moves the metric, not as a roleplayed reader's
introspection** — and was pre-registered (`PREREG_FORECASTER.json`, SHA `91137220…`,
committed before the result) on a finer real-data stratification (gender × recency × email,
18 cases, ground truth recomputed from the Hillstrom RCT).

| predictor (VISIT) | direction accuracy | heterogeneity rank ρ (perm p) |
|---|---|---|
| introspective reader-roleplay (certified §4) | **0.0** | −0.29 (at chance) |
| **expert-forecast elicitation** | **1.000 (18/18)** | +0.37 (p = 0.13) |

**The advertising-as-harm sign inversion is fixed.** Direction accuracy moves from a
*certified* 0.0 to **1.0 at power** — the bias was an artifact of introspective elicitation,
not an intrinsic limit of the simulator. This resolves the §4 finding's central question in
the un-flattering-prediction-survives direction: it was the elicitation mode. **One honest
narrowing:** the *who-responds-more* heterogeneity ranking improved from −0.29 to +0.37 but
does **not** clear significance at n=18 (permutation p = 0.13) — and the small probe that
first hinted at it (+0.65, n=6) regressed under power, the same small-sample-mirage the
program keeps catching. So the sign claim is certified-fixed; the heterogeneity claim is
"positive-leaning, not yet certified — needs more cases." The fix is also model-dependent
(it is clean on the stronger model; a weaker one still mis-signs a third of cases), which
answers the §4-Fix-#1 question as *both*: a capable model **and** the right elicitation mode.

### Fix attempt #3 — the who-responds-more claim, now certified at power

Fix #2 fixed the *sign*. But a skeptic is right to note that "email beats no-email" is
partly common-world knowledge — the claim the product actually sells is *heterogeneity*:
**which audience responds most.** So we pre-registered a pass/fail bar (`PREREG_HETEROGENEITY.json`,
SHA `7e38d59e…`, committed before the result) — heterogeneity is certified only if the visit
rank correlation exceeds 0.30 with permutation p < 0.05 — and tested it at power on a finer
real-data stratification (gender × recency × channel × email, 38 cases).

| | visit heterogeneity ρ (perm p) | gender-match differential ρ (perm p) |
|---|---|---|
| original reader-roleplay (§4) | −0.29 (at chance) | — |
| **expert-forecast elicitation** | **+0.42 (p = 0.010)** ✅ | **+0.75 (p = 0.0004)** ✅ |

**The who-responds-more claim clears its pre-registered bar** — and the sharpest, least-
guessable form of it (the *gender-match differential*: does the model know that, within one
audience, the men's email out-pulls the women's email by the right amount?) is the strongest
result in this report at p = 0.0004. The visit ranking also replicates on a second model, so
it is not model-idiosyncratic. **Two honest narrowings:** (a) *conversion* heterogeneity is
positive but does **not** clear significance (ρ +0.26, p = 0.11) — the certified claim is
visit-only; (b) the sharp gender-match differential is clean only on the stronger model. This
is the first time, anywhere in this program, that the headline directional-heterogeneity claim
the product is built on has been *certified* against a real randomized experiment — pre-
registered, permutation-tested, with the parts that didn't clear shown alongside.

### Fix attempt #4 — engine integration (honest caveat: the lift does NOT yet transfer in-product)

Fixes #2/#3 were measured on a **standalone** forecaster elicitation (a direct, change-explicit,
percentage-point forecast over rich segment descriptions). That validated framing was then shipped
into the production engine behind a flag and made the default (`SIDIRA_ELICITATION_MODE=forecaster`).
A **powered through-engine re-benchmark** — driving the *production* metric seam
(`compose_metric_prompt` + `elicit_visit_decision`) over the real panel — shows the standalone win
does **not** carry through: roleplay visit direction-accuracy **0.00**, forecaster only **0.12** (the
standalone run hit 1.0). Diagnosis: the engine metric pass is **blinded** (the treatment is not
legible to the forecaster as a specific change), uses a **coarse /10 allocation** (small real uplifts
round to ties), and conditions on **generic GMM personas**. The standalone win needed
change-legibility + magnitude elicitation + audience richness together, not the framing voice alone.
**Status: the lever is the deployed default (never worse than roleplay, which is provably backwards),
but the accuracy lift is NOT yet realized through the engine** — we make no in-product accuracy claim
until this through-engine benchmark turns green. Work in progress: make the treatment legible to the
forecaster without re-introducing demand-effect bias, finer-grained elicitation, richer audience
conditioning — re-gated by this same through-engine run.

### Fix attempt #5 — comparative-delta elicitation RESOLVES the engine-integration gap

Fix #4 localized the cause: the engine forecast the two arms in **independent passes
and subtracted**, so each anchored on the same base rate and the real ±7pp effect
collapsed to ~0. Fix #5 changes that to a **single comparative pass** — the
forecaster sees both versions and gives the directional difference directly.

| through the engine (visit direction accuracy) | result |
|---|---|
| per-arm roleplay | 0.00 |
| per-arm forecaster | 0.12 |
| **comparative-delta forecaster** | **1.00** |

It is validated **end-to-end through the production runner** (real
`SimulationRunner.run`, A/B, flag on): every treatment agent produced a comparative
delta and the production aggregation returned **+10pp, 90% CI (8.5, 11.5)** —
positive, CI clear of zero, matching the RCT (the email raises visits). The
through-engine direction milestone is now met.

**Status & honest limits.** Shipped flag-gated (`SIDIRA_METRIC_COMPARATIVE`,
**default OFF**) — proven to work when on, but the production default is unchanged.
The end-to-end run is n=8 / one case / one model (green on **direction**, not
powered), and **heterogeneity through the comparative engine is not yet validated**
(the deltas are clustered — the richer-audience lever is open). The next step is a
**powered + heterogeneity run through the comparative engine**; only after that
(and a deliberate decision) would the default flip. No in-product accuracy claim
beyond direction until then.

### Fix attempt #6 — heterogeneity recovers through the comparative engine (given rich personas)

The powered run (pre-registered, bar fixed first: ρ>0.30 AND p<0.05) drove 38
gender×recency×channel strata — each a **descriptive** segment persona — through the
production comparative pass.

| approach | Spearman ρ (perm p) |
|---|---|
| standalone forecaster (Fix #3) | +0.42 (0.01) |
| comparative engine, generic GMM personas (e2e) | ~0 (clustered) |
| **comparative engine, segment-rich personas** | **+0.385 (0.015)** ✅ |

**CERTIFIED.** The who-responds-more ranking recovers through the production
comparative pass — *when the audience carries segment signal*. So the lever is the
comparative pass **and** persona richness together: the same pass with the thin
production GMM pack gives clustered deltas (direction only), so **enriching the
persona conditioning is the remaining product gap** before this lands in the
default. One dataset / metric (visit) / model; still flag-gated, default OFF.

### Fix attempt #7 — persona enrichment closes the gap (the missing cluster-naming step)

The live personas carry segment signal only as raw stats
(`value_sensitivity.history (-0.60σ)`) — the cluster-naming step never ran. An
**enricher** that turns those real feature stats into readable descriptions
(*"Men's-only shoppers split almost evenly between new and returning customers…"*)
recovers heterogeneity through the production comparative pass **even better than
hand-written text**:

| audience conditioning | Spearman ρ (perm p) |
|---|---|
| raw-jargon GMM personas (live gap) | ~0 (clustered) |
| hand-written rich personas | +0.385 (0.015) |
| **enricher-generated (real stats → NL)** | **+0.457 (0.004)** ✅ |

So the two production levers — **comparative pass** + **persona enrichment** — are
both proven; together they recover the certified who-responds-more ranking through
the engine. The gap was never the method, only that the persona descriptions were
stats, not language.

**Now shipped (2026-06-18):** the enricher is a backend service
(`services/persona_enricher.py`), the benchmark Hillstrom pack's descriptions are
enriched (jargon → language), and `SIDIRA_METRIC_COMPARATIVE` is flipped
**default-ON** (no customers in production, so zero impact; opt out with `=0` to
reproduce the per-arm baseline). Remaining: run the enricher in the upstream
persona-build naming step (sidira-personas) for real-customer packs, broaden beyond
visit/one-model, and the customer backtest pilot. Still: magnitudes uncalibrated.

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

### 5.1 The scope the evidence actually supports (honest positioning)

The Hillstrom null draws a clean line worth stating plainly, because it is a *feature* of how
the product should be sold, not a hidden weakness:

- **In scope — deliberative reactions to a product change.** Sidira's core job is to simulate
  how a real audience *consciously reacts* to something you can show them: a new feature, a
  redesign, a pricing change, a flow. These are decisions a person can introspect and report on
  ("given this screen, what would I do?") — exactly what verbalized agent simulation is built
  to capture. The directional discipline in this report (blind, pre-registered, null-certified)
  is what makes that claim trustworthy.
- **Out of scope (today) — sub-deliberative channel effects.** A marketing email's lift is a
  *nudge*: it works by reminding and re-surfacing, below the level a person would report when
  asked to introspect their own behavior. The Hillstrom benchmark is precisely such a nudge, and
  the certified null shows the current method does not capture it. We do **not** claim
  marketing-channel or ad-campaign lift prediction. Naming this boundary — on real RCT evidence,
  rather than discovering it in front of a customer — is itself the trustworthy move.

> **✅ UPDATED — see the §4 banner.** A 2026-06-17 audit found the harness fed a control-
> contaminating `decision_point` to both arms, so the model-comparison agreement below could not,
> by itself, establish intrinsicness (both models ran on the same confounded stimulus). We fixed
> the confound (#361) and ran a pre-registered clean re-run (Groq): `direction_accuracy` stayed
> 0.0 on both outcomes → the ad-aversion is **confirmed robust to de-confounding** and is not a
> stimulus artifact. The "intrinsic" conclusion now rests on that clean Groq re-run; the original
> Groq==Sonnet agreement (on the confounded harness) is corroborating, not load-bearing. A Sonnet
> *clean* re-run remains an optional confirmation of model-independence specifically.

The model-comparison test probed whether that boundary is *intrinsic* to introspective
simulation or merely a limit of the current model. **It is now settled: intrinsic.** Re-running
the identical pre-registered benchmark with a frontier model (Claude Sonnet 4.6) in place of the
smaller Groq model left direction accuracy at **0.0 on both conversion and visit** — the
stronger model is *exactly* as backwards. The bias is therefore model-independent, not a
weak-model reasoning failure, so the in/out-of-scope line above is a property of verbalized
introspective elicitation itself rather than of a model choice. This is the strongest,
moat-preserving form of the result: it is publishable, it does not widen the claim, and it
tells us a production model swap will not buy directional accuracy on sub-deliberative nudges.

---

## 6. Benchmark 3 — Cookie Cats gate move (the first in-scope test, and a structural lesson)

Hillstrom and Upworthy both probe the *perimeter* of what Sidira sells (a marketing nudge, a
headline). Benchmark 3 is the first to test the **center**: a deliberative reaction to a real
**product change**. Cookie Cats is a real mobile-game A/B test — the first forced progress gate
was moved from level 30 to level 40 — measured on 90,189 players. Its ground truth is
*counter-intuitive*: the **earlier** gate wins on 7-day retention (real lift = −0.0082), even
though the naive product instinct ("a later wall = more free play = happier players") predicts the
opposite. A simulator that merely echoes that instinct fails this test.

**The headline result (the clean causal question).** On the whole-population gate_30-vs-gate_40
comparison for the primary metric (7-day retention), the simulator predicted the **correct,
counter-intuitive direction**: that moving the gate later *lowers* retention (direction accuracy
1.0). This is the first time the simulator has called a counter-intuitive *real product-change*
winner correctly against external ground truth — a genuine, encouraging signal pointing the right
way, and qualitatively different from the perimeter results.

**The honest caveat (and it is decisive).** That clean comparison is a single case (one population,
one number), so the null-integrity certificate is **VOID** — a single label cannot be scrambled, so
the permutation null has no power to rule out leakage. The result is therefore **suggestive, not
certified**. The only endpoints that clear the 8-case certification floor are by-engagement-octile
slices, and they sit at chance (rank-ρ −0.46 / +0.05; direction 0.125 / 0.25 on retention_7 /
retention_1) — but those slices condition on `sum_gamerounds`, a **post-treatment** variable, so they
are confounded *by construction* (pre-registered as descriptive, not causal) and are a poor scoring
target.

**The structural lesson (this shapes the whole program).** You cannot manufacture independent cases
by re-slicing a single experiment. Splitting on a *pre-treatment* trait would preserve the clean
comparison — but Cookie Cats records **no** pre-treatment trait (only an ID, the arm, and
post-treatment behavior/outcomes), so no honest within-experiment split exists. Splitting *randomly*
is valid but hollow: every random slice estimates the *same* tiny effect, so it replicates one bit
of evidence N times rather than producing N independent bits — a split a sophisticated reviewer would
rightly reject. **The honest unit of evidence is a whole experiment.** Cookie Cats is therefore
**case #1 of a directional-accuracy portfolio — and it is a correct one.** Certifying a directional
claim requires assembling ~8 *different* real product-change experiments, each contributing one clean
whole-population bit. That portfolio — not any single dataset — is what a sellable in-scope accuracy
claim will be built on.

---

## 7. Benchmark 4 — the product-change directional portfolio (the first *certified* in-scope test)

Cookie Cats gave one correct but uncertifiable bit. Benchmark 4 is the program's first
**certified** in-scope external directional test: a portfolio of **8 different real
product-change A/B experiments**, each contributing one clean whole-population directional
bit, run blinded through the real simulation engine and scored only on **direction** (did the
sim pick the real winner?). The set is deliberately **balanced** (5/8 control-won) and
**counter-intuitive** — a prettier redesign that lost, fewer form fields that lost, a
skip-day valve that *raised* return, the simplest of six widgets that won where only 3/21
experts guessed it — so a sim that merely parrots product-design priors gets several signs
wrong. Eight cases is exactly the null-integrity certificate's floor, so the portfolio
clears it with genuinely independent bits. Pre-registered before the run (SHA-256
`17478e06…fdb05d2b4`).

**The headline result.** Direction accuracy **0.25 (2/8)**, with a **PASSING** null-integrity
certificate (not VOID, not underpowered, 0 dropped). rank-ρ 0.0 (p=0.59). That is **below
chance (0.5) and below the human-expert baseline (~2.3/8 = 0.29).** This is the first
certified in-scope external directional measurement — and it is an **honest negative**: the
simulator does not, today, beat chance or expert intuition at calling real product-change
winners. It is not the sellable in-scope positive.

**The diagnosis (this is the valuable part).** The misses are not random — they are
systematic. Reconstructing each prediction from the per-case sign agreement:

| case | real winner | sim predicted | ✓/✗ |
|---|---|---|---|
| cookiecats_gate_move | control | treatment | ✗ |
| duolingo_weekend_amulet | treatment | control | ✗ |
| msn_realestate_widget | treatment | treatment | ✓ |
| office_online_redesign | control | treatment | ✗ |
| msn_homepage_extra_offers | control | treatment | ✗ |
| tinkoff_defer_passport | treatment | treatment | ✓ |
| cxl_form_fields_9_to_6 | control | treatment | ✗ |
| multistep_form_3_vs_6 | control | treatment | ✗ |

The sim predicted **"treatment wins" on 7 of 8 cases.** It got **all five control-won
counter-intuitive cases wrong** and scored only on the two treatment-won cases where the
change genuinely won. (The one case it called "control" — Duolingo — was treatment-won, so
that was wrong too.) The behaviour is directionally near-degenerate toward *"the proposed
change wins"* — in fact slightly **worse** than a naive "always-treatment" rule (which would
score 3/8 on this set). This is the exact priors-echoing failure mode the balanced
counter-intuitive set was curated to expose.

**This is the mirror image of the Hillstrom ad-aversion bias, and that symmetry is the real
finding.** On a marketing *nudge*, the sim predicts the treatment **harms** (anti-change); on
a product *change*, it predicts the treatment **wins** (pro-change). The framing flips the
sign of the prior, and the sim echoes whichever prior the framing evokes — rather than
reasoning about the deliberative trade-off underneath. Same root cause as §4/§5.1:
introspective elicitation on a blinded single-state view returns the salient prior of the
framing, not a genuine valuation.

**One more registered caveat fired.** Cookie Cats scored *wrong* here under the portfolio's
generic "conversion" elicitation, even though it scored *right* in §6's retention-specific
pilot. A single generic-conversion act under-fits a case whose real mechanism is a
delayed-return / retention effect — the pre-registered fidelity risk, realized. Per-metric
(and per-domain) elicitation is a documented follow-up.

**The held-out probe seals the diagnosis: reciting, not reasoning.** Two famous results were
kept *out* of the certified set as a contamination check — with a pre-registered rule: if the
sim aces the famous cases but flunks the obscure ones, it is reciting, not reasoning. That is
exactly what happened. The sim scored **2/2 (100%)** on the famous cases (Netflix's
browse-vs-wall, Highrise's simple page) while scoring **2/8 (and 0/5 on the obscure
control-won cases)** on the certified set. The decisive tell is Netflix: the real winner is
the *control* (the registration wall won, even though 46% of users *said* they wanted to
browse) — and the sim called control correctly there, **against its own pro-change bias.** The
only good explanation for it abandoning that strong prior on the single most-famous case is
that it *recited* the textbook result. (Highrise is consistent with both memory and the
pro-change prior, so it is ambiguous on its own; Netflix is the smoking gun.) The complete
picture: the simulator **pattern-matches** — it falls back on the framing's prior when a case
is obscure, and on a memorized answer when a case is famous. Neither is the deliberative
reasoning the product claims, and this is precisely why "just ask an LLM which variant wins"
is an invalid measurement and why the obscure, balanced portfolio is the honest test. (The
probe is reported as suggestive only — at n=2 it is VOID by the same certification floor that
the scored set clears.) As a robustness note, the scored 8 cases reproduced *identically* on
the re-run, so the 0.25 is deterministic, not sampling noise.

**Integrity follow-up (a leak we found in our own data, and fixed).** A post-run read-only
audit of the harness confirmed the *engine* renders both arms symmetrically — but found that
the authored case *narratives* did not: the treatment side was often written in more
benefit-laden language than the control ("more appealing", "preserves the streak",
"simplest"), and one case (the MSN real-estate widget) literally carried the phrase **"winner
of 6 variants"** in its treatment text — a direct outcome leak the blindness test missed
because it checked for "won", not "winner". Since the adapter passes these strings verbatim
into the blinded stimulus, that asymmetry reached the model, and one of the two "correct"
calls (MSN real-estate) is therefore contaminated. We have normalized all eight cases to
neutral, parallel, mechanic-only descriptions (evaluative adjectives and outcome hints
stripped from *both* arms, no valence flip toward control, factual mechanic preserved),
sealed a v2 pre-registration (SHA-256 `9f796b55…`, pinning the normalized cases by hash) with
a registered prediction *before* re-running — the audit's expectation is that direction
accuracy stays near chance while the 7/8 treatment-rate falls toward ~5/8, because the cxl
case (whose treatment copy carried a *negative* signal yet was still predicted to win) already
shows the pro-change prior is structural, not just copy-deep. The clean re-run is the decisive
test that separates copy-valence artifact from genuine prior; its result is reported next.

**The clean re-run overturned the artifact — and reopened the in-scope-positive question.**
With the narratives normalized (and *nothing else* changed), direction accuracy went from
**0.25 (2/8) to 0.75 (6/8)**, null-cert PASSED, rank-ρ 0.51 (p=0.13). Four cases flipped
wrong→right (cookiecats, Duolingo, office-online, MSN-homepage); the two that stayed wrong are
exactly the "simplification wins" cases (fewer form fields, fewer steps). So the v1 "pro-change
bias" was **substantially a measurement artifact of our own benchmark's asymmetric copy**, not a
genuine intrinsic prior — the cleanest proof being cookiecats, whose only v1/v2 difference was a
parenthetical pro-treatment gloss, and whose removal flipped the prediction to correct. This
also *refutes our own v2 pre-registered prediction* (which expected the clean score to stay near
chance) — in the flattering direction, which is precisely when to be most skeptical, so we ran
an **independent adversarial audit** of the rewrites before trusting the number. Its verdict:
three of the four flips are clean (the punitive-vs-lenient or clutter framing is *intrinsic to
the real mechanic*, not injected), and the heterogeneous flip direction (3 toward control, 1
toward treatment) plus the two surviving misses rule out a contaminating uniform pro-control
swing. The one soft spot is office-online, where "the price is not shown" — though factual —
becomes the single most salient cue on a Buy page; a strict reading discounts that case, giving
a **conservative 5/8**. Both 5/8 and 6/8 sit far above the ~2.3/8 expert baseline. Two honest
limits remain before this is a *certified* positive rather than a strong signal: at n=8, 6/8 is
not significant against pure chance (one-sided binomial p≈0.15 — the decisive comparison is vs
the human baseline, not vs a coin), and the portfolio needs *more cases* for power. The
headline lesson is a method win: the campaign's own discipline (audit → found a self-inflicted
leak → re-prereg → clean re-run → adversarial check) caught us about to publish "the sim has an
intrinsic pro-change bias" when the real cause was a benchmark-construction defect.

**The confirmation run, and the honest number.** We then re-ran with the auditor's stricter,
de-salienced office-online wording (pre-registered: if it stays control the flip is earned, if it
reverts it was salience). It **reverted to treatment** — so the office-online v2 hit was carried
by the price cue, and the honest, audited clean score is **5/8 (0.625)**, rank-ρ 0.57 (p=0.12).
The full trajectory: v1 2/8 (valence-leak false negative) → v2 6/8 (clean but office-online
salience-inflated) → **v2.1 5/8 (conservative, de-salienced)**. A sharp caveat must lead any
external framing: because the set is 5/8 control-won, the trivial **"always predict control"
baseline also scores 5/8** — so the sim's *headline* direction-accuracy does not beat the
strongest constant baseline here. The sim is not constant (it predicted treatment 6×, control 2×):
it correctly called **all three** treatment-wins — which an always-control rule gets wrong — plus
two of five control-wins (the Cookie Cats gate-timing and the MSN clutter cases), and the
discriminating signal shows in rank-ρ. Its three misses are all "the streamlined/redesigned
variant wins" cases (office-online, fewer form fields, fewer steps) — a narrower, nameable
residual prior, not v1's blanket pro-change. Honest and bounded: 5/8 clears the human-expert
baseline (~2.3/8) and always-treatment (3/8) and the engine genuinely discriminates direction (it
nails every real treatment-win), but on this control-heavy set the headline ties always-control
and nothing is significant against chance at n=8. A real, encouraging in-scope signal — not a
certified positive. The path to certification is a **larger, balanced (~50/50) portfolio**, where
the headline must beat 0.5 rather than an inflated constant baseline and n clears significance.

> **⚠️ v3 EXPANSION RESULT (2026-06-17) — the v2.1 signal does NOT generalize; standing tempered.**
> We did the larger-portfolio step: +7 audited tier-1 real product-change A/Bs (independent
> adversarial valence audit; 3 cases blocked and fixed with the auditor's own rewrites; a
> social-proof-nudge case excluded), to **n=15** (prereg `3c0c8057…`, cases `b88af0a9…`, sealed
> before the result). **Result: direction_accuracy 0.467 (7/15) — below chance, below the
> always-treatment baseline (0.60).** The original 8 reproduced exactly (5/8), but the **7 new
> cases scored 2/7 (below chance)**, and per-class accuracy was roughly equal (control 3/6,
> treatment 4/9 — no pro-change tilt). Our pre-registered prediction (≈0.70, treatment-tilted)
> was wrong in the un-flattering direction. **Honest reading: the encouraging v2.1 5/8 was
> substantially the favorable composition of those 8 cases; on a broader, harder sample the sim
> is at chance.** Two non-exclusive causes: (1) several new cases are subtle/aesthetic *micro*
> changes (signup colour, mail new-tab, price-range display) — closer to sub-deliberative nudges
> (the §5.1-certified weak class); the only two it got right (Amazon offer relocation, Etsy
> pagination-vs-infinite-scroll) are the substantive/behavioural ones; (2) audit-neutralised
> micro-cases may render the one-sentence blinded stimulus *inert* (the neutralisation that kills
> a leak can kill the signal). **Revised, defensible claim: the engine reads SUBSTANTIVE
> deliberative product-change direction better than chance/experts on favourable cases, but this
> does NOT generalise to subtle/aesthetic micro-changes or marketing nudges — a finer scope
> boundary than §7 first stated.** Next: report the deliberative vs micro subsets separately, and
> either render subtle cases more richly (arm-symmetric) or scope them out. Artifact:
> `portfolio_results_v3.txt`.
>
> **↳ SUBSET FOLLOW-UP (2026-06-17, EXPLORATORY — the dilution is confirmed).** We did the
> deliberative-vs-micro split *without cherry-picking*: an **independent agent, blind to the sim's
> per-case correctness**, classified all 15 cases by stimulus type (substantive-deliberative=A vs
> subtle/micro/aesthetic=B) under a fixed a-priori rubric; that classification was **sealed**
> (`v3_blind_classification.json`, canonical SHA `feb22099…`) *before* any subset number was
> computed. Result: **Class A (substantive, n=10) = 7/10 = 0.70; Class B (micro/aesthetic, n=5) =
> 0/5 = 0.00.** So the aggregate 0.467 is substantially **dilution** — adding 5 micro cases the sim
> has no purchase on dragged down a substantive-class 0.70, and the two *new* substantive cases
> (Amazon, Etsy) both scored correct. **But three honest brakes:** (i) Class A's 0.70 is
> **underpowered — not significant** (one-sided binomial p=0.17 vs chance, p=0.38 vs the 0.60
> always-control baseline; n=10 can't clear p<0.05). (ii) A **residual pro-change tilt persists
> even within Class A**: treatment-class 4/4 but control-class 3/6 — all three misses are the same
> "*simplification / fewer fields / fewer steps wins*" failure (cxl 9→6, multistep 6→3,
> office_online declutter); this localises the #221 lever to control-won simplification cases.
> (iii) Class B's 0/5 is **confounded** (all 5 micro cases were treatment-won, so 0/5 just means
> the sim defaulted to no-change on every thin stimulus) — uninformative-leaning-negative, not a
> clean anti-signal. **Status: EXPLORATORY / hypothesis-generating** (splitting on this dimension
> after seeing the null is itself a post-hoc choice; the blind+sealed classification only guards
> the *split*, not the *decision to split*). The confirmatory test is a **new pre-registered
> class-A-only powered run** (n≥18–20, deliberately enriched with control-won simplification cases
> to force balanced discrimination; micro/aesthetic scoped out as out-of-format). If Class A holds
> ≥0.70 with control-class ≥~0.5 → first genuinely balanced, significant, **narrow** in-scope
> positive. Artifacts: `portfolio_v3_subset_analysis.txt`, `v3_blind_classification.json(+.sha256)`,
> `subset_score.py`.
>
> **❌ CONFIRMATORY RESULT (2026-06-17) — the narrow positive is REFUTED on fresh data.** We ran
> the confirmatory test the subset analysis demanded: **14 FRESH substantive-deliberative cases**
> (none in v2.1/v3), deliberately **control-heavy (8 control-won / 6 treatment-won)** and enriched
> with control-won "the change backfired" field experiments (Ascarza proactive-churn, Kanuri-
> Andrews recovery-incentive, Algesheimer eBay-community, Lambrecht-Tucker retargeting, etc.).
> Integrity: an **independent blind auditor guessed winners 6/14 = 0.43 (below chance) → no leak**,
> and itself made the same error on these cases (independently confirming they're genuinely hard);
> pre-registration `f9aa80e6` + cases content-SHA `4ef9494f` **sealed before the run**; primary
> endpoint pre-declared as **control-class accuracy**. **Result: dir_acc 0.286 (4/14) — BELOW
> chance, BELOW both constant baselines (always-control 0.571, always-treatment 0.429), ~tied
> with the Kohavi expert floor; rank-ρ −0.18 (p=0.76); cert passed, 0 dropped.** Per-class:
> **control-class 2/8 = 0.25** (my pre-registered prediction was 2-3/8 — **correct, un-flattering**)
> and **treatment-class 2/6 = 0.33** (I predicted ~5-6/6 — **wrong; both classes failed**).
> **The v3 substantive-class 0.70 did NOT replicate** → it was in-sample favorable composition,
> not a real narrow skill. **Sharper diagnostic:** the sim predicted the **"more/richer/higher"
> arm in 12/14 cases** regardless of control/treatment label — so the product-framing bias is
> **more-is-better, NOT pro-change** (when the treatment was a *reduction*, the sim backed the
> richer control). Magnitudes are tiny (|Δ|≤0.022) — a faint richer-arm lean over a near-flat
> signal. **This refutes the #221 "de-bias the pro-change prior" lever** (no clean tilt to remove)
> and means the honest standing on the in-scope positive is now: **there is none** — on fresh,
> balanced, audited, pre-registered cases the engine is at/below chance. Artifacts:
> `portfolio_confirm_result.txt`, `PREREG_CLASS_A_CONFIRM.json(+.sha256)`,
> `PORTFOLIO_CASES_CONFIRM.json`, `CONFIRM_AUDIT_RESULT.md`, `confirm_ckpt.jsonl`.

**What it means for the program.** The benchmark did its job: it converted "is the sim
accurate on in-scope product changes?" into a *certified, reproducible* engineering target
with a **named, fixable** bias (pro-change direction) plus a named fidelity gap
(generic-conversion vs retention). That is exactly the honest-null foundation §5 commits to —
a rigorous certified null plus a diagnosed mechanism is a stronger trust signal to a
sophisticated buyer than a cherry-picked win. No in-scope directional positive is claimable
until a fix moves direction accuracy off chance on *this* pre-registered set. The next levers
are (a) de-biasing the pro-change prior at outcome elicitation (#221, analogous to the
ad-aversion work), (b) per-metric elicitation so retention-shaped cases aren't forced through
a generic conversion act (#222), and (c) the held-out memorization probe (Netflix browse +
Highrise) to confirm priors-echoing rather than reciting.

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
- 2026-06-17: **Model comparison (Claude Sonnet 4.6 vs Groq baseline) — pre-registered
  (`147236f1…`), gate OFF, both outcomes; COMPLETE.** Direction accuracy **0.0 on both
  conversion and visit** under Sonnet — *identical* to the Groq baseline (rank-ρ −0.32 / −0.33,
  both at chance). A frontier model is exactly as backwards. **Conclusion: the ad-aversion bias
  is model-independent / intrinsic to introspective elicitation** — no production model swap
  fixes it. This closes the pre-registered both-outcome model-comparison design and hardens the
  §5.1 scope boundary. Next lever: stop probing the out-of-scope perimeter (marketing nudges) and
  land the first *positive* on the in-scope deliberative core — external real-world product-change
  A/B (Cookie Cats lead) + the internal Streamly known-good/known-bad validation.
- 2026-06-17: **Pivot to the in-scope deliberative core — Cookie Cats harness built + merged
  (PR #348).** Every certified result to date is a null/inversion on the *out-of-scope* nudge
  class; the product's actual job (deliberative reactions to a product change) has no external
  positive yet. Cookie Cats is the best obtainable external real-world product-change A/B (mobile
  game: first progress gate moved level 30→40, ~90k per-user rows, counter-intuitive verified
  winner — the *earlier* gate wins on 7-day retention). The harness mirrors Hillstrom (gated data
  fetcher, derived GMM engagement pack, `benchmark-cookiecats` CLI, 56 tests). **Honest scoping
  caveat baked into the pre-registration:** the dataset carries no pre-treatment covariates, so the
  only clean *causal* endpoint is the single whole-population A/B (one directional bit — does the
  sim predict the counter-intuitive winner?); engagement-octile strata are descriptive, not causal
  (they condition on a post-treatment mediator). And the gate-timing effect is itself partly
  *behavioral* (forced-break psychology), so a wrong sign here would refine the deliberative-vs-
  behavioral boundary rather than simply refute in-scope capability. The run is the next step,
  pending a deliberate go/no-go (it spends API budget on the shared prod box).
- 2026-06-17: **Cookie Cats Groq pilot — RAN (prereg `fd8cc62a…`, committed before result); §6 added.**
  The first IN-SCOPE external product-change test. Clean causal whole-population endpoint:
  **direction accuracy 1.0 on retention_7 — the sim correctly predicted the counter-intuitive winner
  (later gate hurts retention)** — but VOID (n=1, uncertifiable). The certifiable 8-octile endpoints
  are at chance, but they condition on a post-treatment mediator (confounded, pre-registered as
  descriptive). Lesson: independent cases can't be manufactured from one experiment (no pre-treatment
  covariate to split on; random splits are hollow). **Cookie Cats = case #1 of a directional-accuracy
  portfolio, and it's correct.** Next: assemble ~8 different real product-change A/Bs to certify a
  directional claim across whole-experiment cases.
- 2026-06-17: **Product-change directional PORTFOLIO — the first *certified* in-scope test; §7 added
  (prereg `17478e06…fdb05d2b4`, committed before result).** 8 balanced (5/8 control-won),
  counter-intuitive real product-change A/Bs, blinded through the engine, direction-only scored.
  **Direction accuracy 0.25 (2/8), null-integrity certificate PASSED** (not VOID) — below chance
  (0.5) and below the Kohavi expert baseline (~2.3/8). **Honest negative.** Diagnosis: the sim
  predicted "treatment wins" on 7/8 cases (all 5 control-won counter-intuitive cases wrong) — a
  **pro-change direction bias**, the *mirror image* of the Hillstrom ad-aversion bias (framing flips
  the prior; the sim echoes whichever prior the framing evokes). Cookie Cats scored wrong here under
  generic-conversion elicitation vs right in §6's retention-specific pilot (registered fidelity risk,
  realized). Result artifact `portfolio-benchmark/portfolio_results.txt`. Next levers: de-bias the
  pro-change prior at elicitation (#221), per-metric elicitation (#222), held-out memorization probe.
- 2026-06-17: **Held-out memorization probe + scored re-run — RECITING-NOT-REASONING confirmed.**
  The pre-registered contamination check ran (`--include-heldout`): the sim scored **2/2 (100%)** on
  the two famous cases (Netflix browse-vs-wall, Highrise simple page) while scoring **2/8 (0/5 on
  obscure control-won)** on the certified set — the exact "aces famous, flunks obscure" red flag.
  Decisive tell: on Netflix (real winner = control) the sim called control correctly, *against* its
  own pro-change bias — only explicable as recitation of the textbook result. Conclusion: the sim
  **pattern-matches** (framing-prior when obscure, memory when famous), not deliberative reasoning —
  validating why "ask an LLM which wins" is invalid. The scored 8 reproduced identically (dir_acc
  0.25 deterministic). §7 updated.
- 2026-06-17: **Portfolio integrity reversal — the v1 negative was OUR OWN benchmark's valence
  leak, not a model bias.** Adapter audit: engine renders arms symmetrically but the authored
  narratives carried arm-asymmetric valence + an outcome leak ("winner of 6 variants"). Normalized
  all 8 to neutral/parallel/mechanic-only copy, sealed v2 prereg (`9f796b55…`) before re-run:
  **dir_acc 0.25 → 0.75 (6/8)**, cert PASSED. Independent adversarial audit cleared 3/4 flips,
  flagged office-online (price-salience); the pre-registered stricter-rewrite confirmation
  (`390c5606…`) reverted office-online → honest **5/8 (0.625)**, rank-ρ 0.57 (p=0.12). Lead caveat:
  on this 5/8-control set the always-control baseline also scores 5/8, so the headline ties it —
  the sim's edge is nailing all 3 treatment-wins + positive rank-ρ; the 3 misses are
  "simplification/redesign wins" priors. Beats the human baseline (~2.3/8), not significant vs
  chance at n=8. **A real, encouraging in-scope signal — not a certified positive.** Method win:
  the audit→re-prereg→clean-run→adversarial-check discipline caught a self-inflicted false negative.
  Opened PR #353 (valence-symmetry blindness-test guard). §7 updated. Next: larger, balanced
  portfolio, re-run for power.
- 2026-06-17: **Hillstrom "intrinsic ad-aversion" put UNDER RE-EXAMINATION — same audit lens, a
  real harness confound found.** Applying the portfolio's stimulus-construction lens to Hillstrom:
  the elicitation `decision_point` ("the customer is reading the promotional e-mail in their
  inbox", cli.py) is fed to BOTH arms incl. the No-E-Mail control → control agent told it's reading
  the email the treatment adds → inflates control, drives treatment−control delta to ≈0/negative
  (matches the observed −0.01..−0.03). The model-comparison "intrinsic/model-independent" claim
  does NOT survive: both models ran on the same confounded harness (shared stimulus bug ≠ model
  property). §4 + §5.1 marked PROVISIONAL. Decisive next experiment: arm-correct the decision_point
  (Fix 1, isolating), pre-register, re-run the 8 cases on both outcomes (Groq). If dir_acc moves
  off 0.0 → §4/§5.1 retracted (a second self-inflicted false negative); if it stays 0.0 with control
  de-contaminated → intrinsic genuinely survives. (Caveat: Hillstrom's real effect is small/partly
  sub-deliberative, so a true null can co-exist with the confound — less certain to flip than the
  portfolio's large deliberative effects.)
- 2026-06-17: **Fix-1 de-confound RE-RUN DONE → ad-aversion CONFIRMED, not retracted.** PR #361
  arm-corrected the decision_point (→ "looking at their inbox", email-free; guarded by a regression
  test) + deployed to the box. Pre-registered single-variable clean re-run (PREREG_FIX1 SHA
  `f2947b39…`, committed before result; Groq, same 8 cases, both outcomes). **dir_acc stayed 0.0 on
  BOTH conversion and visit** (cert PASSED, not VOID; rank_ρ conv −0.16 / visit +0.19, chance). The
  pre-registered prediction (dir_acc moves off 0.0) was wrong in the UN-flattering direction → §4
  banner + §5.1 caveat changed from PROVISIONAL to CONFIRMED/strengthened: the confound was real and
  fixed but NOT load-bearing for the sign inversion; the ad-aversion is intrinsic, not a rendering
  artifact. "Model-independent" narrowed: re-established for Groq on the clean harness; Sonnet clean
  re-run optional. Contrast §7 portfolio, where de-leaking DID flip the score (that one was an
  artifact) — the audit→fix→prereg→clean-rerun discipline distinguished the two. Artifact:
  fix1_deconfound_result.txt.
</content>
