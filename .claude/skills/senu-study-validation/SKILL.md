# senu-study-validation — is this senu game/study good enough to validate the Sidira engine?

Evaluate a study built on the **senu** data-collection platform for **Sidira-validation readiness** —
i.e., will running it actually produce a clean, decision-grade test of the engine's directional
prediction? This is the reusable form of the Beat-the-Clock / Counter-Intuition-Battery reviews:
it returns a verdict (**READY / NEEDS-CHANGES / NOT-A-FIT**) plus specific fixes, each routed to the
right owner (senu platform vs Sidira study-author).

> **Lives in sidira-simulator on purpose.** The criteria below are *Sidira's validation methodology*
> (study-content/methodology, our IP). senu is a generic platform that should NOT carry
> Sidira-specific validation logic. This skill *reads* senu artifacts (point it at a senu checkout)
> but the judgment is Sidira's.

## When to use
- Before running any senu study as a Sidira engine-validation (or before recruiting for it).
- When a senu agent/author asks "is this study good?" or proposes a new game/lever/outcome.
- Reviewing a senu PR that adds/changes a study's outcome, lever, prereg, power, or export.

## Inputs (where to look in the senu repo)
Point at the senu checkout (e.g. `~/Projects/senu`). The load-bearing artifacts:
- **Template + items + deal pool** — `packages/core/src/templates.ts` (the study's content, outcomes, trust-root pools).
- **Runtime / outcome computation** — e.g. `packages/core/src/<game>Runtime.ts`, `<game>Payout.ts`.
- **Export envelope (firewall)** — `packages/core/src/exportEnvelope.ts` (Table A `personaProfile` vs Table B `abOutcome`).
- **Validator / power gate** — `packages/core/src/<game>Validator.ts`.
- **Prereg** — `docs/prereg/<STUDY>.md`.
- **The game UI** — `apps/pwa/components/<Game>.tsx` (where outcome is actually defined — the ceiling bug usually hides here).

## The checklist — score every dimension

Each dimension: what to check · PASS bar · the failure it guards against · owner of any fix.

1. **Outcome variance / no ceiling — THE #1 KILLER.** What is the registered *primary outcome*, and
   does its distribution have real spread, or does it pin near a boundary?
   - PASS: a continuous or choice-between-options outcome with a sim/pilot-verified ~40–60% split (no
     >~80% mass at any value). FAIL: reflexive-yes / "did ≥1 thing" / conversion that ceilings ~90–100%
     (Beat-the-Clock's `converted = claims.length>0`; F&F's reflexive yes). Demand the sim/pilot
     distribution (mean, SD, %floor, %cap) BEFORE recruiting. *Owner: outcome **definition** = Sidira;
     ceiling/variance **diagnostic** = senu.*
2. **Counter-intuitive lever.** Is the live A/B manipulation genuinely counter-intuitive (the naive /
   more-is-better prediction differs from the registered human-truth direction), or an obvious
   sanity-check (e.g. savings-framing, "efficiency sort → more")? PASS: a human can't confidently call
   the sign, and the naive call is plausibly wrong. FAIL: obvious lever → a correct engine call proves
   nothing about the bias. *Owner: Sidira (study author).*
3. **Two-table leakage firewall.** Does the export cleanly separate **pre-treatment** persona features
   (Table A) from **sealed outcomes** (Table B)? Any pre-treatment field that encodes the outcome? Any
   path the predictor could read B before sealing? PASS: `exportEnvelope` keeps `personaProfile` and
   `abOutcome` distinct; outcomes excluded from the features-only slice. *Owner: senu (platform rail).*
4. **Sealed / blind / role-separated prereg.** Is there a sealed prereg with **three separated
   artifacts** — (a) the human-truth hypothesis, (b) the engine's *blind* prediction (locked before
   unblinding), (c) the measured truth — with **win = engine-vs-measured-truth, never vs the human
   hypothesis**, and nobody authoring one to match another? FAIL: §5-style collapse of the human
   hypothesis into "the Sidira prediction" (the Exp-1 leak). Changing the design after data = void.
   *Owner: prereg **content** = Sidira; **sealing mechanism** (hash/lock) = senu.*
5. **Power / N adequacy + achievability.** Is the registered N sufficient for the MDE on the *actual*
   primary (two-sample **mean** test for a continuous primary; two-proportion only for a binary
   primary — don't size a continuous outcome on a risk-difference), AND achievable for the recruitment
   plan? FAIL: N inflated-down by an implausibly large MDE; or required-N ≫ reachable cohort (→ run it
   as an explicit underpowered *pilot*, not the confirmatory test). *Owner: Sidira (registers N);
   power-gate mechanism = senu.*
6. **Comprehension + anti-random-clicking gate.** Is there a per-item response-time floor AND a *live*
   comprehension catch-trial (with per-player option-order shuffle so position-tappers don't pass)?
   FAIL: the F&F failure — confused/random clicking that timing/engagement audits can't see. Must be
   live, not just server-graded after. *Owner: senu (generic quality rail).*
7. **Predictability / reliability ceiling (NEW).** Given the planned N and the plausible effect size,
   is the effect resolvable AT ALL? Estimate the reliability ceiling (≈ 1 − sampling-var / observed-var;
   max achievable rank-corr ≈ √reliability). FAIL/abstain-flag: a small effect + modest N → most
   variance is sampling noise → no predictor (engine or human) can call it; don't stake a claim on it.
   *Owner: Sidira (methodology).*
8. **Arm-invariance / single clean manipulation.** For reward/payout studies, is the payout
   **arm-invariant** (the lever literally cannot move the ₹/reward)? Is the treatment a *single* change
   vs control (no confounds bundled)? FAIL: lever leaks into the outcome; multiple simultaneous changes.
   *Owner: senu (payout rail) + Sidira (lever design).*
9. **Renderable treatment.** Is the change a concrete rendered artifact the engine can simulate a
   persona reacting to (UI/copy/price/flow), not an opaque/internal tweak? FAIL: unrenderable change →
   the engine has nothing to react to. *Owner: Sidira.*
10. **Outcome-direction polarity declared.** Is each outcome's "higher = which direction" explicit
    (reverse-coded items flagged)? FAIL: silent reverse-coding (caught us on the Hewitt CalarcoS38
    Approval scale) → sign-inverted scoring. *Owner: Sidira.*

## Verdict format (return this)
```
STUDY: <name>   |  VERDICT: READY | NEEDS-CHANGES | NOT-A-FIT
Per-dimension: 1 ✅/❌ … 10 ✅/❌  (one line each, with the specific finding)
BLOCKERS (must fix before running): <list, each tagged [senu] or [Sidira]>
NICE-TO-HAVE: <list>
If NEEDS-CHANGES: the minimal change set + who owns each.
If NOT-A-FIT: why this design can't produce a clean engine test (and whether a redesign could).
```

## Precedent (calibrate against these)
- **Beat the Clock = NOT-READY → fixed:** `converted=≥1-claim` ceilinged (dim 1 ❌) + obvious
  savings-framing lever (dim 2 ❌). Fix: continuous `earnedPaise` primary + sealed ~50/50 bar; swap to
  the H2 loud-timer counter-intuitive lever; keep firewall/arm-invariant payout. Exp-2 sealed prereg.
- **Counter-Intuition Battery = GOOD, with gaps:** 4 genuinely counter-intuitive items, choice-between-
  options outcomes (variance by design), strong firewall/randomization (dims 1–3 ✅) — gaps: no prereg
  doc, thin comprehension gate, sunk-cost ceiling risk (dims 4,6 ⚠️).

## Rules of thumb
- A high score on prose/engagement but a ceilinged or obvious outcome = **NOT-A-FIT**. The outcome and
  the lever (dims 1–2) are the make-or-break; everything else is hygiene.
- Always route fixes by the **platform/study split**: senu owns generic rails (firewall, randomization,
  sealing mechanism, quality gate, ceiling diagnostics, arm-invariant payout); Sidira owns content
  (hypotheses, predicted directions, win rule, outcome definitions, items, power registration).
- If you can't get the sim/pilot outcome distribution, you cannot pass dim 1 — withhold READY.
