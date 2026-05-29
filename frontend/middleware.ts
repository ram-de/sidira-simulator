import { NextRequest, NextResponse } from "next/server";

const WWW_HOST = "www.sidira.ai";
const APEX_HOST = "sidira.ai";

export function middleware(request: NextRequest) {
  const host = request.headers.get("host")?.toLowerCase();

  if (host === WWW_HOST) {
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.hostname = APEX_HOST;
    redirectUrl.protocol = "https:";
    redirectUrl.port = "";
    return NextResponse.redirect(redirectUrl, 308);
  }

  return NextResponse.next();
}
