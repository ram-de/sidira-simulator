// v2 "Reading Console" flag — SERVER reader (#372). The neutral constants + the
// client-safe reader live in lib/v2-flag-shared.ts (no next/headers), so
// middleware (edge runtime) and client components import from there. This
// module adds the server-component reader and re-exports the shared surface so
// existing `@/lib/v2flag` imports keep working.
//
// As of the global rollout, v2 is ON by default. It is turned OFF only by an
// explicit switch: NEXT_PUBLIC_V2 === "0" (build-wide kill switch) or request
// cookie sidira_v2 === "0" (per-browser opt-out, set by middleware on ?v2=0 and
// re-enabled on ?v2=1).

import { cookies } from "next/headers";
import { V2_ENV_OFF, V2_COOKIE, V2_COOKIE_OFF } from "./v2-flag-shared";

export {
  V2_ENV_ON,
  V2_ENV_OFF,
  V2_COOKIE,
  V2_COOKIE_ON,
  V2_COOKIE_OFF,
  v2EnabledClient,
} from "./v2-flag-shared";

// Server helper — true unless explicitly opted out (env kill switch or the
// per-browser opt-out cookie). Uses next/headers cookies(), valid in server
// components and route handlers. (cookies() throws outside a request scope;
// only call it from server-rendered code, never module top-level.)
export function v2Enabled(): boolean {
  if (V2_ENV_OFF) return false;
  try {
    if (cookies().get(V2_COOKIE)?.value === V2_COOKIE_OFF) return false;
  } catch {
    // Called outside a request scope (e.g. static generation) — no cookie to
    // read; fall through to the default (on). The env kill switch above still
    // applies.
  }
  return true;
}
