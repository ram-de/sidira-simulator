// ───────────────────────────────────────────────────────────────────────────
// useOrgRole / useIsOrgAdmin — client-side Clerk org-role gate (#49).
//
// The admin console (Members & roles + Data sources) is an ADMIN surface. The
// AUTHORITATIVE enforcement is the backend `require_admin` (a member's write
// 403s regardless of what the UI shows — api/deps.py). This hook is the UX
// companion: it decides whether to render the admin nav entry + the /admin route
// body for the current user, so a member never sees a dead link or a form they
// can't submit.
//
// Fallback discipline mirrors the backend exactly (api/deps.py DEFAULT_ORG_ROLE):
// when Clerk is NOT configured (local dev / CI, no publishable key) there is no
// session and no role — so we resolve to "admin", the same dev/test default the
// backend's keyless path uses. This keeps the console reachable in local dev
// without auth fixtures. When Clerk IS configured the live session role is
// authoritative: `org:admin` / `org:owner` (or the bare `admin` / `owner`) →
// admin; anything else (member, roleless) → not admin.
// ───────────────────────────────────────────────────────────────────────────
"use client";

import { useAuth } from "@clerk/nextjs";

import { clerkEnabled } from "@/lib/clerk";

// The admin tier per the council RBAC matrix: Clerk owner + admin collapse to
// "admin". Clerk v2 session roles arrive namespaced (`org:admin`); accept the
// bare forms too so a custom role config still classifies. Kept in lockstep with
// the backend `auth.is_admin_role` admin set.
const ADMIN_ROLES = new Set(["org:admin", "org:owner", "admin", "owner"]);

export function isAdminRole(role: string | null | undefined): boolean {
  if (!role) return false;
  return ADMIN_ROLES.has(role.trim().toLowerCase());
}

export type OrgRoleState = {
  // null while Clerk is still loading the session (avoid flashing a member view
  // for an admin, or vice-versa, before the role resolves).
  loading: boolean;
  isAdmin: boolean;
  role: string | null;
};

export function useOrgRole(): OrgRoleState {
  // useAuth is safe to call unconditionally — the ClerkProvider is mounted app-
  // wide. When Clerk is disabled it still returns (isLoaded true, no org role).
  const { isLoaded, orgRole } = useAuth();

  // Keyless dev/CI path: no Clerk → admin (mirrors backend DEFAULT_ORG_ROLE).
  if (!clerkEnabled()) {
    return { loading: false, isAdmin: true, role: "admin" };
  }

  const role = orgRole ?? null;
  return { loading: !isLoaded, isAdmin: isAdminRole(role), role };
}

// Convenience for the common nav/route gate. Returns false while loading so the
// admin chrome appears only once the role is confirmed.
export function useIsOrgAdmin(): boolean {
  const { isAdmin } = useOrgRole();
  return isAdmin;
}
