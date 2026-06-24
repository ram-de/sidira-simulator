// /simulations/new — the v2 Reading-Console wizard (AppShellV2, sheet surface).
// This file has no "use client"; the leaf component keeps its own.
//
// #44: the wizard now reads ?parent / ?prose via useSearchParams for the
// refinement carry-through, so it MUST sit under a Suspense boundary (Next.js
// App Router requires one for useSearchParams or `next build` errors).

import { Suspense } from "react";
import SimulationNewV2 from "./SimulationNewV2";

export default function NewSimulationPage() {
  return (
    <Suspense fallback={null}>
      <SimulationNewV2 />
    </Suspense>
  );
}
