import Link from "next/link";
import type { ReactNode } from "react";

import { FONT_MONO, FONT_NARROW, TOKENS } from "@/lib/design";

export function PolicySection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section style={{ marginTop: 32 }}>
      <h2
        style={{
          fontSize: 22,
          fontWeight: 600,
          lineHeight: 1.35,
          letterSpacing: "-0.02em",
          margin: "0 0 12px",
        }}
      >
        {title}
      </h2>
      {children}
    </section>
  );
}

export function PolicyParagraph({ children }: { children: ReactNode }) {
  return <p style={{ margin: "0 0 16px" }}>{children}</p>;
}

export function PolicyDocument({
  title,
  current,
  children,
}: {
  title: string;
  current: "privacy" | "terms";
  children: ReactNode;
}) {
  return (
    <main
      style={{
        maxWidth: 760,
        margin: "0 auto",
        padding: "48px 24px 80px",
        color: TOKENS.ink,
        lineHeight: 1.7,
        overflowWrap: "anywhere",
      }}
    >
      <nav
        aria-label="Monsi policies"
        style={{ display: "flex", flexWrap: "wrap", gap: "8px 24px", fontSize: 15 }}
      >
        <Link href="https://sidira.ai" style={{ color: TOKENS.ink }}>Sidira</Link>
        <Link
          href="/monsi/privacy"
          aria-current={current === "privacy" ? "page" : undefined}
          style={{ color: TOKENS.ink }}
        >
          Privacy
        </Link>
        <Link
          href="/monsi/terms"
          aria-current={current === "terms" ? "page" : undefined}
          style={{ color: TOKENS.ink }}
        >
          SMS terms
        </Link>
      </nav>

      <article>
        <header style={{ marginTop: 48, paddingBottom: 24, borderBottom: `1px solid ${TOKENS.rule}` }}>
          <p style={{ fontFamily: FONT_MONO, fontSize: 12, color: TOKENS.inkMuted, margin: "0 0 12px" }}>
            MONSI · PRIVATE SMS PILOT
          </p>
          <h1
            style={{
              fontFamily: FONT_NARROW,
              fontSize: "clamp(2.3rem, 6vw, 3.25rem)",
              fontWeight: 600,
              lineHeight: 1.1,
              letterSpacing: "-0.025em",
              margin: "0 0 16px",
            }}
          >
            {title}
          </h1>
          <p style={{ color: TOKENS.inkMuted, fontSize: 15, margin: 0 }}>
            Effective <time dateTime="2026-09-29">September 29, 2026</time>
          </p>
        </header>
        {children}
      </article>

      <footer style={{ marginTop: 48, paddingTop: 24, borderTop: `1px solid ${TOKENS.rule}`, fontSize: 14 }}>
        <p style={{ color: TOKENS.inkMuted, margin: "0 0 8px" }}>Monsi · Private SMS proof of concept</p>
        <a href="mailto:founders@sidira.ai" style={{ color: TOKENS.ink }}>founders@sidira.ai</a>
      </footer>
    </main>
  );
}
