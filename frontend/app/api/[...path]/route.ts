import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const API_BASE_INTERNAL =
  process.env.SIDIRA_API_BASE_INTERNAL ?? "http://127.0.0.1:8000";
const INTERNAL_API_KEY = process.env.SIDIRA_INTERNAL_API_KEY ?? "";

function targetUrl(request: NextRequest, path: string[]): URL {
  const incoming = new URL(request.url);
  const suffix = path.map(encodeURIComponent).join("/");
  return new URL(`/${suffix}${incoming.search}`, API_BASE_INTERNAL);
}

async function proxy(
  request: NextRequest,
  { params }: { params: { path?: string[] } },
) {
  const headers = new Headers();
  const accept = request.headers.get("accept");
  const contentType = request.headers.get("content-type");

  if (accept) headers.set("accept", accept);
  if (contentType) headers.set("content-type", contentType);
  if (INTERNAL_API_KEY) {
    headers.set("X-Sidira-Internal-Key", INTERNAL_API_KEY);
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
