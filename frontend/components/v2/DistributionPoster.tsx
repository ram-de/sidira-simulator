// ───────────────────────────────────────────────────────────────────────────
// DESIGN SYSTEM v2 — DistributionPoster (Tier-3 static SVG, §5.5 / §7.1).
// The frozen settled-distribution poster: the Population Field's value-series
// rendered as a real binned histogram, dodged by arm. Used on WORKING/RECORD
// pages (and as the field's reduced-motion fallback). NOT a live reading:
//   • the pooled-mean line uses --signal-dim, never bright --signal (P5)
//   • inferred means carry ◇/◆; recorded n prints bare (P8)
// Prop-driven so later pages feed it real per-arm bin counts.
// ───────────────────────────────────────────────────────────────────────────
"use client";

import { useId } from "react";
import { CalGlyph } from "./primitives";

export type Bar = { x: number; h: number };

export type DistributionPosterProps = {
  // Per-arm dodged bars: { x (px on a 0..360 viewBox), h (px height) }.
  controlBars: Bar[];
  treatBars: Bar[];
  // Mean line x-position (px) + per-arm mean tick positions.
  pooledMeanX: number;
  controlMeanX: number;
  treatMeanX: number;
  pooledMeanLabel: string; // e.g. "MEAN 0.62"
  calibrated?: boolean;
  // CI band rect on the viewBox.
  ci?: { x: number; width: number };
  // Caption line under the figure.
  footerNote: string; // e.g. "240 AGENTS · BINNED · BAR HEIGHT = AGENT COUNT"
  ariaLabel: string;
};

const BASELINE = 126;

export function DistributionPoster({
  controlBars,
  treatBars,
  pooledMeanX,
  controlMeanX,
  treatMeanX,
  pooledMeanLabel,
  calibrated = false,
  ci = { x: 124, width: 60 },
  footerNote,
  ariaLabel,
}: DistributionPosterProps) {
  const meanColor = calibrated ? "var(--signal)" : "var(--signal-dim)";
  // Unique gradient id per instance — two posters on one page must not collide
  // on a fixed `id` (the second would inherit the first's <defs>).
  const rawId = useId();
  const ciId = `v2-ci-${rawId.replace(/:/g, "")}`;
  return (
    <svg
      viewBox="0 0 360 168"
      role="img"
      aria-label={ariaLabel}
      style={{ display: "block", width: "100%", height: "auto" }}
    >
      <defs>
        <linearGradient id={ciId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--spread)" stopOpacity="0.14" />
          <stop offset="1" stopColor="var(--spread)" stopOpacity="0.015" />
        </linearGradient>
      </defs>

      {/* CI band behind the bars (spread) */}
      <rect x={ci.x} y={22} width={ci.width} height={104} fill={`url(#${ciId})`} />

      {/* baseline axis: rejects ← reaction → adopts */}
      <line x1={16} y1={BASELINE} x2={344} y2={BASELINE} stroke="var(--console-line)" strokeWidth={1} />
      {[16, 98, 180, 262, 344].map((tx, i) => (
        <line
          key={tx}
          x1={tx}
          y1={BASELINE}
          x2={tx}
          y2={i % 2 === 0 ? BASELINE + 4 : BASELINE + 3}
          stroke="var(--console-line)"
          strokeWidth={1}
        />
      ))}

      {/* histogram bars — dodged by arm, height = agents in bin */}
      <g fill="var(--arm-control)" fillOpacity={0.82}>
        {controlBars.map((b, i) => (
          <rect key={i} x={b.x} y={BASELINE - b.h} width={7} height={b.h} />
        ))}
      </g>
      <g fill="var(--arm-treat)" fillOpacity={0.82}>
        {treatBars.map((b, i) => (
          <rect key={i} x={b.x} y={BASELINE - b.h} width={7} height={b.h} />
        ))}
      </g>

      {/* per-arm mean ticks (thin, dashed, arm-tinted) */}
      <line x1={controlMeanX} y1={34} x2={controlMeanX} y2={BASELINE} stroke="var(--arm-control)" strokeWidth={1} strokeDasharray="1.5 2.5" opacity={0.65} />
      <line x1={treatMeanX} y1={34} x2={treatMeanX} y2={BASELINE} stroke="var(--arm-treat)" strokeWidth={1} strokeDasharray="1.5 2.5" opacity={0.65} />

      {/* pooled mean — frozen poster → signal-dim (P5); carries ◇/◆ (P8) */}
      <line x1={pooledMeanX} y1={18} x2={pooledMeanX} y2={BASELINE} stroke={meanColor} strokeWidth={1.4} />
      <circle cx={pooledMeanX} cy={22} r={2.6} fill={meanColor} />
      <text x={pooledMeanX} y={13} textAnchor="middle" fontFamily="Geist Mono" fontSize={9} fill={meanColor}>
        {pooledMeanLabel} <tspan fill={calibrated ? "var(--signal-dim)" : "var(--spread-dim)"}>{calibrated ? "◆" : "◇"}</tspan>
      </text>

      {/* axis labels on their own baseline (no crowding) */}
      <text x={16} y={150} fontFamily="Geist Mono" fontSize={8.5} letterSpacing={0.5} fill="var(--text-mut)">REJECTS</text>
      <text x={180} y={150} textAnchor="middle" fontFamily="Geist Mono" fontSize={8} letterSpacing={0.5} fill="var(--text-mut)">reaction →</text>
      <text x={344} y={150} textAnchor="end" fontFamily="Geist Mono" fontSize={8.5} letterSpacing={0.5} fill="var(--text-mut)">ADOPTS</text>
      <text x={180} y={164} textAnchor="middle" fontFamily="Geist Mono" fontSize={7.5} letterSpacing={0.4} fill="var(--text-mut)">{footerNote}</text>
    </svg>
  );
}

// A compact figure header: the marquee inferred reading (number + ± + glyph)
// plus a hedged verdict tag — the page's focal climax (P10).
export function PosterFigure({
  value,
  ci,
  calibrated = false,
  verdict,
}: {
  value: string;
  ci: string;
  calibrated?: boolean;
  verdict: string;
}) {
  return (
    <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
      <span
        className="v2-mono v2-tnum"
        style={{ fontWeight: 500, fontSize: "3.1rem", lineHeight: 0.92, color: "var(--text-hi)", letterSpacing: "-0.02em" }}
      >
        {value}
      </span>
      <span className="v2-mono v2-tnum" style={{ fontSize: "1.05rem", color: "var(--spread)" }}>
        {ci}
      </span>
      <span style={{ color: "var(--spread-dim)", fontSize: "1.2rem", alignSelf: "center" }}>
        {calibrated ? "◆" : "◇"}
      </span>
      <span
        className="v2-mono"
        style={{ marginLeft: "auto", alignSelf: "center", fontSize: 11, letterSpacing: "0.06em", color: "var(--text-mut)" }}
      >
        {verdict} <CalGlyph graded={calibrated} />
      </span>
    </div>
  );
}
