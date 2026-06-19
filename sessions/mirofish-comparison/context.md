---
type: session
domain: mirofish-comparison
status: active
started: 2026-06-19
owner: ram-de
---

# Session: mirofish-comparison — Sidira vs MiroFish two-council borrow analysis

## Goal
Run two independent councils (Council A = 4 Claude subagents across distinct expert lenses; Council B = Codex gpt-5.5 panel) comparing Sidira against MiroFish (github.com/666ghj/MiroFish), identify what Sidira can borrow (priority: frontend graph viz), assess each item's fit against existing Sidira code, and produce a written report. REPORT ONLY — no Sidira code changes this run.

## In Progress
- (none — report delivered)

## Completed
- [x] Cloned MiroFish to /tmp/MiroFish; verified key findings (D3 v7 only viz dep; random.choice MBTI personas; zero validation)
- [x] Council A: all 4 lenses (sim-systems, data-science/personas, frontend/graph-viz, product/arch-fit)
- [x] Council B: Codex read-only panel → codex_council.md
- [x] Verified headline claims directly: Sidira code credits MiroFish (simulation_runner.py:13, agent_chat.py:16); no graph/viz lib in frontend; null_integrity.py + conversion_elicitor.py exist
- [x] Synthesized COMPARISON_REPORT.md (verdict + table; 7 ranked borrowables w/ fit+effort; DO-NOT-COPY table; prior-echo section; council agreement map)

## Key Finding (council disagreement, resolved)
Codex ranked "build the graph viewer" as #1 borrow (M). Claude frontend lens REJECTED it — Sidira has no graph-shaped data; faking persona-similarity edges violates DESIGN.md §10/§4.1/§7. Resolution: graph is legitimate ONLY after building a backend EVIDENCE-GRAPH model (supports/contradicts/guardrail edges + provenance) — the cost is backend, not D3; render with visx. That model doubles as the best prior-echo defense (counter-evidence beside every positive verdict).

## Next Steps
1. (optional) /pythia-session save to commit report to the branch
2. (optional) /pythia-session close when founder has read it

## Key Files
- Deliverable: sessions/mirofish-comparison/COMPARISON_REPORT.md
- Raw codex panel: sessions/mirofish-comparison/codex_council.md
- MiroFish clone: /tmp/MiroFish (frontend/src/components/GraphPanel.vue, backend/app/services/*)
- Sidira grounding: backend/sidira_simulator/services/{simulation_runner,agent_chat}.py, memory/agent_memory.py, schemas/agent.py, frontend/app/simulations/, DESIGN.md

## Key Context
- MiroFish = orchestration wrapper around CAMEL OASIS + Zep Cloud; predict-by-vibes (single-LLM Markdown report), ZERO accuracy validation = Sidira's moat. DO NOT copy their predictor or synthetic personas.
- ALREADY HAVE: post-hoc persona interview (agent_chat.py + PersonaGroupChatV2.tsx) — excluded from borrow list.
- Borrow-hunt focus: (1) frontend graph/data-viz [priority], (2) Zep graph.add_batch as feeder INTO clustered persona pipeline, (3) OASIS as optional network-effects substrate (never predictor), (4) time-of-day/activity modulation, ontology, memory arch.
- Hard constraints: local files only (no external writes/PRs/issues); ram-de gh identity only; report not implementation.

## For my cofounder
Research/report task. Both councils launched. Findings already validated against the real MiroFish clone (not marketing). Final report lands in this session dir.
