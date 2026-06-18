# Design-partner backtest — pre-registered pilot scorecard (TEMPLATE)

Copy this per partner. **Sections A–D are SEALED BEFORE any result is computed** (commit the
file, record the git hash + UTC date below — that commit IS the pre-registration). Sections E–G
are filled AFTER. This is the same discipline that made the #342 benchmarks trustworthy and that
protects against rationalizing a weak result into a "promising" one.

---

## A. Partner & data inventory  *(seal before result)*

| field | value |
|---|---|
| Partner / domain | `[e.g. DTC skincare, mobile game, B2C SaaS]` |
| Prepared by / date (UTC) | `[name] / [YYYY-MM-DD]` |
| # historical experiments provided | `[N]` |
| # with a CLEAR recorded winner | `[n]` |
| Primary metric type(s) | `[conversion / retention / CTR / revenue / signup ...]` |
| Change-classes present | `[copy, pricing, UI layout, flow/steps, promo/urgency, imagery, ...]` |
| Pre-treatment audience data available? | `[yes/no — which features]` |
| **v1.1 persona pack** (rich per-user feature rows, not just centroids)? | `[yes/no — REQUIRED for high-confidence; else engine self-flags "identity_seed fallback, variance degraded"]` |
| **Rendered treatment design** (figma/screens), not just a prose change? | `[yes/no — REQUIRED; a prose-only change runs UNBLINDED → engine self-flags low-confidence (proven on the Streamly dry-run)]` |
| Renderable? (can each change be described control-vs-treatment without leaking the winner) | `[yes / partial — list exclusions]` |
| **Counter-intuitive subset** (the simpler/smaller/less-obvious option won) | `[k cases — LIST ids]` |
| Effect-size balance | `[# large effects vs # near-null]` |

**Power note (state honestly):** with n=`[n]` clear-winner cases and `[k]` counter-intuitive,
this backtest detects only `[large / moderate]` effects. `[k]` < ~10 ⇒ the counter-intuitive read
is suggestive, not confirmatory.

## B. Method  *(seal before result)*

- Persona pack: built from partner data via `sidira-personas run --require-llm` (`[in their env / anonymized]`).
- Engine config: `[model(s), elicitation mode, comparative flag, panel size, k votes/runs]`.
- **Blinding:** real winner stripped from every stimulus; descriptions neutralized.
- **Leak audit:** independent blind auditor guesses winners from descriptions only; proceed only if its guesses don't track truth. `[auditor / date]`
- **Models:** run ≥2 (e.g. Groq + a frontier model) — cross-model agreement is the cheapest artifact filter.
- Multi-run majority vote per case to suppress sampling noise.

## C. Primary metric & baselines  *(seal before result)*

- **Primary endpoint:** `[choose ONE — e.g. direction accuracy on the counter-intuitive subset]`.
- **Guardrail:** overall direction accuracy must beat the **strongest naive baseline on THIS set**
  (always-treatment, always-control, coin-flip — compute all three) and must not regress on the
  intuitive ("richer-won") cases.
- **Screening / decision-utility (the commercial metric):** if the partner had used the sim to
  pick which `[top X%]` of these experiments to run, what is the hit-rate vs running a random `[X%]`?
  (ΔU = realized-winner-rate-with-sim − base-rate.)
- **Calibration (only if predicting magnitude):** predicted lift vs actual — correlation + reliability curve.
- **Artifact controls:** a **placebo "always-pick-simpler" baseline** (a real fix must beat it on
  counter-intuitive WITHOUT sacrificing intuitive cases); leave-one-out where relevant.

## D. Pre-registered decision rule  *(seal before result — fill the thresholds)*

| outcome | trigger (set numerically NOW) | action |
|---|---|---|
| **GO** | counter-intuitive acc ≥ `[e.g. 0.70]` AND overall beats best naive baseline AND ΔU ≥ `[e.g. +0.15]` | pursue the screening product |
| **NARROW** | passes only within change-class(es) `[___]` | scope product to those classes |
| **PIVOT** | per-test direction fails BUT batch-ranking / calibration / comprehension signal holds | change predicted target to the working signal |
| **KILL** | at/below best naive baseline across classes (and replicated on ≥2 partners) | redeploy assets; stop the prediction thesis in this form |

**Registered prediction (what we expect, recorded before the run):** `[___]`
**Sealed:** commit hash `[____]` · UTC `[YYYY-MM-DD HH:MM]` · cases SHA-256 `[____]`

---

## E. Results  *(fill AFTER — do not edit A–D)*

| metric | value | baseline(s) | pass? |
|---|---|---|---|
| Overall direction accuracy | `[x/n]` | always-trt `[__]` / always-ctrl `[__]` / coin 0.50 | `[ ]` |
| **Counter-intuitive subset** (primary) | `[x/k]` | placebo-simpler `[__]` | `[ ]` |
| Intuitive ("richer-won") guard | `[x/m]` | (must not regress) | `[ ]` |
| Screening ΔU (top `[X%]`) | `[+__]` | random-`[X%]` base-rate `[__]` | `[ ]` |
| Calibration (if applicable) | r=`[__]` | — | `[ ]` |
| Cross-model agreement | `[__]` | — | `[ ]` |

**Per-change-class breakdown** (where does it work?):

| class | n | accuracy | note |
|---|---|---|---|
| `[copy]` | | | |
| `[pricing]` | | | |
| `[UI/layout]` | | | |
| `[flow/steps]` | | | |

## F. Verdict (against the sealed rule in D)

`[GO / NARROW-to-X / PIVOT-to-Y / KILL]` — because `[which thresholds were/weren't met]`.
Prediction was `[right / wrong]`, in the `[flattering / un-flattering]` direction.

## G. Honest limits & next step

- Limitations: `[power, confounds, non-renderable exclusions, single-domain, mediator covariates...]`
- Next: `[2nd partner / scope to class X / change target / wind-down per KILL]`
- If GO/NARROW: confirm on a **fresh, held-out** slice of their experiments before any product claim.
