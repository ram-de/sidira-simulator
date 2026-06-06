import Link from "next/link";
import { TOKENS, FONT_SANS, FONT_SERIF } from "@/lib/design";
import SidiraLockupDuo from "@/components/SidiraLockupDuo";

export default function AboutPage() {
  return (
    <main
      style={{
        minHeight: "100vh",
        background: TOKENS.paper,
        color: TOKENS.ink,
        fontFamily: FONT_SANS,
        WebkitFontSmoothing: "antialiased",
      }}
    >
      {/* Top bar — mirrors public homepage header */}
      <header
        style={{
          maxWidth: 1280,
          margin: "0 auto",
          padding: "24px 32px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: `0.75px solid ${TOKENS.rule}`,
        }}
      >
        <Link
          href="/"
          aria-label="Sidira home"
          style={{ color: TOKENS.ink, textDecoration: "none", display: "inline-block" }}
        >
          <SidiraLockupDuo height={36} />
        </Link>
        <Link
          href="/"
          style={{
            color: TOKENS.inkMuted,
            fontFamily: FONT_SANS,
            fontSize: 13,
            fontWeight: 500,
            textDecoration: "none",
          }}
        >
          ← Home
        </Link>
      </header>

      <article
        style={{
          maxWidth: 720,
          margin: "0 auto",
          padding: "80px 32px 120px",
        }}
      >
        {/* Editorial hero — one Instrument Serif moment per page */}
        <h1
          style={{
            fontFamily: FONT_SERIF,
            fontStyle: "italic",
            fontSize: 48,
            fontWeight: 400,
            lineHeight: 1.15,
            color: TOKENS.ink,
            margin: 0,
            marginBottom: 40,
          }}
        >
          Precision before commitment.
        </h1>

        <p
          style={{
            fontSize: 18,
            lineHeight: 1.7,
            color: TOKENS.ink,
            margin: 0,
            marginBottom: 64,
          }}
        >
          Product teams aren&rsquo;t short on hypotheses. They&rsquo;re short on answers that
          arrive before the build commitment. Sidira pressure-tests a proposed change against
          customer-grounded personas so the team knows where it lands before an engineering
          sprint starts.
        </p>


</article>
    </main>
  );
}
