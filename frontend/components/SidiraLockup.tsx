import { FONT_NARROW } from "@/lib/design";

// Primary horizontal lockup — mark + SIDIRA wordmark. Geometry matches
// frontend/public/brand/sidira-lockup.svg per DESIGN.md §3.1.
// Inline SVG so stroke/text inherit currentColor without a network round-trip.
export default function SidiraLockup({ height = 32 }: { height?: number }) {
  return (
    <svg
      width={(height / 60) * 240}
      height={height}
      viewBox="0 0 240 60"
      fill="none"
      aria-label="Sidira"
      style={{ display: "block" }}
    >
      <g
        transform="translate(0 5) scale(0.5)"
        stroke="currentColor"
        strokeWidth={2.2}
        strokeLinejoin="round"
        fill="none"
      >
        <polygon points="84.641,70 50,90 50,63 61.260,56.5" />
        <polygon points="50,90 15.359,70 38.740,56.5 50,63" />
        <polygon points="15.359,70 15.359,30 38.740,43.5 38.740,56.5" />
        <polygon points="15.359,30 50,10 50,37 38.740,43.5" />
        <polygon points="50,10 84.641,30 61.260,43.5 50,37" />
        <polygon points="84.641,30 84.641,70 61.260,56.5 61.260,43.5" />
      </g>
      <text
        x={64}
        y={44}
        fontFamily={FONT_NARROW}
        fontWeight={600}
        fontSize={44}
        letterSpacing={2.6}
        fill="currentColor"
      >
        SIDIRA
      </text>
    </svg>
  );
}
