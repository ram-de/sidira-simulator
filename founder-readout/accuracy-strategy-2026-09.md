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

## 9. Addendum (2026-09-25): the agentic pivot

Written after the founder's follow-up questions on "X for agents" products, on raising to
hire researchers, and on whether the accuracy problem can be sidestepped. Short answers, then
the reframing that came out of it.

### 9.1 Four questions, four answers

- **Pivot into agent infrastructure (mail, browser, payments, chat for agents)?** No. Those
  are picks-and-shovels categories with thin moats, dozens of funded entrants each, and
  incumbents already shipping the same thing. We would enter with no distribution, no data and
  no head start. Worse than the position we hold.
- **Does the agentic wave change our problem?** Yes, and this is the pivot worth making. Agents
  will soon propose most product changes, at a volume no team can test. That flips the
  economics: the sim no longer has to *predict the sign* of every idea, it has to *triage*.
  Kill what the company's own history already disproves, abstain honestly on the rest, and
  route the rest to a real test that an agent can build and run cheaply. Both halves of that
  are things the engine has already demonstrated under seal. The hard part, guessing a
  genuinely new idea's outcome, moves to the real experiment.
- **Would funding plus research scientists solve accuracy?** Partly, and which part matters.
  Cold-start sign prediction from a description is not a talent gap: Amazon, Spotify and
  Microsoft have larger teams than any round buys and none of them is above chance on it.
  Research money *can* move the grounded route (cross-customer transfer by mechanism class,
  surrogate metrics, pre-period calibration for acting agents, negative-control methods on
  messy exhaust), buy data rights from design partners, and run the acting-agent line at
  proper n. Realistic ceiling: right on roughly three of four directional calls where
  grounding exists, honest about the rest. Hire research engineers who live in customer
  data, not scientists chasing the ungrounded problem. Raise on the corpus and the loop, not
  on "we will crack the simulation".
- **Can agents stand in for the users we can never interview?** Only when their answers are
  pinned to records. An agent that took part in a *simulation* can only tell you about the
  simulation. An agent that took part in, or watched, the *real* test can be debriefed and it
  means something: the customer's own support and analytics agents reading arm-tagged records,
  and the growing share of agent-driven shoppers who are genuine visitors and can be asked why
  they abandoned. Rule: every interview answer cites a record or is marked as a guess. That
  single rule separates this from the persona chat.

### 9.2 The installed observer (persona replacement)

An agent installed in the customer's product that learns how users interact over time and
then takes part in screening is the right replacement for personas, and it is close to the
strongest thing anyone has shown working (clickstream-seeded agents with pre-period
calibration). Three conditions:

1. **"Learn" means a fitted behaviour model, not a narrative profile.** Per segment: action
   propensities by page state, drop points, response to past changes. The language model does
   perception of a new variant (what is on the page, what actions exist); the learned model
   does propensity. Blend the two and it drifts back into fiction.
2. **Observation teaches the status quo; experiments teach change.** The observer's real
   training signal is the arm-tagged tests the gate routes to traffic. The tests teach the
   observer, the observer sharpens the next screen.
3. **It earns its vote.** No vote until it passes a sealed backtest on that customer's own
   tests against predict-flat; loses the vote if it drifts.

Cold start is a ladder: day one, no vote, value is the mined archive plus test shaping; weeks
one to four, observation gives segment shares and funnel rates, enough for the arithmetic tier
and to catch broken variants; after the first handful of arm-tagged tests, the backtest, then
the vote. A per-vertical base model warm-starts it, treated as a prior because transport is
still our largest exposure. Runs inside the customer's environment (zero-egress), and stays
small: a nightly-updated behaviour model plus a language model for perception.

### 9.3 The story: Meridian Home, one year

*Month zero.* Voyager connects to Slack, Notion, the support desk and the warehouse; it finds
eleven past A/B tests in old decks and threads and writes them into the archive. Nobody
remembered more than four. Sidira drops an observer into the storefront and connects to the
experimentation platform. The observer starts learning traffic shape. It does not vote.

*Month one.* The PM, Dana, works with a planning agent that reads Voyager and a coding agent
that builds. Two hundred ideas a week arrive as structured hypotheses. Sidira makes one of
three calls. KILL when the company's own history answers it (hiding the delivery estimate lost
conversion two years ago; sixty of two hundred die this way, at no cost). PASS when the
warehouse and archive line up (first-visitor discount: three past discount tests lifted
conversion and hurt margin; passed, margin added as guardrail). ABSTAIN when it honestly does
not know (mobile add-to-cart placement; sized, stopping rule set, handed to the platform, and
the branch already exists so the test starts the next morning).

*Month two.* The button test ends. Dana opens a chat with Meridian's working agents, each
reading arm-tagged records. Support: thirty-one treatment chats complained about hidden fabric
swatches, links attached. Analytics: product-to-cart up, cart-to-checkout down, small screens.
Three agent-driven shoppers who abandoned in treatment are asked why: the delivery estimate
was hidden. Every answer cites a record. The result and the debrief land in the archive.
Nobody files a report.

*Month six.* After nine arm-tagged tests the observer predicts them blind, beats predict-flat,
and earns its vote. It now walks new variants on the staged build with Meridian's real
propensities; its confidence is scored against every subsequent test.

*Month twelve.* Test slots did not increase. What went into them changed:

| Before | After |
|---|---|
| Twenty ideas a quarter, five tested, chosen by gut | Two hundred a week, sixty percent killed or passed on evidence, the rest tested |
| Two weeks from idea to test start | One day; the branch exists before the decision |
| One in three tests underpowered or mis-metriced | Tests shaped before launch, guardrails attached |
| Results in decks, forgotten in a quarter | Every result and debrief in the archive, feeding the next call |
| Losers found only after burning traffic | Known losers never reach traffic |

Why it works: the company's own history is the model; confidence is honest and re-scored
monthly; real tests close the loop, and the loop compounds per customer. Why it serves both
worlds: Dana keeps the veto and her overrules are scored; her agents submit over the same
interface, get the same three calls, and learn which of their ideas keep dying. The ratio of
human to agent submissions will flip; the gate will not change.

### 9.4 Making it a product for agents

The engine is AI-native; the surface is not. An agent-native product is one where the agent
is the first-class user and the console is a view over what agents did. Pitch line: **the
gate every agent calls before a change reaches users.** Coding agents have CI for
correctness; nothing gives them CI for user behaviour.

Five primitives, exposed as an MCP server and a REST API, dashboard built on top:

1. **Submit a hypothesis** (structured contract: change, segment, metric, branch) and get a
   verdict, a confidence, the evidence records, and a test spec on ABSTAIN or PASS.
2. **Run the test** on the customer's platform, or on a lightweight assignment SDK we ship;
   traffic budget enforced here.
3. **Get the result** by webhook when the stopping rule fires, with guardrail status and the
   arm-tagged debrief.
4. **Search the archive** (Voyager's memory as a tool) so planning agents stop repeating known
   losers.
5. **Read your own score.** Every agent has an identity and a calibration record; a poor
   record loses traffic budget, a good one earns it.

What changes: programmatic onboarding (observer tag, scoped credentials, a key; the human sets
policy once: budget, guardrails, which verdicts need a signature); discovery in MCP registries,
coding-agent tool catalogs and an llms.txt; per-call and per-test pricing on agent-friendly
rails; many agents from many vendors brokered by one gate; humans keep the veto and the veto
is scored. What does not change: accuracy still comes from the customer's history and real
tests, cold start is not fixed by the surface, and abstentions must not be hidden from a
machine caller that will act on the verdict without reading caveats.

Build order: MCP server with the five primitives on the existing verdict path; assignment SDK
and platform integrations; agent identity and calibration scores; self-serve keys, usage
billing, registry listings; dashboard last, as a read view of the ledger; persona chat and
wizard retired along the way.

### 9.5 Is this already happening?

Yes, in three layers, the youngest of which is the least trusted:

- **Agents writing and merging code is mainstream.** Razorpay's internal agent system merges
  thousands of PRs a month, over a third with no human in the loop; Stripe auto-merges
  low-risk changes. One estimate puts Claude Code at roughly four percent of public GitHub
  commits, double the prior year.
- **Agents deciding what to build from product data has started, with a human approving.**
  PostHog ships background agents that watch product data for errors, frustration and feedback,
  research the problem, write the fix and open a PR; nothing ships on autopilot. PostHog found
  PMs and marketers using its AI more than the engineers it targeted.
- **Agents generating hypotheses and variants is where the experimentation vendors are
  racing.** Optimizely Opal has a variation-development agent; VWO ships an MCP server; Pagent
  defines hypotheses, builds real-code variants and runs tests; one vendor claims fully
  autonomous hypothesis, synthetic simulation and deploy with no human; Statsig is inside
  OpenAI; a CHI 2026 paper automates A/B tests on live sites with interactive agents.

Consequences: the firehose exists now; the human-approval step is the wedge (companies want to
let agents ship more and cannot because review does not scale); the competitive risk is the one
already named in §8, every platform will bundle "AI hypothesis generation" for free. No public
evidence shows agents choosing what to build *well*; the evidence shows they choose
prolifically and that humans are the bottleneck. That is the condition under which a
calibrated gate is worth paying for.

### 9.6 The difference from the competition, stated precisely

Every competitor claims accuracy (85–97%, unverified). The claim we can own is stronger and
none of them can make it without our loop: **every verdict ships with its own scored track
record, per customer, sealed, and "we don't know" is a first-class answer.**

Concretely, four things a competitor cannot copy by shipping a feature:

1. **Calibration, not accuracy.** A stated ninety percent that is right nine times in ten on
   *this* customer's tests, re-scored every month, with the ledger inspectable. A headline
   percentage from a vendor's private benchmark is not that.
2. **Abstention as a product feature.** The gate is allowed to say "I don't know", and the
   abstention is routed to a real test rather than dressed up as a prediction. Nobody selling
   85–97% can afford this; it is the only honest answer on the majority of genuinely new ideas.
3. **Evidence attached to every call.** KILL comes with the past test; PASS comes with the
   warehouse rows; the debrief cites the chat, session or agent log. A verdict without a
   citation is marked as a guess.
4. **Neutrality across generators.** Optimizely, VWO, PostHog and the coding agents all
   *generate*. Being the gate that arbitrates all of them on the customer's own evidence is a
   position none of the generators can hold, because each is selling its own ideas.

The paired corpus (hypothesis, what the gate said, what the real test showed) is what makes
claims 1 to 3 checkable, and it accrues only to whoever runs the loop. That remains the moat.

Sources for §9.5: Masters Union on agents in production (Razorpay, Stripe); SerpSculpt Claude
Code usage statistics; PostHog product page, AI-products handbook and "building AI features"
newsletter; Humblytics "AI A/B testing tools ranked by agent-readiness"; Varify "AI-powered
A/B testing platforms 2026"; ACM CHI 2026 "Agent A/B: Automated and Scalable A/B Testing on
Live Websites with Interactive LLM Agents".

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
