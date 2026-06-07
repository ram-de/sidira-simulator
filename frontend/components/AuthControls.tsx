"use client";

import { OrganizationSwitcher, SignedIn, UserButton } from "@clerk/nextjs";

import { clerkEnabled, clerkAppearance, SIGN_IN_URL } from "@/lib/clerk";

// Signed-in controls for the product TopNav (#32). Renders nothing when Clerk is
// not configured, so the pre-Clerk nav is unchanged. OrganizationSwitcher is the
// tenant switcher (tenancy = Clerk org); hidePersonal keeps users in an org
// context, matching the org-required onboarding in /sso-callback.
export default function AuthControls() {
  if (!clerkEnabled()) return null;

  return (
    <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12 }}>
      <SignedIn>
        <OrganizationSwitcher
          appearance={clerkAppearance}
          hidePersonal
          afterSelectOrganizationUrl="/"
          afterCreateOrganizationUrl="/"
        />
        <UserButton appearance={clerkAppearance} afterSignOutUrl={SIGN_IN_URL} />
      </SignedIn>
    </div>
  );
}
