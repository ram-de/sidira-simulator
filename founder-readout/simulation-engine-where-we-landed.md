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
   confidently-wrong *net-negatives* that the LLM (and human intuition) never see.
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
| LLM persona **role-play** (agent "becomes" a user) | **0.29 — below chance.** The persona machinery actively *hurts* vs. a one-line comparison. |
| LLM **comparative / naive** one-shot | ~0.50 — at chance. |
| **Council of priors** (naive/contrarian/base-rate + router) | Rejected — made it *worse* (diversity ≠ accuracy). |
| **Decomposition, selective-prediction, reference-class** analogy | All NULL — at chance. Pre-registration killed two of my own favored bets. |
| **Empirical causal adjustment** on real data (Cookie Cats, Hillstrom) | **Works** on the estimable slice — recovers the true effect where the naive comparison flips. |
| **Negative-control guard** (catch hidden confounding) | LEAD on synthetic + one real RCT; **failed** on a hard real naturally-confounded benchmark → route forward is a stronger proximal method. Honest LEAD, not promoted. |
| **Grounded mediation simulation** (GNCE) | Ties the LLM when the mechanism is nameable; **abstains** honestly when the signal isn't in the data. |
| **Ambiguous-dominance battery** (AMBDOM) | **Grounded sim 1.00 vs LLM 0.00** on magnitude-driven flips. And the LLM scored **0.17 — it never once predicted a decline.** |
| **Design-partner production blind tests** | Engine tracks *intuition*, not truth — always predicts a business lift, wrong on the business metric of every counter-intuitive case. |

## 3. What died (say it plainly)

- **"AI simulates your users and predicts the outcome"** — the fundable-sounding pitch — is not real for
  the hard cases. No prompting trick rescues it. The binding constraint is **data, not model** (the same
  signature as the famous Fragile Families study, where the entire ML arsenal converged on a trivial
  baseline).
- **The LLM is structurally optimistic.** Given a change with both an upside and a downside, it reaches
  for "up" and never confidently says "this loses." That's not a tuning bug; it's a prior. It's exactly
  why it's dangerous as an oracle and exactly the gap our engine fills.

## 4. What survived (the three real assets)

1. **The empirical watchdog.** Where a customer's own data can answer the question, we *calculate* the
   effect with causal inference and a built-in check that says **"I don't trust this"** instead of
   guessing. Trustworthy where it speaks, silent where it can't.
2. **Grounded simulation on the magnitude-flip slice.** When a change helps one way and hurts another and
   the net depends on *how much*, words can't resolve it — but a model fit to the data can. We proved this
   decisively (1.00 vs 0.00) and confirmed it on a real dataset (recovering a famous counter-intuitive
   result the intuitive story gets backwards).
3. **The LLM front face.** It answers anything, decomposes a change into its mechanisms, and powers the
   conversational "why." It's the product's surface and coverage — just not its source of truth.

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

## 6. The moat and the data factory

Reading the Bridgewater × Thinking Machines result carefully: their win came from **a verifiable,
expert-labeled dataset** (the training trick was downstream). Our prediction task lacks that verifiable
reward at scale — each label costs a full A/B test. So the moat is to **manufacture it**: **Senu**, run as
a factory that deliberately produces *counter-intuitive* labeled cases, over-sampling the failure-mode
taxonomy (cannibalization, trade-down, substitution, novelty-decay, gross-vs-net, mix-flip, …).

Founder-endorsed **80/20:** ~80% of experiments fall into a small, finite, *recognizable* set of patterns;
~20% is an irreducible long tail we abstain on. The target is **not** global accuracy — it's a **growing,
trustworthy confident subset + a killed optimism bias**, because the cost savings come from the confident
skip/ship slice. Phase-1 is a lean ~₹20-lakh / 6-month program with a hard **month-4–5 decision gate**:
does the learning curve bend (new cases fall into seen patterns) and does the structure transfer? Scale on
evidence, not faith.

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
