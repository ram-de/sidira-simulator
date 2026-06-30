# Alt-method battery — the "think-differently" loop (2026-06-28)

A pre-registered loop testing whether a **structurally different use of the LLM** beats chance on
the 14-case product-change directional benchmark, after every prior LLM-narrative method (per-arm
roleplay 0.286, comparative 0.50, council worse, naive retracted) landed at/below chance. Run on
Groq `llama-3.3-70b-versatile`, blinded stimulus, every prediction sealed (sha256) before its run.

## The four methods (all sealed in PREREG_ALT_METHODS.md, sha 55579d4f)

| Method | Idea | Result | Verdict |
|---|---|---|---|
| **M0 holistic** | "which version wins?", k=5 majority (anchor) | 7/14 (0.50) | chance (anchor) |
| **M1 decomposition** | LLM rates 6 mechanisms → frozen theory sign-rule (LLM never predicts winner) | 7/13 (0.54) | **NULL** |
| **M2 analogy** | leave-one-out few-shot: other 13 labeled cases in-context, predict by analogy | iter1 0.79 → robustness 0.57 | **NULL** (artifact) |
| **M3 selective** | abstain on low vote-agreement (meta-reliability) | degenerate (all unanimous) | **NULL** |

## What the pre-registration caught

My sealed primary bet was **H3 — selective prediction** ("the path is knowing *when* you're right,
not being right more often"). It **failed**: the model votes 5/5 unanimous on all 14 cases even at
temp 0.4, so internal agreement has no gradient to threshold on. Unlike the negative-control guard
(which works because the control is an *external* check), internal self-consensus has nothing to
anchor it.

I bet **against** H2 (analogy). It surprised me at 11/14 = 0.79 in iter1 — beating the base-rate
floor (0.57) by correctly flipping 4/6 treatment cases, via a legible mechanism (the in-context
examples de-bias M0's *change-wins* prior). So I stress-tested it (PREREG_ITER2, sha caca1969):
**5 example-orderings × 3 seeds = 15 passes**. Median = **0.5714, exactly the base-rate floor**;
9/15 runs collapse to it, best ordering only 0.71. The 0.79 was an **in-context-ordering artifact**.
Downgraded LEAD → NULL by the sealed gate.

## The convergent conclusion

**Every structurally-different LLM-narrative method tested now lands at chance on this set:**
holistic, decomposition, analogy, selective, council, naive. This is no longer one negative result —
it's a *robust convergence*. The binding constraint is confirmed to be **validation data, not
method**: 14 narrative cases (no per-case features, no external A/B corpus to retrieve from) cannot
power any method past chance, and the one apparent exception died under a robustness gate.

The only orthogonal survivor remains the **empirical/causal route** (the negative-control guard) —
because it learns from a customer's *per-user data*, not from narratives, and is provably accurate
on the feature-expressible slice. The reference-class idea (M2) is the one that *would* extend the
LLM path **if** a real, representative, labeled A/B corpus existed — which is exactly the data
investment already on the roadmap (portfolio growth, the Senu made-to-order BenchmarkCase factory,
the #222 conversion calibrator). Method exploration converges on the data work, now with receipts.

## Honest limits
- n=14, underpowered: no verdict here is stronger than NULL/LEAD by construction.
- All on one model (llama-3.3-70b) + one curated set. A representative corpus is the missing input
  for the analogy direction, not a different prompt.
- Recorded in the campaign run-store as `altmethod-decomposition`, `altmethod-selective`,
  `altmethod-analogy` (all NULL).
