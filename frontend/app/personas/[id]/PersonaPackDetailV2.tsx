"use client";
import AppShellV2 from "@/components/v2/AppShellV2";
import PersonaPackDetailLegacy from "./PersonaPackDetailLegacy";
export default function PersonaPackDetailV2({ params }: { params: { id: string } }) {
  return (
    <AppShellV2 activeNav="personas" title="Persona pack" surface="sheet">
      <PersonaPackDetailLegacy params={params} />
    </AppShellV2>
  );
}
