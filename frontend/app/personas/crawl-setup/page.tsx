import { v2Enabled } from "@/lib/v2flag";
import CrawlSetupLegacy from "./CrawlSetupLegacy";
import CrawlSetupV2 from "./CrawlSetupV2";
export default function CrawlSetupPage() {
  return v2Enabled() ? <CrawlSetupV2 /> : <CrawlSetupLegacy />;
}
