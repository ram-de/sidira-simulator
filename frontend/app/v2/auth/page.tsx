// ───────────────────────────────────────────────────────────────────────────
// /v2/auth — DESIGN SYSTEM v2 PREVIEW · sign-in screen (dark Console)
//
// A PUBLIC, NOINDEX, nav-suppressed, STATIC-MOCK preview under the clean
// top-level /v2/<slug> namespace. Reachable only by typing /v2/auth — nothing
// links here, and it touches NO real auth-walled route. The global product nav
// is suppressed on /v2/* (components/ConditionalTopNav.tsx); this page ships its
// own self-contained Console TopBar with the mono mark.
//
// ARCHETYPE — Console (dark). Auth is the gateway into the dark in-app
// experience (design-system-v2.md §4: app-shell/dashboard/setup are Console). A
// login screen is a focused, centered surface: ONE sign-in card on a quiet,
// brutally-still field (the impact budget — §0.2 — has no SHOWPIECE here; the
// computation isn't on this screen). The card carries one minimal Provenance
// strip; the wordmark/dot rest in ink, never signal (the signal budget, §1.9).
//
// This page CONSUMES the shared v2 layer (lib/design-v2.ts, components/v2/*,
// v2-theme.css) and never re-inlines a raw hex or font name. The interactive
// form is its own "use client" child (./SignInForm); this file stays a server
// component. Page-local input styling is token-driven (CSS vars only), mirroring
// the HERO_GRID_CSS precedent in app/product/v2/page.tsx.
// ───────────────────────────────────────────────────────────────────────────
import type { Metadata } from "next";
import {
  ConsoleShell,
  Wrap,
  TopBar,
  Designator,
  ProvenanceBar,
  ConsoleMarkMono,
  type NavItem,
  type ProvSeg,
} from "@/components/v2";
import { SignInForm } from "./SignInForm";
import "@/styles/v2-theme.css";

export const metadata: Metadata = {
  title: "Sign in — Sidira",
  robots: { index: false, follow: false },
};

// ── static mock data (consts, top of file) ─────────────────────────────────
// The top bar's marketing nav (inert hrefs). No "active" item — auth is its own
// surface, off the nav.
const NAV: NavItem[] = [
  { label: "Personas", href: "#" },
  { label: "Product", href: "#" },
  { label: "Simulations", href: "#" },
  { label: "About", href: "#" },
];

// One minimal Provenance strip for the card — environment/build facts only.
// These are EXEMPT recorded facts (env, region, build id), so they print BARE
// with NO ± and NO ◇/◆ glyph (§1.10); `calibrated` is omitted so the bar shows
// no calibration segment — a sign-in screen has no inferred reading to grade.
const AUTH_PROV: ProvSeg[] = [
  { content: "SIDIRA INSTRUMENT" },
  { content: "PROD" },
  { content: "REGION us-east-1" },
  { content: "BUILD 2026.W25.3" },
];

export default function AuthV2Page() {
  return (
    <ConsoleShell>
      <TopBar
        nav={NAV}
        provenance={{ label: "SNAPSHOT 2026-W25", calibrated: false, live: false }}
      />

      {/* ── AUTH STAGE — one centered card on a brutally-quiet field ──────── */}
      <section className="v2-auth-stage">
        {/* a single, still ambient wash (no motion, no Population Field — auth
            is WORKING-class, §0.2). Token-driven radial behind the card. */}
        <div aria-hidden className="v2-auth-bg" />

        <Wrap style={{ position: "relative", zIndex: 1 }}>
          <div className="v2-auth-card v2-elevated">
            {/* ── card header: mono mark + a single eyebrow ─────────────── */}
            <div className="v2-auth-head">
              <span className="v2-auth-mark" aria-hidden>
                <ConsoleMarkMono size={34} />
              </span>
              <Designator>SIGN IN · SIDIRA CONSOLE</Designator>
              <h1 className="v2-auth-title">Open the instrument.</h1>
              <p className="v2-auth-sub">
                Sign in to your workspace to compose a hypothesis and read a
                synthetic cohort.
              </p>
            </div>

            {/* the interactive child — inert, no submit, no API */}
            <SignInForm />

            {/* ── create-account affordance ─────────────────────────────── */}
            <p className="v2-auth-foot">
              New to Sidira?{" "}
              <a href="#" className="v2-auth-link">
                Create an account
              </a>
            </p>
          </div>

          {/* one minimal provenance strip beneath the card (§7.3) */}
          <div className="v2-auth-prov">
            <ProvenanceBar segments={AUTH_PROV} />
          </div>
        </Wrap>
      </section>

      {/* page-local token-driven styling (no raw hex / no raw font names) */}
      <style>{AUTH_CSS}</style>
    </ConsoleShell>
  );
}

// ── page-local CSS — every value is a v2 CSS var or a plain unit (no hex,
//    no font names). Mirrors the HERO_GRID_CSS precedent in product/v2. ───────
const AUTH_CSS = `
.v2-auth-stage{
  position:relative;
  min-height:calc(100vh - 52px);
  display:flex;
  align-items:center;
  justify-content:center;
  overflow:hidden;
  padding:64px 0 96px;
}
.v2-auth-bg{
  position:absolute;
  inset:0;
  z-index:0;
  pointer-events:none;
  background:
    radial-gradient(60% 50% at 50% 30%, rgba(57,184,148,.06), transparent 62%),
    linear-gradient(180deg, var(--console-850) 0%, var(--console-900) 100%);
}
.v2-auth-card{
  position:relative;
  z-index:1;
  width:100%;
  max-width:412px;
  margin:0 auto;
  background:var(--console-800);
  border:1px solid var(--console-line-50);
  border-radius:var(--r-panel);
  padding:40px 36px 34px;
}
.v2-auth-head{
  margin-bottom:28px;
}
.v2-auth-mark{
  display:inline-flex;
  color:var(--text-hi);
  margin-bottom:20px;
}
.v2-auth-title{
  margin-top:14px;
  font-size:1.6rem;
  line-height:1.1;
  letter-spacing:-0.025em;
  font-weight:600;
  color:var(--text-hi);
  text-wrap:balance;
}
.v2-auth-sub{
  margin-top:10px;
  font-size:0.9375rem;
  line-height:1.55;
  color:var(--text-mut);
  max-width:34ch;
}
.v2-auth-label{
  font-size:0.8125rem;
  font-weight:450;
  color:var(--text-mut);
}
.v2-auth-input{
  width:100%;
  height:40px;
  padding:0 12px;
  border-radius:var(--r-well);
  background:var(--console-700);
  border:1px solid var(--console-line-50);
  color:var(--text-hi);
  font-family:var(--v2-font-sans);
  font-size:0.9375rem;
  line-height:1.4;
  transition:border-color .14s var(--ease-out), box-shadow .14s var(--ease-out);
}
.v2-auth-input::placeholder{
  color:var(--text-mut);
  opacity:.7;
}
.v2-auth-input:hover{
  border-color:var(--console-line-60);
}
.v2-auth-input:focus{
  outline:none;
  border-color:var(--signal-dim);
  box-shadow:0 0 0 2px var(--signal-wash);
}
.v2-auth-forgot{
  font-size:0.8125rem;
  color:var(--text-mut);
  transition:color .14s var(--ease-out);
}
.v2-auth-forgot:hover{
  color:var(--text-hi);
}
.v2-auth-submit{
  width:100%;
  margin-top:4px;
}
.v2-auth-or{
  display:flex;
  align-items:center;
  gap:12px;
  margin:2px 0;
}
.v2-auth-or-rule{
  flex:1;
  height:1px;
  background:var(--console-line-40);
}
.v2-auth-or-word{
  font-size:10px;
  letter-spacing:0.12em;
  color:var(--text-mut);
}
.v2-auth-sso{
  width:100%;
}
.v2-auth-foot{
  margin-top:26px;
  padding-top:22px;
  border-top:1px solid var(--console-line-40);
  text-align:center;
  font-size:0.875rem;
  color:var(--text-mut);
}
.v2-auth-link{
  color:var(--text-hi);
  font-weight:500;
  transition:color .14s var(--ease-out);
}
.v2-auth-link:hover{
  color:var(--signal-dim);
}
.v2-auth-prov{
  margin-top:24px;
  display:flex;
  justify-content:center;
}
@media(max-width:480px){
  .v2-auth-card{padding:32px 22px 28px;border-radius:var(--r-panel);}
  .v2-auth-stage{padding:32px 0 64px;}
}
`;
