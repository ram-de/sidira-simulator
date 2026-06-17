"use client";

// /simulations/[id]/personas/[persona_id] — v2 shell-wrap (interim).
//
// The persona-group chat surface (~1k lines, two modes sharing one composer)
// gets the v2 Reading-Console chrome (left rail + nav + account switcher) while
// its legacy body renders verbatim on a light Sheet surface inside the rail —
// the composer, both chat modes, drill-down links, and feedback all behave
// exactly as before. A full Console reskin is a deferred follow-up.
import AppShellV2 from "@/components/v2/AppShellV2";
import PersonaGroupChatLegacy from "./PersonaGroupChatLegacy";

export default function PersonaGroupChatV2() {
  return (
    <AppShellV2 activeNav="simulations" title="Persona reactions" surface="sheet">
      <PersonaGroupChatLegacy />
    </AppShellV2>
  );
}
