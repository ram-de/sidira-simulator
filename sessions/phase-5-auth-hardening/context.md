---
type: session
domain: phase-5-auth-hardening
status: active
started: 2026-05-30
owner: ram-de
---

# Session: phase-5-auth-hardening -- proxy auth and pre-customer hardening

## Goal
Close out the production Postgres bootstrap follow-up, redeploy the merged backend from `main`, and implement #124 so the web proxy no longer needs a backend gateway token in Amplify/Next deployment artifacts.

## In Progress
- [ ] Land PR #130 and execute the post-merge production rollout.

## Completed
- PR #129 was squash-merged to `main` as `ad6f49ad231bd94b66878df86f06ed097ffc9e33`.
- `origin/main` includes the Neon URL normalizer hardening and production Postgres bootstrap docs.
- Production health was checked after the merge: `GET https://api.sidira.ai/health` returned 200.
- #110 was reviewed: simulator/domain rename is done, but the parent issue still includes producer repo renames for `pythia-personas` and `pythia-crawler`, so it should not be closed as fully complete yet.
- Updated `CONTEXT.md` and `ROADMAP.md` so the next pointer moves from merging #129 to shipping #124.
- Added a #110 GitHub comment noting that only producer-repo rename scope remains and the simulator/domain work is done.
- Redeployed the EC2 backend from `main` through AWS Console SSM Run Command `dce6ba0d-70be-4c99-a3e7-b7a6e9280552`.
- Post-redeploy smoke: `GET https://api.sidira.ai/health` returned 200, direct `GET https://api.sidira.ai/models` remained gated with 404, and `https://sidira.ai` still returns the expected Amplify Basic Auth 401.
- Started #124 on `codex/124-proxy-auth-hardening`.
- Implemented runtime web-proxy auth: Amplify now receives only `SIDIRA_API_BASE_INTERNAL=https://api.sidira.ai/_sidira_web_proxy`; the Next `/api` proxy forwards the browser Basic Auth `Authorization` header and no longer embeds or forwards `SIDIRA_INTERNAL_API_KEY`.
- Added Caddy `_sidira_web_proxy` handling that validates Basic Auth with SSM-loaded runtime values, strips the proxy prefix, and adds `X-Sidira-Internal-Key` server-side before proxying to FastAPI.
- Updated the EC2 deploy helper to require and write `/sidira/prod/SIDIRA_WEB_PROXY_BASIC_AUTH_USER` and `/sidira/prod/SIDIRA_WEB_PROXY_BASIC_AUTH_HASH` alongside the existing backend internal key.
- Codex review found a P1: Docker Compose can interpolate `$` inside `env_file`, corrupting bcrypt hashes. Fixed by writing both raw `/opt/sidira/api.env` for `docker run --env-file` and Compose-safe `/opt/sidira/api.env.compose` for Docker Compose.
- Codex review found a second P1: removing `next.config.env` entirely could leave the deployed SSR route without `SIDIRA_API_BASE_INTERNAL`. Fixed by serializing only the non-secret proxy base into the Next route bundle while keeping `SIDIRA_INTERNAL_API_KEY` out.
- Codex review found a P2: Caddy would validate Basic Auth but still forward the browser `Authorization` header upstream. Fixed with `header_up -Authorization` before injecting `X-Sidira-Internal-Key`.
- Updated deploy/runbook docs and config guard tests to capture the #124 auth boundary.
- Verification passed: `backend/.venv/bin/pytest tests/test_deploy_config.py -q`, `backend/.venv/bin/pytest tests/ -q` (392 passed, 11 skipped), `frontend npx tsc --noEmit`, `frontend npm run build` with `SIDIRA_API_BASE_INTERNAL=https://example.com/_proxy`, `git diff --check`, Docker Compose env-file hash preservation, and `docker run ... caddy validate --config /etc/caddy/Caddyfile`.
- Final `/codex review --base main` passed clean with no correctness, security, or deployment findings.
- Opened PR #130: https://github.com/ram-de/sidira-simulator/pull/130.

## Next Steps
1. Merge PR #130 after the user approves landing it.
2. After #124 merges, create SSM values `/sidira/prod/SIDIRA_WEB_PROXY_BASIC_AUTH_USER` and `/sidira/prod/SIDIRA_WEB_PROXY_BASIC_AUTH_HASH`, update Amplify `SIDIRA_API_BASE_INTERNAL` to `https://api.sidira.ai/_sidira_web_proxy`, remove Amplify `SIDIRA_INTERNAL_API_KEY`, then redeploy backend and frontend.
3. Verify `https://sidira.ai/simulations` works after Basic Auth and direct unauthenticated `https://api.sidira.ai/models` remains blocked.

## Key Files
- `CONTEXT.md` -- sprint narrative and next-work pointer.
- `ROADMAP.md` -- current critical path.
- `docs/sidira-domain-runbook.md` -- production domain/auth/deploy runbook.
- `frontend/app/api/[...path]/route.ts` -- current same-origin web proxy.
- `frontend/next.config.js`, `amplify.yml` -- current Amplify/Next env handling.
- `deploy/Caddyfile.api`, `deploy/ec2-api-deploy.sh` -- EC2 runtime proxy and SSM secret loading.

## Key Context
- User asked not to use local AWS CLI because it is configured for work. AWS production actions should use the browser console / SSM console unless explicitly changed.
- Current direct backend protection is `SIDIRA_INTERNAL_API_KEY` enforced in FastAPI. `/health` remains public.
- #124 removes the current weakness where Amplify/Next received the internal gateway token so the same-origin web proxy could add `X-Sidira-Internal-Key`.
- Crawler work should wait until #124 is done unless there is a specific customer-product crawl to start.

## For my cofounder
Branch `codex/124-proxy-auth-hardening` starts after PR #129 merged. PR #130 contains the #124 fix. The #124 path keeps browser traffic on `/api`, removes the internal gateway token from Amplify/Next, and lets the EC2/Caddy runtime proxy validate the existing Basic auth header before adding the backend internal key server-side.
