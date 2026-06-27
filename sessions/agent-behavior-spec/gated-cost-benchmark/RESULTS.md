# Gated accuracy + cost benchmark (#39)

**Goal (founder):** re-benchmark the engine on the public data we already have, but
this time *gated* — call what's callable, abstain on what's too tough — treat each
data point as a real experiment with a cost, and report **how accurate we are** and
**how much money we save**.

Every run is appended to **`RUNS.csv`** (the reusable ledger — see `bench_store.py`)
so results accumulate and stay comparable instead of being recomputed and lost.

---

## What we could run NOW (no live engine, no fabrication)

A faithful gated benchmark needs, per case, the engine's **prediction + a
per-case confidence** (the confidence is what the abstention gate thresholds on).
Inventory of the public data we already have:

| Dataset | ground truth | stored engine prediction | per-case confidence | re-scorable now? |
|---|---|---|---|---|
| Milkman **gym** (54 nudges) | ✅ coefs | ✅ blind **ranking** | ❌ (ordering only) | **rank-only** ✅ |
| Hewitt **megastudies** (175) | ✅ | ✅ point preds | ❌ | ⚠️ paused (#16: reverse-coded / no clean control) |
| **Upworthy** headlines | ✅ | ❌ | ❌ | needs live run |
| product **portfolio** (8–15) | ✅ (narrative) | ❌ structured | ❌ | needs live run |
| vaccination / SSPP / DellaVigna-Pope | partial / gated | ❌ | ❌ | not available |

So exactly one dataset is cleanly re-scorable from stored artifacts: the **gym**,
and only as a **ranking** problem (it has no per-case confidence, so it cannot yet
demonstrate the *calibrated abstention gate* — the moat).

## Result — gym megastudy (`gym_gated_cost.py`)

Treat each of the 54 interventions as a candidate A/B test costing $C. You can't run
them all; Sidira ranks them and you run the top-B.

- **Overall rank skill: Spearman ρ = +0.132** (n=52) — near-random, matches the prior
  backtest; the gym domain is under-resolved by this data (ceiling ~0.5).
- **But the edge is concentrated at small budgets** — where prioritisation actually
  matters:

  | test budget B | engine captures | random | oracle | tail-recall@B |
  |---|---|---|---|---|
  | 5 | **16.5%** | 9.6% | 20.8% | **0.60** |
  | 10 | 26.6% | 19.2% | 37.5% | 0.40 |
  | 20 | 40.0% | 38.5% | 62.8% | 0.30 |

  At B=5 the engine's top picks capture **~1.7× the real effect of random** and recover
  **3 of the true top-5**. By B≈20 the advantage has washed out.

**Honest read:** on this domain the engine is a weak-but-positive *triage* signal —
useful for "which handful should we test first," not a confident ranker. The dollar
savings from the "tests-to-reach-X%-of-effect" framing are negligible (~1 test of 52)
because the effect is spread across many interventions; the real value is the
small-budget top-k lift, not slate-wide deduplication.

## What this does NOT yet show (and what would)

The **moat** is *calibrated abstention* — per case, "callable" vs "too tough" — and a
cost model driven by correctly abstaining. The stored gym run is a pure ordering with
no per-case confidence, so it cannot demonstrate that. To prove it we need a **live
engine run that emits `confidence_score` per case** on a clean dataset:

1. **Gym re-run** (54 calls) — adds per-case confidence → real risk–coverage curve →
   callable-accuracy + abstain-rate + cost.
2. **Product-change portfolio** (the best fit for "$ per experiment") — live run.

Both require LLM spend and **rotating the exposed keys first (#14)**. Once available,
each run appends a row to `RUNS.csv` via `record_run(...)` with `gated=yes`,
`callable_accuracy`, and `abstain_rate` populated — same table, directly comparable to
this rank-only baseline.

## Result — product portfolio, LIVE engine (`portfolio_gated_cost.py`)

A live prod run (208cd9e · `benchmark-portfolio` · 10 agents/arm · Groq llama-3.3-70b)
over **8 real product-change A/B tests**, each a directional bit (treatment vs
control won). All 8 are deliberately **counter-intuitive** cases — the set is built
to stress the engine's "more-is-better" bias.

- **Raw direction:** balanced sign-match **0.533** (forced, n=8); **4/6 = 0.667** on
  the cases it actually called (non-zero signal); it self-abstained (|signal|≈0) on 2/8.
  At/near the 0.625 "always pick the balance" baseline — consistent with the known
  finding.
- **THE MOAT TEST (does confidence track accuracy?) — FAILS on raw signal.** Ordering
  by |predicted signal| (the engine's own confidence proxy), the risk–coverage curve
  is **0.00 → 0.50 → 0.33 → 0.50 → 0.60 → 0.67** as coverage rises. The engine's
  **single most-confident call (multistep-form, +0.17) is its biggest MISS** (the
  form added steps and lost; the engine confidently predicted it would win). Accuracy
  *rises* with coverage — the opposite of what an abstention gate needs.
  (`abstention_is_monotone` returns True only **vacuously** — it no-ops at n<10.)

**Honest conclusion (the strategically important one):** on this data, **abstaining
on low engine-confidence gives NO lift** — confidence does not track accuracy, so the
gate would drop correct calls as readily as wrong ones. Dollar savings from raw-signal
gating ≈ **$0**. This matches the literature (raw LLM confidence is overconfident;
Kamath 2006.09462): the abstention moat needs a **TRAINED selective-prediction
calibrator on REAL outcomes**, not the engine's raw signal — i.e. calibration to a
**client's own A/B history** (#18/#20). Public data can't supply that history, so this
result **empirically validates the design-partner pilot path** (#23/#24) as the only
way to actually prove the moat. n=8 is below the gate's certification floor (G0≥50) —
illustrative, not certified.

## Files
- `bench_store.py` — append-only ledger (`RUNS.csv`); `record_run(**fields)` upserts by `run_id`.
- `gym_gated_cost.py` — the gym rank + cost analysis (records `gym-rank-stored-blind`).
- `portfolio_gated_cost.py` — the live product-portfolio moat test (records `portfolio-live-pop10`).
- `RUNS.csv` — the accumulating results table.
