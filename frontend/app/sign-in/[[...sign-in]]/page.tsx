import { SignIn } from "@clerk/nextjs";

import AuthShell from "@/components/AuthShell";
import AuthUnavailable from "@/components/AuthUnavailable";
import {
  clerkEnabled,
  clerkAppearance,
  SIGN_UP_URL,
  POST_AUTH_URL,
} from "@/lib/clerk";

// Catch-all route ([[...sign-in]]) so Clerk can mount its own sub-paths
// (e.g. the OAuth /sign-in/sso-callback leg) under this segment. The top-level
// /sso-callback route is the post-auth app gateway, distinct from Clerk's leg.
export default function SignInPage() {
  if (!clerkEnabled()) {
    return (
      <AuthShell>
        <AuthUnavailable />
      </AuthShell>
    );
  }

  return (
    <AuthShell>
      <SignIn
        appearance={clerkAppearance}
        signUpUrl={SIGN_UP_URL}
        forceRedirectUrl={POST_AUTH_URL}
        fallbackRedirectUrl={POST_AUTH_URL}
      />
    </AuthShell>
  );
}
