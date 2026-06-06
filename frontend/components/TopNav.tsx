"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import SidiraLockup from "@/components/SidiraLockup";
import { TOKENS, FONT_SANS } from "@/lib/design";

const TABS = [
  { href: "/personas", label: "Personas" },
  { href: "/product", label: "Product" },
  { href: "/simulations", label: "Simulations" },
] as const;

export default function TopNav() {
  const pathname = usePathname() ?? "/";

  return (
    <header
      style={{
        borderBottom: `0.75px solid ${TOKENS.rule}`,
        background: TOKENS.paperElevated,
        padding: "12px 24px",
        display: "flex",
        alignItems: "center",
        gap: 24,
      }}
    >
      <Link
        href="/"
        aria-label="Sidira home"
        style={{ color: TOKENS.ink, textDecoration: "none", display: "inline-block" }}
      >
        <SidiraLockup height={32} />
      </Link>
      <nav style={{ display: "flex", gap: 16 }}>
        {TABS.map((tab) => {
          const active = pathname === tab.href || pathname.startsWith(tab.href + "/");
          return (
            <Link
              key={tab.href}
              href={tab.href}
              style={{
                textDecoration: "none",
                color: active ? TOKENS.ink : TOKENS.inkMuted,
                fontFamily: FONT_SANS,
                fontSize: 13,
                fontWeight: active ? 600 : 400,
                borderBottom: active ? `1.5px solid ${TOKENS.ink}` : "1.5px solid transparent",
                paddingBottom: 4,
              }}
            >
              {tab.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
