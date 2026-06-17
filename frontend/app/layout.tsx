import type { Metadata } from "next";
import { headers } from "next/headers";
import { Archivo, Archivo_Narrow, JetBrains_Mono } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";

import ConditionalTopNav from "@/components/ConditionalTopNav";
import { isPublicSiteHost } from "@/lib/site-hosts";
import { clerkEnabled, clerkAppearance } from "@/lib/clerk";
import { v2Enabled } from "@/lib/v2flag";
import { TOKENS, FONT_SANS } from "@/lib/design";

// MVP ships the fallback column of DESIGN.md §5.1 as production: Archivo
// (body 400 / display 600 / UI labels 500), Archivo Narrow (wordmark +
// marketing display), JetBrains Mono (data). No serif anywhere — R2 dropped
// GT Sectra and its stand-in entirely.
const fontSans = Archivo({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

const fontNarrow = Archivo_Narrow({
  subsets: ["latin"],
  variable: "--font-narrow",
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

const fontMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "Sidira",
  description: "Validate product hypotheses before you build them.",
  applicationName: "Sidira",
  icons: {
    icon: "/icon.svg",
    shortcut: "/icon.svg",
    apple: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const host = headers().get("host");
  const showProductNav = !isPublicSiteHost(host);
  // v2 flag evaluated SERVER-side (cookie/env) so ConditionalTopNav suppresses
  // the global nav on the v2 /simulations list deterministically — no flash, no
  // hydration mismatch (#372).
  const v2On = v2Enabled();

  const fontClass = [
    fontSans.variable,
    fontNarrow.variable,
    fontMono.variable,
  ].join(" ");

  const tree = (
    <html lang="en" className={fontClass}>
      <body
        style={{
          margin: 0,
          fontFamily: FONT_SANS,
          color: TOKENS.ink,
          background: TOKENS.paper,
        }}
      >
        {/* Focus ring — DESIGN.md §7.8. The app's one global element-selector
            rule: offset ink hairline on :focus-visible. Surfaces that need a
            different ring color (glass) set --focus-ring inline. */}
        <style
          dangerouslySetInnerHTML={{
            __html: `
              :focus-visible {
                outline: 1px solid var(--focus-ring, ${TOKENS.ink});
                outline-offset: 2px;
              }
            `,
          }}
        />
        {showProductNav ? <ConditionalTopNav v2On={v2On} /> : null}
        <div style={{ minHeight: showProductNav ? "calc(100vh - 56px)" : "100vh" }}>
          {children}
        </div>
      </body>
    </html>
  );

  // Wrap in ClerkProvider only when Clerk is configured. Without the publishable
  // key the prebuilt components would throw during render/SSR, so the unconfigured
  // build renders the pre-Clerk tree unchanged (see lib/clerk.ts).
  return clerkEnabled() ? (
    <ClerkProvider appearance={clerkAppearance}>{tree}</ClerkProvider>
  ) : (
    tree
  );
}
