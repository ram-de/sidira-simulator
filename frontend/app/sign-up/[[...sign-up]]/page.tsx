"use client";

import { SignUp } from "@clerk/nextjs";

import { ConsoleMarkMono } from "@/components/v2";
import {
  clerkEnabled,
  clerkAppearanceConsole,
  SIGN_IN_URL,
  POST_AUTH_URL,
} from "@/lib/clerk";
import "@/styles/v2-theme.css";

// Sign-up always routes to /sso-callback, which ensures the new user has an
// organization. That organization.created event is what #31's webhook turns
// into a provisioned customer, so org creation is a required step of onboarding.
//
// VISUAL ONLY: the page frame is the v2 dark "Reading Console" (design-system-v2
// §4 / design-rethink/mocks/auth.html). The Clerk <SignUp> widget, its props,
// routing, and redirects are unchanged; it is themed dark via the shared
// `clerkAppearanceConsole` (lib/clerk.ts).
export default function SignUpPage() {
  if (!clerkEnabled()) {
    return (
      <AuthStage>
        <AuthUnavailableConsole />
      </AuthStage>
    );
  }

  return (
    <AuthStage
      eyebrow="CREATE ACCOUNT · SIDIRA CONSOLE"
      title="Open an instrument of your own."
      sub="Create a workspace to compose a hypothesis and read a synthetic cohort."
    >
      <SignUp
        appearance={clerkAppearanceConsole}
        signInUrl={SIGN_IN_URL}
        forceRedirectUrl={POST_AUTH_URL}
        fallbackRedirectUrl={POST_AUTH_URL}
      />
    </AuthStage>
  );
}

// ── Dark Console auth stage (visual frame only) ─────────────────────────────
// A single centered surface on a brutally-quiet field (design-system-v2 §0.2 —
// auth is WORKING-class, no showpiece). The `.v2-console` scope carries the v2
// tokens from v2-theme.css; the Clerk widget (themed via clerkAppearanceConsole)
// sits where {children} is. Token-driven CSS only — no raw hex, no font names.
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
            <ConsoleMarkMono size={34} />
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
        Sign-up is unavailable in this environment. Set{" "}
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
