import Link from "next/link";
import { headers } from "next/headers";

import { isPublicSiteHost } from "@/lib/site-hosts";

const CARDS = [
  {
    href: "/personas",
    title: "Personas",
    body: "Connect your Snowflake, map your columns into Sidira's 7 feature groups, and build a versioned persona pack.",
    cta: "Build personas",
  },
  {
    href: "/product",
    title: "Product",
    body: "Connect your product sandbox. The weekly crawler captures how every capability works today — PRD + Figma per capability.",
    cta: "Connect product",
  },
  {
    href: "/simulations",
    title: "Simulations",
    body: "Submit a hypothesis. Watch the agents react. Then chat with each agent about why they reacted that way.",
    cta: "New simulation",
  },
];

export default function HomePage() {
  const host = headers().get("host");

  if (isPublicSiteHost(host)) {
    return <PublicCompanyHome />;
  }

  return <ProductHome />;
}

function ProductHome() {
  return (
    <main style={{ maxWidth: 960, margin: "64px auto", padding: "0 24px" }}>
      <h1 style={{ fontSize: 40, margin: 0 }}>Sidira</h1>
      <p style={{ color: "#555", marginTop: 8, marginBottom: 48 }}>
        Validate product hypotheses before you build them.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
        {CARDS.map((card) => (
          <Link
            key={card.href}
            href={card.href}
            style={{
              border: "1px solid #eee",
              borderRadius: 8,
              padding: 20,
              textDecoration: "none",
              color: "#111",
              display: "block",
            }}
          >
            <h3 style={{ marginTop: 0 }}>{card.title}</h3>
            <p style={{ color: "#555", fontSize: 14, lineHeight: 1.5 }}>{card.body}</p>
            <span style={{ color: "#111", fontWeight: 500 }}>{card.cta} →</span>
          </Link>
        ))}
      </div>
    </main>
  );
}

function PublicCompanyHome() {
  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#f7f5ef",
        color: "#171510",
      }}
    >
      <header
        style={{
          maxWidth: 1120,
          margin: "0 auto",
          padding: "28px 24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 16,
        }}
      >
        <Link
          href="/"
          style={{
            color: "#171510",
            fontSize: 20,
            fontWeight: 700,
            textDecoration: "none",
          }}
        >
          Sidira
        </Link>
        <nav style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <Link
            href="mailto:founders@sidira.ai?subject=Sidira%20access"
            style={{
              color: "#171510",
              fontSize: 14,
              fontWeight: 600,
              textDecoration: "none",
            }}
          >
            Request access
          </Link>
          <Link
            href="https://app.sidira.ai"
            style={{
              background: "#171510",
              borderRadius: 6,
              color: "#fff",
              fontSize: 14,
              fontWeight: 650,
              padding: "10px 14px",
              textDecoration: "none",
            }}
          >
            Sign in
          </Link>
        </nav>
      </header>

      <section
        style={{
          maxWidth: 1120,
          margin: "0 auto",
          padding: "76px 24px 92px",
          display: "grid",
          gridTemplateColumns: "minmax(0, 1.05fr) minmax(280px, 0.75fr)",
          gap: 48,
          alignItems: "center",
        }}
      >
        <div>
          <p
            style={{
              color: "#6a604f",
              fontSize: 14,
              fontWeight: 700,
              letterSpacing: 0,
              margin: "0 0 18px",
              textTransform: "uppercase",
            }}
          >
            Private alpha for product teams
          </p>
          <h1
            style={{
              fontSize: 64,
              lineHeight: 1,
              letterSpacing: 0,
              margin: 0,
              maxWidth: 760,
            }}
          >
            Validate product bets before you build.
          </h1>
          <p
            style={{
              color: "#4f493e",
              fontSize: 20,
              lineHeight: 1.55,
              margin: "28px 0 0",
              maxWidth: 660,
            }}
          >
            Sidira helps product teams pressure-test hypotheses against
            customer-grounded personas before roadmap bets turn into engineering
            commitments.
          </p>
          <div style={{ display: "flex", gap: 12, marginTop: 34, flexWrap: "wrap" }}>
            <Link
              href="mailto:founders@sidira.ai?subject=Sidira%20access"
              style={{
                background: "#171510",
                borderRadius: 6,
                color: "#fff",
                fontSize: 15,
                fontWeight: 700,
                padding: "13px 18px",
                textDecoration: "none",
              }}
            >
              Request access
            </Link>
            <Link
              href="https://app.sidira.ai"
              style={{
                border: "1px solid #cfc6b4",
                borderRadius: 6,
                color: "#171510",
                fontSize: 15,
                fontWeight: 700,
                padding: "12px 17px",
                textDecoration: "none",
              }}
            >
              Sign in
            </Link>
          </div>
        </div>

        <aside
          aria-label="Sidira workflow summary"
          style={{
            background: "#fffdf8",
            border: "1px solid #ded6c8",
            borderRadius: 8,
            boxShadow: "0 24px 60px rgba(58, 48, 32, 0.12)",
            padding: 28,
          }}
        >
          {[
            ["1", "Describe the bet", "Capture the proposed product change and the audience it should move."],
            ["2", "Run the simulation", "See where customer reactions cluster before the team commits build time."],
            ["3", "Refine with evidence", "Turn weak spots into sharper hypotheses for the next product review."],
          ].map(([step, title, body]) => (
            <div
              key={step}
              style={{
                borderBottom: step === "3" ? "none" : "1px solid #ebe4d7",
                display: "grid",
                gap: 14,
                gridTemplateColumns: "34px 1fr",
                padding: step === "1" ? "0 0 20px" : "20px 0",
              }}
            >
              <span
                style={{
                  alignItems: "center",
                  background: "#e9f0ed",
                  borderRadius: 6,
                  color: "#235142",
                  display: "flex",
                  fontSize: 14,
                  fontWeight: 800,
                  height: 34,
                  justifyContent: "center",
                  width: 34,
                }}
              >
                {step}
              </span>
              <span>
                <strong style={{ display: "block", fontSize: 17 }}>{title}</strong>
                <span style={{ color: "#5e574b", display: "block", fontSize: 14, lineHeight: 1.5, marginTop: 5 }}>
                  {body}
                </span>
              </span>
            </div>
          ))}
        </aside>
      </section>
    </main>
  );
}
