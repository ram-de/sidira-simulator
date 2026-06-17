import { v2Enabled } from "@/lib/v2flag";
import PersonaPackDetailLegacy from "./PersonaPackDetailLegacy";
import PersonaPackDetailV2 from "./PersonaPackDetailV2";
export default function PersonaPackDetailPage({ params }: { params: { id: string } }) {
  return v2Enabled() ? (
    <PersonaPackDetailV2 params={params} />
  ) : (
    <PersonaPackDetailLegacy params={params} />
  );
}
