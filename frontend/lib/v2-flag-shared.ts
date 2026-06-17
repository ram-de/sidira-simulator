// Neutral v2 "Reading Console" flag constants + the client-safe reader (#372).
// This module imports NOTHING server-only (no next/headers), so it is safe to
// import from middleware (edge runtime) and client components alike. The
// server-only reader lives in lib/v2flag.ts, which re-exports everything here.
//
// Everything is OFF by default, so production behavior is byte-identical until
// the flag is explicitly turned on. Two switches, OR'd:
//   1. NEXT_PUBLIC_V2 === "1"  — build/deploy-wide opt-in (inlined at build into
//      both server and client bundles, like NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY).
//   2. request cookie sidira_v2 === "1" — a per-browser preview toggle, set by
//      middleware on ?v2=1 and cleared on ?v2=0 (a non-httpOnly preview cookie).

// The build-wide env switch. NEXT_PUBLIC_* is inlined at build into server and
// client bundles alike, so this reads correctly in both contexts.
export const V2_ENV_ON = process.env.NEXT_PUBLIC_V2 === "1";

// The preview cookie name + value. Exported so middleware and the client-side
// reader agree on the exact contract.
export const V2_COOKIE = "sidira_v2";
export const V2_COOKIE_ON = "1";

// Client-safe reader — same OR logic as the server v2Enabled(), but reads
// document.cookie instead of next/headers (which is server-only). Returns false
// during SSR / when document is unavailable so the server and the first client
// render agree (no hydration mismatch); a client effect can re-read after mount.
export function v2EnabledClient(): boolean {
  if (V2_ENV_ON) return true;
  if (typeof document === "undefined") return false;
  return document.cookie
    .split("; ")
    .some((c) => c === `${V2_COOKIE}=${V2_COOKIE_ON}`);
}
