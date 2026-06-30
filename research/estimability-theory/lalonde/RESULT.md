# LaLonde promotion test — RESULT: the guard FAILS on canonical real confounding

*Sealed prereg `PREREG_LALONDE_PROMOTION.md` (sha 8673207a). One scored run, no tuning.
Verdict: **NULL / return-to-bench — the core claim did not transfer to real data.***
**This is the most important result of the estimability arc, and it is negative.**

## The numbers

| | A experimental (n=445) | B PSID (n=2,675) | C CPS (n=16,177) |
|---|---|---|---|
| naive ATE re78 | **+$1,794** ✓ | **−$15,205** ✗ | **−$8,498** ✗ |
| adjusted ATE re78 | +$1,595 ✓ | −$8,928 ✗ | −$3,693 ✗ |
| re74 placebo (RAW) | −$11 ≈ 0 | **−$17,333** | **−$11,921** |
| re74 placebo (ADJUSTED) | −$488 (−0.074) | −$406 (−0.026) | −$300 (−0.031) |
| guard trips? | **YES (false-trip)** | **NO (false-confident)** | **NO (false-confident)** |
| overlap fraction | 1.00 | 0.17 | 0.04 |

(Naive A = +$1,794 = the canonical Dehejia-Wahba experimental effect — data loaded correctly.)

## All three pre-registered predictions FAILED
1. **Specificity (clean RCT): FAIL** — the guard *false-trips* on experimental NSW (adjusted re74
   placebo −0.074 > 0.05 floor; small-n T-learner noise manufactured a residual where randomization
   guarantees none).
2. **Detection (the load-bearing claim): FAIL** — on PSID/CPS the naive sign is correctly wrong
   (−$15k/−$8.5k) and the *raw* re74 placebo is enormous (−$17k/−$12k), but the *adjusted* placebo
   collapses below the floor, so **the guard does not trip on massive real hidden confounding.** It
   would ship the wrong-sign answer with confidence.
3. **COCA recovery: did not recover** — COCA stays negative on B/C (my lean held), and because the
   guard didn't abstain, the system would actually *ship* the wrong-sign COCA estimate.

## The mechanism (the real, generalizable finding)
**`re75` (1975 earnings) is in the adjustment set and is near-collinear with the negative control
`re74` (1974 earnings).** Adjusting the re74 placebo on its own one-year-apart twin explains away
essentially all the selection bias on re74 (−$17,333 → −$406) — so the placebo looks clean
*post-adjustment*. But the same covariates do **not** clean re78 (four years out, far less correlated
with re75), leaving the −$8,928 wrong-sign estimate intact. **When a strong adjustment covariate
proxies the negative control, the adjusted-NC residual is artificially deflated and the guard
under-trips.** The synthetic validation never exercised this because its DGPs had no covariate
near-collinear with the NC.

## Why this matters (honest downgrade)
- The negative-control guard was the campaign's **first validated win** (4 synthetic LEADs + a clean
  Hillstrom-injection check). This is the **first time it faced real, naturally-occurring confounding
  with a known experimental truth — and it failed.** The synthetic LEADs were, in part, artifacts of
  DGPs that lacked the NC-collinearity structure real data has.
- It **validates the adversary's critiques (c)** "the synthetic phase-diagram is circular — you get
  out the structure you put in" **and (e)** "nothing transfers synthetic→real."
- **The founder-readout (`founder-readout/README.md`, on main) overstates the guard's robustness and
  needs this caveat.**

## The deeper tension (not a trivial bug)
The *raw* re74 placebo would have detected the confounding **perfectly** here (≈0 on the RCT, huge on
the confounded versions). But "use the raw, unadjusted NC effect" is **not** a valid general fix: the
NC was adjusted precisely to remove benign observed-covariate associations (synthetic iter1 showed an
unadjusted floor of 0.02 false-alarms on benign residual — which is *why* they adjusted and set
floor=0.05). So the guard sits between two failure modes — **adjust → miss collinear-proxy confounding
(LaLonde); don't adjust → false-alarm on benign association** — and LaLonde lands it squarely in the
false-negative one. This is a genuine limitation of the single-NC-guard design, not a typo.

## Candidate fixes (next, pre-registered)
1. **NC-collinearity-aware adjustment**: exclude covariates near-collinear with the NC from the NC's
   adjustment set (keep them for the outcome). Principled here (re75 *is* part of the selection
   structure), but trades specificity for sensitivity in general.
2. **Proximal / double-NC** (Miao-Geng-Tchetgen Tchetgen 2018): the structural machinery is designed
   for exactly this — it does not rely on the NC being "clean after adjustment." The harder, more
   correct route.
3. **NC nomination must avoid adjustment-set collinearity** — a concrete new rule for the LLM/domain
   step that picks the negative control.

Promotion remains OPEN. The honest status: the guard is a synthetic-validated heuristic with a
real-data failure mode now identified; it is not yet a real-world-validated instrument.

---

## Fix diagnostic (sealed `PREREG_LALONDE_FIX.md` sha da091a88) — candidate fix found, LEAD

Tested the principled rule **"do not adjust a negative control on a covariate near-collinear with
it"** by removing `re75` from the NC's adjustment set only (re75 stays in the main model). Both
sealed predictions **PASS**:

| Condition | NC re74 residual, **re75 removed** | raw placebo (no cov.) | guard trips? |
|---|---|---|---|
| A experimental | −0.034 (−$225) | −0.002 (−$11) | **No** ✓ (specificity) |
| B PSID | **−0.979** (−$15,302) | −1.109 | **Yes → abstain** ✓ (detection restored) |
| C CPS | **−1.126** (−$10,890) | −1.233 | **Yes → abstain** ✓ |

(Compare the broken guard: re75-*in* deflated B/C to −0.026/−0.031, no-trip.) The prior −0.074
small-n false-trip on A also **cleared** (−0.074 → −0.034) — it was itself partly the re75
collinearity. So the failure **was** the collinearity mechanism, and a principled NC-aware
adjustment restores detection on LaLonde with intact specificity.

**Honest standing — candidate fix / LEAD, NOT promotion:** validated on *one* benchmark (LaLonde);
the rule raises NC sensitivity globally, so it could increase false-positives where an NC legitimately
correlates with a benign covariate (the adjust-vs-raw tension persists — this fix moves toward the
raw end). **Promotion still requires:** (1) synthetic re-validation with NC-collinear covariates
*added to the DGP* (does the rule preserve specificity there?), (2) the ~6 other real RCTs from the
corpus manifest, (3) ideally IHDP/ACIC. A concrete new rule for the NC-nomination step also falls
out: **the negative control must not be collinear with an adjustment covariate.**
