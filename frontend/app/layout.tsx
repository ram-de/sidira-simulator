import type { Metadata } from "next";
import { headers } from "next/headers";
import {
  Archivo_Narrow,
  Hanken_Grotesk,
  Instrument_Serif,
  JetBrains_Mono,
} from "next/font/google";

import TopNav from "@/components/TopNav";
import { isPublicSiteHost } from "@/lib/site-hosts";

// Production fonts per DESIGN.md §5.1 ship as licensed faces (Söhne, Söhne
// Schmal, Berkeley Mono, GT Sectra Fine). These four free Google Fonts are
// the documented preview stand-ins until the licensed faces are wired in.
// Hanken Grotesk is the closest Söhne substitute that ships with Next 14.2's
// bundled Google Fonts list.
const fontSans = Hanken_Grotesk({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
  weight: ["300", "400", "500", "600", "700"],
});

const fontNarrow = Archivo_Narrow({
  subsets: ["latin"],
  variable: "--font-narrow",
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

const fontSerif = Instrument_Serif({
  subsets: ["latin"],
  variable: "--font-serif",
  display: "swap",
  weight: "400",
  style: ["normal", "italic"],
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

  const fontClass = [
    fontSans.variable,
    fontNarrow.variable,
    fontSerif.variable,
    fontMono.variable,
  ].join(" ");

  return (
    <html lang="en" className={fontClass}>
      <body
        style={{
          margin: 0,
          fontFamily: "var(--font-sans), ui-sans-serif, sans-serif",
          color: "#0E1A2B",
          background: "#F4EFE6",
        }}
      >
        {showProductNav ? <TopNav /> : null}
        <div style={{ minHeight: showProductNav ? "calc(100vh - 56px)" : "100vh" }}>
          {children}
        </div>
      </body>
    </html>
  );
}
