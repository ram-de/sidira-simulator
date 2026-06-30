# Research Charter — A Theory of Estimability for Behavioral Interventions

*Drafted 2026-06-28 from a parallel literature-terrain + charter + adversary workflow
(`nobel-research-charter`, 8 agents). This document deliberately includes its own hostile
review, because the review is the most important result.*

## The question (reframed away from the trap)

> For a specific, **not-yet-run** product/policy change, can we build a **calibrated,
> externally-anchored test** that decides — *before* running it — whether the **direction**
> of its effect is estimable-in-advance from the available data, emitting a directional call
> where it is and **abstaining with a known error rate** where it is not?

This is **not** "build a perfect user simulator." That ambition runs straight into the
**Fragile Families Challenge** (Salganik et al., PNAS 2020): 160 teams, 12,942 predictors,
the full ML arsenal — and the best model barely beat a 4-variable regression, with diverse
methods *converging* to the same low ceiling. The lesson, now 6 years old: for rich human
outcomes the limit is the **data/problem, not the model**. Our own campaign reproduced this
signature exactly (every LLM-narrative method at chance on the 14-case directional benchmark;
complexity *hurts* vs a one-line comparison). So the honest science is not to fight the ceiling
but to **instrument the boundary** of it for the harder, interventional (Pearl rung-2) query.

## The literature spine (what we stand on)

| Strand | Established result | What we borrow |
|---|---|---|
| Predictability ceilings | FFC: diverse methods converge at a low ceiling; data-bound not model-bound | The convergence + simple-baseline-gap *ceiling diagnostic*; Common-Task discipline |
| Causal identification | Back-door/ignorability (Pearl); credible natural-experiment inference (2021 Nobel: Angrist/Imbens/Card) | The formal conditions under which a *sign* is point-identified |
| Negative controls / proximal CI | NCO falsification (Lipsitch 2010); **COCA / proximal causal learning (Miao-Geng-Tchetgen Tchetgen 2018; Shi 2020)** | Our guard is a *special case of the 2010 test*; the 2018 work is the frontier we have **not** yet implemented |
| Structural choice | McFadden RUM / BLP / Lucas invariance (Nobel) | Feature-expressibility = the regime where counterfactuals are valid |
| Calibration / selective pred | Conformal (Vovk); selective risk (El-Yaniv); covariate-shift conformal (Tibshirani 2019) | Risk-coverage curves; the proof that **internal-vote confidence is formally vacuous** (why our M3 failed) |

## The honest contribution claim

For directional predictions about not-yet-run changes, the binding constraint is
**identification, not model capacity** — and this can be made operational and calibrated as a
**router** (certify the knowable, abstain on the rest), not a predictor. We explicitly **concede**:
the ceiling itself is rediscovered (FFC); the guard is Lipsitch's 2010 test; the reframe is
Hofman et al. 2021's "characterize what is predictable." The only candidate-new object is the
**operational per-case routing gate** — and it is not yet earned.

## Falsifiable predictions (pre-registerable)

1. **Convergence-at-chance:** on any directional benchmark with obvious cases removed, no
   LLM-narrative method beats a one-line baseline by a meaningful margin. *(Confirmed, n=14.)*
2. **Slice-gated causal success:** causal/uplift ML recovers the sign above chance *only* where
   the driver is in the per-user features; off-slice it returns to chance. *(Partly confirmed.)*
3. **Coupling-monotone guard power:** guard sensitivity is monotone in NC↔confounder coupling;
   below a threshold it misses >50% of confounded cases. *(iter0 0/3 reproduces.)*
4. **Selective-accuracy lift:** on the retained subset, directional accuracy strictly exceeds
   full-set accuracy (a real risk-coverage curve); the internal-agreement version is flat. *(M3
   confirmed flat/vacuous.)*
5. **Floor transfer:** a synthetic-tuned NC floor holds on a *second, unseen* real RCT.
6. **Proximal recovery (NEW, the live bet):** double-negative-control / COCA recovers the correct
   sign on a non-trivial fraction of cases the single-NC guard currently *abstains* on — expanding
   the estimable slice. This is the one move that is **not** rediscovery.

## The hostile review (kept verbatim in spirit — the gut-check)

A dedicated adversary agent argued the program adds nothing. Its core, and I accept most of it:

- **(a)** We rediscovered the FFC ceiling at 1/300th the sample. Independent rediscovery at n=14
  is not validation of *our method*; it's evidence the benchmark is too small to say anything new.
- **(b)** The guard is the textbook 2010 NCO test; `floor=0.05, ratio=1.5` are two tuned magic
  numbers (cf. VanderWeele-Ding's *derived* E-value). We stopped at *detection* and shipped
  abstention as a design choice when it is a **capability ceiling** — the 2018 proximal work
  *corrects* the bias on cases we discard. And the guard is silent exactly when the confounder is
  novel (the cases that matter).
- **(c)** The synthetic phase-diagram is **circular**: you recover the boundary you encoded. It
  can't surprise or falsify; real interventions are outcome-mechanism shifts, not the covariate
  shifts the generator produces.
- **(d)** It never touches the binding constraint. Conformal/selective guarantees need *hundreds*
  of exchangeable held-out points; we have 14, and an intervention shifts the outcome mechanism,
  voiding vanilla/weighted conformal. The calibrated gate is "calibrated to nothing."
- **(e)** Nothing transfers: synthetic→real (real confounding is unobserved *by definition*),
  slice→LLM (the causal route needs the per-user table the LLM use-case lacks → "econml with a
  refusal message").

**The adversary's one condition for the program to be worth running:**
> *Assemble a corpus of real, run-to-completion product/policy A/Bs with per-user covariates AND
> withheld true directional outcomes — hundreds of exchangeable cases — so the gate's risk-coverage
> curve can be built and shown to hold out-of-sample on REAL interventions where the confounding
> was genuinely unobserved. Build the corpus first, or this is theater.*

## Decision — what we actually do (corpus-first)

The charter and its harshest critic agree. So the program is, in priority order:

1. **CORPUS (the binding constraint).** Determine whether a corpus of hundreds of real
   per-user A/B interventions can be *assembled from public sources* — or whether it must be
   *manufactured* (which is exactly what the Senu made-to-order BenchmarkCase factory is for).
   Either answer is decisive. This is where "run as many agents as long as you want" genuinely
   pays off: it is an exhaustive search + curation problem, not a data-generation impossibility.
2. **PROXIMAL CI (the one non-rediscovery method move).** Implement double-negative-control /
   COCA; pre-register; test on synthetic + the two real RCTs (Hillstrom, Cookie Cats); measure
   whether it recovers sign where the single-NC guard abstains. Deployable the moment the corpus
   grows; rebuts "econml with a refusal message."
3. **PHASE DIAGRAM (characterization, not discovery).** Run it — but framed honestly as a
   *calibration substrate and a map of the silent-failure region C* (confident-and-wrong), not as
   a finding. Lower priority; its circularity is conceded.

## What "as long as you want" can and cannot buy

- **Cannot:** manufacture real validation data by spending compute. The wall is real.
- **Can:** (i) exhaustively search/curate whatever real microdata *does* exist; (ii) implement and
  stress-test the actual identification frontier (proximal CI) on the data we have; (iii) prove,
  rigorously, *where* the knowable/unknowable boundary sits on synthetic + real anchors — so the
  product never sells a confident answer it can't back. The deliverable is an **honest, calibrated
  boundary**, and a credible plan to earn the corpus that turns it into a guarantee.
