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
- [ ] **#149 — forward Clerk credential through prod proxy + Next token hop**
  — **PR #158 MERGED to `main` 2026-06-09 as `a917c49`** (worktree removed,
  remote branch deleted). Code side DONE; only the prod flip remains. Design:
  Clerk token rides `X-Sidira-Clerk-Authorization` (the `Authorization` slot
  holds the hop Basic credential consumed by Caddy `basic_auth`); Caddy
  promotes it to `Authorization` upstream and never leaks the Basic credential
  to the backend. Env-gated on the Amplify publishable key — prod behavior
  unchanged until cutover. Verified: typecheck+build, `caddy validate`, live
  header-semantics test (promotion/carrier-drop/no-leak/401-bad-hop), codex
  round 1 clean. Cutover procedure + rollback documented in
  `docs/sidira-domain-runbook.md` § Clerk Production Cutover. Issue #149 stays
  open until the prod flip (Amplify keys + SSM secret together) is executed.
  **Flip pre-flight blocker FIXED 2026-06-09 — PR #159 merged as `0cec35a`:**
  the Codex flip prompt's Step 0b caught that `amplify.yml` writes a curated
  `frontend/.env.production` (Amplify console env vars reach the BUILD only;
  the Next runtime compute never sees them) and the Clerk pair was missing —
  `CLERK_SECRET_KEY` would have been a silent runtime no-op. `amplify.yml` now
  conditionally writes both Clerk vars into `.env.production` (optional =
  keyless pre-cutover/preview builds still pass; half-set pair fails the build
  fast). Also fixed `test_public_api_is_gated_by_backend_internal_key`, which
  was failing on `main` since #158's two-branch Caddyfile split (stale global
  ordering assertion → per-branch invariants). Suite 430 passed; codex round 1
  findings (2 test-strength gaps) addressed. **The flip is now UNBLOCKED** —
  re-run the Codex flip prompt; Step 0b will pass.
- [x] **Item 1 — Enable Clerk Organizations** — DONE on the **Production** instance
  (app `app_3EoIE8Rsl9TGEOJ1wHuXD4zxcVz`, instance `ins_3EoIQrcTqt9VuPdpSVAwEW2QZ3k`,
  `pk_live_`/`sk_live_` keys — confirmed by founder). Organizations enabled;
  **Membership required = Standard** (every user must belong to ≥1 org → always
  resolves to an `org_id`/tenant, aligning with the backend 403-on-tenantless gate);
  **Allow user-created organizations = on**; **Create first organization automatically =
  off** (app drives creation via `<CreateOrganization>`); org-limit-per-user
  Unlimited (capping to 1 was optional, skipped); members-per-org default = 5
  (raise later if customer teams exceed 5).
- [x] **Item 2 — Activate #31 webhook in prod** — backend VERIFIED LIVE 2026-06-07.
  Clerk webhook endpoint registered (`organization.created`) on the **Production**
  Clerk instance pointing at `https://api.sidira.ai/webhooks/clerk`; signing secret
  stored as SecureString `/sidira/prod/SIDIRA_CLERK_WEBHOOK_SECRET` (value starts
  `whsec_`, us-east-1) and deployed to EC2 `i-04b155fafcc90042b` via
  `sudo SIDIRA_DEPLOY_BRANCH=main /opt/sidira/repo/deploy/ec2-api-deploy.sh`.
  Verified: `grep -c SIDIRA_CLERK_WEBHOOK_SECRET /opt/sidira/api.env` → 1; unsigned
  `POST https://api.sidira.ai/webhooks/clerk` → **401** (secret loaded, rejecting).
  **E2E CONFIRMED:** Clerk "Send example" `organization.created` → **Succeeded (200)**
  (msg `msg_3EoMZuWCv332kFbJS…`, 2026-06-07 06:55) — signature verified + customer
  provisioned. NB: the sample event used a placeholder org id, so it created a TEST
  customer row in the prod DB — delete or ignore as test data.
  - **Gotcha encountered:** first deploy ran *before* the SSM param existed → read
    empty → `write_env` skips empty values (script line 59) → endpoint 503'd. Fix
    was just to create the param then re-run the deploy (no code change).
  - **Reachability note:** host-local `curl localhost:8000` returns `000` — port
    8000 is exposed only on the Docker network (Caddy reaches `api:8000`), NOT
    published to the host. Always test through `https://api.sidira.ai/...`.
  - Webhook is wired **Production Clerk instance → prod backend** (no dev/prod split).

## Completed

### Auth-provider portability insurance — docs + invariant pins (this PR)
- Founder asked for "external_id column insurance" against a future Clerk →
  WorkOS (or similar) swap. Scope discovery: **the mapping column already
  exists** — `customers.clerk_org_id` (unique, nullable) has been in the schema
  since migration 001 and is populated by the #31 webhook. What was missing was
  the *contract*: nothing documented why the column exists, that `customers.id`
  is opaque/permanent (its equality with the Clerk org id is a value
  coincidence, not a semantic dependency), or where the provider seams are.
- Shipped: `docs/auth-provider-portability.md` (why Clerk, full coupling map,
  5-invariant portability contract, WorkOS swap playbook), seam-marking
  docstrings on `Customer`, `auth._extract_customer_id` (THE resolution seam),
  and the webhook module, invariant-pinning test
  `test_customer_external_id_supports_provider_swap`, and an ONBOARDING.md
  pointer row.
- **Decision (2026-06-09): did NOT mint internal UUID PKs.** Rationale in the
  doc — the mapping column buys the same swap path; UUID PKs would force a DB
  lookup into the currently DB-free auth hot path and break the
  signup-then-act race dedup (`ensure_exists` keyed on the org claim), all on
  the eve of the #149 flip.

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

**Items 1 & 2 DONE on the Production Clerk instance + prod backend, 2026-06-07**
(Organizations enabled; webhook live + E2E-confirmed via Clerk "Send example" → 200).
Remaining work is the rest of Production go-live wiring + the still-blocked session gate:

1. ✅ **Enable Clerk Organizations** — DONE on the Production instance (see In Progress).
2. ✅ **Activate the #31 webhook** — DONE on the Production instance, E2E-confirmed
   (Clerk "Send example" `organization.created` → Succeeded/200). Fully live.

3. **Finish Production Clerk go-live wiring** (the non-webhook parts): verify the
   `sidira.ai` **domain/DNS** in the Production instance (CNAMEs for Clerk's frontend
   API) and put the `pk_live_`/`sk_live_` keys into the **Amplify** frontend env. These
   only light up sign-in/up, which is gated behind #149 anyway — so sequence with #149.
   **[PAUSED 2026-06-07 — decision pending before any action.]** Analysis done this
   session: adding `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` to Amplify is a **hard prod auth
   cutover**, not additive — `frontend/middleware.ts` ends with
   `clerkEnabled() ? clerkAuthMiddleware : basicAuthMiddleware`, so the publishable key
   swaps the temporary Basic-Auth gate for Clerk sign-in the instant it deploys.
   Prerequisites/gotchas captured for resume:
   - **Domain/DNS first:** `pk_live_`/`sk_live_` are domain-bound — must add + verify
     CNAMEs in Clerk → Configure → Domains (Clerk frontend API on `clerk.app.sidira.ai`
     or similar) BEFORE the keys work.
   - **Both keys together in Amplify:** `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` (pk_live) +
     `CLERK_SECRET_KEY` (sk_live) — Next `clerkMiddleware`/`auth()` needs the secret
     server-side. This is the **frontend** secret, SEPARATE from the backend's
     `SIDIRA_CLERK_SECRET_KEY` on EC2 (which stays unset; that's the #149-blocked one).
   - **Lockout risk:** Clerk replaces the Basic-Auth gate; with invite-only now on, the
     founder must have a Clerk account on the Production instance first (create org +
     self-invite, confirm sign-in) or risk locking out of the prod app.
   - **Not tenant-scoped until #149:** signed-in users' API calls still hit the backend
     default tenant (`streamly_sample`) via the Basic-Auth proxy hop — org isolation is
     not end-to-end until #149. Reversible (remove key + redeploy).
   - **DECIDED 2026-06-09: (a) stage safely.** Verify Clerk domain/DNS + create
     founder org/account (self-invite, confirm hosted sign-in) — NO Amplify keys yet;
     the Amplify flip happens later together with #149 as one coherent cutover.
   - **Staged-cutover runbook (founder-in-browser, safe to do anytime — nothing
     here changes prod traffic):**
     1. *Verify the production domain:* Clerk Dashboard → Production instance
        (`ins_3EoIQrcTqt9VuPdpSVAwEW2QZ3k`) → **Configure → Domains** → set
        `sidira.ai` as the production domain. Clerk shows the required DNS
        records (frontend API CNAME like `clerk.sidira.ai`, plus
        `accounts.`/`clkmail.`/DKIM ones). Add each CNAME wherever sidira.ai
        DNS is hosted (Route 53), then wait for all checks in the Clerk Domains
        page to turn green. `pk_live_`/`sk_live_` keys don't work until this
        verifies.
     2. *Create the founder's org + account (lockout insurance):* Dashboard →
        **Organizations → Create organization** (e.g. "Sidira") — this fires
        `organization.created` → the live #31 webhook provisions the `customers`
        row (verify: 200 in the webhook log). Then invite via **ORGANIZATION
        invitation** (Organizations → org → Members → Invite member — NOT
        instance-level Users → Invitations: with membership-required +
        user-created-orgs OFF, an org-less user is stranded); accept the invite
        and sign in via Clerk's hosted Account Portal (`accounts.sidira.ai`
        once DNS verifies) to confirm the production sign-in flow end-to-end.
     3. *Stop there.* Do NOT add `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` /
        `CLERK_SECRET_KEY` to Amplify — that's the hard cutover, deferred to
        ship together with #149.
   - **STEPS 1–2 DONE 2026-06-09 (founder-in-browser).** All 5 CNAMEs added in
     Route 53 and verified in Clerk; TLS certs issued and confirmed by probe
     (`clerk.sidira.ai` frontend API → HTTP 200; `accounts.sidira.ai` serves a
     valid Google Trust Services cert — curl 403 on it is Clerk bot protection,
     browser works). Founder org created; users invited via org invitations,
     accepted, and **completed signup**. Two hiccups en route, same root cause:
     no invite email + portal unreachable = domain verification hadn't been run
     yet in Clerk (cert issuance and email sending are both gated on verify).
     **Sanity check CONFIRMED 2026-06-09: founder verified the Clerk webhook
     log is clean (200 Succeeded on the real org events) — `customers` row
     provisioned.** Staged cutover steps 1+2 fully closed. Step 3 holds — no
     Amplify keys until #149, which is now the active work item.
4. **#30 — customer-scoping leak audit** — **AUDIT COMPLETE 2026-06-09, NO LIVE
   LEAKS** (founder go-ahead given; ran in parallel with the staged cutover prep).
   **PR #157 MERGED to `main` as `f346760`; issue #30 auto-closed.** Worktree
   removed; remote branch deleted.
   - **Findings:** every live route threads `Depends(current_customer_id)` into
     repo/store calls; both Postgres + InMemory repo implementations filter every
     get/list/touch/update on `customer_id`; all R2 keys embed
     `customers/{customer_id}/…` (agent memory, feedback.jsonl, run state, events).
     `models.py`/`config.py` are tenant-agnostic by design. The only unscoped
     routers were the three **Phase 4.5 501 stubs** (`persona_packs`,
     `persona_builds`, `feature_stores`) — not live leaks; no hotfix issues needed
     per #30 acceptance.
   - **Deliverable:** new `backend/tests/test_customer_isolation.py` — the
     cross-customer isolation matrix (SimulationRepo, AgentInstanceRepo,
     AgentFeedbackRepo, AgentMemory, FeedbackLog, RunStateStore) plus
     `test_every_route_resolves_the_tenant`, a route-walking regression guard:
     every route must depend on `current_customer_id` or sit on an explicit
     commented allowlist (`/health`, `/webhooks/clerk`, `/models`,
     `/config/limits`). The 3 stub routers got the dependency added now so future
     implementers inherit the wiring.
   - **Drive-by fix:** `test_feedback_api.py` concurrent-thumbs test used legacy
     `asyncio.get_event_loop().run_until_complete(...)` which raises on 3.11+ once
     any earlier pytest-asyncio test unsets the loop — switched to `asyncio.run()`.
   - Verification: 429 passed / 11 skipped; ruff + black clean. `/codex review`
     run twice (round 1: P2 no-Postgres-coverage + 2 P3s → all fixed → round 2
     clean). Postgres repos now covered too: SQL-shape tests assert the
     customer_id predicate; stub-row tests prove cross-customer get/update/touch
     reject without committing. GitNexus MCP not connected — manual impact
     analysis (stub handlers have no in-code callers; LOW risk).
5. **Prod-enablement of the Clerk session gate is still BLOCKED** on #149 (Caddy
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
- **Onboarding evolution (intended path): invite-only → capped self-serve →
  per-org SSO.** Same Clerk org=customer model the whole way; only the "door"
  tightens/loosens per customer size. (1) *Now:* invite-only (Clerk Restrictions)
  for design partners — no stranger can provision a tenant. (2) *Launch:* open
  self-serve, but gated by email verification + bot protection + a free-tier
  **usage cap** (LLM agents run on our API keys, so open signup without a cap =
  strangers spending our money). Signup gate decides *who's in the door*; tenant
  isolation (#30) + usage limits decide *what they can do inside*. (3) *Enterprise:*
  Clerk supports per-org **SSO (SAML/OIDC) + SCIM + verified domains** — turn on
  per-tenant, customer's Okta/Azure AD governs access, zero self-signup. No rebuild
  at any stage — just stricter doors as customers grow.
- **Production Clerk is now in invite-only beta posture (set 2026-06-07):**
  (1) Sign-ups restricted to invitation-only (Protect → Restrictions) — no random
  internet account creation. (2) "Allow user-created organizations" = OFF
  (Organizations → Settings) — only the founder provisions each customer's org from
  the dashboard, which still fires `organization.created` → provisions the
  `customers` row; invited users then join that org. Implication for #32: invited
  users won't hit the frontend `<CreateOrganization>` step (they join a pre-made
  org) — correct invite-only behavior, no breakage since the frontend isn't live in
  Amplify yet. To open self-serve later: reverse both toggles + add email
  verification + bot protection + free-tier usage cap.

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
prod-enablement blocker after #32). **#30 is DONE and MERGED (PR #157, `f346760`)
— no live leaks found**; the isolation test matrix + route-scoping regression
guard now run in CI, and the Phase 4.5 stub routers carry the scoping dependency.
Cutover decision made 2026-06-09: stage safely (Clerk DNS + founder self-invite
now, Amplify keys later with #149) — step-by-step runbook is in Next Steps item 3.
