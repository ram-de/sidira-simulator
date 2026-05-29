# Sidira Simulator

The customer-facing application for Sidira — a multi-tenant SaaS for **pre-experiment hypothesis validation via behavioral simulation**.

A PM submits a feature hypothesis (PRD + Figma). Sidira simulates how the customer's userbase would react — using personas extracted from real user data and a weekly-captured Feature Pack of how the product works today — and returns a confidence score plus diagnosed weaknesses. The PM then chats with the individual agents that participated to understand *why* they reacted the way they did.

## Subsystems in the Sidira architecture

The customer-facing simulator repo is now `sidira-simulator`; producer repos
remain `pythia-*` until their package/repo rename work is explicitly scheduled.

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

Postgres is optional for local development. With no database URL, the backend
uses process-local InMemory repos and simulation history resets on restart. To
exercise the durable metadata path, point `DATABASE_URL` at Neon or a local
Postgres instance and run migrations:

```bash
cd backend
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/sidira_simulator
alembic upgrade head
uvicorn sidira_simulator.main:app --reload
```

`SIDIRA_DATABASE_URL` and legacy `PYTHIA_DATABASE_URL` are also accepted by the
runtime, but `DATABASE_URL` is the recommended local and deployment spelling.

For deployment, the canonical Sidira hosts are `sidira.ai`, `app.sidira.ai`,
and `api.sidira.ai`. Production browser calls use the same-origin `/api` proxy;
set Amplify server-side `SIDIRA_API_BASE_INTERNAL=https://api.sidira.ai` and
`SIDIRA_INTERNAL_API_KEY`, and set backend
`SIDIRA_CORS_ORIGINS=https://sidira.ai,https://app.sidira.ai`. See
`docs/sidira-domain-runbook.md` for the domain and metadata checklist.

## AWS deployment scaffold

- `amplify.yml` builds the `frontend/` monorepo app in AWS Amplify Hosting and
  validates then writes the server-side API proxy env vars into
  `.env.production` before `next build`. `frontend/next.config.js` passes those
  values to the server route bundle; they must not be exposed as `NEXT_PUBLIC_*`.
  This is an alpha-stage gateway-token workaround for the web proxy, not a
  long-term secret boundary; #124 tracks moving proxy auth to runtime secret
  storage before broader access.
- `backend/Dockerfile` packages the FastAPI backend for the production Docker
  Compose API host or another Linux container host.
- `deploy/docker-compose.api.yml` runs the API behind Caddy for a small
  browser-console-managed Lightsail/EC2 instance.
- Production model/provider secrets stay on the backend host in AWS-managed
  secret storage; do not commit `.env` files.

## License

MIT
