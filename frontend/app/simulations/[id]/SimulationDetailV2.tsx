"use client";

// /simulations/[id] — v2 shell-wrap (interim).
//
// The live simulation reader is the app's most complex surface (~3.9k lines of
// streaming / polling / run-state). Per the v2 migration call, this pass gives
// it the v2 Reading-Console CHROME — the persistent left rail + nav + Clerk
// account switcher — without rebuilding its interior. The legacy body renders
// verbatim on a light Sheet surface inside the Console rail (a sanctioned
// Console-rail + Sheet-content composition), so nothing is lost: every field,
// poll, and state behaves exactly as before. A full Console reskin of the
// interior is a deferred follow-up.
import AppShellV2 from "@/components/v2/AppShellV2";
import SimulationDetailLegacy from "./SimulationDetailLegacy";

export default function SimulationDetailV2() {
  return (
    <AppShellV2 activeNav="simulations" title="Reading" surface="sheet">
      <SimulationDetailLegacy />
    </AppShellV2>
  );
}
