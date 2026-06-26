// /memory/connect — Experiment-archive onboarding (#19). The v2 Console surface.
//
// The missing "connect your experimentation platform and pull results" flow:
// pick a source -> authenticate/upload -> map fields -> preview -> import ->
// archive populated. CSV works end-to-end now; Statsig/SQL are real connectors
// that work the moment the customer supplies credentials and report an honest
// "needs credentials" state until then — never fabricated data. The leaf
// component carries "use client".

import ConnectFlowV2 from "./ConnectFlowV2";

export default function ConnectPage() {
  return <ConnectFlowV2 />;
}
