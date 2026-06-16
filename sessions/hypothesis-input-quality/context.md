---
type: session
domain: hypothesis-input-quality
status: active
started: 2026-06-15
owner: ram
---

# Session: hypothesis-input-quality — input vetting + scoring standard for the simulation

## Goal
Determine, at distinguished-engineer / PhD rigor, whether and how Sidira should
**vet hypothesis inputs and attach a quality score** that the simulation decision
factors in — because the simulation is heavily input-dependent (garbage-in →
garbage-out). Then file tickets and build it autonomously via /loop (incl. merge +
deploy).

## Hypothesis under test (the user's idea — to be validated OR refuted)
> Vet the hypothesis inputs, compute an **input quality score**, and have the
> simulation decision take that score into account.
The user explicitly flagged this "might be right or completely wrong" — the panel
must pressure-test it, not rubber-stamp it.

## In Progress
- [x] T1 (#310) — MERGED (PR #317, squash 004cfc1) 2026-06-16. **Deploy HELD** (see Deploy Gate).
- [x] T2 (#311) — MERGED (PR #320, squash ef5fbcd) 2026-06-16. Abstention verdict "NOT ANSWERABLE
      BY THIS INSTRUMENT" (out_of_scope, abstain-not-block); categorical fields in result_json
      (no migration); DESIGN.md §8.2 added; codex clean round 6. **Deploy still HELD.**
- [x] T3 (#312) — MERGED (PR #323, squash 26c13c2) 2026-06-16. Pre-flight ordinal lint
      (green/amber/red/abstain): LLM judge (reasons ⊆ existing weakness taxonomy) + deterministic
      leading-framing lint + paraphrase-abstain (reuses conversion_elicitor K-pass, cost-gated to
      non-green); routes red/amber into existing refinement.py (trigger widened, not forked);
      categorical input_flags on result_json (no migration); confidence_score byte-identical
      (asserted); DESIGN.md §8.2 disclosure note + changelog 0.3.4; codex clean. NOTE: built in two
      passes — backend stalled (watchdog) then finisher completed tests+frontend+DESIGN. **Deploy still HELD.**
- [x] T4 (#313) — MERGED (PR #329, squash 82b09cf) 2026-06-16. **Deploy now UNBLOCKED.**
      Wizard structured claim fields (if/for/then/direction → prose, free-text escape hatch);
      surfaced OEC metric bundle decoupled from A/B (clears T1 oec_undeclared block single-arm);
      needs_input/override UI consuming the create-path 422 inline (Run-anyway-as-generic-reception
      affordance); inline pre-submit lint via NEW additive `POST /simulations/preflight`
      (deterministic, zero-LLM, no-persist; reuses assess_answerability + _detect_leading_framing
      verbatim — no drift). No scoring.py change, no scalar, no migration; confidence_score
      untouched. DESIGN.md §7.7 reused + changelog 0.3.5; codex clean (one P2 fixed). Backend
      touched → ONE combined redeploy of #310–#313 below.

## Deploy Gate — CLEARED 2026-06-16 (T4 merged)
All four build tickets (#310–#313) are on `main` (HEAD 82b09cf). Backend was touched across the
chain (answerability.py, input_lint.py, simulations.py preflight route, schemas, deps) — execute
ONE combined manual redeploy of api.sidira.ai via deploy/REDEPLOY.md. **NO migration in the whole
chain** (runbook step 2 = normal path, SIDIRA_AUTO_MIGRATE not required). Until the redeploy lands,
prod serves the previous build (no new routes) but is NOT broken — the live wizard simply doesn't
emit run_as_generic_reception/preflight yet, and the old create path has no gate. The gate + wizard
go live together on redeploy.

## Tickets (FILED 2026-06-16, ram-de)
- Epic **#309** — Hypothesis input answerability (pre-flight gate, not a score)
- **#310 T1** — pre-persist answerability gate (deterministic, no-LLM) — MVP, build first
- **#311 T2** — abstention verdict "NOT ANSWERABLE BY THIS INSTRUMENT" (dep #310)
- **#312 T3** — pre-flight ordinal lint → refinement; paraphrase-abstain (dep #310)
- **#313 T4** — upstream authoring: structured fields + metric bundle + inline lint (dep #310–#312)
- **#314 T5** — validate gate labels vs #222 held-out outcomes (BLOCKED on #222)

## Completed
- [x] Grounding pass A: mapped hypothesis-input → simulation → decision pipeline (Key Files)
- [x] Grounding pass B: inventoried existing rigor stack (Key Context — output/run integrity, NOT input vetting)
- [x] Grounding pass C: synthesized on-file research/intent (Key Context pass C below)
- [x] Wrote shared panel brief (/tmp/gigo_panel_brief.md) with bad-input taxonomy a–h
- [x] Ran 5-lens adversarial panel (exp-science / ML-data-quality / measurement-validity / decision-theory / red-team)
- [x] Synthesized → `analysis.md` (UNANIMOUS verdict: RESHAPE)

## Decision (see analysis.md)
- **KILL the 0–100 input-quality score** (construct error, uncalibratable, Goodhart,
  fails paraphrase bar, "grades the customer's homework" to a Kohavi buyer).
- **NEVER discount confidence_score by an input factor** — corrupts the #222
  calibration target (entangles input quality with effect magnitude; unfalsifiable
  component, violates ablation doctrine).
- **BUILD a deterministic pre-flight answerability gate that ROUTES, not scores**, at
  `api/simulations.py` pre-persist. Genuinely-new axis = instrument-fit → ABSTENTION
  verdict. Everything else folds into existing taxonomy/refinement/reliability-regime.
- Real leverage is UPSTREAM authoring (structured fields + inline lint).

## Next Steps
1. File T1–T5 (T1=MVP deterministic gate; T2=abstain verdict; T3=ordinal lint;
   T4=authoring; T5=blocked on #222 backtest validation)
2. /loop build starting at T1; I handle merge + deploy (backend = manual deploy)

## Key Files (grounding pass A — input→sim→decision pipeline)
- `backend/sidira_simulator/schemas/simulation.py:26-79` — `Hypothesis` schema
  (required: capability_name + prose; optional: proposed_prd, proposed_figma,
  conversion-metric bundle). Only validation = metric-field completeness (57-79).
- `backend/sidira_simulator/api/simulations.py:80-138` — create_simulation route;
  validation = population cap, model availability, persona IDs. **No quality gate.**
- `frontend/app/simulations/new/page.tsx:279-361` — wizard; only checks non-empty
  prose + population bounds. Conversion-metric fields NOT in UI (API-only).
- `backend/sidira_simulator/services/simulation_runner.py:196-1002` — run()+_score().
- `backend/sidira_simulator/services/scoring.py` — confidence_score formula (624-668:
  `100×(0.6·sentiment + 0.4·weakness_signal)`), low-N + failure-rate gates (844-864).
- `backend/sidira_simulator/schemas/simulation.py:236-243` — Weakness categories
  incl. `untestable_hypothesis` ("too vague to falsify"), `wrong_metric` — but these
  are POST-HOC diagnostics, not pre-flight gates.
- `frontend/app/simulations/[id]/page.tsx:120-157` — DECISION_POLICY ship@80; verdictFor().
- Integration points for an input score: (1) API pre-persist, (2) runner entry,
  (3) post-aggregation SimulationResult field, (4) frontend verdict.

## Key Context (grounding pass B — existing rigor stack)
- **A large rigor stack EXISTS but is OUTPUT/RUN integrity, not INPUT vetting:**
  - `services/null_integrity.py` — permutation null-integrity certificate + SHA-256
    hash-commitment (pre-registration); `passed/void_reason/underpowered`.
  - `services/conversion_elicitor.py` — blinded per-metric elicitation, K-paraphrase
    ensemble, instability flag.
  - `services/treatment_renderer.py` — structured state-diff, two views (blinded/
    unblinded), **per-modality reliability regime** (strong copy r≈0.85 … weak UI
    r≈0.25-0.34) = confidence ceiling. THIS already encodes "how trustworthy is this
    KIND of change" — adjacent to input quality.
  - `services/behavioral_profile.py`, `persona_pack_translator.py`,
    `conversion_calibrator.py` (protocol, no-op default).
  - Degradation guard: >50% LLM-classification failure → score×0.7 + underpowered.
  - Paired sampling #90; delta cancels uncalibrated propensity.
- **DESIGNED not built:** ablation harness #222, OEC-aligned scoring, shrinkage
  calibration, CTR/retention elicitors, stratified honesty table.
- **MISSING (this session's gap):** hypothesis INPUT quality scoring. Confirmed
  no pre-flight input score / refusal-to-run exists.
- ADVERSARIAL NOTE for panel: existing `untestable_hypothesis`/`wrong_metric`
  weakness categories + reliability-regime already do post-hoc input critique. A
  new input score must compose with these, not duplicate. Open question: pre-flight
  gate vs. post-hoc diagnostic vs. decision-weighting — which actually adds value?

## Key Context (grounding pass C — research intent & strategic tensions)
- **Credibility deliberately leans on the BACKTEST harness (#222), NOT input gating.**
  "A component earns its place iff it improves held-out prediction of real experiment
  outcomes" (ablation-protocol.md). Risk: an input score can't be backtested against
  real outcomes → would be an UNFALSIFIABLE component by the team's own doctrine.
- **Hypothesis-linting was proposed and called "cheap/product-fixable"**
  (persona-classifier-research/analysis.md:59 — "specify metric? cohort? mechanism?")
  but NO ticket exists; never built. Closest de-facto input critique = the POST-HOC
  weakness taxonomy + the refinement service.
- **OEC-declaration-at-submission** (agent-behavior-spec/oec-scoring.md:25) is the
  closest existing "gate decision on input completeness" — specced, not enforced.
- **Deepest GIGO:** agents "faithfully roleplay the fabrication" — unfalsifiable /
  fabricated inputs get simulated AS IF TRUE. Team's chosen defense pattern is
  degrade-and-disclose (thin source "must never masquerade as a grounded row").
- **Bad-input taxonomy (a–h):** (a) vague/unfalsifiable; (b) wrong/missing metric;
  (c) wrong cohort; (d) broken mechanism; (e) structurally-invisible change (prose-only,
  no proposed_figma → agent compares wireframe to paragraph); (f) demand-characteristic
  framing; (g) out-of-scope OEC (long-horizon revenue); (h) equilibrium/network/novelty.
- **OPEN ADVERSARIAL QUESTION the panel must resolve:** does an explicit input-quality
  score that the decision factors in ADD value, or DUPLICATE the harness + taxonomy +
  refinement + reliability-regime + paraphrase-instability stack? And if it adds value,
  is the lever a GATE / DISCOUNT / ABSTAIN / DISPLAY / ROUTE-TO-REFINEMENT — or upstream
  AUTHORING-time prevention rather than downstream scoring?

## Key Context
- Distinguished-engineer panel framing: Google / Meta / Airbnb / Amazon / Uber DS+ML.
- Panel lenses launched: (1) experimentation/causal scientist, (2) ML data-quality
  platform, (3) measurement-validity + LLM-judge, (4) decision-theory/product,
  (5) adversarial red-team (mandate: kill the idea).
- Adversarial mandate: a strong reviewer would ask whether input scoring is the
  right lever at all, or whether it duplicates/should-fold-into the existing
  agent-behavior-spec rigor stack (pre-registration, blinded metric elicitation,
  null-integrity certificate, shrinkage, paraphrase ensemble).
- Autonomy: user said don't wait for merge/deploy — I own those. Backend is
  manual-deploy (deploy/REDEPLOY.md).

## For my cofounder
Investigating whether to add an input-quality gate/score to the simulation
decision path. Deep research first, then autonomous build via /loop.
