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
// the temporary Basic Auth gate on the app host. #149 will add backend token
// forwarding through the Caddy proxy; that header redesign is out of scope here.
const clerkAuthMiddleware = clerkMiddleware(async (auth, request) => {
  const redirect = hostRedirect(request);
  if (redirect) return redirect;

  const host = request.headers.get("host");
  if (!isPublicSiteHost(host) && isProtectedRoute(request) && !isAuthRoute(request)) {
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
