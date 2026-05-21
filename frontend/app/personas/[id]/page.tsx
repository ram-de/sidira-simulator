export default function PersonaPackDetailPage({ params }: { params: { id: string } }) {
  return (
    <main style={{ maxWidth: 960, margin: "48px auto", padding: "0 24px" }}>
      <h1>Pack {params.id}</h1>
      <p style={{ color: "#555" }}>
        Pack detail. Lists personas with names, descriptions, JTBD, behavioral snapshots, and the
        pack&apos;s stability score. CTA to promote to <code>latest</code>.
      </p>
      <p style={{ marginTop: 24, color: "#888", fontSize: 14 }}>
        Phase 4.5 placeholder. Backend routes: <code>GET /persona-packs/{params.id}</code>,
        <code> POST /persona-packs/{params.id}/promote</code>.
      </p>
    </main>
  );
}
