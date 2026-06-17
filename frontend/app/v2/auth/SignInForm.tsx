// ───────────────────────────────────────────────────────────────────────────
// /v2/auth — sign-in form (the one interactive child of the static auth mock).
//
// STATIC MOCK ONLY. This is a design preview: the inputs are real focusable
// fields so the Console input states (§4.2/§4.11) read true, but the form never
// submits and never calls an API — onSubmit is prevented, the button is inert.
// It consumes ONLY components/v2 + the scoped v2-theme.css classes; no raw hex,
// no raw font names (every token is a CSS var or a lib/design-v2 export).
// ───────────────────────────────────────────────────────────────────────────
"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/v2";

export function SignInForm() {
  // Local-only state so the inputs are genuinely interactive in the preview;
  // nothing leaves the component, nothing is submitted.
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // Inert: the mock never authenticates. Prevent the default so no navigation
  // or network request ever fires.
  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
  }

  return (
    <form onSubmit={onSubmit} noValidate style={{ display: "grid", gap: 18 }}>
      <Field
        id="v2-auth-email"
        label="Work email"
        type="email"
        autoComplete="email"
        placeholder="you@company.com"
        value={email}
        onChange={setEmail}
      />

      <div style={{ display: "grid", gap: 8 }}>
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            justifyContent: "space-between",
            gap: 12,
          }}
        >
          <label htmlFor="v2-auth-password" className="v2-auth-label">
            Password
          </label>
          {/* secondary, low-emphasis recovery affordance — ink, never signal */}
          <a href="#" className="v2-auth-forgot">
            Forgot password?
          </a>
        </div>
        <Field
          id="v2-auth-password"
          type="password"
          autoComplete="current-password"
          placeholder="••••••••••••"
          value={password}
          onChange={setPassword}
          bare
        />
      </div>

      {/* type="submit" is forwarded via the Button's rest props (it reads
          btnRest.type at runtime); the prop bag below keeps it type-safe. */}
      <Button
        as="button"
        variant="primary"
        hero
        className="v2-auth-submit"
        {...({ type: "submit" } as { type: "submit" })}
      >
        Sign in
      </Button>

      {/* SSO — a single secondary affordance; inert link, ink hairline */}
      <div className="v2-auth-or" aria-hidden>
        <span className="v2-auth-or-rule" />
        <span className="v2-mono v2-auth-or-word">OR</span>
        <span className="v2-auth-or-rule" />
      </div>
      <Button as="a" href="#" variant="secondary" hero className="v2-auth-sso">
        <SsoGlyph /> Continue with SSO
      </Button>
    </form>
  );
}

// ── a single labelled Console input (§4.2). `bare` skips the inline label so a
//    caller can render the label + an adjacent affordance on its own row. ──────
function Field({
  id,
  label,
  type,
  autoComplete,
  placeholder,
  value,
  onChange,
  bare = false,
}: {
  id: string;
  label?: string;
  type: string;
  autoComplete: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
  bare?: boolean;
}) {
  return (
    <div style={{ display: "grid", gap: 8 }}>
      {!bare && label ? (
        <label htmlFor={id} className="v2-auth-label">
          {label}
        </label>
      ) : null}
      <input
        id={id}
        className="v2-auth-input"
        type={type}
        autoComplete={autoComplete}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        spellCheck={false}
      />
    </div>
  );
}

// minimal SSO key glyph — currentColor stroke so it inherits the button ink.
function SsoGlyph() {
  return (
    <svg
      viewBox="0 0 24 24"
      width={15}
      height={15}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      style={{ display: "block", opacity: 0.85 }}
    >
      <circle cx="8" cy="8" r="4.5" />
      <path d="M11 11l8 8M16 16l2.5-2.5M19 19l2-2" />
    </svg>
  );
}
