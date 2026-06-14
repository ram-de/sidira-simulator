# Per-metric outcome elicitation — the conversion question (draft v1)

**Session:** agent-behavior-spec · 2026-06-13 · spec §3a
**Scope:** the exact in-character question that makes an agent reveal a *conversion* decision, so the simulator can report **conversion lift** (treatment vs control) instead of a generic sentiment-blend. Sibling questions (retention, CTR) follow the same template; conversion is drafted first as the load-bearing case.

---

## 0. Design constraints (from the research; why the obvious question is wrong)

The naive question — "Would you buy this? (yes/no)" — fails on four documented LLM-simulation pathologies:

| Pathology | Source | Consequence for "would you buy?" |
|---|---|---|
| Acquiescence / positivity bias | Funhouse Mirrors; Bisbee | Inflated yes-rate; agents are agreeable |
| Hyper-rationality | Funhouse Mirrors; CoMPosT | Agents convert whenever it's "reasonable," ignoring real-life inertia |
| Mode collapse @ temp 0, single sample | Bisbee 2024; Meister 2024 | One deterministic answer, no within-agent distribution |
| Uncalibrated absolute magnitude | Hewitt 2024 | Absolute P(convert) is direction-right but inflated — never trust the level |

Five design responses, each mapped to a constraint:

1. **Forced choice among realistic alternatives, not yes/no.** Conversion competes against *do-nothing, defer, comparison-shop, abandon* — the paths a real user actually takes. Kills acquiescence.
2. **"What do you *actually* do," grounded in the behavioral snapshot** — not "what's reasonable." Counters hyper-rationality; leans on the individual-conditioning lever (the persona's real behavior is already in the prompt).
3. **Base-rate anchor in the prompt** ("most visits don't end in a purchase") — counters positivity inflation.
4. **Elicit a distribution, not a point** — a 100-point allocation across the same options (verbalized sampling). One call, gives a per-agent distribution, sidesteps mode collapse without N× resampling.
5. **Score the DELTA on the paired identity, never the level.** The same agent identity (paired seed, #90) faces control *and* treatment; `lift_i = p_conv(treatment_i) − p_conv(control_i)`. The inflated absolute propensity is a per-agent constant that **cancels in the delta** — this is what makes lift usable *before* the #222 calibration layer exists.

---

## 1. Where it sits in the call sequence

Conversion is an **agent-side, in-character elicitation** — NOT a scorer-side classifier like sentiment/weakness (those are a meta-LLM reading the reaction text; a purchase decision is the persona's own action and depends on its behavioral propensity, not the tone of its prose).

```
turn 1  agent reaction (existing, unchanged)   → free text, in-character ("the why" + chat artifact)
turn 2  conversion elicitation (NEW)           → structured decision, conditioned on turn 1 + identity
```

Reason-then-decide: keep the natural reaction first (it stays the chat/"why" content and the sentiment/weakness input), then ask the behavioral choice conditioned on it. Runs once per agent **per arm** via the agent's frozen identity prompt + memory (`agent_memory.py`), so a control agent decides against the current product and a treatment agent against the change — same identity, paired.

> **Cheaper variant (flag for the cost/quality call):** fold the decision into the *initial* reaction prompt as a structured tail → 1 LLM call instead of 2 per agent. Loses a little grounding (the decision no longer reads back its own spelled-out reaction) and muddies the free-text chat artifact. Recommend the 2-turn form as default; expose the 1-call form for large/cheap runs.

---

## 2. The conversion question (prompt text, draft v1)

Appended as turn 2. `{...}` come from the Hypothesis target-metric field (#221) + the treatment-rendering layer (the on-screen options).

```
## What you do next

You just saw the {capability_name} as described. Forget what a "reasonable"
person would do — think about what YOU actually do next, given how you normally
behave (your behavioral snapshot above). Be honest with yourself: most of the
time, on most visits, people do NOT {conversion_action} — they get distracted,
put it off, or just keep browsing. Hold yourself to that bar.

You're at this moment: {decision_point}

If you hit this exact moment 10 separate times in your normal life, how would
those 10 times split across what you'd do? Put a number on each (they add to 10):

{action_options}
  - e.g. "{conversion_action_label}"          ← the conversion
  - "{realistic_non_conversion_option_1}"      ← e.g. keep browsing, decide later
  - "{realistic_non_conversion_option_2}"      ← e.g. leave / do something else
  - "{realistic_non_conversion_option_3}"      ← e.g. look at a competitor first

Then say, in one sentence, the single biggest reason your split looks the way it
does — tied to something specific about you or the product, not a generic reason.
```

**Structured output** (forced via `chat_json`, the existing pattern):

```jsonc
{
  "action_counts": { "<option label>": <int 0..10>, ... },  // sums to 10
  "primary_reason": "<=1 sentence, grounded",
  "self_reported_confidence": <0.0..1.0>
}
```

Per-agent conversion propensity in this arm:
`p_conv = action_counts[conversion_action_label] / 10`.

The 10-trial framing (vs. a raw probability) is deliberate: LLMs allocate counts far better than they state calibrated probabilities, and "10 times in your normal life" smuggles in base-rate realism. The `primary_reason` feeds the chat/“why” surface and is the per-persona theme cluster later.

---

## 3. What the Hypothesis must carry (feeds #221)

The question is a template; these fields fill it and MUST live on the structured target-metric (new on `schemas/simulation.py:Hypothesis`):

- `metric_name`: "conversion" (selects this template)
- `conversion_action` + `conversion_action_label`: the event + its in-character phrasing ("complete checkout", "start your free trial", "subscribe")
- `decision_point`: the moment the user is at ("you've added 2 items to your cart and are on the cart screen")
- `choice_set`: the realistic alternatives — **sourced from the reverse-figma/PRD** (the actual on-screen paths), which is why this depends on the treatment-rendering layer. Default fallback set = {convert, keep browsing/defer, leave, comparison-shop} when the screen doesn't enumerate them.

If `metric_name` is absent → today's sentiment behavior, unchanged (backwards-compatible).

---

## 4. Aggregation (lives in #221; restated for the contract)

1. Per matched pair (persona_id, sample_index): `lift_i = p_conv(treatment_i) − p_conv(control_i)` ∈ [−1, +1].
2. Panel conversion lift = persona-weight-weighted mean of `lift_i` (reuse the Hamilton weights).
3. CI via the existing #90 paired bootstrap, swapping the per-agent quantity from sentiment-delta → `p_conv`-delta.
4. Report **in conversion-rate units** (percentage points), e.g. "+4.2pp [+1.1, +7.6] simulated conversion lift", alongside the existing sentiment `confidence_score` (not replacing it).

---

## 5. Honesty guardrails (carry into the result UI)

- **Modality cliff:** conversion is a *behavioral* outcome → the weak regime (published r≈0.25–0.34), materially weaker than copy/CTR (r≈0.85). Surface the regime on the card; do not present conversion lift with the same confidence as a headline test.
- **Pre-calibration (before #222):** report **rank + direction + relative** lift ("treatment beats control, CI excludes zero, #2 of 6 variants"). Do NOT print a bare "+5.0pp" as truth — the delta cancels per-agent bias but the *scale* is still uncalibrated until the shrinkage layer is fit (Upworthy → CTR first, then conversion on Hillstrom/Criteo).
- **Reuse the #91 disclaimer copy** ("synthetic-agent reception, not a real business metric") — strengthen, don't drop it.

---

## 6. Design decisions (resolved for v1 — revisit if data argues otherwise)

1. **Distribution mechanism → verbalized 10-trial allocation (1 call).** Temperature-resampling ensemble is the truer distribution but costs N× per agent; the verbalized allocation gives a usable per-agent distribution at 1 call and is the documented mode-collapse fix. Decision: verbalized is the v1 default; keep resampling-ensemble as an opt-in for high-value runs once cost headroom exists.
2. **Decision granularity → single decision point for v1.** One decision at the metric's event. A multi-step funnel (browse → cart → checkout with drop-off at each) is richer but N× the calls and forces the renderer to model intermediate steps — defer until single-point lift is validated against the harness.
3. **Choice-set sourcing → resolved in the treatment-rendering layer.** The realistic alternatives come from the actual on-screen paths the renderer surfaces, with a curated default set ({convert, defer/keep browsing, leave, comparison-shop}) as the fallback when the screen doesn't enumerate them. Locked there, not here.

> Rationale: each open question had a clear v1 default; carrying them as "TBD" would block #221 sizing for no reason. These are reversible defaults, not one-way doors.
