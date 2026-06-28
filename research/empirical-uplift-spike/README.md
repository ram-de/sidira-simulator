# Empirical-uplift spike — a different angle on engine accuracy

**Question.** Sidira's engine predicts product-change outcomes by *imagining* agent
reactions with an LLM. A completely different route: for a **feature-expressible**
change, *learn* the effect empirically from the customer's own behavioral logs with
a causal/uplift model — no LLM, no real-money panel. Does it work, and where does it
break?

**Method.** A self-contained Streamly-like synthetic feature store (2,500 users, 6
segments) with a **known, by-construction** heterogeneous treatment effect, so there
is ground truth to score against. The change under test ("autoplay-next on the home
feed") helps casual users but hurts power users; because power users have a high
retention base, the **true net 30-day-retention effect is negative — the opposite of
the obvious "more engagement = good" prior.** Assignment is observational and
confounded (autoplay rolled out to already-engaged users first), like a real log.

Predictors raced against the oracle ATE:
- **more-is-better prior** — fixed `+` sign; stands in for the LLM's uncontrolled prior.
- **naive diff-in-means** — the raw correlation (confounded).
- **IPW** + **T-learner / uplift** — propensity- and covariate-adjusted causal ML.

## Results

| Scenario | True ATE | prior (LLM stand-in) | naive diff-in-means | IPW | T-learner / uplift |
|---|---|---|---|---|---|
| **S1** feature-expressible, driver in the store | **−5.5pp** | +4.0pp ❌ | +0.9pp ❌ | **−4.8pp ✅** | **−3.9pp ✅** |
| **S2** real driver *not* in the store (unobserved confounder) | −3.2pp | +4.0pp ❌ | +3.7pp ❌ | +4.0pp ❌ | +4.2pp ❌ |

- **S1 — the win.** Where the change is feature-expressible and the driver is in the
  data, causal ML recovers the correct sign and near-exact magnitude, while *both* the
  obvious prior and the naive correlation get the sign **wrong**. A slice Sidira can
  predict **provably accurately, with zero LLM calls.**
- **S2 — the honest bound.** When the real driver isn't a column, *every* empirical
  method flips to the wrong sign. No ML rescues a missing variable. **This is where the
  LLM engine earns its keep** — it brings outside-world priors the feature store lacks.

## So what

Points to a **router, not a replacement**: detect feature-expressibility + sufficient
support → empirical engine (high-confidence, sellable); else → LLM engine (broad,
flagged). Carves out a defensible accurate slice now instead of betting on one paradigm.

The same router is the keystone of the **council-of-priors** idea (which agent/prior to
trust per hypothesis) — one classifier unlocks both routes.

## Run

```
/opt/homebrew/bin/python3.11 research/empirical-uplift-spike/uplift_spike.py
```

Deterministic (seed 20260627). Deps: numpy, scikit-learn.

## The baseline the council aimed to beat

`sessions/agent-behavior-spec/portfolio-benchmark/portfolio_comparative_result.json`:
the *comparative-forecaster* (NOT the persona-sim engine — see the retraction below)
scores **0.50 directional accuracy** (7/14) — chance — and its errors are *systematic*:
on high-counter-intuitive cases it predicts `treatment` almost every time the real winner
was `control` (ascarza, kanuri, algesheimer, lambrecht, anderson — all MISS). That hidden
**"the new thing wins" prior** is what the council tried to correct by making the prior
explicit and plural with a router to decide when to distrust it. Target: **0.50**.

## Phase C result — council-of-priors: a clean NEGATIVE

Ran live (Groq llama-3.3-70b, blinded, temperature 0). Two case sets:

**Same 14 cases the engine scored 0.50 on** (`PORTFOLIO_CASES_CONFIRM.json`, apples-to-apples):

| predictor | directional acc (n=14) |
|---|---|
| naive single call | **0.64** (9/14) |
| council, unrouted (equal-weight 4 priors) | 0.50 (7/14) |
| council, routed (router-weighted) | 0.57 (8/14) |
| comparative-forecaster (prior baseline, sonnet) | 0.50 |
| per-arm persona-roleplay (the simulation) | 0.286 |

**The council mechanism does not work.** Adding explicit prior-members (contrarian,
base-rate-skeptic) *lowered* accuracy below a single naive call — they flip correct
answers as often as wrong ones (diversity ≠ accuracy, measured). The router helps over
the unrouted council (0.57 > 0.50) but cannot recover the naive baseline, and it
under-fires `COUNTER_INTUITIVE` exactly on the cases that needed it.

On the **other 8 product cases** (`PORTFOLIO_CASES.json`) all three variants tied at
**0.75** — but that set is contamination-prone (famous case studies) and has no matched
engine baseline, so it proves nothing on its own.

### A "naive beats the engine" lead — investigated, then RETRACTED

First read: the naive call (0.64) seemed to beat "the engine" (0.50). Checking
`portfolio_comparative.py` killed it. The 0.50 baseline is **not** the persona-sim engine
— it is the *comparative-forecaster* (show one expert both versions + the metric, ask
which wins; k=4) on **claude-sonnet-4-6**, essentially the same method as my naive call.
Re-running it on **my** model (llama-3.3-70b) scores **0.500 again**
(`comparative_llama_result.json`) — nearly case-for-case identical. So the 0.64-vs-0.50
gap was **model confound + n=14 noise** (a 2-case difference: ascarza, office_help), not
a method win. *There is no naive-beats-engine effect.*

What the baselines actually show (same 14 cases):

| method | dir. acc | note |
|---|---|---|
| per-arm persona-roleplay (the "simulation") | **0.286** | below chance — more-is-better bias (known, #342) |
| comparative narrative call (sonnet, k=4) | 0.50 | at chance |
| comparative narrative call (llama, k=4) | 0.50 | at chance — model confound killed |
| my naive call (llama, k=1) | 0.64 | 9/14, p≈0.4 vs chance — NOT significant |
| council routed / unrouted | 0.57 / 0.50 | worse than naive |

**Robust, sobering conclusion:** on this set, *no* LLM forecasting method — roleplay,
comparative, council, or naive — reliably beats chance (0.50) at calling the directional
winner. The simulation machinery is actively *worse* than a one-line comparison (0.286 vs
0.50), as the team already found in #342. Consistent with the campaign's other nulls
(Upworthy, Hillstrom).

**Verdict:** council-of-priors rejected; the naive-beats-engine lead retracted as noise.
The one mechanism that genuinely worked is the **empirical/causal route (Phase A)** — it
survives precisely because it learns from *data*, not narratives. That is the angle worth
pursuing.

## Phase B (real data) — Cookie Cats, 90,189 real players

The synthetic spike, redone on **real human A/B outcomes** (`realdata_uplift.py`,
design sealed in `PREREG_REALDATA.json`, sha256 `027aa4a8…`). True effect is the
established RCT: gate_30 (control) wins (retention_7 ATE −0.82pp). We then INJECT
selection bias on engagement (treatment arm pulled to 86.7 avg rounds vs control's
16.8 — like a change rolled out to power users first) and test recovery:

| retention_7 (true −0.82pp, control) | estimate | sign |
|---|---|---|
| naive diff-in-means (confounded) | **+22.01pp** | **WRONG** — confounding makes the loser look like a huge winner |
| T-learner standardization (causal) | −0.81pp | **RIGHT** (recovers −0.82pp almost exactly) |
| IPW selection-corrected (causal) | −0.61pp | **RIGHT** |

(retention_1 same pattern: naive +34.4pp WRONG; causal −0.40 / −0.08pp RIGHT.) Exactly
as pre-registered. The empirical route's S1 win is now demonstrated on real data at scale.

**Honest caveats (registered):** the confounding is *injected* (real outcomes + real
covariate, constructed selection), and `sum_gamerounds` is plausibly *post-treatment* —
so this is a selection-bias-correction demo, not a clean pre-treatment-confounder claim.
Recovery is near-exact partly because we adjust for the *same* variable we selected on
(the favorable case); the unobserved-confounder case (spike S2) still defeats it. Next:
**Hillstrom** (recency/history/channel measured *before* the email) for the clean
pre-treatment version. Power: 90k users but ONE A/B decision — depth, not breadth.

## Phase B (real data) — Hillstrom, 42,693 customers (clean pre-treatment covariates)

The methodologically tight version (`realdata_hillstrom.py`, sealed in
`PREREG_HILLSTROM.json`, sha256 `ffcb13d9…`). Womens E-Mail vs No E-Mail; true RCT =
email lifts visits **+4.52pp** (treatment wins — opposite polarity to Cookie Cats). All 8
covariates are measured *before* the email, so adjusting for them has no mediator caveat.
Injected selection on baseline spend (email arm pulled to $123 avg history vs control's
$358).

| visit (true +4.52pp, treatment) | estimate | sign |
|---|---|---|
| naive diff-in-means (confounded) | +2.12pp | RIGHT (but halved) |
| causal, adjust WITH confounder — T-learner / IPW | **+4.97 / +4.88pp** | **RIGHT** (recovers +4.52) |
| causal, WITHOUT confounder (S2 attempt) — T-learner / IPW | +3.60 / +4.42pp | RIGHT |

**Primary result — confirmed:** causal adjustment recovers the true effect on clean
pre-treatment covariates → removes the one caveat Cookie Cats carried.

**Two pre-registered sub-predictions REFUTED (reported honestly, not re-tuned):**
1. Naive did *not* flip sign — only attenuated (+2.12 vs +4.52). The true effect is too
   large for the injected confounding to overpower. (Cookie Cats flipped because its true
   effect is tiny, −0.82pp.)
2. The "unobserved confounder" ablation did *not* fail — dropping `history` still recovered
   (+3.60pp), because the **other pre-treatment covariates proxy spend**. "Unobserved" only
   bites with no observed proxy; Hillstrom's correlated covariates don't provide that.
   Cookie Cats' synthetic S2 remains the clean bound illustration.

Net: the empirical route's core mechanism holds on two real datasets of opposite polarity;
its *dramatic* failure modes are condition-specific, now characterized.

## Status / next

- [x] **Phase A** — synthetic-fixture proof (`uplift_spike.py`). Empirical route beats
      the obvious prior on the feature-expressible slice (S1); honest bound where an
      unobserved confounder defeats it (S2).
- [x] **Phase B (real data)** — Cookie Cats 90k: causal adjustment recovers the true
      counter-intuitive sign (−0.81pp vs −0.82pp truth) where naive averaging is
      catastrophically wrong (+22pp). Pre-registered + sealed.
- [x] **Phase C built** — `council_benchmark.py`: 4 explicit-prior members
      (naive / more-is-better / contrarian / base-rate-skeptic) + a regime router, with a
      **pre-registered** consolidation rule, blindness (members see only
      domain/control/treatment/metric), and 3 ablations (naive-only / council-unrouted /
      council-routed). Dry-run verified. **Needs an LLM key to execute** — `--dry-run`
      prints prompts without spend.
- [x] **LLM head-to-head** — ran live (Groq llama-3.3-70b). Council rejected; comparative
      vs roleplay vs naive all at/below chance; naive-beats-engine lead retracted (see above).
- [x] **Hillstrom** — clean pre-treatment covariates: causal adjustment recovers the true
      +4.52pp email lift (T-learner +4.97 / IPW +4.88). Two staged failure-modes (naive
      flip, S2 ablation) pre-registered and REFUTED — reported honestly, not re-tuned.
- [ ] **Upworthy LLM / no-persona generalization** — confirm "no-persona ≥ persona-roleplay"
      beyond the 14-case set (less contamination than famous Cookie Cats).
- [ ] **Productize the survivor** — the feature-expressibility router: data-supported,
      feature-expressible change → empirical engine; else → LLM. Socialize + scope a build.

> Caveat: Phase A S1/S2 are constructed demonstrations; Phase B uses real outcomes but
> *injected* confounding (favorable case — adjusts for the selected-on variable). The LLM
> results are n≤14, directional-only, contamination-prone — signals, not validations.
