import type { Metadata } from "next";
import Link from "next/link";

import PublicConsoleTopBar from "@/components/PublicConsoleTopBar";
import { ConsoleShell } from "@/components/v2";
import "@/styles/v2-theme.css";

// Dark "Reading Console" reskin of the public /about page. Renders inside a
// `.v2-console` scope so all `var(--console-*)` / `var(--text*)` tokens resolve
// from styles/v2-theme.css. The duo aperture mark in the top bar is sanctioned
// here: /about is a brand-mode surface (DESIGN.md §1.3).
//
// Content is grounded, not invented: every claim traces to repo material
// (README, ROADMAP, the accuracy report, the twin-council white paper). No
// metrics, customers, testimonials, team bios, or features that don't exist; no
// "predicts winners" overclaim (counter-intuitive A/B direction is at chance
// today — honesty is the brand). The name-origin story is kept off buyer-facing
// surfaces by design (DESIGN.md intro).
export const metadata: Metadata = {
  title: "About — Sidira",
  description:
    "Sidira is AI audience simulation that pre-screens which A/B-test ideas are worth running — upstream of A/B testing, validated honestly.",
};

const SECTION: React.CSSProperties = { marginTop: 56 };

const H2: React.CSSProperties = {
  fontSize: 22,
  fontWeight: 600,
  letterSpacing: "-0.02em",
  lineHeight: 1.15,
  color: "var(--text-hi)",
  margin: "0 0 16px 0",
};

const BODY: React.CSSProperties = {
  fontSize: 16,
  lineHeight: 1.7,
  color: "var(--text)",
  margin: "0 0 16px 0",
};

const STRONG: React.CSSProperties = { fontWeight: 600, color: "var(--text-hi)" };

function Term({ children }: { children: React.ReactNode }) {
  return <span style={STRONG}>{children}</span>;
}

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
          Screen the bet before you spend the traffic.
        </h1>

        <p
          style={{
            fontSize: "1.2rem",
            lineHeight: 1.62,
            color: "var(--text)",
            margin: 0,
            maxWidth: "60ch",
          }}
        >
          Product teams aren&rsquo;t short on hypotheses. They&rsquo;re short on a
          fast, honest way to decide which ones are worth a live test. Sidira is
          AI audience simulation that pre-screens that backlog &mdash; a step{" "}
          <Term>upstream</Term> of A/B testing, not a replacement for it.
        </p>

        <section style={SECTION}>
          <h2 style={H2}>What Sidira does</h2>
          <p style={BODY}>
            A team describes a proposed product change and the audience it should
            move. Sidira simulates how a panel of customer-grounded agents would
            react, and returns a <Term>directional read</Term> plus the weaknesses
            the cohort surfaces &mdash; before the change becomes an engineering
            commitment. No production traffic, no shipping to learn.
          </p>
          <p style={BODY}>
            After every run the agents that participated are{" "}
            <Term>conversable</Term>. A PM can ask a segment why it didn&rsquo;t
            engage &mdash; like interviewing the users who ran in your A/B test
            &mdash; and turn weak spots into a sharper hypothesis for the next
            review.
          </p>
        </section>

        <section style={SECTION}>
          <h2 style={H2}>The honest claim</h2>
          <p style={BODY}>
            The live randomized experiment stays the ground truth. Sidira&rsquo;s
            job is to help you <Term>prioritize what to test</Term>, not to declare
            winners. It is a directional hypothesis generator and weakness
            surfacer &mdash; not a calibrated predictor, and not a digital-twin
            oracle. A chat with an agent is a hypothesis aid, never evidence.
          </p>
          <p style={BODY}>
            We are explicit about the limits. Calibrated probabilities are on the
            roadmap, claimed only when a backtest on real experiments earns them.
            Where the engine shows directional promise, it does not yet generalize
            to subtle, cosmetic, or counter-intuitive changes &mdash; and we say so
            rather than smooth it over.
          </p>
        </section>

        <section style={SECTION}>
          <h2 style={H2}>How we measure ourselves</h2>
          <p style={BODY}>
            A vendor you should trust is one that shows you its measurement,
            including where it falls short. We pre-register every prediction and
            fingerprint it before we look at the result, grade against real
            randomized experiments, run independent adversarial leak audits, demand
            replication on fresh data, and report the nulls &mdash; including the
            ones that caught our own false positives before they could become
            claims.
          </p>
          <p style={BODY}>
            Signed-in customers can read the full accuracy &amp; methodology report:
            how we measure, what the benchmarks show today, and where the honest
            limits are. When we can prove more, we publish it the same way &mdash;
            pre-registered, exactly as the numbers come back.{" "}
            <Link
              href="mailto:founders@sidira.ai?subject=Sidira%20accuracy%20report"
              style={{ color: "var(--text-hi)", textDecoration: "underline" }}
            >
              Ask for access
            </Link>
            .
          </p>
        </section>

        <section style={SECTION}>
          <h2 style={H2}>Who&rsquo;s building it</h2>
          <p style={BODY}>
            Sidira is founder-built and in private alpha. Questions, or want to
            put your A/B history to work as a design partner?{" "}
            <Link
              href="mailto:founders@sidira.ai?subject=Sidira"
              style={{ color: "var(--text-hi)", textDecoration: "underline" }}
            >
              founders@sidira.ai
            </Link>
            .
          </p>
        </section>
      </article>
    </ConsoleShell>
  );
}
