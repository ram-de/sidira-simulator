# Confident-KILL calibration study (2026-07-14)

Can the Sidira simulation engine, with a calibrated confidence layer, **confidently
KILL** losing A/B variants at a bounded false-negative (killed-winner) rate — validated
on public data with real outcomes, no client partner required?

**840 real simulations** through the faithful product path (`SimulationRunner.run()`,
A/B mode, `signal = result.lift`), scored with the real `PlattCalibrator` under honest
5-fold cross-fit. Full writeup: [`CONFIDENT-KILL-UPWORTHY-RESULTS.md`](./CONFIDENT-KILL-UPWORTHY-RESULTS.md).

## Five experiments

| # | Experiment | N | Corpus | Headline result |
|---|---|---|---|---|
| 1 | Subtle A/B | 600 | Upworthy real winner vs real loser | 52% dir-acc (coin flip, p=0.22); **NO-GO** for KILL — screen correctly PASSes |
| 2 | Obvious junk | 240 | real winner vs synthetic broken arm | 100% dir-acc, **0% killed-winner**, 100% coverage — confident KILL works |
| 3 | Graded ladder | 150 | real winner vs LLM-degraded arm (L1→L3) | monotonic ramp: chance→0.66→0.76→0.96→junk — killable = *clearly-flawed*, not *slightly-worse* |
| 4 | Persona-richness ablation | 100 | subtle pairs, generic-10 vs rich-24 personas | +2% noise, **no callable region either way** — persona lever closed |
| 5 | **GoodUI reverse-PRD** | 131 | real product/UI A/B tests, real outcomes | **0.594 dir-acc, p=0.034 — first significant beat of chance**; tail enriched for losers but thin. See [`GOODUI-REVERSE-PRD-RESULTS.md`](./GOODUI-REVERSE-PRD-RESULTS.md) |

**Net:** a real, safe confident-KILL regime exists and spans obvious-junk → plausibly-but-
clearly-flawed variants; the engine correctly abstains (PASSes) on subtle/optimized ones;
neither calibration nor persona richness manufactures signal that isn't there. The one
untested input lever is **real product context (reverse-PRD)** — Upworthy is text-only
headlines (the degenerate worst case), so it cannot exercise it. That needs a product-
feature dataset (see below) or the design-partner pilot.

## Layout

```
harness/
  batch_runner.py   run the engine over a pairs CSV, checkpointed + resumable
                    (env: SIDIRA_PAIRS, SIDIRA_RESULTS, SIDIRA_PERSONAS_JSON, SIDIRA_POP)
  gen_ladder.py     LLM-generate graded-difficulty variants (exp 3)
analysis/
  analyze_calibration.py     cross-fit calibrator + KILL/margin/deadzone sweep + GO/NO-GO (exp 1)
  analyze_junk.py            per-category junk detection + confident-KILL (exp 2)
  analyze_ladder.py          per-level detection gradient (exp 3)
  analyze_rich_vs_generic.py paired rich-vs-generic verdict, new-metric framing (exp 4)
data/
  download_upworthy.sh       fetch raw Upworthy CSVs from OSF (not committed, ~90MB)
  labeled_pairs*.csv         built pairs (subtle / junk / ladder)
  results*.csv               collected engine signals + ground truth
  rich_personas.json         24-persona behavioral panel (exp 4)
```

Paths in the scripts point at the original scratchpad run dir; adjust `SP` to re-run.

## Reproduce

1. `bash data/download_upworthy.sh`
2. Rebuild pairs (the build logic is inline in the run transcript; `labeled_pairs*.csv` are committed).
3. From `backend/` with `GROQ_API_KEY` set:
   `SIDIRA_PAIRS=.../labeled_pairs.csv SIDIRA_RESULTS=.../results.csv .venv/bin/python harness/batch_runner.py`
4. `python analysis/analyze_calibration.py results.csv` (and the other analyzers).

## Next: testing the reverse-PRD lever — dataset shortlist (verified 2026-07-14)

Recent LLM-A/B papers (SimAB, AgentA/B, SimGym, RealUserSim) validated on **private** data
and released nothing usable. Kaggle/HF "A/B" sets are numeric logs with no creatives. The
accessible corpora, ranked for the product-feature regime:

1. **GoodUI Evidence** ⭐ — 633 real UI/product A/B tests, before/after screenshots + change
   descriptions + labeled effect sizes. Best fit for the reverse-PRD lever. $60/mo, scrape
   behind login (check ToS). https://goodui.org/evidence/
2. **GuessTheTest** — CRO tests with a built-in **human "guess the winner" baseline** (the
   PM-eyeball comparison). $47–247/mo, ToS blocks scraping. https://guessthetest.com/
3. **Wikimedia fundraising banner archive** — fully open, real creatives + winners, prose
   extraction; banner regime ≈ headlines. https://meta.wikimedia.org/wiki/Fundraising
4. **Hewitt et al. (Nature 2026)** — 70 survey experiments, off-regime but a real forecaster
   baseline. https://www.treatmenteffect.app/
5. **DellaVigna–Vivalt SSPP** — 66 realized projects, best forecaster baseline, off-regime.

Plan: GoodUI primary (tests the untested lever) + GuessTheTest for forecaster-lift + Wikimedia
for free volume.
