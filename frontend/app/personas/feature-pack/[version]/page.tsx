import { v2Enabled } from "@/lib/v2flag";
import FeaturePackLegacy from "./FeaturePackLegacy";
import FeaturePackV2 from "./FeaturePackV2";
export default function FeaturePackPage({ params }: { params: { version: string } }) {
  return v2Enabled() ? (
    <FeaturePackV2 params={params} />
  ) : (
    <FeaturePackLegacy params={params} />
  );
}
