import { NextRequest, NextResponse } from "next/server";
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

import {
  APP_HOST,
  PUBLIC_SITE_HOST,
  isWwwHost,
  isPublicSiteHost,
  shouldRedirectProductPathToApp,
} from "@/lib/site-hosts";
import { clerkEnabled, SIGN_IN_URL } from "@/lib/clerk";

const TEMPORARY_APP_BASIC_AUTH = process.env.SIDIRA_WEB_PROXY_BASIC_AUTH?.trim();

// Product surfaces that require a signed-in user once Clerk is configured.
// The public marketing host is exempted separately (it never serves these).
const isProtectedRoute = createRouteMatcher([
  "/",
  "/personas(.*)",
  "/product(.*)",
  "/simulations(.*)",
  "/agents(.*)",
]);

// Clerk's own auth surfaces must stay reachable while signed out.
const isAuthRoute = createRouteMatcher([
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/sso-callback(.*)",
]);

// The same-origin proxy (app/api/[...path]/route.ts) staples the server-side
// Basic Auth credential onto any request that arrives without one, so an
// unauthenticated /api call would otherwise reach the backend with the server's
// credential. These routes must be gated too once Clerk is enabled.
const isApiRoute = createRouteMatcher([
  "/api(.*)",
  "/trpc(.*)",
]);

function appAuthChallenge() {
  return new NextResponse("Authorization required", {
    status: 401,
    headers: {
      "www-authenticate": "Basic realm=\"Sidira\"",
    },
  });
}

// 401 for API callers under Clerk — no www-authenticate header, so the browser
// does not raise a Basic Auth prompt (that gate is the pre-Clerk fallback only).
function apiAuthChallenge() {
  return new NextResponse("Authentication required", { status: 401 });
}

function hasValidTemporaryAppAuth(request: NextRequest): boolean {
  if (!TEMPORARY_APP_BASIC_AUTH) return true;
  return request.headers.get("authorization") === `Basic ${TEMPORARY_APP_BASIC_AUTH}`;
}

// Host normalization is independent of auth: www → apex, and product paths hit
// on the public marketing host bounce to the app host. Runs in both the Clerk
// and pre-Clerk paths. Returns a redirect response to short-circuit, else null.
function hostRedirect(request: NextRequest): NextResponse | null {
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

  return null;
}

// Pre-Clerk behavior: host redirects + the temporary app-host Basic Auth gate
// (the Amplify workaround). Used verbatim when Clerk is not configured so CI,
// preview, and prod-before-Clerk keep working exactly as before.
function basicAuthMiddleware(request: NextRequest) {
  const redirect = hostRedirect(request);
  if (redirect) return redirect;

  const host = request.headers.get("host");
  if (!isPublicSiteHost(host) && !hasValidTemporaryAppAuth(request)) {
    return appAuthChallenge();
  }

  return NextResponse.next();
}

// Clerk-configured behavior: host redirects still run first, then unauthenticated
// requests to protected product routes are redirected to /sign-in. Clerk replaces
// the temporary Basic Auth gate on the app host. The backend token hop lives in
// app/api/[...path]/route.ts → Caddy (#149).
const clerkAuthMiddleware = clerkMiddleware(async (auth, request) => {
  const redirect = hostRedirect(request);
  if (redirect) return redirect;

  const host = request.headers.get("host");
  // The marketing host and Clerk's own auth surfaces stay open while signed out.
  if (isPublicSiteHost(host) || isAuthRoute(request)) {
    return NextResponse.next();
  }

  // API proxy routes require a session, but answer with 401 rather than a
  // sign-in redirect — an API client can't follow an HTML redirect. This closes
  // the bypass where the proxy would forward to the backend with the server's
  // Basic Auth credential. The proxy forwards the session's Clerk token (#149).
  if (isApiRoute(request)) {
    const { userId } = await auth();
    if (!userId) return apiAuthChallenge();
    return NextResponse.next();
  }

  if (isProtectedRoute(request)) {
    await auth.protect({
      unauthenticatedUrl: new URL(SIGN_IN_URL, request.url).toString(),
    });
  }

  return NextResponse.next();
});

export default clerkEnabled() ? clerkAuthMiddleware : basicAuthMiddleware;

export const config = {
  matcher: [
    // Run on app routes; skip Next internals and static asset files.
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
