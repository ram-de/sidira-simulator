# Customer admin console — council consensus (2026-06-27)

**Question:** what should the customer-facing admin console be — structure, admin-vs-member
RBAC, and the data-refresh model for the three customer inputs (experimentation-source
connectors, crawl, persona packs)?

**Method:** 4-member council — codex (repo-grounded feasibility) + 3 Claude lenses
(B2B product/RBAC, data/infrastructure refresh, security/governance). Strong convergence.

---

## The governing principle (unanimous)
**Admin owns the pipes, the people, and the purse; members do the work.** The test for any
control: *does it create persistent workspace state or spend money* (→ admin) *or just run
against state that already exists* (→ member)? **Configuration = admin; execution = member.**

## Console structure (council-ordered)
1. **Members & roles** — the keystone; can't sell seats without it.
2. **Data sources / connectors** — experiment source + credentials; where money/risk live.
3. **Crawl setup** — product-surface ingestion config + run history.
4. **Personas** — persona-pack builds/refreshes (expensive GMM jobs over real data).
5. **Billing & plan** — manual for the first cohort (no UI v1).
6. **Workspace settings** — name, retention, danger zone.
7. **Audit log** — events from day one; viewer later.

## RBAC matrix
Clerk orgs give owner/admin/member. owner+admin → "admin" tier (owner-only extras:
transfer ownership, delete workspace, payment method).

| Capability | Admin/Owner | Member |
|---|---|---|
| Connect/configure experiment source + credentials | ✅ | ❌ |
| Re-import / refresh, run crawl, build personas, run a simulation | ✅ | ✅ |
| Read own `/memory` + shared archive/results | ✅ | ✅ (own `/memory` only) |
| Invite/remove members, set roles | ✅ | ❌ |
| Billing / plan | ✅ (owner: payment) | ❌ |
| Delete connector / workspace, transfer ownership | owner | ❌ |

> `/memory` is now per-user-private, so "read /memory" is self-only for everyone — **not** an
> admin power. **No admin "view all conversations" backdoor** (admin-over-org ≠ admin-over-person).

## Data-refresh model (the founder's questions, answered)
Reproducibility is PARTLY in place: artifacts are immutable versioned snapshots behind a `latest`
pointer, and a `Simulation` row records `persona_pack_version` / `feature_pack_version` /
`run_seed` — but that pinning is **provenance/display only today**. The background run reloads
`latest` again (`simulation_orchestrator.py:223`), so there is **no exact-replay path that
resolves a saved sim against its pinned artifacts** — that is a WORK ITEM (#47), not a solved
guarantee. So a "refresh" safely publishes a new version + flips the pointer for *new* runs, but
re-running an *old* sim today would pick up `latest`, not its pinned version. Given that, refresh
is a freshness-vs-cost call:

- **Experimentation source → one-time import on connect + on-demand "Re-import." NEVER live.**
  Past A/Bs are historical; live per-query buys zero freshness and burns warehouse credits / rate
  limits.
- **Crawl → weekly scheduled (default) + "Crawl now" (override).** Cadence is already modeled
  (`weekly | on_demand`). *Caveat:* no simulator-side scheduler exists yet — weekly automation
  needs a scheduler (cron/Action) or ships on-demand-only in v1.
- **Personas → on-demand "Rebuild" with HUMAN promotion** (stability-gated, expensive, can fail —
  never auto-promote) + a soft "personas are N months old" nudge. No cron.

**Console reproducibility rule (TARGET — partly a work item, #47):** a refresh publishes a new
version; viewing/re-running a saved sim MUST resolve its pinned version, never `latest`. Today the
versions are pinned for provenance but the re-run path still reloads `latest`
(`simulation_orchestrator.py:223`) — closing that is part of #47. Surface the pinned
`persona_pack_version` / `feature_pack_version` on every result page (provenance works now).

## Security / governance hard lines
- **Secrets** (DB creds, Statsig/Snowflake keys): write-only, **never echoed** (return last-4 /
  host / "set ✓"), admin-only create/rotate/delete, redacted in errors (keep the #488 invariant),
  AAD-bound to `customer_id:connection_id` (crypto already built in `adapters/credentials.py`).
- **Cross-tenant + cross-user isolation = a non-bypassable, CI-enforced invariant** (extend
  `test_customer_isolation.py` to the new console surfaces).
- **Cascade delete (FUTURE policy, not current behavior):** today deleting a feature-store keeps
  existing persona-build records and crawl-config delete is config-only (never touches R2
  artifacts) — so derived artifacts currently SURVIVE a source delete. Target policy: deleting a
  source removes its cred blob + derived persona packs — BUT with an explicit exception preserving
  any version a saved sim is pinned to (else delete breaks reproducibility). Reconcile delete vs
  immutable-pinned-artifacts as part of the admin-console data-governance work. Goal: no orphaned
  PII-derived artifacts).
- **Members never see:** raw credential config (beyond last-4), or another member's private
  `/memory` threads.
- **Audit:** append-only, actor + action + target + timestamp, keyed by customer + Clerk user id.

## Feasibility — what exists vs the build delta (codex)
- **Exists:** crawl config persisted (`crawl_configs`, encrypted creds, CRUD, cadence, manual
  trigger → sidira-crawler GitHub Action); feature-store creds persisted (envelope-encrypted,
  list/delete/test); persona builds (trigger API + Postgres worker queue + stability gate +
  versioned packs); auth sets `customer_id` + `user_id`.
- **#1 risk / keystone gap:** **no role enforcement** — `auth.py` ignores the Clerk org role, so
  every member can already save sources / trigger crawls / start persona builds.
- **Delta:** (S) `require_admin` + role extraction; (M/L) persisted *experiment-source*
  connections (today `/connectors` is one-shot, in-memory, creds not persisted); (M) refresh-trigger
  wrappers + status normalization; (M) audit table; (S/M) a console-summary aggregation endpoint;
  the console frontend.

## Recommended v1 (smallest unblock) → tickets
1. **#45 — RBAC foundation** (`require_admin` + Clerk org-role). *Do first; security-critical.*
2. **#46 — persisted experiment-source connections** (connect/manage/re-import, admin-only).
3. **#49 — console frontend + summary endpoint** (v1 = **Members & roles + Data sources** only).
4. **#48 — audit events** (emit from day one; viewer later).
5. **#47 — refresh/trigger model + reproducibility surfacing** (crawl weekly-scheduler, persona
   rebuild+promote nudge, pinned-version display).

Crawl / personas / sims already have member screens, so the v1 admin surface is really
"an admin can hand a member a seat without handing them the database password."
