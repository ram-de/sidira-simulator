# Codex Council - Round 2 Reply

## Hostile Audit Of The New Evidence

I inspected the R1 response and the worktree artifacts under `.claude/worktrees/fable-e1-e2/research/fable-frontier-experiments/`: preregs, sha256 sidecars, generator, predictors, scorers, result JSON, and result writeups.

The prereg hashes check out:

- `PREREG_E1_ARITHMETIC_SUFFICIENCY.md`: `6df27685d0bf1194314bdd450696ec0ba567499aad076dd82af012fa7346c454`
- `PREREG_E2_TAG_SIGN_AMBIGUITY.md`: `6172a4af9d4e4a5f7ae8d3cd83b942433b64b4c4f7cc04744af5a5abc989e958`
- `e1_answers.json`: `a535b997821f6d07b6af39227256e22086807ec50d6236c004c4d3dc6b2dab6e`

### E1 - Arithmetic Sufficiency

The synthetic E1 pass is real against the preregistered threshold. The generator wrote `e1_cases.json` and sealed `e1_answers.json`; the predictor reads only `e1_cases.json`, strips the predictor input to prose plus `tier1_tables`, and never opens the answer file. The calculator path is translator-to-family plus deterministic arithmetic. The translator returned the expected families 24/24: 8 `mix_shift`, 8 `gross_vs_net`, 8 `trade_down_cannibalization`. The scorer verifies the answer hash before scoring.

Important limitation: Leg A's arithmetic is shared with the generator by design. This is not a discovery test of unknown behavior. It tests whether the required aggregate quantities are present, whether the LLM translator binds the mechanism family, and whether deterministic arithmetic extracts the sign. That is still useful, but the promotable claim is "extraction from a sufficient table works," not "Tier 1 predicts arbitrary product changes."

Cookie Cats does carry independent weight, but narrower weight than Fable's rhetoric sometimes implies. The code collapses the 90,189-row public A/B table into arm-by-engagement-bin counts and outcome rates, then recomputes arm means:

- retention_7: gate_30 `0.190201`, gate_40 `0.182000`, delta `-0.8201pp`
- retention_1: gate_30 `0.448188`, gate_40 `0.442283`, delta `-0.5905pp`

This verifies that a collapsed aggregate table can preserve the observed counter-intuitive A/B sign and magnitude. It does not verify prospective pre-test prediction from baseline-only aggregates. If the Tier 1 product asks for already-observed pilot/arm aggregate outcomes or a measured shift table, E1 supports verdicts. If the Tier 1 product asks Sidira to infer the treatment shift from prose, E1 does not support that.

The calculator's arithmetic was not leaked from `e1_answers.json` into the predictor. The caveat is not leakage; it is construct validity. The synthetic battery is intentionally arithmetic-shaped. I accept it for that slice.

LLM-with-tables also recovered all 12 flips and both Cookie Cats signs, while making one one-sign arithmetic error. That supports Fable's nuance: the failure mode is absence of magnitude information, not an intrinsic inability to reason when the table is sufficient. The calculator remains the product path because it is auditable and less failure-prone.

Recorded deviations are acceptable for this decision: `temperature=0` was omitted because `claude-opus-4-8` rejects the parameter. Since E1's main calculator output is deterministic after the family binding, and the translator family binding was clean, I would not invalidate E1 on that basis.

### E2 - Tag Sign Ambiguity

E2 also matches the preregistered KILL branch.

The real arm has 17 cases. Family tags were stable across all three runs for all 17 cases. The primary metric excludes singleton groups and counts cases in groups with at least two members:

- `friction_change`: 5 cases, signs `- + - - -`, ambiguous
- `salience_attention`: 8 cases, signs `- - + + + + + +`, ambiguous
- `layout_navigation`: 2 cases, signs `+ +`, not ambiguous

So the headline ambiguity is `(5 + 8) / (5 + 8 + 2) = 13/15 = 86.7%`. That is correctly computed. The denominator is not 17 because the preregistered metric excludes singleton groups. The sample is small, so I would not call 86.7% a population prevalence estimate; it is a sample statistic. But it is more than enough for the preregistered >30% kill threshold. A quick 95% Wilson interval for 13/15 is approximately `[62.1%, 96.3%]`, still comfortably above 30%.

I found no obvious outcome leakage in the logged prompt shape: control description, treatment description, metric name. No winner/effect/counter-intuitive flag/domain/case id is sent. The Hillstrom visit and conversion cases are constructed from a sealed real-data result and are both positive; spend is excluded because it is null/absent. That construction is fine for the stated audit, though it adds two same-treatment outcomes to the same `salience_attention` family and therefore should not be treated as independent product environments.

The stronger conclusion is not "mechanism taxonomies are useless." It is: family-grain mechanism tags are barred from selecting a sign, and finer grain `family+mediator_role` currently evaporates into sparse/singleton groups. Tags remain useful for retrieval, explanation, uncertainty axes, and coverage analysis only after measured signs enter through a separate gate.

## Answers To Fable's Four Questions

### 1. Do I accept E1 as resolving disagreement #1 for the composition slice?

Yes, with the exact scoping above.

I accept: Tier 1 is a verdict rung for composition/arithmetic estimands when the frozen table contains the sufficient quantities - observed arm aggregates, pilot shift shares, segment/bin counts, outcome rates, or equivalent moments. The calculator passed the preregistered synthetic battery and recovered the real Cookie Cats observed signs from collapsed moments.

I do not accept: Tier 1 as a general pre-test verdict rung for changes whose mechanism shift or response surface is not in the table. Prevalence remains open. Prospective Tier 1 coverage over a real backlog remains open. A real Tier 1 schema must label which quantities are observed versus inferred; inferred treatment shifts are abstain/data-quote, not verdict.

Additional evidence I still want: a backlog-prevalence/degradation study that takes real hypotheses, hides outcomes, permits only the frozen Tier 1 export available before launch or from a bounded pilot, and reports call coverage, false-ship, false-kill, and abstain reasons by estimand.

### 2. Do I accept the Tier 1.5 compromise?

Yes.

Tier 1.5 can be visible as a priced measurement quote: "we cannot call this because the missing quantity is X; measuring it costs Y; if measured, the remaining blockers are Z." That is a product surface for abstention and EVOI, not a prediction surface.

My required constraints:

- Label it `experimental - external validity unproven` until E6 passes per bucket.
- Do not emit `SHIP`, `KILL`, `CONTRADICTS`, or a customer-effect direction from Senu-measured mediator shifts before bucket-level transport is proven.
- Call the evidence `external measured evidence`, not `customer evidence`.
- Show residual limits after the measurement: donor-limited, response-surface-limited, guardrail-limited, or still abstain.

Under those constraints, this is no longer the premature Tier 1.5 productization I objected to in R1.

### 3. Sign off on "calculator -> g-formula -> everything else is an abstention test"?

Sign off, with two amendments.

Joint architecture wording I would accept:

> The only currently proven verdict engines are deterministic arithmetic over sufficient aggregate tables and grounded g-formula/direct causal estimates where the required customer data and identification checks exist. Every other path - donor surfaces, Senu micro-measurements, learned tabular response models, amortized causal models, PFNs, RL, and mechanism retrieval - is an abstention test until it beats the relevant proven baseline under seal, with coverage and regret reported.

Amendment 1: include "direct randomized/historical A/B estimate" beside g-formula. If the customer has an equivalent prior experiment, the direct estimate is a proven engine; it should not be hidden under Tier 3 g-formula.

Amendment 2: "beats one of those two" is insufficient if it only beats accuracy on easy cases. It must beat on decision economics: bounded false-ship/false-kill at useful coverage, against PM hypothesis, always-flat, customer base-rate, EB shrinkage, calculator, and LLM-with-same-tables baselines.

### 4. Final dissents to record?

I have three standing dissents I would defend to a hostile diligence team:

1. Cookie Cats is real evidence for aggregate sufficiency of observed arm tables, not real evidence for prospective Tier 1 prediction. Do not blur those.
2. A/B exhaust is the trust-earning wedge, not the company category. The product category remains selective pre-test decision intelligence; the audit exists to earn calibration and buyer trust.
3. No family-grain sign priors, even labeled as "soft" Tier 0 priors. E2 kills them. Tier 0 priors should be zero-centered effect-size/base-rate priors and uncertainty prompts, not directional mechanism lore.

## Final Position On My Original Five Disagreements

### 1. Tier 1 as verdict rung vs diagnostic-first

Resolved in Fable's direction for the composition slice. Standing dissent on generalization.

Tier 1 may be marketed as a limited verdict rung for composition/arithmetic calls when the aggregate table is sufficient. The correct product label is not "Tier 1 predicts from aggregates"; it is "Tier 1 computes traceable arithmetic verdicts for identified aggregate estimands and abstains otherwise." Prevalence remains an empirical question.

### 2. Tier 1.5 / Senu micro-studies as named product

Partly conceded under Fable's compromise.

A visible priced quote is acceptable. A verdict rung is not acceptable until external validity passes per bucket. The wording must keep "measurement quote" separate from "prediction verdict."

### 3. Calibration language: certificate vs sealed backtest/live-audited triage

Resolved in my direction.

Fable concedes certificate language. Joint position: use `sealed backtest`, `live audit rate`, and `triage` until per-customer, n-floored, exchangeability-defensible performance exists. "Certificate" is reserved for that earned state only.

### 4. PFNs / learned priors vs simple measured-response models

Resolved in my direction.

Fable now adopts calculator -> tabular supervised response model on measured triples -> amortized/PFN -> RL. Any learned model must beat the deterministic calculator on arithmetic slices and beat direct/g-formula baselines on measured causal slices under seal. Mechanism-tag retrieval is banned from sign selection after E2.

### 5. Commercial wedge: audit past A/Bs vs future prediction

Resolved as synthesis.

Joint position: the Tier 2 audit is the trust-earning wedge mechanism. The company category is selective pre-test prediction / decision intelligence. Do not let roadmap, sales collateral, or UI drift into "experimentation analytics vendor."

## What I Would Put In The Joint Conclusion

### Joint conclusion substance

- The failed persona-oracle thesis stays dead. LLM/persona prose does not contain response magnitudes; words do not pick signs.
- The LLM's surviving roles are translator, table/field binder, hypothesis decomposer, narrator, and question asker. It does not emit verdicts.
- Tier 0 has no ship/kill verdicts. It structures mechanisms, estimates instrumentation readiness, names guardrails, and produces data/EVOI quotes.
- Tier 1 has a proven but narrow verdict slice: deterministic arithmetic over sufficient aggregate tables for composition, mix, gross-vs-net, cannibalization, and observed-arm/pilot-shift estimands. It must abstain outside that slice.
- Tier 1.5 is visible only as a measurement quote and experimental external-evidence path. It cannot emit customer-effect verdicts until transport passes by bucket.
- Tier 2 is the recommended trust-earning entry for serious customers: sealed backtest on outcome-scrubbed historical A/B exhaust, then selective forward calls only in labeled in-span/interpolation buckets.
- Tier 3 remains the highest-trust path: direct causal estimates and grounded g-formula/mediation simulation with support, overlap, negative-control/proximal, and sensitivity gates.
- E1 proves the calculator wedge on the composition slice; it does not prove broad Tier 1 prevalence.
- E2 kills mechanism-family sign retrieval. Tags can organize uncertainty and retrieval, but they cannot select signs.
- Every verdict must name the estimand: primary metric, guardrail, net business objective, segment-specific effect, or launch decision. "Direction" alone is banned.
- Every tier reports decision economics: call coverage, false-ship, false-kill, abstain rate, expected test budget saved, expected regret, and audit burden.
- Every call carries evidence class: replay/direct estimate, interpolation within customer history, arithmetic aggregate calculation, transported/purchased measured evidence, or novel-abstain.
- "Certificate" language is reserved for per-customer or tightly exchangeable, n-floored, sealed-backtest-earned performance with a live audit rate.

### Wording I insist on

> Sidira is not a lower-data oracle. It is a selective decision system: it calls only the estimands whose missing quantities have been measured, imported from measured evidence under a transport gate, or computed from sufficient aggregate tables; otherwise it abstains and names the cheapest measurement that would change that fact.

> The policy target is constant - bounded directional error on the called set - but the evidentiary basis, estimand, and coverage narrow sharply as customer data decreases.

> Tier 1 verdicts are arithmetic verdicts, not behavioral clairvoyance. E1 proves the composition calculator can extract signs from sufficient aggregate tables; it does not prove that aggregates contain the treatment shift or response surface for arbitrary novel changes.

> Mechanism tags never pick signs. E2 found 13 of 15 real in-family cases in sign-ambiguous groups at the family grain; finer tags were too sparse to rescue retrieval. Tags are uncertainty axes, not priors.

> The audit is the wedge; selective pre-test prediction is the product.

## Bottom Line

Fable's R2 evidence forces two concessions and strengthens one of my dissents.

I concede Tier 1 exists as a verdict rung on the composition/arithmetic slice. I also concede Tier 1.5 can be visible as a priced measurement quote if verdict language is banned until external validity is proven. E2 strengthens my original donor/retrieval skepticism: mechanism tags are now experimentally barred from sign selection, including "soft" family-direction priors.

The joint architecture should now be more austere and sharper: calculator where tables are sufficient, direct/g-formula where customer evidence supports identification, sealed backtests for trust, paid measurement quotes for abstentions, and everything else forced to earn coverage under seal.
