import { TOKENS, FONT_SANS } from "@/lib/design";

export default function ProductPage() {
  return (
    <main style={{ maxWidth: 960, margin: "48px auto", padding: "0 24px", fontFamily: FONT_SANS }}>
      <h1 style={{ color: TOKENS.ink }}>Product</h1>
      <p style={{ color: TOKENS.inkMuted }}>
        Connect your product sandbox and declare the capabilities the crawler should walk weekly.
        Each capability becomes a reverse-PRD + reverse-Figma in your Feature Pack.
      </p>
      <p style={{ marginTop: 24, color: TOKENS.inkMuted, fontSize: 14 }}>
        Placeholder. Backed by the crawler producer. Wizard flow lands in a future phase parallel
        to Phase 4.5 (Personas wizard).
      </p>
    </main>
  );
}
