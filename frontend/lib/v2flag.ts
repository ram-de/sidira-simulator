// v2 "Reading Console" preview flag — SERVER reader (#372). The neutral
// constants + the client-safe reader live in lib/v2-flag-shared.ts (no
// next/headers), so middleware (edge runtime) and client components import from
// there. This module adds the server-component reader and re-exports the shared
// surface so existing `@/lib/v2flag` imports keep working.
//
// Everything is off by default so production behavior is byte-identical until
// the flag is explicitly turned on. Two switches, OR'd: NEXT_PUBLIC_V2 === "1"
// (build-wide) or request cookie sidira_v2 === "1" (per-browser preview toggle,
// set by middleware on ?v2=1 and cleared on ?v2=0).

import { cookies } from "next/headers";
import { V2_ENV_ON, V2_COOKIE, V2_COOKIE_ON } from "./v2-flag-shared";

export {
  V2_ENV_ON,
  V2_COOKIE,
  V2_COOKIE_ON,
  v2EnabledClient,
} from "./v2-flag-shared";

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
