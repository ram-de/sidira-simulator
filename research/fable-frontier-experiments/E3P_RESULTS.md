# E3-P Results — Backlog-Prevalence Study

**Run 2026-07-01.** Prereg `PREREG_E3P_BACKLOG_PREVALENCE.md` (sha256 `80f5625d…`, sealed on `main` before any case assembly). Truths sealed at assembly (`3eb0bc5c…`), predictions sealed before unsealing truths (`f4a96761…`). Deviations: `e3p_deviations.md` (one blind pipeline revision v1→v2 pre-seal; v1 made zero calls and leaked no outcome information). Scorer verifies both seals before scoring (`e3p_score.py` → `e3p_score.json`).

## Verdict: **MARGINAL** (pre-registered band: COVERAGE-B in [5%, 15%) with zero confident-wrong)

Per the sealed outcome rules: tier 1 ships as a **minor rung; the sales motion leads tier-2-first**. The codex generalization dissent is substantially vindicated on *prevalence*; the E1 extraction claim survives untouched on *error* (zero confident-wrong anywhere).

## The backlog

59 cases, assembled after sealing by three independent assemblers under anti-cherry-picking audit logs (`e3p_candidates_{goodui,industry,local}.md`; 299 candidates logged in total, every exclusion reasoned):

- **Realistic stratum, n=44**: 18 GoodUI free write-ups (encounter-order, cap 18), 20 Kohavi-collection/industry cases (48 candidates, every qualifying experiment taken in order), 4 Hillstrom (seeded 20% pilot vs full-data truth — the one honestly simulated post-pilot regime), 2 Cookie Cats (full-experiment aggregate tables; circularity declared).
- **Curated stratum, n=15**: the portfolio-15, reported separately (over-samples counter-intuitive outcomes by construction).
- Truth base rate (realistic): 61.4% treatment-wins — PM optimism is right about 3 times in 5, which is exactly why an audit that never sign-errs has value.

## Headline numbers (realistic stratum)

| Metric | Arm A (strict pre-launch) | Arm B (post-pilot) |
|---|---|---|
| Coverage | **0.0%** (0/44) | **13.6%** (6/44) |
| Called-set directional accuracy | — | 4/6 (0.667) |
| Confident-wrong (sign-opposite) | 0 | **0** |
| False-ship / false-kill | 0 / 0 | **0 / 0** |
| Flat-mismatch (conservative miss) | — | 2 |
| Always-treatment-wins on called set | — | 0.667 |

- **PREVALENCE (in-principle, translator, blind): 2.3%** of the realistic backlog (1/44) is composition-decidable without the experiment's own arm outcomes. 97.7% of real experiment hypotheses are behavioral-response questions — the translator correctly refuses them for pre-launch arithmetic. Curated stratum: 6.7% (1/15).
- **Both misses are under-calls, not errors**: `hil_04` (women's-email conversion — a 20% pilot lacks power for a small true effect → "flat") and `cc_01` (retention-1 — z≈1.8 < 1.96 → "flat"; E1 found the same borderline). The calculator never called a wrong sign. Under the prereg's decision-economics framing, a flat-call on a true small effect is a deferral, not a false-ship.
- **Called accuracy ties always-treatment-wins on the called subset** (0.667 vs 0.667, n=6). The calculator's value on this backlog is not beating PM optimism on direction — it is the **zero-sign-error property + calibrated flat-calls + the abstain ledger**, which optimism cannot supply. This is why the PASS bar (which required beating that baseline) was not met even at higher coverage.

## The abstain ledger is the finding

Arm A: 43/44 `non_composition_mechanism`, 1 `missing_shift_quantity` — the measured justification for the pilot-first product mode: strict pre-launch tier-1 arithmetic can call essentially nothing on a realistic backlog, and says so instead of guessing.

Arm B: 37/44 `missing_response_quantity`, 1 `missing_shift_quantity` — and here the artifact-vs-principle distinction (deviation note 4) is critical: **0 of 38 public write-ups publish per-arm aggregates**, so public-artifact COVERAGE-B is a floor, not an estimate of customer-side coverage. All 6 calls came from the only cases where raw data let us build the frozen tier-1 export ourselves. A real customer owns their pilot's per-arm aggregates by construction — the write-up-derived 86% `missing_response_quantity` mass converts, at a customer, into "export the frozen schema and these become callable."

## What E3-P settles

1. **Tier-1 pre-launch arithmetic is a diagnostic + data-quote surface, not a wedge** — in-principle prevalence ~2%. The frontier table's tier-1 row must not be sold as pre-launch prediction (this was already the joint product-label rule; now it is measured).
2. **The post-pilot calculator keeps its E1 error profile in the wild**: whenever the sufficient tables existed, it called with zero sign errors and abstained or flat-called under ambiguity — on real retail email data and a real game experiment, not just the synthetic battery.
3. **Coverage is a data-logistics number, not a method number.** The blocker on 86% of Arm-B abstains is that nobody published the tables — precisely the artifact the frozen tier-1 export schema (an afternoon of customer work) or a Senu measurement is designed to produce. E3-P therefore *prices the ask*: the EVOI quote for most of a realistic backlog is "give us your pilot's per-arm aggregate export."
4. **Sales motion confirmed tier-2-first** (per the MARGINAL rule): lead with the A/B-exhaust audit; the tier-1 calculator rides along for the composition slice and for post-pilot calls once the export exists.

## Limits

- n=6 called cases; the zero-confident-wrong result is consistent with E1's 24/24 but adds only modest evidence mass; correlated evidence units (hil_01–04 one population; cc_01/cc_02 one experiment; cc ≡ cur_01 across strata — not pooled).
- Cookie Cats Arm-B tables are full-experiment aggregates (declared circularity); Hillstrom is the only honest pilot→full-test extrapolation, and it went 3/4 exact + 1 conservative flat.
- Public write-up selection skews (GoodUI: SMB e-commerce consultancy mix; Kohavi collections: 13/20 Microsoft properties, publication bias toward surprises) — both logged by the assemblers.
- Coverage-B at a real customer is estimated by argument (data ownership), not measured here; measuring it requires a design-partner backlog, which is founder-gated.
