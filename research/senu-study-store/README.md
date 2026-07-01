# Senu Study-Results Store

A reproducible, git-committed, sealed home for **completed Senu studies and how the engine's
blind prediction fared against the measured truth.** This is where a study stops being a
one-off and becomes a durable, findable, scored case that feeds the engine — the
predicted-vs-actual pairs the [#222 conversion_calibrator] has been waiting for.

It is the sibling of `../engine-strength-campaign/` (which logs *engine-method* validation
runs). Same discipline — append-only JSONL, regenerated ledger, sha256-sealed prereg, zero
infra — different payload: this store logs *real-world Senu cases*.

> Built for ticket **#547**. Complements the Senu data-factory (#534), the study-designer
> skill (`.claude/skills/senu-study-designer/`), and the launch gate (`preFlightCheck`).

---

## Why this exists (the gap it closes)

Before this, a finished Senu study left its pieces scattered: design in Senu's Postgres
(`study_specs`), raw completions in Senu, no A/B analysis anywhere durable, no record of what
the engine *predicted*, and the `senu.export.v1 → BenchmarkCase` adapter was a draft doc with
no code. **No single place held the raw result + the computed analysis + the engine's
predicted-vs-actual score, reproducibly.** This store is that place.

## The three files

| File | What it is |
|---|---|
| `studystore.py` | The append-only CLI. `add` / `update` / `seal` / `ledger` / `list`. |
| `studies.jsonl` | The store. One JSON line per case event; latest line per `case_id` wins. Git-committed. |
| `LEDGER.md` | **Regenerated** from the store — never hand-edited. The human-readable scoreboard. |
| `prereg/` | Sealed pre-registration artifacts (one dir per case). The `.sha256` is what's stored. |
| `senu_export_to_benchmarkcase.py` | Adapter stub: `senu.export.v1` envelope → `BenchmarkCase[]`. |

## The `case_id` convention (the join key)

```
case_id = senu:<studyId>:<behaviorSchema>:<groundTruthName>
```

- `studyId` — the Senu `StudySpec` id that ran the game.
- `behaviorSchema` — the emitted behavior schema/version (e.g. `split-the-loot.v2`).
- `groundTruthName` — the named measured outcome (e.g. `accept_rate`, `net_revenue`).

One study that yields two scored outcomes → two `case_id`s (`…:accept_rate` and
`…:net_revenue`). This same id is how the case maps to a `BenchmarkCase`.

## The reproducibility contract (non-negotiable)

Every **scored** case must carry all four, or it is not trustworthy:

1. **`human_truth_sha`** — sha256 of the sealed thoughtful-human hypothesis, committed
   *before* the data. (Seal it with `python studystore.py seal --file human.json`.)
2. **`prereg_sha`** — sha256 of the sealed **engine-blind** prediction, committed *before*
   the measured outcome is known.
3. **`envelope_ref`** — a pointer (path / R2 key / content hash) to the raw
   `senu.export.v1` export the analysis ran on.
4. **`benchmarkcase_ref`** — the derived `BenchmarkCase` json (once the adapter runs).

**Reproducibility test:** re-running the sealed harness on the referenced envelope must
reproduce the `measured` block byte-for-what-matters. If it doesn't, the case is `VOID`.

## The 3-artifact role-separation discipline (LOCKED — calibration contract §11)

Three artifacts, authored by **separate roles / at separate times**, **never tuned to each
other**:

| artifact | field | who / when |
|---|---|---|
| Sealed human-truth hypothesis | `human_truth_sha` | a thoughtful human, before data |
| Engine **BLIND** prediction | `engine_blind` (+ `prereg_sha`) | the engine, without the outcome |
| Measured truth | `measured` | realized, post-launch |

**A WIN is `engine_blind` vs `measured` — never `human_truth` vs anything.** Register only a
genuinely *leaned* counter-intuitive direction; do not hedge to look right. This is the same
discipline enforced across the whole calibration program.

## Scoring (the only rule that counts)

`score.outcome` compares the engine's **blind sign** to the **measured sign**:

- `HIT` — blind sign == measured sign.
- `MISS` — wrong sign. (Logged, never hidden — a miss is a finding.)
- `ABSTAIN` — the engine declined (guard `CANT-VALIDATE`, or confidence below threshold).
  An honest non-answer; it is **not** a miss and is scored separately.
- `PENDING` — not yet scored.

We score **direction only** — sign + confidence/abstain. Magnitude stays backstage (the
Cookie Cats lesson: right sign, ~40% magnitude error). See
`founder-readout/why-sidira-beats-pm-insight.md` §7.

## Usage

```bash
PY=/opt/homebrew/bin/python3.11    # analysis interpreter (no venv)

# 1. Seal the human hypothesis and the engine-blind prereg BEFORE the measured outcome:
$PY studystore.py seal --file prereg/<studyId>/human_truth.json      # -> record as human_truth_sha
$PY studystore.py seal --file prereg/<studyId>/engine_blind.json     # -> record as prereg_sha

# 2. Register the case when the study launches (status RUNNING/PENDING):
$PY studystore.py add --file cases/<studyId>.json

# 3. When results land, fill measured + score (append a new line; history kept):
$PY studystore.py update --case-id 'senu:S123:split-the-loot.v2:accept_rate' \
    --set status=SCORED \
    --set 'measured.sign=-' --set 'measured.effect=-0.031' --set 'measured.n=1116' \
    --set score.outcome=HIT --set score.sign_correct=true

# 4. Regenerate the ledger (add/update do this automatically):
$PY studystore.py ledger
```

Dotted `--set` keys reach nested fields (`score.outcome`, `measured.sign`, `engine_blind.guard`).

## Record schema

See the module docstring in `studystore.py` for the authoritative field list. The shape
mirrors `runstore.py` so the two stores read the same way. `example_case.json` is a
filled-in template (marked `VOID` / synthetic — it is **not** a real result).

## Control vs treatment is NOT something we build in Senu

Senu is **multi-tenant** — built to serve every customer, not just Sidira — so it is
deliberately generic. When you design a Senu game you pick a hand-vetted template, declare
the field that carries the arm, and assign **role-named** arm values (`calm`/`urgent`). Senu
already knows, *generically*, everything an A/B test needs, and exports it:

- each arm's experimental **role** — `baseline` (= control) or `manipulation` (= treatment),
  enforced in `StudySpec` (an arm literally *cannot* be named `control`/`treatment`);
- the frozen `primaryOutcome` + template `metric`;
- a pre-registered `trueDirection` (`treatment_higher`/`control_higher`/`null`).

So identifying control vs treatment needs **no custom Senu build** — it's the arm role Senu
already emits. The **only** thing Senu can't hold (and mustn't, or it stops being
multi-tenant) is the *customer-specific* fact: **what the manipulation arm means in this
customer's product** ("`cap_off` = we removed the skip-cap"). That mapping is a small
**Sidira-side** artifact — the arm dictionary — keyed by `study_id`.

## What's buildable now vs gated (ticket #547)

- **A — this Sidira-side store: BUILDABLE NOW ✅** (this directory).
- **B — the adapter** `senu.export.v1 → BenchmarkCase` (`senu_export_to_benchmarkcase.py`):
  **the mechanical `ground_truth` half WORKS NOW ✅** — it aggregates the envelope's
  `ab_outcome` rows by arm and labels control/treatment from the arm **role** (no guessing).
  The `capability`/`hypothesis` half is assembled from the Sidira-side arm dictionary. Both
  halves run today against the `examples/` fixtures (`python3.11 test_adapter.py`).
- **C — the arm dictionary is a SIDIRA-SIDE artifact ✅ built** (`arm_dictionary.py` +
  `examples/study_S123_arm_dictionary.json`), **not** a Senu build. What remains **gated**
  is only *operational*: the written **Sidira–Senu data agreement** that lets the Senu
  export be shared with Sidira, and authoring one dictionary per real study. No Senu code
  changes; nothing custom in the multi-tenant product.

## Files (Sidira-side adapter + decoder)

| File | What it is |
|---|---|
| `arm_dictionary.py` | The Sidira-side decoder: `study_id → (which manipulation = which product change)`. Schema + validator + loader. |
| `senu_export_to_benchmarkcase.py` | The adapter. Mechanical `ground_truth` (works now) + `capability`/`hypothesis` from the arm dictionary. |
| `examples/` | A synthetic arm dictionary + envelope so the whole chain runs end-to-end. |
| `test_adapter.py` | Plain-python smoke test (`python3.11 test_adapter.py`). |

## Confidentiality

No partner identities, raw partner readouts, or partner magnitudes go in this store. Senu
cases are our own manufactured data; keep it that way. (See the campaign memory.)

[#222 conversion_calibrator]: https://github.com/ram-de/sidira-simulator/issues/222
