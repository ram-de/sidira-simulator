// Design system tokens — DESIGN.md §4. Update both this file and DESIGN.md
// together if values change.
export const TOKENS = {
  ink: "#0E1A2B",
  inkMuted: "#4A5668",
  paper: "#F4EFE6",
  paperElevated: "#FAF6EE",
  paperRecessed: "#EBE5D8",
  rule: "rgba(14, 26, 43, 0.16)",
  signal: "#C8FF3D",
  avira: "#D696C8",
  alert: "#E84A2C",
  warn: "#D9A300",
  success: "#2F6B3F",
  // Glass — the instrument display (DESIGN.md §4.2). Live computed readings
  // ONLY: never chrome, nav, tables, text content, or marketing.
  glass: "#0A1421",
  glassRule: "rgba(244, 239, 230, 0.08)",
  glassText: "#F4EFE6",
  glassMuted: "rgba(244, 239, 230, 0.55)",
} as const;

// Duo-mark scope ONLY — DESIGN.md §4.4/§9.2. Sid-blue is not a system token;
// these exist so aperture keyframes and the duo lockup never hardcode hexes.
export const DUO_SID = "#2C5577";
export const DUO_AVIRA = TOKENS.avira;

export const FONT_SANS = "var(--font-sans), ui-sans-serif, sans-serif";
export const FONT_NARROW = "var(--font-narrow), sans-serif";
export const FONT_MONO = "var(--font-mono), ui-monospace, monospace";

// Motion curves — DESIGN.md §9.3. Mechanical curve for telemetry wipes and
// tab underlines; settle curve for the aperture-close commit beat (800ms).
export const EASE_MECH = "cubic-bezier(0.32, 0.72, 0, 1)";
export const EASE_SETTLE = "cubic-bezier(0.34, 1.1, 0.64, 1)";

// fontFeatureSettings for tabular numerals — apply to all scores, CIs,
// timestamps, deltas, cohort sizes per DESIGN.md §5.3.
export const TNUM: { fontVariantNumeric: string; fontFeatureSettings: string } = {
  fontVariantNumeric: "tabular-nums",
  fontFeatureSettings: '"tnum" on',
};
