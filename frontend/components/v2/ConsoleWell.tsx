// ───────────────────────────────────────────────────────────────────────────
// DESIGN SYSTEM v2 — ConsoleWell (§6.4) — a self-contained dark instrument inset.
// The reusable wrapper for embedding a Console (dark) instrument inside a Sheet
// (light) RECORD without inverting the route. It applies `.v2-well` (the dark
// surface frame) AND `.v2-console-scope` (a COMPLETE re-declaration of every
// Console token the well's contents need — text, signal, spread, arm, the
// console-line alphas incl. --console-line-45 that ProvenanceBar reads — so the
// instrument renders correctly regardless of the surrounding scope, never
// relying on a token leaking in from `.v2-sheet`). Both classes live in
// v2-theme.css; no raw color literal is inlined here.
//
// CRITICAL route-mode law (§6.4): a ProvenanceBar rendered inside the well stays
// CONSOLE-styled (it reads --text-mut / --text / --console-line-45 from this
// scope), NOT recolored to Sheet. Compose the bar as a child and it inherits the
// dark scope correctly.
// ───────────────────────────────────────────────────────────────────────────
import type { CSSProperties, ReactNode } from "react";

export function ConsoleWell({
  children,
  className,
  style,
  role,
  "aria-label": ariaLabel,
}: {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  role?: string;
  "aria-label"?: string;
}) {
  return (
    <div
      className={["v2-well", "v2-console-scope", className]
        .filter(Boolean)
        .join(" ")}
      role={role}
      aria-label={ariaLabel}
      style={style}
    >
      {children}
    </div>
  );
}
