# How We Measure Sidira — An Accuracy & Methodology Report (DRAFT)

> **Status:** internal draft, 2026-06-17. Customer-facing trust artifact in the
> **honest-null** framing. Founder-review gate before any publication to
> `sidira.ai/research`. Discloses the science of *measurement*; conceals the science of
> *prediction* (the drug-trial principle — publish endpoints/protocol/outcomes, never the
> synthesis route). See [[project-accuracy-whitepaper]] for the disclose/conceal contract.
>
> **Why this exists:** across four independent benchmarks the simulator did **not** clear
> a sellable in-scope directional-accuracy bar. Rather than bury that, this report makes the
> *discipline that produced those honest results* the product's differentiator. To a
> Kohavi-class buyer, "we pre-registered, caught our own false positives, and report the
> null" is a stronger trust signal than any cherry-picked win.

---

## 1. The problem we're attacking

Online controlled experiments (A/B tests) are the gold standard for product decisions, but
they are **slow** (weeks of live traffic), **expensive** (you ship to real users to learn),
and **gated on scale** (small teams can't power a clean test). Teams want a faster,
cheaper way to ask "which version is likely to win, and why?" *before* committing traffic.

Sidira simulates panels of audience-conditioned agents to generate **directional
hypotheses** and surface **weaknesses** ahead of a real test. The honest claim is a
hypothesis generator, **not** a digital-clone oracle — and chat with an agent is a
hypothesis aid, **never** evidence. This report is about how rigorously we hold ourselves
to measuring whether, and where, that generator is actually right.

## 2. Why naive LLM-persona approaches fail (and how that shaped our method)

A tempting shortcut is to ask a large language model "which of these two versions wins?"
We reject that as **invalid measurement**: it tests the model's *memory* of published
case studies, not its *reasoning* about an unseen product change. Two failure modes drove
our entire evaluation design:

- **Memorization / recitation.** On famous textbook cases (e.g. the Netflix
  browse-before-signup result) the engine can recite the known answer while flunking
  obscure cases — skill-shaped on the surface, recall underneath. We detect this with
  **held-out famous-case probes** scored separately.
- **Priors-echoing.** The engine tends to echo whatever prior its *framing* evokes rather
  than reason case-by-case. Framed as a marketing nudge, it predicts "people resist being
  marketed to"; framed as a product change, it predicts "the new thing is better." Same
  engine, opposite bias, flipped by framing alone — the signature of echoing a prior, not
  deliberating.

So we evaluate the **full simulation engine** on a **blinded** control-vs-treatment
stimulus (winner hidden and wording neutralized), scoring its *directional* prediction
against real experimental ground truth — never by asking a model to name a winner.

## 3. The evaluation framework (this is the part we *want* a skeptic to inspect)

Every claim in this report is produced under the following discipline. Each control was
added because it caught a real error of ours — they are not decorative.

- **External ground truth.** We grade against real randomized experiments: a 100k+
  Upworthy headline-CTR archive, the MineThatData Hillstrom email RCT (64k customers, real
  per-user features, randomized arms), and a curated portfolio of published product-change
  A/B experiments with known winners.
- **Out-of-sample, pre-registered.** Before each run we lock the prediction *and* the
  scoring rule into a file, fingerprinted with canonical-JSON SHA-256, committed **before**
  any result is observed. A prediction that turns out wrong in the *un-flattering*
  direction is therefore credible evidence, not spin.
- **Replication, not just discovery.** A promising number on the data that *suggested* it
  is only a hypothesis. We re-run locked predictions on **fresh** cases. If the number
  holds it replicated; if it collapses it was a sample artifact. (This caught two of our
  own would-be claims — see §4.)
- **Null-integrity certificate.** A label-permutation test confirms the statistical
  machinery is well-formed (the observed result sits where it should in a scrambled-label
  null). Passing the certificate is a *validity* check, **not** a win.
- **Leak audits by an independent adversary.** A separate agent, shown only the neutralized
  arm descriptions with winners stripped, tries to guess the winners. If its guesses track
  the truth, our wording leaks and we rewrite. On our hardest set the auditor scored
  *below chance* — confirming no leak.
- **Kohavi-proof baselines.** A result must beat not just chance (0.5) but the strongest
  naive constant strategy ("always predict treatment" / "always predict control") on that
  specific set, and is anchored against human-expert survey baselines.
- **No silent truncation.** Every stratum is reported, including the poor and underpowered
  ones.

## 4. Results — an honest null across four benchmarks, and the errors we caught

### 4.1 Upworthy headline CTR — a certified low-ceiling null
A pre-registered confirming run (n=60 fresh cases, pop=100) returned **rank-ρ = −0.11
(p=0.81)** — dead-centre in the scrambled-label null — and direction accuracy ≈ chance.
An earlier exploratory probe had shown a tempting **+0.386 (n=20, p=0.045)**; it **did not
replicate**. Pre-registration caught our own small-sample false positive before it became a
published claim. Real Upworthy lifts are intrinsically tiny (~0.1–0.5pp); the ceiling is
genuine and **panel-independent** (rebuilding the persona panel with real per-persona
behavioral seeds fixed a real internal variance bug but did not move the number) and
**model-independent** (a frontier model, below).

### 4.2 Hillstrom email RCT — a real, model-independent limit
On real per-user data with randomized arms, the engine showed an **ad-aversion sign
inversion**: it predicted the wrong direction on the email treatment (directional accuracy
0.0 on both conversion and visit outcomes under the pre-registered design), and treatment
heterogeneity was at chance — refuting our pre-registered prediction. A **model
comparison** (Claude Sonnet 4.6 vs the Groq baseline, identical pre-registered benchmark,
both outcomes) returned **identical** results — so a stronger model does not fix it. The
limit is a property of the framing-prior, not the model.

### 4.3 Product-change portfolio — the discovery, and the failed replication
This is the most instructive arc, because it shows the discipline working in real time.

1. An initial run scored **0.25 (2/8)** with an apparent "pro-change" tilt. A self-audit
   found the cause was **our own benchmark's valence leak** (benefit-laden treatment
   wording) plus an outcome leak — not a model property.
2. Neutralized and re-sealed, the clean set scored **0.625–0.75**; an independent
   adversarial audit walked us back to a conservative **5/8** (still hard cases left hard).
3. A powered expansion to 15 cases fell to **0.467** — below chance. A *blind* classifier
   split it: **substantive** changes 7/10 = 0.70, **micro/cosmetic** changes 0/5 = 0.00.
   The aggregate was **dilution**; a narrow signal seemed to survive on substantive cases.
4. **The confirmatory test.** We built 14 *fresh* substantive cases, deliberately balanced
   control-heavy (8 control-won / 6 treatment-won), independently blind-audited (auditor
   below chance → no leak), prediction sealed first. The 0.70 **did not replicate**:
   **dir_acc 0.286 (4/14)** — below chance and below both naive baselines; both per-class
   accuracies failed (control-class 2/8, treatment-class 2/6). Our pre-registered (and
   un-flattering) prediction that control-class would be low was correct.

A sharper diagnostic fell out: the residual bias is **more-is-better, not pro-change** —
across the 14 cases the engine picked the *bigger/richer* arm 12 times regardless of which
arm actually won, with near-zero effect magnitudes. When the change was a *reduction*, it
backed the control. So the prior is "more wins," a faint lean over an almost-flat signal.

### 4.4 What the four results say together
Across Upworthy (null), Hillstrom (real limit), the portfolio (chance/below on fresh
data), and internal calibration (correctly left un-fit, because no rank signal ever
appeared to calibrate against), there is **no certified in-scope directional positive
today**. The honest through-line is a faint framing-prior and little case-by-case
directional signal on counter-intuitive changes — measured rigorously and reported
plainly.

## 5. Limitations & responsible use

- The engine is a **directional hypothesis generator and weakness surfacer**, not a
  calibrated predictor. Absolute metric-rank calibration is **unproven and on the roadmap**,
  not claimed.
- Demonstrated skill on counter-intuitive product-change direction does **not** generalize
  to subtle/cosmetic changes or marketing nudges.
- Chat with an agent is a hypothesis aid, **never** evidence; agents are scaffolding for a
  diverse, audience-conditioned panel, not clones of real people.
- The strongest remaining in-scope avenue is **first-party validation on a customer's own
  real per-user data with known-good / known-bad changes** — published case narratives have
  been exhausted as a ground-truth source.

## 6. The customer takeaway

You should trust a vendor that shows you its measurement, including where it falls short.
We pre-register predictions, fingerprint them before we look at results, run independent
adversarial leak audits, demand replication on fresh data, and report the nulls. That
discipline caught two of our own false positives before they could become claims. The
product's present, defensible value is **fast, diverse, audience-grounded directional
hypotheses and weakness-surfacing to prioritize what to test** — with honest limits, and a
measurement program you can audit.

---

### Appendix — disclosure boundary (internal note, not for publication)
**Disclosed above (trust):** ground-truth sources, pre-registration + hash-commit,
out-of-sample/replication, null-integrity certificate, leak audits, Kohavi-proof baselines,
the false positives we caught, honest limits and posture.
**Concealed (moat):** persona-pack construction from real data (the GMM/centroid/posterior
ML), treatment/state-diff rendering, prompt composition, elicitation templates, aggregation
math, model choices, and the #221/#222 calibration mechanism. Methodology is described only
at "we condition simulated panels on real audience data and elicit per-metric behavior."

*Source artifacts: `hillstrom-benchmark/BENCHMARK_REPORT.md` (all §), `portfolio-benchmark/
portfolio_confirm_result.txt` + prereg/cases/audit files, `ACCURACY_CAMPAIGN_PRIMER.md`,
and the Upworthy confirm result on the bind-mount. Every number above is pulled from a
sealed, pre-registered run.*
