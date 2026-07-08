# Kill-rate backtest v0 — readout (#602)

**Date:** 2026-07-08 · **Prereg:** `PREREG_KILLRATE_V0.md` (sealed before scoring) · **Script:** `backtest_v0.py`
**Corpora:** portfolio 8 (narratives) · Hillstrom (raw) · Upworthy archive (4,869 tests, raw per-arm)
**Bottom line:** the pre-registered binary power-kill is REFUTED as a selective
predictor; the run redirects #602/#594 rather than certifying a headline number.

## Pre-registered results (reported as sealed, no rule swaps)

**Portfolio 8:** coverage 1/8. Published narrative cases carry no pre-launch
quantitative facts (traffic, baseline), so K1/K2 are uncomputable and K3/K4
have no corpus. The one assessable case (Cookie Cats: n=45k/arm, baseline 0.19)
→ RUN (MDE 3.8% rel); it failed in reality, so v0 caught 0/1 failures there.
**Finding: this corpus was built for directional scoring and cannot feed a
kill-rate backtest. The deciding version of #602 needs a real experiment log
with per-experiment traffic/baseline — i.e. a design partner's history.**

**Hillstrom (per-metric triage):** visit metric → RUN (MDE 7.9% rel), actually
significant — correct. Conversion metric → KILL (MDE 35.8% rel), actually
significant — **false kill**, and an instructive one: the true effect was
+118% relative (email-vs-no-email is a sledgehammer, not a product tweak). The
prereg's flat "plausible effects ≤10%" prior is wrong across intervention
classes → priors must be per mechanism class, which is exactly #525's job.

**Upworthy (n=4,869):** DEGENERATE. K1 kills 100% of tests (every test's MDE
≈55% rel > 22.6% prior), including the 45% that concluded. Sensitivity ×0.5/×2
doesn't rescue it.

## Diagnosis (the real finding)

Upworthy allocated a near-uniform slot to every test (n/arm IQR 2.7k–4.1k;
~17% power for the median winning effect). **When every experiment has the
same design, power carries no selective information**: AUC of ex-ante size
predicting a conclusive result = **0.555 (n_arm) / 0.579 (n_total)** — coin-flip.
A graded exploratory rule (kill if power<θ, any θ) kills wasted slots and
winners at the same rate. What separates Upworthy's winners from its wasted
slots is the *effect size* — which headline actually differed — and that is
knowable ex ante only through a content/analogy prior (K4), out of v0 scope.

## What this means for the product (redirects, not kills, the thesis)

1. **The power kill is prescriptive, not selective.** Its product form is the
   #594 design sheet — "at your traffic this design has 17% power; resize to
   n=X or don't run" — issued BEFORE allocation, where Sidira sits. As an
   ex-post failure predictor at fixed uniform design, it is provably useless
   (AUC 0.55). Upworthy's honest triage output was: "your standard slot only
   ever detects lucky-large effects."
2. **Selective kill power — cutting the 70–92% — must come from effect priors
   (K3/K4), i.e. the experiment corpus (#525 + Senu pairs + cross-customer
   catalog).** v0 empirically confirms the corpus-moat thesis from the other
   direction: without priors, grounded triage can only say "underpowered,"
   not "not worth running."
3. **Priors must be mechanism-class-conditional** (Hillstrom false kill:
   marketing-email effects are 10× product-tweak effects).
4. **v1 spec:** partner experiment log (varied designs, real traffic/baselines)
   + per-class effect priors; pre-register a graded rule — expected
   P(conclusive | class prior, design), kill below threshold — and score
   sensitivity + false-kill as in v0. Public corpora cannot certify this:
   narratives lack numbers, Upworthy lacks design variation.

## Scoreboard vs prereg endpoints

| endpoint | result |
|---|---|
| portfolio coverage | 1/8 (endpoint met: quantified the corpus gap) |
| portfolio kills on failures | 0/1 assessable |
| Hillstrom | 1 correct RUN, 1 false KILL (class-prior lesson) |
| Upworthy kill on wasted / false-kill | 100% / 100% — rule degenerate, refuted |
| headline "saved X of Y at Z%" | NOT CERTIFIABLE from public corpora — v1 needs partner log |
