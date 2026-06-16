# Hypothesis Input Quality (GIGO) — Distinguished-Engineer Panel Synthesis

**Date:** 2026-06-16 · **Owner:** ram · **Status:** decided → tickets filed → building via /loop

> Founder's question: *"The simulation is heavily input-dependent — garbage in, garbage
> out. Should we vet the hypothesis inputs, compute an input quality score, and have the
> simulation decision factor in that score? It might be right or completely wrong."*

This doc is the synthesis of a five-lens adversarial panel (experimentation science,
ML data-quality engineering, measurement validity / LLM-judge, decision theory, and a
dedicated red-team). Each panelist independently read the codebase and the prior
research. **The verdict was unanimous.**

---

## TL;DR — the decision

**The diagnosis is right; the proposed mechanism is wrong.** GIGO is real and the
hypothesis input is genuinely the least-vetted surface in the pipeline. But the fix is
**NOT** a learned 0–100 "input quality score" that the decision multiplies in. It is a
**deterministic pre-flight answerability gate that ROUTES** (block-with-fix / disclose /
abstain), spends **zero LLM tokens on the common cases**, reuses machinery that already
exists, and **never touches `confidence_score` arithmetically.**

Two things are unanimous and load-bearing:

1. **No scalar input score.** A single cardinal number over free-text prose is a
   construct error (it fuses ≥4 uncorrelated failure axes), it is **uncalibratable**
   (there is no ground-truth "this hypothesis was 72% well-posed" label in any A/B
   result), it is **Goodhart-gameable** (PMs write to the rubric), it **fails the
   product's own paraphrase-instability bar** (a number that wobbles ±15 on reword is a
   self-inflicted wound), and to a Kohavi-class buyer it reads as the synthetic-user
   vendor **grading the customer's homework** — performing the "untestable assumption
   hidden in an LLM" critique instead of answering it.

2. **Never discount `confidence_score` by an input factor.** This is the sharpest
   technical objection, raised independently by every lens. Multiplying the headline by
   an input-quality term **entangles "how well-posed is the question" with "how strong
   is the effect"** — and `confidence_score` is the *exact* quantity the #222 backtest
   harness exists to calibrate against real experiment outcomes. An input score cannot
   be backtested (no outcome label), so multiplying it in injects an **unfalsifiable
   component** into the calibration target, violating the team's own doctrine:
   *"a component earns its place iff it improves held-out prediction of real experiment
   outcomes"* (`ablation-protocol.md:10`). The existing ×0.7 degradation guard is
   legitimate **because it keys on an observable run-integrity event** (>50%
   classification failure), not a subjective rubric.

---

## Why the founder's instinct is still correct

The diagnosis is sound and the gap is real:

- The hypothesis is the **least-validated input in the whole pipeline.** Today the only
  checks are non-empty prose, population bounds, valid persona IDs/model, and
  metric-bundle completeness *if* a metric is set (`schemas/simulation.py:57-79`,
  `api/simulations.py:85-131`). There is **no answerability check and no refusal-to-run.**
- The deepest GIGO is real: agents **faithfully roleplay** whatever they're given. An
  unfalsifiable or structurally-invisible hypothesis produces a confident-looking
  number about nothing.
- One bad-input class is invisible to **every** existing component until a full
  (expensive) run is wasted: a **structural change submitted as prose-only** with no
  `proposed_figma` — "the agent compares a wireframe against a paragraph."

So the panel does **not** reject the founder; it re-shapes the mechanism from a *score
the decision weights* into a *gate the decision routes on.*

---

## What "input quality" actually decomposes into

Not one latent trait — four separable sub-constructs, with different remedies and
different homes. Critically, **three of the four are already covered**; only one is new:

| Sub-construct | Already covered? | Where |
|---|---|---|
| **Falsifiability** (does the prose yield a refutable prediction?) | Yes, post-hoc | `untestable_hypothesis` weakness (`scoring.py:160,174`) |
| **Specificity** (metric / cohort / mechanism named) | Yes, post-hoc | `wrong_metric` / `wrong_cohort` / `broken_mechanism` (`scoring.py:171-173`) |
| **Neutrality of framing** (no demand-characteristic / leading prose) | Mostly | blinded elicitor + unblinded-fallback flag (`conversion_elicitor.py`, `scoring.py:1210`) |
| **Measurability-by-this-instrument** (can a first-exposure single-session panel resolve this OEC at all?) | **NO — genuinely new** | — |

The existing six-category weakness taxonomy **is already an input critique** — it just
runs *post-hoc, from agent reactions.* The right move for falsifiability/specificity is
to **lift the same vocabulary forward to pre-flight** (one taxonomy, two timepoints),
**not** invent a parallel score. The only axis the stack does not measure anywhere is
**instrument-fit**: nothing today asks "is this OEC (e.g. 90-day revenue, virality,
equilibrium, novelty-decay) even within this instrument's resolving power?"

---

## The design — a pre-flight answerability gate that routes

Single integration point: **`api/simulations.py` pre-persist** (before
`orchestrator.prepare`, before any LLM token is spent). It returns a structured
`AnswerabilityVerdict { state, reasons[], fixes[] }` — **not a number** — and the rest of
the system routes on `state`:

- **`needs_input` (hard block + fix, deterministic only).** The two unambiguous,
  one-field-fixable structural defects:
  - **Structurally-invisible change** — prose describes a UI-structure/visual change
    (reuse `treatment_renderer`'s deterministic `prose_only` / reliability-regime
    classifier) **and** `proposed_figma is None` → "attach the structured change, or the
    agents compare a wireframe to a paragraph." *This is the highest-value piece: the
    one failure class no existing component catches pre-run.*
  - **OEC undeclared** — `metric_name is None` → prompt to declare the decision metric,
    with an explicit "run as generic-reception (not OEC-aligned)" escape hatch. Never a
    dead end for a paying user.
- **`out_of_scope` → ABSTAIN (run allowed, verdict withheld).** Deterministic
  long-horizon / revenue / network / novelty detector → a **fourth verdict state**,
  *"NOT ANSWERABLE BY THIS INSTRUMENT,"* surfaced in `verdictFor()` exactly like the
  existing `underpowered_design` flip. Abstention **strictly dominates a discount** in
  expected-cost terms for a Kohavi-class buyer: a tool that says *"I can't resolve this,
  here's why"* is more credible than one that always returns a (now quietly wrong) number.
- **`disclose` (amber) → run + stamp the card.** Semantic, probabilistic flags
  (vague-ish prose, leading framing) → run normally and attach `input_flags` to the
  result card using the team's chosen **degrade-and-disclose** pattern. Route red/amber
  into the **existing** `refinement.py` service (move its trigger earlier; do not fork
  the vocabulary). If an LLM judge is used at all, it returns **ordinal green/amber/red
  + named reasons from the existing taxonomy**, and **reuses the paraphrase-instability
  machinery to ABSTAIN** ("indeterminate — please clarify") rather than emit a number
  that flips on reword.
- **`answerable` → run silently (today's path, unchanged).**

**The real leverage is upstream.** The cheapest place to kill garbage is to make it
unconstructable: split the wizard's single free-text "01 · Claim" textarea into
structured fields (*if [change] for [cohort], then [OEC metric] moves [direction]*),
surface the metric-bundle fields (API-only today) in the UI, and inline-lint before
submit. *Don't grade the garbage — prevent it.*

---

## What this composes with (no duplication)

- **Weakness taxonomy** — same vocabulary, earlier timepoint. Pre-flight checks the
  cheap, input-only subset; the post-hoc taxonomy still does the agent-revealed autopsy.
- **Refinement service** — the block/disclose path *is* a pre-flight call into the
  existing service; its trigger moves earlier, the rewrites are reused verbatim.
- **Reliability regime** — the structural-invisibility gate is a thin policy wrapper over
  `render_state_diff`'s existing `prose_only` output; do not re-derive it.
- **Blinded elicitor** — owns framing/neutrality; add only a cheap overt-leading-prose
  lint, do not rebuild blinding.
- **#222 backtest harness** — the gate is **subordinate** to it. The gate's own labels
  (`needs_input` / `out_of_scope` / amber) become **backtest features**: do flagged runs
  demonstrably calibrate worse on held-out outcomes? If an axis doesn't earn its place,
  cut it. This keeps the gate falsifiable — the discipline a free-floating score can
  never satisfy.

---

## Risks the design explicitly defuses

| Risk | How the gate avoids it |
|---|---|
| **Calibration corruption** | Routes, never multiplies `confidence_score`. |
| **False precision / unfalsifiable component** | Emits categorical states + reasons, not a cardinal score; labels are backtest-validated. |
| **Goodhart / writing-to-the-rubric** | Deterministic presence checks (you can't fake attaching a Figma diff); satisfying them *is* the desired behavior. |
| **Trust optics (Kohavi)** | Inspectable named reasons ("UI-structure change submitted prose-only") read as engineering rigor; a 72/100 reads as blame-shifting. |
| **Friction / activation loss** | Hard-block only the two one-field structural defects; everything semantic is disclose-and-run with an override. |
| **Reliability under paraphrase** | Ordinal verdicts + abstain-on-instability; never a wobbly number. |

---

## Ticket plan (dependency-ordered)

- **T1 (foundational, MVP — deterministic, zero-LLM):** pre-persist answerability gate
  with the two structural checks — **structurally-invisible change** (UI-structure prose
  + no `proposed_figma`) and **OEC-undeclared** — returning `AnswerabilityVerdict` and
  routing (block-with-fix / run-as-generic). No confidence multiplier, no `verdictFor`
  change. Reuses the regime classifier + the metric-bundle schema. *Ships in days.*
- **T2 (abstention):** `out_of_scope` detector → fourth verdict state *"NOT ANSWERABLE BY
  THIS INSTRUMENT"* in `SimulationResult` + `verdictFor()`, composing with the
  `underpowered_design` flip. Depends on T1.
- **T3 (pre-flight ordinal lint):** falsifiability + leading-framing check returning
  ordinal green/amber/red + taxonomy-vocabulary reasons; routes red/amber into the
  existing refinement service; reuses paraphrase-instability to abstain; amber → card
  stamp. Depends on T1.
- **T4 (upstream authoring):** structured claim fields + surfaced metric bundle + inline
  linting in the wizard, making the (a)/(b)/(e) classes unconstructable. DESIGN.md
  compliance. Depends on T1–T3.
- **T5 (falsifiability, blocked on #222):** log answerability labels against held-out
  outcomes; validate that flagged runs calibrate worse; cut any axis that doesn't earn
  its place. Tracking ticket, starts when #222 lands.

**Build order for /loop:** T1 first (highest value, lowest risk, no LLM, no calibration
entanglement), then T2, then T3, then T4. T5 is filed as blocked.
