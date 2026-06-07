import { SignUp } from "@clerk/nextjs";

import AuthShell from "@/components/AuthShell";
import AuthUnavailable from "@/components/AuthUnavailable";
import {
  clerkEnabled,
  clerkAppearance,
  SIGN_IN_URL,
  POST_AUTH_URL,
} from "@/lib/clerk";

// Sign-up always routes to /sso-callback, which ensures the new user has an
// organization. That organization.created event is what #31's webhook turns
// into a provisioned customer, so org creation is a required step of onboarding.
export default function SignUpPage() {
  if (!clerkEnabled()) {
    return (
      <AuthShell>
        <AuthUnavailable />
      </AuthShell>
    );
  }

  return (
    <AuthShell>
      <SignUp
        appearance={clerkAppearance}
        signInUrl={SIGN_IN_URL}
        forceRedirectUrl={POST_AUTH_URL}
        fallbackRedirectUrl={POST_AUTH_URL}
      />
    </AuthShell>
  );
}
