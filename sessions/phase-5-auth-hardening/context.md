---
type: session
domain: phase-5-auth-hardening
status: closed
started: 2026-05-30
closed: 2026-05-31
owner: ram-de
---

# Session: phase-5-auth-hardening -- proxy auth and pre-customer hardening

## Goal
Close out the production Postgres bootstrap follow-up, redeploy the merged backend from `main`, and implement #124 so the web proxy no longer needs a backend gateway token in Amplify/Next deployment artifacts.

## In Progress
(nothing)

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
- PR #130 was squash-merged to `main` as `1ebbcd14134f52d74b2fe63f38ef82ab2c17ae06`.
- Issue #124 is closed as completed.
- Executed the #124 production rollout from AWS Console/CloudShell without using
  the local AWS CLI.
- Rotated the web Basic Auth credential twice. The first generated credential
  was discarded because a failed CloudShell command printed its base64 form in
  the terminal error output; the active credential is the second rotation.
- Updated `/sidira/prod/SIDIRA_WEB_PROXY_BASIC_AUTH_USER` to `sidira` through
  SSM Parameter Store version 3.
- Updated `/sidira/prod/SIDIRA_WEB_PROXY_BASIC_AUTH_HASH` with the active
  Caddy-compatible bcrypt hash through SSM Parameter Store version 4.
- Updated Amplify branch Basic Auth for `sidira-simulator/main` to the same
  active username/password pair.
- Added Amplify app-level `SIDIRA_WEB_PROXY_BASIC_AUTH` for the Next SSR proxy.
  `SIDIRA_API_BASE_INTERNAL` remains `https://api.sidira.ai/_sidira_web_proxy`;
  backend gateway/model secrets remain only on EC2/SSM.
- Redeployed the backend through SSM. Run Commands
  `259aa036-8281-4763-99a0-41264e4e17d4` and
  `2ea5ec0e-c348-471a-bed1-8b5269eab8c5` succeeded; later force-recreate helper
  commands `daba9063-2f2b-489b-855e-ff923ce0d7a5` and
  `7715ad79-80b2-4c87-adf2-6d83fd8ff215` ended with Docker exit 125 after the
  deploy helper had already rebuilt/restarted the containers.
- Production verification found one follow-up gap: Amplify access control strips
  the browser `Authorization` header before the Next SSR `/api` route sees it,
  so the first #124 design still produced 401s through `https://sidira.ai/api/*`.
- Opened PR #131: https://github.com/ram-de/sidira-simulator/pull/131.
- PR #131 added a server-side `SIDIRA_WEB_PROXY_BASIC_AUTH` fallback to the Next
  `/api` route, updated Amplify build checks and docs, and was squash-merged to
  `main` as `2e2e275f246e4b522e402e231626533305959b5b`.
- PR #131 verification passed locally: deploy-config test, full backend suite
  (392 passed, 11 skipped), frontend production build with dummy proxy env,
  frontend typecheck, `git diff --check`, and `codex review --base main`.
- Amplify deployed `main` after PR #131. Production smoke passed:
  `https://sidira.ai/api/models` returned 200 with the active Basic Auth
  credential, `https://sidira.ai/api/simulations` returned 200 with the active
  Basic Auth credential, `https://api.sidira.ai/_sidira_web_proxy/models`
  returned 200 with the active Basic Auth credential, unauthenticated
  `https://sidira.ai/` returned 401, and unauthenticated
  `https://api.sidira.ai/models` returned 404.

## Next Steps
— session complete

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
- #124/#131 removed the code/config weakness where Amplify/Next received the
  internal gateway token. Amplify now has only the same-origin proxy base plus a
  web-proxy Basic Auth credential; EC2/Caddy validates that credential and adds
  `X-Sidira-Internal-Key` server-side.
- The active Basic Auth password is from the second rotation. Do not reuse the
  first generated credential; it appeared in CloudShell output and should be
  treated as compromised.
- The #124 production rollout is verified; crawler/product-pack work can resume.

## For my cofounder
#124 is fully rolled out. The production path is now: browser -> Amplify Basic
Auth -> Next `/api` -> Caddy `_sidira_web_proxy` Basic Auth -> FastAPI with
`X-Sidira-Internal-Key` injected only on EC2. The backend gateway token and model
provider keys are not in Amplify. The remaining critical product work can move
back to crawler/product-pack scope.
