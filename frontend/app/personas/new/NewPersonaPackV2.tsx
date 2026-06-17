"use client";
import AppShellV2 from "@/components/v2/AppShellV2";
import NewPersonaPackLegacy from "./NewPersonaPackLegacy";
export default function NewPersonaPackV2() {
  return (
    <AppShellV2 activeNav="personas" title="New persona pack" surface="sheet">
      <NewPersonaPackLegacy />
    </AppShellV2>
  );
}
