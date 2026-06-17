import Link from "next/link";
import { SheetMarkDuo } from "@/components/v2";
import { APP_URL } from "@/components/PublicTopBar";

// ───────────────────────────────────────────────────────────────────────────
// Public-surface top bar — dark "Reading Console" reskin of PublicTopBar.
//
// Same LINKS / hrefs / copy as PublicTopBar (brand → "/", About → "/about",
// Request access → mailto, Sign in → APP_URL) — only the surface changes to the
// dark Console language (DESIGN.md / design-system-v2). Used by the public
// marketing pages (`/`, `/about`, `/product`) which render INSIDE a
// `.v2-console` scope (ConsoleShell), so all `var(--console-*)` / `var(--text*)`
// tokens resolve from styles/v2-theme.css.
//
// The duo aperture mark is sanctioned here: public site / about are brand-mode
// surfaces (DESIGN.md §1.3). The wordmark rests in paper (`--text-hi`), never
// signal (P1). Links are real Next <Link> elements so every target is preserved
// byte-for-byte and client routing still works.
// ───────────────────────────────────────────────────────────────────────────
export default function PublicConsoleTopBar({
  currentPath,
}: {
  currentPath?: "/about" | "/product";
}) {
  return (
    <header
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        background: "rgba(16,25,42,.86)",
        backdropFilter: "blur(14px) saturate(140%)",
        WebkitBackdropFilter: "blur(14px) saturate(140%)",
        borderBottom: "1px solid var(--console-line-50)",
      }}
    >
      <div
        style={{
          maxWidth: 1240,
          margin: "0 auto",
          padding: "13px 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 24,
          flexWrap: "wrap",
        }}
      >
        <Link
          href="/"
          aria-label="Sidira home"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 9,
            color: "var(--text-hi)",
            textDecoration: "none",
          }}
        >
          <SheetMarkDuo size={26} />
          <span
            style={{
              fontWeight: 600,
              letterSpacing: "0.08em",
              fontSize: 15,
            }}
          >
            SIDIRA
          </span>
        </Link>

        <nav
          style={{
            display: "flex",
            gap: 4,
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <Link
            href="/about"
            aria-current={currentPath === "/about" ? "page" : undefined}
            style={{
              color:
                currentPath === "/about" ? "var(--text-hi)" : "var(--text-mut)",
              fontSize: 13.5,
              fontWeight: 450,
              textDecoration: "none",
              padding: "7px 12px",
              borderRadius: "var(--r-well)",
            }}
          >
            About
          </Link>
          <Link
            href="mailto:founders@sidira.ai?subject=Sidira%20access"
            style={{
              color: "var(--text-mut)",
              fontSize: 13.5,
              fontWeight: 450,
              textDecoration: "none",
              padding: "7px 12px",
              borderRadius: "var(--r-well)",
            }}
          >
            Request access
          </Link>
          <Link
            href={APP_URL}
            className="v2-btn v2-btn--primary"
            style={{ textDecoration: "none" }}
          >
            Sign in
          </Link>
        </nav>
      </div>
    </header>
  );
}
