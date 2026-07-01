# Senu Study-Results Ledger — predicted‑vs‑actual, engine‑blind

> **Auto-generated from `studies.jsonl` by `studystore.py` — do not hand-edit.**
> Regenerate: `python studystore.py ledger`. Abstains and misses are findings and stay logged.

Each row is one real Senu case scored by the ONLY rule that counts: the engine's **blind**
prediction (made without the measured outcome) vs the **measured** truth. The sealed
`human_truth` hypothesis is a third, separate artifact — never the yardstick for a "win".

Outcome legend: `HIT` (blind sign == measured sign) · `MISS` (wrong sign) ·
`ABSTAIN` (engine declined — guard `CANT-VALIDATE` or low confidence; honest non-answer) ·
`PENDING` (not yet scored). Status legend: RUNNING · PENDING · SCORED · ABSTAINED · VOID.

**Scoreboard:** 0 case(s) · **sign accuracy 0/0** on scored cases · 0 honest abstain(s). Taxonomy patterns covered: —.

> Read accuracy against the attempt count and remember the discipline: a win is only
> `engine_blind` vs `measured`. Never author one artifact to match another.

## Cases
| Case | Pattern | Human‑sha | Prereg | Blind vs Measured | Outcome | N | Notes |
|---|---|---|---|---|---|---|---|

## Reproducibility contract
Every scored case must carry: (1) a sealed `human_truth_sha`, (2) a sealed `prereg_sha`
for the engine-blind call, (3) an `envelope_ref` to the raw `senu.export.v1` export, and
(4) a `benchmarkcase_ref` once the adapter has run. Re-running the sealed harness on the
referenced envelope must reproduce the `measured` block. See `README.md`.

_Feeds the #222 conversion_calibrator. Sibling of `../engine-strength-campaign/LEDGER.md`._
