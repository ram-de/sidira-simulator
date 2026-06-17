// /simulations/new — thin SERVER wrapper that picks the render by the v2 flag.
//
// Flag OFF (default): renders the LEGACY wizard verbatim, byte-identical to
// before the v2 work. Flag ON: wraps that same legacy wizard in the v2 Reading-
// Console shell (AppShellV2, sheet surface) — identical behaviour, v2 chrome.

import { v2Enabled } from "@/lib/v2flag";
import SimulationNewLegacy from "./SimulationNewLegacy";
import SimulationNewV2 from "./SimulationNewV2";

export default function NewSimulationPage() {
  return v2Enabled() ? <SimulationNewV2 /> : <SimulationNewLegacy />;
}
