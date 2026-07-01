# E3-P deviations log

All deviations below occurred BEFORE prediction sealing and with the truths
file sealed and unread by the orchestrator (blind pipeline iteration).

1. **Translator prompt/pipeline v1 → v2** (2026-07-01). v1 asked the
   translator a single `composition_decidable_in_principle` question; the
   model answered it in the strict pre-launch sense and both arms collapsed
   to 118/118 abstain, including the six cases whose Arm-B tables contain
   per-arm outcome aggregates — the exact extraction regime E1 proved. The
   prereg's pipeline text separates translator classification from the
   availability check, so v2 restores that split: the translator classifies
   estimand/mechanism/pre-launch-composition-decidability only (this is the
   PREVALENCE flag), and decidability-with-observed-tables is deterministic
   code (per-arm outcome aggregates present → calculator extracts). v1
   output preserved at `e3p_predictions_v1_discarded.json`. The orchestrator
   saw only abstain-reason patterns from v1, no directions (v1 made zero
   calls), so no outcome information influenced the revision.
2. **Translator no longer sees table schemas** (v2): prose + primary metric
   only. Availability is entirely code-side.
3. **`temperature` omitted** on claude-opus-4-8 (rejects the parameter) —
   carried over from E1.
4. **Arm-B abstain codes for non-composition cases without published per-arm
   tables** are recorded as `missing_response_quantity` (the pilot's per-arm
   aggregates are missing from the public artifact; they would plausibly
   exist at a real customer's decision time). `non_composition_mechanism` is
   an Arm-A code. Results must report the "missing in the artifact vs
   missing in principle" distinction alongside COVERAGE-B.
5. **Calculator call/flat/stability rules** fixed pre-unseal as documented in
   `e3p_predict.py` (z-test 1.96 with n; 1% relative rule without n; Simpson
   segment-weight perturbation guard; token-overlap arm identification with
   abstain-on-ambiguity).
6. **Sealed truths contain one non-case meta-row** (codex review P3, noted
   post-seal without modifying the sealed file): the GoodUI assembler added
   `_meta_goodui_source_caveat`, so `e3p_truths.json` has 60 rows for 59
   backlog cases. Inert for scoring — the scorer joins on backlog ids only —
   and `e3p_truths.json` is left byte-identical to preserve the seal
   (`3eb0bc5c…`). Future runs: `e3p_merge_seal.py` should enforce exact
   backlog↔truth id equality, not just no-missing-truths.
7. **Arm-B call rule is table-presence-driven** (codex review note): when
   per-arm outcome tables exist, the calculator extracts regardless of the
   translator's pre-launch composition classification — by design (E1
   extraction regime), so Arm-B coverage on artifact-poor public sources is
   a data-availability floor. Customer-side coverage is an ownership
   argument, not an E3-P measurement (E3P_RESULTS.md Limits).
