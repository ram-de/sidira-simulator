# Founder Readout — Making the Simulation Engine Stronger
### The "engine-strength" campaign, 2026-06-28

*Written to be read on the road. Plain language, concrete examples, honest about limits.*

---

## TL;DR (read this if nothing else)

We've been asking: **can Sidira predict the result of a product change without guessing?**
For the slice of changes where the answer lives in a customer's own data, the answer is **yes** —
and this campaign found the missing safety piece that makes it trustworthy.

The win, in one line: **we now have a way for the engine to know when it's about to be wrong, and
say "I don't know" instead of confidently guessing.** That "I don't know" is what routes a question
over to the LLM. Before this, the engine had no honest way to tell a real answer from a confident
mistake.

We proved it over **6 careful experiments** (each one sealed and graded blind, so we couldn't fool
ourselves), including a test on **real-world data** (a public email-marketing experiment with 42,693
customers). The method held up, including an adversarial stress test.

It is a **strong lead, not a finished product.** It needs to be wired into the live system and tried
on a real customer before we call it done. Details and honest caveats below.

---

## 1. The two ways Sidira can answer a question

When a customer asks *"will this product change help?"*, there are two engines that could answer:

**A) The LLM engine (what we have today).** We describe the change and the users to a large language
model, and it reasons about what people will do. It's flexible — it can take a swing at *any*
question. But it's essentially an educated guess, and our earlier testing showed that on hard,
counter-intuitive cases it does **no better than a coin flip**. It doesn't *know*; it *guesses*.

**B) The empirical engine (the one this work is about).** If the customer's own data already contains
the answer, we can **calculate** the effect directly — no guessing, no LLM. This only works for some
questions, but where it works, it's grounded in real numbers.

The product idea is a **router**: for each question, decide *"can we calculate this from their data?"*
If yes → use the empirical engine (trustworthy). If no → fall back to the LLM (flexible but a guess).

---

## 2. How the empirical engine works — a simple example

Say **a food-delivery app** is the customer and they ask:

> *"If we show customers a 'group order' button, will more of them place an order this week?"*

The empirical engine doesn't ask an AI what it thinks. It looks at the customer's own data, where some
users already saw the button and some didn't, and **compares them**. Each user is one row:
*did they see the button? did they order? plus everything we know about them (how often they order,
city, app version, etc.).*

Sounds easy — just compare the two groups. **The catch is "confounding."** Here's the trap:

> The users who saw the new button first were the app's **power users** (the company rolled it out to
> their most active customers). Power users order a lot *anyway*. So if you just compare "saw button"
> vs "didn't," the button looks amazing — but you're really just seeing that power users order more.
> The button might have done nothing.

The empirical engine corrects for this. It uses standard causal-inference math (the same tools used in
medicine and economics) to **compare like-with-like** — power users who saw the button against power
users who didn't, casual users against casual users — and then combine. That correction is the whole
value: it turns a misleading raw comparison into an honest estimate.

**We proved this part works on real data**, twice, earlier in this project:
- A mobile game's A/B test (90,189 players): we deliberately poisoned the data with confounding. The
  naive comparison gave the **wrong winner** (+22 points the wrong way). The corrected estimate
  recovered the **true answer** almost exactly.
- An email-marketing experiment (42,693 customers): the corrected estimate matched the real measured
  lift (+4.5%) closely.

---

## 3. The problem this campaign set out to fix

The correction in section 2 only works if **all the important confounders are in the data.** What if
something we *can't see* drove who got the change?

Example: imagine the real reason some users saw the "group order" button wasn't power-user
status (which we can measure) but a hidden marketing campaign in certain neighborhoods that we have no
record of. Our correction can only adjust for what it can see. The hidden cause sails right through,
and the engine produces a **confident, wrong** answer.

The scary part we discovered in **experiment 0**: the engine's existing confidence signal **completely
missed this.** We gave it 10 datasets, 3 of which were rigged with hidden confounding. It got those 3
wrong — and reported **"high confidence" on all 3.** It had no idea it was wrong. A tool that's
confidently wrong and can't tell is worse than useless; it's dangerous.

So the campaign's mission became: **give the engine a way to detect "there's something hidden here —
don't trust this answer."**

---

## 4. The discovery: the "negative-control" check

Here's the idea, by analogy:

> You're testing whether a new heater warms a room. You put a thermometer in the room — it reads
> warmer. Great? Not so fast. You also place a second thermometer **inside a sealed fridge across the
> hall**, where the heater *cannot possibly* reach. If that fridge thermometer *also* reads warmer,
> then something other than your heater is warming the whole building — and your "the heater works"
> reading is contaminated. You should distrust it.

The fridge thermometer is a **negative control**: a measurement that *should not move* if everything is
clean. If it moves, you know there's a hidden influence messing with your real measurement.

**For this example:** to check the "group order" button result, we also measure its "effect" on something
the button *couldn't* have caused — say, **whether the user opened the billing/settings page**, which
has nothing to do with group orders. If the button *also* appears to "boost" billing-page visits, then
the group that saw the button was simply **more active overall** to begin with — so the retention boost
is partly an illusion. The engine then says **"I can't trust this — route to the LLM."**

That's the whole discovery. A metric that *shouldn't* react becomes an alarm bell for hidden
confounding that the normal checks can't see.

---

## 5. The 6 experiments, as a story

Every experiment was **pre-registered and sealed** before running (we wrote down our prediction, locked
it with a cryptographic fingerprint, *then* ran it and graded blind) — so we could not move the goalposts
or fool ourselves. This is the same discipline we use across the accuracy work.

| # | What we tried | What happened |
|---|---|---|
| **0** | Test the engine's existing confidence on 10 datasets | **The alarm.** It got 3 wrong and was "highly confident" on all 3. Found the danger. |
| **1** | First version of the negative-control check | **Half worked.** It caught the hidden problems — but was too twitchy and also flagged good answers. We did *not* fudge the dial; we logged it as a fail. |
| **2** | Tuned the sensitivity, tested on **brand-new** data | **First real win.** Caught every hidden-confounding case, zero false alarms. |
| **3** | Tested it on a **real public experiment** (Hillstrom email, 42,693 people) + stress test | **Held up.** 100% specificity (never cried wolf on the genuine experiment); caught the hidden bias when we injected it. The setting we learned on fake data transferred to real data unchanged. |
| **4** | Use **several** negative controls at once, not just one | **Made it sturdier.** A single weak control can miss the problem; using a few and trusting the loudest alarm fixed that with no downside. |
| **5** | Close the last hole: telling a **true zero** ("the change did nothing") apart from a real effect | **Closed it.** New rule: only trust the result if the real effect is clearly *bigger* than the bias the controls reveal. Otherwise say "I can't tell" and route to the LLM. |

Net result: a **complete, 3-part safety gate** on the empirical engine. It abstains when (1) a control
shows hidden confounding, (2) several controls agree something's off, or (3) the effect is too small to
separate from the noise. When it *doesn't* abstain, we have real evidence the answer is trustworthy.

---

## 6. Why this matters for the product

- It turns the empirical engine from *"fast but occasionally confidently wrong"* into *"trustworthy
  where it speaks, honest where it can't."* That honesty is exactly what makes the **router** viable —
  the engine now has a principled way to say *"this one's not for me, send it to the LLM."*
- It's a **selling point, not just an internal fix**: we can tell a customer *"when our empirical engine
  gives you an answer, here's the built-in check that proves it isn't an artifact of your data."*
- It reuses what we already build: the negative controls are just **other metrics in the customer's
  feature store** — no new data collection.

---

## 7. Honest limits (please read — this is not finished)

1. **It's a strong lead, not "promoted."** Our real-data test used *injected* confounding on one public
   dataset. To truly promote it we need it to work on **naturally-occurring** confounding, ideally in a
   live customer engagement.
2. **It needs the right "fridge thermometer."** The check only works if at least one negative control is
   genuinely connected to the hidden problem. A poorly-chosen control misses it (we saw this — one weak
   control in the real-data test under-reacted). **Picking good negative controls is a judgment call** —
   and that's a job for the LLM / a human, even inside the "no-LLM" empirical path. So the LLM still
   earns its keep, just in a narrower role.
3. **Small real effects get deferred.** If a change has a real but *tiny* effect — smaller than the
   confounding noise in the data — the honest answer is "we can't tell from this data," and it goes to
   the LLM. We're trading a little coverage for a lot of honesty.
4. **Not yet wired into the live product.** All of this lives in research code and a reusable building
   block (`negative_control_guard()`); it still has to be ported into the persona-build worker and the
   router.

---

## 8. What's next (my recommended order)

1. **Port the building block into the live system** — the persona-build worker (which already reads the
   customer's data) computes these checks at build time, so at question-time the router just looks up the
   answer. This is the real productization step.
2. **Find naturally-confounded real data** (or a willing customer) to push this from "lead" to "promoted."
3. **Have the LLM nominate the negative controls** — turn limit #2 into a feature: the LLM's job becomes
   *"for this question, which of the customer's metrics shouldn't be affected?"*

I've left the loop at a clean stopping point with all six experiments validated and the safety gate
consolidated into reusable code. Everything is reproducible and sealed.

---

## Where the details live (for whoever picks this up)

- **Run ledger** (every experiment, verdict, fingerprint): `research/engine-strength-campaign/LEDGER.md`
- **The reusable safety gate**: `research/empirical-uplift-spike/causal_estimator.py` →
  `negative_control_guard()`
- **The router design** (where this plugs in): `research/empirical-uplift-spike/SCOPE_ROUTER.md`
- **Each experiment's sealed pre-registration**: `research/engine-strength-campaign/PREREG_ITER*.md`
- **Session log**: `sessions/empirical-accuracy-route/context.md`

*Verdict legend: PROMOTED (proven, replicated, stress-tested) · LEAD (works, needs replication) ·
NULL (tested, no signal) · MECH-ONLY (works on synthetic data only). This campaign: 1 MECH-ONLY,
1 NULL, 4 LEADs — all on the one idea that worked, the negative-control safety gate.*
