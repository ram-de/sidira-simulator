// ───────────────────────────────────────────────────────────────────────────
// DESIGN SYSTEM v2 — Section + SectionHead + ScrollReveal (§2.2, §3, §5.3).
// Marketing section scaffolding: one eyebrow designator (no 01/02 numerals,
// §2.3), an h2, and an optional sub. ScrollReveal settles content in once.
// ───────────────────────────────────────────────────────────────────────────
"use client";

import { useEffect, useRef, type CSSProperties, type ReactNode } from "react";

// Reveal-once on scroll. Settles in via the .v2-reveal/.in classes (§5.3);
// reduced-motion / no-IO falls back to immediately visible. Renders a <div>
// (every section wrapper on the marketing pages is a block container).
export function ScrollReveal({
  children,
  className,
  style,
}: {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const reduce =
      typeof window !== "undefined" &&
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce || !("IntersectionObserver" in window)) {
      el.classList.add("in");
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((en) => {
          if (en.isIntersecting) {
            en.target.classList.add("in");
            io.unobserve(en.target);
          }
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.08 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <div
      ref={ref}
      className={["v2-reveal", className].filter(Boolean).join(" ")}
      style={style}
    >
      {children}
    </div>
  );
}

// A top-level marketing region. 96px vertical rhythm + a hairline divider (§3).
export function Section({
  children,
  divider = true,
  style,
}: {
  children: ReactNode;
  divider?: boolean;
  style?: CSSProperties;
}) {
  return (
    <section
      style={{
        padding: "96px 0",
        borderBottom: divider ? "1px solid var(--console-line-40)" : undefined,
        ...style,
      }}
    >
      {children}
    </section>
  );
}

// Section head — one eyebrow designator + h2 + optional sub (§2).
export function SectionHead({
  eyebrow,
  title,
  sub,
}: {
  eyebrow: ReactNode;
  title: ReactNode;
  sub?: ReactNode;
}) {
  return (
    <ScrollReveal style={{ marginBottom: 56, maxWidth: 720 }}>
      <div style={{ marginBottom: 18 }}>
        <span className="v2-desig">{eyebrow}</span>
      </div>
      <h2
        style={{
          fontSize: "2.05rem",
          lineHeight: 1.1,
          letterSpacing: "-0.028em",
          fontWeight: 600,
          color: "var(--text-hi)",
          textWrap: "balance",
        }}
      >
        {title}
      </h2>
      {sub ? (
        <p
          style={{
            marginTop: 18,
            fontSize: "1.075rem",
            lineHeight: 1.62,
            color: "var(--text-mut)",
            maxWidth: "60ch",
          }}
        >
          {sub}
        </p>
      ) : null}
    </ScrollReveal>
  );
}
