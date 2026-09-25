# Stroma — the gate every agent calls before a change reaches users

### 2026-09-25 · consolidated from the accuracy readout, the agentic-pivot discussion, and the competitive scan

> **Naming:** Stroma is the product. The memory layer and the gate are two parts of one
> product; the earlier working names for them are retired in this document.

> **Status:** draft for founder review. The Slack thread on this topic
> (voyager-per3655, channel C0C4D3G7ZFE, 2026-09-25) could not be read from the
> session that produced this draft; its points are not yet folded in. See §7.

---

## 0. The thesis in four sentences

Agents now propose and build most product changes, at a volume no team can test. The company
still has to decide which changes deserve real traffic and which should die before they waste
a slot. Stroma is that decision: a calibrated gate that kills what the company's own history
already disproves, passes what its own data supports, and says "we don't know" on the rest
and routes it to a real test. Stroma's memory layer, which reads the company's own
interactions and data, is what makes the gate possible, and every
real test makes the gate sharper for that customer, which nobody else can copy.

---

## 1. What we learned about accuracy, and why it points here

Eighteen months of sealed studies, ours and the field's, reduce to one principle:

**Directional accuracy is a function of whether the deciding quantities are in the inputs.
It is not a function of the model, the persona machinery, or the prompt.**

The evidence, compressed:

| Method | Inputs | Result |
|---|---|---|
| Persona role-play over a text rendering of the page (ours) | Description + personas | 0.29 directional; richness ablation: no effect |
| Naive LLM asked directly (ours) | Description | 0.50, i.e. chance |
| Multi-model councils (ours) | Description | Worse; 0/12 on flips when models agree |
| Frontier judge on 330 real product tests (2026, external) | Description | κ ≈ 0.1; no prompt, model or stimulus lever helped; "always B" beat the judge |
| Digital twins of individuals (2026, external) | Person profile | r ≈ 0.2 per person |
| Arithmetic over the customer's aggregate tables (ours) | Warehouse rows | 24/24 |
| Grounded simulator with g-formula and negative-control watchdog (ours) | Warehouse rows + lever map | 12/12 where the LLM scored 0.00–0.50 |
| Agents *acting* on the live build, clickstream-seeded, pre-period calibrated (Shopify, Amazon, 2026) | Real behaviour + real page | 0.70–0.77 on real e-commerce tests; small n; Amazon: "not clearly above baseline" |

Three consequences, each of which shaped the product below:

1. **Cold-start sign prediction from a description is not a talent or model gap.** Amazon,
   Spotify and Microsoft have more researchers than any seed round buys and none of them is
   above chance on it. Raising money to "crack the simulation" would be raising against the
   evidence.
2. **What works is getting the customer's own quantities into the system.** Past tests,
   warehouse tables, real behaviour. That is a data-acquisition problem, and Stroma's memory layer is a
   data-acquisition layer over exactly the places that data already lives.
3. **The one thing the engine has always done well is say when it does not know.** The
   confident-KILL study killed zero winners on clearly flawed variants; the abstention path is
   calibrated. In a world of five test slots a quarter that was a weakness ("it abstains too
   much"). In a world of two hundred agent-generated ideas a week it is the whole product.

So the accuracy strategy and the product strategy are the same move: stop trying to predict
the sign of new ideas from words, and build the gate that triages on evidence, abstains
honestly, and lets the real test answer the rest.

---

## 2. The story: Meridian Home, one year

Meridian is a mid-size online furniture store.

**Month zero: the install.** Stroma connects to Slack, Notion, the support desk and the
warehouse and starts reading. It drops a small observer into the storefront and connects
to Meridian's experimentation platform. By the end of the week Stroma has found eleven past
A/B tests scattered across old decks and threads, with results, and written them into
Meridian's experiment archive. Nobody remembered more than four. The observer starts learning
the shape of Meridian's traffic: segment shares, drop points, device mix. It does not vote on
anything yet, and it is not allowed to until it earns it.

**Month one: two hundred ideas a week.** The PM, Dana, works with a planning agent that reads
Stroma's memory and a coding agent that builds. Ideas arrive by the dozen, many as ready branches.
Each one enters Stroma as a structured hypothesis: what changes, for whom, which metric, why.
Stroma makes one of three calls.

- **KILL** when Meridian's own history already answers it. An agent proposes hiding the
  estimated delivery date to clean up the product page. Two years ago Meridian tested hiding
  delivery information and conversion dropped. Killed, past test attached. Sixty of the two
  hundred die this way in the first month, at no cost.
- **PASS** when the warehouse and the archive line up behind it. A first-visitor discount
  banner: first-time visitors are forty percent of traffic with low conversion, and three past
  discount tests all lifted conversion and hurt margin. Passed, with margin added as a
  guardrail metric.
- **ABSTAIN** when Stroma honestly does not know. Moving the mobile add-to-cart button above
  the fold. Nothing in the archive; layout changes are small and hard to predict. Stroma says
  so, sizes the test, sets the stopping rule, and hands it to the platform. The branch already
  exists, so the test starts the next morning instead of waiting for a sprint.

**Month two: the debrief.** The button test ends. Dana used to get a number and a shrug. Now
she opens a chat with Meridian's own working agents, each reading records tagged by test arm.
The support agent: thirty-one treatment chats complained about missing fabric swatches, links
attached. The analytics agent: product-to-cart rose, cart-to-checkout fell, mostly on small
screens. Three agent-driven shoppers that abandoned in the treatment arm are asked why, and
answer that the delivery estimate was hidden under the new button. Every answer cites a
record; an answer without one is marked as a guess. The result and the debrief are written to
the archive automatically. Nobody files a report.

**Month six: the observer earns its vote.** After nine arm-tagged tests, the observer has
watched real Meridian users react to real changes, not just to the product as it stands.
Stroma runs a sealed backtest: the observer predicts those nine tests blind and beats
predict-flat. Only now does it take part in screening, walking new variants on the staged
build with Meridian's real propensities. Its confidence is scored against every later test. If
it drifts, it loses the vote until it recalibrates.

**Month twelve: what Dana shows the CFO.** The test slots did not increase. What went into
them changed.

| Before | After |
|---|---|
| Twenty ideas a quarter, five tested, chosen by gut | Two hundred a week, sixty percent killed or passed on evidence, the rest tested |
| Two weeks from idea to test start | One day, because the branch exists before the decision |
| One in three tests underpowered or measuring the wrong thing | Tests shaped before launch, guardrails attached |
| Results in decks, forgotten within a quarter | Every result and debrief in the archive, feeding the next call |
| Losers found only after burning traffic | Known losers never reach traffic |

The saving is not a smarter oracle. It is traffic no longer spent on ideas the company had
already disproven, engineering time no longer spent building tests that could not answer their
question, and PM time no longer spent rediscovering what the company knew.

**Why it works.** The company's own history is the model. Confidence is honest and re-scored
against real outcomes every month. Real tests close the loop, and the loop compounds per
customer. **Why it serves both worlds.** Dana keeps the veto, and her overrules are scored.
Her agents submit over the same interface, get the same three calls, and learn which of their
ideas keep dying. The ratio of human to agent submissions will flip within the year. The gate
will not change.

---

## 3. Competition: who generates, who gates

### 3.1 How the platforms generate hypotheses today

All four are LLM-generated. The failure is not hallucinated facts; it is unscored plausibility.

- **Optimizely Opal.** Agents over the customer's stack with retrieval. The Experiment
  Planning agent returns a text plan: hypothesis, variants, targeting, metrics, sizing, risks.
  Nothing scores whether the hypothesis is likely to win. Optimizely sits on ~173k experiments
  and has not built that score.
- **VWO Copilot.** Reads heatmaps and session recordings, finds friction, offers ideas you can
  "save as hypothesis". Ships an MCP server. The observation is real; the leap from "users
  hesitate here" to "this change fixes it" is the model's guess.
- **PostHog Max and background agents.** Reads event streams and replays, summarises sessions
  by variant, and now opens pull requests from product signals with a human approving.
  PostHog's own docs say its AI summaries are hypotheses to be checked against the numbers.
- **Statsig (inside OpenAI).** The least generation: feedback on a hypothesis you wrote, plus
  wrapping AI-generated code in flags and measuring it. The measurement rails, not the judge.
- **The autonomous claimants** (Pagent, Hell Yeah AI, the persona-simulation vendors at
  $2B valuations). Hypothesis, synthetic simulation, deploy, with 85–97% accuracy claims and
  no sealed numbers.

What every one of them emits is generic CRO folklore attached to a real observation: users drop
at step three, so simplify the form, add trust badges, move the button. Reasonable ideas, and
about seventy percent of them will test flat, because that is the base rate.

### 3.2 The three gaps none of them closes

1. **No memory of what the company already tried.** None cross-checks a new idea against the
   company's own past tests. That is the KILL half of the gate and the cheapest win in the
   system.
2. **No score on the hypothesis, and no grading of their own ideas against outcomes.** Every
   idea comes out sounding equally good. A PM with two hundred of them is no better off than
   with twenty.
3. **No abstention.** Nobody selling 85–97% can afford to say "we don't know", so they don't,
   and the counter-intuitive slice is exactly where they are confidently wrong.

### 3.3 The difference, stated precisely

Competitors claim accuracy. The claim we can own is stronger and none of them can make it
without our loop:

**Every verdict ships with its own scored track record, per customer, sealed, and "we don't
know" is a first-class answer.**

- **Calibration, not accuracy.** A stated ninety percent that is right nine times in ten on
  *this* customer's tests, re-scored monthly, ledger inspectable.
- **Abstention as a feature.** Routed to a real test, never dressed up as a prediction.
- **Evidence on every call.** KILL carries the past test; PASS carries the warehouse rows; the
  debrief cites the chat, session or agent log. No citation, marked as a guess.
- **Neutrality across generators.** Optimizely, VWO, PostHog and the coding agents all
  *generate*. The gate that arbitrates all of them on the customer's own evidence is a position
  no generator can hold, because each is selling its own ideas.

The paired corpus (hypothesis, verdict, real outcome) is what makes the first three checkable,
and it accrues only to whoever runs the loop. That is the moat, unchanged since July, now with
a reason for the volume to arrive.

### 3.4 Timing

Agents writing and merging code is mainstream (Razorpay merges thousands of agent PRs a month,
a third with no human; Stripe auto-merges low-risk changes). Agents choosing what to build from
product data has started, with a human approving (PostHog). Agents generating hypotheses and
variants is where the platforms are racing. No public evidence shows agents choosing *well*;
the evidence shows they choose prolifically and that human review is the bottleneck. That is
the condition under which a calibrated gate is worth paying for, and the window before the
platforms bundle a shallow version is the 12–18 months already named in the accuracy readout.

---

## 4. The product, built for agents first

The engine is AI-native; the current surface (wizard, dashboard, persona chat) is not. An
agent-native product is one where the agent is the first-class user and the console is a view
over what the agents did. Coding agents have CI for correctness. Nothing gives them CI for
user behaviour.

### 4.1 Five primitives, over MCP and REST

1. **Submit a hypothesis.** Structured contract: change, segment, metric, branch. Returns a
   verdict, a confidence, the evidence records, and a test spec on ABSTAIN or PASS.
2. **Run the test.** On the customer's platform, or on a lightweight assignment SDK we ship for
   companies that have none. Traffic budget enforced here.
3. **Get the result.** Webhook when the stopping rule fires, with guardrail status and the
   arm-tagged debrief, so the agent can plan the follow-up without a human reading a report.
4. **Search the archive.** Stroma's memory as a tool, so planning agents stop repeating known
   losers.
5. **Read your own score.** Every agent has an identity and a calibration record. A poor record
   loses traffic budget; a good one earns it.

### 4.2 What changes in how it is built and sold

- **Onboarding is programmatic.** Observer tag, scoped credentials, a key. The human sets
  policy once: traffic budget, guardrail metrics, which verdicts need a signature.
- **Discovery is where agents look.** MCP registries, coding-agent tool catalogs, an llms.txt.
  When a customer tells their coding agent "A/B test this", it should find Stroma the way it
  finds a linter.
- **Pricing is per call and per test**, on agent-friendly rails. The human console is free.
- **Many agents, one gate.** Coding, growth and CRO agents from different vendors all want
  traffic. Stroma brokers the shared resource.
- **Humans keep the veto**, and the veto is scored.

### 4.3 What does not change

Accuracy still comes from the customer's own history and real tests. The agent-native surface
does not fix cold start. Abstentions must never be hidden from a machine caller that will act
on the verdict without reading the caveats.

### 4.4 The observer, precisely

The installed observer replaces personas. "Learn" means a fitted behaviour model (per-segment
action propensities by page state, drop points, response to past changes), not a narrative
profile. The language model does perception of a new variant; the learned model does
propensity. It trains on the arm-tagged tests the gate routes to traffic, and it earns its vote
only by passing a sealed backtest on that customer's own tests. Cold start is a ladder: day
one, no vote; weeks one to four, segment shares and funnel rates, enough for the arithmetic
tier; after the first handful of tests, the backtest, then the vote. Runs inside the customer's
environment, stays small.

---

## 5. What we retire, what we keep

| Retire | Keep or flip |
|---|---|
| Personas as predictors; clustering pipeline; persona builder; 8B model; RFT; councils | Segment shares as transport weights and a breadth checklist |
| Page walkthroughs as text for agents to read | Agents acting on the real staged build, clickstream-seeded, gated by a sealed six-week experiment with a pre-registered kill criterion |
| Persona chat as a source of predictions | Chat as narrator of a grounded verdict and as the arm-tagged debrief, every answer citing a record |
| Wizard-first onboarding | Programmatic onboarding; console as a read view of the ledger |

---

## 6. Ninety days

1. MCP server with the five primitives on the existing verdict path, behind a flag.
2. Memory layer → experiment-archive extractor with an extraction-confidence field.
3. Hypothesis contract schema (the thing agents submit).
4. Assignment SDK and the first two platform integrations, so a test can start from a call.
5. Sealed per-customer backtest as the onboarding artifact.
6. The acting-agent experiment (E8), sealed.
7. Agent identity and calibration scores; self-serve keys; usage billing; registry listings.
8. One design partner with an experiment archive. Nothing here certifies without it.

---

## 7. Open items

- **Fold in the Slack discussion** (voyager-per3655 / C0C4D3G7ZFE / p1790294173280639). Not
  readable from the cloud session that drafted this; paste or summarise and this section
  becomes the reconciliation.
- Naming: Stroma is the product; "gate" and "memory" are the two parts. Decide whether either is a customer-facing name.
- Pricing unit: per hypothesis screened, per test run, or a traffic-budget subscription.

---

*Sources and the full evidence base: `founder-readout/accuracy-strategy-2026-09.md` (§1–§8
for the accuracy findings and external references; §9 for the agentic-pivot discussion and the
competitive sources).*
