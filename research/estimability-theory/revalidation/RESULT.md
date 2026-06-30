# Fix re-validation — RESULT: the covariate-drop fix is REFUTED. Route to proximal.

*Sealed prereg `PREREG_FIX_REVALIDATION.md` (sha 8fc805c7). One scored run each, no tuning,
thresholds (floor 0.05, ratio 1.5, drop-threshold 0.8) frozen. Verdict: **NULL / route-to-proximal.***

The LaLonde fix — *"do not adjust a negative control on a covariate near-collinear with it"* — looked
like a candidate LEAD on the single LaLonde benchmark. Tested properly on a synthetic DGP that
**contains** the collinearity structure (Part A) and on 4 real clean RCTs (Part B), it fails the
decisive specificity test on both. The covariate-drop rule is not a general fix.

## Part A — synthetic re-validation (the decisive test)

DGP with the LaLonde twin structure: latent confounder U; continuous NC outcome `W`; an observed
covariate `X_c` solved to hit `corr(X_c, W) == collin` exactly; true-null cells use **benign observed
selection on X_c** (the genuine specificity risk, not a trivial randomized null). 1440 units
(collin{.5,.8,.95} × gamma × tau{−.5,0,.5} × pclean × {confounded,null}, n=8000, 20 seeds).

NC-detection trip rates (the channel the fix modifies):

| class | collin | OLD | FIXED | RAW |
|---|---|---|---|---|
| confounded | 0.95 | 0.829 | **1.000** | 1.000 |
| true-null  | 0.95 | **0.000** | **1.000** | 1.000 |
| true-null  | 0.80 | 0.000 | 0.517 | 1.000 |
| true-null  | 0.50 | 0.033 | 0.033 | 1.000 |

- **P1 (reproduce failure): technical FAIL, direction confirmed.** At collin .95, OLD 0.829 vs FIXED
  1.000 — delta +0.171, just under the pre-chosen 0.20 bar (a delta threshold I set, not frozen by
  prereg). But OLD's detection falls monotonically with collinearity (0.996→0.921→0.829) while FIXED
  holds (0.996→0.958→1.000): the LaLonde mechanism reproduces unambiguously.
- **P2 (fix restores detection): PASS.** Where OLD's NC missed, FIXED trips 0.82 overall, 1.00 at
  collin .95.
- **P3 (SPECIFICITY — decisive): FAIL hard.** On true-null cells (no hidden confounding) with the
  collinear X_c present, FIXED false-trips **0.517 overall, 1.000 at collin .95** vs OLD 0.011. The
  false-trip rate tracks the X_c-drop rate exactly — where FIXED drops X_c it reverts to RAW, and RAW
  false-trips at 1.000 on these benign-but-real observed-selection nulls (which is *why* the NC was
  adjusted in the first place).

## Part B — real RCT breadth (4 datasets: Hillstrom, GOTV, Karlan-List, Orange-Belgium)

- **P4 (sign recovery): PASS 3/3.** Hillstrom +4.5pp, GOTV +8.1pp, Karlan small +, Orange-Belgium
  correctly read as the null/backfire case (sign not forced). The empirical route does its job on
  clean data. Encouraging detail: the collinearity-drop rule *fired* correctly on Hillstrom (dropped
  `womens`, corr 0.82) and specificity held there.
- **P5 (no false alarm): FAIL 1/4.** FIXED false-trips on **Orange-Belgium** (NC residual −0.091 >
  0.05 floor). Likely cause: a **scale-units bug** — the 0.05 floor was calibrated on probability-scale
  binary NCs, but Orange's NC is a standardized continuous variable where 0.05 SD ≈ 2.3 SE, far too
  tight. (Also the messiest set: unequal arms 9010/2886, anonymized covariates.) Either way, per the
  honesty rails it counts as a false-trip on a real RCT.

## Combined verdict — the fix is NULL, the route is proximal

Two independent tests — the decisive synthetic specificity test (P3) and real-RCT breadth (P5) — both
show the covariate-drop rule **trades too much specificity**. It worked on LaLonde only because there
the dropped covariate (re75) was doing *confounding* adjustment work; in the general case (benign
observed-selection nulls, real RCTs) the dropped covariate is doing *legitimate* adjustment work, so
dropping it manufactures false alarms. This is exactly the **adjust-vs-raw tension** the LaLonde
RESULT.md flagged and the prereg's verdict-mapping anticipated: *"Fix → NULL / route-to-proximal if
3 FAILS."* No single-NC covariate rule escapes it — you cannot tell, from collinearity alone, whether
the covariate is cleaning confounding or benign association.

**The route forward is the proximal / double-NC machinery (Miao-Geng-Tchetgen Tchetgen 2018)** — it
does not rely on the NC being "clean after adjustment," which is precisely the assumption that breaks
here. `proximal-coca` (LEAD) is already the first step down that road; this result reinforces it as the
correct direction over a covariate patch.

## Honest standing update
- **lalonde-fix downgraded LEAD → NULL.** The LaLonde-specific finding stands (removing re75 restores
  detection *there*), but the general-fix claim is refuted.
- **Two concrete engineering carries** (founder-gated): (1) make the guard's floor **scale-aware**
  (standardize the NC residual, or set the floor in SE units) — the Orange-Belgium false-trip is
  partly this bug, and it would bite any continuous real-world negative control (revenue, session
  time); (2) the NC-nomination rule **"the negative control must not be collinear with an adjustment
  covariate"** stands — but it's a *selection* rule for picking good NCs, NOT a fix for when you're
  stuck with a collinear one.
- The guard remains a synthetic-validated heuristic with a now-doubly-confirmed real-data failure mode.
  It is **not** a real-world-validated instrument. Proximal is the honest next bet.
