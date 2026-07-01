# Founder Readout — Could we build our own fine-tuned model, like Bridgewater?
### "If we had unlimited resources, how do we fine-tune a model that makes our simulations accurate?"  ·  2026-06-30

*Written to read on the road. Plain language, honest about what fine-tuning can and can't buy.
Grounded in the actual Thinking Machines × Bridgewater write-up (their real numbers below).*

---

## TL;DR (read this if nothing else)

Bridgewater's real lesson is **not** "fine-tune a model." It's: *the frontier model had a
**verifiable, expert-labeled dataset** to be trained against — and building that dataset (and the
pipeline that cleans it) was the actual moat.* The training was reinforcement learning against a
**reward you can check**: "did you match the expert's label?"

That one ingredient — **a verifiable reward at scale** — is exactly what our hardest problem lacks.

So "unlimited resources" does **not** mostly buy GPUs or a clever training recipe. It buys, in order:

1. **A data factory** that manufactures real *(who the users are → what change we made → what
   actually happened)* triples at scale — including the rare counter-intuitive ones. This is the
   Senu thesis, now load-bearing.
2. **An outcome-grounded simulator** trained against those *measured* results (the reward = reality,
   not another LLM's opinion).
3. **The empirical watchdog kept in the loop** as the validator — because even a great simulator
   can't repeal hidden confounding or predict the genuinely unpredictable.

It buys us **the predictable slice, fully captured, plus calibrated honesty on the rest.** It does
**not** buy a crystal ball — and I'll show you exactly where the ceiling is.

---

## 1. What Bridgewater actually did (with the real numbers)

The task was **triage**: "which financial documents are worth an analyst's time" — six narrow
**classification** tasks (is this article relevant to a CFO? is this central-bank line a rate
signal? where does the boilerplate end?).

- Base model **Qwen3-235B**: **44.8%** accuracy — mediocre.
- + **GRPO** (reinforcement learning): jumps to **73.5%**. ← *this is the real lift.*
- + interleaving + a better loss + **on-policy distillation**: **84.7%**.
- For comparison, the best frontier model (Claude Opus 4.8) scored **78.2%**.
- And it ran **~14× cheaper** at inference.

So a tuned open model **beat the frontier model and cost a fraction.** Impressive — but look at
*why it was even possible*: every training example had a **right answer an expert could confirm**, so
the RL had a reward to climb. They even built a cleaning loop: train on cheap vendor labels, then
send the examples the model *disagrees* with to expert investors to re-judge. **The dataset and its
verification pipeline were the product. The training recipe was downstream of it.**

---

## 2. The one ingredient that makes the whole thing work

GRPO, CISPO, on-policy distillation — these all do the same prerequisite thing: **climb a reward you
can compute.** No verifiable reward → none of it works. You can't reinforce toward an answer you
can't check.

> **Bridgewater's reward:** "did you match the expert's relevance label?" — *cheap, abundant,
> verifiable, stable.* You can generate millions of these.

Hold that thought against our two problems.

---

## 3. Our two problems sit on opposite sides of that line

**(A) TRIAGE — "is this hypothesis worth a PM's time / worth testing?"**
This is *Bridgewater's exact shape.* The reward is checkable: from realized history ("did this
experiment produce a decision-changing result, or a wash?") or from a senior PM's judgment. Cheap,
abundant, in-distribution per customer. **A fine-tuned, customer-calibrated triage ranker is buildable
with today's tools** — it applies your best PM's judgment cheaply and consistently across a
thousand-idea backlog. This is the safe, near-term version of the Bridgewater play, and it slots
straight into the "decision economics" layer (only test the uncertain-and-worth-it slice).

**(B) PREDICTION — "what will this product change actually do?"**
Here the reward = **the real A/B outcome**, and that is everything Bridgewater's reward is *not*:

- **Expensive:** each label costs a full experiment, weeks of real traffic.
- **Scarce:** the public ceiling is ~8–12 real experiments; the *counter-intuitive* tail (the part
  that matters) is a handful.
- **Counterfactual:** you never see both outcomes for the same user (the fundamental problem of
  causal inference) — so even the label is an estimate, not a clean truth.

No verifiable reward at scale → **no GRPO miracle.** This is the same data wall the whole accuracy
campaign keeps hitting: *the binding constraint is data, not method.* A vanilla fine-tune doesn't
escape it — fine-tuning **is** the data wall wearing a new hat. (We also measured the failure
directly: no LLM method beats chance on counter-intuitive directional prediction, and the LLM is
structurally optimistic — it never predicts a decline. There's no good "teacher" to distill from when
the teacher itself is at chance.)

**So the unlimited-resources question is really: how do we manufacture a verifiable reward for
problem (B)?** Answer that and the Bridgewater recipe becomes available to us. Everything below is how.

---

## 4. What "unlimited resources" actually buys — the blueprint

### 4a. The data factory (this is where the money goes first)

To RL a simulator against reality, we need thousands of **labeled cases**: a population's per-user
features → a described change → the *measured* effect. Three taps, in priority:

- **Manufactured (the engine):** run real micro-experiments on real users at scale and harvest the
  outcomes. This is **Senu as a BenchmarkCase factory** — not a side project, the *training-data
  plant*. Critically, it must **over-sample counter-intuitive changes** (the rare tail), because a
  factory that only makes "obvious wins" teaches the model the optimism bias we're trying to kill.
- **Customer exhaust:** every customer's own past experiments (their A/B history) — labels we don't
  have to pay to create. This also becomes the per-customer adaptation set (4c).
- **Public corpora:** the ~6 real RCTs + portfolio cases — small, but the honest held-out yardstick.

**The dataset and its cleaning pipeline are the moat — exactly as they were for Bridgewater.** Copy
their verification trick: train on cheap/noisy labels, route the cases the model disagrees with to a
human (or the empirical watchdog) for re-judgment.

### 4b. The outcome-grounded simulator (the fine-tune itself)

Not a chatbot fine-tune on text — there's no signal in text. An **RL fine-tune whose reward is the
measured outcome.** The model takes a population + a change and predicts the effect (direction,
magnitude, who it hits); the reward is how well it matches the *real* result across the factory's
cases. Same discipline Bridgewater used — promote the teacher checkpoint only when held-out accuracy
improves, so you never distill toward a weaker model.

This learns **behavioral physics calibrated to reality**, not to an LLM's priors. The "talk to the
users / why" layer then rests on a model trained on real reactions — the USP, finally grounded.

### 4c. Per-customer adaptation

A base model learns general behavioral physics from the factory; then adapt it on each customer's own
experiment exhaust so it learns *their* users' specific behavior. General base + per-customer head =
accuracy **and** a moat (the model gets better the longer they use us — a flywheel competitors can't
copy without the data).

### 4d. The watchdog stays in the loop

Even a great simulator can't see hidden confounding or predict the irreducibly unpredictable. So the
**empirical watchdog** (the negative-control guard we already built) stays — at *training* time as a
reward gate (only train on cases whose measured truth is trustworthy; abstain-label the rest) and at
*inference* time as the validator that confirms, overrules, or flags the simulator's answer. The
fine-tuned simulator **replaces the ungrounded LLM front-face with a calibrated one; the watchdog
still adjudicates it.**

---

## 5. What fine-tuning can and cannot fix (the honest table)

| Fine-tuning **CAN** fix (in-distribution) | Fine-tuning **CANNOT** fix |
|---|---|
| De-bias the optimism prior — teach it some changes lose | The fundamental problem of causal inference (never see both outcomes) |
| Calibrate confidence — know when it's unsure | Predict the counter-intuitive tail where *no* data exists |
| Triage / prioritize worth-testing (the Bridgewater win) | Hidden confounding — that's the watchdog's job, forever |
| Decompose a change into its mechanisms more reliably | Manufacture a signal that isn't in any data (Salganik's ceiling) |
| Run cheap + fast + consistent at scale (14× cost cut) | Generalize past the population it was trained on |

---

## 6. What each dollar buys, in priority order

1. **Data factory (Senu) + cleaning pipeline.** Without verifiable rewards, nothing downstream works.
   This is 70% of the spend and the entire moat.
2. **The outcome-grounded RL fine-tune.** Cheap relative to the data — GRPO on a mid-size open model
   beat the frontier for Bridgewater. The recipe is known; the bottleneck is the labels.
3. **Per-customer adaptation + the watchdog-in-the-loop.** The flywheel and the safety net.
4. **A cheap distilled front-face** for the conversation layer. Pure cost play — do it last.

---

## 7. The honest ceiling (please read)

Even with infinite data and infinite compute, **accuracy is bounded by what's predictable in
principle.** This is the Salganik result (the Fragile Families study: the entire ML arsenal converged
on a simple baseline — the limit was the data, not the model). Our LLM-at-chance result is the same
signature. Unlimited resources buys us **the predictable slice fully captured, and calibrated honesty
about the rest** — a tool that's accurate where behavior *is* predictable and says "test this" where
it isn't. That honest boundary is the product. A vendor promising more is selling the crystal ball we
already disproved.

One more candid note: because we never observe both outcomes per user, the simulator's per-user
"reactions" are a *useful calibrated fiction* — true on average and per-segment, not literally per
person. The "why" conversation is grounded in learned conditional patterns, and we should say so.

---

## 8. What I'd build first (the cheap version of the dream)

Don't wait for unlimited resources to learn whether the recipe even fits us. Two sealed experiments:

1. **Triage fine-tune, public-data proxy.** Label the ~6 RCTs + portfolio cases worth-it/skip; tune
   a small ranker; score against a frontier-zero-shot baseline and a base-rate prior. This is the
   Bridgewater claim in our scope, and it's cheap. (Win condition: cheap model ranks worth-it cases
   above frontier-zero-shot.)
2. **Outcome-grounded micro-fine-tune feasibility.** On the synthetic factory we already built
   (the AMBDOM / GNCE batteries), RL a small model against the *measured* effects and ask: does it
   beat the optimistic frontier LLM on the counter-intuitive slice — and does it transfer to the real
   Cookie Cats / Hillstrom cases? This tells us whether outcome-grounded fine-tuning adds anything the
   grounded g-formula simulator doesn't already give us, *before* we build the factory.

Both are pre-registered, sealed, scratchpad-only — same discipline as the rest of the campaign. They
answer the real question: **is the bottleneck the model (then fine-tune) or the data (then build the
factory)?** Every result so far says *the data* — and the Bridgewater write-up, read carefully, says
the same thing: they won by building the dataset.

---

*Sources: Thinking Machines × Bridgewater, "Learning to Replicate Expert Judgment in Financial
Tasks" (2026). Ties to [[project-empirical-uplift-and-council-spike]] (the data-wall results),
[[project-senu-arena-feeder-verdict]] (the factory), and the watchdog architecture in
`founder-readout/README.md`.*
