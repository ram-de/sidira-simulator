# Founder Readout — The Simulation Engine: everything we explored, where we landed
### The state of play, 2026-06-30 · written to read on the road, honest about what died and what survived

---

## TL;DR (read this if nothing else)

We set out to build an engine that **simulates your users to predict what a product change will do.**
After months of rigorous, sealed, pre-registered testing, here is the honest landing:

1. **The original thesis is disproven by our own work.** LLM persona-simulation does **not** reliably
   predict which A/B arm wins — it's at or *below* a coin flip on exactly the counter-intuitive cases
   that matter. This is settled, measured many ways, and it's the same result the best-funded competitor
   is quietly ducking.
2. **Three things survived, and they're real:**
   - an **empirical "watchdog"** that's trustworthy where a customer's data can answer the question, and
     **honestly silent** where it can't;
   - **grounded simulation** that provably beats the LLM on the one regime that matters — trade-offs
     whose winner depends on *magnitudes* words can't convey;
   - the LLM as the **front face** — fluent answers, the "talk to your users / why" conversation, and a
     hypothesis generator.
3. **The product is the watchdog architecture:** the LLM answers everything up front; the empirical
   engine **confirms, overrules, or flags** it. The killer feature is **CONTRADICTS** — catching the
   confidently-wrong *net-negatives* that the LLM (and human intuition) never see. **Note this is the
   *target*: the deployed engine today is still the disproven persona role-play (§5d) — the rewiring is the
   roadmap, and being honest about that gap is part of the pitch.**
4. **The moat is not the LLM.** It's honest calibration + a proprietary **data factory** (Senu) that
   manufactures the counter-intuitive labeled cases nobody else has.
5. **The honest ceiling:** capture the predictable slice, abstain on the tail. Not a crystal ball —
   and saying so *is* the product, because everyone else is selling the crystal ball.

---

## 1. The question we set out to answer

*Can we predict the result of a product change — especially a novel or counter-intuitive one — without
running the full A/B test, by simulating user behavior?* If yes, we save customers enormous test budget
and time. The whole campaign was an honest attempt to find where that's true and where it isn't.

## 2. What we tested (the campaign, in one table)

Every method below was run **blind and sealed** (prediction fingerprinted before scoring), so we couldn't
fool ourselves.

| What we tried | Verdict |
|---|---|
| LLM persona **role-play** as the *predictor* (agent "becomes" a user and guesses the outcome) | **0.29 — below chance.** As a source of the verdict, the persona machinery actively *hurts* vs. a one-line comparison. (It survives only as the conversational "why" surface — never as the answer.) |
| LLM **comparative / naive** one-shot | ~0.50 — at chance. |
| **Council of priors** (naive/contrarian/base-rate + router) | Rejected — made it *worse* (diversity ≠ accuracy). |
| **Decomposition, selective-prediction, reference-class** analogy | All NULL — at chance. Pre-registration killed two of my own favored bets. |
| **Empirical causal adjustment** on real data (Cookie Cats, Hillstrom) | **Works** on the estimable slice — recovers the true effect where the naive comparison flips. |
| **Negative-control guard** (catch hidden confounding) | LEAD on synthetic + one real RCT; **failed** on a hard real naturally-confounded benchmark → route forward is a stronger proximal method. Honest LEAD, not promoted. |
| **Grounded mediation simulation** (GNCE) | Ties the LLM when the mechanism is nameable; **abstains** honestly when the signal isn't in the data. |
| **Ambiguous-dominance battery** (AMBDOM) | **Grounded sim 1.00 vs LLM 0.00 (llama) / 0.50 (Opus)** on magnitude-driven flips. No words-only predictor can beat chance here by construction; only the data-grounded sim recovers the flip. |
| **Opus vs llama re-test** (frontier-model swap on AMBDOM/GNCE) | A stronger model **does not** fix the sim on the hard slice: Opus sits **at chance (0.50)** on magnitude flips, grounded stays 1.00. It *does* fix llama's optimism — see §3. The wedge is robust to model strength. |
| **Design-partner production blind tests** | Engine tracks *intuition*, not truth — always predicts a business lift, wrong on the business metric of every counter-intuitive case. |

## 3. What died (say it plainly)

- **"AI simulates your users and predicts the outcome"** — the fundable-sounding pitch — is not real for
  the hard cases. No prompting trick rescues it. The binding constraint is **data, not model** (the same
  signature as the famous Fragile Families study, where the entire ML arsenal converged on a trivial
  baseline).
- **The LLM substitutes a degenerate prior for magnitude reasoning on ambiguous cases — and the
  *direction* of that prior is model-specific.** llama defaults to "up" (pro-feature optimism, never calls
  a decline); Opus defaults to "down" on the same ambiguous prose (a mirror-image constant-pessimism). Both
  land at/below chance on magnitude-driven flips because *neither is reading the magnitudes* — the
  information isn't in the words. The durable claim is **magnitude-blindness on the hard slice, robust to
  model strength**, not "always optimistic." (The production engine's *always-predicts-lift* behavior is a
  separate, real finding about the deployed persona-sim on its own model — don't conflate the two.) This is
  exactly why an LLM is dangerous as an oracle and exactly the gap the grounded sim fills.

## 4. What survived (the three real assets)

1. **The empirical watchdog.** Where a customer's own data can answer the question, we *calculate* the
   effect with causal inference and a built-in check that says **"I don't trust this"** instead of
   guessing. Trustworthy where it speaks, silent where it can't.
2. **Grounded simulation on the magnitude-flip slice.** When a change helps one way and hurts another and
   the net depends on *how much*, words can't resolve it — but a model fit to the data can. We proved this
   decisively (1.00 vs 0.00) and confirmed it on a real dataset (recovering a famous counter-intuitive
   result the intuitive story gets backwards).
3. **The LLM as translator (not storyteller).** Its reliable job is to **translate** a plain-English
   hypothesis into a *mechanism* — the observed lever the change moves, what it might cannibalize, the
   negative control, the confounders — and to power the conversational "why." It does **not** predict the
   outcome by role-playing users; that's the failed approach above. It sets up the computation; the data
   runs it.

## 5. Where we landed — the product

**The watchdog architecture.** Two engines run on every question:

- **LLM (front face)** — the fluent answer + the "talk to your users" conversation.
- **Empirical engine (watchdog)** — validates that answer against the real data and stamps it:
  **CONFIRMS** (ship it), **CONTRADICTS** (the LLM says ship, the data says net-negative — *the catch*),
  or **CAN'T VALIDATE** (no signal → flagged "test it," honest abstain).

Precedence: **trustworthy-empirical > LLM > untrustworthy-empirical (→ abstain).** The LLM is never the
final word alone; a low-trust data read never overrides with a worse guess.

**The sellable wedge, in one line:** *We catch the trade-offs where a winning-looking change quietly loses
money — the net-negatives your intuition and every other AI tool are blind to — and we tell you honestly
when we can't know.* This is **external-validity / generalization auditing of test wins**, powered by
heterogeneity + negative controls in the customer's own data — not persona theater.

## 5b. How the winning route actually works — four corrections worth pinning down

These sharpen (and in places correct) how we've described the engine to ourselves.

**(a) The LLM is a translator, not a predictor.** In the trustworthy route the LLM's only job is to turn
the plain-English hypothesis into a *mechanism*: which observed lever the change moves (the mediator), what
it might cannibalize (the sibling), what shouldn't move (the negative control), what to adjust for (the
confounders). It never guesses the answer by role-playing users — that's the disproven approach. It tells
the math what to compute; the data computes it. Persona role-play survives **only** as the conversational
"why" surface, anchored to that computed result — never as the verdict.

**(b) Two data objects, two jobs — don't conflate them.**
- **The crawled feature pack** is the **reverse-engineered current state of the product** — a PRD/Figma
  reconstructed from crawling the live app. Its job is to **ground the simulated agents in what the product
  is and does today**, so a proposed change reads as a *delta from a real baseline* rather than a generic
  one. It is read *by the agents as context*; it is **not** a regression table.
- **The feature store** (per-user behavioral rows) is the **numeric substrate the empirical estimate runs
  on** — mediators, confounders, segments for the causal computation and the negative-control guard.

  One grounds the agents' *understanding of the product*; the other grounds the *math about the users*.
  Earlier drafts blurred these; the crawl is current-state-for-agents, the feature store is
  behavior-for-the-estimate.

**(c) We compute magnitudes backstage; we ship *direction*.** The g-formula must weigh magnitudes to
resolve which way a two-sided change nets — but the deliverable is the **sign + a confidence/abstain
call**, never a calibrated point estimate. Our own data enforces this: on real Cookie Cats we recovered the
counter-intuitive *loss* (right sign) with the magnitude off by ~40%. Right sign, wrong number — so we sell
the sign and keep the number offstage. Claiming the number is the crystal ball we already disproved.

**(d) So how do we beat the PM's own hypothesis — without selling numbers?** A bare directional arrow on
the PM's *headline* metric does **not** beat a good PM; their hypothesis already is a directional bet. The
standout is that our output is **richer than an arrow yet not a forecast**:
- **Breadth they never modeled** — the reaction of the segments the PM isn't and can't intuit, and the
  direction on the **guardrail metrics they weren't aiming at** ("upgrades up — *but* retention down in
  casual, refunds up").
- **The contrarian catch** — the PM's hypothesis is optimistic *by construction*; our value spikes at
  **CONTRADICTS**, the grounded "this specific belief is the one that loses money, here's the segment and
  mechanism." A tool that only agrees is worthless.
- **Comparative + calibrated abstention** — across a 40-hypothesis backlog: *these* net-lose, *these* are
  safe-to-ship, *this* one is too close → test it. Ordinal, honest, and it's the actual cost saving (which
  tests to skip), with no calibrated magnitude claimed.
- **Interrogable "why"** — a hypothesis is a static sentence; ours is a model of current-state + change you
  can *talk to*, grounded in real reactions.

  One line: *the PM brings a confident, optimistic bet on one metric; we bring the reaction of the users
  they aren't, on the metrics they forgot, with an honest skip / test / this-one-loses — and the receipts
  to argue about it.* We out-breadth and out-honesty them; we don't out-precise them.

## 5c. Where the "user simulation" went, and how you still talk to the users

The USP is "simulate users and talk to them about *why*." That survives — but the *simulator* changed, and
being precise about it is what keeps us honest.

**The user simulation became statistical, not agentic.** In grounded mediation the g-formula, per **real**
user: (1) takes their actual features + observed mediator, (2) applies the mechanism shift the change
causes, (3) recomputes *their* outcome through a response surface **fit to real behavior**, (4) aggregates
to the population effect. So we *are* simulating each user's counterfactual response — but via a model fit
to real data, not an LLM pretending. The users are **real**; the reaction comes from **fitted real
behavior**. That's exactly why it's trustworthy where role-play (an LLM-imagined persona reacting from the
LLM's guess) was at/below chance.

**You still talk to them — the number comes first, then a persona agent narrates it.** After the g-formula
runs, each user/segment carries a record: real features + mechanism shift + computed counterfactual. You
"talk to" that by handing the record to an LLM agent that **speaks for the numbers** — same
translator-not-predictor principle, applied to the output ("numbers → a human *why*"). The agent explains
the result and the features behind it; it does not decide the outcome.

**The one rule that stops this collapsing back into the failed role-play:** does the question need an
*explanation* of the existing result, or a *new prediction*?
- Explanation / exploration ("why did this segment react? which feature drove it? who's most affected?") →
  the agent answers, grounded. ✓
- A *new outcome* ("what if we only lifted the cap for power users?") → that's a new counterfactual →
  **route back to the g-formula**; the chat agent never improvises the number.

**Talking to personas across both arms — still possible, with one honesty shift.** Three levels:
- **Persona/segment across both arms** — fully supported and trustworthy (observed arm = real; other arm =
  the segment-level counterfactual the sim is good at).
- **An individual in their actual arm** — fully grounded, real behavior.
- **The *same individual* across *both* arms** — this is the change. In role-play it was free because the
  agent was fictional; a *real* person only lived in one arm, so their other-arm self is a **per-person
  counterfactual: reliable in aggregate, a calibrated fiction per person.** Offer it, but label it
  honestly. (If the treatment arm was *really* run, both arms hold real — but *different* — people; only
  the cross-arm self is the estimate. For a genuinely novel change, everyone is control and the whole
  treatment side is the computed layer.)

The reframe: role-play's "same agent in both arms" felt powerful but was *doubly fictional* — a made-up
person having a made-up both-arm experience. The statistical version anchors one side in real behavior,
computes the other, and tells you which is which. We trade the *illusion* of per-person both-arm truth for
honesty about observed-vs-estimated — and the thing you actually wanted (how a segment shifts across arms)
gets *more* trustworthy.

## 5d. Is the *current* engine this? No — and the gap is the roadmap

Say this plainly: the **deployed** simulation engine today is the **LLM persona role-play** approach
(persona pack → identity prompt with the treatment state-diff → agents "become" users and produce the
outcome). That is the method the campaign **disproved**. Everything in §5–§5c is the **target** — validated
in research (AMBDOM/GNCE) but **not yet wired into the product.**

What already exists and is reusable:
- the **crawl** (current-state grounding) — reusable as-is;
- the **feature store** + persona builds — reusable as the numeric substrate;
- `causal_estimator.py` + the **negative-control guard** — live in research, not yet in the product path.

What the rewiring requires (the actual work): demote the LLM composer from *predictor* to *translator*,
promote the g-formula to *predictor*, put the negative-control guard in front of the answer as the *gate*,
and re-ground the "talk-to-users" conversation on **computed results** instead of role-play. Components
overlap; the *architecture* (who predicts, who translates, who guards) is different — and the default flow
in production is still the disproven one. Not hiding that is part of the pitch.

## 6. The moat and the data factory

Reading the Bridgewater × Thinking Machines result carefully: their win came from **a verifiable,
expert-labeled dataset** (the training trick was downstream). Our prediction task lacks that verifiable
reward at scale — each label costs a full A/B test. So the moat is to **manufacture it**: **Senu**, run as
a factory that deliberately produces *counter-intuitive* labeled cases, over-sampling the failure-mode
taxonomy (cannibalization, trade-down, substitution, novelty-decay, gross-vs-net, mix-flip, …).

Founder-endorsed **80/20:** ~80% of experiments fall into a small, finite, *recognizable* set of patterns;
~20% is an irreducible long tail we abstain on. The target is **not** global accuracy — it's a **growing,
trustworthy confident subset + a magnitude-blind spot closed** (the grounded sim resolves the trade-offs no
LLM — optimistic *or* pessimistic — can), because the cost savings come from the confident skip/ship slice. Phase-1 is a lean ~₹20-lakh / 6-month program with a hard **month-4–5 decision gate**:
does the learning curve bend (new cases fall into seen patterns) and does the structure transfer? Scale on
evidence, not faith.

## 6b. Can Senu data build an agentic simulator — and how would we use it?

**Can it? Yes — Senu is precisely the data that makes an agentic *and trustworthy* simulator buildable.**
Role-play failed not for lack of chat examples but because it was **optimistic and unanchored**. Senu
attacks that directly: it manufactures **(population → change → measured outcome)** triples at ~₹40/
respondent and over-samples the counter-intuitive tail. A model fit to those outcomes keeps the **agentic
interface** (you talk to it, it behaves like a user) while the **trust** now comes from *"fit to real
outcomes,"* not role-play magic. The genuinely new capability is **transfer**: unlike the per-customer
g-formula (which needs the mechanism observed in *this* customer's data), a Senu-trained model carries
learned behavioral physics *across* customers — it can simulate a change where a customer's own data is
thin. Transfer is the upside *and* the external-validity risk (Senu respondents ≠ the customer's users), so
it must be validated, not assumed.

**How we'd use the data — the sequence (cheap → expensive, each gated on the last):**

1. **Fit a supervised response model on the triples. No LLM training.** The data is tabular, so the honest
   first build is plain ML (gradient-boosted trees / small net) mapping `(features, change-encoding,
   mechanism) → outcome` — a **learned, transferable g-formula.** It directly answers the open question:
   *does a model trained on Senu outcomes beat the plain per-customer g-formula?* Start here; if the signal
   isn't in this, no LLM training rescues it.
2. **Keep a frontier LLM *untrained* as translator + narrator.** It encodes the change (English/Figma →
   mechanism + features — where world-knowledge enables transfer to *unseen* change-types) and narrates the
   computed result in the conversation. No training needed.
3. **Only then RL-fine-tune an open model against measured outcomes** (Bridgewater recipe: reward = match
   to the real Senu outcome, on a Qwen-class model). This yields the single **agentic** model that both
   encodes and predicts, de-biased by reality. Expensive — gate it on Step 1 showing learnable signal.

**Why *not* "just SFT a base LLM on the datasets" (the natural instinct):** there's no signal in the text —
SFT teaches it to *mimic the wording* of outcomes, not predict them, and can re-learn the optimism bias.
Bridgewater's win was **RL against a verifiable reward**, not text fine-tuning. If you train an LLM at all,
it must be RL-against-measured-outcome.

**Discipline (all three steps):** general base (Senu physics) + per-customer head (their exhaust) = the
flywheel; sealed held-out validation on the real RCTs, promote a checkpoint only when held-out accuracy
improves; the negative-control **watchdog stays** — it adjudicates and forces abstain off-distribution.

**Three caveats that decide if it's real:** (1) the calibrated-fiction ceiling doesn't move — trustworthy
at segment level, fiction per person; (2) it *shrinks* the abstain zone, doesn't close it (off-taxonomy →
abstain); (3) the whole bet rides on the 80/20 taxonomy being real — the **month-4–5 learning-curve gate**
is the thing to measure, not assume. And it must *beat the plain g-formula* to justify its cost — an open,
testable question, not a foregone win. (Full treatment in `founder-readout/finetuned-simulator-readout.md`.)

## 7. The honest limits (the part a serious buyer will respect)

- The watchdog's confounding-guard is a **LEAD, not promoted** — it failed a hard real benchmark; the
  stronger method (proximal / double negative-control) is the route, not yet shipped.
- Grounded simulation is an **existence proof** (synthetic + n=1 real); we haven't yet found naturally
  ambiguous *real* data with a true dominance flip to promote it.
- Even with infinite data, some behavior is unpredictable in principle. We win by being **accurate where
  behavior is predictable and honest where it isn't.**

---

## 8. YC readiness — a candid rating (deadline in 4 weeks)

**Overall: ~6.5 / 10 today for an interview; materially movable to ~7.5 in four weeks.** YC is
high-variance (~1% acceptance) — even strong companies get passed. Here's the honest breakdown and what
moves the needle.

| Dimension YC weighs | Score | Why |
|---|---|---|
| **Founders / team** | **8.5** | Ex-DoorDash operator; rare intellectual honesty; ships real infra. This is the strongest card. |
| **Insight / "why now"** | **8** | A genuine contrarian secret: *everyone selling AI user-simulation is shipping a confidently-wrong crystal ball; we did the negative work and found where it actually holds.* Why-now = frontier LLMs plateauing + a flood of un-validated sim tools. |
| **Product / tech** | **7** | Real, shipped, deployed. But the flagship capability is disproven and the survivor (the watchdog) is a LEAD, not a promoted product yet. |
| **Clarity of thinking** | **9** | This campaign is a masterclass. *Double-edged* — it can read as a research project, not a startup. |
| **Market / willingness-to-pay** | **5.5** | Real pain (wasted test budget), but the buyer and price are unproven; "audit your test wins" risks sounding like a vitamin. |
| **Traction / pull** | **3.5** | **The weak spot.** One design partner doing blind tests; no clear paid pilot / LOI / revenue. YC funds *pull*. |

**The narrative decision (get this right or nothing else matters).** Do **not** lead with the disproven
"AI simulates your users" pitch — any technical diligence collapses it and it reads as naïve. **Lead with
the earned insight:** *"Every AI-simulation tool is confidently wrong on exactly the decisions that cost
the most — we can prove it, and we built the only engine that knows when to shut up and catches the losers
you'd have shipped."* That is the contrarian-insight-plus-honesty story YC actually rewards — *if* paired
with evidence of pull.

**The 4-week plan (in priority order):**

1. **Manufacture traction — this is 70% of your delta.** Convert the design partner into a **paid pilot or
   a signed LOI**, and line up **2–3 more design partners** (or a credible waitlist). One sentence of "a
   $Xb company is paying us to audit their test wins" beats every slide.
2. **Build the 60-second "CONTRADICTS" demo.** A real (or realistic) case where the LLM says *ship* and
   the watchdog overrules it with the data and saves a bad launch. That single moment *is* the pitch.
3. **Sharpen the wedge to a knife.** One sentence, one buyer (Head of Growth / Experimentation), one
   before/after ROI number ("teams skip ~40% of tests they'd otherwise run"). Kill the ambiguity about
   what you sell.
4. **Own the honesty as a strength, not a hedge.** Frame the abstain + the negative results as *why you're
   trustworthy* and *why you'll win the diligence* competitors fail. Rigor is your moat; sell it.
5. **Application + video:** founder-forward, insight-forward, traction-forward. Show the DoorDash operating
   instinct and the one contrarian sentence in the first 20 seconds.

**Bottom line:** the founder and the insight are top-decile; the gap is **commercial pull and a crystal-
clear "who pays and why now."** Four weeks is enough to move from "interesting research with a great
founder" to "great founder with a sharp wedge and early pull" — and that second company gets the interview
*and* has a real shot at the offer. The single highest-leverage action is a **paid pilot / LOI in hand by
application day.**

---

*Ties to: the campaign memory [[project-empirical-uplift-and-council-spike]], the watchdog mock, the
fine-tune readout (`founder-readout/finetuned-simulator-readout.md`), the engine-strength readout
(`founder-readout/README.md`), and the open tickets #511 (router), #521 (external-validity wedge),
#534–#537 (data factory + fine-tune experiments).*
