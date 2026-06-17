"use client";
import AppShellV2 from "@/components/v2/AppShellV2";
import CrawlSetupLegacy from "./CrawlSetupLegacy";
export default function CrawlSetupV2() {
  return (
    <AppShellV2 activeNav="personas" title="Crawl setup" surface="sheet">
      <CrawlSetupLegacy />
    </AppShellV2>
  );
}
