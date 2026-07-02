# Non-LLM Method Bake-Off — Consolidated Findings

*Scratchpad research artifact. Public + synthetic data only — no partner data, numbers, or identity appear here. Synthetic results cap at MECH-ONLY; real-data results are LEAD-class (not promoted).*

## The question

Forget the LLM persona-sim. Using only a customer's data, which non-LLM methods recover the **directionally correct** A/B outcome — and where do they fail? Tested across 7 datasets, 3 waves, 40 sealed-before-scoring runs (each cell's directional prediction was sha256-committed before the estimator ran; no re-tuning to predictions).

## Datasets

| dataset | type | true effect | why included |
|---|---|---|---|
| Cookie Cats | real RCT | −0.82pp (counter-intuitive) | tiny counter-intuitive effect — the discriminating case |
| Hillstrom | real RCT | +4.52pp | large effect (un-stressable control) |
| GOTV | real RCT | +8.1pp | large effect, clean NC (prior vote) |
| Karlan | real RCT | + small, + a NULL (match-ratio) | counter-intuitive null |
| Orange-Belgium | real RCT | weak backfire | true effect runs against the naive sign |
| synthetic streaming v2/v3 | synthetic | heterogeneous (helps casual, hurts power) | the heterogeneity / modifier test |
| synthetic true-null | synthetic | 0 | specificity (don't invent effects) |

## Verdict — which methods are actually good

| method | verdict | where it works / fails |
|---|---|---|
| **naive diff-in-means** | baseline only | correct in a clean RCT; flips under *any* confounding |
| **causal adjusters** (T-learner, IPW, X-learner, DR/AIPW) | **the workhorse** | recover the sign under *observed* confounding; flip under *hidden*; struggle on tiny effects. IPW/X-learner slightly hardier than T-learner/DR |
| **"simulate-a-user" methods** (survival hazard, discrete-choice logit) | **add nothing directional** | collapse to the same adjusted logistic comparison; skip unless a genuine multi-alternative choice |
| **CATE per-segment** (X-learner) | **the one behavior-method win** | recovers segment sign-flips that plain ATE masks — *conditional on the effect-modifier* |
| **modifier auto-discovery** (CATE-variance gate → X-learner importance) | **works** | finds the true modifier above decoys, reproduces told-the-modifier sign recovery; honest-tree split over-fires on null (don't use it) |
| **NC-guard** | **the safety net** | turns "confidently wrong" → "honestly silent"; catches hidden confounding (needs one strongly-coupled control); over-abstains on weak effects |

## Wave-by-wave

**Wave 1 (Cookie Cats, Hillstrom).** Under *observed* confounding, naive diff-in-means inverted on Cookie Cats (the confidently-wrong "+0.218, later-gate wins") while every adjusted method held the correct negative sign — the core product value. Under *hidden* confounding all point estimates flipped together; only the NC-guard abstained. Survival hazard and conditional logit tracked T-learner sign-for-sign — no gain.

**Wave 2 (GOTV, Karlan, Orange + streaming heterogeneity).**
- Karlan's counter-intuitive NULL (bigger match ratio buys ~nothing) was cleanly recovered — no lift prior imposed.
- **Orange's weak backfire was missed by every method, even in the clean condition** — when the true effect is weak and contrarian in a way covariates don't explain, the adjusters track the wrong-pointing naive estimate; the guard's only protection is to abstain.
- **CATE beat plain ATE on heterogeneity** (first such win): ATE reports the feature *helping* power users; it's *hurting* them; only per-segment CATE catches it.

**Wave 3 (modifier auto-discovery).** Gate on the CATE-variance ratio (clean hetero/null separation), then name the axis with X-learner importance → recovers the true modifier and the per-segment signs without being told the segment. Honest-tree splits over-fire on noise; BLP is conservative but under-powered. Under confounding the modifier's identity survives but the negative segment's sign washes out.

## The production architecture this implies

1. **Estimability gate** — is the lever's outcome present and does the lever vary? If not → **abstain → measure** (this is the novel-feature case; no method can predict it).
2. **Estimate** via causal adjustment (X-learner / DR-AIPW) on existing per-user outcomes.
3. **NC-guard** → abstain if a strongly-coupled negative control shows hidden confounding, or the effect is below the bias floor.
4. **Heterogeneity** — CATE-variance ratio asks "is there a segment?"; if yes, X-learner importance names it → report per-segment effects (the "concentrated in segment X" finding).
5. **Output** — a directional estimate + any segment concentration, *or* an honest abstain with a sized test.

## Honest limits (load-bearing)

- **Hidden confounding flips every point estimate** — the guard is the only protection, and it needs at least one strongly-coupled negative control (a judgment call).
- **Weak / contrarian true effects are not recovered** — the methods recover counter-intuitive truth when it's a *confounding artifact* (Cookie Cats), not when the true effect is just small and against the grain (Orange). Abstain, don't estimate.
- **CATE's heterogeneity win degrades under confounding** — the segment is found, but its sign can wash out.
- **Modifier discovery needs the variance gate** — a raw tree split invents segments on noise.
- **Synthetic results cap at MECH-ONLY**; real-data results are LEAD, not promoted (needs naturally-confounded real data, ideally a live customer).
- **Behavior-simulation methods (survival, discrete-choice) earned no directional keep** on the tested data — they may matter only for genuine multi-alternative-choice or network/equilibrium levers, which weren't in the corpus.

## Bottom line

The durable non-LLM engine is **causal adjustment + the NC-guard**, with **CATE (gated by variance, named by importance) for heterogeneity**. It is trustworthy on the *estimable slice* and *honestly silent* elsewhere — which is exactly the behavior that makes a router (empirical where it can, abstain/measure or LLM otherwise) viable. The fancy "simulate-a-user" models did not beat plain causal adjustment directionally.
