import { redirect } from "next/navigation";

import { ConsoleMarkMono } from "@/components/v2";
import { clerkEnabled, hostedSignInUrl } from "@/lib/clerk";
import "@/styles/v2-theme.css";

// Catch-all route ([[...sign-in]]) so any /sign-in/* path also lands here.
//
// HOSTED SIGN-IN: this route redirects to the Clerk-hosted Account Portal
// (accounts.sidira.ai) rather than mounting the embedded <SignIn> widget. The
// pinned clerk-js 5.123.13 in our SDK cannot render this instance's Client
// Trust device-verification step (`needs_client_trust`) on a new device — the
// embedded submit spinner dead-ends. The hosted portal (clerk-js v6) handles
// it, then returns to the app's /sso-callback gateway. See lib/clerk.ts
// (hostedSignInUrl) and memory reference-clerk-dark-console-gotchas.
//
// When Clerk is not configured (local dev / CI, no publishable key) we render
// the dark Console "unavailable" surface instead of redirecting to prod.
export default function SignInPage({
  searchParams,
}: {
  searchParams: Record<string, string | string[] | undefined>;
}) {
  if (!clerkEnabled()) {
    return (
      <AuthStage>
        <AuthUnavailableConsole />
      </AuthStage>
    );
  }

  // Forward incoming query params (e.g. Clerk invitation `__clerk_ticket`) to
  // the hosted portal; our return URL is pinned server-side in hostedSignInUrl.
  redirect(hostedSignInUrl(searchParams));
}

// ── Dark Console auth stage (Clerk-unavailable surface only) ────────────────
// A single centered surface on a brutally-quiet field (design-system-v2 §0.2).
// The `.v2-console` scope carries the v2 tokens from v2-theme.css. Token-driven
// CSS only — no raw hex, no font names.
function AuthStage({ children }: { children: React.ReactNode }) {
  return (
    <main className="v2-console auth-stage">
      <div aria-hidden className="auth-bg" />
      <div className="auth-col">
        <div className="auth-head">
          <span className="auth-mark" aria-hidden>
            <ConsoleMarkMono size={34} />
          </span>
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

// Token-driven stage CSS for the unavailable surface. Every value is a v2 CSS
// var or a plain unit — no raw hex.
const AUTH_CSS = `
.auth-stage{
  position:relative;
  min-height:100vh;
  display:flex;
  flex-direction:column;
  align-items:center;
  justify-content:center;
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
.auth-sub{
  margin:10px auto 0;
  font-size:0.9375rem;
  line-height:1.55;
  color:var(--text-mut);
  max-width:38ch;
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
