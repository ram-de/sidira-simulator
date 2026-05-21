"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

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
        borderBottom: "1px solid #eee",
        background: "#fafafa",
        padding: "12px 24px",
        display: "flex",
        alignItems: "center",
        gap: 24,
      }}
    >
      <Link href="/" style={{ fontWeight: 600, fontSize: 18, textDecoration: "none", color: "#111" }}>
        Pythia
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
                color: active ? "#111" : "#666",
                fontWeight: active ? 600 : 400,
                borderBottom: active ? "2px solid #111" : "2px solid transparent",
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
