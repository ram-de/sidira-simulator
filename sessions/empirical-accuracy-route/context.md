---
type: session
domain: empirical-accuracy-route
status: active
started: 2026-06-27
owner: ram-de
---

# Session: empirical-accuracy-route — a non-LLM angle on engine accuracy

## Goal
Test whether a completely different route — empirical/causal ML on real behavioral
data, and a council-of-priors over the LLM — can crack directional accuracy where the
persona-simulation engine has come back null. Find the one angle that actually works.

## In Progress
- [ ] **THEORY-OF-ESTIMABILITY ARC (2026-06-28, "Nobel-level research" prompt; Workflow multi-agent).**
      `research/estimability-theory/`. Reframe: not "perfect simulator" (Fragile Families trap) but a
      calibrated per-case test of WHICH change-directions are knowable-in-advance.
      - **Charter wave** (8 agents) → `RESEARCH_CHARTER.md` WITH its own hostile review. Adversary
        (accepted): ceiling=Salganik, guard=Lipsitch 2010, reframe=Hofman 2021; the one non-theater
        condition = ~hundreds of real per-user A/B cases.
      - **Corpus hunt** (5 agents) → `CORPUS_MANIFEST.md`: public ceiling ~8-12 experiments → hundreds
        UNREACHABLE publicly → must MANUFACTURE (Senu factory). Found ~6 NEW turnkey real RCTs
        (Karlan-List, Bertrand, Gerber-Green-Larimer, Orange-Belgium, Information-R + Hillstrom).
      - **Proximal-CI experiment** (sealed sha 26d3b497) → `proximal/RESULT.md`, **LEAD**: COCA
        recovers 95.8% sign on the EQUI abstain pile (win) but region-C 19.7% vs guard 2.3% in VIOLATED
        (no free lunch). Deployable = COCA-correct INSIDE a guard. Runstore `proximal-coca`.
      - **LaLonde PROMOTION capstone** (sealed 8673207a) → `lalonde/RESULT.md`: **MAJOR NEGATIVE** —
        guard FAILED all 3 predictions on canonical real confounding; on PSID/CPS (-$15k/-$8.5k wrong
        sign) it did NOT trip → would ship wrong sign. Mechanism: re75 (adj set) collinear with NC
        re74 deflates the placebo. Synth→real FAILED (validates adversary c+e). Verdict NULL.
      - **FIX diagnostic** (sealed da091a88): removing re75 from NC adjustment restores detection
        (trips PSID/CPS, no false-trip RCT, prior small-n false-trip cleared) → failure WAS
        collinearity; rule "don't adjust an NC on a covariate collinear with it" fixes LaLonde.
        Candidate LEAD, NOT promotion (n=1; raises sensitivity globally).
      - **FOUNDER-READOUT (on main) overstates the guard → needs the real-data-failure caveat
        (flagged, awaiting user sign-off to edit).**
      - Estimability tally: proximal-coca LEAD / lalonde-promotion NULL / lalonde-fix LEAD.
      - NEXT (founder-gated): synthetic re-validation WITH NC-collinear covariates in the DGP; guard/
        COCA on the ~6 corpus RCTs + IHDP/ACIC; new NC-nomination rule (no adj-set collinearity).
      - Commits: 9a8f68c4→cda9e750 (charter 32c71c9d, corpus 13bbc652, proximal 19196925,
        lalonde-NULL c46b1225, lalonde-fix cda9e750).

- [ ] **DATA-WALL is the live frontier.** The "think-differently" loop (below) exhausted the
      LLM-method angle on the 14-case set — every structurally-different method lands at chance.
      The next genuinely-new work is on the DATA side, not the method side: grow a real,
      representative, labeled A/B corpus (portfolio growth + the Senu BenchmarkCase factory +
      #222 conversion calibrator) so the reference-class/analogy direction has something real to
      grip, and find naturally-confounded real data to push the negative-control guard LEAD→PROMOTED.
      Founder/ops-gated; no further method spikes until the data input changes.

- [x] **"THINK-DIFFERENTLY" ALT-METHOD LOOP — COMPLETE 2026-06-28 (all NULL, data wall confirmed).**
      A pre-registered loop testing whether a structurally-different USE of the LLM beats chance,
      after the council/roleplay/comparative all came back null. `research/alt-method-spikes/`
      (RESULTS.md + 2 sealed preregs + harness). Groq llama-3.3-70b, blinded, 14 cases.
      - **M1 hypothesis-decomposition** (LLM rates 6 mechanisms → frozen sign-rule, never predicts
        winner): 7/13 (0.54) ≈ holistic. **NULL** (H1 as predicted).
      - **M3 selective-prediction** (abstain on low vote-agreement) — *my sealed PRIMARY bet*:
        **FAILED**. Model votes 5/5 unanimous on all 14 even at temp 0.4 → no reliability gradient.
        Internal self-consensus has no external anchor (unlike the negative-control guard). **NULL.**
      - **M2 reference-class analogy** (leave-one-out few-shot, other 13 labeled cases in-context):
        iter1 11/14 (0.79) — the only above-chance result, beat base-rate 0.57 by de-biasing the
        change-wins prior. I bet AGAINST it (H2), so I stress-tested it (iter2, sha caca1969):
        5 orderings × 3 seeds → **median 0.5714 = base-rate floor exactly**. The 0.79 was an
        in-context-ORDERING ARTIFACT. **LEAD→NULL** by the sealed robustness gate.
      - **Convergent finding:** holistic/decomposition/analogy/selective/council/naive ALL at chance.
        Robust convergence → binding constraint is **validation DATA, not method**. Recorded in the
        campaign run-store: `altmethod-decomposition`/`altmethod-selective`/`altmethod-analogy` (NULL).
        Commits 9a8f68c4 (prereg), d23b6ab0 (iter2 prereg), d8330863 (results).

- [x] **PERSONA-WORKER PORT (the productization loop, 2026-06-28).** Landing the validated
      cores into the live persona-build path. Scope doc:
      `research/engine-strength-campaign/SCOPE_PERSONA_WORKER_PORT.md`. 3 phases, each
      built by a fresh agent in an isolated worktree, ruff+pytest + codex-reviewed:
      - **Phase 1 — MERGED** `ram-de/sidira-personas` PR **#20** (`fec750d`): vendored
        `causal_estimator.py` + `manifest_builder.py` into `sidira_personas/estimability/`;
        guard attached per candidate effect via explicit `neg_control_map` (sibling-outcome
        auto-NC removed — causally invalid, codex caught it); `build_manifest_from_frame`
        (in-memory df slice). 84 tests; 3 codex rounds (empty-covar/per-arm-const/NaN/
        degenerate-NC all hardened).
      - **Phase 2 — MERGED** PR **#21** (`44b8608`): wired into `run_pipeline` as an
        ADDITIVE, OFF-BY-DEFAULT (`estimability.enabled is True`) artifact on
        `PipelineResult.estimability_manifest`; exception-wrapped (never breaks the pack);
        bounded (grid cap + `max_rows=50k` sample); numeric-dtype allowlist + unhashable-col
        safe. 94 tests; synthetic enabled-run = 6 supportable effects. codex LGTM.
      - **Phase 3 — MERGED** sidira-simulator PR **#510** (`c7862e7f`): carry
        `estimability_manifest` through `PipelineOutput` (`getattr` forward-compat with the
        pre-field vendored wheel `0.1.0`) and write `estimability_manifest.json` beside the
        pack in R2 in `_write_pack` (NaN→null sanitized via `_json_safe`, pack_version→
        authoritative v_N, additive/guarded — never breaks the pack write). Worker mode has
        no re-serialization boundary → survives. 30 backend tests; codex LGTM. **PORT DONE.**
      - **GATES TO PROD (founder/ops, after Phase 3 merges):** rebuild+vendor the
        sidira-personas wheel (current `0.1.0` pre-dates the field → manifest stays None until
        then); set `estimability.enabled` in a build's config_json; manual backend redeploy
        (touches backend/, but inert with the old wheel so non-urgent).
      - NEXT after the port: orchestrator MAP (LLM nominates valid NCs + maps hypothesis→cols)
        + router pre-flight (#309), then #222 calibrator wiring.

## Completed
- [x] **PRODUCT-ARCHITECTURE RECONCILIATION + DELIVERABLES (2026-07-01).** Long founder Q&A
      pinned down the target architecture (NOT the deployed engine, which is still the disproven
      persona role-play): **LLM = translator** (hypothesis → mechanism spec), **grounded
      g-formula = predictor**; direction-only output (magnitude backstage — Cookie Cats right-sign
      /~40%-wrong-magnitude); **grounded sim is the FRONT door**, negative-control guard is the
      watchdog (CONFIRMS/CONTRADICTS/CANT-VALIDATE), and the **3-model council is an
      abstain-branch caution-dial, NOT a front gate** (consensus = confidently-wrong mode; only
      heterogeneous-bias disagreement is a useful abstain siren). Crawled feature pack =
      reverse-engineered current-state PRD/Figma grounding the agents (NOT the numeric substrate;
      that's the feature store). Statistical user-sim = per-real-user counterfactual replay; the
      "talk to users" convo = LLM narrates the computed record (explain ≠ new-prediction).
      Model-robustness: llama optimist / Opus pessimist / gpt-5.5 balanced — NONE beats the
      magnitude-flip ceiling (grounded 1.00); "structural optimism" is llama-specific; durable
      claim = magnitude-blindness. Deliverables this turn:
      - **Founder docs (PR #548 → main, docs-only):** `founder-readout/why-sidira-beats-pm-insight.md`
        (four edges + receipts + 10-Q objection drill), updated `simulation-engine-where-we-landed.md`
        (§5e runtime flow, Opus + gpt-5.5/council re-tests), `finetuned-simulator-readout.md`.
      - **`/senu-study-designer` skill** (`.claude/skills/senu-study-designer/`): forward/generative
        advisor complementary to `preFlightCheck` — reasons from engine gaps → pre-registered study
        brief. Decides WHAT to run; the gate decides if it's well-formed.
      - **Reproducible study-results store** (`research/senu-study-store/`, ticket **#547** part A):
        `studystore.py` (runstore-pattern CLI, smoke-tested), keyed by
        `case_id = senu:<studyId>:<behaviorSchema>:<groundTruthName>`, 3-artifact role-separation
        (human_truth ≠ engine_blind ≠ measured; win = blind-vs-measured only), prereg templates,
        adapter stub `senu.export.v1 → BenchmarkCase` (ground-truth half now; hypothesis half gated
        on the arm dictionary + data agreement = #547 parts B/C). Feeds #222.
      - **Watchdog epic #538 + sub-tickets #539–#546** created earlier this session.
      - Commits: c15f5f1f (skill+store on branch); PR #548 = curated docs+scaffold off main.
      - ⚠️ Standing: rotate the OpenAI key pasted in chat (in gitignored backend/.env, never
        committed/echoed) once bake-off runs are done.
- [x] **Phase A — empirical/causal route (synthetic): MECHANISM WORKS.** `uplift_spike.py`.
      On a feature-expressible change with the driver in the data, causal ML (IPW +
      T-learner) recovers the true SIGN where the "more-is-better" prior and naive
      correlation both get it wrong (S1). Honest bound: unobserved confounder defeats it
      (S2 → LLM territory).
- [x] **Phase C — council-of-priors: REJECTED.** `council_benchmark.py`. 4 explicit-prior
      members + regime router, pre-registered consolidation, blinded, 3 ablations. Live
      (Groq llama-3.3-70b). On the same 14 cases the comparative baseline scored 0.50:
      naive 0.64 > council-routed 0.57 > council-unrouted 0.50 — the council made it
      WORSE (extra priors flip correct answers; diversity ≠ accuracy, measured).
- [x] **"Naive beats engine" lead — investigated + RETRACTED.** The 0.50 baseline is the
      *comparative-forecaster* (same method as my naive call) on sonnet, NOT the
      persona-sim engine. Re-ran it on llama → 0.500 again. So 0.64-vs-0.50 = model
      confound + n=14 noise. ROBUST fact (known, #342): per-arm persona-roleplay 0.286
      (below chance) << comparative narrative 0.50 (at chance). No LLM method beats chance.
- [x] **Phase B — empirical route on REAL data (Cookie Cats 90,189 players).**
      `realdata_uplift.py`, design sealed in `PREREG_REALDATA.json` (sha256 027aa4a8).
      True RCT: gate_30 wins (retention_7 ATE −0.82pp). Injected selection bias on
      engagement (treatment arm 86.7 vs control 16.8 avg rounds) → naive diff-in-means
      **+22.01pp (sign WRONG)**; T-learner standardization **−0.81pp** and IPW −0.61pp
      (both RIGHT; recovers true −0.82pp almost exactly). Exactly as pre-registered.
- [x] **Phase B — Hillstrom (clean pre-treatment, 42,693 customers).**
      `realdata_hillstrom.py`, sealed `PREREG_HILLSTROM.json` (sha256 ffcb13d9). True
      email lift +4.52pp on visit (opposite polarity to Cookie Cats). Causal adjustment
      recovers it: T-learner +4.97 / IPW +4.88. PRIMARY prediction confirmed. TWO sub-
      predictions REFUTED + reported honestly (not re-tuned): naive didn't flip (only
      attenuated +2.12 — true effect too large); the unobserved-confounder ablation still
      recovered (+3.60 — other pre-treatment covariates proxy spend). Cookie Cats keeps the
      dramatic flip + clean S2; Hillstrom adds clean-covariate recovery.
- [x] PR **#508** opened (research/empirical-uplift-spike/, no prod code touched). MERGED.
- [x] **Engine-strength campaign launched** (`research/engine-strength-campaign/`): append-only
      `runstore.py` → `runs.jsonl` + auto `LEDGER.md`; pre-register+seal every run; codex made
      robust to flakiness via **self-blinding generation** (secret os.urandom seed, hidden
      regime→file shuffle, sealed key OUTSIDE worktree, only sha256 committed) — no live codex
      dependency. Verdict legend PROMOTED/LEAD/NULL/MECH-ONLY.
- [x] **iter0 — empirical core blind on 10-regime synthetic Streamly (MECH-ONLY).** causal 7/8
      vs naive 6/8 directional (the whole advantage = the sign-flip case). **KEY FINDING:**
      overlap-based confidence flagged 0 of its 3 errors — overlap is necessary, NOT sufficient.
- [x] **iter1 — negative-control guard (NULL by strict rule, mechanism confirmed).** A
      negative-control outcome (shares confounding, true effect 0) DOES reveal unobserved
      confounding overlap can't see (P1 2/2). But the pre-registered 0.02 band false-alarmed on
      benign observed-confounding residual incl the sign-flip win (P2 fail). Did NOT re-tune.
- [x] **iter2 — negative-control guard, floor 0.05, HELD-OUT (LEAD — first of campaign).**
      Floor chosen on iter1's residual gap (observed ≤0.04 vs hidden ≥0.10), validated on a
      FRESH independently-seeded v3 set. P1 2/2 + P2 7/7: catches both unobserved-confounder
      errors with ZERO false alarms incl sign-flip. Residual error = true-null false-positive
      (pre-registered limit a negative control structurally can't catch). Folded into
      SCOPE_ROUTER.md as the empirical-trust confidence gate. Synthetic ⇒ ceiling LEAD; real
      microdata replication still required before PROMOTED.
- [x] **iter3 — negative-control guard on REAL Hillstrom RCT + adversarial verification
      (LEAD — real-data replication).** `realdata_nc_hillstrom.py`, sealed
      `PREREG_ITER3_NCREAL.md` (sha256 96a2e6e8). Hide `history`, inject selection on it, use a
      pre-treatment flag as the negative control. Pre-registered (mens): P1 specificity PASS
      (clean RCT nc −0.0015, no false abstain — this half is the GENUINE RCT), P2/P3 sensitivity
      PASS (hidden-confounder nc −0.091 > 0.05 trips; visit estimate degrades +4.54→+3.18pp).
      The 0.05 floor learned on synthetic TRANSFERRED to real data. Adversarial sweep (4 NCs ×
      3 seeds): **specificity 100% (12/12)**, sensitivity 75% (9/12) — mens/womens/recency
      robust, **newbie under-trips** (weak coupling = pre-registered proxy-absorption risk,
      confirmed). Honest finding: guard power needs a STRONGLY-coupled negative control →
      choosing it is an LLM/domain job. **LEAD not PROMOTED: confounding injected, n=1 dataset.**

- [x] **iter4 — multi-NC CONSENSUS guard (LEAD, held-out synthetic).** `iter4_consensus.py`,
      sealed `PREREG_ITER4_CONSENSUS.md` (sha256 bf203e85). Fixes iter3's weak-NC failure: trip on
      the MAX |residual| over a SET of candidate negative controls. Held-out 8-set self-blind:
      specificity 4/4 (3 NCs added ZERO false alarms) + sensitivity single-weak 2/4 → **consensus
      4/4** (recovers the unobserved-with-proxy bias a weak control misses). Corroborated by iter3's
      real Hillstrom sweep (max NC = recency ≈0.6). Upgraded `negative_control_guard()` to accept a
      control set + return per-control effects; self-test green.

- [x] **iter5 — true-null guard (LEAD, held-out synthetic).** `iter5_truenull.py`, sealed
      `PREREG_ITER5_TRUENULL.md` (sha256 a77c1996). Closes the last gap: trust the main sign only
      if |main| > 1.5·|nc_residual| (the bias the control reveals), else abstain. P1 2/2 (both
      true-nulls now abstain; old guard called both confident-wrong "treatment"), P2 3/3 (clear
      real effects still trusted), P3 3/3 (sub-bias real effects honestly deferred to LLM, 0 wrong).
      Recalibrated confounder to mostly-linear (sub-floor residuals) BEFORE commit/unseal so the
      ratio rule — not the floor — was under test. Folded ratio into `negative_control_guard()`.
- [x] **Founder readout written + (to be) merged to main:** `founder-readout/README.md` — plain-
      language, road-readable, marketplace + fridge-thermometer examples, the 6-experiment story,
      honest limits. Per the "land campaign docs on main" preference.

## Campaign ledger (research/engine-strength-campaign/LEDGER.md)
iter0 MECH-ONLY · iter1 NULL · iter2 LEAD (held-out synth) · iter3 LEAD (real Hillstrom + adv) ·
iter4 LEAD (consensus, held-out synth) · iter5 LEAD (true-null ratio). Guard now COMPLETE 3-part
gate: floor (hidden conf) + consensus (robust to weak control) + ratio (true-null/sub-bias). **Net: the negative-control guard — single + consensus —
is the campaign's validated win**, closing the iter0 calibration gap (overlap can't see hidden
confounding). Validated across synthetic held-out + real RCT + adversarial; consolidated into
`causal_estimator.py::negative_control_guard()`. Open gaps / next: (a) **true-null** false-positive
still uncaught by any negative control (needs a separate guard — likely an identification limit,
worth one honest NULL-or-not iteration); (b) PROMOTED needs naturally-occurring confounding / a
live deployment; (c) router must NOMINATE the negative-control set per hypothesis (LLM/domain job);
(d) port `causal_estimator` + the guard into **sidira-persona-worker** (Snowflake load + R2 write).

## Next Steps
1. **sidira-persona-worker PR** — port `manifest_builder.py` + `causal_estimator.py` in;
   feed real `ColumnProfile`s + crawler `Capability` list + a Snowflake `load_frame`; write
   `estimability_manifest.json` to R2 beside `persona_pack.json`; version it with the pack.
   Replace rule-based linkage with the LLM MAP step (same output shape).
2. **Orchestrator MAP + router** (backend) — in `SimulationOrchestrator.prepare`: load the
   manifest, match `hypothesis.prose` → catalog entry, route match→retrieve (empirical) vs
   unmatched→`SimulationRunner.run` (LLM, flagged).
3. **Pre-flight surface** (backend+frontend) — extend answerability #309 with the
   "estimable from your data?" branch + route/confidence card.
4. **#222 calibrator wiring** — hang the empirical estimate on the `MetricCalibrator` seam
   (replace `IdentityCalibrator` in `services/conversion_calibrator.py`).
5. (optional) Upworthy / no-persona LLM generalization beyond the 14 cases.
6. (optional) Land PR #508 to main once reviewed.
7. **#534** — Senu counter-intuitive taxonomy program, Phase 1 (lean ~50 designed tests) + learning-curve
   gate (the ₹20-lakh/6-mo plan, top ~6–8 patterns, decision gate on curve+transfer). Links #478/#484/#50.
8. **#535** — Experiment: triage fine-tune (Bridgewater-shaped) on public corpora — label worth-it/skip;
   small ranker vs frontier-zero-shot + base-rate. The cheap, near-term Bridgewater play. Links #50.
9. **#536** — Experiment: outcome-grounded micro-fine-tune feasibility on the synthetic factory — RL a
   small model against measured AMBDOM/GNCE effects; vs the optimistic LLM on the counter-intuitive slice +
   transfer to Cookie Cats/Hillstrom; answers "is the bottleneck model or data?" before the factory. Links #50.
10. **#537** — Promote AMBDOM existence-proof: find naturally-ambiguous real data with a true dominance flip
   (+ close the A4 resolution-curve gap — where grounded sim breaks as the margin shrinks). Links #521/#222.
11. (doc) (optional) PR `founder-readout/finetuned-simulator-readout.md` to main so it's readable anywhere.

## Key Files
- `research/empirical-uplift-spike/README.md` — full writeup (the canonical record).
- `research/empirical-uplift-spike/uplift_spike.py` — Phase A synthetic (S1 win / S2 bound).
- `research/empirical-uplift-spike/council_benchmark.py` (+ `council_result*.json`) — Phase C council, rejected.
- `research/empirical-uplift-spike/realdata_uplift.py` (+ `realdata_cookiecats_result.json`) — Phase B real data.
- `research/empirical-uplift-spike/PREREG_REALDATA.json` (+ `.sha256`) — sealed pre-registration.
- `research/empirical-uplift-spike/comparative_llama_result.json` — the model-confound control.

## Key Context
- **The survivor = empirical/causal route.** It's the only thing that beat chance, because
  it learns from DATA, not narratives. Everything LLM-prompt-shaped (persona, no-persona,
  council) sits at/below chance on directional prediction.
- Persona-simulation (per-arm roleplay) is actively WORSE than a one-line comparison
  (0.286 vs 0.50) — the machinery hurts. Already known internally (#342); re-confirmed.
- Empirical route's limit (registered): needs the effect driver to be an OBSERVED,
  feature-expressible variable; unobserved confounder (spike S2) defeats it.
- LLM keys live in main-checkout `backend/.env` (gitignored, NOT in worktrees) — load
  GROQ_API_KEY from there to run LLM spikes. Cookie Cats data: ryanschaub mirror.
- Ties to [[project-empirical-uplift-and-council-spike]] (memory), the directional
  portfolio, and the #222 calibrator (the empty slot this route could eventually fill).

## Estimability arc + fix re-validation + persona info-gate (2026-06-29)
- **LaLonde covariate-drop fix REFUTED** (sealed 8fc805c7, `research/estimability-theory/
  revalidation/RESULT.md`): Part A synthetic specificity FAILS (FIXED guard false-trips
  0.517 / 1.000@collin.95 on benign nulls); Part B 1/4 real-RCT false-trip (Orange-Belgium,
  likely a scale-units floor bug — binary-prob vs standardized-continuous NC). `lalonde-fix`
  downgraded LEAD→NULL (runstore `fix-revalidation`). **Route = proximal/double-NC (MGT 2018)**,
  not a covariate patch. Tally: 0 PROMOTED, 5 LEAD, 7 NULL, 1 MECH-ONLY.
- **Persona information-sufficiency gate BUILT + self-validated** (`research/estimability-
  theory/info_gate/`, commit b5c6cd36): L0 presence / L1 variance / L2 discriminability
  (HistGBM vs permutation null on a PRE-TEST proxy — outcome-blind). PASS = necessary-not-
  sufficient pre-filter; the persona-level twin of the empirical feature-expressibility gate.
  Self-test: 5 synthetic packs (sufficient/absent/degenerate/noise/partial) all classified
  right (sufficient AUC 0.838 p=0.005; noise AUC 0.501 p=0.478). Works today on any per-user
  feature table.
- **In-distribution experiment drafted** (`PREREG_INDISTRIBUTION_GATE_DRAFT.md`, NOT sealed):
  the info-gate's PASS/FAIL is the pre-committed partition; engine must beat BASE-RATE on PASS
  only (P1) + be at chance on FAIL (P2) + beat naive-intuition + counter-intuitive slice reported
  separately. Sealed + run when a design partner's sealed A/B history lands. n=1 = LEAD not PROMOTE.

## PRODUCTION BLIND TESTS w/ a design partner (2026-06-29 →, `research/estimability-theory/blind-tests/`)
**NOTE: partner identity, raw readouts, magnitudes, and the specific experiment descriptions are
CONFIDENTIAL and were scrubbed from the repo + git history (2026-06-30) at the partner's request.**
Only the abstract method/learnings are retained here. Sealed blind tests (sha256 committed BEFORE
reveal), engine on Groq llama-3.3-70b, scored once against pre-registered rules. Archetypes only:
- **Case 1 — modest UI change (negative control):** engine gave a confident large INCREASE with N
  identical personas giving the IDENTICAL reason (= one opinion ×N; L0 gate FAIL, ungrounded). Truth =
  a *small* genuine win. Direction matched but UNINFORMATIVE (the naive/base-rate call); magnitude
  overshot; confidence fake. → the ABSTAIN/capability-score case.
- **Case 2 — price-transparency feature ("worked in market X → confident"):** gate said GROUNDABLE
  (mechanism features present → L0+L1 PASS) and the engine showed real heterogeneity across segments.
  **TRUTH = counter-intuitive NEGATIVE for high-value users** (a TRADE-DOWN ACCELERATOR: price salience
  → high-value users defect to cheaper options → worse selection → disengage). Sign set by an
  EFFECT-MODIFIER (position on the price ladder); the winning market was the LEAST-representative one
  (downside structurally impossible there) → evidence-backed-but-non-generalizing failure.
- **Case 3 — moving customers off a higher-value state onto a cheaper promo:** engine said "do MORE";
  **TRUTH: the cheaper state LOST** on margin/profit (cannibalized a frequency-driving premium state).
  Engine wrong; I also conceded "activity up" and was wrong. Got right: margin deterioration +
  "underperforms the premium state" + "score on profit not count."
- **Case 4 — a subsidy claiming INCREMENTAL volume:** unprimed per-persona engine gave maximal
  fake-confidence ("100% incremental"). **TRUTH: ~flat net volume** — the subsidized channel rose while
  a sibling channel fell ~the same → substitution, not growth. Engine wrong; **mechanism/incrementality
  read called the cross-channel CANNIBALIZATION verbatim in the seal.** Honest miss: my incrementality
  lean was the right side but under-extreme.
- **Case 5 — a declutter/removal UI change claiming distal MAU/orders lift:** MIXED. Distal metrics
  NOT establishable (null) → my **flat/null + ABSTAIN-on-distal** calls held; engine overreached on the
  business metric. BUT the genuinely counter-intuitive proximal finding (removal *raised* engagement via
  perceived relevance) went AGAINST my mechanism lean (I entertained engagement-down), and my selection
  call was backwards. **Bounds the wedge: edge is gross-vs-net ECONOMICS + estimability/abstain, NOT
  engagement psychology.**
- **Pattern:** engine tracks INTUITION not truth — right when obvious is right (case 1), wrong on the
  business metric of every counter-intuitive case (it always predicts business lift). The structured
  economic/incrementality read wins on gross-vs-net/substitution cases; the **ABSTAIN** is the durable,
  model-confound-free product behavior. Root cause: a volume framing conflates gross activity with
  INCREMENTAL value; the engine simulates the demand side and is blind to the COUNTERFACTUAL
  (substitution / unit economics), which lives in the data, not the persona.
- **"engine" vs "me" (clarified for founder):** "engine" = the product's persona-SIMULATION; "me" =
  my own out-of-engine economic/causal read (the wedge prototype). The read winning is NOT "Claude >
  product" — it's that the WINNING METHOD (incrementality + unit-economics audit) is different in kind
  from simulation and becomes a DATA COMPUTATION on the customer's own readout (no LLM opinion → no
  model-strength confound). That data-computed audit is the product (#521); #530 validates it.
- **PRODUCT WEDGE (the reframe):** the costly predictions are the evidence-backed-but-non-
  generalizing ones ("worked in market X → roll out"). Sellable thing = **generalization /
  external-validity AUDITING of existing test wins** — find the effect-modifiers + cannibalization/
  trade-down signal in the customer's OWN test data (empirical route's heterogeneity + negative
  controls, NOT simulation). These 2 cases = first entries for the #517 in-distribution harness.

## Feature-store schema + capability score + telemetry/UI route (2026-06-29, later)
- **Council-of-experts deliverable** (`research/estimability-theory/feature-store-spec/FEATURE_STORE_SPEC.md`,
  5 lenses + adversarial critic + synthesis via Workflow, web-researched): the **33-class** feature-store
  schema (A empirical-anchor, B user-state×10, C interaction-telemetry×5, D context, E entity, F market,
  G acquisition/semantic, H guards, I longitudinal) that grounds empirical DIRECTION prediction for A/B
  tests. HONEST coverage ~35–45% of a roadmap, **only ~10–20% counter-intuitive** (~25–30% cold-start);
  12 documented abstain-only classes. Build priority: Wave0 guards → Wave1 spine (B1+A2+C1+A1) = bulk.
- **Case-1 (UI) reopened** — was wrongly marked permanent-abstain; UI friction IS loggable as telemetry
  (class C1). UI = ~40–55% of roadmap (founder), must be solved. Same 2-layer structure as pricing:
  C1 exposure + a **UI-experiment library** (past UI changes' telemetry→outcome) as response. UNVALIDATED;
  needs a real UI-experiment corpus; novel patterns abstain; empirical-route-fed-by-telemetry not role-play.
- **Persona-pack capability score BUILT** (#518, `info_gate/{feature_taxonomy,pack_capability,test_pack_capability}.py`,
  commit 402335c4): `score_pack(pack)->CapabilityProfile` = presence×variance×support per class → score N +
  answerable/partial/abstain surface + gap_list + summary(). Reuses the gate's _l1_check. 8 tests pass, ruff
  clean. Verified behavior = the thesis: thin order-history pack scores 8.7 + ABSTAINS on ui_friction_flow
  (blind-test-1 reproduced); +C1 telemetry → ui_friction_flow partial + C1 validated (case-1 unlock).
- **PRODUCT-AGNOSTIC refactor BUILT** (#523, commit 137466d9): 33 classes are domain-neutral CONCEPTS;
  only patterns are vertical-specific. `feature_taxonomy.py` generic_patterns + ADAPTERS for marketplace/
  saas/ecommerce/content_media/fintech; `score_pack(column_map=, vertical=)` precedence column_map (product
  Map-step path, #271 reuse) > adapter > generic. PROOF verified: marketplace + saas packs w/ DIFFERENT
  column names both validate SAME abstract C1 + both unlock ui_friction_flow; E2 two-sided supply correctly
  ABSENT for single-sided saas. 13 tests pass, ruff clean. (Founder caught marketplace-specific bias — corrected.)
- **SCOPE TRUTH:** everything this session = research/ only (zero backend/frontend; product engine imports
  nothing from research/). The capability layer is a PROTOTYPE, not wired into the product.
- **Tickets logged:** #518 capability score, #519 33-class schema+Wave0/1, #520 telemetry-UI route+library,
  #521 generalization-audit wedge; 3 blind tests logged on #517; all under router epic #511.
  **+ NEW data-plane epic #522** w/ 8 children: #523 product-agnostic taxonomy (BUILT), #524 telemetry(C1)
  ingestion, #525 experiment-history(A1) store, #526 UI-experiment library, #527 backend persist/serve
  capability profile, #528 frontend capability surface, #529 guards H2/H3, #530 real-corpus UI validation.
  Build order: Wave0 #529 → Wave1 #523/#524/#525 → #527 → #526 → #528 → #530 gate.
- **Competitive read** (`competitive/artificial-societies.md`): best-funded LLM-persona player validates only
  on intuition-aligned engagement (R²=.78 LinkedIn), ducks false-positives → our counter-intuitive/causal/
  generalization niche is vacated. Borrow: per-individual grounding + empirical readout-metric calibration.

## Simulation-engine reckoning + watchdog architecture + fine-tune readout (2026-06-30)
Founder REASSERTED the simulate-novel-questions + talk-to-users USP (rejected the pure audit pivot).
Two sealed experiments + an architecture reframe + a fine-tune strategy readout. All scratchpad-only
(`scratchpad/method-bakeoff/`), zero repo/prod code; partner data untouched.
- **GNCE** (grounded novel-counterfactual extrapolation, PREREG sha 434fd8f0): can a model fit WITHOUT
  the treated outcome simulate a novel feature via an OBSERVED MEDIATOR (g-formula) and beat the LLM?
  Real Groq. **A1 USP-claim REFUTED** — grounded sim 1.00 but a mechanism-aware LLM TIES it (battery
  fixed magnitudes so the dominant sign stayed qualitatively guessable). Honest boundary P4 HELD
  (abstains when mediator-proxy unobserved = swipe-delete). Hillstrom mechanism TRANSFERS = LEAD.
- **AMBDOM** (ambiguous-dominance battery, PREREG sha 47d6f06e): the regime GNCE couldn't build — two
  opposing mechanisms, net sign decided by MAGNITUDE words can't carry. **A1 HELD DECISIVELY: grounded
  1.00 (12/12) vs LLM 0.00 on magnitude-driven flips.** Bigger unpredicted finding: **LLM is BELOW
  chance (0.17) — answered UP 18/DOWN 0/UNSURE 18, NEVER predicts a decline** (structural optimism,
  CONVERGES with the blind-test pattern). Cookie Cats REAL recovered the counter-intuitive negative
  (LEAD). LIMIT: existence-proof only; B2 = 10 realistic datasets all one-sign → no real
  population-dominance flip to promote on (the data wall). Both in [[project-empirical-uplift-and-council-spike]].
- **Watchdog architecture** (founder's framing, adopted): run BOTH engines on every question — LLM is
  the FRONT FACE (answers anything + the "why" chat), empirical is the WATCHDOG (validates/overrules/
  flags). Precedence = trustworthy-empirical > LLM > untrustworthy-empirical(→abstain); the
  negative-control guard is the gate. Three verdicts: CONFIRMS / **CONTRADICTS (the product — catches the
  optimism-blind net-negatives)** / CAN'T-VALIDATE. Updated the product mock
  (`scratchpad/insight-engine-flow.html`, Overview + Predict screens) to show it.
- **Fine-tune strategy readout** (`founder-readout/finetuned-simulator-readout.md`): from the real
  Thinking Machines × Bridgewater write-up. KEY REFRAME: their win = RL (GRPO 44.8→73.5; OPD added the
  last points) against a VERIFIABLE REWARD that exists only because triage is a labelable classification
  task. The dataset+cleaning pipeline was the moat, not the trick. **Our prediction task lacks a
  verifiable reward at scale (each label = a full A/B, counterfactual) → no GRPO miracle → same data
  wall.** Triage ("worth testing?") IS Bridgewater-shaped (cheap labels) → buildable. "Unlimited
  resources" buys a DATA FACTORY first (Senu, over-sampling counter-intuitive), then an outcome-grounded
  fine-tune (reward = measured truth), then keep the watchdog. Honest ceiling = Salganik (predictable
  slice + calibrated abstention, not a crystal ball).
- **Senu data-factory plan (founder endorsed 80/20):** ~80% of experiments ≈ a small FINITE taxonomy of
  recurring failure modes (cannibalization, trade-down, substitution, novelty-decay, gross-vs-net,
  mix-flip, declutter-paradox, friction-as-filter…), ~20% long tail we ABSTAIN on. Target = grow the
  trustworthy CONFIDENT SUBSET + kill the optimism bias (NOT global accuracy — cost savings come from the
  confident-skip/ship slice). **6-mo Phase-1 LEAN budget: ~50 designed tests × ~1,000 respondents avg @
  ₹40 = ~₹20 lakh (~$24k)**, ~₹3.3 lakh/mo; covers top ~6–8 patterns + matched controls. Base ₹60 lakh
  (100×1.5k), Aggressive ₹1.4 cr (175×2k). **DECISION GATE @ month ~4–5: the LEARNING CURVE bends (new
  cases fall into seen structures) AND transfer holds (vs public RCTs) → scale; flat → stop, fall back to
  watchdog-audit.** Bet on the curve, not faith. Customer experiment-exhaust = free labels (Senu only
  manufactures the designed/counter-intuitive portion); chase heterogeneity only on mix-flip patterns
  (the 2–3× cost multiplier).
- **Tickets:** commented the fine-tune design-spike conclusions on #50; created the new experiment/program
  tickets (see Next Steps 7–10). GNCE/AMBDOM/watchdog-mock/readout are DONE (research+doc artifacts).

## For my cofounder
The big takeaway: no LLM-prompting trick (persona/council) beats a coin flip at predicting
which A/B arm wins — but the **empirical/causal route does** (working on real Cookie Cats +
Hillstrom). Since then: the negative-control guard FAILED on real confounded data (LaLonde),
and the candidate fix is now REFUTED too — honest route is proximal/double-NC. New: a **persona
information-sufficiency gate** (does the persona even encode what a hypothesis turns on?) is built
+ self-validated — it's the first gate and the partition the design-partner in-distribution
experiment scores against. Product read: sellable as an honest TRIAGE/bias-catcher (NOT an accuracy
oracle), gated on the guard becoming real-data-trustworthy; the moat is the gate + Senu data
factory, not the predictor. The council idea remains a documented dead end — don't re-spin it.
