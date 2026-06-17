import { v2Enabled } from "@/lib/v2flag";
import CapabilityDetailLegacy from "./CapabilityDetailLegacy";
import CapabilityDetailV2 from "./CapabilityDetailV2";
export default function CapabilityDetailPage({ params }: { params: { name: string } }) {
  return v2Enabled() ? (
    <CapabilityDetailV2 params={params} />
  ) : (
    <CapabilityDetailLegacy params={params} />
  );
}
