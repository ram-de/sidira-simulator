import Link from "next/link";
import { TOKENS, FONT_SANS, FONT_MONO } from "@/lib/design";

// Persona pack detail — honest placeholder (R2 PR 6, #168). Pack browsing
// isn't served by the backend yet, so this page says so in user terms
// instead of leaking internal route names. Route stays as-is; the Library
// deliberately doesn't link here until packs are browsable.
export default function PersonaPackDetailPage({ params }: { params: { id: string } }) {
  const packId = decodeURIComponent(params.id);

  return (
    <main style={{ fontFamily: FONT_SANS, color: TOKENS.ink }}>
      <header
        style={{
          padding: "20px 24px 16px",
          borderBottom: `1px solid ${TOKENS.rule}`,
          display: "flex",
          alignItems: "baseline",
          gap: 16,
        }}
      >
        <h1 style={{ margin: 0, fontSize: 20, fontWeight: 600, letterSpacing: "-0.01em" }}>
          Persona pack
        </h1>
        <span
          style={{
            fontFamily: FONT_MONO,
            fontSize: 11,
            color: TOKENS.inkMuted,
            letterSpacing: "0.06em",
          }}
        >
          {packId.toUpperCase()}
        </span>
      </header>

      <div style={{ padding: 24, maxWidth: 640 }}>
        <p style={{ margin: 0, fontSize: 14, lineHeight: 1.5, color: TOKENS.inkMuted }}>
          Pack browsing isn&apos;t available yet. When it ships, this page will list the
          pack&apos;s personas — names, descriptions, jobs-to-be-done, behavioral
          snapshots — alongside the pack&apos;s stability score, and let you promote a
          validated pack to active.
        </p>
        <p style={{ margin: "16px 0 0", fontSize: 14, lineHeight: 1.5 }}>
          <Link
            href="/personas"
            style={{
              color: TOKENS.ink,
              textDecoration: "none",
              borderBottom: `1px dotted ${TOKENS.inkMuted}`,
              fontWeight: 500,
            }}
          >
            ← Back to the Library
          </Link>
        </p>
      </div>
    </main>
  );
}
