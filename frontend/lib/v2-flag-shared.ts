// Neutral v2 "Reading Console" flag constants + the client-safe reader (#372).
// This module imports NOTHING server-only (no next/headers), so it is safe to
// import from middleware (edge runtime) and client components alike. The
// server-only reader lives in lib/v2flag.ts, which re-exports everything here.
//
// As of the global rollout, v2 is ON by default — every migrated route renders
// the Reading Console. It is turned OFF only by an explicit switch, OR'd:
//   1. NEXT_PUBLIC_V2 === "0"  — build/deploy-wide kill switch (inlined at build
//      into both server and client bundles, like the Clerk publishable key).
//   2. request cookie sidira_v2 === "0" — a per-browser opt-out, set by
//      middleware on ?v2=0 and re-enabled on ?v2=1 (a non-httpOnly cookie).
// (The legacy *Legacy.tsx render paths stay reachable via these switches for one
// verification cycle; a follow-up removes the flag + legacy entirely.)

// The build-wide kill switch. NEXT_PUBLIC_* is inlined at build into server and
// client bundles alike, so this reads correctly in both contexts.
export const V2_ENV_OFF = process.env.NEXT_PUBLIC_V2 === "0";
// Retained for the explicit opt-in value (still meaningful as the "on" cookie
// value); v2 is on by default regardless, so this no longer gates anything by
// itself.
export const V2_ENV_ON = process.env.NEXT_PUBLIC_V2 === "1";

// The opt-out cookie name + values. Exported so middleware and the client-side
// reader agree on the exact contract.
export const V2_COOKIE = "sidira_v2";
export const V2_COOKIE_ON = "1";
export const V2_COOKIE_OFF = "0";

// Client-safe reader — same default-ON logic as the server v2Enabled(), but
// reads document.cookie instead of next/headers (server-only). During SSR /
// when document is unavailable it returns the default (true) so server and the
// first client render agree (no hydration mismatch).
export function v2EnabledClient(): boolean {
  if (V2_ENV_OFF) return false;
  if (typeof document === "undefined") return true;
  const optedOut = document.cookie
    .split("; ")
    .some((c) => c === `${V2_COOKIE}=${V2_COOKIE_OFF}`);
  return !optedOut;
}
