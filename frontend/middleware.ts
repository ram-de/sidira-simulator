import { NextRequest, NextResponse } from "next/server";

import {
  APP_HOST,
  PUBLIC_SITE_HOST,
  isWwwHost,
  isPublicSiteHost,
  shouldRedirectProductPathToApp,
} from "@/lib/site-hosts";

const TEMPORARY_APP_BASIC_AUTH = process.env.SIDIRA_WEB_PROXY_BASIC_AUTH?.trim();

function appAuthChallenge() {
  return new NextResponse("Authorization required", {
    status: 401,
    headers: {
      "www-authenticate": "Basic realm=\"Sidira\"",
    },
  });
}

function hasValidTemporaryAppAuth(request: NextRequest): boolean {
  if (!TEMPORARY_APP_BASIC_AUTH) return true;
  return request.headers.get("authorization") === `Basic ${TEMPORARY_APP_BASIC_AUTH}`;
}

export function middleware(request: NextRequest) {
  const host = request.headers.get("host");

  if (isWwwHost(host)) {
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.hostname = PUBLIC_SITE_HOST;
    redirectUrl.protocol = "https:";
    redirectUrl.port = "";
    return NextResponse.redirect(redirectUrl, 308);
  }

  if (shouldRedirectProductPathToApp(host, request.nextUrl.pathname)) {
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.hostname = APP_HOST;
    redirectUrl.protocol = "https:";
    redirectUrl.port = "";
    return NextResponse.redirect(redirectUrl, 308);
  }

  if (!isPublicSiteHost(host) && !hasValidTemporaryAppAuth(request)) {
    return appAuthChallenge();
  }

  return NextResponse.next();
}
