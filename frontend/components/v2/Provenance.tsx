// ───────────────────────────────────────────────────────────────────────────
// DESIGN SYSTEM v2 — Provenance Bar + compact global marker (§6, §7.3).
// One mono silkscreen strip per live reading region. Segments are pipe/border
// separated. EXEMPT facts (n, seed, model, snapshot) print BARE; the region's
// calibration state is carried ONCE here via the ◇/◆ marker (P8).
// ───────────────────────────────────────────────────────────────────────────
import type { CSSProperties, ReactNode } from "react";
import { CalGlyph, StatusDot } from "./primitives";

// A segment in a provenance bar. `bold` lifts a recorded fact to --text.
export type ProvSeg = { content: ReactNode; bold?: boolean };

const segBase: CSSProperties = {
  padding: "0 9px",
  borderLeft: "1px solid var(--console-line-45)",
};

// Provenance Bar — the region silkscreen (§7.3). `calibrated` toggles ◇/◆;
// pass `calibrated={undefined}` to omit the calibration segment entirely.
export function ProvenanceBar({
  segments,
  calibrated,
  align = "start",
  style,
}: {
  segments: ProvSeg[];
  calibrated?: boolean;
  align?: "start" | "end";
  style?: CSSProperties;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        flexWrap: "wrap",
        fontFamily: "var(--v2-font-mono)",
        fontSize: 10.5,
        letterSpacing: "0.04em",
        color: "var(--text-mut)",
        ...style,
      }}
    >
      {segments.map((seg, i) => (
        <span
          key={i}
          style={{
            ...segBase,
            ...(i === 0 ? { paddingLeft: 0, borderLeft: "none" } : null),
          }}
        >
          {seg.bold ? (
            <b style={{ color: "var(--text)", fontWeight: 500 }}>
              {seg.content}
            </b>
          ) : (
            seg.content
          )}
        </span>
      ))}
      {calibrated !== undefined ? (
        <span
          style={{
            ...segBase,
            borderLeft: "none",
            ...(align === "end" ? { marginLeft: "auto" } : null),
            color: "var(--text-mut)",
          }}
        >
          <CalGlyph graded={calibrated} />{" "}
          {calibrated ? "GRADED" : "UNCALIBRATED"}
        </span>
      ) : null}
    </div>
  );
}

// Compact global provenance reference for the top bar (§4.5). A single
// reference (snapshot + calibration marker), NOT a second full legend.
export type ProvenanceMarkerProps = {
  label: ReactNode;
  calibrated?: boolean;
  live?: boolean;
};

export function ProvenanceMarker({
  label,
  calibrated = false,
  live = false,
}: ProvenanceMarkerProps) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        fontFamily: "var(--v2-font-mono)",
        fontSize: 10.5,
        letterSpacing: "0.05em",
        color: "var(--text-mut)",
      }}
    >
      <StatusDot live={live} />
      <span>
        {label} <CalGlyph graded={calibrated} />{" "}
        {calibrated ? "GRADED" : "UNCAL"}
      </span>
    </div>
  );
}
