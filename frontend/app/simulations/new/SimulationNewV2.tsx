"use client";

// /simulations/new — v2 shell-wrap (interim).
//
// The run wizard is one of the three dense simulation surfaces (~2.7k lines).
// This pass gives it the v2 Reading-Console chrome (left rail + nav + account
// switcher) while its legacy body renders verbatim on a light Sheet surface
// inside the rail — every field, validation rule, and submit payload behaves
// exactly as before. A full Console reskin of the wizard interior (per the
// /v2/simulations-new mock) is a deferred follow-up.
import AppShellV2 from "@/components/v2/AppShellV2";
import SimulationNewLegacy from "./SimulationNewLegacy";

export default function SimulationNewV2() {
  return (
    <AppShellV2 activeNav="simulations" title="New hypothesis" surface="sheet">
      <SimulationNewLegacy />
    </AppShellV2>
  );
}
