import { SIDIRA_HOME_HTML } from "@/lib/sidira-home-html";

// Served at "/" on the public host via the rewrite in middleware.ts.
export const dynamic = "force-static";

export function GET() {
  return new Response(SIDIRA_HOME_HTML, {
    headers: { "content-type": "text/html; charset=utf-8" },
  });
}
