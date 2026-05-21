import Link from "next/link";

export default function SimulationsIndexPage() {
  return (
    <main style={{ maxWidth: 960, margin: "48px auto", padding: "0 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>Simulations</h1>
        <Link
          href="/simulations/new"
          style={{
            background: "#111",
            color: "#fff",
            padding: "8px 14px",
            borderRadius: 6,
            textDecoration: "none",
            fontWeight: 500,
          }}
        >
          + New simulation
        </Link>
      </div>
      <p style={{ color: "#555" }}>
        Submit a hypothesis. Pythia samples your latest persona pack, runs reactions against your
        latest feature pack, and returns a confidence score plus diagnosed weaknesses. Then chat
        with each agent that participated.
      </p>
      <p style={{ marginTop: 24, color: "#888", fontSize: 14 }}>
        Placeholder list. Backend route <code>GET /simulations</code> lands in Phase 2.
      </p>
    </main>
  );
}
