# pythia-simulator

The customer-facing application for [Pythia](https://github.com/ram-de/pythia-personas) — a multi-tenant SaaS for **pre-experiment hypothesis validation via behavioral simulation**.

A PM submits a feature hypothesis (PRD + Figma). Pythia simulates how the customer's userbase would react — using personas extracted from real user data and a weekly-captured Feature Pack of how the product works today — and returns a confidence score plus diagnosed weaknesses. The PM then chats with the individual agents that participated to understand *why* they reacted the way they did.

## Subsystems in the Pythia architecture

```
pythia-personas/      → Persona Pack
pythia-crawler/       → Feature Pack
                                       ↓ both consumed by ↓
                       pythia-simulator         ← this repo
                       (frontend + backend +
                        workers + agent memory)
                                       ↓ stores ↓
                       Cloudflare R2 (artifact store)
                       Postgres (metadata + chat history)
```

See `docs/pythia-system-architecture.md` for the full picture.

## Layout

```
pythia-simulator/
├── backend/          FastAPI service — API + simulation orchestration + agent chat
├── frontend/         Next.js app — PM-facing UI
├── workers/          Long-running tasks (heavy LLM fan-outs)
├── docs/             Architecture mirror + design notes
└── MILESTONES.md     Phase tracker
```

## Defining feature: agent memory

After every simulation, the agents that participated are **independently conversable**. PMs can talk to the late-night-muncher persona to ask why she didn't engage with the proposed reorder button — like interviewing the users who ran in your A/B test.

The memory model:
- **Identity prompt** (frozen) — persona + Feature Pack slice + hypothesis context
- **Initial reaction** (frozen) — what the agent said during the simulation
- **Conversation log** (append-only) — PM follow-up Q&A

This is also the surface for Layer-3 calibration: PM "realistic / not realistic" flags become training signal for the specialized 8B model on Pythia's roadmap.

## Local dev

```bash
# Backend
cd backend && python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
uvicorn pythia_simulator.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

Backend reads artifacts from a local mirror when `R2_BUCKET` is unset (see `LocalArtifactStore`).

## License

MIT
