import { TOKENS, FONT_SANS } from "@/lib/design";

// Centered paper backdrop for the Clerk auth surfaces (#32). The prebuilt Clerk
// card sits in the middle; the page itself stays free of the product TopNav
// because these routes render on the app host where layout shows the nav only
// for product pages — auth pages are full-bleed by design.
export default function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 24px",
        background: TOKENS.paper,
        fontFamily: FONT_SANS,
        color: TOKENS.ink,
      }}
    >
      {children}
    </main>
  );
}
