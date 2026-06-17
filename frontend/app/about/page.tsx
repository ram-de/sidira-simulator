import PublicConsoleTopBar from "@/components/PublicConsoleTopBar";
import { ConsoleShell } from "@/components/v2";
import "@/styles/v2-theme.css";

// Dark "Reading Console" reskin of the public /about page. Renders inside a
// `.v2-console` scope so all `var(--console-*)` / `var(--text*)` tokens resolve
// from styles/v2-theme.css. Copy is preserved byte-for-byte from the prior
// paper version (hero line + the single lede paragraph) — only the surface
// changes. The duo aperture mark in the top bar is sanctioned here: /about is a
// brand-mode surface (DESIGN.md §1.3).
export default function AboutPage() {
  return (
    <ConsoleShell>
      <PublicConsoleTopBar currentPath="/about" />

      <article
        style={{
          maxWidth: 760,
          margin: "0 auto",
          padding: "96px 24px 128px",
        }}
      >
        {/* Marketing display — narrow grotesk weight, instrument voice at
            editorial scale on the dark Console. */}
        <h1
          style={{
            fontSize: "clamp(2.6rem, 4.4vw, 3.25rem)",
            fontWeight: 700,
            letterSpacing: "-0.035em",
            lineHeight: 1.02,
            color: "var(--text-hi)",
            textWrap: "balance",
            margin: 0,
            marginBottom: 40,
          }}
        >
          Precision before commitment.
        </h1>

        <p
          style={{
            fontSize: "1.2rem",
            lineHeight: 1.62,
            color: "var(--text)",
            margin: 0,
            marginBottom: 64,
            maxWidth: "60ch",
          }}
        >
          Product teams aren&rsquo;t short on hypotheses. They&rsquo;re short on answers that
          arrive before the build commitment. Sidira pressure-tests a proposed change against
          customer-grounded personas so the team knows where it lands before an engineering
          sprint starts.
        </p>


      </article>
    </ConsoleShell>
  );
}
