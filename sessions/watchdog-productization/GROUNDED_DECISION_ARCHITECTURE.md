# Grounded Decision Architecture — Target Flow, Mechanics & Build Inventory

**Status:** design doc / living. Written 2026-07-05 from a founder Q&A on the end-to-end
"grounded decision" flow. Captures target-state, answers six mechanics questions, and inventories
what exists vs. what's ticketed vs. what isn't ticketed yet.

**Scope note.** Everything in the *decision* path (translator → grounded predictor → watchdog →
council → verdict) ships **inert behind `SIDIRA_DECISION_FLOW_ENABLED`** (default OFF). Prod is
unchanged today. This doc describes the target when it's on AND the producer + per-persona pieces are
built — not current live behaviour.

---

## 0. The two data feeds (don't merge them)

| Feed | Source | Artifact | What it is |
|---|---|---|---|
| **Feature store** | customer's warehouse (Snowflake…), connected | **Persona Pack** (`v_N`) | one row per user, behavioural columns → clustered personas. The observational data grounding estimates. |
| **Crawler** | walks the live product UI weekly | **Feature Pack** (`YYYY-Www`) | catalogue of product **capabilities** (reverse-PRD + reverse-Figma per capability). The *names* of levers. |

A **lever** is the *join* of the two: a crawler **capability** (e.g. "recommendation carousel") mapped
to a **treatment column** in the warehouse. No treatment column → the capability isn't grounded → LLM route.

---

## 1. Target-state flow

```
ONBOARDING  (per customer; once + refresh)
  Snowflake warehouse ─▶ Persona-pack build ─▶ persona pack (v_N)
    (feature store)        (sidira-personas)     + ESTIMABILITY MANIFEST ◀── LEVER MAP step
  Product URL ─▶ Crawler ─▶ Feature Pack (capabilities)   (capability→treatment col,
  Past experiments ─▶ Experiment connections ─▶ archive     + outcome + covariates + NEG CONTROLS)
    (OPTIONAL)

DECISION  (per hypothesis)
  hypothesis
    │
    ├─(1)─▶ Experiment-archive match?  ─ ALREADY_TESTED ─▶ surface the real recorded result   ◀ best
    │         experiment_similarity                                                             evidence
    │             │ NOVEL / SIMILAR
    ├─(2)─▶ LLM TRANSLATOR ─▶ MechanismSpec ─▶ GROUNDED PREDICTOR (g-formula reader)
    │         (uses capability catalogue)          │  matches (treatment,outcome) in manifest
    │                                              ▼
    │                                         WATCHDOG  (negative-control guard, precomputed)
    │                                         ├ CONFIRMS / CONTRADICTS  (trustworthy) ─▶ grounded verdict
    │                                         └ CANT_VALIDATE ─▶ ABSTAIN ────────────┐
    │                                                                                │
    └─(3)─▶ COUNCIL / LLM educated guess  ◀──────────────────────────────────────────┘  (unverified)

  ─▶ DirectionVerdict:  SHIP  /  NO-SHIP  /  CAN'T-CALL — TEST IT
  ─▶ grounded "talk-to-users" chat, grounded on the computed result

FEEDBACK  (accuracy over time)
  Senu real A/B outcomes ─▶ (engine_blind, measured) pairs ─▶ guard-threshold + calibrator tuning
  our shipped predictions ─▶ (predicted, actual) pairs ─▶ conversion_calibrator (#222)
```

**Precedence (verified in `negative_control_watchdog.py` + `decision_flow.py`):**
`direct past-experiment match  >  trustworthy grounded (watchdog CONFIRMS/CONTRADICTS)  >  LLM guess  >  untrustworthy grounded`.
Untrustworthy empirical is never laundered as truth — that's the whole point of the watchdog.

**One correction to the mental model:** there are **two** empirical routes, not one.
(1) the **experiment-archive** route asks *"have you literally already tested this?"* — retrieval of a
real recorded result. (2) the **feature-store causal** route (translator→grounded→watchdog) *estimates*
from observational warehouse data when no direct experiment exists. Today route (1) is retrieval-only
(no causal transfer from a *portfolio* of past experiments to a novel hypothesis — that's #520/#526).

---

## 2. Where is the watchdog & how does it work?

**Placement:** `translator (#539) → grounded predictor (#540) → **watchdog (#541)** → router/LLM (#542)`.
It sits between the grounded prediction and the router.

**What it is:** a pure **reader/classifier** of *precomputed* negative-control evidence. The heavy NC
compute (sklearn) runs **once at pack-build time** in the worker and is baked into the estimability
manifest. At runtime the watchdog imports **no ML** — that's what keeps the API image ML-free. It
**never raises**; any unexpected shape degrades to `CANT_VALIDATE`.

**Three verdicts** (`watchdog_classify`):

| Verdict | When | Router action |
|---|---|---|
| **CONFIRMS** | covered + supportable + guard clean, and (no LLM take, or LLM agrees) | grounded sign stands |
| **CONTRADICTS** | covered + supportable + guard clean, LLM take **opposes** the grounded sign | **flagship** — surface the *data's* sign, not the LLM's |
| **CANT_VALIDATE** | not covered / not supportable / no NC evidence precomputed (`guard_trips is None`) / guard **tripped** | covered→**ABSTAIN**; not-covered→fall through to LLM |

`trustworthy = (verdict != CANT_VALIDATE)`. The distinction "CANT_VALIDATE on a *covered* lever →
abstain" vs "on a *not-covered* lever → just use the LLM" is deliberate: if our own data on this exact
lever can't certify an answer, we must not pass an LLM guess off as grounded.

---

## 3. How do we come up with negative controls / confounders for a lever?

This is the **hardest open problem** and the honest answer is: *partly automatable, but nomination is
a domain/LLM judgment.* From `negative_control_guard` (`causal_estimator.py`):

**What the guard needs per lever:** `treatment`, `outcome`, `covariates[]` (confounders to adjust for),
and `neg_controls` — **one or a SET of metrics the treatment should NOT cause but which share the
confounding** (canonically: *pre-treatment* versions of the outcome / behaviours).

**How it decides (3-part gate, `floor=0.05, ratio=1.5`):**
1. Estimate treatment→outcome (adjusted, T-learner).
2. Estimate treatment→each negative-control (adjusted). Take the **decisive** one = max |residual|.
3. **Trip (abstain) if** either: **(a) hidden confounding** — any NC residual `> floor` (the treatment
   "moves" something it can't cause ⇒ unobserved confounding the overlap diagnostics can't see); or
   **(b) indistinguishable** — the main effect isn't `> ratio ×` the bias the NC reveals (a true-null
   or sub-bias real effect can't be told apart from confounding).

**Validated limits (from the engine-strength campaign):**
- Needs **≥1 negative control strongly coupled to the confounding**; a weak set under-trips.
- A **SET** with consensus (max |residual|) recovers bias a single weak control misses (lifted
  Hillstrom sensitivity from 75%→full coverage at 100% specificity; `0.05` floor transferred
  synthetic→real).
- The cost of honesty: effects **smaller than the measurable bias** get deferred to the LLM.

**How to nominate them in the product (the design):** the **LLM MAP step** (#512) — which already sees
the mechanism *and* the crawler capability context — nominates, from the warehouse column catalogue,
per lever: the outcome, the covariates, and candidate negative controls (defaulting to pre-treatment
outcomes + plausibly-unrelated metrics). The worker's `manifest_builder` then *computes* the guard over
that nominated set at build time. **Nomination quality is itself something to calibrate** (Senu / real
outcomes tell us which NCs actually caught bias). Do not present auto-nominated NCs as authoritative —
surface them for review.

---

## 4. Feature completeness — the "7 categories," is it enough?

**What we collect today (real, config-driven in `sidira-personas`):** 7 fixed feature groups —
`demographic_identity`, `behavioral_patterns`, `motivations_jtbd`, `pain_points_friction`,
`value_sensitivity`, `channel_tech_behavior`, `loyalty_lifecycle`. Defined in per-customer YAML
(`config/*.yaml`), **not hardcoded** — the pipeline iterates groups generically, so an 8th group is a
config edit (a new feature *type*/normalizer is a code branch in `adapter.py`). One production config
(`friends_family.yaml`) already uses a **different 4-group set**, proving the "7" is convention, not law.

**Is it enough? Two honest answers:**

1. **The repo's own methodology-of-record already says no.** `sidira-personas/docs/PERSONA_METHODOLOGY.md`
   §1 is titled *"the two-layer feature ontology (replaces the fixed seven groups)"* — argues the 7 are
   "a content checklist, not a methodology… no fixed column list survives contact with a second
   customer," demographics are poor predictors. It proposes **6 semantic verbs × 10 company-agnostic
   feature families** (RFM, engagement, breadth, lifecycle, funnel, habit, social, churn, value-sens,
   friction). **This is written but UNBUILT.**

2. **Completeness for *personas* ≠ completeness for *grounding*.** The 7 groups describe *audiences*
   (clustering). Causal grounding needs a **different** completeness: a treatment/proxy column, an
   outcome column, valid **confounders**, and **negative controls** — for each lever you want to ground.
   A pack can be persona-complete and grounding-empty.

**Concrete gaps to close:**
- **No coverage gate today.** Missing features are silently imputed / dropped (`adapter.py:100`
  `continue`); no null-fraction or coverage report. The documented **coverage manifest** (structurally-
  missing vs behaviourally-missing) is roadmap, not code. Grounding needs exactly this — a lever whose
  columns are structurally missing must route to LLM, not silently zero-impute.
- **Collect causal-relevant columns, not just persona columns:** pre-treatment outcomes (for NCs),
  exposure/assignment logs where they exist, and enough covariate breadth for adjustment.

**Recommendation:** don't chase "more categories" for its own sake. Add (a) a **coverage manifest** and
(b) a **grounding-completeness check per lever** (does this lever have treatment + outcome + confounders
+ ≥1 usable NC?). That's the completeness that matters for a trustworthy call.

---

## 5. Per-persona grounded sim + aggregation → ship / no-ship / test

**Current state: ABSENT.** The grounded route matches a MechanismSpec against **pack-level**
(population) precomputed candidate effects. There is **no per-persona loop**.

**Target design (what you described):**
1. Run the grounded estimate **conditioned on each persona segment** (a conditional average treatment
   effect, CATE, per persona) — the g-formula supports stratification.
2. Each persona yields a per-segment direction (+ magnitude, held backstage).
3. **Aggregate**, weighted by persona size, to a population call — AND inspect the *distribution* of
   signs across personas.
4. **Output:**
   - all personas agree, guard clean → **SHIP** (positive) / **NO-SHIP** (negative / CONTRADICTS)
   - personas **disagree in sign** (heterogeneous), or guard trips, or council disagrees →
     **CAN'T CALL — TEST IT** (optionally: a *segmented* recommendation "ship for A, not for B")
   - This maps onto `DirectionVerdict.caution` = `none` (ship/no-ship) / `moderate` (unverified) /
     `hard` (inconclusive), which is already the output contract.

Heterogeneity is *the* differentiator (resolving good-vs-bad magnitude trade-offs intuition/LLM miss).
Related tickets: **#514/#515** (persona info-sufficiency gate). The per-persona grounded loop + sign-
dispersion aggregation is **not ticketed yet** — see §7.

---

## 6. Two feedback loops that improve grounded accuracy

Both turn the guard from "validated on 1 RCT" into a calibrated instrument. Both must obey
**role-separation**: the WIN is `engine_blind` (sealed prediction) vs `measured` truth — never author one
to match the other.

**(a) Senu tests → accuracy.** Senu is a made-to-order **BenchmarkCase factory**: each study is a
hypothesis with a **real, human-measured A/B outcome** (ground truth). Feeding `(engine_blind, measured)`
pairs lets us: validate the guard's specificity/sensitivity on *real* data (as Hillstrom did); calibrate
the abstain thresholds (`floor`/`ratio`) per domain; learn which **negative-control nominations**
actually caught bias; and tune the translator's mechanism→lever mapping on cases where grounding was
right/wrong. Senu supplies the **measured truth** the paired corpus needs — the moat. *(Scaffold built:
`research/senu-study-store/calibrator.py`; 0 real sealed pairs yet — Senu is founder-gated.)*

**(b) Our own predictions → calibration.** Every real prediction becomes a `(predicted, actual)` pair
once the customer ships & measures. Accumulate → `conversion_calibrator` (#222): measure directional
accuracy on non-abstain cases, detect systematic bias (e.g. pro-feature optimism), recalibrate when to
abstain, and prove accuracy to buyers. *(Seam only: typed `Calibrator` Protocol + no-op
`IdentityCalibrator`; fitted shrinkage is #222-gated on real outcome data that doesn't exist yet.)*

---

## 7. Inventory — available / ticketed / not-yet-ticketed

Legend: **✅ built** · **🟡 partial** · **⬜ absent**. "Inert" = built but behind the OFF flag.

| # | Stage | State | Tickets (remaining) |
|---|---|---|---|
| 1 | Persona-pack build from warehouse (worker) | ✅ | #268 done; scaling #291/#292/#293 open |
| 2 | Feature-store connection onboarding (connect/map/health) | ✅ | Snowflake-only → #255; per-column override UI #271 |
| 3 | Crawler → Feature Pack (capabilities, reverse-PRD/Figma) | ✅ | multi-setup #474; mobile #216 |
| 4 | Experiment connections — import PAST experiments | ✅ | #46/#19 done; sql/statsig/csv connectors live |
| 5 | Empirical route: decide from past experiments | 🟡 retrieval only | #28/#29, #38 gate; **causal transfer from a portfolio → #520/#526** |
| 6 | **Estimability manifest / lever MAP (PRODUCER)** | 🟡 research prototype only | **port to worker #513; LLM MAP levers #512; capability layer/taxonomy #522/#523** |
| 7 | LLM mechanism translator | ✅ inert | #539 |
| 8 | Grounded predictor (g-formula reader) | ✅ inert | #540 |
| 9 | Negative-control watchdog | ✅ inert | #541 |
| 10 | Council fallback / abstain | ✅ inert | #542 router, #543 council |
| 11 | DirectionVerdict output + API + frontend panel | ✅ inert | #545 |
| 12 | **Per-persona grounded sim + aggregation** | ⬜ absent | related #514/#515; **core loop NOT ticketed** |
| 13 | Senu calibration feeder | ✅ scaffold, 0 real pairs | #547, #478, #546 |
| 14 | Prediction→outcome calibration loop (#222) | 🟡 seam only | #222; harness #517; answerability #314 |

**Cross-cutting, built:** the whole decision chain (7–11) is merged + deployed (SHA `21f31d4`) but
**inert** — `SIDIRA_DECISION_FLOW_ENABLED` is OFF, and the flag isn't even wired into
`ec2-api-deploy.sh` yet (SSM param alone is a no-op; turning on = deploy-script change + redeploy).

### The load-bearing gaps (in build order)

1. **[#513/#512] The producer.** Port `manifest_builder` + `causal_estimator` from `research/` into
   `sidira-persona-worker` so pack builds **emit the estimability manifest with NC-guard fields**.
   Until this, every grounded call → `CANT_VALIDATE`. *(This is "step (a)" from the prior conversation.)*
2. **[not ticketed] Coverage / grounding-completeness manifest** (§4) — so structurally-missing levers
   route to LLM honestly instead of silent zero-impute.
3. **[not ticketed] Per-persona grounded loop + sign-dispersion aggregation** (§5) — the heterogeneity
   differentiator; #514/#515 only cover an info-sufficiency gate, not the loop.
4. **[not ticketed] NC/confounder auto-nomination as a reviewable step** (§3) — the LLM MAP (#512) must
   emit candidate NCs + confounders for human review, and we must track which NCs actually catch bias.
5. **[#520/#526] Causal transfer from the experiment portfolio** — decide a *novel* hypothesis from a
   *set* of past experiments (meta-analytic), not just exact-match retrieval.
6. **[founder-gated] Real outcome data** — Senu pairs (#547/#478) + shipped-prediction pairs (#222) to
   calibrate the guard beyond one RCT.
7. **[founder-gated] Flag wiring + flip** + OpenAI key (council's gpt-5.5 arm) or drop it from the panel.

### Not-yet-ticketed summary (candidates to file)

- Per-persona grounded prediction + aggregation loop (§5).
- Coverage/grounding-completeness manifest + per-lever grounding check (§4).
- NC/confounder auto-nomination + a reviewable "lever card" surface (§3).
- A frontend "grounding sources / observable levers" view (the thing that prompted this whole thread —
  today no UI surfaces which levers are grounded vs guessed).

---

## 8. Recommended sequence

1. **Producer first (#513/#512)** — emit the manifest on a real pack rebuild (Streamly). This turns the
   whole chain from architecture into something measurable, and empirically shows **how many levers are
   groundable from warehouse data alone** (expect: few → which is the argument for experiment data).
2. **Coverage manifest + grounding-completeness** — so "few" is honest, not silent.
3. **Per-persona loop + aggregation** — the differentiated output.
4. **Wire + flip the flag** on Streamly; add the grounding-sources UI.
5. **Feed real outcomes** (Senu #547/#478, then shipped predictions #222) to calibrate.

Flipping the flag before step 1 produces only honest "can't-validate / unverified" panels + LLM spend —
low payoff. The producer is the unlock.
