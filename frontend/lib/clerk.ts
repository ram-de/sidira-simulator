// Clerk wiring for the product app (#32). Everything is gated on the publishable
// key so the app stays fully functional — and the build stays green — when Clerk
// is not configured (local dev without keys, CI, and prod until #149 + the Clerk
// secret land). When the key is absent we render the pre-Clerk surfaces and the
// middleware keeps the temporary Basic-Auth fallback. This mirrors the backend's
// env-gated Clerk middleware (#29).
import { TOKENS, FONT_SANS, FONT_NARROW } from "@/lib/design";

// NEXT_PUBLIC_* is inlined at build into both server and client bundles, so this
// reads correctly from middleware (server) and the auth pages (client) alike.
export const CLERK_PUBLISHABLE_KEY =
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "";

export const clerkEnabled = (): boolean => CLERK_PUBLISHABLE_KEY.length > 0;

// Auth route URLs — keep in lockstep with the file-system routes under app/.
export const SIGN_IN_URL = "/sign-in";
export const SIGN_UP_URL = "/sign-up";
// Post-authentication landing: a client gateway that ensures the user has an
// active organization (so #31's organization.created webhook provisions the
// customer) and then routes by whether the tenant already has a persona pack.
export const POST_AUTH_URL = "/sso-callback";

// Brand-aligned Clerk appearance — maps the prebuilt components onto DESIGN.md
// tokens (§4 palette, §5 type, 4px radius, 2px input borders). Refinements are
// fair game for design review; this keeps the components on-brand out of the box.
export const clerkAppearance = {
  variables: {
    colorPrimary: TOKENS.ink,
    colorBackground: TOKENS.paperElevated,
    colorText: TOKENS.ink,
    colorTextSecondary: TOKENS.inkMuted,
    colorInputBackground: TOKENS.paperRecessed,
    colorInputText: TOKENS.ink,
    colorDanger: TOKENS.alert,
    borderRadius: "4px",
    fontFamily: FONT_SANS,
  },
  elements: {
    card: {
      boxShadow: "none",
      border: `0.75px solid ${TOKENS.rule}`,
      background: TOKENS.paperElevated,
    },
    formButtonPrimary: {
      fontFamily: FONT_NARROW,
      fontSize: "13px",
      fontWeight: 600,
      letterSpacing: "0.08em",
      textTransform: "uppercase" as const,
    },
    formFieldInput: {
      borderWidth: "2px",
    },
  },
} as const;
