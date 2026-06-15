// Library furniture — the shared card/record primitives for the Library IA
// (#207). Extracted from app/personas/page.tsx so the landing and the
// feature-pack browse page render the SAME components instead of each
// redefining them inline (the project's shared-primitives rule). Everything
// here is a record on paper — no glass, no live readings (DESIGN.md §4.2,
// §7.6, §10). Components style themselves from the design tokens; callers
// never pass raw hex.

import Link from "next/link";
import { Fragment } from "react";
import { TOKENS, FONT_MONO, TNUM } from "@/lib/design";

// Hover + §9.5 live carrier. The carrier is the single sanctioned pulse;
// reduced motion renders the static frame. Render <LibraryStyles /> once per
// page that uses these primitives so `.lib-card` / `.lib-link` resolve.
export function LibraryStyles() {
  return (
    <style
      dangerouslySetInnerHTML={{
        __html: `
          .lib-card { transition: border-color 80ms ease-out; }
          .lib-card:hover { border-color: ${TOKENS.inkMuted}; }
          .lib-link { color: ${TOKENS.ink}; text-decoration: none; border-bottom: 1px dotted ${TOKENS.inkMuted}; transition: border-color 80ms ease-out; }
          .lib-link:hover { border-bottom-color: ${TOKENS.ink}; }
          .lib-carrier { position: relative; }
          .lib-carrier::after { content: ""; position: absolute; left: 0; right: 0; bottom: -3px; height: 2px; background: ${TOKENS.signal}; animation: lib-carrier 3.4s ease-in-out infinite; }
          @keyframes lib-carrier { 0%, 100% { opacity: 0.45; } 50% { opacity: 1; } }
          @media (prefers-reduced-motion: reduce) { .lib-carrier::after { animation: none; } }
        `,
      }}
    />
  );
}

export function isoDate(iso: string): string {
  const t = new Date(iso);
  return Number.isNaN(t.getTime()) ? iso : t.toISOString().slice(0, 10);
}

export function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section style={{ marginBottom: 32 }}>
      <span
        style={{
          display: "block",
          fontSize: 11,
          fontWeight: 500,
          letterSpacing: "0.16em",
          textTransform: "uppercase",
          color: TOKENS.inkMuted,
          paddingBottom: 10,
          borderBottom: `1px solid ${TOKENS.rule}`,
        }}
      >
        {label}
      </span>
      {children}
    </section>
  );
}

export function CardGrid({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(290px, 1fr))",
        gap: 16,
        marginTop: 14,
      }}
    >
      {children}
    </div>
  );
}

export function Card({ ghost = false, children }: { ghost?: boolean; children: React.ReactNode }) {
  return (
    <article
      className="lib-card"
      style={{
        background: ghost ? TOKENS.paper : TOKENS.paperElevated,
        border: `1px ${ghost ? "dashed" : "solid"} ${TOKENS.rule}`,
        borderRadius: 4,
        // §4.2 elevated top highlight, token-derived (paper-elevated, no raw hex).
        boxShadow: ghost ? "none" : `inset 0 1px 0 ${TOKENS.paperElevated}`,
        padding: 16,
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
      }}
    >
      {children}
    </article>
  );
}

export function CardHead({ name, children }: { name: string; children?: React.ReactNode }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "baseline",
        gap: 10,
        marginBottom: 10,
        width: "100%",
      }}
    >
      <span style={{ fontSize: 15, fontWeight: 600, flex: 1, minWidth: 0 }}>{name}</span>
      {children}
    </div>
  );
}

export function Rows({ rows }: { rows: [string, React.ReactNode][] }) {
  return (
    <dl
      style={{
        margin: 0,
        display: "grid",
        gridTemplateColumns: "auto 1fr",
        gap: "3px 14px",
        width: "100%",
      }}
    >
      {rows.map(([dt, dd]) => (
        <Fragment key={dt}>
          <dt
            style={{
              fontSize: 10,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: TOKENS.inkMuted,
              paddingTop: 2,
            }}
          >
            {dt}
          </dt>
          <dd style={{ margin: 0, fontFamily: FONT_MONO, fontSize: 11.5, ...TNUM }}>{dd}</dd>
        </Fragment>
      ))}
    </dl>
  );
}

export function Chip({ strong = false, children }: { strong?: boolean; children: React.ReactNode }) {
  // Designators carry ink weight, never color (§4.3).
  return (
    <span
      style={{
        fontFamily: FONT_MONO,
        fontSize: 10.5,
        letterSpacing: "0.06em",
        border: `1px solid ${strong ? TOKENS.ink : TOKENS.rule}`,
        color: strong ? TOKENS.ink : TOKENS.inkMuted,
        borderRadius: 2,
        padding: "2px 7px",
        whiteSpace: "nowrap",
        ...TNUM,
      }}
    >
      {children}
    </span>
  );
}

// Sentence-case helper copy inside a card — body font, never mono caps (§5.4).
export function CardNote({ children }: { children: React.ReactNode }) {
  return (
    <p style={{ margin: "10px 0 0", fontSize: 12, lineHeight: 1.5, color: TOKENS.inkMuted }}>
      {children}
    </p>
  );
}

export function CardLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="lib-link"
      style={{ display: "inline-block", marginTop: 12, fontSize: 12.5, fontWeight: 500 }}
    >
      {children}
    </Link>
  );
}

export function BodyNote({ children }: { children: React.ReactNode }) {
  return (
    <p style={{ margin: "12px 0 0", fontSize: 13, lineHeight: 1.5, color: TOKENS.inkMuted }}>
      {children}
    </p>
  );
}

// A designed empty-state — §7.7 note anatomy (paper-recessed surface) carrying
// the next action. Empty is not an error: it takes the neutral `rule` border,
// never `alert`/`warn` (§4.3, color never carries state alone), and reads in
// sentence-case body font (§5.4).
export function EmptyState({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        marginTop: 12,
        padding: 16,
        border: `1px solid ${TOKENS.rule}`,
        borderRadius: 4,
        background: TOKENS.paperRecessed,
        color: TOKENS.ink,
        fontSize: 13,
        lineHeight: 1.5,
      }}
    >
      {children}
    </div>
  );
}

export function PendingNote({ children }: { children: React.ReactNode }) {
  // §8.6 — pending states are honest text, never skeletons or spinners.
  return (
    <p style={{ margin: "12px 0 0", fontSize: 13, color: TOKENS.inkMuted }}>{children}</p>
  );
}

export function ErrorNote({ children }: { children: React.ReactNode }) {
  // §7.7 note anatomy — the alert border carries severity; the message
  // reads in ink (§4.3).
  return (
    <div
      role="alert"
      style={{
        marginTop: 12,
        padding: 12,
        border: `0.75px solid ${TOKENS.alert}`,
        borderRadius: 2,
        background: TOKENS.paperRecessed,
        color: TOKENS.ink,
        fontSize: 13,
      }}
    >
      {children}
    </div>
  );
}
