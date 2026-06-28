# Synthetic Streamly Challenge — a BLIND benchmark for the empirical/causal route

**Roles (do not blur them).** `codex` is the **data generator + sealer**. `Claude` is the
**blind predictor**. The whole point is that Claude runs `causal_estimator.py` on the data
**without knowing the true effects**, then we unseal and score. If the generator reveals the
answers, or the predictor peeks, the test is worthless.

This mirrors the project's prereg discipline (Cookie Cats / Hillstrom): seal the truth,
predict blind, score after. Here the *generator* holds ground truth instead of an RCT.

## What this proves — and what it does NOT

- **Proves:** whether the *method is mechanically sound and well-calibrated* across many
  confounding regimes — where it recovers the true sign, where it breaks, and whether its
  own diagnostics (overlap / support) warn when it's about to be wrong.
- **Does NOT prove:** generalization to *real human behavior*. The confounding here is
  whatever codex chooses, not what the world throws. Synthetic success is necessary, not
  sufficient — real datasets (with *found*, not injected, confounding) remain the bar for
  "sellable." Do not let a good scorecard here be reported as real-world validation.

---

## Paths (everything is absolute under the worktree)

Worktree root:
`/Users/ram/Projects/sidira-simulator/.claude/worktrees/empirical-uplift-spike`
Research dir (call it `$R`):
`/Users/ram/Projects/sidira-simulator/.claude/worktrees/empirical-uplift-spike/research/empirical-uplift-spike`

### codex WRITES:

| File | Committed? | Contents |
|---|---|---|
| `$R/.data/synthetic_streamly/dataset_01.csv` … `dataset_10.csv` | **No** (`.data/` is gitignored) | The datasets — one row per user, columns only, NO truth labels. Claude reads these. |
| `$R/synthetic_streamly_index.json` | **Yes — commit up front** | The "question paper": per dataset → `filename`, `n_rows`, `treatment_col`, `outcome_col`, `outcome_type` ("binary"\|"continuous"), `covariate_cols` (list), `gen_seed`. **No answers.** |
| `$R/SYNTHETIC_STREAMLY_ANSWERS.sha256` | **Yes — commit up front** | `sha256` of the sealed answer key (below). This locks the answers without revealing them. |
| `~/synthetic_streamly_answers_SEALED.json` (**OUTSIDE the repo/worktree**) | **No — keep out of the worktree entirely** | The sealed answer key (schema below). Do NOT place anywhere under `$R` or the worktree — Claude can read any path and must stay blind. Reveal only at scoring. |

### Claude WRITES (blind, after codex commits the index + sha256):

| File | Contents |
|---|---|
| `$R/synthetic_streamly_predictions.json` | Per dataset: `supportable` (bool), `naive_sign`, `t_learner_sign`, `t_learner_pp`, `ipw_sign`, `ipw_pp`, `overlap_fraction`, `predicted_winner` ("treatment"\|"control"\|"null/uncertain"), `confidence` ("high"\|"low" — low if overlap poor or support thin), `note`. Committed before unsealing. |

### Scoring (after predictions are committed): reveal `…_SEALED.json`, verify its sha256
matches the committed `.sha256`, then produce `$R/synthetic_streamly_scorecard.md`.

---

## Dataset schema (Streamly-shaped)

One row per user. Use realistic streaming covariates (8–12 of):
`tenure_days, plays_28d, watch_minutes_28d, avg_session_min, titles_started_28d,
completion_rate, plan_tier (0/1/2), device_mobile (0/1), region_code (int),
notifications_on (0/1), days_since_last_play, is_trial (0/1)`.

- **Treatment**: ONE binary column, a plausible feature toggle
  (`got_autoplay` / `got_personalized_home` / `got_new_onboarding`). Roughly balanced-ish
  arms after confounding (avoid <2% in either arm).
- **Outcome**: ONE column — binary (`retained_30d`, `resubscribed`) or continuous
  (`watch_minutes_next_week`). Mix across datasets.
- **Confounding**: where specified, make treatment **assignment depend on covariates**
  (e.g. autoplay shipped to already-active users first), so naive diff-in-means is biased.
- `n_rows`: 8,000–40,000 per dataset. Set and record `gen_seed` per dataset (determinism).

## Regime matrix — generate exactly these 10

| # | Regime | Purpose |
|---|---|---|
| 01 | **Clean RCT**, moderate true effect, treatment wins | sanity — causal ≈ naive ≈ truth |
| 02 | **Clean RCT**, small true effect | sanity — can it see a small real effect |
| 03 | **True null** (ATE ≈ 0) **+ confounding** that makes naive look nonzero | false-positive control — causal should say ~0 |
| 04 | Confounded, **observed driver**, moderate effect, good overlap | the bread-and-butter win |
| 05 | Confounded, **observed driver**, **naive gets the SIGN WRONG** (Cookie-Cats-like) | the headline win |
| 06 | Confounded, **strong** confounding, **poorer overlap** | stress — `support_check`/overlap should flag low confidence |
| 07 | Confounded, **nonlinear** covariate→outcome relationship | stress — does a linear learner still get the sign |
| 08 | **Heterogeneous** effect (differs by segment), clear net sign | does it recover the net ATE under heterogeneity |
| 09 | **Unobserved-confounder trap** — true driver OMITTED from columns, no proxy | honesty check — expected to FAIL; do diagnostics warn? |
| 10 | **Unobserved-confounder trap WITH observed proxies** (Hillstrom-like) | does proxy adjustment partially rescue (as Hillstrom showed) |

Mix binary and continuous outcomes across the 10. **Shuffle the regime order** vs the file
numbering is NOT required — but Claude must NOT be able to infer the regime from the index
(the index carries only schema, never the regime label or whether it's a trap).

## Sealed answer key schema (`~/synthetic_streamly_answers_SEALED.json`)

```json
{
  "generator": "codex",
  "seed_base": 20260628,
  "datasets": [
    {
      "filename": "dataset_01.csv",
      "regime": "clean_rct_moderate",
      "true_ate": 0.043,                 // in outcome units (pp for binary as a fraction)
      "true_sign": "positive",
      "true_winner": "treatment",
      "assignment_rule": "random (p=0.5)",
      "hidden_driver": null,             // or a description for traps 09/10
      "notes": "…"
    }
    // … one per dataset
  ]
}
```

## Scoring (what Claude computes after unsealing)

1. **Headline:** directional accuracy of the **causal** estimate (t-learner) vs the **naive**
   diff on the should-work set {01,02,04,05,06,07,08}. Causal should ≥ naive, and should win
   clearly on 05.
2. **Null (03):** does causal report ≈0 / "null-uncertain" rather than inventing a sign?
3. **Traps (09,10):** record pass/fail honestly (09 expected to fail). **Key question:** did
   `confidence`/overlap flag low on the cases it got wrong, or did it confidently mislead?
   (Calibration matters more than raw accuracy here.)
4. **Magnitude:** mean |estimate − true_ate| on supportable cases.
5. Write `synthetic_streamly_scorecard.md` with a per-dataset table + an honest verdict,
   including any regime where the method silently fails (that's a finding, not a failure to hide).

## Integrity checklist (codex)

- [ ] Commit `synthetic_streamly_index.json` + `SYNTHETIC_STREAMLY_ANSWERS.sha256` FIRST.
- [ ] Keep `…_SEALED.json` OUTSIDE the worktree. Never echo true effects into any committed file, CSV header, or filename.
- [ ] CSVs contain only feature columns — no `true_*` columns, no give-away column names.
- [ ] Confirm `.data/synthetic_streamly/` is gitignored (it is — `$R/.gitignore` has `.data/`).
