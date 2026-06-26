// ───────────────────────────────────────────────────────────────────────────
// DESIGN SYSTEM v2 — shared primitives (Console mode).
// Prop-driven, reusable atoms that consume the scoped v2-theme.css classes.
// Later v2 pages import from here; do NOT re-inline tokens in pages.
// ───────────────────────────────────────────────────────────────────────────
import type { ReactNode } from "react";

type Cx = string | false | null | undefined;
function cx(...parts: Cx[]): string {
  return parts.filter(Boolean).join(" ");
}

// ── Designator — mono UPPERCASE machine identifier / eyebrow (§2.3) ────────
export function Designator({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <span className={cx("v2-desig", className)}>{children}</span>;
}

// ── Chip — bordered designator (§4.8) ──────────────────────────────────────
export function Chip({ children }: { children: ReactNode }) {
  return <span className="v2-chip">{children}</span>;
}

// ── Calibration glyphs — ◇ uncalibrated (spread-dim) / ◆ graded (signal-dim)
export function CalGlyph({ graded = false }: { graded?: boolean }) {
  return graded ? (
    <span className="v2-gf">◆</span>
  ) : (
    <span className="v2-gh">◇</span>
  );
}

// ── Status badge — border + word only, never a filled pill (§4.8) ──────────
type BadgeKind = "live" | "hold" | "failed" | "neutral";
export function StatusBadge({
  kind = "neutral",
  children,
}: {
  kind?: BadgeKind;
  children: ReactNode;
}) {
  return (
    <span className={cx("v2-badge", kind !== "neutral" && `v2-badge--${kind}`)}>
      {children}
    </span>
  );
}

// ── Status dot — resting ink by default; live = breathing signal (§5.4) ────
export function StatusDot({ live = false }: { live?: boolean }) {
  return <span className={cx("v2-dot", live && "v2-dot--live")} aria-hidden />;
}

// ── Button — variant-driven (§4.1) ─────────────────────────────────────────
// `live` is the ONE variant that may carry signal; reserve it for controls
// that initiate a live reading (Run / Read now), per the signal budget (P2).
type ButtonVariant =
  | "primary"
  | "live"
  | "secondary"
  | "ghost"
  | "destructive";

export function Button({
  as = "button",
  variant = "primary",
  hero = false,
  href,
  children,
  className,
  ...rest
}: {
  as?: "button" | "a";
  variant?: ButtonVariant;
  hero?: boolean;
  href?: string;
  children: ReactNode;
  className?: string;
  // Accept the native button attributes (e.g. `disabled`, `type`) and anchor
  // attributes (e.g. `target`) — both are spread onto the rendered element
  // below. `disabled` drives the §7.7 honest disabled state via `.v2-btn:disabled`.
} & React.ButtonHTMLAttributes<HTMLButtonElement> &
  React.AnchorHTMLAttributes<HTMLAnchorElement>) {
  const cls = cx(
    "v2-btn",
    `v2-btn--${variant}`,
    hero && "v2-btn--hero",
    className,
  );
  if (as === "a") {
    return (
      <a className={cls} href={href} {...rest}>
        {children}
      </a>
    );
  }
  // Default to type="button" so a Button inside a <form> never submits it by
  // accident; callers that want a submit/reset button pass `type` explicitly.
  const btnRest = rest as React.ButtonHTMLAttributes<HTMLButtonElement>;
  return (
    <button className={cls} type={btnRest.type ?? "button"} {...btnRest}>
      {children}
    </button>
  );
}

// ── Panel — the card/panel surface (§4.4). Never nest panels. ──────────────
export function Panel({
  elevated = true,
  className,
  children,
  ...rest
}: {
  elevated?: boolean;
  className?: string;
  children: ReactNode;
} & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cx("v2-panel", elevated && "v2-elevated", className)}
      {...rest}
    >
      {children}
    </div>
  );
}
