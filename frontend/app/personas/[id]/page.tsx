import { TOKENS, FONT_SANS } from "@/lib/design";

export default function PersonaPackDetailPage({ params }: { params: { id: string } }) {
  return (
    <main style={{ maxWidth: 960, margin: "48px auto", padding: "0 24px", fontFamily: FONT_SANS }}>
      <h1>Pack {params.id}</h1>
      <p style={{ color: TOKENS.inkMuted }}>
        Pack detail. Lists personas with names, descriptions, JTBD, behavioral snapshots, and the
        pack&apos;s stability score. CTA to promote to <code>latest</code>.
      </p>
      <p style={{ marginTop: 24, color: TOKENS.inkMuted, fontSize: 14 }}>
        Phase 4.5 placeholder. Backend routes: <code>GET /persona-packs/{params.id}</code>,
        <code> POST /persona-packs/{params.id}/promote</code>.
      </p>
    </main>
  );
}
