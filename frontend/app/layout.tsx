import type { Metadata } from "next";
import { headers } from "next/headers";

import TopNav from "@/components/TopNav";
import { isPublicSiteHost } from "@/lib/site-hosts";

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

  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          fontFamily:
            'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
          color: "#111",
          background: "#fff",
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
