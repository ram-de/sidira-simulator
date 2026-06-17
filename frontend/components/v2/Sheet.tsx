// ───────────────────────────────────────────────────────────────────────────
// DESIGN SYSTEM v2 — SHEET primitives (§1.7, §6.4, §7.4).
// The light RECORD-mode counterpart to the Console components. Sheet pages
// (About, capability/PRD detail, persona-pack record, changelog) compose from
// these; they consume the `.v2-sheet`-scoped tokens/classes in v2-theme.css and
// never re-inline a raw hex. Console wells embedded here (§6.4) re-assert the
// dark scope locally without inverting the route.
// ───────────────────────────────────────────────────────────────────────────
"use client";

import type { CSSProperties, ReactNode } from "react";

// ── Sheet top bar (§4.5, Sheet) — light counterpart to Console TopBar. ──────
// Wordmark + route nav left; quiet + primary actions right. Sticky, paper blur.
export type SheetNavItem = { label: string; href: string; active?: boolean };

export function SheetTopBar({
  nav,
  actions,
}: {
  nav: SheetNavItem[];
  actions?: ReactNode;
}) {
  return (
    <header
      className="v2-sheet-topbar"
      style={{
        position: "sticky",
        top: 0,
        zIndex: 40,
        background: "var(--sheet-topbar-bg)",
        backdropFilter: "saturate(1.2) blur(8px)",
        WebkitBackdropFilter: "saturate(1.2) blur(8px)",
        borderBottom: "0.75px solid var(--sheet-topbar-border)",
      }}
    >
      <div className="v2-sheet-topbar-inner">
        <a
          href="/"
          aria-label="Sidira home"
          style={{ display: "flex", alignItems: "center", gap: 11 }}
        >
          <SheetMark />
          <span
            style={{
              fontWeight: 600,
              fontSize: 16,
              letterSpacing: "0.06em",
              color: "var(--sheet-ink)",
              textTransform: "uppercase",
            }}
          >
            SIDIRA
          </span>
        </a>
        <nav className="v2-sheet-nav">
          {nav.map((item) => (
            <a
              key={item.label}
              href={item.href}
              aria-current={item.active ? "page" : undefined}
              className="v2-sheet-nav-link"
              style={{
                fontSize: 14,
                fontWeight: 500,
                color: item.active ? "var(--sheet-ink)" : "var(--sheet-mut)",
                padding: "7px 11px",
                borderRadius: "var(--r-well)",
              }}
            >
              {item.label}
            </a>
          ))}
          {actions}
        </nav>
      </div>
    </header>
  );
}

// The Sheet aperture mark — single-tone ink iris (NOT the dual-tone founder
// variant, which is reserved for brand-mode surfaces only).
function SheetMark() {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden
      style={{ width: 25, height: 25, display: "block" }}
    >
      <circle cx="16" cy="16" r="14.5" stroke="var(--sheet-line)" strokeWidth="1" />
      <circle cx="16" cy="16" r="9" stroke="var(--sheet-mut)" strokeWidth="1.3" />
      <circle
        cx="16"
        cy="16"
        r="9"
        stroke="var(--sheet-ink)"
        strokeWidth="1.4"
        strokeDasharray="14 42.5"
        strokeDashoffset="-8"
        strokeLinecap="round"
      />
      <circle cx="16" cy="16" r="2.4" fill="var(--sheet-ink)" />
    </svg>
  );
}

// ── Record grid (§3 reading layout) — Provenance Spine + single measure ─────
// 180px binder margin + 1fr document column. Responsive collapse handled by the
// `.v2-record` page CSS the consuming page ships (mirrors page-one's pattern).
export function RecordGrid({
  spine,
  children,
  className,
  style,
}: {
  spine: ReactNode;
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <div
      className={["v2-record", className].filter(Boolean).join(" ")}
      style={{
        maxWidth: 1180,
        margin: "0 auto",
        padding: "0 32px",
        display: "grid",
        gridTemplateColumns: "180px 1fr",
        alignItems: "start",
        ...style,
      }}
    >
      {spine}
      {children}
    </div>
  );
}

// ── §7.4 THE PROVENANCE SPINE — provenance as architecture (Sheet). ─────────
// A permanent left binder-margin: stacked record facts (recorded → print bare)
// + the calibration state (only the ◇ glyph wears spread; the WORD stays muted,
// P7). Always present, quiet, never dismissible. Renders as a sticky <aside>.
export type SpineFact = { k: ReactNode; v: ReactNode };

export function ProvenanceSpine({
  heading = "Record",
  facts,
  calibrated = false,
  showKey = true,
  className,
}: {
  heading?: ReactNode;
  facts: SpineFact[];
  calibrated?: boolean;
  showKey?: boolean;
  className?: string;
}) {
  return (
    <aside
      aria-label="Provenance"
      className={["v2-spine", className].filter(Boolean).join(" ")}
      style={{
        position: "relative",
        borderRight: "0.75px solid var(--sheet-line)",
        padding: "128px 28px 96px 0",
      }}
    >
      <div className="v2-spine-sticky" style={{ position: "sticky", top: 96 }}>
        {/* Non-heading element: the spine label must not inject an <h4> ahead
            of the page <h1> (a11y heading order). The aside already carries an
            aria-label, so this reads as a styled caption, not a document heading. */}
        <div
          style={{
            fontFamily: "var(--v2-font-mono)",
            fontSize: 10,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            color: "var(--sheet-mut)",
            marginBottom: 20,
          }}
        >
          {heading}
        </div>
        <div className="v2-spine-grid">
          {facts.map((f, i) => (
            <SpineItem key={i} k={f.k}>
              {f.v}
            </SpineItem>
          ))}
        </div>
        <div
          className="v2-spine-rule"
          style={{ height: "0.75px", background: "var(--sheet-line)", margin: "22px 0" }}
        />
        <div className="v2-spine-tail">
          <SpineItem k="Calibration">
            <span style={{ color: "var(--sheet-mut)" }}>
              <span className="v2-gh" style={{ marginRight: 5 }}>
                {calibrated ? "◆" : "◇"}
              </span>
              {calibrated ? "graded" : "uncalibrated"}
            </span>
          </SpineItem>
          {showKey ? (
            <div className="v2-spine-item" style={{ marginTop: 14 }}>
              <span
                style={{
                  fontFamily: "var(--v2-font-mono)",
                  fontSize: 11,
                  color: "var(--sheet-mut)",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 5,
                  lineHeight: 1.6,
                }}
              >
                <span className="v2-gf">◆</span>graded&nbsp;·&nbsp;
                <span className="v2-gh">◇</span>estimate
              </span>
            </div>
          ) : null}
        </div>
      </div>
    </aside>
  );
}

function SpineItem({ k, children }: { k: ReactNode; children: ReactNode }) {
  return (
    <div className="v2-spine-item" style={{ marginBottom: 15 }}>
      <span
        style={{
          fontFamily: "var(--v2-font-mono)",
          fontSize: 9.5,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: "var(--sheet-mut)",
          display: "block",
          marginBottom: 3,
        }}
      >
        {k}
      </span>
      <span
        style={{
          fontFamily: "var(--v2-font-mono)",
          fontSize: 12.5,
          color: "var(--sheet-ink)",
          letterSpacing: "0.01em",
        }}
      >
        {children}
      </span>
    </div>
  );
}

// ── Newsreader prose (§2) — the one sanctioned serif body, max 68ch. ────────
// `lead` enables the printed-record drop-cap on the opening paragraph.
export function Prose({
  lead = false,
  children,
  className,
  style,
}: {
  lead?: boolean;
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <div
      className={["v2-prose", lead && "v2-prose--lead", className]
        .filter(Boolean)
        .join(" ")}
      style={style}
    >
      {children}
    </div>
  );
}

// ── Sheet section + kicker (§3 chapter rhythm) — airy 96px between. ─────────
export function SheetKicker({ children }: { children: ReactNode }) {
  return <div className="v2-kicker">{children}</div>;
}

export function SheetSection({
  kicker,
  title,
  intro,
  children,
  style,
}: {
  kicker?: ReactNode;
  title?: ReactNode;
  intro?: ReactNode;
  children: ReactNode;
  style?: CSSProperties;
}) {
  return (
    <section style={{ marginTop: 96, ...style }}>
      {kicker ? <SheetKicker>{kicker}</SheetKicker> : null}
      {title ? (
        <h2
          style={{
            fontWeight: 600,
            fontSize: "1.5rem",
            lineHeight: 1.12,
            letterSpacing: "-0.02em",
            color: "var(--sheet-ink)",
            marginTop: kicker ? 14 : 0,
            marginBottom: 24,
            textWrap: "balance",
            maxWidth: "24ch",
          }}
        >
          {title}
        </h2>
      ) : null}
      {intro ? (
        <p
          style={{
            fontFamily: "var(--v2-font-serif)",
            fontSize: "1.0625rem",
            lineHeight: 1.65,
            color: "var(--sheet-ink)",
            maxWidth: "64ch",
            marginBottom: 32,
          }}
        >
          {intro}
        </p>
      ) : null}
      {children}
    </section>
  );
}
