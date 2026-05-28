import Link from "next/link";

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
