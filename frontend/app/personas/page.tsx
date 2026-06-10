import Link from "next/link";
import { TOKENS, FONT_SANS } from "@/lib/design";
import SampleWorkspaceCard from "@/components/SampleWorkspaceCard";

export default function PersonasIndexPage() {
  return (
    <main style={{ maxWidth: 960, margin: "48px auto", padding: "0 24px", fontFamily: FONT_SANS }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ color: TOKENS.ink }}>Personas</h1>
        <Link
          href="/personas/new"
          style={{
            background: TOKENS.ink,
            color: TOKENS.paper,
            padding: "8px 14px",
            borderRadius: 4,
            textDecoration: "none",
            fontWeight: 500,
            fontSize: 13,
          }}
        >
          + New pack
        </Link>
      </div>
      <p style={{ color: TOKENS.inkMuted }}>
        Connect a feature store, map your columns, and build a versioned persona pack. The most
        recent promoted pack is what your simulations will use.
      </p>

      <section style={{ marginTop: 32 }}>
        <h3 style={{ color: TOKENS.ink }}>Pack versions</h3>
        <p style={{ color: TOKENS.inkMuted, fontSize: 14 }}>
          (Empty state. Backend route <code>GET /persona-packs</code> not yet wired — Phase 4.5.)
        </p>
      </section>

      {/* sessions/sample-workspace: probes GET /personas and renders only
          when this tenant has no Persona Pack yet. */}
      <SampleWorkspaceCard detectEmpty />
    </main>
  );
}
