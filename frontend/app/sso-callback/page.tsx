"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CreateOrganization, useAuth } from "@clerk/nextjs";

import { SheetMarkDuo } from "@/components/v2";
import { getActivePersonas } from "@/lib/api";
import {
  clerkEnabled,
  clerkAppearanceConsole,
  POST_AUTH_URL,
  SIGN_IN_URL,
} from "@/lib/clerk";
import "@/styles/v2-theme.css";

function StatusMessage({ children }: { children: React.ReactNode }) {
  return <p className="auth-status">{children}</p>;
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
//
// VISUAL ONLY: the surrounding loading/redirect screen now wears the v2 dark
// "Reading Console" frame (design-system-v2 §4). The auth logic below — the
// gateway effect, the CreateOrganization props (afterCreateOrganizationUrl,
// skipInvitationScreen), and every redirect — is unchanged. Clerk's
// CreateOrganization is themed dark via the shared `clerkAppearanceConsole`.
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
      <AuthStage>
        <AuthUnavailableConsole />
      </AuthStage>
    );
  }

  if (needsOrg) {
    return (
      <AuthStage
        eyebrow="WORKSPACE · SIDIRA CONSOLE"
        title="Name your workspace."
        sub="A workspace groups your personas, hypotheses, and readings under one tenant."
      >
        <CreateOrganization
          appearance={clerkAppearanceConsole}
          afterCreateOrganizationUrl={POST_AUTH_URL}
          skipInvitationScreen
        />
      </AuthStage>
    );
  }

  return (
    <AuthStage>
      <StatusMessage>Setting up your workspace…</StatusMessage>
    </AuthStage>
  );
}

// ── Dark Console auth stage (visual frame only) ─────────────────────────────
// A single centered surface on a brutally-quiet field (design-system-v2 §0.2 —
// auth is WORKING-class, no showpiece). The `.v2-console` scope carries the v2
// tokens from v2-theme.css; the gateway content (Clerk CreateOrganization or the
// status line) sits where {children} is. Token-driven CSS only — no raw hex.
function AuthStage({
  children,
  eyebrow,
  title,
  sub,
}: {
  children: React.ReactNode;
  eyebrow?: string;
  title?: string;
  sub?: string;
}) {
  return (
    <main className="v2-console auth-stage">
      <div aria-hidden className="auth-bg" />
      <div className="auth-col">
        <div className="auth-head">
          <span className="auth-mark" aria-hidden>
            <SheetMarkDuo size={34} />
          </span>
          {eyebrow ? <span className="v2-desig">{eyebrow}</span> : null}
          {title ? <h1 className="auth-title">{title}</h1> : null}
          {sub ? <p className="auth-sub">{sub}</p> : null}
        </div>
        {children}
      </div>
      <style>{AUTH_CSS}</style>
    </main>
  );
}

// Clerk-not-configured surface, dark Console treatment (no publishable key).
function AuthUnavailableConsole() {
  return (
    <div className="v2-panel v2-elevated auth-unavailable">
      <span className="v2-desig">Authentication not configured</span>
      <p className="auth-sub" style={{ marginTop: 10 }}>
        Sign-in is unavailable in this environment. Set{" "}
        <code className="v2-mono">NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY</code> to
        enable Clerk.
      </p>
    </div>
  );
}

// Shared, token-driven stage CSS (mirrors app/v2/auth + design-rethink/mocks/
// auth.html). Every value is a v2 CSS var or a plain unit — no raw hex.
const AUTH_CSS = `
.auth-stage{
  position:relative;
  min-height:100vh;
  display:flex;
  flex-direction:column;
  align-items:center;
  justify-content:center;
  overflow:hidden;
  padding:64px 24px 96px;
}
.auth-bg{
  position:absolute;
  inset:0;
  z-index:0;
  pointer-events:none;
  background:
    radial-gradient(60% 50% at 50% 28%, var(--signal-wash), transparent 62%),
    linear-gradient(180deg, var(--console-850) 0%, var(--console-900) 100%);
}
.auth-col{
  position:relative;
  z-index:1;
  width:100%;
  max-width:440px;
  display:flex;
  flex-direction:column;
  align-items:center;
  gap:24px;
}
.auth-head{
  width:100%;
  text-align:center;
}
.auth-mark{
  display:inline-flex;
  color:var(--text-hi);
  margin-bottom:18px;
}
.auth-title{
  margin:12px 0 0;
  font-size:1.6rem;
  line-height:1.1;
  letter-spacing:-0.025em;
  font-weight:600;
  color:var(--text-hi);
  text-wrap:balance;
}
.auth-sub{
  margin:10px auto 0;
  font-size:0.9375rem;
  line-height:1.55;
  color:var(--text-mut);
  max-width:38ch;
}
.auth-status{
  margin:0;
  font-size:0.9375rem;
  color:var(--text-mut);
}
.auth-unavailable{
  width:100%;
  max-width:440px;
  padding:32px 28px;
  text-align:center;
}
.auth-unavailable code{
  font-size:0.8125rem;
  color:var(--text);
}
@media(max-width:480px){
  .auth-stage{padding:40px 18px 64px;}
}
`;
