"use client";

import { OrganizationSwitcher, SignedIn, UserButton } from "@clerk/nextjs";

import {
  clerkEnabled,
  clerkAppearance,
  clerkAppearanceConsole,
  SIGN_IN_URL,
} from "@/lib/clerk";

// Signed-in controls for the product TopNav (#32). Renders nothing when Clerk is
// not configured, so the pre-Clerk nav is unchanged. OrganizationSwitcher is the
// tenant switcher (tenancy = Clerk org); hidePersonal keeps users in an org
// context, matching the org-required onboarding in /sso-callback.
//
// `appearance` lets a host pick the Clerk theme: the default light
// `clerkAppearance` for the legacy light TopNav, or the dark
// `clerkAppearanceConsole` for the v2 Reading Console rail (AppShellV2), where
// the light theme would paint the org name near-black-on-dark (invisible).
export default function AuthControls({
  appearance = clerkAppearance,
}: {
  appearance?: typeof clerkAppearance | typeof clerkAppearanceConsole;
} = {}) {
  if (!clerkEnabled()) return null;

  return (
    <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12 }}>
      <SignedIn>
        <OrganizationSwitcher
          appearance={appearance}
          hidePersonal
          afterSelectOrganizationUrl="/"
          afterCreateOrganizationUrl="/"
        />
        <UserButton appearance={appearance} afterSignOutUrl={SIGN_IN_URL} />
      </SignedIn>
    </div>
  );
}
