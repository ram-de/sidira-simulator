// v2 "Reading Console" preview flag (#372). Mirrors the env-gated clerkEnabled()
// pattern (lib/clerk.ts): everything is off by default so production behavior is
// byte-identical until the flag is explicitly turned on. Two switches, OR'd:
//   1. NEXT_PUBLIC_V2 === "1"  — build/deploy-wide opt-in (inlined at build into
//      both server and client bundles, like NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY).
//   2. request cookie sidira_v2 === "1" — a per-browser preview toggle, set by
//      middleware on ?v2=1 and cleared on ?v2=0 (a non-httpOnly preview cookie).
// With no env and no cookie, every helper returns false everywhere.

import { cookies } from "next/headers";

// The build-wide env switch. NEXT_PUBLIC_* is inlined at build into server and
// client bundles alike, so this reads correctly in both contexts.
export const V2_ENV_ON = process.env.NEXT_PUBLIC_V2 === "1";

// The preview cookie name + value. Exported so middleware and the client-side
// reader agree on the exact contract.
export const V2_COOKIE = "sidira_v2";
export const V2_COOKIE_ON = "1";

// Server helper — true if the build env opts in OR the request carries the
// preview cookie. Uses next/headers cookies(), valid in server components and
// route handlers. (cookies() throws outside a request scope; only call it from
// server-rendered code, never module top-level.)
export function v2Enabled(): boolean {
  if (V2_ENV_ON) return true;
  try {
    return cookies().get(V2_COOKIE)?.value === V2_COOKIE_ON;
  } catch {
    // Called outside a request scope (e.g. static generation) — fall back to
    // the env switch only, which V2_ENV_ON already covered above.
    return false;
  }
}

// Client-safe variant — same OR logic, but reads document.cookie instead of
// next/headers (which is server-only). For client components such as
// ConditionalTopNav. Returns false during SSR / when document is unavailable so
// the server and the first client render agree (no hydration mismatch); the
// client effect re-reads after mount.
export function v2EnabledClient(): boolean {
  if (V2_ENV_ON) return true;
  if (typeof document === "undefined") return false;
  return document.cookie
    .split("; ")
    .some((c) => c === `${V2_COOKIE}=${V2_COOKIE_ON}`);
}
