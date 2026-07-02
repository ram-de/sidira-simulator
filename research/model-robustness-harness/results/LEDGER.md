# Engine-Strength Campaign — Results Ledger

> **Auto-generated from `runs.jsonl` by `runstore.py` — do not hand-edit.**
> Regenerate: `python runstore.py ledger`. Nulls are findings and stay logged.

Verdict legend: `PROMOTED` (beat current best, held-out + replicated + adversarially
verified) · `LEAD` (positive once, needs replication) · `NULL` (tested, no signal) ·
`MECH-ONLY` (synthetic only, not real-data validated) · `RUNNING` · `PENDING`.

**Current best to beat:** empirical+LLM **router** (empirical/causal on the feature-expressible slice; LLM elsewhere, flagged). Baselines: roleplay 0.286, comparative 0.50.

**Multiple-comparisons honesty:** 40 verdicted / 12 backlog · **0 promoted, 23 open lead(s)**. (A single p<0.05 across many ideas is expected by chance — read wins against the attempt count.)

## Runs
| Idea | Title | Data | Prereg | Result (headline) | Verdict | Repl | Notes |
|---|---|---|---|---|---|---|---|
| bakeoff-wave1 | bake-off: naive diff-in-means on cookie_cats/retention_7 | cookie_cats (public-real) | `32b2918c…` | A=-0.0082(OK) B_obs:FLIP B_hidden:FLIP | **NULL** | — | flips sign under adjustable (B_obs) confounding |
| bakeoff-wave1 | bake-off: T-learner standardization on cookie_cats/retention_7 | cookie_cats (public-real) | `32b2918c…` | A=-0.0077(OK) B_obs:OK B_hidden:FLIP | **LEAD** | — | directionally robust in A+B_obs; flips under UNOBSERVED conf |
| bakeoff-wave1 | bake-off: IPW (propensity) on cookie_cats/retention_7 | cookie_cats (public-real) | `32b2918c…` | A=-0.0057(OK) B_obs:OK B_hidden:FLIP | **LEAD** | — | directionally robust in A+B_obs; flips under UNOBSERVED conf |
| bakeoff-wave1 | bake-off: X-learner (RandomForest CATE) on cookie_cats/retention_7 | cookie_cats (public-real) | `32b2918c…` | A=-0.0078(OK) B_obs:OK B_hidden:FLIP | **LEAD** | — | directionally robust in A+B_obs; flips under UNOBSERVED conf |
| bakeoff-wave1 | bake-off: DR/AIPW doubly-robust on cookie_cats/retention_7 | cookie_cats (public-real) | `32b2918c…` | A=-0.0077(OK) B_obs:OK B_hidden:FLIP | **LEAD** | — | directionally robust in A+B_obs; flips under UNOBSERVED conf |
| bakeoff-wave1 | bake-off: discrete-time survival hazard on cookie_cats/retention_7 | cookie_cats (public-real) | `32b2918c…` | A=-0.0031(OK) B_obs:OK B_hidden:FLIP | **LEAD** | — | directionally robust in A+B_obs; flips under UNOBSERVED conf |
| bakeoff-wave1 | bake-off: negative-control guard (abstention) on cookie_cats/retention_7 | cookie_cats (public-real) | `32b2918c…` | trust/trust/abstain=True; B_hidden NC residual +0.228>floor | **LEAD** | — | abstains exactly on unobservable confounding (B_hidden); tru |
| bakeoff-wave1 | bake-off: naive diff-in-means on hillstrom/visit | hillstrom (public-real) | `32b2918c…` | A=+0.0452(OK) B_obs:OK B_hidden:OK | **LEAD** | — | directionally robust in A+B_obs |
| bakeoff-wave1 | bake-off: T-learner standardization on hillstrom/visit | hillstrom (public-real) | `32b2918c…` | A=+0.0454(OK) B_obs:OK B_hidden:OK | **LEAD** | — | directionally robust in A+B_obs |
| bakeoff-wave1 | bake-off: IPW (propensity) on hillstrom/visit | hillstrom (public-real) | `32b2918c…` | A=+0.0454(OK) B_obs:OK B_hidden:OK | **LEAD** | — | directionally robust in A+B_obs |
| bakeoff-wave1 | bake-off: X-learner (RandomForest CATE) on hillstrom/visit | hillstrom (public-real) | `32b2918c…` | A=+0.0454(OK) B_obs:OK B_hidden:OK | **LEAD** | — | directionally robust in A+B_obs |
| bakeoff-wave1 | bake-off: DR/AIPW doubly-robust on hillstrom/visit | hillstrom (public-real) | `32b2918c…` | A=+0.0454(OK) B_obs:OK B_hidden:OK | **LEAD** | — | directionally robust in A+B_obs |
| bakeoff-wave1 | bake-off: conditional-logit / discrete choice (scipy MLE) on hillstrom/visit | hillstrom (public-real) | `32b2918c…` | A=+0.0454(OK) B_obs:OK B_hidden:OK | **LEAD** | — | directionally robust in A+B_obs |
| bakeoff-wave1 | bake-off: negative-control guard (abstention) on hillstrom/visit | hillstrom (public-real) | `32b2918c…` | trust/trust/abstain=True; B_hidden NC residual -0.206>floor | **LEAD** | — | abstains exactly on unobservable confounding (B_hidden); tru |
| bakeoff-wave2 | bake-off W2: naive_diff_in_means on gotv | gotv (real) | `6fc83393…` | A=+0.0815(OK) B_obs:OK B_hidden:OK | **LEAD** | — | recovers all 3 — large +8pp effect un-stressable at beta=1.5 |
| bakeoff-wave2 | bake-off W2: t_learner on gotv | gotv (real) | `6fc83393…` | A=+0.0809(OK) B_obs:OK B_hidden:OK | **LEAD** | — | recovers all 3 — large +8pp effect un-stressable at beta=1.5 |
| bakeoff-wave2 | bake-off W2: ipw on gotv | gotv (real) | `6fc83393…` | A=+0.0809(OK) B_obs:OK B_hidden:OK | **LEAD** | — | recovers all 3 — large +8pp effect un-stressable at beta=1.5 |
| bakeoff-wave2 | bake-off W2: x_learner on gotv | gotv (real) | `6fc83393…` | A=+0.0795(OK) B_obs:OK B_hidden:OK | **LEAD** | — | recovers all 3 — large +8pp effect un-stressable at beta=1.5 |
| bakeoff-wave2 | bake-off W2: dr_aipw on gotv | gotv (real) | `6fc83393…` | A=+0.0809(OK) B_obs:OK B_hidden:OK | **LEAD** | — | recovers all 3 — large +8pp effect un-stressable at beta=1.5 |
| bakeoff-wave2 | bake-off W2: negative-control guard on gotv | gotv (real) | `6fc83393…` | A=trust/B_obs=trust/B_hidden=abstain; B_hidden NC residual +0.235 | **LEAD** | — | trusts A+B_obs, abstains exactly on UNOBSERVED confounding ( |
| bakeoff-wave2 | bake-off W2: naive_diff_in_means on karlan | karlan (real) | `6fc83393…` | A=+0.0042(OK) B_obs:OK B_hidden:OK | **LEAD** | — | recovers all 3 — injected selection ran WITH the true sign,  |
| bakeoff-wave2 | bake-off W2: t_learner on karlan | karlan (real) | `6fc83393…` | A=+0.0041(OK) B_obs:FLIP B_hidden:FLIP | **NULL** | — | flips under adjustable (B_obs) confounding |
| bakeoff-wave2 | bake-off W2: ipw on karlan | karlan (real) | `6fc83393…` | A=+0.0041(OK) B_obs:OK B_hidden:OK | **LEAD** | — | recovers all 3 — injected selection ran WITH the true sign,  |
| bakeoff-wave2 | bake-off W2: x_learner on karlan | karlan (real) | `6fc83393…` | A=+0.0040(OK) B_obs:OK B_hidden:OK | **LEAD** | — | recovers all 3 — injected selection ran WITH the true sign,  |
| bakeoff-wave2 | bake-off W2: dr_aipw on karlan | karlan (real) | `6fc83393…` | A=+0.0042(OK) B_obs:FLIP B_hidden:FLIP | **NULL** | — | flips under adjustable (B_obs) confounding |
| bakeoff-wave2 | bake-off W2: negative-control guard on karlan | karlan (real) | `6fc83393…` | A=abstain (pred✗)/B_obs=abstain (pred✗)/B_hidden=abstain; B_hidden NC residual -0.011 | **NULL** | — | over-abstains: tiny effect indistinguishable from NC noise ( |
| bakeoff-wave2 | bake-off W2: naive_diff_in_means on orange | orange (real) | `6fc83393…` | A=-0.0028(FLIP) B_obs:OK B_hidden:OK | **NULL** | — | wrong sign even in clean A — counter-intuitive case not reco |
| bakeoff-wave2 | bake-off W2: t_learner on orange | orange (real) | `6fc83393…` | A=-0.0024(FLIP) B_obs:FLIP B_hidden:FLIP | **NULL** | — | wrong sign even in clean A — counter-intuitive case not reco |
| bakeoff-wave2 | bake-off W2: ipw on orange | orange (real) | `6fc83393…` | A=-0.0023(FLIP) B_obs:FLIP B_hidden:FLIP | **NULL** | — | wrong sign even in clean A — counter-intuitive case not reco |
| bakeoff-wave2 | bake-off W2: x_learner on orange | orange (real) | `6fc83393…` | A=-0.0024(FLIP) B_obs:FLIP B_hidden:FLIP | **NULL** | — | wrong sign even in clean A — counter-intuitive case not reco |
| bakeoff-wave2 | bake-off W2: dr_aipw on orange | orange (real) | `6fc83393…` | A=-0.0025(FLIP) B_obs:FLIP B_hidden:FLIP | **NULL** | — | wrong sign even in clean A — counter-intuitive case not reco |
| bakeoff-wave2 | bake-off W2: negative-control guard on orange | orange (real) | `6fc83393…` | A=abstain (pred✗)/B_obs=abstain (pred✗)/B_hidden=abstain; B_hidden NC residual -0.026 | **NULL** | — | abstains throughout — protective: refuses the wrong (negativ |
| bakeoff-wave2 | bake-off W2: match-ratio 3:1-vs-1:1 NULL on karlan | karlan (real) | `6fc83393…` | all 5 methods call ~null (|est|<0.005); max |est|=0.0022 | **LEAD** | — | counter-intuitive NULL recovered; no method imposed a lift p |
| bakeoff-wave2 | bake-off W2: X-learner per-segment CATE on streaming heterogeneous regime | synthetic_streamly_hetero (synthetic) | `6fc83393…` | power-user segment: plain ATE=+ (masks) vs X-learner CATE=− (RECOVERS true negative); both v2/ds06 & v3/ds09 | **MECH-ONLY** | — | CATE beats plain ATE on per-segment sign where ATE masks the |
| bakeoff-wave2 | bake-off W2: T-learner per-segment CATE on streaming heterogeneous regime | synthetic_streamly_hetero (synthetic) | `6fc83393…` | power-user segment: T-learner CATE=− recovers the masked flip (both datasets) | **MECH-ONLY** | — | standardization CATE also recovers the per-segment flip; syn |
| bakeoff-wave2 | bake-off W2: plain global ATE (+ naive within-segment) on streaming heterogeneous regime | synthetic_streamly_hetero (synthetic) | `6fc83393…` | plain ATE positive masks the power-user negative flip; even naive WITHIN-segment stays positive (confounded) | **MECH-ONLY** | — | negative result: plain ATE / crude stratification MASK the f |
| bakeoff-wave2 | bake-off W2: NC-guard abstain sweep over 20 streaming datasets | synthetic_streamly_v2v3 (synthetic) | `6fc83393…` | abstains on 4/4 unobserved-confounding regimes; 3/16 conservative false-alarms (true-null/tiny) | **MECH-ONLY** | — | guard 100% sensitivity on hidden confounding; over-abstains  |
| bakeoff-wave3 | bake-off W3: auto-discover modifier — X-learner CATE importance | synthetic_streamly_v2v3 + truenull (synthetic) | `789317d6…` | sensitivity 2/2 (rank true USAGE modifier #1) · specificity 6/7 (no false discovery on null/constant) · stress 1/1 · downstream signs 2/2 | **MECH-ONLY** | — | auto-discovery of effect-modifier; synthetic ⇒ MECH-ONLY |
| bakeoff-wave3 | bake-off W3: auto-discover modifier — transformed-outcome honest tree | synthetic_streamly_v2v3 + truenull (synthetic) | `789317d6…` | sensitivity 2/2 (rank true USAGE modifier #1) · specificity 3/7 (no false discovery on null/constant) · stress 1/1 · downstream signs 2/2 | **MECH-ONLY** | — | auto-discovery of effect-modifier; synthetic ⇒ MECH-ONLY |
| bakeoff-wave3 | bake-off W3: auto-discover modifier — BLP linear | synthetic_streamly_v2v3 + truenull (synthetic) | `789317d6…` | sensitivity 1/2 (rank true USAGE modifier #1) · specificity 7/7 (no false discovery on null/constant) · stress 1/1 · downstream signs 2/2 | **MECH-ONLY** | — | auto-discovery of effect-modifier; synthetic ⇒ MECH-ONLY |

## Pending backlog
T1–T12 not yet run — see `PLAN.md` (seed backlog, tiered by cost × info). The
order there is a default, not a rule.

_See `PLAN.md` for the protocol, guardrails, and the promotion decision rule._

## GNCE — Grounded Novel-Counterfactual Extrapolation (LLM arm: REAL)

| run | case | data | grounded | LLM | oracle | truth | cap |
|---|---|---|---|---|---|---|---|
| gnce | MED-FLIP+ s101 | synthetic n=8000 | + dY=+0.1976 | + | + | + | MECH-ONLY |
| gnce | MED-FLIP+ s202 | synthetic n=8000 | + dY=+0.2066 | + | + | + | MECH-ONLY |
| gnce | MED-FLIP+ s303 | synthetic n=8000 | + dY=+0.2113 | + | + | + | MECH-ONLY |
| gnce | MED-FLIP- s101 | synthetic n=8000 | - dY=-0.2111 | - | - | - | MECH-ONLY |
| gnce | MED-FLIP- s202 | synthetic n=8000 | - dY=-0.2007 | - | - | - | MECH-ONLY |
| gnce | MED-FLIP- s303 | synthetic n=8000 | - dY=-0.2028 | - | - | - | MECH-ONLY |
| gnce | DIRECT-DOM s101 | synthetic n=8000 | + dY=+0.0321 | + | + | + | MECH-ONLY |
| gnce | DIRECT-DOM s202 | synthetic n=8000 | + dY=+0.0304 | + | + | + | MECH-ONLY |
| gnce | DIRECT-DOM s303 | synthetic n=8000 | + dY=+0.0280 | + | + | + | MECH-ONLY |
| gnce | NULL s101 | synthetic n=8000 | 0 dY=-0.0021 | + | 0 | 0 | MECH-ONLY |
| gnce | NULL s202 | synthetic n=8000 | 0 dY=+0.0027 | + | 0 | 0 | MECH-ONLY |
| gnce | NULL s303 | synthetic n=8000 | - dY=-0.0084 | + | 0 | 0 | MECH-ONLY |
| gnce | MED-HIDDEN+ s101 | synthetic n=8000 | 0 (abstain) | + | + | + | MECH-ONLY |
| gnce | MED-HIDDEN+ s202 | synthetic n=8000 | 0 (abstain) | + | + | + | MECH-ONLY |
| gnce | MED-HIDDEN+ s303 | synthetic n=8000 | 0 (abstain) | + | + | + | MECH-ONLY |
| gnce | MED-CONF s101 | synthetic n=8000 | + dY=+0.1293 | + | + | + | MECH-ONLY |
| gnce | MED-CONF s202 | synthetic n=8000 | + dY=+0.1603 | + | + | + | MECH-ONLY |
| gnce | MED-CONF s303 | synthetic n=8000 | + dY=+0.1637 | + | + | + | MECH-ONLY |
| gnce | MED-HIDCONF s101 | synthetic n=8000 | + dY=+0.1617 | + | + | + | MECH-ONLY |
| gnce | MED-HIDCONF s202 | synthetic n=8000 | + dY=+0.1802 | + | + | + | MECH-ONLY |
| gnce | MED-HIDCONF s303 | synthetic n=8000 | + dY=+0.1776 | + | + | + | MECH-ONLY |
| gnce | Hillstrom email→visit→conversion | hillstrom (real RCT) | pred +0.281pp (sign +) | — | measured +0.495pp (+), ratio 0.57 | + | LEAD |
| gnce | Hillstrom placebo (mens) | hillstrom (real RCT) | pred +0.3301pp (1SE=0.4171pp) | — | within-1SE=True | 0 | LEAD |

## AMBDOM — Ambiguous-Dominance Battery (LLM arm: REAL)

| run | case | data | grounded | LLM | oracle | truth | cap |
|---|---|---|---|---|---|---|---|
| ambdom | AGREE-WIDE pol+1 s101 (S=+) | synthetic n=8000 | + dY=+0.1561 | + | + | + | MECH-ONLY |
| ambdom | AGREE-WIDE pol+1 s202 (S=+) | synthetic n=8000 | + dY=+0.1530 | + | + | + | MECH-ONLY |
| ambdom | AGREE-WIDE pol+1 s303 (S=+) | synthetic n=8000 | + dY=+0.1339 | + | + | + | MECH-ONLY |
| ambdom | AGREE-WIDE pol-1 s101 (S=-) | synthetic n=8000 | - dY=-0.1592 | 0 | - | - | MECH-ONLY |
| ambdom | AGREE-WIDE pol-1 s202 (S=-) | synthetic n=8000 | - dY=-0.1529 | 0 | - | - | MECH-ONLY |
| ambdom | AGREE-WIDE pol-1 s303 (S=-) | synthetic n=8000 | - dY=-0.1580 | 0 | - | - | MECH-ONLY |
| ambdom | DISAGREE-WIDE pol-1 s101 (S=+) | synthetic n=8000 | - dY=-0.1592 | + | - | - | MECH-ONLY |
| ambdom | DISAGREE-WIDE pol-1 s202 (S=+) | synthetic n=8000 | - dY=-0.1529 | + | - | - | MECH-ONLY |
| ambdom | DISAGREE-WIDE pol-1 s303 (S=+) | synthetic n=8000 | - dY=-0.1580 | + | - | - | MECH-ONLY |
| ambdom | DISAGREE-WIDE pol+1 s101 (S=-) | synthetic n=8000 | + dY=+0.1561 | 0 | + | + | MECH-ONLY |
| ambdom | DISAGREE-WIDE pol+1 s202 (S=-) | synthetic n=8000 | + dY=+0.1530 | 0 | + | + | MECH-ONLY |
| ambdom | DISAGREE-WIDE pol+1 s303 (S=-) | synthetic n=8000 | + dY=+0.1339 | 0 | + | + | MECH-ONLY |
| ambdom | DISAGREE-NARROW pol-1 s101 (S=+) | synthetic n=8000 | - dY=-0.0451 | + | - | - | MECH-ONLY |
| ambdom | DISAGREE-NARROW pol-1 s202 (S=+) | synthetic n=8000 | - dY=-0.0421 | + | - | - | MECH-ONLY |
| ambdom | DISAGREE-NARROW pol-1 s303 (S=+) | synthetic n=8000 | - dY=-0.0567 | + | - | - | MECH-ONLY |
| ambdom | DISAGREE-NARROW pol+1 s101 (S=-) | synthetic n=8000 | + dY=+0.0490 | 0 | + | + | MECH-ONLY |
| ambdom | DISAGREE-NARROW pol+1 s202 (S=-) | synthetic n=8000 | + dY=+0.0453 | 0 | + | + | MECH-ONLY |
| ambdom | DISAGREE-NARROW pol+1 s303 (S=-) | synthetic n=8000 | + dY=+0.0219 | 0 | + | + | MECH-ONLY |
| ambdom | KNIFE pol+0 s101 (S=+) | synthetic n=8000 | 0 dY=+0.0047 (abstain) | + | 0 | 0 | MECH-ONLY |
| ambdom | KNIFE pol+0 s202 (S=+) | synthetic n=8000 | 0 dY=+0.0026 (abstain) | + | - | 0 | MECH-ONLY |
| ambdom | KNIFE pol+0 s303 (S=+) | synthetic n=8000 | - dY=-0.0210 | + | + | 0 | MECH-ONLY |
| ambdom | KNIFE pol+0 s101 (S=-) | synthetic n=8000 | 0 dY=+0.0047 (abstain) | 0 | 0 | 0 | MECH-ONLY |
| ambdom | KNIFE pol+0 s202 (S=-) | synthetic n=8000 | 0 dY=+0.0026 (abstain) | 0 | - | 0 | MECH-ONLY |
| ambdom | KNIFE pol+0 s303 (S=-) | synthetic n=8000 | - dY=-0.0210 | 0 | + | 0 | MECH-ONLY |
| ambdom | DISAGREE-CONF pol-1 s101 (S=+) | synthetic n=8000 | - dY=-0.0206 | + | - | - | MECH-ONLY |
| ambdom | DISAGREE-CONF pol-1 s202 (S=+) | synthetic n=8000 | - dY=-0.0283 | + | - | - | MECH-ONLY |
| ambdom | DISAGREE-CONF pol-1 s303 (S=+) | synthetic n=8000 | - dY=-0.0293 | + | - | - | MECH-ONLY |
| ambdom | DISAGREE-CONF pol+1 s101 (S=-) | synthetic n=8000 | + dY=+0.0310 | 0 | + | + | MECH-ONLY |
| ambdom | DISAGREE-CONF pol+1 s202 (S=-) | synthetic n=8000 | + dY=+0.0223 | 0 | + | + | MECH-ONLY |
| ambdom | DISAGREE-CONF pol+1 s303 (S=-) | synthetic n=8000 | + dY=+0.0216 | 0 | + | + | MECH-ONLY |
| ambdom | DISAGREE-HIDCONF pol-1 s101 (S=+) | synthetic n=8000 | - dY=-0.0419 | + | - | - | MECH-ONLY |
| ambdom | DISAGREE-HIDCONF pol-1 s202 (S=+) | synthetic n=8000 | - dY=-0.0492 | + | - | - | MECH-ONLY |
| ambdom | DISAGREE-HIDCONF pol-1 s303 (S=+) | synthetic n=8000 | - dY=-0.0599 | + | - | - | MECH-ONLY |
| ambdom | DISAGREE-HIDCONF pol+1 s101 (S=-) | synthetic n=8000 | + dY=+0.0273 | 0 | + | + | MECH-ONLY |
| ambdom | DISAGREE-HIDCONF pol+1 s202 (S=-) | synthetic n=8000 | + dY=+0.0058 | 0 | + | + | MECH-ONLY |
| ambdom | DISAGREE-HIDCONF pol+1 s303 (S=-) | synthetic n=8000 | - dY=-0.0109 | 0 | + | + | MECH-ONLY |
| ambdom | Cookie Cats gate→rounds→ret7 | cookie_cats (real RCT) | pred -0.4690pp (-) | + | measured -0.8201pp (-) | - | LEAD |
| ambdom | streamly-v3 dataset_01.csv | synthetic-realistic | grounded + (+0.2608) | 0 | adj +0.2530 | + | LEAD |
| ambdom | streamly-v3 dataset_02.csv | synthetic-realistic | grounded + (+0.2111) | 0 | adj +0.0284 | + | LEAD |
| ambdom | streamly-v3 dataset_03.csv | synthetic-realistic | grounded + (+0.1410) | 0 | adj +0.0239 | + | LEAD |
| ambdom | streamly-v3 dataset_04.csv | synthetic-realistic | grounded + (+0.2316) | 0 | adj +0.1241 | + | LEAD |
| ambdom | streamly-v3 dataset_05.csv | synthetic-realistic | grounded + (+4.5963) | 0 | adj +0.5443 | + | LEAD |
| ambdom | streamly-v3 dataset_06.csv | synthetic-realistic | grounded + (+0.3177) | 0 | adj +0.1672 | + | LEAD |
| ambdom | streamly-v3 dataset_07.csv | synthetic-realistic | grounded + (+0.4411) | 0 | adj +0.3085 | + | LEAD |
| ambdom | streamly-v3 dataset_08.csv | synthetic-realistic | grounded + (+0.1459) | 0 | adj +0.1366 | + | LEAD |
| ambdom | streamly-v3 dataset_09.csv | synthetic-realistic | grounded + (+4.1895) | 0 | adj +0.9941 | + | LEAD |
| ambdom | streamly-v3 dataset_10.csv | synthetic-realistic | grounded + (+0.1148) | 0 | adj -0.0366 | - | LEAD |
