# Stroma — the gate every agent calls before a change reaches users

### 2026-09-25 · founder readout

Agents now propose and build most product changes, at a volume no team can test, and the real
problem underneath is that learning is slow and expensive. Stroma is the agent at your company
that knows what the company has learned, knows what it has not, and is constantly trying to
learn it. It kills ideas the company's own history already disproves, passes what its own data
supports, says "we don't know" on the rest and routes them to a real test, and proposes what
the company should learn next. Every real test makes it sharper for that customer, which
nobody else can copy.

## What Stroma does

Stroma sits one step before the experimentation platform. It does not build the product and it
does not run the experiment. It decides which ideas deserve real traffic, on evidence, and
hands validated tests to Optimizely, Statsig, PostHog or VWO through connectors.

Every idea enters as a structured hypothesis: what changes, for whom, which metric should move,
and why. Stroma makes one of four calls.

| Call | When | What the caller gets |
| --- | --- | --- |
| KILL | The company's own history already disproves it | The past test that answers it, attached |
| PASS | The company's own data and past results line up behind it | The evidence rows, plus guardrail metrics to track |
| ABSTAIN | Nothing in the company's history answers it | An honest "we don't know", a shaped test (metric, traffic, stopping rule), and a hand-off to the platform |
| LEARN | A driver in the company's metrics tree has never been measured | A proposed experiment, ranked by the value of knowing the answer |

Stroma also runs the other direction. Decisions the company already made without a test are
scored the same way, and the ones resting on nothing become LEARN proposals.

Every confidence number is calibrated: a stated ninety percent is right nine times in ten on
that customer's own tests, re-scored every month against real outcomes. Every call cites a
record. A call without one is marked as a guess.

## Meridian Home: one year with Stroma

Meridian is a mid-size online furniture store. Its product manager, Dana, works with a planning
agent that proposes changes and a coding agent that builds them.

**Month zero: the install.** Stroma connects to Slack, Notion, the support desk and the
warehouse and starts reading. It drops a small observer into the storefront and connects to
Meridian's experimentation platform. By the end of the week it has found eleven past A/B tests
scattered across old decks and threads, with results, and written them into Meridian's
experiment archive. Nobody remembered more than four. The observer starts learning the shape
of Meridian's traffic. It does not vote on anything yet.

**Month one: two hundred ideas a week.** Ideas arrive by the dozen, many as ready branches.
Each one enters Stroma as a structured hypothesis.

- An agent proposes hiding the estimated delivery date to clean up the product page. Two years
  ago Meridian tested hiding delivery information and conversion dropped. **KILL**, past test
  attached. Sixty of the two hundred die this way in the first month, at no cost.
- An agent proposes a first-visitor discount banner. First-time visitors are forty percent of
  traffic with low conversion, and three past discount tests all lifted conversion and hurt
  margin. **PASS**, with margin added as a guardrail metric.
- An agent proposes moving the mobile add-to-cart button above the fold. Nothing in the
  archive; layout changes are small and hard to predict. **ABSTAIN**. Stroma sizes the test,
  sets the stopping rule and hands it to the platform. The branch already exists, so the test
  starts the next morning instead of waiting for a sprint.

**Month two: the debrief.** The button test ends. Dana used to get a number and a shrug. Now
she asks Meridian's own working agents, each reading records tagged by test arm. The support
agent: thirty-one treatment chats complained about missing fabric swatches, links attached.
The analytics agent: product-to-cart rose, cart-to-checkout fell, mostly on small screens.
Three agent-driven shoppers that abandoned in the treatment arm are asked why, and answer that
the delivery estimate was hidden under the new button. Every answer cites a record. The result
and the debrief are written to the archive automatically. Nobody files a report.

**Month three: what Meridian should learn next.** Stroma holds Meridian's metrics tree and
knows which drivers have been measured and which have not. Delivery-fee sensitivity by channel
sits under the biggest unexplained node in revenue, and no test has ever touched it. Stroma
proposes the experiment itself: the lever, the segments, the metric, the traffic it needs, and
the decision it will unlock. **LEARN** turns "what should we do next" from an opinion into a
plan backed by a result.

**Month six: the observer earns its vote.** After nine arm-tagged tests, the observer has
watched real Meridian users react to real changes. Stroma runs a sealed backtest: the observer
predicts those nine tests blind and beats the baseline. Only now does it take part in
screening, walking new variants on the staged build with Meridian's real behaviour. If it
drifts, it loses the vote until it recalibrates.

**Month twelve: what Dana shows the CFO.** The test slots did not increase. What went into them
changed.

| Before | After |
| --- | --- |
| Twenty ideas a quarter, five tested, chosen by gut | Two hundred a week, sixty percent killed or passed on evidence, the rest tested |
| Two weeks from idea to test start | One day, because the branch exists before the decision |
| One in three tests underpowered or measuring the wrong thing | Tests shaped before launch, guardrails attached |
| Results in decks, forgotten within a quarter | Every result and debrief in the archive, feeding the next call |
| Losers found only after burning traffic | Known losers never reach traffic |

The saving is real, but it is not the pitch. The pitch is learning velocity. Meridian now
learns more true things about its customers per quarter than a competitor with the same
traffic, and every quarter the gap widens. Without Stroma, you lose to the company that runs it.

Dana keeps the veto, and her overrules are scored. Her agents submit over the same interface,
get the same four calls, and learn which of their ideas keep dying. Within the year the ratio
of human to agent submissions flips. Stroma does not change.

## Why this works: what predicts real experiment outcomes

Accuracy on real A/B tests depends on whether the deciding quantities are in the inputs. It
does not depend on the model, the persona machinery or the prompt. That single finding,
confirmed across our own sealed studies and the strongest published results of 2026, is the
foundation of the product.

| Method | What it reads | Directional accuracy on real tests |
| --- | --- | --- |
| Synthetic personas role-playing over a description of the page | Text | 0.29, and richer personas do not help |
| A frontier model asked directly | Text | 0.50, the same as a coin |
| Multi-model councils | Text | Worse than one model; wrong on the surprises exactly when the models agree |
| A frontier judge on 330 real product tests (external, 2026) | Text | Near chance; no prompt, model or stimulus lever helped; "always pick B" beat it |
| Digital twins of individual people (external, 2026) | Person profile | r ≈ 0.2 per person |
| Arithmetic over the company's own aggregate tables | Warehouse rows | 24 of 24 |
| Grounded simulation with the company's lever map and a negative-control check | Warehouse rows | 12 of 12 where the model alone scored 0.00 to 0.50 |
| Agents acting on the live product, seeded from real clickstream, calibrated on a pre-period (Shopify, Amazon, 2026) | Real behaviour on the real page | 0.70 to 0.77, on small samples |

Three consequences follow.

1. **Predicting the outcome of a new idea from its description is not a talent or model gap.**
   Teams at Amazon, Spotify and Microsoft are larger than any seed round buys, and none is
   above chance on it. The information is not in the text.
2. **What works is getting the company's own quantities into the system.** Past tests,
   warehouse tables, real behaviour. Stroma's memory layer reads exactly the places that data
   already lives.
3. **Saying "we don't know" is the product's strongest capability, not its weakness.** In a
   world of five test slots a quarter, abstaining looked like failure. In a world of two hundred
   agent-generated ideas a week, an honest abstention that routes to a cheap real test is the
   whole job. The hard part, guessing a genuinely new idea's outcome, moves to the real
   experiment.

The observer that learns each customer's users is built on the one method above that does
work on new ideas: agents acting on the real build, seeded from real behaviour. It learns a
fitted behaviour model per segment, not a narrative profile, trains on the arm-tagged tests
Stroma routes to traffic, and earns its vote only by passing a sealed backtest on that
customer's own tests.

## What makes it defensible

Every competitor claims accuracy. Stroma makes a stronger claim that none of them can make:
**every verdict ships with its own scored track record, per customer, sealed, and "we don't
know" is a first-class answer.**

- **Calibration, not a headline number.** A stated ninety percent that is right nine times in
  ten on this customer's tests, re-scored monthly, with the ledger open for inspection. A
  percentage from a vendor's private benchmark is not that.
- **Abstention as a feature.** Routed to a real test, never dressed up as a prediction. Nobody
  selling 85 to 97 percent can afford to say "we don't know", so they don't, and the
  counter-intuitive ideas are exactly where they are confidently wrong.
- **Evidence on every call.** KILL carries the past test. PASS carries the warehouse rows. The
  debrief cites the chat, the session or the agent's action log. No citation, marked as a guess.
- **Neutrality across generators.** Optimizely, VWO, PostHog and the coding agents all generate
  ideas. The gate that arbitrates all of them on the customer's own evidence is a position no
  generator can hold, because each is selling its own ideas.

Underneath all four is the paired record of hypothesis, verdict and real outcome that Stroma
writes on every test. It is what makes the calibration checkable, and it accrues only to
whoever runs the loop. A competitor can copy the method in a quarter. It cannot copy a
customer's year of results.

## The market: who generates ideas, who gates them

Agents writing and merging code is mainstream. Razorpay's internal agent system merges
thousands of pull requests a month, over a third with no human in the loop, and Stripe
auto-merges low-risk changes. Agents choosing what to build from product data has started,
with a human approving: PostHog's background agents watch for errors, frustration and
feedback, write the fix and open a pull request. Agents generating hypotheses and test
variants is where the experimentation platforms are racing.

| Vendor | What it generates | What it does not do |
| --- | --- | --- |
| Optimizely Opal | Agents over the customer's stack; an experiment-planning agent returns hypothesis, variants, targeting, metrics and sizing as text | Scores no hypothesis against outcomes, despite an archive of about 173,000 experiments |
| VWO Copilot | Ideas from heatmaps and session recordings; an MCP server for agents | Never checks a new idea against the company's own past tests |
| PostHog | Session summaries by variant; background agents that open pull requests from product signals | Its own docs call its AI summaries hypotheses to be checked against the numbers |
| Statsig (inside OpenAI) | Feedback on a hypothesis you wrote; flags and measurement for AI-generated code | The rails, not the judge |
| Autonomous claimants (Pagent, Hell Yeah AI, the persona-simulation vendors) | Hypothesis, synthetic simulation and deploy, with 85 to 97 percent accuracy claims | No sealed numbers, no abstention |

All of them generate with a language model reading real data. The failure is not invented
facts. It is unscored plausibility: generic conversion folklore attached to a real
observation, every idea sounding equally good, and about seventy percent of them testing flat,
because that is the base rate. None of the four platforms remembers what the company already
tried, scores its own ideas against outcomes, or says "we don't know".

No public evidence shows agents choosing what to build well. The evidence shows they choose
prolifically and that human review is the bottleneck. That is the condition under which a
calibrated gate is worth paying for, and the window before the platforms bundle a shallow
version is twelve to eighteen months.

Sources: [Masters Union on agents in production](https://mastersunion.org/blog/ai-agents-are-writing-production-code-heres-what-that-changes-for-engineers),
[PostHog AI products](https://posthog.com/handbook/engineering/ai/products),
[PostHog session summaries](https://posthog.com/docs/posthog-ai/session-summaries),
[Optimizely Experiment Planning agent](https://support.optimizely.com/hc/en-us/articles/39805144467981-Experiment-Planning-agent),
[VWO Copilot](https://vwo.com/product-updates/vwo-copilot-ai-powered-optimization/),
[Statsig AI features](https://www.statsig.com/blog/statsig-ai-features),
[Humblytics ranking of AI A/B tools](https://humblytics.com/blog/best-ai-ab-testing-tools).

## Built for agents

Coding agents have continuous integration for correctness. Nothing gives them the same for
user behaviour. Stroma is that check: the gate every agent calls before a change reaches
users. The agent is the first-class user, and the human console is a view over what the agents
did.

Six primitives, exposed as an MCP server and a REST API:

1. **Submit a hypothesis.** A structured contract: change, segment, metric, branch. Returns a
   verdict, a confidence, the evidence records, and a test spec on ABSTAIN or PASS.
2. **Run the test.** On the customer's platform through a connector, or on a lightweight
   assignment kit for companies with none. Traffic budget is enforced here.
3. **Get the result.** A webhook when the stopping rule fires, with guardrail status and the
   arm-tagged debrief, so the agent can plan the follow-up without a human reading a report.
4. **Search the archive.** The company's experiment memory as a tool, so planning agents stop
   repeating known losers.
5. **Read your own score.** Every agent has an identity and a calibration record. A poor record
   loses traffic budget; a good one earns it.
6. **Ask what to learn next.** The unmeasured drivers in the company's metrics tree, ranked by
   the value of knowing, each with a proposed experiment. Planning agents call this before they
   generate anything.

How it is sold:

- **Onboarding is programmatic.** An observer tag, scoped credentials, a key. The human sets
  policy once: traffic budget, guardrail metrics, and which verdicts need a signature.
- **Discovery is where agents look.** MCP registries, coding-agent tool catalogs, an llms.txt.
  When a customer tells their coding agent "A/B test this", it finds Stroma the way it finds a
  linter.
- **Pricing is per call and per test.** The human console is free.
- **Many agents, one gate.** Coding, growth and CRO agents from different vendors all want
  traffic. Stroma brokers the shared resource.
- **Humans keep the veto**, and the veto is scored.
- **Stroma builds neither the platform nor the product.** Validated tests go to the customer's
  experimentation platform. Agents connect to Stroma to learn what to build and build it
  elsewhere.

The pitch is the experimentation case, because it is the most compelling story and the one
with hard results behind every "what next". The vision is wider: the same loop works in any
function where data and knowledge are used, and the functions least served by experimentation
today will be the most impressed by it.

## What we are building next

1. The MCP server with the six primitives, on the existing verdict engine.
2. The memory-to-archive extractor that finds a company's past experiments in its docs, chat
   and dashboards, with a confidence field on every extracted result.
3. The hypothesis contract: the structured object agents submit.
4. The assignment kit and the first two platform connectors, so a test can start from a single
   call.
5. A sealed backtest on each customer's own history as the onboarding artifact.
6. The observer, validated under seal on real tests before it earns a vote.
7. Agent identity and calibration scores, self-serve keys, usage billing, registry listings.
8. One design partner with an experiment archive, and an experimentation-platform veteran on
   the team.

Stroma does not just preserve what the company has learned. It identifies what the company
should learn next, helps design the experiments to learn it, and makes the result available
everywhere it matters.
