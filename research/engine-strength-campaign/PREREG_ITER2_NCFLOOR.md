# Pre-registration — iteration 2: negative-control guard, magnitude floor (HELD-OUT)

**Sealed before running** (sha256 committed alongside).

## Motivation (from iter1)
iter1 confirmed P1 (negative controls catch unobserved confounding overlap misses) but failed
P2: at band 0.02 the guard also tripped 3 observed-confounding cases the core got RIGHT —
including the sign-flip win. iter1's negative-control magnitudes separated cleanly:
**observed-confounding residual ≤ 0.04, hidden-confounding signal ≥ 0.10.** A magnitude floor
of **0.05** sits in that gap. Choosing 0.05 from iter1 is a dev-set decision; this iteration
**validates it on a FRESH, independently-seeded self-blind dataset** (held-out test).

## Design
Generate a NEW v3 challenge (`CHALLENGE_SUFFIX=v3`, fresh `os.urandom` secret seed, same 10
regimes + neg_control). Predict blind with `NC_BAND=0.05`. Score against P1/P2 as in iter1.
No other change from iter1 — single hyperparameter (the floor) under test, out-of-sample.

## Falsifiable predictions
1. **P1 (held):** guard still trips on both unobserved-confounder regimes on fresh data.
2. **P2 (the target):** guard does NOT trip any observed-confounding case the core gets right
   (the 0.05 floor clears the benign ≤0.04 residual) — in particular it SPARES the sign-flip win.
3. **Net:** with-guard wrong actions ≤ without-guard wrong actions, and strictly fewer than
   iter1's false-alarm count (the floor recovers the wins iter1 wrongly abstained on).

## Decision rule
- P1 PASS **and** P2 PASS on fresh data => **LEAD** — a negative-control + 0.05-floor guard
  improves calibration out-of-sample; promote to the router design, pending a REAL-data
  replication (synthetic ceiling is MECH-ONLY).
- P1 fails, or P2 still false-alarms on a core win => **NULL** — the floor isn't robust
  out-of-sample; log the residual distribution and stop (do not keep nudging the number).
- Synthetic => verdict ceiling is MECH-ONLY/LEAD; never PROMOTED without real microdata.
