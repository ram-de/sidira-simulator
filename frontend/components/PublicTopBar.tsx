import Link from "next/link";
import SidiraLockupDuo from "@/components/SidiraLockupDuo";
import { TOKENS, FONT_SANS, FONT_NARROW } from "@/lib/design";

// Where "Sign in" lands. In dev the app host doesn't exist, so go straight
// to the register on the local server.
export const APP_URL =
  process.env.NODE_ENV === "development"
    ? "http://127.0.0.1:3000/simulations"
    : "https://app.sidira.ai";

// Public-surface top bar (home, about). The duo lockup is sanctioned here —
// public site and about use the standard dual-color mark (DESIGN.md §1.3) — and it
// links home so every public page has a way back.
export default function PublicTopBar({
  currentPath,
}: {
  currentPath?: "/about";
}) {
  return (
    <header
      style={{
        maxWidth: 1280,
        margin: "0 auto",
        padding: "24px 32px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 24,
        flexWrap: "wrap",
        borderBottom: `0.75px solid ${TOKENS.rule}`,
      }}
    >
      <Link
        href="/"
        aria-label="Sidira home"
        style={{ color: TOKENS.ink, textDecoration: "none", display: "inline-block" }}
      >
        <SidiraLockupDuo height={36} />
      </Link>
      <nav style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
        <Link
          href="/about"
          aria-current={currentPath === "/about" ? "page" : undefined}
          style={{
            color: currentPath === "/about" ? TOKENS.ink : TOKENS.inkMuted,
            fontFamily: FONT_SANS,
            fontSize: 16,
            fontWeight: 500,
            textDecoration: "none",
            padding: "8px 4px",
          }}
        >
          About
        </Link>
        <Link
          href="mailto:founders@sidira.ai?subject=Sidira%20access"
          style={{
            color: TOKENS.inkMuted,
            fontFamily: FONT_SANS,
            fontSize: 16,
            fontWeight: 500,
            textDecoration: "none",
            padding: "8px 4px",
          }}
        >
          Request access
        </Link>
        <Link
          href={APP_URL}
          style={{
            background: TOKENS.ink,
            border: `0.75px solid ${TOKENS.ink}`,
            borderRadius: 4,
            color: TOKENS.paper,
            fontFamily: FONT_NARROW,
            fontSize: 12,
            fontWeight: 600,
            letterSpacing: "0.08em",
            padding: "10px 16px",
            textDecoration: "none",
            textTransform: "uppercase",
          }}
        >
          Sign in
        </Link>
      </nav>
    </header>
  );
}
