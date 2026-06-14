# Elicitation templates (spec, draft v1)

**Session:** agent-behavior-spec · 2026-06-13 · spec §3 (general; §3a `elicitation-conversion.md` is the per-metric instance)
**Scope:** the elicitation techniques that apply across every metric and arm — *how* we ask, independent of *what* we ask. §3a applied these to conversion; this is the shared toolkit the other metrics (retention, CTR, …) and the benchmark harness reuse. Five techniques, each tied to a documented bias and to where it plugs into the current call path.

The call path today (audited): the agent emits one free-text reaction from its frozen identity prompt; `scoring.py` then makes two **scorer-side** `chat_json` calls (sentiment POSITIVE/NEUTRAL/NEGATIVE + weakness) over that text. Everything below is **agent-side** elicitation (the persona answering in-character), which is a different layer from those scorer-side classifiers — see §3a §1.

---

## 3b. Design unblinding (the biggest single bias lever)

**Code-confirmed problem.** `_TREATMENT_TASK_BLOCK` opens: *"The product team is considering this change: {prose} … React to this proposed change."* The agent is **told it's evaluating a PM's proposal.** That induces *demand characteristics* — the agent shifts from "user living their life" to "helpful evaluator grading a proposal," which amplifies acquiescence and hyper-rationality (it reasons about whether the change is *good*, not whether it would *change its own behavior*). The control arm is symmetric-ish ("react to the product as it works today") but still frames the agent as a reviewer.

**Spec — support both modes, default to blinded for metric prediction:**

- **Blinded (default for outcome/metric elicitation):** present the treatment state as *just the product* — no "proposed change," no "the team is considering." The agent meets the changed product the way a real user meets a shipped change: cold, in the moment. Both arms become "here is the product; here's what you do," differing only in which state (§1 renders the difference invisibly to the agent's framing). This is the apples-to-apples behavioral A/B.
- **Unblinded (kept for the chat / "why" feature):** the current framing — useful when the *value* is the agent's articulated opinion of the proposal (qa §5, the counterfactual interview). Explicitly NOT for the metric number.

**Decision rule:** metric elicitation (§3a-style decisions) runs **blinded**; chat/explanation runs unblinded. Never read a metric off an unblinded run — the demand characteristic inflates it. This splits today's single prompt into a behavioral pass (blinded) and an explanation pass (unblinded), reusing the same frozen identity.

> Tension to flag: blinding requires §1's renderer to present the treatment state as a coherent standalone product (not a diff narrated to the agent). The "what changed / NOT changing" changelog from §1 is then used **only** in the unblinded/chat pass and the scorer, **not** shown to a blinded behavioral agent. §1's output therefore has two views: standalone-state (blinded) and state+diff (unblinded/scorer). Add this to §1's contract.

---

## 3c. Verbalized sampling / distribution elicitation (general form)

§3a's 10-trial allocation is one instance. The general principle (analysis §3.3, counters temp-0 mode collapse): **elicit a distribution per agent, not a point.**

- For a **choice** metric (convert / click / churn): the N-trial allocation across options (§3a).
- For a **scalar** metric (satisfaction, willingness-to-pay, sessions/week): ask for a *range with a most-likely* ("most weeks ~3 visits, as few as 1 a bad week, up to 6 a good one"), or an explicit low/mode/high triple → treat as a per-agent distribution.
- For a **binary** with no natural alternatives: still force the 10-trial framing ("of 10 such moments, how many do you X?") rather than yes/no.

Why per-agent and not just panel-level: the within-agent distribution is what survives temp-0 (one deterministic completion otherwise), and it feeds the paired bootstrap (§3d) with a richer per-identity quantity than a single bit. One call gets it via verbalized allocation; resampling-ensemble is the costlier truer alternative (§3a Q1, deferred).

---

## 3d. Delta-vs-control framing (the scoring backbone)

This is the move that makes uncalibrated absolute levels usable, restated as a general rule (mechanics in #221 / §3a §4):

- The **same identity** (paired `(persona_id, sample_index)` seed, #90) faces control and treatment. The per-agent quantity is the **delta** `q(treatment) − q(control)`, not either level.
- The agent's inflated absolute propensity is a per-agent constant that **cancels in the delta** → the panel-mean delta is direction- and rank-credible *before* #222 calibration; the absolute level is not.
- **Never frame the delta to the agent.** Each agent answers about *one* state in isolation (blinded, §3b); the subtraction happens in aggregation, never in the prompt. Asking an agent "how much *more* would you do X under the change?" re-introduces the demand characteristic 3b removes — it tells the agent a change exists and asks it to rationalize a direction. The delta is an analyst operation, not an agent question.

**Decision rule:** agents are blinded and answer per-state; deltas are computed downstream. This is the single most important framing rule in §3.

---

## 3e. Paraphrase ensemble

LLM outputs are surface-form sensitive — the same question reworded shifts the answer. To stop a single prompt's idiosyncrasy from masquerading as signal:

- Run the elicitation under **K paraphrases** of the *question* (not the identity — identity stays frozen), average the per-agent quantity across them. K=3 as a starting point.
- Paraphrase the *elicitation wording only*; the rendered state (§1) and identity (§2) are held byte-identical so the ensemble isolates prompt-sensitivity, not content variation.
- **Cost note:** K paraphrases × (blinded behavioral pass) is K× the calls. Reserve the full ensemble for benchmark runs and high-value production runs; default production K=1 with the ensemble as an opt-in (same cost posture as §3a's resampling).
- This composes with 3c: paraphrase-ensemble reduces *between-prompt* variance; verbalized sampling captures *within-agent* distribution. Different axes — use both where budget allows.

---

## 3f. No-persona control prompt (the ablation arm)

The analysis asked for a **persona-free arm** to measure what the persona scaffolding actually buys (ties to §4 ablation and the "personas are scaffolding, not the engine" verdict, qa §6). Three rungs, identical except the identity layer:

1. **Persona + individual row** (full §2 stack) — the product configuration.
2. **Row only, no persona gestalt** — does the individual row carry the accuracy, with the persona narrative stripped? (the research predicts most of the signal is here.)
3. **No persona, no row** — generic user (demographic bands only or nothing). The floor.

Each rung reuses §1 (rendered state) and §3b–e (blinded, distribution, paraphrase) unchanged — **only the identity assembly (§2) varies.** Scored on the Tier-0 harness (#222); Park 2024 predicts rung 1 ≥ 2 ≫ 3, and §4 measures the actual ordering on Sidira's task. The no-persona prompt is just `compose_identity_prompt` with layers 3 (and 4) suppressed — a flag on the composer, not a separate template.

---

## 4. How these compose (one elicitation run)

For a metric prediction (blinded behavioral pass):
```
for each paired identity (persona_id, sample_index):           # §2 + #90
  for arm in {control, treatment}:                             # §3d
    render state as standalone product (blinded)               # §1 standalone view + §3b
    for k in 1..K paraphrases:                                 # §3e
      ask the metric's N-trial allocation (in-character)       # §3a + §3c
    q[arm] = mean over k of the per-agent quantity
  delta_i = q[treatment] − q[control]                          # §3d, downstream only
panel lift = weighted mean of delta_i ; CI = paired bootstrap  # #90 / #221
```
For the chat / "why" surface: a **separate unblinded pass** (§3b) over the same frozen identities, never feeding the metric number.

---

## 5. Open questions

1. **Two passes (blinded behavioral + unblinded chat) = 2× base calls** before paraphrase/resampling multipliers. Acceptable, or fold chat into an on-demand-only pass triggered when a PM actually opens the agent? (recommend: behavioral pass always; chat pass lazy/on-demand — most agents are never chatted with.)
2. **Blinding fidelity:** can §1 always render a coherent standalone treatment state, or do some change classes only make sense *as* a diff (e.g. "we removed the confirmation step")? Removal-type changes may be unblindable. (recommend: blind where the state is self-coherent; fall back to unblinded + flag for removal/pure-mechanic changes.)
3. **Paraphrase generation:** hand-authored K paraphrases per metric (controlled, limited) vs LLM-generated per run (diverse, but a paraphrase could drift meaning)? (recommend: hand-authored, reviewed set per metric for v1 — meaning-stability matters more than diversity.)
