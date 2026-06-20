# How to test #1 — Evidence/provenance graph (local)

Branch: `feat/evidence-graph` (worktree). Nothing is merged. Two test paths.

## 1. No-auth data proof (fastest — proves the feature works)

Runs the REAL `ScoringService.aggregate()`; no DB/auth/LLM. From the worktree:

```bash
WT=.claude/worktrees/feat+mirofish-activity-weighting/backend
VENV=backend/.venv/bin/python          # the main-checkout venv
PYTHONPATH="$WT" $VENV /tmp/demo_evidence_graph.py
```

Expected: a populated evidence graph with counter-evidence ordered first
(contradicts / guardrail before supports), and `confidence_score` unchanged by
the graph. Also covered by unit tests:

```bash
PYTHONPATH="$WT" $VENV -m pytest tests/test_scoring.py -q   # 42 pass
```

`test_aggregate_parity_snapshot` proves the score is byte-identical (the graph
is descriptive only).

## 2. Backend API proof (the OpenAPI surface)

Backend boots with in-memory repos — no Postgres, no Clerk (falls back to the
`demo` customer):

```bash
cp backend/.env <worktree>/backend/.env       # LLM keys; gitignored
PYTHONPATH="$WT" $VENV -m uvicorn sidira_simulator.main:app --port 8000
curl -s localhost:8000/openapi.json | jq '.components.schemas.EvidenceGraph'
```

`evidence_graph` is now a field on `SimulationResult` in the schema.

## 3. Full UI (the visible register) — needs two things seeded

The register renders at `/simulations/[id]` (Reading Console → "EVIDENCE
REGISTER — WHAT THE READING RESTS ON", under the weakness register). To see it
**populated** in the browser you need:

1. **Clerk dev keys** in `frontend/.env.local` (`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`,
   `NEXT_PUBLIC_API_BASE=http://localhost:8000`) — the app is auth-walled.
2. **A completed simulation** for the signed-in customer — which needs a persona
   pack + a hypothesis + an LLM run. In-memory mode starts empty, so a pack must
   be seeded (or point `DATABASE_URL` at a dev Postgres that already has one).

Once a sim completes, the register lists each persona cohort and each diagnosed
weakness as a typed edge (SUPPORTS / CONTRADICTS / GUARDRAIL RISK / WEAK·INFERRED),
counter-evidence first, with confidence + agent counts. Old sims show
"NO EVIDENCE GRAPH — RUN PREDATES THIS INSTRUMENT" (migration-free).

## Before merge
- `npm run typecheck` (frontend) — passes.
- `/codex review` on the diff (project rule: codex review before PR).
- This is the first slice of #1; the optional force-graph view is deferred (the
  register is the DESIGN.md-honest surface — the data has no real edge topology).
