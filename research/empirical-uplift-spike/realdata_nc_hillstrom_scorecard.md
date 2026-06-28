# Negative-control guard on REAL data (Hillstrom) — Scorecard (iter3)

Design sealed in `PREREG_ITER3_NCREAL.md` (sha256 `96a2e6e8`). Frozen `causal_estimator`,
NC_BAND=0.05 (from iter2, **not re-tuned**). T = Womens E-Mail; main Y = `visit`
(true RCT lift ≈ +4.52pp); negative control = a pre-treatment flag the email cannot cause;
hidden confounder = spend `history` (excluded from the adjustment set).

## Pre-registered result (negative control = `mens`, seed 20260629)
| Check | Value | Verdict |
|---|---|---|
| P1 specificity — clean RCT does NOT trip | clean nc = **−0.0015** | PASS |
| P2 sensitivity — injected nc ≫ clean nc | injected nc = **−0.0911** | PASS |
| P3 trips on injected (\|nc\| > 0.05) | 0.0911 > 0.05 | PASS |
| main `visit` estimate | clean **+4.54pp** / injected **+3.18pp** (true +4.52) | guard fires when biased |

**Verdict: LEAD — real-data replication of iter2.** The clean half uses the genuine randomized
trial (no injection); the 0.05 floor learned on synthetic data transferred to real data.

## Adversarial verification (4 negative controls × 3 seeds = 12 cells)
- **Specificity: 100% (12/12).** No negative control trips on the clean RCT → the guard never
  falsely abstains on a real experiment. (Strongest property — low false-alarm on truth.)
- **Sensitivity: 75% (9/12).** `mens`, `womens`, `recency` trip under the hidden confounder at
  every seed (recency strongly, nc ≈ +0.6); **`newbie` under-trips** (−0.016…−0.029 < 0.05).

## Honest finding (pre-registered risk, confirmed)
A negative control only catches the bias if it is **strongly coupled to the confounding**.
`newbie` is weakly coupled to `history` (and what coupling exists is laundered by the observed
covariates), so the guard misses the bias there. Implication for the router: **picking a valid,
strong negative control is a domain/LLM judgment** — a weak choice fails silently. The guard is
necessary and now real-data-validated, but it is not automatic.

## Why LEAD and not PROMOTED
The specificity test is fully real, but the **confounding is injected**, not naturally occurring,
and this is **one** real dataset. PROMOTED is reserved for naturally-occurring confounding or a
live customer deployment. Recorded LEAD with replication + adversarial verification done.
