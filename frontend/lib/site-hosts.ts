export const PUBLIC_SITE_HOST = "sidira.ai";
export const WWW_HOST = "www.sidira.ai";
export const APP_HOST = "app.sidira.ai";

const PRODUCT_PATH_PREFIXES = [
  "/agents",
  "/api",
  "/personas",
  "/product",
  "/research",
  "/simulations",
] as const;

export function normalizeHost(host: string | null): string {
  return (host ?? "").toLowerCase().split(":")[0] ?? "";
}

export function isPublicSiteHost(host: string | null): boolean {
  const normalized = normalizeHost(host);
  if (
    process.env.NODE_ENV === "development" &&
    normalized === "localhost" &&
    process.env.SIDIRA_PUBLIC_HOST === "1"
  ) {
    return true;
  }
  return normalized === PUBLIC_SITE_HOST || normalized === WWW_HOST;
}

export function isWwwHost(host: string | null): boolean {
  return normalizeHost(host) === WWW_HOST;
}

export function shouldRedirectProductPathToApp(
  host: string | null,
  pathname: string,
): boolean {
  if (!isPublicSiteHost(host)) return false;
  return PRODUCT_PATH_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}
