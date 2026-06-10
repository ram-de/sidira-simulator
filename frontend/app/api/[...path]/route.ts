import { NextRequest, NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";

import { clerkEnabled } from "@/lib/clerk";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const API_BASE_INTERNAL =
  process.env.SIDIRA_API_BASE_INTERNAL ?? "http://127.0.0.1:8000";
const WEB_PROXY_BASIC_AUTH = process.env.SIDIRA_WEB_PROXY_BASIC_AUTH?.trim();

// The Authorization slot on the upstream hop is occupied by the Basic
// credential that Caddy's `_sidira_web_proxy` basic_auth consumes, so the
// Clerk session token rides this header instead; Caddy promotes it to
// Authorization after the hop auth passes (deploy/Caddyfile.api). #149
const CLERK_FORWARD_HEADER = "x-sidira-clerk-authorization";

// Clerk session token for the signed-in user, or null. Only call when Clerk
// is enabled — auth() requires clerkMiddleware to have run, which the
// middleware guarantees for /api routes exactly when clerkEnabled().
async function clerkBearer(): Promise<string | null> {
  const { getToken } = await auth();
  const token = await getToken();
  return token ? `Bearer ${token}` : null;
}

function targetUrl(request: NextRequest, path: string[]): URL {
  const incoming = new URL(request.url);
  const suffix = path.map(encodeURIComponent).join("/");
  return new URL(
    `${API_BASE_INTERNAL.replace(/\/$/, "")}/${suffix}${incoming.search}`,
  );
}

async function proxy(
  request: NextRequest,
  { params }: { params: { path?: string[] } },
) {
  const headers = new Headers();
  const accept = request.headers.get("accept");
  const authorization =
    request.headers.get("authorization") ??
    (WEB_PROXY_BASIC_AUTH ? `Basic ${WEB_PROXY_BASIC_AUTH}` : null);
  const contentType = request.headers.get("content-type");

  if (accept) headers.set("accept", accept);
  if (authorization) headers.set("authorization", authorization);
  if (contentType) headers.set("content-type", contentType);

  if (clerkEnabled()) {
    const bearer = await clerkBearer();
    if (bearer) headers.set(CLERK_FORWARD_HEADER, bearer);
  }

  const body =
    request.method === "GET" || request.method === "HEAD"
      ? undefined
      : await request.arrayBuffer();
  const response = await fetch(targetUrl(request, params.path ?? []), {
    method: request.method,
    headers,
    body,
    cache: "no-store",
    redirect: "manual",
  });

  const responseHeaders = new Headers(response.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("content-length");
  return new NextResponse(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
