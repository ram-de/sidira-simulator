# Sidira Domain and Metadata Runbook

Canonical Phase 4.7 hostnames:

| Surface | Hostname | Purpose |
|---|---|---|
| Marketing/root | `sidira.ai` | Public entry point. Can redirect to the app while marketing is not live. |
| Frontend app | `app.sidira.ai` | Next.js customer-facing simulator. |
| Backend API | `api.sidira.ai` | FastAPI service consumed by the frontend. |

## Current Audit (2026-05-28)

- `sidira.ai` resolves to `162.255.119.57`, but HTTPS does not currently answer on port 443.
- `app.sidira.ai` has no DNS answer yet.
- `api.sidira.ai` has no DNS answer yet.
- GitHub Project #1 is titled Sidira.
- `pythia-simulator`, `pythia-personas`, and `pythia-crawler` descriptions/homepages use Sidira metadata. Repo names are intentionally unchanged for now.

## Deploy Environment

Frontend:

```bash
NEXT_PUBLIC_API_BASE=https://api.sidira.ai
```

Backend:

```bash
SIDIRA_CORS_ORIGINS=https://sidira.ai,https://app.sidira.ai
```

Keep local development on `http://127.0.0.1:3000` and `http://127.0.0.1:8000`.

## DNS And HTTPS Checklist

- Point `sidira.ai` at the chosen frontend/edge provider.
- Point `app.sidira.ai` at the Next.js deployment.
- Point `api.sidira.ai` at the FastAPI deployment.
- Enable provider-managed HTTPS certificates for all three names.
- Verify `GET https://api.sidira.ai/health` returns `{"status":"ok"}`.
- Verify the frontend can call the API without a CORS failure from `https://sidira.ai` and `https://app.sidira.ai`.

## GitHub Metadata Checklist

- Rename the GitHub Project title from Pythia to Sidira.
- Update repo descriptions to use Sidira.
- Decide whether to rename repos from `pythia-*` to `sidira-*` now or keep repo names stable until the producer repos are ready.
- If renaming repos, do it after open PR branches are merged or explicitly recreated against the new remote names.

## Rollback Notes

- GitHub repo renames create redirects, but local clones should still run:
  `git remote set-url origin git@github.com-personal:ram-de/<new-repo>.git`.
- Keep the temporary `pythia-simulator` CLI alias and `PYTHIA_*` env fallbacks until after the first Sidira deployment has soaked.
- Revert frontend API routing by setting `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000` locally or to the prior backend URL in production.
- Revert backend CORS by restoring the previous `SIDIRA_CORS_ORIGINS` deploy value.
