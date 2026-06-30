# Persona information-sufficiency gate (Gate 1)

The first gate of the router, at the persona level. Before any simulation, it asks:
**does this persona pack encode the variable the hypothesis turns on?** It is the
persona-level twin of the empirical half's feature-expressibility gate — one
estimability law, two surfaces.

## How it decides (cheap → rigorous)
| Layer | Check | Fails when |
|---|---|---|
| **L0 presence** | the mechanism feature(s) exist in the pack schema | demographics-only pack, mechanism variable simply absent |
| **L1 variance** | non-degenerate across the population (numeric spread / categorical entropy floor) | feature present but constant — carries zero discriminating info |
| **L2 discriminability** | a flexible model (HistGBM) recovers a **pre-test behavioral proxy** from the feature(s), beating a permutation null (p ≤ 0.05 and score − null ≥ margin) | feature varies but is unrelated to the behavior the mechanism implicates |

`PASS = L0 ∧ L1 ∧ L2`.

## What PASS means (and does not)
PASS is **necessary, not sufficient.** It removes the *information-impossible* cases —
it does **not** promise the engine predicts the direction correctly. That is the job
of the in-distribution accuracy test (`../PREREG_INDISTRIBUTION_GATE_DRAFT.md`), which
scores the engine separately on the gate's PASS vs FAIL sets. The strong claim under
test: the engine beats base-rate **only on PASS**.

## Outcome-blind by construction
The gate never sees the A/B outcome. L2 scores against a **pre-test** behavioral proxy
(e.g. historical browse-abandon rate for "overload"), so the PASS/FAIL partition can be
committed before any outcome is unsealed.

## Files
- `persona_info_gate.py` — `evaluate(pack, HypothesisSpec, GateConfig) -> GateResult`; `partition(cases)` for the pre-committed split.
- `test_persona_info_gate.py` — self-validating: synthetic packs with KNOWN answers (sufficient / absent / degenerate / noise / partial-coverage); asserts the gate classifies all five correctly. **All pass.**
- `test_result.json` — last run's per-case detail.

## Run
```
/opt/homebrew/bin/python3.11 test_persona_info_gate.py
```

## Not yet frozen
`GateConfig` thresholds (L1 spread/entropy floors, L2 alpha/margin) are placeholders.
They get fixed WITH a partner's real feature distributions and sha-sealed before the
in-distribution run — never tuned post-hoc. `evaluate()` works today on any per-user
feature table; a real persona pack's sample-rows / feature-store reduce to exactly that.
