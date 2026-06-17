"use client";
import AppShellV2 from "@/components/v2/AppShellV2";
import CapabilityDetailLegacy from "./CapabilityDetailLegacy";
export default function CapabilityDetailV2({ params }: { params: { name: string } }) {
  return (
    <AppShellV2 activeNav="personas" title="Capability" surface="sheet">
      <CapabilityDetailLegacy params={params} />
    </AppShellV2>
  );
}
