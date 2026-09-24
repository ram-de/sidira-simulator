# Founder Readout — Simulation accuracy, a fresh look with Voyager in the picture
### 2026-09-24 · what changed since July, what it means for the engine, and the strategy I'd build around

---

## TL;DR

1. **The July diagnosis held up, and the field caught up to it.** Accuracy comes from the
   *information in the inputs* (the customer's own experiments, warehouse tables, real
   behaviour), never from the persona machinery or a bigger model. Three independent 2026
   results say the same thing: persona role-play is *worse* than asking the model for a plain
   population prior; a frontier judge on 330 real product tests scored κ ≈ 0.1 and no prompt,
   model, or stimulus lever helped; digital twins land at r ≈ 0.2 per person.
2. **One genuinely new signal:** agents that *act* on a live product (not read a text
   rendering of it), seeded from real clickstream, with a behavioural outcome and a pre-period
   calibration step, report 70–77% directional agreement on real e-commerce tests (Shopify
   SimGym, Amazon). Small n, unreplicated, and Amazon itself says "not clearly above baseline".
   It is a sealed experiment to run, not a bet to make.
3. **Voyager changes the problem more than any model does.** Every proven engine we have is
   gated on data the customer would not hand over on day one. Voyager is a continuous ingestion
   layer over exactly the places that data already lives (experiment readouts in decks, Slack,
   dashboards, Jira, the experimentation platform). Voyager lifts a customer from tier 0 to
   tier 2 automatically, supplies the lever map for tier 3, and closes the predicted-vs-actual
   loop without anyone doing data entry. **That is the accuracy strategy.**
4. **Personas: retire as predictors, keep only as segment weights.** Page walkthroughs: retire
   as text for agents to read; test them in their 2026 form (agents acting on control vs
   treatment arms of a real build) under seal, with a pre-registered kill criterion.
5. **The market slot is open and it is ours by temperament:** calibrated, abstaining, pre-test
   triage validated on the customer's own history, plugged into the incumbent platforms. Nobody
   else can afford to say "we don't know"; every funded competitor is selling 85–97%.

---

## 1. Where the engine stands (facts, not hopes)

From our own sealed campaign (all pre-registered, fingerprinted before scoring):

| Route | Result | Status |
|---|---|---|
| Persona role-play as predictor | 0.29 directional, below chance | dead |
| One-line LLM comparison | 0.50 | dead |
| Councils / more priors / frontier swap | worse or unchanged; 0/12 on magnitude flips when models agree | dead |
| Persona richness (10 generic vs 24 rich) | +2% noise, no callable region | lever closed |
| Reverse-PRD product context on 131 real GoodUI tests | 0.594, p = 0.034; below the 0.67 majority-class rate | real but weak |
| Arithmetic over sufficient aggregate tables (E1) | 24/24 incl. 12/12 narrative flips | proven, coverage unknown |
| Grounded g-formula + negative-control watchdog on per-user data | 12/12 on magnitude flips; Cookie Cats sign recovered under injected confounding | proven on the flip slice, LEAD on real data |
| Direct match to a past experiment | best evidence when it exists | proven, retrieval only |
| Confident-KILL screen | 0% killed-winner on clearly-flawed variants; correctly PASSes subtle ones | safe, cannot KILL pre-partner |

What is deployed today is still the role-play panel with the KILL/PASS/ABSTAIN screen stamped
on top. The Senu ledger has zero scored cases. The friends-and-family game is live with no
players. There is no design partner archive. So the proven engines exist in research and the
unproven one is the one customers touch.

## 2. What changed outside (June to September 2026)

**Against words-only prediction, now with large n.**
- *The Judge Knows When It Knows* (Aug 2026, pre-registered, 330 real conversion tests from a
  CRO catalogue, screenshots only): Gemini 3 Flash κ = 0.14; on the significant half κ = 0.11
  with CI through zero. A 2.8× pricier frontier model, prompt redesign, stimulus fidelity and
  change-type priors all failed their gates. "Always pick B" beat the judge's most confident
  slice. 44% of catalogue "winners" were not significant, so the labels themselves are noisy.
- *Do Synthetic Personas Predict Real Audience Response?* (Sept 2026, Upworthy): a no-persona
  population-prior query beat a 10-persona panel (Kendall τ 0.36 vs 0.08, non-overlapping CIs).
  Role-play injects bias. This is our 0.29-vs-0.50 result, replicated by someone else.
- *Funhouse Mirrors* landed in Science Advances (Sept): twins r ≈ 0.2 per person, no better
  than demographics for population means. *Statistical realism is not evidence of treatment-
  effect accuracy* (Apr): making agents look realistic can make effect estimates worse.
- OptimismBench (Jul): 14 of 16 frontier models are optimistic about success; only Anthropic's
  frontier tier is pessimistic; a system prompt saying "you are biased" does not fix it. This
  is our llama-up / Opus-down finding, generalised.

**For grounded, acting agents, small n.**
- Shopify SimGym (Feb/May 2026): personas fitted from production clickstream, VLM browser
  agents on the live storefront, add-to-cart as outcome: 77% directional agreement on 50 real
  theme/UI changes. Shipped as "research preview" with an explicit "not a replacement" label.
- Amazon S-RCT (Aug 2026): 67 historical marketing tests, sign agreement 0.70, agents overshoot
  magnitudes, a two-phase pre-period calibration cuts squared error ~77×, within-subject design
  cuts SE ~2.4×. The authors say directional signal is *not clearly above uninformed baselines*.
- Data-grounded personas with pairwise elicitation (Sept 2026): 0.75–0.90 directional on 40
  tests; ungrounded personas ablate to chance.
- Hewitt et al. in Nature (Aug): r = 0.85 on 70 survey experiments with *text* treatments,
  magnitudes overestimated; weak on megastudies of same-mechanism nudges, where human experts
  are at r ≈ 0 too.

**Method pieces that read like a spec for what we already designed.**
- *The Illusion of Intervention* (Google/DeepMind, May): LLM experiments are observational;
  proposes negative-control outcomes as the diagnostic. That is our watchdog, validated from
  the outside.
- Spotify's surrogacy framework (Jun): LLM panels recover 39% of the human effect raw; a
  nonparametric calibration to a small human sample closes the gap, with a falsification test.
- Tigre and Souto (Mar): Trust / Correct / Abandon decision rule with an n = 50–300 calibration
  sample. Beta-Bernoulli post-hoc calibration on resolved outcomes beats forecasting-fine-tuned
  models (May). Local empirical-Bayes pooled over *comparable* experiments beats global EB on
  ASOS's 78 experiments (Nov 2025).

**Infrastructure.**
- RL fine-tuning as a service is going away (OpenAI shuts self-serve fine-tuning by Jan 2027,
  Tinker raised prices 50%) and there are no small-n tabular wins for GRPO. Skip.
- TabPFN-3.5 and CausalPFN are real for estimating effects *from* data; nothing amortises a
  prior over not-yet-run experiments. Weights are non-commercial.
- Computer-use agents are cheap and mechanically reliable now (OSWorld-Verified ~85%, cloud
  browsers ~$0.02/hour, DOM-structured access). Building a treatment variant behind a flag is
  now an agentic-coding task, not a sprint. "Simulate before you build" matters less than it
  did; "simulate before you spend traffic" is the value.

**Market.**
- Simile raised $200M at $2B (Jul) selling behaviour prediction with vendor-reported 85%; Aaru,
  Brox, Studio claim 85–97% with no independent validation. Prediction claims are escalating
  while evidence is not.
- Prioritisation is being bundled free: Optimizely Opal Idea Builder, Amplitude's
  experimentation agent, Kameleoon Predictive Impact Scoring. Synthetic qual became a Dovetail
  checkbox (Jul). Wondering shut down.
- Amplitude took over Statsig (May). Statsig, Convert, Optimizely ship MCP servers. Nobody in
  the incumbent set ships a calibrated pre-test prediction or an abstention rate.
- Company-brain products (Microsoft Work IQ GA in June, OpenAI company knowledge, Glean at
  $200M ARR) all ingest meetings, Slack and docs continuously and can reach a warehouse. None
  of them emit structured, tracked, calibrated hypotheses. That layer is unoccupied.

## 3. The one principle that explains every result

**Directional accuracy is a function of whether the deciding quantities are present in the
inputs.** Words-only: chance on anything non-obvious (ours, the 330-test judge, Upworthy).
Aggregate tables that contain the mix and rates: near-perfect (E1). Per-user data with a
causal identification check: the wedge (AMBDOM, Cookie Cats). Agents that observe real
behaviour on the real product: a real but modest signal that needs a human calibration sample.
The customer's own past experiments: the strongest cheap prior there is, and the only source
that fixes base rates (mature programmes win 8–20% of the time with ~70% true nulls, so a
predictor must beat "predict flat", not a coin flip).

The persona pack and the crawler were attempts to *manufacture* those quantities from
descriptions. They cannot; the numbers are not in the words. The question is therefore not
"how do we make the simulation smarter" but "how do we get the deciding quantities into the
system for every customer, cheaply, without a day-one data negotiation". That is what Voyager
is for.

## 4. Voyager as the accuracy engine

The July councils concluded the data dependency "cannot be dissolved, only restructured into a
ladder". Voyager restructures it by ingestion rather than by asking. Five concrete jobs:

1. **Harvest the experiment exhaust (tier 2, for free).** Past experiments live in readout
   decks, Slack threads, dashboards, Jira epics and the experimentation platform. Voyager
   extracts (hypothesis text, arms, primary metric, dates, traffic, outcome, decision) into the
   experiment archive we already have. Thirty resolved non-null experiments is the certificate
   bar; most mid-market programmes cross it within a year of history. This is the substrate for
   the retrieval route (already top precedence in the decision flow), for local empirical-Bayes
   priors per change class, and for the sealed per-customer backtest.
2. **Deliver hypotheses pre-structured.** Voyager-generated hypotheses arrive with mechanism,
   lever, primary metric, guardrails, segment, expected direction, the most similar past tests
   and their outcomes. That is the translator's output produced upstream, from context the
   translator never had. Input quality was already a known lever (input lint, answerability);
   this raises coverage and lowers translation error.
3. **Build the estimability map.** Voyager knows which tables, flags and dashboards exist and
   what they are called. That is the lever map and metric registry the Ground step currently
   asks the customer to fill in by hand. It turns tier-3 onboarding from a wizard into a review.
4. **Close the loop automatically.** When the experiment ships, Voyager sees the readout. The
   (prediction, outcome) pair lands in the calibrator without data entry. This is the paired
   corpus the July decision named as the moat, built by the ingestion layer rather than by Senu
   studies. Senu stays as the factory for the counter-intuitive tail; Voyager supplies volume.
5. **Fix base-rate realism.** Voyager sees the whole backlog, including what flopped and what
   was never run. Public corpora are winner-biased; the customer's own stream is not.

Idea *source* also predicts win rate (analytics-, archive- and research-sourced ideas win more
often than intuition-sourced ones). Voyager raises the prior before Sidira screens it. The two
products are one loop: Voyager raises the base rate of the backlog, Sidira screens it against
the customer's own evidence, the outcomes feed both.

## 5. Personas and page walkthroughs: what to ditch, what to flip

**Personas.** Retire the persona pack as anything that touches a verdict. Keep segment shares
as transport weights (P(z)) and as the breadth checklist ("the segments you did not model").
Stop investing in the clustering pipeline, the builder wizard and the 8B model plan. Segment
definitions should come from the customer's warehouse and from the segments their past
experiments were cut by, which Voyager can read. The "talk to your users" chat survives as a
narrator over computed results, labelled as such.

**Page walkthroughs.** The crawler's current job, rendering the product as text for agents to
read, is the weakest lever we have measured (0.594 with product context, κ ≈ 0.1 for screenshot
judging at large n). The 2026 signal came from a different use of the same machinery: agents
*acting* on the real control and treatment, with a behavioural outcome, calibrated against a
pre-period human baseline. Flip the crawler into an arm-walker:

- treatment is a real build behind a flag (agentic coding makes this cheap) or an interactive
  prototype;
- agents are seeded from real clickstream segments, not archetypes;
- outcome is an action (click, add, complete), not a sentiment;
- pre-period calibration on the control arm against the customer's real numbers, per Amazon;
- scored under seal against predict-flat and always-treatment, with κ and Brier, never accuracy.

Pre-register a kill criterion (for example: no better than always-treatment on 40 sealed cases
at the design partner, or on the Streamly mock, in six weeks) and let the result decide whether
walkthroughs survive. I would not build product around it until it passes.

## 6. What the engine looks like, ranked by evidence

| Rank | Engine | Evidence | Data it needs | Voyager's role |
|---|---|---|---|---|
| 1 | Retrieval of the customer's own past tests + local EB prior per change class + sealed backtest | strongest and cheapest; ASOS local EB, LOLA fine-tune on history, our own precedence order | experiment exhaust | harvests it |
| 2 | Arithmetic and g-formula over warehouse tables with the negative-control watchdog | proven on the flip slice (E1, AMBDOM, Cookie Cats) | cross-tab export or per-user rows | supplies the lever map |
| 3 | Clickstream-seeded agents acting on real arms, pre-period calibrated | 70–77% on 50–67 tests, unreplicated, needs a build | a flagged variant + control traffic numbers | supplies segments and baselines |
| 4 | LLM population prior, inverted-pair bias correction, Beta-Bernoulli calibration on resolved outcomes | labelled prior only; never a verdict | resolved outcomes to calibrate | supplies outcomes |
| dead | Text-rendered persona role-play; councils; fine-tuning without a corpus | disproven, ours and theirs | — | — |

Precedence stays as designed: trustworthy empirical > labelled prior > untrustworthy empirical
(abstain). The decision-economics report per customer (coverage, false-ship, false-kill,
abstain rate, traffic saved) is the product number, not directional accuracy.

## 7. Ninety-day plan

1. **Flip the verdict path.** Behind the existing flag, stop deriving the screen's signal from
   the role-play panel. Replace the LLM leg with a population-prior query using inverted-pair
   elicitation (ask P(win) and P(lose), log the skew per model) and a Beta-Bernoulli calibrator
   on resolved outcomes, emitted as *prior, not verdict*. Keep the chat.
2. **Voyager → experiment archive.** Build the extractor that turns readout decks, Slack
   threads, dashboards and platform exports into archive records with a confidence field per
   extracted number. Target: 30 resolved non-null experiments for the design partner. The
   kill-rate backtest already told us published narratives lack traffic and baselines; the
   platform export is the anchor, Voyager is the glue.
3. **Hypothesis contract.** Define the Voyager → Sidira hypothesis schema (mechanism, lever,
   metric, guardrails, segment, expected direction, nearest past tests, base rate). It is the
   translator's output shape; validate it with the existing input lint.
4. **Sealed per-customer backtest as onboarding.** Time-masked, outcome-scrubbed descriptions
   in, predictions sealed, outcomes revealed. Report κ and Brier against predict-flat and
   always-treatment, plus coverage and killed-winner rate. This is the sales artefact and the
   trust certificate, now automatable.
5. **E8, the arm-walker experiment.** Six weeks, sealed, with the kill criterion above.
6. **Stop.** No persona-pipeline work, no 8B model, no RFT, no council work.
7. **Public data, only for calibration transfer.** GoodUI and GuessTheTest with the
   always-treatment baseline and human 59% anchor; Wikimedia banners for free volume; ask
   Mozilla for Nimbus results (the one open archive with PRD-quality descriptions).
8. **Traction.** One design partner with an experiment archive is worth more than every
   public dataset combined. Nothing here certifies without it.

## 8. Honest caveats

- The acting-agent results are small-n, single-team, e-commerce, with no predict-flat baseline
  reported, and Amazon's own conclusion is cautious. Our richness ablation found nothing, but
  it was text-rendered role-play; whether *acting* on a real build is different is exactly what
  E8 has to settle.
- Voyager-mined archives will be messy: survivorship, missing denominators, decisions recorded
  without numbers. The estimate has to carry an extraction-confidence field and the certificate
  bar has to count only resolved, numerically complete cases.
- The calibrated-fiction ceiling does not move: trustworthy at segment level, fiction per
  person. Twins are still r ≈ 0.2 and no 2026 result changes that.
- The 12–18 month clock: if OpenAI or Amazon productises replay-based simulation inside an
  experimentation platform, "predict from your logs" becomes a platform feature. The defence is
  the per-customer calibration track record and being an acquirable module over MCP, not a
  competing platform.

---

*Ties to: `simulation-engine-where-we-landed.md` (July landing), `sessions/fable-research/
DEBATE_CONCLUSION.md` (the ladder and the proven-engines statement), `sessions/confident-kill-
calibration-study/` (840 sims + GoodUI), `sessions/agent-behavior-spec/killrate-backtest/`
(why priors need the customer's own log), `sessions/watchdog-productization/
GROUNDED_DECISION_ARCHITECTURE.md` (the flow this plugs into).*

External sources referenced: Ashokkumar, Hewitt et al., Nature 656 (2026); Li et al.,
arXiv:2604.02458; "The Judge Knows When It Knows", arXiv:2608.07517; "Do Synthetic Personas
Predict Real Audience Response?", arXiv:2609.25010; Peng, Toubia et al., Science Advances
(Sept 2026); SimGym, arXiv:2602.01443 and 2605.19219; Amazon S-RCT, arXiv:2608.02345;
persona-conditioned agents, arXiv:2609.01038; "The Illusion of Intervention", arXiv:2605.20767;
Spotify surrogacy, arXiv:2606.17165; Tigre and Souto, arXiv:2609.13148; OptimismBench,
arXiv:2607.26981; Beta-Bernoulli calibration, arXiv:2605.27668; local EB on ASOS,
arXiv:2511.21282; Spotify on Bayesian A/B (Sept 2026 blog); Optimizely 173k-experiment report;
GoodUI 70,149-guess analysis; Microsoft Work IQ GA (June 2026).
