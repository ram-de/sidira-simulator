# Engine-Strength Campaign — an autonomous, honest search for what makes Sidira's engine strong

**Standing directive (2026-06-28).** Run a loop: propose unconventional, unexplored ideas
to strengthen the simulation engine; pre-register; secure data (existing / public / codex-
generated, blind); test; score honestly; promote only what truly beats the current best.

**What we already know (the starting line).**
- Per-arm persona roleplay = **0.286** (below chance). Comparative forecaster = **0.50**
  (chance). Council-of-priors = **rejected** (worse than naive). On the 14-case set, NO
  LLM-prompting method beats chance.
- The **one survivor**: the empirical/causal route on the feature-expressible slice, wrapped
  in a **router** (empirical where data supports it; LLM elsewhere, flagged). That router IS
  the current best. Everything here is measured against it.

---

## Hard guardrails (NON-NEGOTIABLE — the campaign is worthless without them)

1. **Pre-register every test.** Sealed prediction + design + sha256 BEFORE running (the
   codex-seal pattern from SYNTHETIC_STREAMLY_CHALLENGE). Role separation: whoever designs
   the test does not author the result to match.
2. **One positive = a LEAD, not a result.** No idea is "promoted" until it **replicates on a
   held-out set** it wasn't tuned on. (Upworthy and naive-beats-engine both died at this gate.)
3. **Multiple-comparisons honesty.** Track how many ideas tested; a single p<0.05 across 20
   ideas is expected by chance. Apply correction; report the count of attempts alongside any win.
4. **Nulls are findings.** Every idea gets logged in LEDGER.md with its verdict, including
   "tested, null." Nulls are not buried or retried until they fluke positive.
5. **Synthetic ≠ validation.** Synthetic/codex data tests MECHANISM; only real data with
   FOUND (not injected) confounding counts toward "sellable." Label every result by data type.
6. **No fabrication.** Never invent numbers, datasets, or outcomes. If a test can't be run,
   say so. Adequate power required before a null is called definitive.

## Decision rule — what "makes the engine strong" means
An idea is **promoted into the engine/router** only if it:
> beats the current-best router on a **pre-registered, adequately-powered, HELD-OUT** test,
> AND **replicates** once on fresh data, AND survives an **adversarial verification** pass
> (independent agent tries to refute it). Otherwise: logged as lead (needs more data) or null.

---

## The loop (each iteration)

1. **Pick / generate** an idea (from the backlog below, or a new one — a council/Workflow may
   brainstorm + diversify candidates).
2. **Pre-register** a sharp, falsifiable prediction + test design; seal + hash.
3. **Secure data** — reuse (portfolio, Cookie Cats, Hillstrom, synthetic Streamly), find
   public, or have codex generate it BLIND (generator seals truth, predictor runs blind).
4. **Build** the minimal harness; **run**; **score** vs the pre-registration.
5. **Verdict** → LEDGER.md (win-lead / null / mechanism-only). If win-lead → schedule a
   held-out replication + adversarial-verify before promotion.
6. **Report** at each verdict (and immediately on any promotion-grade result). **Loop.**

"Council if need be" = use multi-agent orchestration as a TOOL (brainstorm idea variants,
adversarially verify a positive). It does NOT mean resurrecting the rejected council-of-
priors *predictor*.

---

## Seed backlog — unexplored / unconventional ideas (tiered by cost × expected info)

### Tier 1 — cheap, high-information (test first)
- **T1. Test-time scaling on the comparative call.** We only tried k=4. Push k=32–64 with
  structured reasoning (explicit base-rate anchoring + devil's-advocate self-consistency).
  Does the comparative call have latent signal that more sampling extracts? Cheap to settle.
- **T2. Calibrated abstention (conformal / selective prediction).** Don't improve the point
  guess — learn WHEN to trust it. A router that commits only on calibrated-confident cases
  and abstains otherwise can make the PRODUCT strong even at chance on hard cases. Honest,
  sellable ("we tell you when we know").
- **T3. Uncorrelated-error ensemble.** Even at-chance methods stack ABOVE chance if their
  errors are independent. Measure error-correlation across {empirical, comparative,
  retrieval}; stack if uncorrelated. Pure analysis on existing predictions — nearly free.
- **T4. Retrieval / case-based forecasting.** Featurize past real A/B experiments; for a new
  hypothesis, retrieve the k most similar and predict by analogy (how human experts actually
  forecast). Needs an experiment corpus + a similarity embedding.

### Tier 2 — hybrid LLM×empirical (the most promising new territory)
- **T5. LLM as feature-engineer, not predictor.** LLM proposes WHICH covariates/interactions
  /confounders matter for a hypothesis; the empirical model does the math. Each side plays to
  strength (LLM = world knowledge of confounders; math = unbiased estimation).
- **T6. Stronger causal learners.** We used T-learner + IPW. Add doubly-robust AIPW,
  X-learner, DR-learner, causal forests. Better heterogeneity handling → extends the survivor.
- **T7. Mechanism decomposition (behavioral-economics calculator).** Decompose a change into
  signed primitives (friction ±, choice overload, loss aversion, social proof) each with an
  empirical prior from literature; compose. Interpretable + unconventional.
- **T8. CATE / segment-ranking instead of ATE.** Maybe the engine is bad at net sign but good
  at "who responds." Test whether it ranks segments by responsiveness even when the average
  sign is wrong — a different, possibly defensible value proposition.

### Tier 3 — data-hungry / heavier (gated on a real-outcome corpus)
- **T9. Few-shot / fine-tune on real (change → direction) pairs.** The calibration data wall.
  Feed the portfolio + Senu-generated + any gathered real outcomes; few-shot then fine-tune
  a direction predictor. The Senu feeder (project memory) is the intended corpus source.
- **T10. Meta-analytic base-rate prior.** Fit a Bayesian prior over effect-direction by change-
  type from published A/B meta-data; update with customer data. A "base-rate engine."
- **T11. Adversarial debate.** Two agents argue treatment-wins vs control-wins before a judge
  (adversarial, unlike the independent-vote council). Test if debate elicits truth here.
- **T12. LLM-counterfactual augmentation, calibrated.** When the feature store is thin,
  generate synthetic agents from the LLM but CALIBRATE them on the empirical slice where both
  exist. High risk (imports LLM bias) — test honestly, kill fast if it doesn't calibrate.

(Backlog is living — ideas added/reordered as results come in. Order is a default, not a rule.)

## Gating & status
- **Starts after** the Synthetic Streamly Challenge is scored (validates the empirical core
  end-to-end first). That scoring is iteration 0.
- Running ledger: `LEDGER.md` (this dir). Results land on a feature branch → PR per batch.
