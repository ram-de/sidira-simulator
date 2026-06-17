import { v2Enabled } from "@/lib/v2flag";
import AgentChatLegacy from "./AgentChatLegacy";
import AgentChatV2 from "./AgentChatV2";
export default function AgentChatPage() {
  return v2Enabled() ? <AgentChatV2 /> : <AgentChatLegacy />;
}
