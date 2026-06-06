// Design system tokens — DESIGN.md §4. Update both this file and DESIGN.md
// together if values change.
export const TOKENS = {
  ink: "#0E1A2B",
  inkMuted: "#4A5668",
  paper: "#F4EFE6",
  paperElevated: "#FAF6EE",
  paperRecessed: "#EBE5D8",
  rule: "#D6CFC0",
  signal: "#C8FF3D",
  avira: "#D696C8",
  alert: "#E84A2C",
  warn: "#D9A300",
} as const;

export const FONT_SANS = "var(--font-sans), ui-sans-serif, sans-serif";
export const FONT_NARROW = "var(--font-narrow), sans-serif";
export const FONT_SERIF = "var(--font-serif), Georgia, serif";
export const FONT_MONO = "var(--font-mono), ui-monospace, monospace";

// fontFeatureSettings for tabular numerals — apply to all scores, CIs,
// timestamps, deltas, cohort sizes per DESIGN.md §5.3.
export const TNUM: React.CSSProperties = {
  fontVariantNumeric: "tabular-nums",
  fontFeatureSettings: '"tnum" on',
};
