# F&F validation harness — BLINDED engine prediction + role-separated scoring (#444)

This directory holds the machinery that turns the friends-&-family game into a
**blinded, pre-registered, role-separated** test of the simulation engine. It
asks one question: *given a persona pack built from these players, does the
engine predict these players' real A/B behaviour?*

> ⚠️ **This is the MACHINERY.** It does **not** run the real sealed experiment —
> there are no real players yet. The included end-to-end test runs on **SYNTHETIC
> outcomes** and produces a verdict that is **NOT a real validation result**. The
> moment real friends-&-family players have played, the real sealed `player_outcomes`
> (Table B) replaces the synthetic one and the scorer is run against THAT.

## The named failure mode

The validity lens named the one thing that sinks a validation like this:
**wanting it to pass.** Everything below — the blind, the seal, the role split,
the hash gate, the score-once rule — exists to make it structurally hard for the
person who wants a GO to manufacture one.

## The two roles (DIFFERENT people)

| Role | Runs | Sees | Must NOT see |
|------|------|------|--------------|
| **Engine-runner** | `predict.py --seal` | the persona pack, the game's micro-A/B descriptions, the audited obvious priors | **Table B `player_outcomes`** (the answer key) |
| **Scorer** | `score.py` | Table B, the sealed `PREREG_FF.json` | (verifies the seal hash before scoring) |

The engine-runner is **blind to outcomes by construction**: `predict.py` reads
only the pack + `obvious_priors.json`, and a runtime guard
(`_assert_no_outcome_access`) trips loudly if any outcomes artifact is ever opened.

## The sealed workflow

```
                ENGINE-RUNNER (blind)                    SCORER (different person)
                ─────────────────────                    ─────────────────────────
  1. predict.py --seal
       runs the FULL engine (SimulationRunner) on
       the committed friends_family pack, once per
       micro-A/B, with a per-item conversion Hypothesis
       → predicted winning arm + confidence per item
       → ALSO records the "always-pick-obvious" placebo
       → writes PREREG_FF.json (pack SHA-256, engine
         predictions, audited priors + counter-intuitive
         flags, placebo predictions, win rule, stopping rule)

  2. git add PREREG_FF.json && git commit
       COMMITTED **BEFORE ANY OUTCOME IS COMPUTED**.
       This is the seal. ───────────────────────────────────────►

                                                         3. (real run) collect Table B player_outcomes
                                                            from the game DB. Only NOW does it exist.

                                                         4. score.py --outcomes <player_outcomes>
                                                              VERIFIES the committed pack SHA-256 still
                                                              matches the seal (else the run is BURNED).
                                                              Per item: real winner via two-proportion
                                                              z-test + 95% CI; ties dropped SYMMETRICALLY
                                                              for engine AND placebo. Computes engine
                                                              hit-rate, placebo hit-rate, binomial chance
                                                              test, GO/NO-GO per the sealed rule.
```

Any post-seal edit to the pack, the predictions, the metrics, the priors, or the
win rule **burns the run** (`stopping_rule.no_post_seal_edits`). The pack-SHA
gate in `score.py` enforces the pack half of that automatically.

## The sealed win rule (`PREREG_FF.json.win_rule`)

**GO** iff ALL of:

1. **Beats chance** — the engine direction hit-rate across the **K ≥ 5** scored
   micro-A/Bs clears the binomial bar: a one-sided binomial test (chance = 0.5)
   with **α = 0.10**. This admits a clean sweep (5/5 → p ≈ 0.03, 6/6, or 4/4 after
   two ties drop → p ≈ 0.06 = proof-of-life) but **rejects a single wrong-direction
   miss** at K = 5–6 (4/5 → p ≈ 0.19, 5/6 → p ≈ 0.11).
2. **Beats the placebo strictly** — the engine hit-rate is **strictly greater**
   than the "always-pick-obvious" placebo's hit-rate.
3. **Right on ≥ 1 genuinely counter-intuitive item** — the engine is correct on at
   least one item where the obvious prior is *wrong*. Per the #442 audit,
   `default_stickiness` is **OBVIOUS** (engine bet and obvious prior coincide) and
   carries **no** counter-intuitive weight, so this gate must be satisfied by one of
   `{choice_overload, countdown_urgency, prosocial_backfire, effort_justification}`.

A **GO licenses the paid PoC / design-partner stage — NOT deployment accuracy, NOT
generalization beyond F&F.** Proof-of-life, not confirmation.

## How the engine's prediction is read

For each micro-A/B the engine-runner builds a one-screen `Capability` + a
conversion `Hypothesis` whose prose contrasts **CONTROL** (the arm the obvious
prior backs) with **TREATMENT** (the other arm), plus the item's binary outcome
metric. The full `SimulationRunner` runs on the pack; the predicted winner is the
**sign of the paired `metric_lift_pp`** (treatment − control): positive → treatment
wins, negative → control wins. A CI straddling zero halves the reported confidence.
The conversion regime is `weak_behavioral` (the modality cliff) — direction/rank
signal, never a calibrated effect size.

The conversion elicitation is an LLM parse that occasionally fails for a whole arm
(lift → None) as a run-to-run flake; `predict.py` retries an item with a fresh seed
a bounded number of times so a transient miss doesn't sink an item to NULL.

## Player-level scoring

The sealed primary unit of evidence is the **population per-item hit-rate**. The
committed pack is **privacy-clean** (head-count weights + `sample_rows` statistics
only) and carries **no** `player_id → persona_id` assignments map, so player-level
scoring is **infeasible from the pack alone** and `score.py` reports it as such —
*unless* an assignments sidecar is supplied (`--assignments`), in which case it adds
a companion player-level agreement rate (never itself a GO gate). The synthetic test
supplies such a sidecar to exercise that path.

## Files

| File | Role | What it does |
|------|------|--------------|
| `predict.py` | engine-runner | BLINDED full-engine prediction per micro-A/B + placebo + **seal** → `PREREG_FF.json` |
| `score.py` | scorer | hash-gates the seal, reads Table B, computes real winners + hit-rates + GO/NO-GO |
| `gen_synthetic_outcomes.py` | test only | SYNTHETIC Table B + assignments sidecar (machinery test scaffolding) |
| `run_synthetic.py` | test only | end-to-end driver: predict → seal → gen-outcomes → score, all stamped SYNTHETIC |
| `PREREG_FF.json` | sealed artifact | the committed pre-registration (written by `predict.py --seal`) |
| `verdict_FF.json` | output | the scorer's verdict object |
| `synthetic_player_outcomes.json`, `synthetic_assignments.json` | test only | synthetic Table B + assignments (regenerated by the test) |

## Running

Environment: keys come from `backend/.env`; the engine needs `ANTHROPIC_API_KEY`.

```bash
# load keys + use the backend venv
set -a && . backend/.env && set +a

# (1) ENGINE-RUNNER — blinded prediction + seal (real run)
PYTHONPATH=backend backend/.venv/bin/python sessions/ff-validation-game/harness/predict.py --seal --population 12
git add sessions/ff-validation-game/harness/PREREG_FF.json && git commit -m "seal F&F pre-registration"

# (2) SCORER — a DIFFERENT person, AFTER Table B exists (real run)
PYTHONPATH=backend backend/.venv/bin/python sessions/ff-validation-game/harness/score.py \
    --outcomes <path/to/player_outcomes.json>

# END-TO-END MACHINERY TEST on SYNTHETIC outcomes (what #444 ships — NOT a real result)
PYTHONPATH=backend backend/.venv/bin/python sessions/ff-validation-game/harness/run_synthetic.py --population 10
```
