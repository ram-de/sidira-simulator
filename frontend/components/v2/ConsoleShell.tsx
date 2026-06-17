// ───────────────────────────────────────────────────────────────────────────
// DESIGN SYSTEM v2 — ConsoleShell + TopBar (§4.5).
// The shell applies the `.v2-console` scope (which carries all v2 tokens via
// v2-theme.css) and a constrained marketing wrap; the TopBar is the v2 nav.
// ───────────────────────────────────────────────────────────────────────────
"use client";

import {
  useEffect,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import { ProvenanceMarker, type ProvenanceMarkerProps } from "./Provenance";
import { ConsoleMarkMono } from "./Marks";

// The page MUST import v2-theme.css so .v2-console resolves its tokens.
// On mount we add `.v2-js` to the root: that marker gates the ScrollReveal
// hidden start-state (styles/v2-theme.css), so with JS disabled all revealed
// content stays fully visible (progressive enhancement, §5.3).
export function ConsoleShell({
  children,
  style,
}: {
  children: ReactNode;
  style?: CSSProperties;
}) {
  const [js, setJs] = useState(false);
  useEffect(() => {
    setJs(true);
  }, []);
  return (
    <main
      className={js ? "v2-console v2-js" : "v2-console"}
      style={{ minHeight: "100vh", ...style }}
    >
      {children}
    </main>
  );
}

// ── Sheet shell (§1.7, §6.4) — the LIGHT counterpart to ConsoleShell. ───────
// Applies the `.v2-sheet` scope (paper tokens + blueprint grain in v2-theme.css)
// and the same `.v2-js` mount marker that gates ScrollReveal's hidden start
// state (so with JS off, all revealed content stays visible). A Sheet page is a
// RECORD: still, ink-on-paper, serif prose. A §6.4 Console well embedded inside
// stays dark by re-asserting `.v2-console` locally — the route never inverts.
export function SheetShell({
  children,
  style,
}: {
  children: ReactNode;
  style?: CSSProperties;
}) {
  const [js, setJs] = useState(false);
  useEffect(() => {
    setJs(true);
  }, []);
  return (
    <main
      className={js ? "v2-sheet v2-js" : "v2-sheet"}
      style={{ minHeight: "100vh", ...style }}
    >
      {children}
    </main>
  );
}

// Marketing wrap — 1240px max, 24px gutter (§3.3).
export function Wrap({
  children,
  style,
}: {
  children: ReactNode;
  style?: CSSProperties;
}) {
  return (
    <div
      style={{
        maxWidth: 1240,
        margin: "0 auto",
        padding: "0 24px",
        ...style,
      }}
    >
      {children}
    </div>
  );
}

export type NavItem = { label: string; href: string; active?: boolean };

// Top bar (§4.5): wordmark + route nav left; a SINGLE global provenance
// reference + a sign-in action right. The resting wordmark is ink, never
// signal (P1). The global marker dot rests (ink) unless a run is live.
export function TopBar({
  nav,
  provenance,
  action,
}: {
  nav: NavItem[];
  provenance?: ProvenanceMarkerProps;
  action?: ReactNode;
}) {
  return (
    <header
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        height: 52,
        background: "rgba(16,25,42,.86)",
        backdropFilter: "blur(14px) saturate(140%)",
        WebkitBackdropFilter: "blur(14px) saturate(140%)",
        borderBottom: "1px solid var(--console-line-50)",
      }}
    >
      <Wrap
        style={{ height: "100%", display: "flex", alignItems: "center", gap: 22 }}
      >
        <a
          href="/"
          aria-label="Sidira home"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 9,
            fontWeight: 600,
            letterSpacing: "0.06em",
            color: "var(--text-hi)",
            fontSize: 15,
          }}
        >
          <ConsoleMarkMono size={26} />
          SIDIRA
        </a>
        <nav style={{ display: "flex", gap: 2, marginLeft: 8 }}>
          {nav.map((item) => (
            <a
              key={item.label}
              href={item.href}
              style={{
                position: "relative",
                fontSize: 13.5,
                color: item.active ? "var(--text-hi)" : "var(--text-mut)",
                padding: "7px 12px",
                borderRadius: "var(--r-well)",
                transition: "color .14s var(--ease-out)",
              }}
            >
              {item.label}
              {item.active ? (
                <span
                  aria-hidden
                  style={{
                    position: "absolute",
                    left: 12,
                    right: 12,
                    bottom: -1,
                    height: 2,
                    /* active nav is neutral ink, never signal — the saturated
                       accent is reserved for LIVE READING ONLY (§1.3, P2) */
                    background: "var(--text-hi)",
                    borderRadius: 2,
                  }}
                />
              ) : null}
            </a>
          ))}
        </nav>
        <div
          style={{
            marginLeft: "auto",
            display: "flex",
            alignItems: "center",
            gap: 14,
          }}
        >
          {provenance ? <ProvenanceMarker {...provenance} /> : null}
          {action}
        </div>
      </Wrap>
    </header>
  );
}
