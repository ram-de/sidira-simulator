"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CreateOrganization, useAuth } from "@clerk/nextjs";

import AuthShell from "@/components/AuthShell";
import AuthUnavailable from "@/components/AuthUnavailable";
import { getActivePersonas } from "@/lib/api";
import { clerkEnabled, clerkAppearance, POST_AUTH_URL, SIGN_IN_URL } from "@/lib/clerk";
import { TOKENS, FONT_SANS } from "@/lib/design";

function StatusMessage({ children }: { children: React.ReactNode }) {
  return (
    <p
      style={{
        margin: 0,
        fontFamily: FONT_SANS,
        fontSize: 14,
        color: TOKENS.inkMuted,
      }}
    >
      {children}
    </p>
  );
}

// Post-authentication gateway (#32). Three states, resolved client-side once
// Clerk has loaded the session:
//   1. not signed in        → bounce to /sign-in
//   2. signed in, no org    → render <CreateOrganization>; the resulting
//                             organization.created event drives #31's webhook,
//                             which provisions the customer in the backend
//   3. signed in, has org   → route by pack presence: a tenant with no active
//                             Persona Pack starts one at /personas/new, an
//                             existing tenant lands on the dashboard at /
//
// #149 will forward the Clerk session token to the backend through the proxy so
// getActivePersonas() is authenticated as the tenant; until then the call may be
// served under the temporary Basic-Auth context. Either way, a thrown/empty
// result is treated as "no pack yet" and sends the user to /personas/new.
//
// #212: GET /personas no longer 404s for an empty tenant — it serves a generic
// starter pack (is_starter=true) so the rest of the product is clickable. A
// starter is NOT a real pack, so it must still route the user into onboarding,
// otherwise brand-new orgs would skip /personas/new entirely.
export default function PostAuthGatewayPage() {
  const router = useRouter();
  const { isLoaded, isSignedIn, orgId } = useAuth();
  const [needsOrg, setNeedsOrg] = useState(false);

  useEffect(() => {
    if (!clerkEnabled() || !isLoaded) return;

    if (!isSignedIn) {
      router.replace(SIGN_IN_URL);
      return;
    }

    if (!orgId) {
      setNeedsOrg(true);
      return;
    }

    setNeedsOrg(false);
    let cancelled = false;
    (async () => {
      let destination = "/personas/new";
      try {
        const active = await getActivePersonas();
        // A starter pack (#212) means "no real pack yet" — keep onboarding.
        if ((active?.personas?.length ?? 0) > 0 && !active?.is_starter) {
          destination = "/";
        }
      } catch {
        // No active pack (404) or not yet authenticated to the API → onboard.
        destination = "/personas/new";
      }
      if (!cancelled) router.replace(destination);
    })();

    return () => {
      cancelled = true;
    };
  }, [isLoaded, isSignedIn, orgId, router]);

  if (!clerkEnabled()) {
    return (
      <AuthShell>
        <AuthUnavailable />
      </AuthShell>
    );
  }

  if (needsOrg) {
    return (
      <AuthShell>
        <CreateOrganization
          appearance={clerkAppearance}
          afterCreateOrganizationUrl={POST_AUTH_URL}
          skipInvitationScreen
        />
      </AuthShell>
    );
  }

  return (
    <AuthShell>
      <StatusMessage>Setting up your workspace…</StatusMessage>
    </AuthShell>
  );
}
