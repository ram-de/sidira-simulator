# Pythia — Overall Roadmap

**Last updated:** 2026-05-21

The Pythia product spans three repos. This document is the single map of how phases sequence across all of them, the critical path, and what to focus on next. Per-repo MILESTONES files have the detailed phase specs.

| Repo | Role | Per-repo plan |
|---|---|---|
| [`pythia-personas`](https://github.com/ram-de/pythia-personas) | Persona Pack producer | [MILESTONES.md](https://github.com/ram-de/pythia-personas/blob/main/MILESTONES.md) |
| [`pythia-crawler`](https://github.com/ram-de/pythia-crawler) | Feature Pack producer | [MILESTONES.md](https://github.com/ram-de/pythia-crawler/blob/main/MILESTONES.md) |
| [`pythia-simulator`](https://github.com/ram-de/pythia-simulator) | Customer-facing app (frontend + backend + agent memory + single UI for all 3 producers) | [MILESTONES.md](https://github.com/ram-de/pythia-simulator/blob/main/MILESTONES.md) |

---

## Where we are today (2026-05-21)

✅ All three repos scaffolded with passing smoke tests.
✅ Artifact contract defined and exemplified by a complete sample Feature Pack (`pythia-crawler/samples/example_acme_2026-W21/`).
✅ System architecture finalized: R2 artifact store as integration contract; producers as library + CLI; simulator as the only customer-facing surface.
✅ Agent memory + identity-continuity guarantee designed and enforced (the differentiator vs mirofish-style engines).
✅ MiroFish prior-art surveyed and four patterns adapted; rejection rationale documented.
✅ Three-tab UI shell (Personas / Product / Simulations) live in the dev frontend.
✅ Backend has 15 API routes registered (6 working, 9 returning 501 with implementation notes).

What's **not** yet real: any actual end-to-end run. Every interesting endpoint is a stub. The next big leap is making one simulation work top-to-bottom against fixture data.

---

## Cross-repo phase alignment

Phases that share a number-letter across repos are coordinated; the simulator's phase is the integration point.

| Phase | `pythia-simulator` | `pythia-personas` | `pythia-crawler` | Status |
|---|---|---|---|---|
| 0 | Design | Architecture | Design | ✅ All done |
| 1 | Scaffold | Adapter/Encoder/Cluster/Calibrate | Scaffold | ✅ All done |
| 1.5 | MiroFish adaptation | — | — | ✅ Simulator done |
| 2 | Postgres + loaders | (Round 1 ✅; Round 2 pending) | Walker (Playwright) | 🔲 Pending |
| 3 | Simulation runner + scoring + refinement | — | Synthesis (PRD + Figma) | 🔲 Pending |
| 4 | Chat UI | — | R2 wiring + diff | 🔲 Pending |
| 4.5 | **Persona Builder UI (scaffolded)** | — | — | 🚧 Scaffolded |
| 5 | Auth (Clerk) + multi-tenancy | R2 artifact integration | — | 🔲 Pending |
| 6 | Observability | Schema v1.1 + validation | — | 🔲 Pending |
| 7 | First customer (Lumen MVP) | First customer | First customer | 🔲 Pending (all 3 simultaneously) |
| 8 | Refinement loop UX | Layer-3 calibration prep | — | 🔲 Pending |
| 9 | Layer-3 calibration | Layer-3 loop | — | 🔲 Pending |
| 10 | Specialized 8B model | — | — | 🔲 Long-term |

---

## Critical path

```
Phase 2 (simulator) ──┐
                      ├──> Phase 3 (simulator) ──> Phase 4 (chat UI) ──> Phase 5 (auth)
Phase 2 (crawler) ────┘                                                       │
                                                                              ▼
                                                                       Phase 7 (first customer)
                                                                              │
                                                                              ▼
                                                                       Phase 8 → 9 → 10
```

Most non-critical work (Phase 4.5 Persona Builder UI completion, crawler Phases 2–4) can run in parallel branches behind the critical path.

---

## What to focus on next

**Recommendation: a "Magic Moment" sprint — make one simulation work end-to-end against fixture data.**

This is the minimum viable execution of Phases 2 + 3 in the simulator, scoped down to remove blockers:
- One hardcoded customer (`demo` — no auth, no multi-tenancy yet)
- Fixture Persona Pack (hand-built JSON, not generated from Snowflake yet)
- Fixture Feature Pack (already exists: `pythia-crawler/samples/example_acme_2026-W21/`)
- Real LLM calls for agent reactions + scoring + refinement
- Synchronous request handling (no background queue yet)
- Minimal frontend: submit hypothesis form → live result page

### Why this first

1. **Single biggest unknown reduction.** Everything else is plumbing or polish. The actual quality of a Pythia simulation — does the score feel right? do agents react authentically? — is the only thing that decides whether the product is worth building. Confirm it works *now*.
2. **Unblocks Phase 4 (chat UI) — the differentiator.** The chat experience is the wedge that makes Pythia not-just-another-experimentation-tool. It needs real agents from real simulations to be meaningful. Phase 4 can't start until Phase 3 produces real agents.
3. **Demo-able to anyone.** As soon as the loop works, every conversation with a founder/customer/investor becomes a live demo instead of a deck.
4. **Stress-tests the artifact contract.** First real consumption of the sample Feature Pack will surface schema gaps before they cost us a customer.

### Concrete sub-tasks for the Magic Moment sprint

| # | Task | Repo | Est |
|---|---|---|---|
| 1 | Postgres schema + Alembic migration 001 (simulations, agent_instances tables) | simulator | 0.5d |
| 2 | `adapters/postgres.py` async session factory + repository pattern | simulator | 0.5d |
| 3 | `adapters/persona_loader.py` — read pack from a hardcoded local fixture path | simulator | 0.5d |
| 4 | `adapters/feature_pack_loader.py` — read the sample Acme Feature Pack | simulator | 0.5d |
| 5 | Hand-build a fixture Persona Pack JSON (5–7 personas, plausible behavioral snapshots) | simulator | 1d |
| 6 | Wire `POST /simulations` end-to-end → `SimulationRunner.run()` | simulator | 1d |
| 7 | Implement real scoring: weakness classification + sentiment + confidence aggregation | simulator | 2d |
| 8 | Implement refinement agent (single LLM call returning 1–3 suggestions) | simulator | 1d |
| 9 | Frontend `/simulations/new` form (capability dropdown + hypothesis textarea + submit) | simulator | 0.5d |
| 10 | Frontend `/simulations/[id]` result view (score gauge + weaknesses + agent list) | simulator | 1d |
| 11 | Frontend `/simulations/[id]/state` polling for live progress | simulator | 0.5d |
| 12 | End-to-end manual demo: submit a hypothesis, watch agents react, see the score | simulator | — |

**Total estimate: ~8 working days (~1.5 weeks)**. After this lands, everything else gets a stronger foundation and clearer signal on what's worth building next.

### What to *not* do during the Magic Moment sprint

- Don't wire Clerk auth (`customer_id = "demo"` hardcoded — fine for now)
- Don't finish the Persona Builder wizard (Phase 4.5 stays scaffolded; revisit after the loop works)
- Don't build the chat UI yet (Phase 4 starts the moment Magic Moment is done)
- Don't build crawler Phase 2 yet (the sample artifact is sufficient until a customer's product exists)
- Don't worry about parallel job queues, observability, SOC 2, billing

These are all important — they're just not next.

---

## After the Magic Moment

In rough order:

1. **Phase 4 — Chat UI** (the differentiator from every other experimentation tool)
2. **Phase 5 — Auth + multi-tenancy** (so a second customer can exist)
3. **Phase 4.5 completion — Persona Builder wizard** (self-serve onboarding)
4. **Crawler Phase 2 + 3 — Playwright walker + synthesis** (so customers don't need to hand us a Feature Pack)
5. **Phase 6 — Observability**
6. **Phase 7 — First customer (Lumen MVP)**
7. **Phase 8 — Refinement loop UX**
8. **Phase 9 — Layer-3 calibration**
9. **Phase 10 — Specialized 8B model**

---

## Links

- [pythia-simulator MILESTONES](https://github.com/ram-de/pythia-simulator/blob/main/MILESTONES.md) — per-phase detail for the customer-facing app
- [pythia-personas MILESTONES](https://github.com/ram-de/pythia-personas/blob/main/MILESTONES.md) — per-phase detail for the persona producer
- [pythia-crawler MILESTONES](https://github.com/ram-de/pythia-crawler/blob/main/MILESTONES.md) — per-phase detail for the feature-pack producer
- [System architecture](docs/system-architecture.md) — three-repo composition, artifact contract, stack decisions
- [MiroFish prior-art](docs/mirofish-prior-art.md) — what we borrowed, what we explicitly rejected
- [Feature Pack Crawler spec](docs/feature-pack-crawler-spec.md) — crawler subsystem design
