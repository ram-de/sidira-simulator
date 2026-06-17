// ───────────────────────────────────────────────────────────────────────────
// /about/v2 — THE ONE §6.4 Console well embedded in the Sheet.
// A frozen reading specimen: a small `--console-900` instrument inset into the
// light record. It re-asserts `.v2-console` LOCALLY (via the page CSS scope on
// `.v2-well`) so the dark tokens resolve, but the route stays Sheet — no
// masthead inversion, and the provenance inside the well is NOT recolored to
// Sheet (route-mode law, §6.4). Static SVG histogram — no canvas, no drift.
// ───────────────────────────────────────────────────────────────────────────
import { ProvenanceBar, ConsoleWell } from "@/components/v2";

export function SpecimenWell() {
  return (
    <div style={{ marginTop: 36 }}>
      <div
        style={{
          fontFamily: "var(--v2-font-mono)",
          fontSize: 10,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: "var(--sheet-mut)",
          marginBottom: 10,
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <span>Specimen · one settled reading</span>
        <span style={{ flex: 1, height: "0.75px", background: "var(--sheet-line)" }} />
      </div>

      {/* ConsoleWell establishes a complete, self-contained dark Console token
          scope (incl. --console-line-45 for the ProvenanceBar) — see v2-theme.css. */}
      <ConsoleWell
        role="figure"
        aria-label="A frozen Sidira reading: net adoption lift +0.041 ±0.012, uncalibrated. Two paired distributions — control in blue, treatment shifted right in magenta — over a reaction axis from rejects to adopts."
      >
        {/* Provenance Bar — the region silkscreen; candor-exempt facts print bare */}
        <div
          style={{
            padding: "9px 16px",
            borderBottom: "1px solid var(--console-line)",
            background: "rgba(11,18,32,.5)",
          }}
        >
          <ProvenanceBar
            calibrated={false}
            segments={[
              { content: <span style={{ color: "var(--signal-dim)" }}>CH1 · TREATMENT</span> },
              { content: "n=1,200" },
              { content: "seed 0x4f" },
              { content: "groq/llama-3.3" },
              { content: "2026-W25" },
            ]}
          />
        </div>

        <div className="v2-well-body">
          <div style={{ minWidth: 0 }}>
            <span
              style={{
                fontFamily: "var(--v2-font-mono)",
                fontSize: 10,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                color: "var(--text-mut)",
              }}
            >
              Net adoption lift · treatment vs. control
            </span>
            <div
              className="v2-tnum"
              style={{
                fontFamily: "var(--v2-font-mono)",
                fontWeight: 500,
                fontSize: "2.7rem",
                lineHeight: 1,
                color: "var(--text-hi)",
                letterSpacing: "-0.01em",
                marginTop: 8,
              }}
            >
              +0.041
              <span style={{ fontSize: "0.40em", color: "var(--spread)", verticalAlign: "0.55em", marginLeft: 4 }}>
                ±0.012
              </span>
              <span style={{ color: "var(--spread-dim)", fontSize: "0.36em", verticalAlign: "0.7em", marginLeft: 6 }}>
                ◇
              </span>
            </div>
            <p style={{ marginTop: 10, fontSize: 13, lineHeight: 1.5, color: "var(--text)", maxWidth: "34ch" }}>
              The cohort settled into a distribution shifted right of control. A directional read,
              not a graded verdict.
            </p>
            <span
              style={{
                marginTop: 14,
                display: "inline-flex",
                alignItems: "center",
                gap: 7,
                fontFamily: "var(--v2-font-mono)",
                fontSize: 11,
                letterSpacing: "0.04em",
                color: "var(--spread)",
              }}
            >
              <span style={{ color: "var(--spread-dim)" }}>◇</span>
              DIRECTIONAL · read alongside sentiment
            </span>
          </div>

          {/* The frozen distribution poster — a genuinely binned histogram. */}
          <div style={{ height: 158, position: "relative" }}>
            <SpecimenSvg />
          </div>
        </div>

        <div style={{ padding: "0 22px 16px" }}>
          <div
            style={{
              marginTop: 14,
              paddingTop: 12,
              borderTop: "1px solid var(--console-line)",
              display: "flex",
              justifyContent: "space-between",
              fontFamily: "var(--v2-font-mono)",
              fontSize: 10.5,
              color: "var(--text-mut)",
              letterSpacing: "0.02em",
            }}
          >
            <span>
              <ArmDot kind="ctl" />
              CONTROL · 600
            </span>
            <span>
              TREATMENT · 600
              <ArmDot kind="trt" />
            </span>
          </div>
        </div>
      </ConsoleWell>

      <p
        style={{
          marginTop: 10,
          fontSize: 12,
          color: "var(--sheet-mut)",
          fontFamily: "var(--v2-font-sans)",
          maxWidth: "60ch",
        }}
      >
        A frozen specimen of a live reading, the kind the product renders in motion. On this record
        it sits still: a printed figure, not a running field.
      </p>
    </div>
  );
}

function ArmDot({ kind }: { kind: "ctl" | "trt" }) {
  return (
    <span
      aria-hidden
      style={{
        width: 7,
        height: 7,
        borderRadius: 9999,
        display: "inline-block",
        verticalAlign: "middle",
        margin: "0 5px",
        background: kind === "ctl" ? "var(--arm-control)" : "var(--arm-treat)",
      }}
    />
  );
}

// The static specimen SVG — a real binned histogram (counts sum to each arm's
// n), control columns + treatment stepped density, CI ribbon on the treatment
// mean, settled mean line in signal-dim (P5, frozen poster — never bright).
function SpecimenSvg() {
  return (
    <svg
      viewBox="0 0 250 158"
      preserveAspectRatio="xMidYMid meet"
      aria-hidden
      fontFamily="'Geist Mono',monospace"
      style={{ display: "block", width: "100%", height: "100%" }}
    >
      <rect x="141" y="12" width="18" height="106" fill="rgba(200,182,138,.13)" />
      <line x1="14" y1="118" x2="236" y2="118" stroke="#33405C" strokeWidth="1" />
      <g fill="rgba(79,168,224,.13)" stroke="#4FA8E0" strokeWidth=".75">
        <rect x="22" y="113" width="14.5" height="5" />
        <rect x="37" y="107" width="14.5" height="11" />
        <rect x="52" y="96" width="14.5" height="22" />
        <rect x="67" y="76" width="14.5" height="42" />
        <rect x="82" y="48" width="14.5" height="70" />
        <rect x="97" y="17" width="14.5" height="101" />
        <rect x="112" y="6" width="14.5" height="112" />
        <rect x="127" y="12" width="14.5" height="106" />
        <rect x="142" y="36" width="14.5" height="82" />
        <rect x="157" y="62" width="14.5" height="56" />
        <rect x="172" y="63" width="14.5" height="55" />
        <rect x="187" y="89" width="14.5" height="29" />
        <rect x="202" y="104" width="14.5" height="14" />
        <rect x="217" y="113" width="14.5" height="5" />
      </g>
      <path
        fill="rgba(224,139,196,.12)"
        stroke="none"
        d="M22,118 L22,115 L37,115 L37,112 L52,107 L67,98 L82,82 L97,62 L112,40 L127,18 L142,9 L157,15 L172,46 L187,80 L202,103 L217,113 L232,116 L232,118 Z"
      />
      <path
        fill="none"
        stroke="#E08BC4"
        strokeWidth="1.3"
        strokeLinejoin="round"
        d="M22,115 L37,115 L37,112 L52,112 L52,107 L67,107 L67,98 L82,98 L82,82 L97,82 L97,62 L112,62 L112,40 L127,40 L127,18 L142,18 L142,9 L157,9 L157,15 L172,15 L172,46 L187,46 L187,80 L202,80 L202,103 L217,103 L217,113 L232,113 L232,116"
      />
      <line x1="110" y1="6" x2="110" y2="118" stroke="#4FA8E0" strokeWidth="1" strokeDasharray="2 3" opacity=".55" />
      <text x="106" y="14" fill="#4FA8E0" fontSize="7" letterSpacing=".3" textAnchor="end" opacity=".8">
        x̄ ctl
      </text>
      <line x1="150" y1="9" x2="150" y2="118" stroke="rgba(57,184,148,.18)" strokeWidth="4.5" />
      <line x1="150" y1="9" x2="150" y2="118" stroke="#39B894" strokeWidth="1.3" />
      <text x="150" y="6" fill="#929BAE" fontSize="8.5" letterSpacing=".4" textAnchor="middle">
        MEAN +0.041
      </text>
      <text x="14" y="130" fill="#929BAE" fontSize="8" letterSpacing=".5" textAnchor="start">
        REJECTS
      </text>
      <text x="236" y="130" fill="#929BAE" fontSize="8" letterSpacing=".5" textAnchor="end">
        ADOPTS
      </text>
      <text x="125" y="130" fill="#929BAE" fontSize="7.5" letterSpacing=".5" textAnchor="middle">
        REACTION SCORE · 14 BINS
      </text>
      <text x="125" y="151" fill="#929BAE" fontSize="7" letterSpacing=".4" textAnchor="middle">
        1,200 AGENTS BINNED · CONTROL 600 + TREATMENT 600
      </text>
    </svg>
  );
}
