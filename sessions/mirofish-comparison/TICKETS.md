# MiroFish-borrow tickets — the real four (net-new builds)

Derived from `COMPARISON_REPORT.md` §(b) + due-diligence §(b.1). #4 and #6 are
already built (excluded). #2 (cross-highlight) is a near-free polish, listed at
the end as an optional warm-up. Each ticket is default-safe: it must not change
existing behavior unless explicitly enabled, to protect sealed backtests /
null-integrity.

Recommended execution order: **#5 → #1 → #3 → #7** (smallest+safest first;
research bet last). #2 optional any time.

---

## Ticket A — #5 Activity/engagement weighting (per-persona contribution weight)
**Effort:** S · **Status:** NET-NEW · **Risk:** touches the *locked* scorer — additive + default-1.0 only.

**Goal.** Let each persona's contribution to the final score be weighted by how
active/engaged that cohort actually is (a measured population property), instead
of every agent counting equally. Default = uniform 1.0 → byte-identical output.

**Why.** Today `_compute_score` weights only by classifier *confidence*
(`scoring.py:638-668`); allocation sets headcount, not contribution
(`population_sampler.py`). A feature loved only by rarely-active users currently
counts as much as one loved by power users.

**Scope / files.**
- `backend/sidira_simulator/schemas/identity.py` — add optional `activity_weight: float = 1.0` (or a normalized engagement field) to the per-agent/persona context.
- `backend/sidira_simulator/services/identity_seed.py` / `prompt_composer.py` — derive the weight from existing real-data signals already on the persona (`behavioral_snapshot`, `tenure_band`); never from experimenter/LLM config (DO-NOT-COPY: config-authored dials).
- `backend/sidira_simulator/services/scoring.py` `_compute_score` — multiply the existing confidence weight by `activity_weight`. Default 1.0 ⇒ `w*1.0==w` exact.
- (optional) surface the weight on the agent/persona in `schemas/simulation.py` so it's visible in the UI.

**Default-safe contract.** With no activity source present, every weight is
exactly 1.0 and the scorer output is bit-identical. Guard behind a build/run
flag so it is opt-in until validated.

**Local test.** Unit test on `_compute_score`: (a) all-1.0 weights reproduce
today's score exactly; (b) non-uniform weights shift the mean in the expected
direction. Boot backend; run a sim; confirm default run unchanged.

**Prior-echo note.** Neutral-to-helpful: weight is data-sourced, not invented.

---

## Ticket B — #1 Evidence/provenance model + viewer
**Effort:** M backend + S–M frontend · **Status:** NET-NEW (no edge model, no graph lib).

**Goal.** Attach to every prediction a small graph of *typed* evidence edges —
`supports_change` / `contradicts_change` / `guardrail_risk` / `weak_or_inferred`
— each with `confidence` + `provenance` (which persona/behavior/feature/metric/
data-source it came from). Surface **counter-evidence beside the positive
verdict.** This is the moat payoff and the main prior-echo defense.

**Scope / files.**
- Backend (the load-bearing half): new `EvidenceGraph` DTO (nodes+typed edges) in `schemas/`, populated during scoring from data Sidira *already has* — `per_agent_analyses`, `Weakness{supporting_agent_ids}`, persona `behavioral_snapshot`. Add to `SimulationResult` (`schemas/simulation.py`) as an optional field; build in `services/scoring.py`. Edges must carry real provenance, never manufactured persona-similarity.
- Frontend: add **`visx`** (`@visx/network`) — *not* raw D3, *not* react-force-graph. Render on `frontend/app/simulations/[id]/page.tsx` as a DESIGN.md-compliant panel (ink-on-paper, 3-carrier color budget §4.1, 4px radius §7.1, no floating cards/pills/glow §10). Show contradicting evidence next to the verdict chip.

**Default-safe contract.** Optional field; absent ⇒ UI unchanged. No scorer-number change.

**Local test.** Run a sim; verify the result JSON carries the evidence graph with
real source ids; verify the panel renders and shows ≥1 contradicting edge for a
positive verdict. Visual QA against DESIGN.md.

**Prior-echo note.** Primary defense — makes "more-is-better" verdicts resting on
generic support edges visible.

---

## Ticket C — #3 Document → feature feeder (into clustering)
**Effort:** L · **Status:** NET-NEW (input is Snowflake/structured-only today).

**Goal.** Ingest unstructured documents (interviews, tickets, surveys, crawl
text), extract structured features, and feed them into the existing GMM
clustering pipeline — so persona packs can be grounded in richer real inputs,
not just tabular columns.

**Scope / files.**
- Backend: new document-ingest path alongside `adapters/feature_stores/` (today `FeatureStore` = `run_query`/`preview`, Snowflake-only). An extraction stage that converts docs → a **per-row feature table** matching the 8 metric types `adapt_group()` accepts (`sidira-personas/adapter.py:93-122`), which then re-enters `run_pipeline` and **passes the existing Jaccard/holdout/stability gates**.
- Reuse #4's fixed-schema discipline (`column_mapper` CANONICAL_GROUPS pattern) so extraction columns are bounded — never free LLM-invented fields.
- Customer/build-scoped storage (`customers/{customer_id}/personas/{version}/…`); no global graph; **no hard Zep dependency** (borrow the pattern, not the vendor).
- Frontend: wizard upload step in `frontend/app/personas/new/`.

**Default-safe contract.** Pure addition; existing Snowflake builds untouched.

**Local test.** Build a persona pack from a sample doc set; confirm extracted
features are structured, bounded to the fixed schema, and the build passes the
existing gates. Compare a doc-fed pack vs a tabular pack.

**Prior-echo note.** Neutral *iff* extraction is extractive + fixed-schema (#4),
not generative persona prose.

---

## Ticket D — #7 OASIS network-effects substrate (optional mode) — RESEARCH BET
**Effort:** L · **Status:** NET-NEW · **Gate:** do not start without a real network-effects requirement.

**Goal.** An *optional* mode that models agent interaction over a social graph
(followers/reposts/threads) to answer network-effect questions ("will this
referral mechanic spread?"). Substrate **only** — never the A/B predictor.

**Scope / files.**
- New deps (`oasis-ai`, `camel-ai`); a **separate worker process** (mirror the `sidira-persona-worker` split) so the API image stays light.
- Use OASIS to produce network-diffusion *structure* (reach, cascade size), feed that as **context** into Sidira's existing frozen-agent elicitation; the scorer + null-integrity certificate stay the judge. Run **blinded**; keep the no_persona shadow + null gate.
- Separate metrics surface; **must not** mix into the standard confidence score (changes the estimand).

**Default-safe contract.** Entirely separate mode; standard A/B path untouched.

**Local test.** Out of scope until a network-effects product need exists; when
built, validate against a network-effect benchmark, not the A/B harness.

**Prior-echo note.** DANGER if it ever touches the predictor — interaction loops
amplify prior-echo. Substrate-only is the only safe posture.

---

## Optional warm-up — #2 Cross-highlight (rail ↔ cohort register)
**Effort:** S (prop-wiring) · **Status:** PARTIAL (shared state exists in InspectorRail).

Pass `selectedPersona` + `onSelectPersona` into `PersonaGroupedAgents`
(`frontend/app/simulations/[id]/page.tsx:879, 2576`); add `isSelected` styling +
click + scroll-into-view so selection is bidirectional across the two
components. Pure frontend, DESIGN.md-clean, no library. Safe, visible quick win.
