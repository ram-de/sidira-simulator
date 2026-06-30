# Persona-Pack Capability Score — design

*Corrects the case-3 "source elasticity data" framing. We only ever ingest TWO things: persona
data and historical data. So required signals must live in the pack's feature SCHEMA, validated at
BUILD time — not asked for bespoke per prediction. The info-sufficiency gate generalizes from
per-hypothesis pass/fail into a **pack capability profile**: "this pack scores X; it can answer
these case-classes, abstains on those; to unlock more, add these feature-classes."*

## The operating model (two paths, both structured — never an open-ended ask)
1. **Build-time (preferred):** the feature taxonomy below is the canonical feature-store **spec**.
   Every pack is built against it and ships with a capability score. Expanding what the engine can
   answer = a one-time schema/ingestion decision, computed once, not a per-prediction scramble.
2. **Prediction-time (fallback only):** if a hypothesis needs a feature-class the pack lacks, the
   router **abstains and emits a NAMED request for that class** ("provide promo-response history with
   treatment variation"), which feeds back into the pack spec. Never "give us more data" open-ended.

## Feature taxonomy (the "exhaustive set", v0) — each class unlocks a case-class
| # | Feature class | What it is | Validated by |
|---|---|---|---|
| 1 | **Identity / state** | demographics, tenure, lifecycle, membership status | presence |
| 2 | **Behavioral-rate** | orders, frequency, AOV, recency, category mix | presence + variance |
| 3 | **Heterogeneity drivers** | the variables an effect varies ACROSS (grocery-share, price-sensitivity proxy, channel mix) | presence + variance + discriminability |
| 4 | **Mechanism-exposure** | does the pack encode the variable THIS hypothesis turns on (delivery-fee usage, promo-order share, comparison behavior) | the current L0/L1/L2 gate |
| 5 | **Response / elasticity** | how a user responds to a change — price/fee/promo **AND UI/interaction** — **derived from historical treatment variation the population actually experienced** (transaction history for pricing; a **library of past UI experiments** for interaction) | variation/**support** check (empirical-route's overlap requirement) |
| 6 | **Market / relational structure** | competitive set, substitute availability/**selection**, merchant mix per market | presence + per-market coverage |
| 7 | **Outcome + causal support** | recorded outcomes + exposure + covariate overlap | the empirical estimability check |
| 8 | **Interaction telemetry / friction-exposure** | per-user event-stream aggregates on the affected surface: impression/tap, **mis-tap / rage-tap rate, time-to-action, dwell, scroll/hesitation, truncation-view, abandonment-after-step** | presence + variance on the touched surface |

## Case-class ↔ required feature-class registry
| Case-class | Needs | Example |
|---|---|---|
| Segmentation ("who reacts") | {3} | which users respond to a change |
| Volume / frequency change | {2}, +{5} if a pricing lever | order-rate effect of a fee/promo |
| **Pricing / fee / promo swap** | **{5} with support** | **case 3 (membership)** |
| **Generalization audit** of a prior win | {3, 6} + the prior experiment internals | **case 2 (ALDI→broad)** |
| **UI / perceptual-friction** | {8} friction-exposure + {5} UI-change-response (past-UI-experiment library) | **case 1 (size-selector)** — solvable WITH telemetry ingested at build (was wrongly marked permanent-abstain) |
| Direct effect estimation | {7} | analyze THIS / a PAST experiment |

## The score (what "50" means)
For each feature class, run presence (L0) + variance (L1) + discriminability/support (L2/overlap).
Emit:
- a **coverage vector** — per class: `absent | present-weak | validated`
- a **headline score** — weighted % of case-classes unlocked (the "50")
- an **answerable surface** — "can answer {segmentation, volume}; abstains on {pricing-swap: no response class, generalization: no market-structure, UI-perception: un-loggable}"
- a **prescriptive gap list** — "add promo/fee experiment history → unlocks pricing-swap; add competitive-set + selection-by-market → unlocks generalization"

That is literally: *"this pack scores 50, it can only solve these case-classes, and it needs THESE
feature-classes to solve more."*

## The three real cases, scored against the taxonomy
- **Case 1 (size-selector UI):** **RECLASSIFIED — solvable, not permanent-abstain.** The order-history
  pack lacked the signal, but UI friction IS loggable as **interaction telemetry (class 8)**, which the
  partner already collects. UI experiments are the MAJORITY of a real product roadmap, so this class is
  mandatory, not optional. See "Telemetry route for UI experiments" below.
- **Case 2 (grocery generalization):** had class {3} heterogeneity (grocery-share present) but lacked
  class {6} market-structure/selection → **partially answerable; generalization audit blocked** on the
  missing class. Gap list: add per-market competitive-set + selection.
- **Case 3 (membership swap):** needed class {5} response/elasticity (fee + promo), derivable from
  historical experiment variation but **absent from the pack** → **abstain + named request** for
  promo/fee experiment history; fold into the spec so the next pack scores higher.

## Telemetry route for UI experiments (case-1 bucket — the MAJORITY of a real roadmap)
*Ground truth from large-marketplace experimentation practice: most experiments are UI/interaction/flow changes, not pricing.
Abstaining on them = unsellable. They are solvable by ingesting **telemetry at pack-build time**, and
the structure is IDENTICAL to the pricing case — two layers, only the data source differs.*

| Layer | Pricing case (#3) | UI case (#1) |
|---|---|---|
| **Exposure** (who hits the mechanism) | delivery-fee usage, promo-order share | **interaction telemetry (class 8):** mis-tap rate, time-to-select, truncation-view, abandonment on the affected surface |
| **Response** (size the effect) | price/fee/promo elasticity from transaction history | **UI-change response from a library of PAST UI experiments** (their telemetry deltas → conversion outcomes) |

**What it requires at build time:**
1. **Aggregate event streams to per-user × surface features** (not raw events) — a real but tractable
   ETL: e.g. `item_page.mis_tap_rate`, `size_selector.time_to_select`, `…truncation_view`,
   `…abandon_after`. This is the new grain: order-history **+** interaction-telemetry.
2. **A UI-experiment library** — the partner's past UI changes, each with its telemetry signature
   (what friction it moved) and measured outcome. A mature product org has hundreds; this is the analog of pricing
   elasticity history. From it you fit an empirical response: *"changes that cut mis-tap rate by X and
   time-to-select by Y produced conversion +Z, with this variance."*

**Why this would have beaten the engine on case 1:** the case-1 change was a modest tap-target/UI
fix → the library would predict a **small** lift with **calibrated uncertainty** — much closer to the
**small measured win** than the engine's much larger fabricated point estimate, and without the
identical-personas fake unanimity.

**HONEST CAVEAT (don't overclaim):** this route is **structurally sound but UNVALIDATED.** The pricing/
generalization routes have real-data anchors (Cookie Cats, Hillstrom, the generalization audit); the telemetry-UI
route does not yet. It needs a real **UI-experiment corpus (telemetry + outcomes)** to show it beats
chance on *counter-intuitive* UI cases — same discipline as everything else. Two guards keep it honest:
(a) **novel UI patterns with no analog in the library → abstain** (out of support), and (b) it is the
EMPIRICAL route fed by telemetry, **not** a return to fake-confident persona role-play. The good news:
the corpus that would validate it exists at exactly the partner we'd sell to (unlike the public-data desert).

## Why this unifies with the empirical route
The capability score **is the estimability router run at build time over the whole feature schema.**
Classes 5 and 7 require historical *variation/support* (not just a column) — the same support/overlap
check the empirical route already does. So instead of routing each hypothesis live and discovering a
gap, we **pre-compute the pack's answerable surface** and attach the honest score + ceiling up front.

## Build plan (proposed)
1. Extend `persona_info_gate.py`: from `evaluate(pack, hypothesis)` → add
   `score_pack(pack, taxonomy) -> CapabilityProfile` (coverage vector + headline + answerable surface +
   gap list).
2. Encode the **taxonomy + case-class registry** as data (a small JSON/py spec), so it's auditable and
   extensible.
3. Reuse the empirical-route support check for classes 5/7 (variation/overlap, not just presence).
4. Self-validate on synthetic packs that deliberately have/lack each class (extend the existing
   5-pack test harness).
