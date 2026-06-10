import PublicTopBar from "@/components/PublicTopBar";
import { TOKENS, FONT_SANS, FONT_NARROW } from "@/lib/design";

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
      <PublicTopBar currentPath="/about" />

      <article
        style={{
          maxWidth: 720,
          margin: "0 auto",
          padding: "80px 32px 120px",
        }}
      >
        {/* Marketing display — DESIGN.md §5.1: narrow grotesk SemiBold,
            uppercase. No serif anywhere in R2. */}
        <h1
          style={{
            fontFamily: FONT_NARROW,
            fontSize: 48,
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.01em",
            lineHeight: 1.1,
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
