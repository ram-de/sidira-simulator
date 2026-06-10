"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import AuthControls from "@/components/AuthControls";
import SidiraLockup from "@/components/SidiraLockup";
import { TOKENS, FONT_SANS, EASE_MECH } from "@/lib/design";

// Workbench chrome — DESIGN.md §9.3 + R2 mock (product-mock-mvp.html).
// MVP nav is Hypotheses · Library only; Objectives / Rollouts / Calibration
// and the CAL readout are future-only surfaces and must not appear (R2.4 —
// the nav never promises what the product can't do yet). Labels rename, the
// routes underneath do not.
const TABS = [
  { href: "/simulations", label: "Hypotheses", matches: ["/simulations", "/agents"] },
  { href: "/personas", label: "Library", matches: ["/personas"] },
] as const;

export default function TopNav() {
  const pathname = usePathname() ?? "/";
  const [hovered, setHovered] = useState<string | null>(null);

  return (
    <header
      style={{
        height: 56,
        display: "flex",
        alignItems: "center",
        gap: 32,
        padding: "0 24px",
        borderBottom: `1px solid ${TOKENS.rule}`,
        background: TOKENS.paper,
      }}
    >
      <Link
        href="/"
        aria-label="Sidira home"
        style={{ color: TOKENS.ink, textDecoration: "none", display: "inline-flex", alignItems: "center" }}
      >
        <SidiraLockup height={28} />
      </Link>
      <nav style={{ display: "flex", gap: 24, flex: 1, alignSelf: "stretch", alignItems: "stretch" }}>
        {TABS.map((tab) => {
          const active = tab.matches.some(
            (m) => pathname === m || pathname.startsWith(m + "/"),
          );
          const hot = active || hovered === tab.href;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              aria-current={active ? "page" : undefined}
              onMouseEnter={() => setHovered(tab.href)}
              onMouseLeave={() => setHovered(null)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                textDecoration: "none",
                color: hot ? TOKENS.ink : TOKENS.inkMuted,
                fontFamily: FONT_SANS,
                fontSize: 13,
                fontWeight: 500,
                borderBottom: `2px solid ${active ? TOKENS.ink : "transparent"}`,
                // §9.3: hover 80ms ease-out, tab underline 160ms mech curve.
                transition: `color 80ms ease-out, border-bottom-color 160ms ${EASE_MECH}`,
              }}
            >
              {tab.label}
            </Link>
          );
        })}
      </nav>
      <AuthControls />
    </header>
  );
}
