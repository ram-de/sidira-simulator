// /simulations — the v2 "Reading Console" list (the only design as of the
// global v2 rollout). Carries the §8.1 honesty law. This file has no
// "use client"; the leaf component keeps its own.

import SimulationsListV2 from "./SimulationsListV2";

export default function SimulationsIndexPage() {
  return <SimulationsListV2 />;
}
