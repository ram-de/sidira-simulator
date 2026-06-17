import Link from "next/link";
import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { isPublicSiteHost } from "@/lib/site-hosts";
import { APP_URL } from "@/components/PublicTopBar";
import PublicConsoleTopBar from "@/components/PublicConsoleTopBar";
import { ConsoleShell } from "@/components/v2";
import "@/styles/v2-theme.css";

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

// Dark "Reading Console" reskin of the public landing. Renders inside a
// `.v2-console` scope (ConsoleShell) so all `var(--console-*)` / `var(--text*)`
// tokens resolve from styles/v2-theme.css. Every <Link>/href/CTA target and
// every piece of copy is preserved byte-for-byte from the prior paper version —
// only markup structure + styles change.
function PublicCompanyHome() {
  return (
    <ConsoleShell>
      {/* Narrow-viewport collapse for the multi-column grids. */}
      <style>{`
        @media (max-width: 768px) {
          .sidira-public-section-head { grid-template-columns: 1fr !important; }
          .sidira-public-step-row { grid-template-columns: 1fr !important; gap: 8px !important; }
        }
      `}</style>

      {/* Top bar — shared with /about and /product */}
      <PublicConsoleTopBar />

      {/* Hero */}
      <section
        style={{
          maxWidth: 1240,
          margin: "0 auto",
          padding: "96px 24px 112px",
        }}
      >
        <p
          style={{
            color: "var(--text-mut)",
            fontFamily: "var(--v2-font-mono)",
            fontVariantNumeric: "tabular-nums",
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
              background: "var(--signal)",
              display: "inline-block",
            }}
          />
          Private alpha · 2026
        </p>
        {/* Marketing display — narrow grotesk weight, instrument voice at
            editorial scale on the dark Console. */}
        <h1
          style={{
            color: "var(--text-hi)",
            fontWeight: 700,
            fontSize: "clamp(2.7rem, 6vw, 5rem)",
            lineHeight: 1.0,
            letterSpacing: "-0.035em",
            margin: 0,
            maxWidth: "18ch",
            textWrap: "balance",
          }}
        >
          Validate product bets before you build.
        </h1>
        <p
          style={{
            color: "var(--text)",
            fontSize: "1.2rem",
            lineHeight: 1.55,
            margin: "32px 0 0",
            maxWidth: "60ch",
            fontWeight: 450,
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
            marginTop: 40,
            flexWrap: "wrap",
            alignItems: "center",
          }}
        >
          <Link
            href="mailto:founders@sidira.ai?subject=Sidira%20access"
            className="v2-btn v2-btn--primary v2-btn--hero"
            style={{ textDecoration: "none" }}
          >
            Request access
          </Link>
          <Link
            href={APP_URL}
            className="v2-btn v2-btn--secondary v2-btn--hero"
            style={{ textDecoration: "none" }}
          >
            Sign in
          </Link>
        </div>
      </section>

      {/* How it works — three steps separated by hairlines, no colored circles */}
      <section
        style={{
          maxWidth: 1240,
          margin: "0 auto",
          padding: "0 24px 112px",
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
              color: "var(--text-mut)",
              fontFamily: "var(--v2-font-mono)",
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
              color: "var(--text-hi)",
              fontWeight: 600,
              fontSize: "2.05rem",
              letterSpacing: "-0.028em",
              lineHeight: 1.1,
              margin: 0,
              maxWidth: "40ch",
              textWrap: "balance",
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
            borderTop: "1px solid var(--console-line-40)",
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
                borderBottom: "1px solid var(--console-line-40)",
                alignItems: "baseline",
              }}
            >
              <span
                style={{
                  color: "var(--text)",
                  fontFamily: "var(--v2-font-mono)",
                  fontVariantNumeric: "tabular-nums",
                  fontSize: 14,
                  fontWeight: 500,
                  letterSpacing: "0.04em",
                }}
              >
                {String(idx + 1).padStart(2, "0")} ·{" "}
                <span style={{ color: "var(--text-mut)" }}>step</span>
              </span>
              <h3
                style={{
                  color: "var(--text-hi)",
                  fontWeight: 550,
                  fontSize: 20,
                  letterSpacing: "-0.01em",
                  lineHeight: 1.3,
                  margin: 0,
                }}
              >
                {step.title}
              </h3>
              <p
                style={{
                  color: "var(--text-mut)",
                  fontSize: 15,
                  lineHeight: 1.6,
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
          maxWidth: 1240,
          margin: "0 auto",
          padding: "32px 24px 64px",
          borderTop: "1px solid var(--console-line-50)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          gap: 24,
          flexWrap: "wrap",
        }}
      >
        <span
          style={{
            color: "var(--text-mut)",
            fontFamily: "var(--v2-font-mono)",
            fontSize: 11,
            letterSpacing: "0.04em",
          }}
        >
          sidira · private alpha · 2026
        </span>
        <Link
          href="mailto:founders@sidira.ai"
          style={{
            color: "var(--text-mut)",
            fontFamily: "var(--v2-font-mono)",
            fontSize: 11,
            letterSpacing: "0.04em",
            textDecoration: "none",
          }}
        >
          founders@sidira.ai
        </Link>
      </footer>
    </ConsoleShell>
  );
}
