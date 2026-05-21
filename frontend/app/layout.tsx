import type { Metadata } from "next";

import TopNav from "@/components/TopNav";

export const metadata: Metadata = {
  title: "Pythia",
  description: "Validate product hypotheses before you build them.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
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
        <TopNav />
        <div style={{ minHeight: "calc(100vh - 56px)" }}>{children}</div>
      </body>
    </html>
  );
}
