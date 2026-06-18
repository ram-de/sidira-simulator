# Method-change research synthesis — fixing product-change directional simulation (#342)

Two councils, five independent perspectives — Claude lenses (causal-inference/HTE,
LLM-reasoning, behavioral-science, eval-methodology) + a Codex/gpt-5.5 frontier panel —
asked: what METHOD change (not a bigger model) fixes the more-is-better / prior-echo
failure on counter-intuitive product changes? They converged hard. This is the consensus.

## Unanimous diagnosis: the elicitation TARGET is mis-specified

Every member, independently: the engine asks for a **verdict** ("which version is
better?"), and the model's cheapest path to a verdict is to read the sign off a
**valence/level judgment** ("richer / more-featured / more-urgent = better"). That prior
is right on easy cases and wrong on counter-intuitive ones — hence chance accuracy below
the always-richer baseline. This explains the two prior failures: a bigger model echoes
the same prior more fluently (model-independent), and comparative elicitation is *still*
a "which is better" question. **The fix is to change WHAT we elicit, off the verdict.**

## The consensus method stack (ranked)

### Tier 1 — change the TASK; cheap, highest mechanistic plausibility, test FIRST
**M1. Per-arm behavioral simulation + signed mechanism ledger** (the fusion all five
converged on — the single highest-leverage bet). Three moves, together:
- **Judge each arm in ISOLATION** (between-subjects; the agent never sees the other arm,
  never told a change is tested). The treatment effect = ŷ(B) − ŷ(A) **differenced in
  code**, so the *sign comes from arithmetic, not the LLM's opinion*. (causal #1, behav #1, LLM #2)
- **Elicit ACTION, not opinion** — drop the persona into the arm and have it *enact*
  (convert / defer / abandon) with the proximate cause; aggregate behaviors → a rate.
  Counter-intuitive winners are exactly where *behavior* inverts *opinion*. (behav #1, LLM #2)
- **Forced signed mechanism ledger BEFORE any number** — require concrete positive AND
  **negative** causal pathways (the negative/"backfire" channel mandatory), each naming a
  specific persona friction + predicted action. (Codex #1 top pick, LLM #1, causal #3, behav #2)

**M2. Reference-class inversion prompting** — before forecasting, force "the obvious option
looks stronger because…; now list the conditions under which that advantage REVERSES" from
a curated library of behavioral reversal priors *with direction encoded* (deadline→procrastination,
timer→reactance, zoom→load, visible discount→quality-suspicion/deal-training). The model
selects which apply to THIS audience. Cheap add-on to M1. (Codex #2, behav #2)

### Tier 2 — add if Tier 1 underperforms
**M3. Reference-class base-rate anchoring + shrinkage** (aggregation-level). Real A/B
effects are mostly small/null and "obvious" often loses; anchor the prior over the effect
there and shrink weak/​conflicted panel signal toward zero, tie-breaking near-zero cases
toward the simpler arm. (causal #2, Codex #6)

**M4. Two-stage HTE** — feed clean per-arm micro-outcomes (from M1) + persona feature rows
into a causal forest / R-learner; the **estimator** decides the sign, fully removing the LLM
from the sign decision, and yields who-responds-more as a bonus. The *destination*, not the
first step — GIGO if the micro-outcomes are still biased. (causal #5, Codex #4)

### Tier 3 — controls, NOT primary fixes (all members flagged these)
- **Self-consistency / sampling more paths** — averages a *systematic* bias toward itself
  ("a tighter estimate of the wrong answer"). Run as a CONTROL: if it helps, the bias is
  partly variance (changes the diagnosis). Predict: no lift.
- **Debate / advocate-judge** — risk: the more *fluent* (usually prior-aligned) side wins
  unless the judge is strictly outcome-probability-grounded and order-balanced. Heavier, not better.

## Critical guardrails (convergent — the discipline that makes a result trustworthy)
- **Discriminator metric = accuracy on the "less-won" subset** (where the simpler/leaner
  option won). Overall accuracy is a guardrail, not the headline. Report the full 2×2
  (predicted more/less × actual more/less).
- **DEADLIEST artifact: a secret "pro-simpler thumb."** Any method that just nudges toward
  "less" aces the less-won subset with zero real reasoning. Catch it two ways: (1) counter-
  balance with cases where the richer arm genuinely won — a real fix improves less-won
  WITHOUT costing richer-won; a thumb trades one for the other; (2) run a **placebo
  "leaner-advocate" prompt** baseline — if it matches the fancy method, the method is a thumb.
- **Validate the reasoning isn't valence-in-disguise** — every mechanism/ledger entry must
  name a concrete persona friction + predicted action, checked, or it's wasted tokens.
- **Pre-register one primary endpoint**; paired per-case **McNemar exact** test; **multi-run
  majority vote** per case to kill sampling noise; **two models** (Groq + Opus) — cross-model
  replication is the cheapest artifact filter.
- **In-sample wins don't ship.** Need a held-out fresh confirmation set: ~40–60 fresh
  less-won cases to confirm a realistic effect; ~20 detects only a LARGE effect — state the
  bound out loud. (Our exploration set is ~10–24; it generates candidates, never confirms.)
- **Watch easy-case regression** (over-correction → contrarian flips) and log a standing
  **"more-is-better pick rate"** as the early-warning diagnostic.

## Recommended first experiment (concrete, cheap, falsifiable)
Build **M1 (per-arm behavioral-sim + mechanism ledger)**, optionally + **M2**, as a
flag-gated elicitation method at the research-script level (mirroring portfolio_comparative.py
— no production engine change yet). Run on the V4 counter-intuitive set:
- arms: current comparative baseline vs M1 vs a **placebo leaner-advocate** (artifact control)
- primary endpoint: less-won subset accuracy (paired McNemar exact); guardrail: richer-won
  accuracy must not regress; multi-run majority; pre-registered before the run.
- pass → lock the prompt/code and confirm on a fresh held-out counter-intuitive set.

If M1 lifts less-won without costing richer-won AND beats the placebo thumb → the first
credible path to product-change directional skill. If it ties the placebo → we learned the
gain was a thumb, not reasoning (still a real finding).

## Source artifacts
Codex council: `codex_council.md`. Claude lenses: agent transcripts (causal / LLM-reasoning
/ behavioral / eval). This synthesis is the de-duplicated consensus.
