# Empirical-uplift spike — a different angle on engine accuracy

**Question.** Sidira's engine predicts product-change outcomes by *imagining* agent
reactions with an LLM. A completely different route: for a **feature-expressible**
change, *learn* the effect empirically from the customer's own behavioral logs with
a causal/uplift model — no LLM, no real-money panel. Does it work, and where does it
break?

**Method.** A self-contained Streamly-like synthetic feature store (2,500 users, 6
segments) with a **known, by-construction** heterogeneous treatment effect, so there
is ground truth to score against. The change under test ("autoplay-next on the home
feed") helps casual users but hurts power users; because power users have a high
retention base, the **true net 30-day-retention effect is negative — the opposite of
the obvious "more engagement = good" prior.** Assignment is observational and
confounded (autoplay rolled out to already-engaged users first), like a real log.

Predictors raced against the oracle ATE:
- **more-is-better prior** — fixed `+` sign; stands in for the LLM's uncontrolled prior.
- **naive diff-in-means** — the raw correlation (confounded).
- **IPW** + **T-learner / uplift** — propensity- and covariate-adjusted causal ML.

## Results

| Scenario | True ATE | prior (LLM stand-in) | naive diff-in-means | IPW | T-learner / uplift |
|---|---|---|---|---|---|
| **S1** feature-expressible, driver in the store | **−5.5pp** | +4.0pp ❌ | +0.9pp ❌ | **−4.8pp ✅** | **−3.9pp ✅** |
| **S2** real driver *not* in the store (unobserved confounder) | −3.2pp | +4.0pp ❌ | +3.7pp ❌ | +4.0pp ❌ | +4.2pp ❌ |

- **S1 — the win.** Where the change is feature-expressible and the driver is in the
  data, causal ML recovers the correct sign and near-exact magnitude, while *both* the
  obvious prior and the naive correlation get the sign **wrong**. A slice Sidira can
  predict **provably accurately, with zero LLM calls.**
- **S2 — the honest bound.** When the real driver isn't a column, *every* empirical
  method flips to the wrong sign. No ML rescues a missing variable. **This is where the
  LLM engine earns its keep** — it brings outside-world priors the feature store lacks.

## So what

Points to a **router, not a replacement**: detect feature-expressibility + sufficient
support → empirical engine (high-confidence, sellable); else → LLM engine (broad,
flagged). Carves out a defensible accurate slice now instead of betting on one paradigm.

The same router is the keystone of the **council-of-priors** idea (which agent/prior to
trust per hypothesis) — one classifier unlocks both routes.

## Run

```
/opt/homebrew/bin/python3.11 research/empirical-uplift-spike/uplift_spike.py
```

Deterministic (seed 20260627). Deps: numpy, scikit-learn.

## The baseline the council must beat (existing engine result)

`sessions/agent-behavior-spec/portfolio-benchmark/portfolio_comparative_result.json`:
the **single-agent engine scores 0.50 directional accuracy** (7/14) — chance — and
the errors are *systematic*: on high-counter-intuitive cases it predicts `treatment`
almost every time the real winner was `control` (ascarza, kanuri, algesheimer,
lambrecht, anderson — all "real: control, pred: treatment, MISS"). That is a hidden
**"the new thing wins" prior**. The council makes that prior explicit and plural and
lets a router decide when to distrust it. Target to beat: **0.50**.

## Status / next

- [x] **Phase A** — synthetic-fixture proof (`uplift_spike.py`). Empirical route beats
      the obvious prior on the feature-expressible slice (S1); honest bound where an
      unobserved confounder defeats it (S2).
- [x] **Phase C built** — `council_benchmark.py`: 4 explicit-prior members
      (naive / more-is-better / contrarian / base-rate-skeptic) + a regime router, with a
      **pre-registered** consolidation rule, blindness (members see only
      domain/control/treatment/metric), and 3 ablations (naive-only / council-unrouted /
      council-routed). Dry-run verified. **Needs an LLM key to execute** — `--dry-run`
      prints prompts without spend.
- [ ] **Phase B** — live LLM-engine vs causal-ML head-to-head. Better run on the
      *portfolio* (real product changes with a working harness) than on the synthetic
      fixture (no natural persona representation). **Blocked on:** no LLM key in env +
      empty `local-artifacts` (no persona packs).
- [ ] **Run gate** — both LLM phases need a `GROQ_API_KEY` (cheap; llama-3.3-70b) or an
      approved EC2-box run. Then: execute the council, compare to 0.50.

> Caveat: S1/S2 are constructed demonstrations, not measured outcomes — they prove the
> *mechanism*, not a live accuracy number. The council result will be n=8, directional-
> only, contamination-prone: a **signal**, not a validation.
