"use client";
import AppShellV2 from "@/components/v2/AppShellV2";
import FeaturePackLegacy from "./FeaturePackLegacy";
export default function FeaturePackV2({ params }: { params: { version: string } }) {
  return (
    <AppShellV2 activeNav="personas" title="Feature pack" surface="sheet">
      <FeaturePackLegacy params={params} />
    </AppShellV2>
  );
}
