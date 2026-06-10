# Auth Provider Portability — Clerk Today, Swappable Tomorrow

**Status:** decision record + living playbook. Written 2026-06-09 (Phase 5,
while shipping the Clerk production cutover).
**Read this before:** touching tenant resolution, the Clerk webhook, the
`customers` schema, or evaluating a move to another auth provider
(WorkOS, Auth0, self-hosted, …).

## Why Clerk (the original decision)

- **Stack fit:** deepest Next.js App Router integration available —
  `clerkMiddleware`, server-side `auth()`, prebuilt `<SignIn>` /
  `<CreateOrganization>` components. With Okta/Auth0 we'd hand-roll all of it.
- **B2B primitive:** Clerk Organizations gives us org-as-tenant out of the box;
  the entire backend tenancy model hangs off the `org_id` session claim.
- **Stage fit:** self-serve, generous free tier, per-MAU pricing. Okta-class
  CIAM is sales-led contract pricing aimed at companies with identity teams.
- **Enterprise path without switching:** Clerk supports per-org SSO
  (SAML/OIDC), SCIM, and verified domains. An enterprise customer who runs
  Okta internally federates *into* our Clerk — their IdP governs access to
  their org, we change nothing. Okta belongs on the customer's side of the
  door, not ours.

Realistic reasons we might still move someday: pricing at scale, data
residency, self-hosting requirements (Clerk is cloud-only), or roadmap drift.
None is a capability cliff; all are "fight it when it's real" concerns.

## The coupling map (every Clerk seam, with file paths)

| Seam | Where | Coupling | Swap cost |
|------|-------|----------|-----------|
| Frontend middleware + UI | `frontend/middleware.ts`, `frontend/app/**` (`clerkMiddleware`, `auth()`, `<SignIn>`, `<CreateOrganization>`, `ClerkProvider`) | High — Clerk SDK throughout the auth UI | Largest chunk; UI plumbing, not business logic. WorkOS AuthKit et al. offer equivalents. |
| Token hop through the proxy | `frontend/app/api/[...path]/route.ts` → `deploy/Caddyfile.api` (`X-Sidira-Clerk-Authorization` carrier header, promoted to `Authorization`) | Cosmetic — any IdP's bearer token rides the same rails | Rename the header if you care; otherwise zero. |
| Backend session gate | `backend/sidira_simulator/api/auth.py` (`authenticate()`, verifies the JWT via the Clerk SDK; `CLERK_SECRET_KEY`, `CLERK_AUTHORIZED_PARTIES`) | Moderate — one module | Swap the verification library + JWKS source. The gate consumes standard claims (`sub`, `org_id`). |
| Tenant resolution seam | `auth._extract_customer_id()` — maps session claims → `request.state.customer_id` | **This is THE seam.** Today: returns the claim value directly (claim == customer id by construction, see below). | At swap time this function changes from claim-passthrough to a mapping lookup. Everything downstream is provider-blind. |
| Tenant provisioning | `backend/sidira_simulator/api/webhooks.py` (`organization.created`, Svix-signed) | Moderate — one endpoint | Rewrite for the new provider's org-created event. Idempotency pattern carries over. |
| Database | `customers.id` (PK) + `customers.clerk_org_id` (unique, nullable) in `backend/sidira_simulator/adapters/db_models.py` | **Already decoupled** — see contract below | Backfill a new mapping column; PKs never change. |
| Object storage | R2 prefixes `customers/<customer_id>/…` | Keyed on `customers.id`, NOT on the provider | Zero — as long as the PK never changes (see contract). |
| Users | Not persisted. Clerk is the system of record; `request.state.user_id` (JWT `sub`) is per-request only. | None in our DB | Clerk exports full user data **including password hashes** for migrations; social logins re-link by email; sessions reset at cutover (users sign in again). |

## The portability contract (the actual insurance — maintain these invariants)

1. **`customers.id` is an opaque internal key and is permanent.** For
   webhook-created tenants its *value* happens to equal the Clerk org id
   (deliberate: globally unique, doubles as the R2 prefix root). That is a
   value coincidence, not a semantic dependency — nothing may ever *parse* a
   customer id or assume it is resolvable at the auth provider. At swap time
   ids keep their values; only the mapping column changes.
2. **`customers.clerk_org_id` is the provider mapping column.** Unique,
   populated by the webhook on every provisioned tenant (including the
   signup-then-act race backfill — see `CustomerRepo.ensure_exists`). This is
   the external-id column that makes a swap a backfill instead of a data
   migration. Never repurpose it; a new provider gets its *own* column
   (e.g. `workos_org_id`).
3. **All tenant-scoped tables carry the internal `customers.id` value** in
   their `customer_id` column, never a raw provider id. New tables must follow
   this. (Most enforce it with a real FK — `simulations` and `agent_instances`
   do; `agent_feedback.customer_id` is a denormalized copy with no FK
   constraint, which is fine for portability: what matters is *which* id is
   stored, not whether the DB enforces the reference.)
4. **Never persist raw provider *user* ids** in our DB without an equivalent
   mapping. Today we persist none — keep it that way, or add a `users` table
   with internal PK + `clerk_user_id` mapping column the day we need one.
5. **All claim→tenant resolution goes through `auth._extract_customer_id()`.**
   No other code may read `org_id`/`customer_id` claims off a token.

Invariants 1–2 are pinned by `backend/tests/test_db_models.py`
(`test_customer_external_id_supports_provider_swap`) and the webhook tests in
`backend/tests/test_clerk_webhook.py`.

## Why we did NOT mint internal UUID PKs (decision, 2026-06-09)

Considered and rejected while in invite-only beta, for three reasons:

1. **It buys nothing the mapping column doesn't already provide.** Swap cost
   is determined by whether new-provider tokens can be mapped to existing
   tenants — `clerk_org_id` enables exactly that. The PK's *value* never needs
   to change; an id that looks like `org_…` forever is cosmetic.
2. **It would rewire the auth hot path now for zero current benefit.** The
   session gate is deliberately DB-free (networkless JWT verification only).
   Divorcing id from the org claim forces a per-request DB/cache lookup today
   instead of at swap time.
3. **It breaks the signup-then-act race handling.** `ensure_exists` dedupes a
   placeholder row (created by a simulation request racing the webhook) against
   the webhook delivery *via the shared id*. Internal minting would create
   duplicate tenants unless that logic is reworked — risk taken on the eve of
   the #149 production flip, for nothing.

If we ever do swap, internal-vs-provider-shaped PK values still won't matter.
Don't reopen this unless invariant 1 is somehow violated.

## Swap playbook (sketch, using WorkOS as the example)

1. Add `workos_org_id` (unique, nullable) to `customers`; backfill by matching
   org metadata / verified domains during a dual-running period.
2. Port the frontend: AuthKit (or equivalent) middleware + components replace
   `@clerk/nextjs`. The proxy token hop is unchanged (rename the carrier
   header if desired).
3. Point the backend gate at the new provider's JWT verification; change
   `_extract_customer_id()` to resolve the new provider's org claim →
   `customers.workos_org_id` → internal id (add a small in-process cache; this
   is the moment the gate gains a lookup).
4. Rewrite the provisioning webhook for the new provider's org-created event,
   keeping the idempotent ensure-exists pattern.
5. Migrate users: Clerk exports emails, profiles, and password hashes; social
   logins re-link by email. Users re-authenticate once at cutover.
6. Decommission: keep `clerk_org_id` frozen as a historical mapping; never
   delete it.

A hybrid is also viable: keep Clerk for product auth and add WorkOS purely for
enterprise SSO connections — less compelling since Clerk grew per-org SSO, but
it's an option short of a full swap.
