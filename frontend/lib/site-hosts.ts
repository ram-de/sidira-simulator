export const PUBLIC_SITE_HOST = "sidira.ai";
export const WWW_HOST = "www.sidira.ai";
export const APP_HOST = "app.sidira.ai";

const PRODUCT_PATH_PREFIXES = [
  "/agents",
  "/api",
  "/personas",
  "/product",
  "/simulations",
] as const;

export function normalizeHost(host: string | null): string {
  return (host ?? "").toLowerCase().split(":")[0] ?? "";
}

export function isPublicSiteHost(host: string | null): boolean {
  return normalizeHost(host) === PUBLIC_SITE_HOST;
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
