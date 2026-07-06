# Why Sidira Beats the PM's Own Read of Their Data
### A founder's briefing — internalize this, and you can defend it against any skeptic · 2026-07-01

*The hardest question you'll get from a sharp investor, a Head of Growth, or a rival is:
"The customer already has the data and a smart PM. Why do they need you?" This doc is the
complete answer — the thesis, the four edges, the evidence, and a drill of the objections.*

---

## 0. The thesis in one breath

> **A PM brings the *mechanism* (a causal story) and an *optimistic bet on one metric*. We bring the
> *numbers that decide which way that story nets out* — the magnitudes, the de-confounding, and the
> breadth — that no human head can compute, plus an honest "we don't know, test it" where even the data
> can't answer. We don't out-*intuit* the PM. We out-*resolve* them, and we out-*honest* them.**

Say it even shorter when pressed: **the PM has the hypothesis; we have the verdict — and the humility.**

---

## 1. Steelman the PM first (or you'll lose the room)

Never win this argument by making the PM sound dumb. The credible version concedes everything true:

- The PM often knows the *mechanism* better than any model. They *proposed* "remove the skip cap to drive
  upgrades" because they already understand the cap is the nudge. **We do not claim to discover the story.**
- They have domain context, qualitative feel, and the data sitting in their warehouse.
- A good PM's directional hunch on an *easy* change is often right.

So the edge is **not** "we know their product better." Concede that. The edge is in the **three things a
smart, well-intentioned PM with their own data still cannot do** — because they're limits of the *human
head* and of *naive analysis*, not limits of *intelligence or effort*.

---

## 2. Edge #1 — Magnitude resolution of two-sided trade-offs

**The gap.** Most consequential changes cut both ways: a change *helps* through one mechanism and *hurts*
through another. The **net sign depends on the relative magnitudes** — how much each side moves. A human
feels *direction* ("this helps engagement, this hurts conversion") but cannot feel *size* well enough to
know which wins. Words can't carry it; intuition can't weigh it.

**Why the PM can't close it in their head.** "Removing the cap helps time-in-app but hurts upgrades" — is
the upgrade loss 0.5 points or 4 points? The answer lives in the data's actual response curves, not in
anyone's gut. This is the single most common way confident product bets quietly lose money.

**The evidence (our sharpest result).** We built a battery where two mechanisms oppose and the winner is
set purely by unstated magnitudes (the "AMBDOM" battery). On the clean magnitude-flip cells:

| method | accuracy on magnitude-flip cells |
|---|---|
| **Grounded sim (reads magnitudes from data)** | **1.00 (12/12)** |
| llama (LLM) | 0.00 |
| Opus (frontier LLM) | 0.50 (chance) |
| gpt-5.5 (frontier LLM) | 0.00 |

Not one words-only predictor — however smart — beats chance, because the deciding information isn't in the
description. The grounded g-formula, which reads the mediator strengths from the customer's own data, gets
**every one**. This is the wedge in a single table.

**One-line rebuttal.** *"On the changes that pull two ways, being smart doesn't help — you have to weigh
the magnitudes, and only the data has them. A PM feels the tug-of-war; we compute who wins it."*

---

## 3. Edge #2 — De-confounding (the naive read flips the sign)

**The gap.** The PM's instinct is to look at their data directly: "users who hit the cap upgrade more, so
the cap drives upgrades." That's a **correlation contaminated by who those users are** (heavy users both
hit caps *and* upgrade anyway). The human head — and the naive dashboard query — **cannot separate the
cause from the confounder.**

**Why it matters so much.** It doesn't just add noise; it **flips the sign**, making a loser look like a
big winner. That's the most dangerous failure mode in product analytics, and it's invisible to eyeballing.

**The evidence (real data).** On the Cookie Cats A/B (90,189 real players), inject a realistic selection on
engagement — the way a PM's naive read would be biased:

| read | estimated effect | correct? |
|---|---|---|
| **Naive comparison** (what the PM/dashboard sees) | **+22 pp** | **WRONG SIGN — loser looks like a huge winner** |
| **Causal adjustment** (what we do) | **−0.81 pp** | recovers the true **−0.82 pp** |

The naive number is not just off — it points the *opposite way*. Our causal method recovers the real,
counter-intuitive *negative*. (We got the *sign* right; the magnitude was ~40% off — which is exactly why
we sell direction, not a point estimate. See §7.)

**One-line rebuttal.** *"When the PM queries their own data, selection bias can flip the sign — the losing
change looks like the winner. We run the causal correction their dashboard doesn't, and it flips it back."*

---

## 4. Edge #3 — Killing the shared optimism (the CONTRADICTS catch)

**The gap.** The PM's hypothesis is **optimistic by construction** — they propose changes they *believe in*,
so their read under-weights the downside. And the obvious "just ask an AI" fallback shares a **degenerate
prior**: we measured that LLMs substitute a fixed prior for magnitude reasoning (llama leans "up," Opus
leans "down," gpt-5.5 abstains) — *none* reads the real trade-off. So both the human and the naive-AI err
toward their prior on exactly the hard calls.

**What we add.** The engine's whole value spikes at **CONTRADICTS**: the LLM (or the PM) says *ship it*, and
the data says *net-negative — here's the segment and the mechanism.* A tool that only ever agrees with the
PM is worthless; the product **is** the grounded disagreement, delivered with receipts they can inspect.

**The evidence.** In production blind tests the deployed persona-engine tracked *intuition*, not truth — it
predicted a business lift and was wrong on the business metric of every counter-intuitive case. That's the
optimism failure, measured. The grounded sim is the only arm that recovered the counter-intuitive *losses*.

**One-line rebuttal.** *"Everyone in the room — the PM, and any AI you'd bolt on — is optimistic on the very
bets that lose money. We're the one thing that will tell you 'this one loses,' and show you why in your own
data."*

---

## 5. Edge #4 — Breadth the PM never modeled

**The gap.** A PM's hypothesis is about *one effect on one metric*, from *one head* (usually a power user's).
Real changes ripple: they help one segment and hurt another, and they move **guardrail metrics the PM wasn't
aiming at**. The net can flip on the **segment mix** — a fact the modal-user story gets backwards.

**What we add.** We map the whole surface: "upgrades up — *but* retention down in casual, refunds up," plus
*which* segment and *which* mechanism. And across a 40-hypothesis backlog we rank **skip / test /
this-one-loses** — the triage that is the actual cost saving (which experiments they can safely *not* run).

**One-line rebuttal.** *"The PM gives you the headline; we give you the reaction of the users they aren't, on
the metrics they forgot — and an honest ranking of which tests to skip."*

---

## 6. The objection you must nail: "They have the data — why can't they just analyze it?"

This is the crux, and the honest answer is layered. They **can** in principle; in practice they **don't and
won't**, for five compounding reasons:

1. **The naive analysis flips the sign** (Edge #2). Getting it right needs causal tooling (negative controls,
   heterogeneity, g-formula) that a dashboard query doesn't do and most product teams don't run.
2. **The magnitudes aren't legible to intuition** (Edge #1). Even with the data on screen, a human can't
   weigh two opposing response curves in their head.
3. **They lack the negative-control discipline** — the check that says "I don't trust this, it might be
   confounded → abstain." Without it, they'll confidently ship the flipped-sign read.
4. **It's not their job or their time.** A PM has 40 ideas and no bandwidth to run a rigorous causal study
   on each. We turn a week of a data scientist's time into a verdict — and tell them which of the 40 even
   deserve it.
5. **They're motivated to confirm their own hypothesis** — the optimism prior (Edge #3). We're the
   disinterested party that says "no."

**The clean framing:** *We are the causal analysis they can't do in their head, won't do for every idea, and
are biased against doing honestly — plus the humility gate that refuses to guess when the data can't answer.*

---

## 7. The honesty moat — why "we don't know" is a feature, not a weakness

This is what wins the *technical* diligence, and it's counter-cultural, so internalize it:

- **We refuse to sell a crystal ball.** Where the mechanism isn't in the customer's data, we **abstain** —
  "test it" — instead of guessing. Every competitor selling AI user-simulation is shipping a
  confidently-wrong oracle; we did the negative work and know exactly where the answer holds.
- **We sell direction, never a calibrated number.** Our own Cookie Cats result got the *sign* right and the
  *magnitude ~40% wrong* — so we ship the sign + a confidence/abstain call, and keep magnitude backstage.
  Claiming the number would be the crystal ball we disproved. Saying so *is* the credibility.
- **The watchdog adjudicates everything.** A negative-control guard sits over every grounded answer:
  CONFIRMS / CONTRADICTS / CAN'T-VALIDATE. The data answers; the guard decides if we trust it.

A serious buyer trusts the vendor who shows them the boundary of their tool. A PM's overconfidence and a
rival's crystal ball both fail that test. **Our honesty is the moat.**

---

## 8. What we are NOT claiming (say this before they catch you)

Pre-empting the overclaim is how you win a skeptic's trust:

- **Not** that we predict the *magnitude* — only the direction, where the mechanism is in the data.
- **Not** that we call the *psychological long tail* — changes that work through a feeling with no proxy in
  the logs. There we abstain.
- **Not** that a bigger/smarter model fixes the hard cases — measured: three frontier models and an LLM
  council all fail the magnitude-flip slice. The bottleneck is **data, not model**.
- **Not** omniscience — some behavior is unpredictable in principle (the Fragile-Families result). We win by
  being accurate where behavior *is* predictable and honest where it isn't.

---

## 9. The evidence appendix (memorize the four receipts)

1. **AMBDOM** — grounded 1.00 vs every LLM at/below chance on magnitude-driven flips. *The wedge.*
2. **Cookie Cats (real, 90k users)** — naive **+22pp (wrong sign)** vs causal **−0.81pp** recovering true
   **−0.82pp**. *De-confounding on real data.*
3. **Hillstrom (real email RCT, 42k)** — causal recovers the true **+4.5pp** email lift where the naive read
   is contaminated. *The method generalizes.*
4. **Opus / gpt-5.5 / council re-tests** — frontier models and consensus *don't* crack the flip cells;
   council consensus was **0/12** (confidently wrong). *Robust to model strength — the moat is grounding.*

---

## 10. The objection drill (rehearse these until they're reflex)

**"Isn't this just A/B testing?"**
No — it's what lets you *skip* the A/B you'd otherwise run, and *audit* the ones you already won. We tell you
which tests are safe to skip, and which "wins" were actually confounded losers.

**"Can't their data scientist do this?"**
For one flagship study, maybe — in a week. We do it for the whole backlog, with a built-in confounding guard,
and an honest abstain. And most teams' default read is the naive one that flips the sign.

**"Why not just use GPT-5.5 / a council of models?"**
Measured and refuted. gpt-5.5 scores 0.00 on the magnitude-flip cells; an Opus+gpt-5.5 council agrees
*confidently wrong* 0/12. The information isn't in the words — no model or ensemble extracts it. Only the
data does.

**"Isn't the PM closer to the users?"**
Yes — and we use that. The LLM *translates the PM's mechanism*; the conversation lets them *talk to* the
grounded result. We don't replace their insight; we quantify it and stress-test it.

**"What about the cases you can't call?"**
We abstain and say "test it." That honesty is the point — and it's why you can trust the calls we *do* make.

**"How is this different from a causal-inference consultancy?"**
Speed, scale, and a product: real-time over a whole backlog, a reusable engine calibrated to *their* users
that gets better the longer they use it, and the conversational "why." Not a one-off report.

**"Why doesn't a company like DoorDash just build this themselves?"**
For the raw estimator, they can — and shouldn't. See §11: the engine is the 5%; the buy is the integration
surface, the trust engineering, the maintenance-forever, and the cross-customer calibration they can't get
from their data alone. And the right buyer isn't DoorDash's causal team — it's the 10,000 orgs that don't
have one, and the PMs inside big orgs who can't get DS time.

**"Isn't this just LLM+RAG on their own data?"**
No — RAG retrieves what's written down; the answer here has to be *computed* from raw behavior with a
confounding guard, and the deciding information (magnitudes) is provably *not* in any text (§8, §9). A RAG
demo is a weekend; a trustworthy, maintained, warehouse-wired decision engine is a team-forever.

**"What's the moat if the method is known?"**
Two things: honest calibration (knowing where it holds — the hard, un-sexy negative work nobody else does),
and a proprietary **data factory** (Senu) that manufactures the counter-intuitive labeled cases to keep
extending where the engine is trustworthy. The model isn't the moat; the calibration and the data are.

---

## 11. Build vs. buy — why they don't just build it themselves

The sharpest version of the DIY objection isn't "our PM can do the analysis" (§10) — it's *"our
engineers can build the whole **product**: an LLM+RAG on our own data plus an internal causal
platform."* Answer it honestly, because a hand-wave here loses the room.

**First, concede the premise — pick the right fight.** A company with a world-class experimentation
org (DoorDash publishes theirs, "Curie") *can* build the raw g-formula + negative-control layer, and
probably should. If our pitch is "we infer causal effects from your data," the build-vs-buy logic is
**weakest exactly at the top of the market.** Don't sell the engine there, and never anchor
defensibility on "they can't do causal inference." They can. The convincing case is about everything
*around* the estimator.

**The four reasons sophisticated companies buy what they could build:**

1. **It isn't their core advantage.** DoorDash's edge is logistics, not a feature-decision tool. Every
   eng-hour on a generic decision system is an hour off the thing that wins their market. *Could build ≠
   should build.*
2. **TCO is a team-forever, not a project.** The prototype is a weekend; the product is a permanent
   3–8 person team maintaining warehouse connectors, the product crawler, the capability→lever catalog,
   the persona pipeline, stats correctness, and UI as everything underneath drifts. Buying converts
   standing headcount into a line item.
3. **Trust/correctness engineering is specialized and rare.** Doing causal inference *right* — overlap
   diagnostics, negative controls, honest abstention — and stopping it from lying is exactly the skill
   most teams lack and can't retain. The hard part isn't the estimate; it's the discipline that keeps it
   from being confidently wrong (§7).
4. **Cross-customer data they can't get alone.** One company calibrates only on *its own* experiments.
   Across many customers + a ground-truth factory (Senu), we build a calibrated prior about which
   mechanisms transfer and which negative controls actually catch bias. That's a data network effect no
   single customer can replicate — *the bet we're proving, not yet a proven fact* (transfer across
   companies is the open question; if it holds we have a benchmark moat, if not we're a very good
   single-tenant tool — still a business).

**The Glean test (the objection, verbatim).** "DoorDash can just throw RAG on their docs" is *precisely*
the objection Glean faces and wins anyway: the RAG is ~5% of the product; the 95% is 100+ maintained
connectors, permission/ACL mirroring, freshness, ranking across heterogeneous sources, and continuous
upkeep as every API drifts. A RAG *demo* is a weekend; a company-wide RAG *system* rots in three months
without a dedicated team — on something that isn't the company's differentiator. The transferable lesson:
**the moat is almost never the model — it's the integration surface, the trust engineering, the
maintenance burden, and (best case) the cross-customer data.** That maps onto us cleanly: the causal
engine is our "RAG," and the real product is the maintained system around it.

**The tighter comp than Glean: Eppo / Statsig.** Warehouse-native experimentation products that companies
*with* data teams still buy — because building and *maintaining* a rigorous, trustworthy stats layer
(CUPED, sequential testing, guardrails) is a specialized, never-finished job that isn't their core. We're
the pre-experiment / decision-audit sibling of that category. (Amplitude/Mixpanel is the softer comp:
you *can* rebuild analytics on dbt+Looker — many do — but buy the productized workflow and speed.)

**The sharp version, in three lines:**
- **Buyer:** not DoorDash's causal team — the orgs that have data but *no* causal team, and the PMs
  inside big orgs who can't get DS time. Horizontal decision-support, not a DS-team replacement.
- **Un-buildable-alone part:** the cross-customer calibrated benchmark (Senu ground truth + accumulated
  predicted-vs-actual pairs).
- **The bet / risk:** that calibration *transfers* across companies. State it as the thesis, not a fact.

And the deepest reason of all: the durable product isn't a crystal ball — it's the disciplined,
calibrated, honestly-abstaining decision **audit** layer (§7). Most teams won't build *that*; it's
unglamorous and it says "I don't know." That's exactly what makes the answer trustworthy enough to act on.

---

*Ties to: `founder-readout/simulation-engine-where-we-landed.md` (the full state-of-play + runtime flow),
`sessions/watchdog-productization/GROUNDED_DECISION_ARCHITECTURE.md` (the build spec — this is its
positioning companion), the campaign memory `[[project-empirical-uplift-and-council-spike]]`, and the
watchdog-architecture epic (#538 and its sub-tickets #539–#546).*
