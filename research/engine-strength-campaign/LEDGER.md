# Engine-Strength Campaign — Results Ledger

> **Auto-generated from `runs.jsonl` by `runstore.py` — do not hand-edit.**
> Regenerate: `python runstore.py ledger`. Nulls are findings and stay logged.

Verdict legend: `PROMOTED` (beat current best, held-out + replicated + adversarially
verified) · `LEAD` (positive once, needs replication) · `NULL` (tested, no signal) ·
`MECH-ONLY` (synthetic only, not real-data validated) · `RUNNING` · `PENDING`.

**Current best to beat:** empirical+LLM **router** (empirical/causal on the feature-expressible slice; LLM elsewhere, flagged). Baselines: roleplay 0.286, comparative 0.50.

**Multiple-comparisons honesty:** 13 verdicted / 12 backlog · **0 promoted, 5 open lead(s)**. (A single p<0.05 across many ideas is expected by chance — read wins against the attempt count.)

## Runs
| Idea | Title | Data | Prereg | Result (headline) | Verdict | Repl | Notes |
|---|---|---|---|---|---|---|---|
| iter0 | Synthetic Streamly Challenge — validate empirical core blind (10 regimes) | synthetic_streamly_10regimes (synthetic) | `028888ca…` | causal 7/8 vs naive 6/8 directional; advantage = the sign-flip case only; 3/10 wrong ALL at high confidence (calibration gap) | **MECH-ONLY** | — | codex wedged->self-blind gen; KEY FINDING: overlap-confidenc |
| T2-negative-control-guard | Negative-control outcome as a confounding guard (blind, 10 regimes) | synthetic_streamly_v2_negcontrol (synthetic) | `ef8aecb4…` | negative control CATCHES unobserved confounding overlap missed (P1), but pre-registered 0.02 band false-alarms on benign observed-confounding residual incl the sign-flip win (P2 fail) -> NULL by strict rule | **NULL** | — | STRONG sub-finding: P1 confirmed — neg-control reveals hidde |
| T2-negative-control-guard | Negative-control guard, magnitude floor 0.05 (HELD-OUT fresh data) | synthetic_streamly_v3_negcontrol (synthetic) | `5ded6c98…` | HELD-OUT replication: neg-control + 0.05 floor catches BOTH hidden-confounding errors with ZERO false alarms incl sign-flip win | **LEAD** | yes | FIRST LEAD. Floor 0.05 chosen on iter1 dev gap, validated on |
| T2-negative-control-guard | Negative-control guard on REAL Hillstrom RCT + adversarial sweep | hillstrom_real_rct_injected (public-real) | `96a2e6e8…` | neg-control guard REPLICATES on real RCT: 100% specificity, 75% sensitivity; 0.05 floor transferred synthetic->real; weak NC (newbie) silently misses bias | **LEAD** | yes·adv✓ | Strongest campaign result so far. NOT PROMOTED: confounding  |
| T2-negative-control-guard | Multi-NC CONSENSUS guard (max over several controls), held-out self-blind | synthetic_consensus_8sets (synthetic) | `bf203e85…` | consensus(max over NCs) recovers the unobserved-with-proxy cases a weak single control misses, WITHOUT losing specificity; fixes iter3 newbie failure | **LEAD** | yes | Synthetic ceiling MECH-ONLY but tagged LEAD (held-out + corr |
| T2-negative-control-guard | True-null guard: trust sign only if main effect exceeds the bias the control reveals | synthetic_truenull_8sets (synthetic) | `a77c1996…` | ratio rule |main|>1.5x|nc_residual| converts confident-wrong true-null calls into honest abstentions; clear effects still trusted; sub-bias real effects deferred to LLM | **LEAD** | yes | Closes the last open gap. Honest cost: a real effect SMALLER |
| new | Hypothesis decomposition (LLM as feature-extractor, frozen theory rule) on 14 product-change cases | portfolio_14_confirm (public-real) | `55579d4f…` | Decomposition into 6 mechanisms + frozen sign-rule = within 1 case of holistic. NULL, as pre-registered (H1). | **NULL** | — | Mechanism ratings inherit the same narrative bias as the hol |
| new | Selective prediction via k-vote agreement (meta-reliability) on 14 cases | portfolio_14_confirm (public-real) | `55579d4f…` | PRIMARY BET FAILED (H3). Internal vote-agreement is degenerate/unanimous -> no reliability gradient. Unlike the negative-control guard, internal consensus has no external grounding. | **NULL** | — | The sealed primary hypothesis. Killed cleanly by pre-registr |
| new | Reference-class leave-one-out few-shot analogy on 14 cases (iter1 0.79 -> robustness) | portfolio_14_confirm (public-real) | `caca1969…` | 0.79 was an ORDERING ARTIFACT. Median across reorderings = base-rate floor exactly -> NO discrimination. Downgraded LEAD->NULL by the sealed robustness gate. | **NULL** | no·adv✓ | LLM in-context order-sensitivity. The de-bias-the-change-win |
| new | Proximal CI (COCA single-NC correction): correct-and-answer vs detect-and-abstain | synthetic_equi_vs_violated + Hillstrom/CookieCats anchors (synthetic) | `26d3b497…` | 2018 proximal frontier (COCA) expands the slice CONDITIONALLY; deployable = COCA-correct INSIDE a guard, never alone | **LEAD** | no·adv✓ | Answers adversary critique (b). Promotion needs naturally-co |
| new | GUARD FAILS PROMOTION on canonical naturally-confounded real data (LaLonde NSW) | LaLonde NSW-vs-PSID/CPS (Dehejia-Wahba) (real) | `8673207a…` | The negative-control guard (campaign first validated win, 4 synthetic LEADs) FAILS on the canonical real confounded benchmark. RAW re74 placebo would have detected it perfectly (~0 RCT, huge confounded) but ADJUSTING the NC on a collinear proxy breaks detection. Reveals a fundamental adjust-vs-raw tension. | **NULL** | no·adv✓ | MAJOR honest negative. Validates adversary critiques (c) syn |
| nc-collinearity-fix | Re-validate LaLonde covariate-drop fix on synthetic-with-collinearity + 4 real RCTs | synthetic-collinearity-grid(1440u) + Hillstrom/GOTV/Karlan-List/Orange-Belgium (real) | `8fc805c7` | — | **NULL** | — |  |
| nc-collinearity-fix | NC-collinearity-aware adjustment restores guard detection on LaLonde (DOWNGRADED) | LaLonde NSW (experimental/PSID/CPS) (real) | `da091a88` | — | **NULL** | — |  |

## Pending backlog
T1–T12 not yet run — see `PLAN.md` (seed backlog, tiered by cost × info). The
order there is a default, not a rule.

_See `PLAN.md` for the protocol, guardrails, and the promotion decision rule._
