# True-null guard (effect-vs-residual ratio 1.5) — Scorecard (iter5)

**Integrity:** sha256 `1ce81713911de142…` — OK

> Self-blind synthetic ⇒ MECH-ONLY ceiling.

**P1 true-null caught (abstain):** 2/2 (old guard called 2/2 of them a real effect) → PASS
**P2 clear real effects still trusted (no over-abstention):** 3/3 → PASS
**P3 borderline small-real (honest defer):** 3/3 deferred, 0 trusted-correct, 0 trusted-wrong (cost = deferred-to-LLM)

| File | Regime | Kind | main | nc | old guard | ratio guard | true |
|---|---|---|---|---|---|---|---|
| tn_01.csv | borderline_small_real | borderline | +0.0231 | +0.0254 | treatment | **abstain** | treatment |
| tn_02.csv | confounded_large | clear_real | +0.1477 | +0.0196 | treatment | **treatment** | treatment |
| tn_03.csv | confounded_large | clear_real | +0.1288 | +0.0367 | treatment | **treatment** | treatment |
| tn_04.csv | true_null_confounded | null | +0.0181 | +0.0366 | treatment | **abstain** | null |
| tn_05.csv | clean_rct_large | clear_real | +0.1222 | -0.0139 | treatment | **treatment** | treatment |
| tn_06.csv | borderline_small_real | borderline | +0.0397 | +0.0318 | treatment | **abstain** | treatment |
| tn_07.csv | true_null_confounded | null | +0.0209 | +0.0250 | treatment | **abstain** | null |
| tn_08.csv | borderline_small_real | borderline | +0.0196 | +0.0305 | treatment | **abstain** | treatment |

## Verdict

LEAD (MECH-ONLY ceiling) — ratio rule closes the true-null gap for decidable cases; borderline effects honestly deferred to LLM

The negative control measures the confounding BIAS; trusting the main sign only when it clearly exceeds that bias converts confident-wrong true-null calls into honest abstentions. The unavoidable cost: a real effect SMALLER than the bias is genuinely unidentifiable and gets routed to the LLM — which is the correct, honest fallback.