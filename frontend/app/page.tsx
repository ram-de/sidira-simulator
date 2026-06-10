import Link from "next/link";
import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { isPublicSiteHost } from "@/lib/site-hosts";
import PublicTopBar, { APP_URL } from "@/components/PublicTopBar";
import { TOKENS, FONT_SANS, FONT_NARROW, FONT_MONO } from "@/lib/design";

export default function HomePage() {
  const host = headers().get("host");

  if (isPublicSiteHost(host)) {
    return <PublicCompanyHome />;
  }

  // App host has no home surface in the R2 IA — the hypotheses register IS
  // the landing page (epic #156).
  redirect("/simulations");
}


const STEPS = [
  {
    title: "Describe the bet",
    body: "Capture the proposed product change and the audience it should move. Sidira reads PRDs and Figma the way your reviewers do.",
  },
  {
    title: "Run the simulation",
    body: "See where customer reactions cluster before the team commits build time. Every agent in the cohort can be interviewed afterwards.",
  },
  {
    title: "Refine with evidence",
    body: "Turn weak spots into sharper hypotheses for the next product review. Iterate before the build, not after the rollout.",
  },
];

function PublicCompanyHome() {
  return (
    <main
      style={{
        minHeight: "100vh",
        background: TOKENS.paper,
        color: TOKENS.ink,
        fontFamily: FONT_SANS,
        fontFeatureSettings: '"ss01" on',
        WebkitFontSmoothing: "antialiased",
      }}
    >
      {/* Narrow-viewport collapse for the multi-column grids. Scoped via
          classNames so the inline-style convention used elsewhere stays
          intact. */}
      <style>{`
        @media (max-width: 768px) {
          .sidira-public-section-head { grid-template-columns: 1fr !important; }
          .sidira-public-step-row { grid-template-columns: 1fr !important; gap: 8px !important; }
        }
      `}</style>

      {/* Top bar — shared with /about */}
      <PublicTopBar />

      {/* Hero */}
      <section
        style={{
          maxWidth: 1280,
          margin: "0 auto",
          padding: "96px 32px 112px",
        }}
      >
        <p
          style={{
            color: TOKENS.inkMuted,
            fontFamily: FONT_MONO,
            fontFeatureSettings: '"tnum" on',
            fontSize: 11,
            letterSpacing: "0.08em",
            margin: "0 0 32px",
            textTransform: "uppercase",
            display: "inline-flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <span
            aria-hidden
            style={{
              width: 6,
              height: 6,
              background: TOKENS.signal,
              display: "inline-block",
            }}
          />
          Private alpha · 2026
        </p>
        {/* Marketing display — DESIGN.md §5.1: narrow grotesk SemiBold,
            uppercase, 64–96px. No serif anywhere in R2. */}
        <h1
          style={{
            color: TOKENS.ink,
            fontFamily: FONT_NARROW,
            fontWeight: 600,
            textTransform: "uppercase",
            fontSize: "clamp(48px, 7vw, 96px)",
            lineHeight: 1.1,
            letterSpacing: "0.01em",
            margin: 0,
            maxWidth: "18ch",
          }}
        >
          Validate product bets before you build.
        </h1>
        <p
          style={{
            color: TOKENS.inkMuted,
            fontFamily: FONT_SANS,
            fontSize: 18,
            lineHeight: 1.55,
            margin: "32px 0 0",
            maxWidth: "60ch",
          }}
        >
          Sidira pressure-tests product hypotheses against customer-grounded
          personas. Read the cohort&rsquo;s reaction before the roadmap bet
          becomes an engineering commitment.
        </p>
        <div
          style={{
            display: "flex",
            gap: 12,
            marginTop: 48,
            flexWrap: "wrap",
          }}
        >
          <Link
            href="mailto:founders@sidira.ai?subject=Sidira%20access"
            style={{
              background: TOKENS.ink,
              border: `0.75px solid ${TOKENS.ink}`,
              borderRadius: 4,
              color: TOKENS.paper,
              fontFamily: FONT_NARROW,
              fontSize: 13,
              fontWeight: 600,
              letterSpacing: "0.08em",
              padding: "14px 22px",
              textDecoration: "none",
              textTransform: "uppercase",
            }}
          >
            Request access
          </Link>
          <Link
            href={APP_URL}
            style={{
              background: "transparent",
              border: `0.75px solid ${TOKENS.rule}`,
              borderRadius: 4,
              color: TOKENS.ink,
              fontFamily: FONT_NARROW,
              fontSize: 13,
              fontWeight: 600,
              letterSpacing: "0.08em",
              padding: "14px 22px",
              textDecoration: "none",
              textTransform: "uppercase",
            }}
          >
            Sign in
          </Link>
        </div>
      </section>

      {/* How it works — three steps separated by hairlines, no colored circles */}
      <section
        style={{
          maxWidth: 1280,
          margin: "0 auto",
          padding: "0 32px 112px",
        }}
      >
        <div
          className="sidira-public-section-head"
          style={{
            display: "grid",
            gridTemplateColumns: "200px 1fr",
            gap: 32,
            paddingBottom: 32,
          }}
        >
          <p
            style={{
              color: TOKENS.inkMuted,
              fontFamily: FONT_MONO,
              fontSize: 11,
              letterSpacing: "0.08em",
              margin: 0,
              textTransform: "uppercase",
            }}
          >
            How it works
          </p>
          <h2
            style={{
              color: TOKENS.ink,
              fontFamily: FONT_SANS,
              fontWeight: 500,
              fontSize: 26,
              letterSpacing: "-0.01em",
              lineHeight: 1.25,
              margin: 0,
              maxWidth: "40ch",
            }}
          >
            One instrument, three steps, no roadmap bet escaping unexamined.
          </h2>
        </div>

        <ol
          style={{
            listStyle: "none",
            margin: 0,
            padding: 0,
            borderTop: `0.75px solid ${TOKENS.rule}`,
          }}
        >
          {STEPS.map((step, idx) => (
            <li
              key={step.title}
              className="sidira-public-step-row"
              style={{
                display: "grid",
                gridTemplateColumns: "200px 1fr 1fr",
                gap: 32,
                padding: "32px 0",
                borderBottom: `0.75px solid ${TOKENS.rule}`,
                alignItems: "baseline",
              }}
            >
              <span
                style={{
                  color: TOKENS.ink,
                  fontFamily: FONT_MONO,
                  fontFeatureSettings: '"tnum" on',
                  fontSize: 14,
                  fontWeight: 500,
                  letterSpacing: "0.04em",
                }}
              >
                {String(idx + 1).padStart(2, "0")} ·{" "}
                <span style={{ color: TOKENS.inkMuted }}>step</span>
              </span>
              <h3
                style={{
                  color: TOKENS.ink,
                  fontFamily: FONT_SANS,
                  fontWeight: 500,
                  fontSize: 20,
                  letterSpacing: "-0.005em",
                  lineHeight: 1.3,
                  margin: 0,
                }}
              >
                {step.title}
              </h3>
              <p
                style={{
                  color: TOKENS.inkMuted,
                  fontFamily: FONT_SANS,
                  fontSize: 15,
                  lineHeight: 1.55,
                  margin: 0,
                }}
              >
                {step.body}
              </p>
            </li>
          ))}
        </ol>
      </section>

      {/* Footer */}
      <footer
        style={{
          maxWidth: 1280,
          margin: "0 auto",
          padding: "32px 32px 64px",
          borderTop: `0.75px solid ${TOKENS.rule}`,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          gap: 24,
          flexWrap: "wrap",
        }}
      >
        <span
          style={{
            color: TOKENS.inkMuted,
            fontFamily: FONT_MONO,
            fontSize: 11,
            letterSpacing: "0.04em",
          }}
        >
          sidira · private alpha · 2026
        </span>
        <Link
          href="mailto:founders@sidira.ai"
          style={{
            color: TOKENS.inkMuted,
            fontFamily: FONT_MONO,
            fontSize: 11,
            letterSpacing: "0.04em",
            textDecoration: "none",
          }}
        >
          founders@sidira.ai
        </Link>
      </footer>
    </main>
  );
}
