import PublicConsoleTopBar from "@/components/PublicConsoleTopBar";
import { ConsoleShell } from "@/components/v2";
import "@/styles/v2-theme.css";

// Dark "Reading Console" reskin of the public /product page. Renders inside a
// `.v2-console` scope so all `var(--console-*)` / `var(--text*)` tokens resolve
// from styles/v2-theme.css. Copy is preserved byte-for-byte from the prior
// paper version — only the surface + the shared public top bar change.
export default function ProductPage() {
  return (
    <ConsoleShell>
      <PublicConsoleTopBar currentPath="/product" />

      <section
        style={{
          maxWidth: 960,
          margin: "0 auto",
          padding: "96px 24px 112px",
        }}
      >
        <h1
          style={{
            color: "var(--text-hi)",
            fontSize: "clamp(2.4rem, 4vw, 3rem)",
            fontWeight: 700,
            letterSpacing: "-0.035em",
            lineHeight: 1.04,
            margin: 0,
            textWrap: "balance",
          }}
        >
          Product
        </h1>
        <p
          style={{
            color: "var(--text)",
            fontSize: "1.2rem",
            lineHeight: 1.6,
            marginTop: 24,
            maxWidth: "60ch",
          }}
        >
          Connect your product sandbox and declare the capabilities the crawler should walk weekly.
          Each capability becomes a reverse-PRD + reverse-Figma in your Feature Pack.
        </p>
        <p
          style={{
            marginTop: 24,
            color: "var(--text-mut)",
            fontSize: 14,
            lineHeight: 1.6,
            maxWidth: "60ch",
          }}
        >
          Placeholder. Backed by the crawler producer. Wizard flow lands in a future phase parallel
          to Phase 4.5 (Personas wizard).
        </p>
      </section>
    </ConsoleShell>
  );
}
