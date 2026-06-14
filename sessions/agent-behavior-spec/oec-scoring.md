# OEC-aligned scoring (spec, draft v1)

**Session:** agent-behavior-spec · 2026-06-13 · spec §6 (capstone)
**Scope:** score the simulation against the **customer's Overall Evaluation Criterion** — the metric they actually optimize — instead of generic reception sentiment. This is the analysis §4.4 Q11 gap, and it's the piece that makes everything upstream (§1 rendering, §2 conditioning, §3a per-metric elicitation) add up to a number the customer recognizes. Closes the spec.

---

## 0. Current scoring (audited — `schemas/scoring.py` + `services/scoring.py`)

Per agent: two scorer-side `chat_json` calls — **sentiment** (POSITIVE/NEUTRAL/NEGATIVE + confidence) and **weakness** (the 6 `Weakness.category` flags). Aggregated:

```
sentiment_score  = (Σ conf_i·value_i + prior_k·0.5) / (Σ conf_i + prior_k)
weakness_signal  = 1 − any_flag_share
confidence_score = (0.6·sentiment_score + 0.4·weakness_signal) × 100
ABLiftResult.lift = per-agent sentiment-delta bootstrap, scaled into confidence_score units
```

**The gap, stated plainly: this is OEC-blind.** A customer optimizing **conversion**, one optimizing **7-day retention**, and one optimizing **revenue per session** all receive the *same* `confidence_score` — a generic "how warmly did synthetic users receive this." Kohavi's whole point is that an experiment's success is defined by *its OEC*; scoring against generic reception is scoring against the wrong target. The `lift` being in "confidence_score units" is the same gap in the A/B path (already captured in #221).

---

## 1. The OEC-aligned model

**Definition.** The OEC is the customer's declared success criterion for *this* hypothesis: a **primary metric** (the thing the change is meant to move — conversion, retention, CTR…) plus optional **guardrail metrics** (things that must NOT degrade — complaint rate, latency, unsubscribe). It is sourced from the PM at hypothesis submission → a schema concern on `Hypothesis` (#221's target-metric field, extended to carry guardrails).

**Scoring with an OEC set (the new default when present):**
- **Headline = the primary-OEC lift** from §3a's per-metric elicitation + §3d delta aggregation — e.g. "+4.2pp simulated conversion lift [CI], directional/rank pre-calibration." This is the number the customer optimizes, in the customer's units.
- **Sentiment → demoted to a diagnostic.** It stops being the headline and becomes part of the "why" surface (§5) — useful color ("reception was warm but behavior didn't move," a classic real pattern), never the score.
- **Weakness → stays as the experiment-design critique** (it's already OEC-adjacent: `wrong_metric`, `wrong_cohort`, `underpowered_design` are critiques of the *test*, not the reception). Keep it as the design-quality sidebar.

So the three current signals don't disappear — they're **re-ranked**: OEC lift becomes the headline, sentiment becomes diagnostic, weakness stays as design critique.

---

## 2. Guardrails (composite OEC)

A change can move the primary OEC the right way while tripping a guardrail — conversion up *because* a dark-pattern also spiked refund requests. Kohavi-grade scoring must catch this:
- Each guardrail is **its own §3a-style elicited metric** (a behavioral decision: "would you later regret / return / complain?"), scored as its own arm delta.
- The result reports **primary lift AND guardrail deltas together**; a positive primary with a tripped guardrail is surfaced, not hidden — a "wins primary, fails guardrail" verdict is more valuable than a clean win.
- This connects to the existing `hidden_guardrail_risk` weakness category: the *qualitative* flag already exists; the guardrail metric is its *quantitative* counterpart. The weakness flag can trigger a suggestion to *add* a guardrail metric the PM didn't declare.

---

## 3. Fallback + honesty

- **No OEC declared → today's behavior, explicitly labeled.** Compute the generic `confidence_score` as now, but label it "generic reception — no success metric set" and prompt the PM to declare one. Never present generic reception *as if* it were OEC-aligned. (Same silent-truncation honesty rule used in §1/§2/§4.)
- **Unmeasurable OEC → say so.** If the declared OEC can't be reduced to an elicitable behavioral decision (e.g. a long-horizon revenue figure no single-session agent can produce), the scorer declares it out of scope rather than faking a proxy — and may fall back to the nearest elicitable leading indicator *with that substitution stated*.

---

## 4. What the headline number becomes

- When an OEC is set, `SimulationResult`'s headline shifts from `confidence_score` to the **primary-OEC lift** (native units); `confidence_score` is retained as a secondary "reception" field, not removed (backwards-compatible, and genuinely informative as a divergence signal).
- `ABLiftResult.lift` gains a unit/metric tag — it's no longer always "confidence_score units" but "conversion pp" / "retention pp" / etc., per the elicited OEC. (#221 owns the schema change; §6 owns the semantics.)
- **Calibration gating carries through (§3a §5, §4):** OEC lift is reported **directional/rank/relative** until #222's shrinkage layer calibrates absolute magnitude (Upworthy → CTR first). The headline pre-calibration reads "treatment beats control on conversion, CI excludes zero, ranks #2 of 6" — never a bare "+4.2pp" as truth.

---

## 5. Build / touch points

- **`Hypothesis`** (#221): target-metric field carries `primary_oec` + `guardrails[]` (each = metric name + elicitation template selector + direction).
- **`services/scoring.py`**: add an OEC-aligned aggregation path alongside `aggregate` / `aggregate_ab`; reuse the #90 paired bootstrap, swapping the per-agent quantity to the §3a `p_metric`. **Run `impact` on `aggregate`/`aggregate_ab` before editing** — they feed `SimulationResult` and the route layer.
- **`scoring.py` schemas**: tag `ABLiftResult.lift` with its metric/unit; add primary-OEC + guardrail result fields (or compose them in `SimulationResult` — #221's call).
- The generic sentiment/weakness path stays intact as the fallback + diagnostics — additive, not a rewrite.

---

## 6. The spec as one pipeline (§1 → §6 synthesis)

The six sections are one path from a PM's hypothesis to a trustworthy, OEC-aligned, honestly-bounded number:

```
PM submits hypothesis + OEC (primary + guardrails)             →  §6 / #221
§1  renders (existing state, change) → two views (blinded / diff)
§2  assembles each agent: persona gestalt + individual row (paired seed)
§3  elicits, BLINDED, a per-agent distribution on the OEC's behavioral decision   §3a + §3b–e
§3d aggregates the paired control/treatment delta (bootstrap, #90)
§6  scores it against the OEC (primary lift + guardrail deltas; sentiment→diagnostic)
§5  chat / counterfactual interview explains the "why" (juxtaposition, hypothesis-only)
§4  ablation has already proven which of the above components actually earn their place
    — and #222 calibration converts directional lift → trustworthy magnitude
```

Honesty guardrails run end to end: blinded elicitation (no demand characteristics), delta cancels uncalibrated propensity, modality cliff sets the confidence ceiling, directional-until-calibrated, every fallback logged, chat is hypothesis-not-evidence. That through-line *is* the Kohavi-proof positioning the analysis demanded: "calibrated prior / triage / warm-start," never "digital clones" or an uncalibrated magnitude.

---

## 7. Open questions

1. **Composite OEC weighting:** when a customer has a multi-metric OEC (Kohavi often a single combined metric), do we score each component separately and let the PM weigh, or elicit a combined preference? (recommend: separate components + explicit guardrails for v1 — a single blended OEC number hides the tradeoff that's the whole insight.)
2. **OEC vocabulary:** a free-text metric name vs a controlled list (conversion/retention/CTR/…) that maps to §3a templates? (recommend: controlled list mapping to elicitation templates for v1; free-text falls back to generic + a "no template" flag.)
3. **Sentiment/behavior divergence as a feature:** "warm reception, flat behavior" is a real and valuable pattern — surface it explicitly as a named insight, or just report both numbers? (recommend: name it — it's exactly the trap generic sentiment scoring causes elsewhere, and catching it is a selling point.)
