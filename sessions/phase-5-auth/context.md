---
type: session
domain: phase-5-auth
status: active
started: 2026-05-30
owner: ram-de
---

# Session: phase-5-auth — Phase 5 auth + multi-tenancy (umbrella)

## Goal
Single umbrella session for all Phase 5 auth-related work: production proxy-auth
hardening (#124/#131, shipped) → Clerk session auth + per-request multi-tenancy
(#29, merged) → and the downstream auth chain (#30 scoping audit, #31 signup,
#32 frontend auth pages).

## In Progress
- [ ] **Item 1 — Enable Clerk Organizations** (Clerk dashboard, no code): in flight,
  awaiting founder execution in the dashboard. Runbook prepared (see Next Steps).
- [ ] **Item 2 — Activate #31 webhook in prod** (AWS SSM + Clerk dashboard, no code):
  in flight, awaiting founder execution. Endpoint is `https://api.sidira.ai/webhooks/clerk`
  (Caddy catch-all, no basic-auth; FastAPI `_PUBLIC_PATHS` exempts it). Deploy script
  already loads `/sidira/prod/SIDIRA_CLERK_WEBHOOK_SECRET`. Runbook prepared (see Next Steps).

## Completed

### #32 — Frontend Clerk auth pages + env-gated route protection (MERGED — PR #153, `f958bff`)
- PR #153 squash-merged to `main` 2026-06-07 as `f958bff`; **issue #32 auto-closed**.
  Worktree `phase-5-32-clerk-frontend` removed. Opened/merged via `gh` as `ram-de`.
- Scope **Option 1**: UI + middleware route protection + org-creation at signup +
  pack-based post-signup redirect. Backend token-forwarding through the Caddy proxy
  DEFERRED to **#149** (the remaining prod-enablement blocker for the session gate).
- **Codex P1 FIXED in-PR (auth bypass):** Clerk-path middleware omitted `/api`, so once
  Clerk is enabled an unauthenticated `/api/*` call passed through and the same-origin
  proxy stapled the server's Basic Auth credential → backend reachable without a session.
  Fix: `clerkAuthMiddleware` gates `/api`+`/trpc` on a Clerk `userId`, returning a plain
  **401** (`apiAuthChallenge`, no `www-authenticate`). Test extended to assert the gate.
- Files: `frontend/lib/clerk.ts` (gating + appearance + URLs); `frontend/middleware.ts`
  (clerkMiddleware composed with host redirects, falls back to Basic-Auth when unconfigured);
  `frontend/app/layout.tsx` (conditional `<ClerkProvider>`); `sign-in`/`sign-up`/`sso-callback`
  pages (all `clerkEnabled()`-gated; sso-callback ensures an org via `<CreateOrganization>`
  then routes by `getActivePersonas()` — empty → `/personas/new`, else `/`);
  `components/AuthShell.tsx`, `AuthUnavailable.tsx`, `AuthControls.tsx` (UserButton +
  OrganizationSwitcher in TopNav); `frontend/.env.example`; new env-gating test.
- `@clerk/nextjs` pinned to **v6** (`^6.39.5`); v7 needs Next 15+ (stack is Next 14).
- Verification: build + typecheck + 13 deploy-config tests green; codex clean (P1 → fixed → clean).

### #31 — Clerk webhook → customer (tenant) provisioning (MERGED — PR #152, `415042a`)
- PR #152 squash-merged to `main` as `415042a`; **issue #31 auto-closed**.
- Opened + merged via `gh` CLI as `ram-de` (`github_ramde` MCP server not
  configured this session — used the documented `gh` fallback).
- **Tenancy model decision: customer = Clerk Organization** (one customer/tenant
  with many users). Webhook handles `organization.created` (NOT `user.created`).
  `customer.id == clerk org_id`: the gate's `_extract_customer_id` returns the raw
  `org_id` session claim directly as the tenant key (no DB lookup), and `org_id`
  is the R2 prefix root (`customers/{id}/…`), so global uniqueness prevents prefix
  conflicts.
- New `backend/sidira_simulator/api/webhooks.py` — `POST /webhooks/clerk`:
  returns **503** when `SIDIRA_CLERK_WEBHOOK_SECRET` unset (refuses to act on
  unverifiable deliveries); Svix-verifies every delivery (**401** on bad sig,
  via `except (WebhookVerificationError, ValueError)` so malformed base64 can't
  500); on `organization.created` → `ensure_exists(org_id, name, clerk_org_id=org_id)`
  → **200** `{status: ok, customer_id}`; **400** if org id missing; **200**
  `{status: ignored}` for other events. Public path: signature IS the auth.
- Webhook signing secret is **independent of the session gate** — `auth.py`
  adds `clerk_webhook_secret()` (reads `CLERK_WEBHOOK_SECRET`), distinct from
  `CLERK_SECRET_KEY`. Safe to enable in prod alone (endpoint never sees app
  traffic), unlike the session gate which is still blocked on #149 + #32.
- `main.py`: `_PUBLIC_PATHS = frozenset({"/health", "/webhooks/clerk"})`; both
  gates now check `request.url.path in _PUBLIC_PATHS` so the webhook bypasses the
  session + internal-key gates. Registered `webhooks.router`.
- `repositories.py` `ensure_exists` gained optional `clerk_org_id` (Protocol +
  Postgres + InMemory), backward-compatible.
- **Codex P2 fixed (signup-then-act race):** if a signed-in org hit
  `POST /simulations` before the async `organization.created` landed, the
  orchestrator created a placeholder row (`name == org id`, `clerk_org_id` NULL)
  and the webhook's `ON CONFLICT DO NOTHING` then no-op'd, leaving the record
  unpopulated. Fix: webhook calls now `on_conflict_do_update` the profile fields,
  discriminated on `clerk_org_id IS NOT NULL` (only the webhook passes it), so
  the orchestrator path keeps exact `DO NOTHING` semantics. Mirrored in InMemory.
  Codex re-review: "No actionable bugs found … race appears resolved."
- No new migration: `clerk_org_id` column already exists in `001_initial.py`.
- Added `svix>=1.40` to `backend/pyproject.toml`.
- Tests: new `backend/tests/test_clerk_webhook.py` (8 — secret/sig/provision/
  backfill/idempotency/missing-id/ignored/gate-bypass); +2 repo tests in
  `test_postgres_deps.py` (DO UPDATE SQL + InMemory backfill-then-resist-clobber);
  `test_deploy_config.py` asserts `_PUBLIC_PATHS`.
- Deploy: `ec2-api-deploy.sh` reads + `write_env`s `SIDIRA_CLERK_WEBHOOK_SECRET`
  (unset → endpoint 503s). Documented in `backend/.env.example`.
- Verification: **416 passed / 11 skipped**; ruff + black clean; deploy `bash -n`
  OK. `/codex review` run twice (1 P2 found → fixed → clean).
- GitNexus MCP not connected this session — impact analysis on `ensure_exists`
  done manually (2 callers, optional param, LOW risk, backward-compatible).

### #29 — Clerk SDK install + FastAPI auth middleware (MERGED — PR #150, `a45934f`)
- PR #150 squash-merged to `main` as `a45934f`; **issue #29 auto-closed**.
- Docs follow-up PR #151 merged (`58167ce`): aligned the session-commit rule
  with worktree-session behavior (CLAUDE.md + pythia-session SKILL.md).
- Gate verified locally with curl: gate ON → `/health` 200, `/models` 401 (no
  token AND bogus token), `OPTIONS` bypasses (405 not 401); gate OFF → `/models`
  200 (pass-through). Confirms the 401 is gate-produced and env-controlled.
- Cleanup: removed all merged feature worktrees; `.claude/worktrees/` is empty.
- Added `clerk-backend-api>=5.0` to `backend/pyproject.toml`.
- New `backend/sidira_simulator/api/auth.py`: `clerk_configured()`,
  `authenticate(request) -> AuthState | None`, `_extract_customer_id(payload)`,
  frozen `AuthState(user_id, customer_id)`. Lazily-built `Clerk(bearer_auth=...)`;
  `authenticate_request(... authorized_parties=[...])`.
- `customer_id` via claim chain: `payload["customer_id"]` → `payload["org_id"]`
  → `payload["metadata"]["customer_id"]` (exact claim finalized in #31).
- `clerk_auth_gate` middleware in `main.py`: pass-through when not configured /
  `/health` / `OPTIONS`; else `authenticate()` → 401 on `None`. Registered BEFORE
  `internal_api_key_gate` so the internal-key gate stays outermost.
- Codex P1 (tenant isolation): an authenticated session with `customer_id is None`
  used to fall through to the `SIDIRA_CUSTOMER_ID`/`demo` env default — silently
  granting the fallback tenant. Gate now returns **403 `{"detail": "No tenant for
  user"}`**. Covered by `test_authenticated_without_tenant_is_rejected`.
- `current_customer_id(request)` in `deps.py` prefers `request.state.customer_id`,
  falls back to `resolve_sidira_env("CUSTOMER_ID", "demo")` (backward-compatible).
- New tests in `backend/tests/test_auth_middleware.py` + `test_runtime_config.py`.
- Codex P2: `deploy/ec2-api-deploy.sh` now reads + `write_env`s
  `SIDIRA_CLERK_SECRET_KEY` / `SIDIRA_CLERK_AUTHORIZED_PARTIES` (unset → gate off).
- Guardrail comments in `backend/.env.example` + `deploy/Caddyfile.api`: do NOT
  enable in prod until the proxy forwards Authorization (#149) and the frontend
  sends the token (#32). Filed follow-up issue #149.
- Verification: full suite 406 passed / 11 skipped; ruff + black clean; deploy
  script `bash -n` OK; `git diff --check` clean. `/codex review` run twice.
- Opened PR #150: https://github.com/ram-de/sidira-simulator/pull/150

### #124 / #131 — production proxy-auth hardening (shipped to main)
- #124: web proxy no longer needs a backend gateway token in Amplify/Next.
  Amplify gets only `SIDIRA_API_BASE_INTERNAL=https://api.sidira.ai/_sidira_web_proxy`;
  Caddy `_sidira_web_proxy` validates Basic Auth (SSM values), strips the prefix,
  and injects `X-Sidira-Internal-Key` server-side before proxying to FastAPI.
  Deploy helper requires/writes `SIDIRA_WEB_PROXY_BASIC_AUTH_USER`/`_HASH`.
- Codex P1s fixed: Compose `$`-interpolation corrupting bcrypt hashes (raw
  `api.env` + Compose-safe `api.env.compose`); SSR route losing
  `SIDIRA_API_BASE_INTERNAL` (serialize only the non-secret proxy base).
- Codex P2 fixed: Caddy stripped the forwarded browser `Authorization` via
  `header_up -Authorization` before injecting the internal key.
- PR #130 squash-merged as `1ebbcd14…`; issue #124 closed.
- #131 follow-up: Amplify access control strips `Authorization` before the Next
  `/api` route, so the first design 401'd through `https://sidira.ai/api/*`. Added
  a server-side `SIDIRA_WEB_PROXY_BASIC_AUTH` fallback in the Next route.
  PR #131 squash-merged as `2e2e275f…`. Production smoke passed (200s with creds,
  401 unauth on `sidira.ai/`, 404 unauth on `api.sidira.ai/models`).
- Earlier in the session: PR #129 (Neon URL normalizer + Postgres bootstrap)
  merged as `ad6f49ad…`; #110 producer repo rename scope completed.
- AWS prod actions executed via Console/SSM (not local AWS CLI). Web Basic Auth
  credential rotated twice; active credential is the second rotation (first leaked
  into CloudShell output — treat as compromised).

## Next Steps

**#153 (#32 Clerk frontend), #154 (PreCompact hook), #155 (skill cleanup) all
MERGED to `main` 2026-06-07** (squash: `f958bff`, `1b291d3`, `8bf763a`). All
three worktrees removed; local + remote feature branches deleted. Remaining work:

**Items 1 & 2 are manual dashboard/console actions (Clerk dashboard + AWS Console/SSM)
— the founder executes these; Claude cannot click them. Runbooks below; both verified
code-side ready (deploy script loads the secret, webhook URL is public).**

1. **Enable Clerk Organizations** (Clerk dashboard, not code) so signup can
   create an org — required before the #31 webhook can provision a customer.
   **Runbook:** Clerk dashboard → **Organizations** → toggle **Enable Organizations** on.
   Recommended settings: allow users to create orgs (so `<CreateOrganization>` on the
   sso-callback page works), and (optionally) limit each user to one org for the
   one-customer-per-org tenancy model. Verify a test signup lands on the org-creation
   step and a row appears once the webhook (item 2) is live.

2. **Activate the #31 webhook in prod** — two parts, both manual:
   a. **AWS SSM:** create SecureString `/sidira/prod/SIDIRA_CLERK_WEBHOOK_SECRET`
      with the Clerk signing secret (`whsec_…`) via the **AWS Console** (prod actions
      use Console/SSM, not local CLI). Then re-run `deploy/ec2-api-deploy.sh` on the
      EC2 host so it `write_env`s the value (until then the endpoint returns **503**).
   b. **Clerk dashboard → Webhooks → Add Endpoint:** URL
      `https://api.sidira.ai/webhooks/clerk` (public — Caddy catch-all, no basic-auth;
      FastAPI `_PUBLIC_PATHS` exempts it from both gates). Subscribe to
      **`organization.created`**. Copy the generated signing secret into step (a).
   **Verify:** Clerk "Send test" → expect **200** `{status: ok|ignored}`; a real
   `organization.created` provisions a `customers` row keyed by `org_id`. Bad sig → 401,
   secret unset → 503. Safe on its own — independent of the still-blocked session gate.

3. **#30 — customer-scoping leak audit** (backend; verify every endpoint scopes
   by `customer_id`). Not started — needs explicit go-ahead. Can run in parallel.
4. **Prod-enablement of the Clerk session gate is still BLOCKED** on #149 (Caddy
   must forward Authorization instead of stripping it) and the proxy token hop
   (Next middleware must send the Clerk token; #32 shipped the UI/middleware but
   the token-forwarding hop was deferred to #149). Do NOT set
   `SIDIRA_CLERK_SECRET_KEY` in prod until both ship — flipping it on today would
   401 all app traffic.

Codex CLI note: installed at `~/.npm-global/bin/codex` but off the Bash-tool
PATH — run `export PATH="$HOME/.npm-global/bin:$PATH"` before `codex review`.

## Key Files
- `backend/sidira_simulator/api/webhooks.py` — `POST /webhooks/clerk` org→customer provisioning (#31)
- `backend/sidira_simulator/api/auth.py` — Clerk client + `authenticate()` + `clerk_configured()` (#29) + `clerk_webhook_secret()` (#31)
- `backend/sidira_simulator/adapters/repositories.py` — `ensure_exists(clerk_org_id)` + conflict-backfill (#31)
- `backend/sidira_simulator/main.py` — `clerk_auth_gate` middleware (401/403) + `_PUBLIC_PATHS` allowlist (#31)
- `backend/sidira_simulator/api/deps.py` — `current_customer_id` reads `request.state` first
- `backend/tests/test_auth_middleware.py` — gate tests (#29)
- `deploy/Caddyfile.api`, `deploy/ec2-api-deploy.sh` — EC2 runtime proxy + SSM secret loading
- `backend/.env.example` — Clerk env docs + prod-enablement WARNING
- `frontend/app/api/[...path]/route.ts` — same-origin web proxy (#124/#131)
- `docs/sidira-domain-runbook.md` — production domain/auth/deploy runbook

## Key Context
- **Clerk gate is active only when `CLERK_SECRET_KEY` is configured**; unset =
  pass-through (mirrors `internal_api_key_gate`), so the existing suite stays green.
- Multi-tenancy: a Clerk-gated request only proceeds once it resolves to a
  concrete customer; tenantless authenticated sessions get 403, never the
  env-default tenant.
- Current prod backend protection is the `_sidira_web_proxy` Basic-Auth +
  `X-Sidira-Internal-Key` chain (#124/#131); `/health` stays public. The Clerk
  gate layers on top once #149 + #32 land.
- AWS prod actions use the browser Console / SSM, not the local AWS CLI (it's
  configured for the user's day job).
- GitNexus MCP not connected during #29 — impact analysis done manually (MEDIUM,
  backward-compatible).

## For my cofounder
This is now the single umbrella session for all Phase 5 auth work. #124/#131
(proxy auth) are fully shipped and verified in prod. #29 (Clerk middleware) is
**merged** (PR #150, `a45934f`) and verified locally with curl — the gate is
wired but **inert in prod by design** (secret unset). Before anyone enables it in
production, both #149 (Caddy must forward Authorization instead of stripping it)
and #32 (Next middleware must send the token) have to land, or the gate 401s all
app traffic. **#31 is MERGED** (PR #152, `415042a`) — the `POST /webhooks/clerk` endpoint
provisions one customer per Clerk Organization (customer = tenant with many users)
from `organization.created`, signature-verified via Svix, safe to enable in prod on
its own. **#32 is now in flight** (worktree `phase-5-32-clerk-frontend`): frontend
Clerk pages + env-gated middleware route protection + org-creation at signup (so
#31's webhook fires) + pack-based post-signup redirect. Scope is Option 1 — backend
token-forwarding through the Caddy proxy is deferred to **#149** (the one remaining
prod-enablement blocker after #32). #30 (customer-scoping audit) is next, parallel.
