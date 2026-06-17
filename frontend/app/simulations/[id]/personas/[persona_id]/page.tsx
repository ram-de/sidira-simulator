// /simulations/[id]/personas/[persona_id] — thin SERVER wrapper that picks the
// render by the v2 flag.
//
// Flag OFF (default): renders the LEGACY persona-group chat verbatim, byte-
// identical to before the v2 work. Flag ON: wraps that same legacy surface in
// the v2 Reading-Console shell (AppShellV2, sheet surface) — identical
// behaviour, v2 chrome.

import { v2Enabled } from "@/lib/v2flag";
import PersonaGroupChatLegacy from "./PersonaGroupChatLegacy";
import PersonaGroupChatV2 from "./PersonaGroupChatV2";

export default function PersonaGroupChatPage() {
  return v2Enabled() ? <PersonaGroupChatV2 /> : <PersonaGroupChatLegacy />;
}
