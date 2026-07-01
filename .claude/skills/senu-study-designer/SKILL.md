---
name: senu-study-designer
description: >-
  Use when you need to decide WHAT Senu game/study to run next to generate data that improves or validates
  the Sidira engine. This is the forward/generative advisor — it analyzes the engine's current capability
  gaps (the counter-intuitive taxonomy, the magnitude-flip wedge, the abstain boundaries, the negative-control
  guard, per-customer transfer) and emits a detailed, pre-registered study BRIEF. It is the complement to the
  existing methodological LAUNCH GATE (`preFlightCheck` in @senu/core): this skill designs the study; that gate
  validates it. Flow: /senu-study-designer -> study brief -> author StudySpec -> preFlightCheck -> launch.
  Invoke only when the user asks for a study idea / "what should we run on Senu" / engine-data planning.
---

# /senu-study-designer — What Senu study should we run to improve the engine?

## Overview

Senu is Sidira's **data factory**: it manufactures real, per-user, labeled A/B cases — especially the
*counter-intuitive* ones the engine most needs. But a factory that makes the wrong cases teaches the wrong
lessons. This skill answers the upstream question **"what study is worth running next?"** by reasoning from
the *engine's current gaps*, then emits a study brief detailed enough to author into a `StudySpec`.

**This skill does NOT check whether a study is methodologically valid.** That is the job of the existing
deterministic launch gate — `preFlightCheck` (and its battery / beat-the-clock variants) in
`@senu/core` (`packages/core/src/gameValidator.ts`). The two are complementary and run in sequence:

```
/senu-study-designer  →  a high-value study BRIEF (this skill: is it worth running?)
        ↓  (founder authors it into a StudySpec + builds the game)
preFlightCheck        →  pass/block LAUNCH GATE   (existing code: is it well-formed & contract-compliant?)
        ↓
launch on Senu → results → (store + score against the engine's blind prediction)
```

Never conflate the two. If asked "is this study valid/powered/leaky," that's `preFlightCheck`, not this skill.

## When to use / not use

- **Use:** "what study should we run on Senu next?", "design a game that improves the engine", "we have
  budget for N respondents — what's the highest-value case to manufacture?", planning the Senu Phase-1
  program, closing a specific engine gap (e.g., the dominance-flip / B2 gap).
- **Do not use:** validating an already-designed study (→ `preFlightCheck`); building the game UI; anything
  not about *choosing what data to manufacture*.

## The method — five steps

Work through these in order and show your reasoning. Read `reference/engine-needs.md` (beside this file)
for the current taxonomy, wedge, and known gaps before proposing anything.

### Step 1 — Read the engine's current state (gap analysis)
Pull the ground truth of what the engine can/can't do today, from:
- `founder-readout/simulation-engine-where-we-landed.md` (the wedge, the survivors, the honest limits),
- `research/engine-strength-campaign/LEDGER.md` (what's PROMOTED / LEAD / NULL / MECH-ONLY — the validated
  vs open frontier),
- `reference/engine-needs.md` (the ~12-pattern counter-intuitive taxonomy + the standing gaps).

Name the **specific capability gap** the next study should attack. Prefer, in priority order:
1. **The dominance-flip / B2 gap** — a *naturally-ambiguous* case where two opposing mechanisms net to a
   sign that flips on magnitude (the wedge's promotion blocker: we have only synthetic + n=1 real).
2. **An uncovered taxonomy pattern** — a counter-intuitive failure mode with no labeled case yet.
3. **A negative-control / confounding validation** — a case that stress-tests the watchdog's abstain.
4. **A per-customer transfer test** — does a mechanism learned elsewhere hold on a new population.

### Step 2 — Design the game around a MECHANISM, not a vibe
Specify:
- **The counter-intuitive mechanism** and, for a flip, the **two opposing mediators** (the "good" lever and
  the "bad" lever) whose *relative magnitude* decides the net sign.
- **The arms**, named at the source by ROLE per the locked calibration contract §11 (the game emits e.g.
  `calm`/`urgent`, `headline-A`/`headline-B` — never Sidira/engine build coupling; headline-arm first).
- **The primary outcome** — and it MUST carry *variance*, not a ≥1 ceiling binary (lesson: Beat-the-Clock
  Exp-2). Pick a metric with real spread across people.
- **The segments** you expect to respond differently (where the mix could flip the net).
- **The negative control** — a metric that should NOT move if the mechanism is what you think.

### Step 3 — Pre-register THREE separate artifacts (role-separation discipline)
This is non-negotiable and is what makes the result a real test:
1. **Sealed human-truth hypothesis** — what a thoughtful human predicts, committed (sha256) before data.
2. **Engine BLIND prediction** — what the engine predicts *without* seeing the measured outcome.
3. **Measured truth** — the realized result.
A WIN = engine-blind vs measured-truth agreement. **Never author one artifact to match another.** Register
only a genuinely *leaned* counter-intuitive direction (don't hedge to look right). Keep the three authored
by separate roles / at separate times.

### Step 4 — Size it (power-first, cost-aware)
- State the **MDE** and the **required N** for the primary outcome (this is what `preFlightCheck`'s blocking
  `power` check will enforce — design to pass it, don't discover it at the gate).
- Cost estimate at the current **~₹40/respondent**; give the total and flag if it strains the Phase-1 budget.

### Step 5 — Score the value and emit the brief
Rank the idea by **expected information gain for the engine** (which capability it extends/validates), not by
how "interesting" the game is. Then emit the brief in the output format below.

## Output format — the study brief

```
# STUDY BRIEF — <short name>

## Engine gap this closes
<the specific capability from Step 1, and why it's the highest-value next case>

## Mechanism
- Good lever (mediator+): <...>
- Bad lever (mediator−): <...>   (omit if single-mechanism)
- Net sign is decided by: <what magnitude relationship>

## Design
- Arms (role-named, §11): <...>          - Primary outcome (variance-carrying): <...>
- Segments to watch: <...>               - Negative control: <...>

## Pre-registration (3 artifacts — seal before data)
1. Human-truth hypothesis: <...>
2. Engine BLIND prediction: <how the engine would be run blind; what it should say>
3. Measured truth: <to be filled post-launch>
- Counter-intuitive lean being registered: <the direction we're betting against intuition>

## Power & cost
- Primary MDE: <...>   Required N: <...>   Cost @ ₹40/resp: <...>

## Why this is worth running (info gain)
<what the engine learns; how it advances PROMOTED vs LEAD; ties to which taxonomy pattern / gap>

## Next step
Author as StudySpec → run preFlightCheck (must pass `power` + `firewall_no_leakage` + `manipulation_present`)
→ launch → store results (see the study-results store) and score engine-blind-vs-measured.
```

## Hard rules

- **Stay on the generative side.** Recommend *what to run*; do not re-implement the `preFlightCheck`
  validity checks — point the user there for validation.
- **Role-separation always.** The engine's blind prediction and the human hypothesis are distinct sealed
  artifacts; a "win" is only engine-blind vs measured-truth. Flag any design that would let one be tuned to
  another.
- **Variance, not a binary ceiling.** Reject outcomes that top out at a ≥1 cap.
- **Contract-compliant arms.** Role-named at the source, headline-arm first, zero game↔engine build coupling
  (calibration contract §11).
- **Honest lean.** Only register a genuinely counter-intuitive direction; no hedging to look accurate.
- **Cite the current state.** Ground every recommendation in the LEDGER / readout / taxonomy, not vibes.

## Related
- Validator (downstream): `@senu/core` `preFlightCheck` — `packages/core/src/gameValidator.ts`.
- Calibration contract §11 + `StudySpec`: `packages/core/src/studySpec.ts`.
- Engine state: `founder-readout/simulation-engine-where-we-landed.md`,
  `research/engine-strength-campaign/LEDGER.md`.
- Results store + scoring: the study-results store (reproducible, sealed) — see its README.
- Taxonomy & gaps: `reference/engine-needs.md` (beside this file).
