import { v2Enabled } from "@/lib/v2flag";
import NewPersonaPackLegacy from "./NewPersonaPackLegacy";
import NewPersonaPackV2 from "./NewPersonaPackV2";
export default function NewPersonaPackPage() {
  return v2Enabled() ? <NewPersonaPackV2 /> : <NewPersonaPackLegacy />;
}
