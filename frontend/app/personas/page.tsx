import Link from "next/link";

export default function PersonasIndexPage() {
  return (
    <main style={{ maxWidth: 960, margin: "48px auto", padding: "0 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>Personas</h1>
        <Link
          href="/personas/new"
          style={{
            background: "#111",
            color: "#fff",
            padding: "8px 14px",
            borderRadius: 6,
            textDecoration: "none",
            fontWeight: 500,
          }}
        >
          + New pack
        </Link>
      </div>
      <p style={{ color: "#555" }}>
        Connect a feature store, map your columns, and build a versioned persona pack. The most
        recent promoted pack is what your simulations will use.
      </p>

      <section style={{ marginTop: 32 }}>
        <h3>Pack versions</h3>
        <p style={{ color: "#888", fontSize: 14 }}>
          (Empty state. Backend route <code>GET /persona-packs</code> not yet wired — Phase 4.5.)
        </p>
      </section>
    </main>
  );
}
