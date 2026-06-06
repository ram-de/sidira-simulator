import Link from "next/link";
import { TOKENS, FONT_SANS, FONT_NARROW, FONT_SERIF } from "@/lib/design";

// Inline duo lockup — three Sid-blue blades + three Avira-rose blades.
// Geometry matches frontend/public/brand/sidira-lockup-duo.svg per DESIGN.md §3.1.
// Used ONLY on the about / cofounder page. Never in the nav or favicon.
function SidiraLockupDuo({ height = 48 }: { height?: number }) {
  return (
    <svg
      width={(height / 60) * 240}
      height={height}
      viewBox="0 0 240 60"
      fill="none"
      role="img"
      aria-label="Sidira — founder mode"
      style={{ display: "block" }}
    >
      <g transform="translate(0 5) scale(0.5)" strokeWidth={2.2} strokeLinejoin="round" fill="none">
        <g stroke="#2C5577">
          <polygon points="50,90 15.359,70 38.740,56.5 50,63" />
          <polygon points="15.359,70 15.359,30 38.740,43.5 38.740,56.5" />
          <polygon points="15.359,30 50,10 50,37 38.740,43.5" />
        </g>
        <g stroke="#D696C8">
          <polygon points="84.641,70 50,90 50,63 61.260,56.5" />
          <polygon points="50,10 84.641,30 61.260,43.5 50,37" />
          <polygon points="84.641,30 84.641,70 61.260,56.5 61.260,43.5" />
        </g>
      </g>
      <text
        x={64}
        y={44}
        fontFamily={FONT_NARROW}
        fontWeight={600}
        fontSize={44}
        letterSpacing={2.6}
        fill={TOKENS.ink}
      >
        SIDIRA
      </text>
    </svg>
  );
}

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
