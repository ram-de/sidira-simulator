# PRE-REGISTRATION — Ambiguous-Dominance Battery (AMBDOM)

**Sealed before any estimator or LLM call runs. sha256 committed separately.
No re-tuning of the harness to these predictions. Public + synthetic data only —
no partner data, numbers, or identity appear here or downstream.**

Author: main loop. Date: 2026-06-30. Follows GNCE (PREREG_GNCE.md, 434fd8f0).
Caps: synthetic Arm A = MECH-ONLY; Cookie Cats / streamly-v3 probes = LEAD at most.

---

## Why this experiment exists (what GNCE settled and left open)

GNCE proved grounded mediation simulation recovers the sign of a NOVEL counterfactual
without seeing the treated outcome — **but it did NOT beat a mechanism-aware reasoning
LLM on direction (P1 refuted).** Root cause, in GNCE's own words: the battery *fixed
magnitudes so the dominant sign stayed qualitatively guessable*. Once the narrative
named the beneficial mechanism, a strong reasoner weighed two stated effects and got the
sign — tying grounded sim.

This battery removes that crutch. It builds cases where a feature has **two opposing
mechanisms through observed mediators**, and the **net sign is set by their relative
MAGNITUDES**, which words cannot convey:

> net effect = (how much the feature shifts the good mediator × how strongly that
> mediator drives the outcome) − (same for the harmful mediator).

When those two products are close, naming the mechanisms is not enough — you must KNOW
the magnitudes, and the magnitudes live in the data. This is the one regime where a
data-grounded g-formula should beat a reasoning LLM.

### Honest scope statement (registered to avoid fooling ourselves)

Arm A is an **EXISTENCE PROOF**, not a frequency claim. It tests: *do there exist
realistic-shaped cases where the answer is in the data and not in the words, and does
grounded sim get them while a fair, mechanism-aware LLM cannot?* It does **NOT** establish
how OFTEN real product decisions land in this regime — that is an empirical question
requiring real labeled features, which we don't have at scale. Arm B is the real-data
reality check on whether this regime is reachable outside a controlled DGP.

### Fairness to the LLM (registered so the test isn't rigged)

The LLM gets a FAIR narrative: both mechanisms named, both directions stated, with a
realistic qualitative salience cue a smart PM would have — but NO magnitude information
(because in reality the PM doesn't have the per-unit effect sizes for a novel feature).
Across the balanced battery the salience cue is constructed to be **uncorrelated with the
true net sign** (50/50), so a cue-following or constant-guessing LLM lands at chance BY
CONSTRUCTION. That part of "LLM ≈ chance" is therefore tautological and is registered as
confirmatory-not-novel. **The non-tautological, real-world-relevant test is the DISAGREE
cells (A1):** where the salient/intuitive lean points one way but the data magnitude flips
the net the other way — there a PM (and the LLM) following intuition is wrong, and only the
grounded magnitude saves it.

---

## ARM A — controlled synthetic ambiguous-dominance battery (MECH-ONLY)

Deterministic seeded DGP, n=8000/case. Two OBSERVED mediators:
- `Mg = bg·T + ggC·C + εg`   (good mediator / leading indicator)
- `Mb = bb·T + gbC·C + εb`   (harmful mediator)
- Outcome `Y_latent = lg·Mg − lb·Mb + dC·C [+ hid·U] + εy`;  Y = 1[Y_latent > median].
- **True net ATE sign = sign(lg·bg − lb·bb)** (+ confounding contamination in conf cells).
- "Salient lean" S (what the narrative/LLM is cued toward) is assigned per case and, across
  the balanced cells, is set INDEPENDENT of the true net sign.

Four estimators per case, each emits a SIGN in {+,−,0/abstain}:
- **GROUNDED-SIM** — fit `g = E[Y | Mg, Mb, C]` on the CONTROL arm (T=0) only; estimate the
  T→Mg and T→Mb shifts from observed mediators; simulate ΔY via g-formula over both
  mediators. Never sees treated Y. Dead-band |ΔY|<0.005 → 0 (near-null/abstain). Conf cells
  must adjust for C in both g and the mediator-shift models.
- **LLM** — REAL Groq (`llama-3.3-70b-versatile`, temp 0; fallback `llama-3.1-8b-instant`;
  if unreachable after 2 tries, PROXY = sign of the salient lean S, arm labeled PROXY).
  Narrative names both mechanisms + directions + the salient cue S, NO magnitudes. Sealed to
  `ambdom_llm_log.jsonl`, graded blind. Key loaded via grep from main-checkout backend/.env,
  NEVER printed.
- **ORACLE** — causal adjustment using treated Y (upper bound).
- **TRUTH** — DGP net sign.

### Cells (≥3 seeds each unless noted)

| id | margin | true net vs salient lean | confounding | notes |
|----|--------|--------------------------|-------------|-------|
| AGREE-WIDE   | wide   | net AGREES with lean | none | easy; both should win |
| DISAGREE-WIDE| wide   | net OPPOSES lean (magnitude flips it) | none | **the core A1 cell** |
| DISAGREE-NARROW | narrow | net OPPOSES lean, small margin | none | harder grounded test |
| KNIFE        | ~0     | net ≈ 0 (paths cancel) | none | abstain/near-null test |
| DISAGREE-CONF| narrow | net OPPOSES lean | observed C | grounded must adjust |
| DISAGREE-HIDCONF | narrow | net OPPOSES lean | hidden U in T,Mb,Y | grounded should BREAK |

### SEALED PREDICTIONS — Arm A

- **A1 (the real USP claim).** On DISAGREE cells (WIDE+NARROW, mediator-observed, clean):
  GROUNDED-SIM sign-accuracy **≥ 0.80**; LLM **≤ 0.40**; grounded beats LLM by **≥ 4 cells.**
  This is the regime GNCE could not test — magnitude-driven flips words can't resolve.
- **A2.** On AGREE-WIDE: GROUNDED-SIM and LLM **both ≥ 0.80** (no edge where intuition aligns
  with the magnitude).
- **A3 (honesty / no manufactured confidence).** On KNIFE: GROUNDED-SIM produces near-null
  (|ΔY|<dead-band) or abstains **≥ 0.70** of the time rather than forcing a confident sign.
- **A4 (resolution curve).** GROUNDED-SIM sign-accuracy is **higher on WIDE than on NARROW**
  DISAGREE margins (it resolves easily-separated magnitudes better than knife-edge ones) —
  registered as a monotonic expectation, REFUTED if NARROW ≥ WIDE.
- **A5 (limit — hidden confounding breaks grounded sim too).** On DISAGREE-HIDCONF:
  GROUNDED-SIM sign-accuracy **≤ 0.55** (the structural fit is contaminated when U is in the
  mediator path; NC-guard territory, consistent with the engine-strength campaign).
- **A6 (observed confounding handled).** On DISAGREE-CONF: adjusted GROUNDED-SIM **≥ 0.70**.
- **A7 (tautological-confirmatory).** Across all balanced cells, LLM net sign-acc **0.50±0.12**
  (info not in words by construction) AND LLM never exceeds GROUNDED-SIM on any DISAGREE cell.

---

## ARM B — real / realistic ground-truth probes (LEAD at most)

### B1 — Cookie Cats mediation (REAL RCT, 90,189 players)
Chain: gate position `version` (gate_30 vs gate_40) → `sum_gamerounds` (mediator) →
`retention_7` (outcome). True effect from the RCT: moving the gate later slightly REDUCES
7-day retention (small NEGATIVE; the canonical counter-intuitive result). The intuitive lean
("later gate = more runway before the paywall = better retention") is POSITIVE.
- GROUNDED-SIM: fit `g = P(retention_7 | sum_gamerounds)` on the gate_30 arm only; observe
  gate_40's effect on sum_gamerounds; simulate the retention lift. Never sees gate_40 retention.
- LLM: narrative (later gate, more rounds before wall; intuition +). Real Groq.
- TRUTH: the measured RCT retention_7 effect sign (negative).

**SEALED PREDICTION B1 (honest lean = my own method likely FAILS here).** GROUNDED-SIM via a
single `sum_gamerounds` mediator predicts a **NON-NEGATIVE** sign (≥0) — because
gamerounds→retention is dominantly POSITIVE and gate_40 barely shifts gamerounds, so the
mediation g-formula misses the tiny true negative. i.e. B1 = grounded sim **does NOT recover**
the negative sign; the LLM (intuition) also guesses positive. **Both miss** → illustrates that
real tiny-effect single-mediator ambiguity is beyond this method. REFUTED (pleasant surprise)
if GROUNDED-SIM recovers the negative sign.

### B2 — streamly-v3 heterogeneity-dominance (synthetic-but-realistic, truth = measured ATE)
The v3 datasets have `got_feature` (treatment), `outcome`, plus segment features (plan_tier,
plays_28d, etc.) and a known heterogeneous structure (helps one segment, hurts another). If
`got_feature` is randomized (verify), the measured naive ATE = unbiased truth. The NET sign
depends on the **segment MIX × per-segment magnitudes** — exactly what words can't convey.
- GROUNDED-SIM: fit `g = E[outcome | segment features]` per arm / via CATE composition on a
  train split; predict the population net sign. (Here the "mediators" are the effect-modifying
  segment features; grounded = compose per-segment effects weighted by the observed mix.)
- LLM: narrative (helps light users, may hurt heavy users; which dominates?). Real Groq.
- TRUTH: measured ATE sign per dataset (RCT).

**SEALED PREDICTION B2.** Across the v3 datasets, GROUNDED-SIM (segment-composition) recovers
the population net ATE sign **≥ 0.70**; LLM **≤ 0.55** (can't weigh the mix). If the v3 ATEs
are all the same sign (no genuine dominance ambiguity at population level), B2 is
under-powered → report as PARTIAL with the per-dataset signs rather than forcing a verdict.

---

## Grading

`SCORECARD_AMBDOM.md`: per-cell sign-accuracy for GROUNDED / LLM / ORACLE; the GROUNDED−LLM
DISAGREE-cell delta; the WIDE-vs-NARROW resolution curve; KNIFE abstain behavior; B1 predicted
vs measured sign; B2 per-dataset signs + accuracy. Each A1–A7, B1, B2 marked HELD / REFUTED /
PARTIAL with numbers. Append rows to LEDGER.md under `## AMBDOM`. Note LLM REAL vs PROXY.

## What each outcome means for the founder's thesis

- **A1 holds + A5 holds + B-probes honest** → there is a REAL, bounded regime where grounded
  simulation beats a reasoning LLM on direction: *magnitude-driven flips the words can't
  resolve*. The "simulate novel questions" USP has its empirical foundation — narrowly, on the
  ambiguous-dominance slice, with honest abstention on knife-edges and honest breakage under
  hidden confounding. The product pitch becomes: **we resolve the cases where intuition can't
  tell if the good outweighs the bad.**
- **A1 refuted** → even on magnitude-driven flips grounded sim does not beat the LLM; the
  directional-prediction USP has no empirical foundation in any tested regime, and the
  defensible value collapses to abstention + grounded explanation only. We say so.
- **B2 holds** → the heterogeneity-mix version of the win reaches realistic data, strengthening
  the slice. **B1's honest likely-failure** bounds it: tiny single-mediator real effects stay hard.
