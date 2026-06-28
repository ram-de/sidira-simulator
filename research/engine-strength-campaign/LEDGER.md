# Engine-Strength Campaign — Results Ledger

> **Auto-generated from `runs.jsonl` by `runstore.py` — do not hand-edit.**
> Regenerate: `python runstore.py ledger`. Nulls are findings and stay logged.

Verdict legend: `PROMOTED` (beat current best, held-out + replicated + adversarially
verified) · `LEAD` (positive once, needs replication) · `NULL` (tested, no signal) ·
`MECH-ONLY` (synthetic only, not real-data validated) · `RUNNING` · `PENDING`.

**Current best to beat:** empirical+LLM **router** (empirical/causal on the feature-expressible slice; LLM elsewhere, flagged). Baselines: roleplay 0.286, comparative 0.50.

**Multiple-comparisons honesty:** 1 verdicted / 12 backlog · **0 promoted, 0 open lead(s)**. (A single p<0.05 across many ideas is expected by chance — read wins against the attempt count.)

## Runs
| Idea | Title | Data | Prereg | Result (headline) | Verdict | Repl | Notes |
|---|---|---|---|---|---|---|---|
| iter0 | Synthetic Streamly Challenge — validate empirical core blind (10 regimes) | synthetic_streamly_10regimes (synthetic) | `028888ca…` | causal 7/8 vs naive 6/8 directional; advantage = the sign-flip case only; 3/10 wrong ALL at high confidence (calibration gap) | **MECH-ONLY** | — | codex wedged->self-blind gen; KEY FINDING: overlap-confidenc |

## Pending backlog
T1–T12 not yet run — see `PLAN.md` (seed backlog, tiered by cost × info). The
order there is a default, not a rule.

_See `PLAN.md` for the protocol, guardrails, and the promotion decision rule._
