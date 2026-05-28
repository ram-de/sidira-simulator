# Sidira Simulator

The customer-facing application for Sidira — a multi-tenant SaaS for **pre-experiment hypothesis validation via behavioral simulation**.

A PM submits a feature hypothesis (PRD + Figma). Sidira simulates how the customer's userbase would react — using personas extracted from real user data and a weekly-captured Feature Pack of how the product works today — and returns a confidence score plus diagnosed weaknesses. The PM then chats with the individual agents that participated to understand *why* they reacted the way they did.

## Subsystems in the Sidira architecture

```
pythia-personas/      → Persona Pack
pythia-crawler/       → Feature Pack
                                       ↓ both consumed by ↓
                       sidira-simulator         ← this repo
                       (frontend + backend +
                        workers + agent memory)
                                       ↓ stores ↓
                       Cloudflare R2 (artifact store)
                       Postgres (metadata + chat history)
```

See `docs/system-architecture.md` for the full architecture and **[`ROADMAP.md`](./ROADMAP.md)** for the cross-repo phase plan and what's next.

## Layout

```
sidira-simulator/
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

This is also the surface for Layer-3 calibration: PM "realistic / not realistic" flags become training signal for the specialized 8B model on Sidira's roadmap.

## Local dev

```bash
# Backend
cd backend && python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn sidira_simulator.main:app --reload --env-file .env

# Frontend
cd frontend && npm install && npm run dev
```

Backend reads artifacts from a local mirror when `R2_BUCKET` is unset (see `LocalArtifactStore`).
Use `SIDIRA_*` for simulator-specific backend config, for example
`SIDIRA_CUSTOMER_ID`, `SIDIRA_LOCAL_ARTIFACTS`, `SIDIRA_MAX_AGENTS`,
`SIDIRA_CORS_ORIGINS`, `SIDIRA_CRED_MODE`, and `SIDIRA_LOCAL_CRED_KEY`.
Legacy `PYTHIA_*` names are still accepted as fallbacks during the pre-launch
rename; when both are set, `SIDIRA_*` wins.

## License

MIT
