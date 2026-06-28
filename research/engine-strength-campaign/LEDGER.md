# Engine-Strength Campaign — Results Ledger

Living record of every idea tested. **Nulls are findings and stay logged.** Verdict legend:
`PROMOTED` (beat current best, held-out + replicated + adversarially verified) ·
`LEAD` (positive once, needs replication) · `NULL` (tested, no signal) ·
`MECH-ONLY` (works on synthetic, not real-data validated) · `RUNNING` · `PENDING`.

**Current best to beat:** empirical+LLM **router** (empirical/causal on the feature-
expressible slice; LLM elsewhere, flagged). Baselines: roleplay 0.286, comparative 0.50.

**Attempts counter (for multiple-comparisons honesty):** 0 verdicted / 12 backlog.

| # | Idea | Data | Prereg sha | Result | Verdict | Replicated? | Notes |
|---|------|------|-----------|--------|---------|-------------|-------|
| 0 | Synthetic Streamly Challenge (validate empirical core end-to-end, blind) | codex synthetic (10 regimes) | `ffcb…`(challenge contract) | — | RUNNING | n/a | codex generating; Claude predicts blind → scorecard |
| T1 | Test-time scaling on comparative call (k=32–64, structured) | portfolio 14 + 8 | — | — | PENDING | — | cheap; does comparative have latent signal |
| T2 | Calibrated abstention (conformal / selective) | portfolio + synthetic | — | — | PENDING | — | improve WHEN-to-trust, not the point guess |
| T3 | Uncorrelated-error ensemble | existing predictions | — | — | PENDING | — | near-free; stack only if errors independent |
| T4 | Retrieval / case-based forecasting | experiment corpus (to build) | — | — | PENDING | — | predict by analogy to similar past A/Bs |
| T5 | LLM as feature-engineer (not predictor) | Cookie Cats / Hillstrom / synthetic | — | — | PENDING | — | LLM picks covariates; math predicts |
| T6 | Stronger causal learners (AIPW / X-learner / causal forest) | Cookie Cats / Hillstrom / synthetic | — | — | PENDING | — | extends the survivor; heterogeneity |
| T7 | Mechanism decomposition (beh-econ calculator) | literature priors + portfolio | — | — | PENDING | — | signed primitives, composed |
| T8 | CATE / segment-ranking instead of ATE | Hillstrom / synthetic (heterogeneous) | — | — | PENDING | — | maybe good at WHO, bad at net sign |
| T9 | Few-shot / fine-tune on real (change→direction) pairs | portfolio + Senu feeder | — | — | PENDING | — | the calibration-data wall |
| T10 | Meta-analytic base-rate prior | published A/B meta-data | — | — | PENDING | — | Bayesian direction prior by change-type |
| T11 | Adversarial debate (vs independent-vote council) | portfolio 14 | — | — | PENDING | — | does debate elicit truth here |
| T12 | LLM-counterfactual augmentation, calibrated | feature-expressible slice | — | — | PENDING | — | high risk (LLM bias); kill fast |

_Updated as iterations complete. See PLAN.md for the protocol, guardrails, and decision rule._
