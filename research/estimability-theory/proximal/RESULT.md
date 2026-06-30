# Proximal CI (COCA) — result: correct-and-answer expands the slice, conditionally

*Sealed prereg `PREREG_PROXIMAL_CI.md` (sha 26d3b497). One scored run, no tuning. 600 cells ×
20 seeds × n=8000 = 12,000 runs, 66s. Verdict: **LEAD.***

## The adversary's critique this answers
> "You implemented the 2010 NCO falsification test (detect → abstain), not the 2018 proximal
> frontier (COCA) that *corrects* the bias and recovers the sign on cases you throw away."

Now implemented. COCA correction = `adjusted_ate(Y) − nc_residual`, where `nc_residual` is the
effect-on-the-negative-control the guard already computes. It turns the guard's "trip" signal from
an **abstain trigger** into a **correction term**.

## All three pre-registered predictions PASS

| Prediction | Result | Verdict |
|---|---|---|
| **1. EQUI recovery (the win)** | On guard-abstained, confounded, EQUI cells the adjusted estimator got *wrong* (n=1,538), COCA recovers the correct **sign on 95.8%** (vs adjusted 55.8%, naive 52.2%) | **PASS** |
| **2. VIOLATED no-free-lunch** | VIOLATED region-C (confident + directional + wrong): **COCA 19.7% vs guard 2.3%**; true-null direction-invention **COCA 64% vs guard 11%** | **PASS** (the price is real) |
| **3. Real-anchor safety** | Hillstrom +4.52→**+4.71pp**; Cookie Cats −0.77→**−0.56pp** (NC residual ≈ 0 on clean RCTs → COCA ≈ no-op, signs preserved) | **PASS** |

## What it means
COCA expands the estimable slice **only where additive equi-confounding holds** — exactly its home
turf — and **backfires** where it doesn't (correcting in the wrong direction on the abstain pile,
inventing directions on true nulls). The equi-confounding assumption is load-bearing and unverifiable
from data alone — the same shape as the NC-nomination limit (an LLM/domain must assert it).

**Deployable artifact: COCA-correct *inside* a guard that still abstains when equi-confounding is
implausible — never COCA alone.** Prediction 2's price (and the 64% null-invention rate) is as real
as prediction 1's win.

## Honest limits
- Synthetic recovery ≠ real recovery. The real anchors (Hillstrom, Cookie Cats) are *clean RCTs* —
  safety checks, not win conditions. There is no confounding there for COCA to correct.
- **Promotion (LEAD→PROMOTED) requires naturally-confounded REAL data with known truth** — the
  canonical benchmarks are LaLonde NSW-vs-PSID/CPS, IHDP, and the ACIC challenges. That is the next
  experiment: does COCA-inside-guard recover the *experimental* sign from the *confounded
  observational* version?
- Stretch double-NC / proximal-bridge (needs a negative-control *exposure* Z, assumption-lighter than
  COCA) was scoped but skipped for time — a follow-up.
