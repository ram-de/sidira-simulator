// /simulations/[id] — thin SERVER wrapper that picks the render by the v2 flag.
//
// Flag OFF (default): renders the LEGACY reader verbatim, byte-identical to
// before the v2 work. Flag ON: wraps that same legacy reader in the v2 Reading-
// Console shell (AppShellV2, sheet surface) — identical behaviour, v2 chrome.
// v2Enabled() reads next/headers cookies() (server-only), so this file has no
// "use client"; both leaf components keep their own.

import { v2Enabled } from "@/lib/v2flag";
import SimulationDetailLegacy from "./SimulationDetailLegacy";
import SimulationDetailV2 from "./SimulationDetailV2";

export default function SimulationDetailPage() {
  return v2Enabled() ? <SimulationDetailV2 /> : <SimulationDetailLegacy />;
}
