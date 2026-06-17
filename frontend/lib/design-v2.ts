// ───────────────────────────────────────────────────────────────────────────
// SIDIRA — DESIGN SYSTEM v2 · "THE READING CONSOLE" — shared token layer
//
// Canonical source: design-rethink/system/design-system-v2.md (+ v2.1-patch.md).
// This is the v2 equivalent of lib/design.ts — TypeScript constants for the
// Console/Sheet palettes, ink pairs, accents, type scale, spacing, and radius.
//
// The CSS custom properties that consume these tokens live in a SCOPED
// stylesheet (styles/v2-theme.css, applied only under `.v2-console`),
// so the v2 system never pollutes the live app's global "paper" theme. Import
// from THIS file (or the scoped CSS vars) — never re-inline a raw v2 hex.
//
// Every text/bg pair below clears AA per the spec; values marked [v2-fix] were
// corrected in v2. Hex is the sRGB rounding of the authored OKLCH (§1).
// ───────────────────────────────────────────────────────────────────────────

// ── §1.1 Console — dark instrument body (primary) ──────────────────────────
export const CONSOLE = {
  c900: "#0B1220", // deepest well — glass behind live readings
  c850: "#10192A", // app canvas / hero background
  c800: "#161F32", // raised panels, nav, cards
  c750: "#1D2740", // hover / pressed panel
  c700: "#26314C", // input wells, recessed controls
  line: "#33405C", // hairline rules — render at 1px, alpha 0.5
} as const;

// ── §1.2 Ink on Console (every label/body pair passes AA) ──────────────────
export const INK = {
  hi: "#F2F4F8", // primary text, headlines
  base: "#C6CCD8", // body
  mut: "#929BAE", // captions, axis labels, provenance [v2-fix]
  faint: "#646E84", // DISABLED CONTROLS ONLY — never a label/caption [v2-fix]
} as const;

// ── §1.3 Signal — the one saturated accent (LIVE READING ONLY) ─────────────
export const SIGNAL = {
  base: "#48EFCA", // live traces, the running pulse, active live control
  dim: "#39B894", // settled/resting signal, secondary trace, hover-rest
  wash: "rgba(72,239,202,0.12)", // trace underdraw/fill — never blur/glow
} as const;

// ── §1.4 Spread — doubt as a first-class color (inferred CIs only) ─────────
export const SPREAD = {
  base: "#C8B68A", // CI bands, error-bar caps, "estimate" hatching
  dim: "#90815F", // ungraded/placeholder designator text + ◇ glyph
  wash: "rgba(200,182,138,0.14)", // CI ribbon fill on the field
} as const;

// ── §1.5 Arm tints — A/B identity (provenance, NEVER valence) ──────────────
export const ARM = {
  control: "#4FA8E0", // Control arm · "Sid" pole · steady blue
  treat: "#E08BC4", // Treatment arm · "Avira" pole · calm magenta [v2-fix]
} as const;

// Series ramp (≥3 cohorts) — interpolate the two poles, never a rainbow.
export const ARM_RAMP = [
  "#4FA8E0",
  "#7C9ECF",
  "#A797C9",
  "#C28FC6",
  "#E08BC4",
] as const;

// ── §1.6 Semantic — borders + word only, NEVER fill ────────────────────────
export const SEMANTIC = {
  warn: "#C9A227", // caution border (uncalibrated, low-stability)
  alert: "#F0683C", // hard failures only — 1px border + word, never a banner
} as const;
// NOTE: there is no verdict-ship / verdict-hold token. A verdict is not a color.

// ── §1.7 Sheet — light blueprint record (long-form only) ───────────────────
export const SHEET = {
  base: "#F3F4F7", // reading surface (cool, not cream)
  raised: "#FBFBFD", // sheet cards, modals
  sunk: "#E6E8EE", // inputs, code wells on sheet
  line: "#D4D8E0", // hairlines on sheet (0.75px)
  ink: "#1A2336", // body ink on sheet
  mut: "#5E6678", // muted on sheet
  signal: "#00785F", // signal-as-TEXT on sheet (4.8:1) [v2-fix]
  spread: "#6F5E33", // spread-as-TEXT on sheet (5.6:1) [v2-fix]
} as const;

// ── §2.1 Type families ─────────────────────────────────────────────────────
// Geist (display/body/UI) · Geist Mono (data/numerals) · Newsreader (Sheet prose).
// These resolve to scoped CSS vars set in v2-theme.css; the literal fallbacks
// keep them usable inline before the scoped stylesheet's @import resolves.
export const FONT_V2_SANS =
  'var(--v2-font-sans, "Geist", system-ui, sans-serif)';
export const FONT_V2_MONO =
  'var(--v2-font-mono, "Geist Mono", ui-monospace, monospace)';
export const FONT_V2_SERIF =
  'var(--v2-font-serif, "Newsreader", Georgia, serif)';

// ── §2.2 Type scale (modular ≈ 1.25; tabular numerals on every numeric) ────
// size / line-height / tracking / weight — values lifted verbatim from the spec.
export const TYPE = {
  displayXl: {
    fontSize: "clamp(2.6rem, 6vw, 5.5rem)",
    lineHeight: 0.98,
    letterSpacing: "-0.035em",
    fontWeight: 700,
  },
  displayL: {
    fontSize: "3.25rem",
    lineHeight: 1.02,
    letterSpacing: "-0.03em",
    fontWeight: 600,
  },
  h1: {
    fontSize: "2.0rem",
    lineHeight: 1.08,
    letterSpacing: "-0.025em",
    fontWeight: 600,
  },
  h2: {
    fontSize: "1.5rem",
    lineHeight: 1.12,
    letterSpacing: "-0.02em",
    fontWeight: 600,
  },
  h3: {
    fontSize: "1.125rem",
    lineHeight: 1.2,
    letterSpacing: "-0.01em",
    fontWeight: 550,
  },
  lede: {
    fontSize: "1.375rem",
    lineHeight: 1.5,
    letterSpacing: "-0.005em",
    fontWeight: 400,
  },
  prose: { fontSize: "1.0625rem", lineHeight: 1.65, letterSpacing: "0", fontWeight: 400 },
  bodyL: { fontSize: "1.0625rem", lineHeight: 1.6, letterSpacing: "0", fontWeight: 450 },
  body: { fontSize: "0.9375rem", lineHeight: 1.55, letterSpacing: "0", fontWeight: 400 },
  caption: { fontSize: "0.8125rem", lineHeight: 1.4, letterSpacing: "0", fontWeight: 400 },
  monoData: { fontSize: "0.875rem", lineHeight: 1.3, letterSpacing: "0", fontWeight: 400 },
  dataLg: { fontSize: "2rem", lineHeight: 1.0, letterSpacing: "0", fontWeight: 500 },
  dataXl: {
    fontSize: "clamp(3rem, 7vw, 5rem)",
    lineHeight: 1.0,
    letterSpacing: "-0.01em",
    fontWeight: 500,
  },
  designator: {
    fontSize: "0.6875rem",
    lineHeight: 1.2,
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    fontWeight: 500,
  },
} as const;

// ── §3.1 Spacing scale (4px base, geometric) ───────────────────────────────
export const SPACE = {
  hairline: 2, // between a number and its ± stamp
  tight: 4, // chip internal, glyph gaps
  snug: 8, // table row padding, dense control gaps
  cozy: 12, // input padding
  base: 16, // default panel padding, control gaps
  room: 24, // card padding, between stacked controls
  section: 48, // between WORKING regions
  bay: 64, // between major Console regions
  rest: 96, // Sheet between-section
  vast: 128, // Sheet chapter breaks, hero top/bottom
} as const;

// ── §3.4 Radius — one family ───────────────────────────────────────────────
export const RADIUS = {
  well: 4, // inputs, chips, wells, code blocks
  panel: 8, // panels, cards, modals
  frame: 10, // the hero console frame, the scope display well
  dot: 9999, // only the live status dot
} as const;

// ── §5.2 Easings (only these) ──────────────────────────────────────────────
export const EASE = {
  out: "cubic-bezier(0.22, 1, 0.36, 1)", // reveals, modal enter, default UI
  settle: "cubic-bezier(0.16, 1, 0.3, 1)", // the long convergence / settle
  mech: "cubic-bezier(0.32, 0.72, 0, 1)", // telemetry wipes, tab underline, trace
} as const;

// ── §2.2 Tabular-numeral helper — apply to every numeric/mono element ──────
export const TNUM_V2: { fontVariantNumeric: string; fontFeatureSettings: string } = {
  fontVariantNumeric: "tabular-nums",
  fontFeatureSettings: '"tnum" on',
};

// Convenience: the Google Fonts URL the scoped stylesheet imports (§2.1).
export const V2_FONTS_HREF =
  "https://fonts.googleapis.com/css2?family=Geist:wght@400;450;500;600;700&family=Geist+Mono:wght@400;500&family=Newsreader:ital,opsz,wght@0,6..72,400;1,6..72,400&display=swap";
