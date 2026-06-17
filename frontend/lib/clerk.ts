// Clerk wiring for the product app (#32). Everything is gated on the publishable
// key so the app stays fully functional — and the build stays green — when Clerk
// is not configured (local dev without keys, CI, and prod until #149 + the Clerk
// secret land). When the key is absent we render the pre-Clerk surfaces and the
// middleware keeps the temporary Basic-Auth fallback. This mirrors the backend's
// env-gated Clerk middleware (#29).
import { TOKENS, FONT_SANS, FONT_NARROW, FONT_MONO } from "@/lib/design";

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
    // Workbench chrome (R2 mock): the org switcher renders as the workspace
    // chip — mono 11px, 1px rule border, radius 2 — and the user button as
    // the 26px square avatar.
    organizationSwitcherTrigger: {
      fontFamily: FONT_MONO,
      fontSize: "11px",
      color: TOKENS.ink,
      border: `1px solid ${TOKENS.rule}`,
      borderRadius: "2px",
      padding: "4px 10px",
      transition: "border-color 80ms ease-out",
      "&:hover": {
        borderColor: TOKENS.inkMuted,
        backgroundColor: "transparent",
      },
    },
    userButtonAvatarBox: {
      width: "26px",
      height: "26px",
      borderRadius: "2px",
    },
  },
} as const;

// Console (dark-rail) Clerk appearance — the v2 Reading Console rail footer
// (AppShellV2) renders AuthControls on a dark background, where the default
// light `clerkAppearance` paints the org NAME near-black-on-dark (invisible —
// only the icons survive). These values are LITERAL console-palette hex (not
// CSS vars) on purpose: Clerk renders the org-switcher / user-button dropdowns
// in a portal at document root, OUTSIDE the `.v2` CSS scope where the
// `--console-*`/`--text-*` vars are defined, so a var() would not resolve in
// the popover. Hex values mirror frontend/lib/design-v2.ts (CONSOLE/TEXT/SIGNAL).
export const clerkAppearanceConsole = {
  variables: {
    colorPrimary: "#48EFCA", // SIGNAL.base — accent
    colorBackground: "#161F32", // CONSOLE.c800 — popover/card surface
    colorText: "#F2F4F8", // TEXT.hi — primary text incl. the org name
    colorTextSecondary: "#929BAE", // TEXT.mut — secondary / captions
    colorInputBackground: "#26314C", // CONSOLE.c700 — input wells
    colorInputText: "#F2F4F8", // TEXT.hi
    colorDanger: "#F0683C", // STATUS.alert
    borderRadius: "4px",
    fontFamily: FONT_SANS,
  },
  elements: {
    card: {
      boxShadow: "none",
      border: "0.75px solid #33405C", // CONSOLE.line
      background: "#161F32", // CONSOLE.c800
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
    // The org switcher trigger is the workspace chip in the dark rail — the org
    // NAME must read as light text (TEXT.hi) over the console surface.
    organizationSwitcherTrigger: {
      fontFamily: FONT_MONO,
      fontSize: "11px",
      color: "#F2F4F8", // TEXT.hi — the fix: org name now legible on dark
      border: "1px solid #33405C", // CONSOLE.line
      borderRadius: "2px",
      padding: "4px 10px",
      transition: "border-color 80ms ease-out, background-color 80ms ease-out",
      "&:hover": {
        borderColor: "#929BAE", // TEXT.mut
        backgroundColor: "#1D2740", // CONSOLE.c750 — hover well
      },
    },
    userButtonAvatarBox: {
      width: "26px",
      height: "26px",
      borderRadius: "2px",
    },
  },
} as const;
