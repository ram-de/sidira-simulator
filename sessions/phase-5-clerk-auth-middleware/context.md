---
type: session
domain: phase-5-clerk-auth-middleware
status: active
started: 2026-06-06
owner: ram-de
---

# Session: phase-5-clerk-auth-middleware — #29 Clerk SDK install + FastAPI auth middleware

## Goal
Install the Clerk Python SDK and add FastAPI middleware that validates the Clerk
session token on every non-`/health` request and populates `request.state.user_id`
+ `request.state.customer_id` — the keystone of the Phase 5 auth chain (#29).

## In Progress
(nothing — implementation complete, PR #150 open and awaiting review/merge)

## Completed
- Added `clerk-backend-api>=5.0` to `backend/pyproject.toml`.
- New module `backend/sidira_simulator/api/auth.py`: `clerk_configured()`,
  `authenticate(request) -> AuthState | None`, `_extract_customer_id(payload)`,
  frozen `AuthState(user_id, customer_id)` dataclass. Lazily-built module-level
  `Clerk(bearer_auth=...)`; `authenticate_request(... authorized_parties=[...])`.
- `customer_id` resolved via a claim chain: `payload["customer_id"]` →
  `payload["org_id"]` → `payload["metadata"]["customer_id"]` (exact claim
  finalized in #31 signup; reading a documented chain keeps #29 self-contained).
- `clerk_auth_gate` middleware in `backend/sidira_simulator/main.py`:
  pass-through when `not clerk_configured()`, on `/health`, or `OPTIONS`;
  else `authenticate()` → 401 when `None`. Registered BEFORE
  `internal_api_key_gate` so the internal-key gate stays outermost (Caddy must
  clear the network boundary before we spend a token verification).
- Codex P1 fix — tenantless-session isolation hole: an authenticated session
  with `customer_id is None` used to fall through and `current_customer_id`
  would resolve the `SIDIRA_CUSTOMER_ID`/`demo` env default, silently granting
  the fallback tenant. Gate now returns **403 `{"detail": "No tenant for user"}`**
  instead. Covered by `test_authenticated_without_tenant_is_rejected`.
- `current_customer_id(request)` in `backend/sidira_simulator/api/deps.py` now
  prefers `request.state.customer_id`, falls back to
  `resolve_sidira_env("CUSTOMER_ID", "demo")`. Additive/backward-compatible with
  all existing `Depends(current_customer_id)` call sites.
- New tests `backend/tests/test_auth_middleware.py` (pass-through, 401,
  /health + OPTIONS exempt, session-beats-env, tenantless-403, claim-chain
  extraction) + `test_runtime_config.py` env-default coverage.
- Codex P2 fix — `deploy/ec2-api-deploy.sh` now reads + `write_env`s
  `SIDIRA_CLERK_SECRET_KEY` and `SIDIRA_CLERK_AUTHORIZED_PARTIES` from SSM
  (unset → gate stays disabled, preserving pre-auth deploy behavior).
- Documented the two env vars in `backend/.env.example` with a WARNING block:
  do NOT enable in prod until the frontend (#32) sends the Clerk token AND the
  prod proxy forwards it.
- Codex 2nd-pass P1 (prod proxy strips Authorization): determined to be a
  deployment-sequencing dependency, NOT a diff defect (gate off by default).
  Added guardrail NOTE comments to `deploy/Caddyfile.api` (above
  `header_up -Authorization`) and `backend/.env.example`. Scoped to follow-up
  issue #149.
- Verification: full suite 406 passed / 11 skipped; ruff clean; black clean;
  `bash -n` on deploy script OK; `git diff --check` clean.
- `/codex review` run twice (P1+P2 fixed in-diff; 2nd pass scoped to #149).
- Opened PR #150: https://github.com/ram-de/sidira-simulator/pull/150
  (branch `worktree-29-clerk-auth-middleware`).
- Filed follow-up issue #149 for prod enablement (proxy + frontend must forward
  the Clerk credential before flipping the secret on).

## Next Steps
1. Land PR #150 once review passes.
2. Prod enablement is gated on #149 (proxy forwards Authorization) and #32
   (Next middleware sends the Clerk token). Do NOT set SIDIRA_CLERK_SECRET_KEY
   in prod until both ship — flipping it on today would 401 all app traffic.
3. Downstream Phase 5 chain unblocked by #29: #30 (scoping audit), #31 (signup),
   #32 (frontend auth pages).

## Key Files
- `backend/sidira_simulator/api/auth.py` — Clerk client + `authenticate()` + `clerk_configured()` (new)
- `backend/sidira_simulator/main.py` — `clerk_auth_gate` middleware (401/403)
- `backend/sidira_simulator/api/deps.py` — `current_customer_id` reads `request.state` first
- `backend/tests/test_auth_middleware.py` — gate tests (new)
- `backend/pyproject.toml` — `clerk-backend-api>=5.0`
- `deploy/ec2-api-deploy.sh` — SSM read + write_env for the two Clerk vars
- `deploy/Caddyfile.api` — guardrail NOTE above `header_up -Authorization`
- `backend/.env.example` — env docs + prod-enablement WARNING

## Key Context
- Gate is **active only when `CLERK_SECRET_KEY` is configured**; unset = pass-through
  (mirrors `internal_api_key_gate`), so the existing suite stays green with no overrides.
- Multi-tenancy: a Clerk-gated request only proceeds once it resolves to a concrete
  customer; tenantless authenticated sessions get 403, never the env-default tenant.
- GitNexus MCP not connected this session — impact analysis done manually (MEDIUM,
  backward-compatible).

## For my cofounder
#29 is done and in PR #150; the Clerk gate is wired but **inert in prod by design**
(secret unset). Before anyone enables it in production, both #149 (Caddy must forward
Authorization instead of stripping it) and #32 (Next middleware must send the token)
have to land — otherwise the gate 401s all app traffic. Everything else in the Phase 5
auth chain (#30/#31/#32) is now unblocked.
