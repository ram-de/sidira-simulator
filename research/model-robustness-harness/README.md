# Model-Robustness Harness (ticket #546)

A committed, reproducible regression harness for the sealed **AMBDOM + GNCE** battery.
On every new model release you run **one command** to check whether that model is safe
to adopt as the **translator / narrator** arm — and to confirm the durable finding still
holds: a words-only model must **not** beat chance on the magnitude-driven-flip slice.
Only the **grounded predictor** (a data g-formula, never an LLM) clears that ceiling.

Research-only. Everything here is synthetic + public-dataset (Cookie Cats, Hillstrom,
synthetic flip cells). No partner data, no production code, no redeploy.

---

## The discipline this harness enforces

- **The narrator/translator MAY upgrade** to a stronger model when results justify it
  (better overall/guessable accuracy, better prose translation — e.g. Opus 0.68 overall
  vs llama 0.42). This is the role that turns grounded numbers into readable "why".
- **The predictor STAYS GROUNDED.** Never swap an LLM in for the grounded g-formula on
  the magnitude question. The whole point of the battery is that the answer to a
  magnitude-driven flip lives in the data, not in the words — no LLM reads it.
- A candidate model that **beats the flip ceiling on words alone is a red flag**
  (prose leakage / contamination / mis-sealed cases), not a reason to promote it to
  predictor. Investigate before trusting.

---

## One command — the pre-adoption check

```bash
# needs the matching API key in ENV (never embedded, never printed):
#   claude-*  -> ANTHROPIC_API_KEY     gpt-*/o* -> OPENAI_API_KEY     llama-* -> GROQ_API_KEY
python run_battery.py --model claude-opus-4-8 --arm narrator
python run_battery.py --model gpt-5.5         --arm translator
python run_battery.py --model llama-3.3-70b-versatile
```

This re-runs the sealed battery for the named model (one live call per unique narrative;
the battery reuses symmetric prose templates by design, so it caches by narrative), then
writes `SCORECARD_<model>.md` + `scorecard_<model>.json`.

The **grounded predictor and the sealed truth are NEVER re-run** — they are read from the
sealed result JSON in `results/`. Only the LLM (words-only) arm reflects the model.

### Dry / offline regeneration (no network, no key)

```bash
python run_battery.py --help
python run_battery.py --score-only --from-log results/opus_llm_log.jsonl --model claude-opus-4-8
# the council log carries several arms (opus_sign, gpt55_sign, llama_sign) — name one:
python run_battery.py --score-only --from-log results/council_gpt55_log.jsonl \
    --model gpt-5.5 --sign-key gpt55_sign --conf-key gpt55_conf
```

`--score-only` re-derives a scorecard deterministically from a saved log and makes **no
network call**. Used as the acceptance sanity check for this ticket. A log that carries
more than one arm's signs requires `--sign-key` (the harness refuses to guess).

---

## The pass/fail gates

| gate | what it measures | PASS |
|---|---|---|
| **1. Flip ceiling** (load-bearing) | accuracy on the clean magnitude-driven-flip slice (`DISAGREE-WIDE`+`DISAGREE-NARROW`, n=12), and a one-sided binomial test vs chance 0.50 | model does **NOT** significantly beat chance (as a words-only model should not). A model that beats it is FLAGged for investigation. |
| **2. Direction** | optimism index `(UP−DOWN)/n_scored` and stance (OPTIMIST / PESSIMIST / BALANCED) | reported always; `BALANCED` passes, an optimist/pessimist is FLAGged so the directional prior is recorded (adoption still fine, but noted). |
| **3. Calibration** | Brier, 5-bin ECE, mean-confidence-when-correct vs wrong | confidence discriminates correct from wrong **and** ECE ≤ 0.20. |

`adopt_as_narrator` = `YES` iff the flip-ceiling gate passes (the load-bearing one);
direction + calibration are characterizations recorded alongside. The predictor is
grounded regardless — these gates concern the words-only role only.

---

## Sealed-battery provenance

Sealed 3-artifact discipline (sealed prereg ≠ blind prediction ≠ measured truth):

- `sealed/PREREG_AMBDOM.md` + `.sha256` — Ambiguous-Dominance battery. **Seal VERIFIED**
  (sha256 of the `.md` matches).
- `sealed/PREREG_GNCE.md` + `.sha256` — Grounded Novel-Counterfactual Extrapolation.
  **Seal VERIFIED**.
- `sealed/PREREG_WAVE1|2|3.md` + `.sha256` — the earlier non-LLM method bake-off waves.
  Their `.sha256` files seal the original `BAKEOFF_SEALED_PREDICTIONS*.json` prediction
  artifacts (**not** the `.md`), which were not part of the promoted set. They are carried
  here as **historical record** and are **not independently re-verifiable** from the `.md`
  alone. See `sealed/SEALS.md`.

Evidence (`results/`): the sealed result JSON (`bakeoff_ambdom_results.json`,
`bakeoff_gnce_results.json`, `bakeoff_results.json`, `bakeoff_wave2_results.json`,
`bakeoff_wave3_results.json`), the original LLM logs (`ambdom_llm_log.jsonl`,
`gnce_llm_log.jsonl` = llama arm; `opus_llm_log.jsonl`, `council_gpt55_log.jsonl`),
plus the consolidated `LEDGER.md` and `FINDINGS.md`.

Historical runners (`runners/`) are kept verbatim as the record of how each battery was
generated: `bakeoff_ambdom.py`, `bakeoff_gnce.py`, `bakeoff.py`, `bakeoff_wave2.py`,
`bakeoff_wave3.py`, `run_opus.py`, `run_gpt55.py`, `run_gpt.py`, `analyze_council.py`,
`score_and_log_wave3.py`. The live harness (`run_battery.py`) reuses their logic
(same SYSMSG, same parse rule, cache-by-narrative) refactored into a model-parameterized
entry point. **Note:** the historical runners read the key from the main-checkout
`backend/.env` file; `run_battery.py` reads it from the process ENV only.

### The arms

- **grounded** — the PREDICTOR. A g-formula that fits `Y = g(mediators, covariates)` on
  control-arm data only and simulates the counterfactual. Reads the per-unit magnitudes
  the prose withholds. **Not an LLM; never swapped out.**
- **narrator / translator (LLM, words-only)** — sees a fair qualitative narrative (both
  mechanisms + directions + a salient cue) but **no magnitudes**. This is the role
  `run_battery.py --arm` evaluates. The salient cue is ⟂ the true net sign by
  construction, so a cue-follower lands at chance on flips *by construction*.

---

## Already-run arms (from the promoted scorecards)

Directional sign-accuracy (null-truth cells excluded). "clean FLIP" = the 12
magnitude-driven-flip cells — the decisive slice.

| arm | model | OVERALL | AMBDOM | GNCE | clean FLIP | stance | flip ceiling |
|---|---|---|---|---|---|---|---|
| **grounded** (predictor) | g-formula, not an LLM | **0.92** | **0.97** | 0.83 | **1.00** | — | clears it (reads magnitudes) |
| narrator | `claude-opus-4-8` | 0.68 | 0.50 | 1.00 | 0.50 | PESSIMIST (constant DOWN) | PASS (at chance, does not beat) |
| narrator | `gpt-5.5` | 0.42 | 0.09 | 1.00 | 0.00 | DOWN-leaning, abstain-heavy† | PASS (below chance) |
| narrator | `llama-3.3-70b-versatile` | 0.42 | 0.09 | 1.00 | 0.00 | OPTIMIST (never DOWN on AMBDOM) | PASS (below chance) |

† The harness measures direction on the ambiguous AMBDOM prose via optimism index
`(UP−DOWN)/n`. gpt-5.5 says UP once, DOWN 15×, and abstains on the other 16 of 32 scored
cells → index −0.44, abstain rate 0.50. So it is numerically **DOWN-leaning with heavy
abstention**; the original scorecard framed this as "balanced / abstaining" relative to
llama's optimism. Both describe the same behavior: it refuses to call UP on ambiguous prose.

Readings that survived every model swap:

- **The flip ceiling is structural.** No words-only model (llama 0.00, gpt-5.5 0.00,
  Opus 0.50) beats chance on the clean-flip slice; grounded is 1.00. Swapping the LLM
  changes the *flavor* of the failure, not the *fact* of it.
- **Optimism is llama-specific, not universal.** llama never confidently predicts a
  decline on AMBDOM (pro-feature optimism); Opus is the mirror image (constant DOWN);
  gpt-5.5 refuses to call UP (abstains ~half, else DOWN). The durable claim is
  **magnitude-blindness**, not a fixed direction.
- **Best model for narration ≠ best predictor.** Opus wins overall (0.68) and is the
  right pick for translation/narration; its edge on the hard cases is *not* magnitude
  reasoning (it sits at chance there). The predictive edge on flips comes from
  **grounding**, never from a model swap.
- **A 2-model words-only council does not self-gate.** Two frontier models agree
  confidently-WRONG on the flips (0/12); only heterogeneous 3-model disagreement flags
  100% of flips — a good *abstain trigger*, still not a *predictor*.

---

## Files

```
run_battery.py     one-command per-model runner + scorer CLI (the deliverable)
scorecard.py       scoring: slice accuracy, calibration, direction, flip-ceiling gate
build_cases.py     reconstructs the 59-case battery from sealed results + llama logs
sealed/            PREREG_*.md + .sha256 seals (AMBDOM/GNCE verified; WAVE1-3 historical)
scorecards/        promoted historical scorecards (AMBDOM, GNCE, OPUS, COUNCIL_GPT55, WAVE1-3)
results/           sealed result JSON + LLM logs + LEDGER.md + FINDINGS.md
runners/           historical battery generators (verbatim, record only)
```
