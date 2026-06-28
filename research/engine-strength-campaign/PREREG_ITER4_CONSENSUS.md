# Pre-registration — iteration 4: multi-negative-control CONSENSUS guard (held-out)

**Sealed before running** (sha256 committed alongside).

## Motivation (from iter3)
On real Hillstrom the guard's sensitivity was 75% (9/12): strong negative controls
(mens/womens/recency) tripped under the hidden confounder, but the WEAK one (`newbie`)
under-tripped. A single negative control is a gamble on coupling strength. Hypothesis: a
**consensus over several candidate negative controls — trip if the MAX |residual| exceeds the
floor — recovers the sensitivity a weak single control misses, without sacrificing specificity.**

## Design (self-blind, fresh secret seed; frozen estimator; floor 0.05)
Generate fresh synthetic datasets each emitting THREE negative controls of different coupling to
the confound signal: `nc_strong` (k≈1.3), `nc_mid` (k≈0.7), `nc_weak` (k≈0.25, the "newbie"
analogue). Regimes span the decision-relevant contrasts:
- clean_rct, confounded_observed (adjustment works) — specificity cases (guard must NOT trip).
- unobserved_no_proxy, unobserved_with_proxy — sensitivity cases (guard SHOULD trip).
Predict blind. Compare two rules on the SAME data: **single-weak** (`nc_weak` only) vs
**consensus** (max over the three). Self-blinding protocol identical to iter0-2 (secret
os.urandom seed, hidden regime→file shuffle, sealed key outside worktree, only sha256 committed).

## Falsifiable predictions
1. **P1 specificity:** consensus does NOT trip on any clean_rct / confounded_observed case
   (max residual over the three NCs stays < 0.05 where adjustment works).
2. **P2 sensitivity recovery:** on the unobserved regimes consensus trips on ≥ as many as the
   single-weak rule, and strictly more on at least one (the case nc_weak alone misses).
3. **P3 net:** consensus sensitivity ≥ single-weak sensitivity across all unobserved cases,
   with specificity preserved (P1).

## Honest risk (pre-registered)
Taking the MAX over three controls is three chances to exceed the floor → consensus could raise
false alarms on specificity cases (kills P1). If clean/observed max-residual creeps over 0.05,
that is a real cost of consensus (more controls = more false-trip risk) and the verdict is NULL/
partial, reported with the clean-side max distribution — not fudged.

## Decision rule
- P1 PASS and P2 PASS and P3 PASS → **LEAD** (MECH-ONLY ceiling — synthetic): consensus is the
  better guard; carry to the router design + a future real-data check.
- P1 fails (consensus false-alarms) → **NULL**: single well-chosen control is safer; log it.
- Synthetic ⇒ ceiling MECH-ONLY/LEAD; never PROMOTED without real microdata.
