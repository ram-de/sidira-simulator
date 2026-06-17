// /simulations — thin SERVER wrapper that picks the render by the v2 flag (#372).
//
// Flag OFF (default — no NEXT_PUBLIC_V2 env, no sidira_v2 cookie): renders the
// LEGACY list verbatim, byte-identical to before the v2 work. Flag ON: renders
// the v2 "Reading Console" reskin, which carries the same data, states, and
// §8.1 honesty law. v2Enabled() reads next/headers cookies() (server-only), so
// this file has no "use client"; both leaf components keep their own.

import { v2Enabled } from "@/lib/v2flag";
import SimulationsListLegacy from "./SimulationsListLegacy";
import SimulationsListV2 from "./SimulationsListV2";

export default function SimulationsIndexPage() {
  return v2Enabled() ? <SimulationsListV2 /> : <SimulationsListLegacy />;
}
