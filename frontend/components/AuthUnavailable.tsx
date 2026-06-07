import { TOKENS, FONT_NARROW } from "@/lib/design";

// Rendered on the auth pages when Clerk is not configured (no publishable key).
// Keeps the build green and gives a clear message instead of a thrown Clerk
// component during SSR/prerender. The temporary Basic-Auth gate (middleware)
// still guards the app host in this mode, so these pages are not the entry path.
export default function AuthUnavailable() {
  return (
    <div
      style={{
        maxWidth: 420,
        border: `0.75px solid ${TOKENS.rule}`,
        background: TOKENS.paperElevated,
        borderRadius: 4,
        padding: "32px 28px",
        textAlign: "center",
      }}
    >
      <h1
        style={{
          margin: "0 0 12px",
          fontFamily: FONT_NARROW,
          fontSize: 15,
          fontWeight: 600,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: TOKENS.ink,
        }}
      >
        Authentication not configured
      </h1>
      <p style={{ margin: 0, fontSize: 14, lineHeight: 1.5, color: TOKENS.inkMuted }}>
        Sign-in is unavailable in this environment. Set
        {" "}
        <code>NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY</code> to enable Clerk.
      </p>
    </div>
  );
}
