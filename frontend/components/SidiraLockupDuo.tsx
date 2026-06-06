import { TOKENS, FONT_NARROW } from "@/lib/design";

// Dual-color aperture lockup — Sid-blue left blades, Avira-rose right blades.
// Per DESIGN.md §4.4: use only on public/brand surfaces (homepage, /about, press).
// Never in the product nav, favicon, or in-app UI.
export default function SidiraLockupDuo({ height = 36 }: { height?: number }) {
  return (
    <svg
      width={(height / 60) * 240}
      height={height}
      viewBox="0 0 240 60"
      fill="none"
      role="img"
      aria-label="Sidira"
      style={{ display: "block" }}
    >
      <g transform="translate(0 5) scale(0.5)" strokeWidth={2.2} strokeLinejoin="round" fill="none">
        <g stroke="#2C5577">
          <polygon points="50,90 15.359,70 38.740,56.5 50,63" />
          <polygon points="15.359,70 15.359,30 38.740,43.5 38.740,56.5" />
          <polygon points="15.359,30 50,10 50,37 38.740,43.5" />
        </g>
        <g stroke="#D696C8">
          <polygon points="84.641,70 50,90 50,63 61.260,56.5" />
          <polygon points="50,10 84.641,30 61.260,43.5 50,37" />
          <polygon points="84.641,30 84.641,70 61.260,56.5 61.260,43.5" />
        </g>
      </g>
      <text
        x={64}
        y={44}
        fontFamily={FONT_NARROW}
        fontWeight={600}
        fontSize={44}
        letterSpacing={2.6}
        fill={TOKENS.ink}
      >
        SIDIRA
      </text>
    </svg>
  );
}
