# Ablation protocol (spec, draft v1)

**Session:** agent-behavior-spec · 2026-06-13 · spec §4
**Scope:** the experiment that decides which of the §1/§2/§3 upgrades earn their place. It runs on the Tier-0 harness (#222) and answers one question per component: *does it improve held-out experiment prediction?* — the decision rule from analysis §4 (NOT cluster stability; ARI is explicitly not an outcome here). This is what tells the code teams what to build first and what to cut.

---

## 0. The one rule

**A component earns its place iff it improves held-out prediction of real experiment outcomes, measured against the always-flat baseline and certified against nulls.** Everything below serves that rule. Stability scores, ARI, "the prompt looks better" — none are outcomes here.

---

## 1. Independent variables (the knobs)

Grouped by the spec section that introduces them:

| Group | Knob | Levels |
|---|---|---|
| §2 conditioning | identity depth | persona+row · row-only · persona-only · generic (the §3f 4-rung) |
| §2 conditioning | row deltas | z-scaled · rank-only · off |
| §1 rendering | change representation | structural state-diff · prose-only (today) |
| §1 rendering | "NOT changing" guard | on · off |
| §3 elicitation | framing | blinded · unblinded (today) |
| §3 elicitation | distribution | verbalized N-trial · point (today) |
| §3 elicitation | paraphrase | K=3 ensemble · K=1 |
| model | model / temperature | {opus, sonnet, haiku} × {temp-0, sampled} |

Full factorial is ~thousands of cells — not run. The design below is two targeted slices that together give sufficiency *and* necessity.

---

## 2. Outcome metrics (per harness run)

Computed per dataset, per cell, over held-out experiments:

1. **Direction accuracy** — sign(predicted lift) == sign(realized lift), as a rate. **Scored against the always-flat baseline** (qa §1: flat is right 67–92% of the time, so beating zero is meaningless; beating flat is the bar).
2. **Rank correlation** — Spearman ρ of predicted vs realized lift across the experiment set. This is the product claim ("we re-rank your backlog," qa §3) — the headline metric.
3. **Calibration (gated)** — predicted vs realized magnitude *after* the #222 shrinkage layer. Pre-calibration this is reported as "uncalibrated, rank-only"; it's an outcome only once the shrinkage layer exists.

Datasets (analysis §6): Upworthy (CTR, strong-modality, the first calibration target) · Hillstrom + Criteo (conversion/uplift, the only real end-to-end persona-pipeline test, artifact #5) · demographic-synthetic artifacts 1–4 (engine-only lower bound, no behavioral row → identity-depth knob degrades to generic there, which is itself a measurement).

---

## 3. Design — two slices, not a factorial

**Slice A — the value ladder (sufficiency).** Start from the current production config (prose-only · unblinded · point · persona-only · K=1) as rung 0. Add one upgrade at a time, in the §-predicted value order, measuring the *marginal* gain in rank-ρ and direction-accuracy at each rung:

```
rung 0  current config (baseline)
rung 1  + blinded framing            (§3b — predicted largest single bias fix)
rung 2  + individual row (z/rank)    (§2 layer 4 — predicted largest accuracy lever)
rung 3  + structural diff + guard    (§1)
rung 4  + verbalized distribution    (§3c)
rung 5  + paraphrase K=3             (§3e — variance, not bias; smallest expected gain)
```
The ladder gives the cumulative curve *and* each component's marginal contribution from a realistic base — directly answering "what do we build first." If a rung's CI includes zero marginal gain, that component is **deferred or cut**, regardless of how principled it is.

**Slice B — knockouts from the full config (necessity).** From the full stack (all upgrades on), remove ONE component at a time and measure the *drop*. Sufficiency (ladder) and necessity (knockout) can disagree — a component can look weak when added late (its work already done by an earlier rung) yet costly when removed (it's load-bearing). A component is **confirmed** only if it earns its place on at least one slice; cut only if it fails both.

**Identity-depth (§3f 4-rung)** runs as its own clean OFAT across {persona+row, row-only, persona-only, generic} at otherwise-full config — this is the "are personas the engine or the scaffolding" measurement (qa §6). **Pre-registered prediction (Park 2024): persona+row ≥ row-only ≫ persona-only ≥ generic**, with most of the gain at the row, little from the persona narrative. Commit this ordering *before* running (§5).

Model/temperature is a final OFAT on the winning config only (don't multiply it through the ladder).

---

## 4. Statistical protocol (Kohavi-proof, analysis §4)

- **Paired across experiments:** every cell predicts the *same* held-out experiment set; compare cells on per-experiment paired deltas, bootstrap the CI on the delta. Same discipline as the #90 paired-agent bootstrap, one level up (paired *experiments*, not agents).
- **Null-integrity certificate (mandatory):** scramble the experiment outcome labels → every cell must score at chance on direction and ρ≈0 on rank. A cell that "predicts" scrambled outcomes is leaking; the whole run is void until it doesn't. Ship the certificate with results.
- **Multiple-comparisons honesty:** the ladder + knockouts + depth-OFAT is many comparisons. Pre-register the primary endpoint (rank-ρ on Upworthy + artifact #5), correct the secondaries, and **report every cell run** — no dropping the ones that didn't help (silent-truncation rule, same as §1/§2).
- **Always-flat and random-rank baselines** printed alongside every cell, so a gain is read against the real floor, not zero.

---

## 5. Pre-registration (do this before running)

Write down, hash-commit, and only then run:
1. Primary endpoint: rank-ρ on Upworthy + Hillstrom/Criteo.
2. Predicted orderings: the depth ordering (§3) and the ladder's expected marginal-gain ranking (§3b > §2-row > §1 > §3c > §3e).
3. The decision rule per component (CI-excludes-zero marginal gain on ≥1 slice → build; fails both → cut).

This is the same hash-committed discipline the analysis demands of the *buyer* backtest (Tier 1) — applied inward to our own build decisions so the ablation can't be retrofitted to justify what we already built.

---

## 6. What each result decides

- Ladder + knockout → **build order and cut list** for the #221/#222 implementation. A confirmed component becomes a ticket-blocking requirement; a cut one is documented as "measured, didn't pay" (kills future re-litigation).
- Depth-OFAT → settles **how hard to invest in persona richness vs individual-row sampling** (#7 scope): if row-only ≈ persona+row, the persona narrative is confirmed scaffolding (legibility/chat) and #7 effort goes to the row/posterior, not narrative quality.
- The whole §4 result is also **Tier-0 sales evidence** (analysis §4.5): "here is what each modeling choice buys, measured on public experiments, certified against nulls" — the engine-validation half of the Kohavi-proof story, needing no customer.

---

## 7. Open questions

1. **Held-out split:** leave-one-experiment-out (max data, costly) vs a fixed train/test split per dataset? (recommend: LOO on the small sets Upworthy/Hillstrom; fixed split on Criteo's 13M for cost.)
2. **Cost ceiling:** the ladder alone is 6 rungs × datasets × agent-panels; the full matrix is large. Set a token/$ budget and let it bound K, panel size, and the model-OFAT scope — log what was dropped to the budget (recommend: cap panel at the noise-floor size from qa §2, ~1–3K agents, where sampling error ≈ LLM error).
3. **Who owns the harness run** — is §4 executed inside #222 by the benchmark code, or a separate ablation runner that imports it? (recommend: #222 exposes a cell-runner API; §4 is a config matrix over it, so production and ablation share one code path — same build-once principle as §1.)
