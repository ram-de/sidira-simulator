"use client";
import AppShellV2 from "@/components/v2/AppShellV2";
import AgentChatLegacy from "./AgentChatLegacy";
export default function AgentChatV2() {
  return (
    <AppShellV2 activeNav="simulations" title="Agent" surface="sheet">
      <AgentChatLegacy />
    </AppShellV2>
  );
}
