# Engine-Strength Campaign — Results Ledger

> **Auto-generated from `runs.jsonl` by `runstore.py` — do not hand-edit.**
> Regenerate: `python runstore.py ledger`. Nulls are findings and stay logged.

Verdict legend: `PROMOTED` (beat current best, held-out + replicated + adversarially
verified) · `LEAD` (positive once, needs replication) · `NULL` (tested, no signal) ·
`MECH-ONLY` (synthetic only, not real-data validated) · `RUNNING` · `PENDING`.

**Current best to beat:** empirical+LLM **router** (empirical/causal on the feature-expressible slice; LLM elsewhere, flagged). Baselines: roleplay 0.286, comparative 0.50.

**Multiple-comparisons honesty:** 6 verdicted / 12 backlog · **0 promoted, 4 open lead(s)**. (A single p<0.05 across many ideas is expected by chance — read wins against the attempt count.)

## Runs
| Idea | Title | Data | Prereg | Result (headline) | Verdict | Repl | Notes |
|---|---|---|---|---|---|---|---|
| iter0 | Synthetic Streamly Challenge — validate empirical core blind (10 regimes) | synthetic_streamly_10regimes (synthetic) | `028888ca…` | causal 7/8 vs naive 6/8 directional; advantage = the sign-flip case only; 3/10 wrong ALL at high confidence (calibration gap) | **MECH-ONLY** | — | codex wedged->self-blind gen; KEY FINDING: overlap-confidenc |
| T2-negative-control-guard | Negative-control outcome as a confounding guard (blind, 10 regimes) | synthetic_streamly_v2_negcontrol (synthetic) | `ef8aecb4…` | negative control CATCHES unobserved confounding overlap missed (P1), but pre-registered 0.02 band false-alarms on benign observed-confounding residual incl the sign-flip win (P2 fail) -> NULL by strict rule | **NULL** | — | STRONG sub-finding: P1 confirmed — neg-control reveals hidde |
| T2-negative-control-guard | Negative-control guard, magnitude floor 0.05 (HELD-OUT fresh data) | synthetic_streamly_v3_negcontrol (synthetic) | `5ded6c98…` | HELD-OUT replication: neg-control + 0.05 floor catches BOTH hidden-confounding errors with ZERO false alarms incl sign-flip win | **LEAD** | yes | FIRST LEAD. Floor 0.05 chosen on iter1 dev gap, validated on |
| T2-negative-control-guard | Negative-control guard on REAL Hillstrom RCT + adversarial sweep | hillstrom_real_rct_injected (public-real) | `96a2e6e8…` | neg-control guard REPLICATES on real RCT: 100% specificity, 75% sensitivity; 0.05 floor transferred synthetic->real; weak NC (newbie) silently misses bias | **LEAD** | yes·adv✓ | Strongest campaign result so far. NOT PROMOTED: confounding  |
| T2-negative-control-guard | Multi-NC CONSENSUS guard (max over several controls), held-out self-blind | synthetic_consensus_8sets (synthetic) | `bf203e85…` | consensus(max over NCs) recovers the unobserved-with-proxy cases a weak single control misses, WITHOUT losing specificity; fixes iter3 newbie failure | **LEAD** | yes | Synthetic ceiling MECH-ONLY but tagged LEAD (held-out + corr |
| T2-negative-control-guard | True-null guard: trust sign only if main effect exceeds the bias the control reveals | synthetic_truenull_8sets (synthetic) | `a77c1996…` | ratio rule |main|>1.5x|nc_residual| converts confident-wrong true-null calls into honest abstentions; clear effects still trusted; sub-bias real effects deferred to LLM | **LEAD** | yes | Closes the last open gap. Honest cost: a real effect SMALLER |

## Pending backlog
T1–T12 not yet run — see `PLAN.md` (seed backlog, tiered by cost × info). The
order there is a default, not a rule.

_See `PLAN.md` for the protocol, guardrails, and the promotion decision rule._
