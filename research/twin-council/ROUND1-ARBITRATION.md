# Round 1 Arbitration

Arbiter: orchestrator (neutral). Inputs: `rounds/r1-claude.md` (20 claims),
`rounds/r1-codex.md` (25 claims).

## Verdict: strong convergence on the thesis; 5 open items.

Both councils independently arrived at the same spine, with no prompting toward
it. That is the signal worth noting.

## A. AGREED CORE (both councils, no material dissent)

- **A1. Not "digital twins" — a calibrated causal prior / triage instrument.**
  The live randomized experiment stays ground truth. (Codex C3, C21 · Claude C18)
- **A2. Target is sign + rank of the real ATE, not magnitude.** Magnitudes from
  LLM simulation are biased large and must be shrunk. (Codex C2, C10 · Claude C2, C7)
- **A3. A precise estimand is mandatory**: metric, population, treatment,
  control, horizon. No estimand → not directionally correct. (Codex C1 · Claude C2)
- **A4. The LLM/persona layer is a biased, sign-informative feature extractor**;
  it must never directly emit a calibrated probability or magnitude. (Codex C4 · Claude C5)
- **A5. A fitted calibration layer trained on real past experiments is
  mandatory** (maps raw signal → honest confidence, absorbs stated→revealed
  shrinkage). (Codex C16, C23 · Claude C6, C8)
- **A6. A no-persona LLM panel is a mandatory baseline.** Personas must earn
  their predictive lift. (Codex C8 · Claude C1, implied)
- **A7. An A/A placebo (null) test is a disqualifying gate.** (Codex C15 · Claude C19)
- **A8. Backtest integrity is the dominant threat**: hash-commit before
  unblinding + label-permutation/leakage test. (Codex C16 · Claude C12)
- **A9. Preserve population heterogeneity** and calibrate the agent population to
  the real joint covariate distribution; reject mode-collapsed runs. (Codex C5 · Claude C9, C10)
- **A10. Network / marketplace / equilibrium effects are out of scope** and route
  straight to experiment. (Codex C12 · Claude C11)
- **A11. The system must be allowed to abstain, and must never auto-kill
  tail-risk ideas.** Missed-winner (false-red) is the most dangerous error
  because it is unobservable. (Codex C19, C20 · Claude C4, C16)
- **A12. Sycophancy / demand effects must be tested**; elicitation should be
  blinded, order-randomized, behavioral (choice not Likert). (Codex C24 · Claude C8)

## B. OPEN ITEMS (to resolve in Round 2 — these are the only blockers)

- **D1 — Minimum historical-experiment count for a quantitative claim.**
  Claude: ≥ ~50 sign-balanced. Codex: < 50 cannot support a claim; 150–200 blind
  archive is the minimum *credible* range. Real numeric gap. Resolve to one
  floor + one "credible" target, with the statistical justification (CI width on
  SMR at that n).
- **D2 — Is decision regret THE criterion or one of several?** Claude centers
  the whole judgment on decision-regret-vs-status-quo-triage (value iff regret <
  0). Codex puts regret in a 7-metric basket (balanced acc, MCC, Brier, ECE,
  rank corr, regret, tail-winner recall). Reconcile: primary criterion vs.
  supporting diagnostics.
- **D3 — Persona role.** Codex: soft persona membership > hard assignment;
  personas are scaffolding. Claude: calibrate the joint covariate distribution
  by raking + variance floor. Unify into one population-construction spec.
- **D4 — What the confidence score reports.** Claude: a property of the
  calibration backtest's coverage (off-support → "uncalibrated"). Codex:
  distribution-elicited calibrated sign probability. Unify the semantics.
- **D5 — One agreed metric set + numeric GO thresholds.** Claude gives concrete
  gates (balanced SMR ≥ 0.70, 90% CI LB > 0.55; Kendall τ_b ≥ 0.3; ECE ≤ 0.10;
  regret < 0; A/A passed). Codex gives the metric basket but no single gate.
  Produce ONE gate both sign.

## C. Round 2 instruction

Each council reads BOTH r1 papers. It (1) marks AGREE/DISAGREE/REFINE on the
*other* council's ledger, (2) resolves D1–D5 with explicit reasoning, (3) emits a
revised ledger. Do not relitigate the agreed core (A1–A12) unless you have a
genuinely new objection. Goal: a single merged ledger both councils sign.
