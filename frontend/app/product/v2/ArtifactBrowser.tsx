// ───────────────────────────────────────────────────────────────────────────
// /product/v2 — THE ARTIFACT BROWSER (the hero showpiece, WORKING-class).
// Page-local: this is product-page-specific composition, not a shared
// primitive. It DOES consume the shared v2 layer (Panel-style surface via
// .v2-panel-equivalents, ProvenanceBar, DistributionPoster). One reading
// region · one Provenance Bar · one static poster (P9: no live field here).
// ───────────────────────────────────────────────────────────────────────────
"use client";

import { useRef, useState } from "react";
import {
  ProvenanceBar,
  DistributionPoster,
  PosterFigure,
  CalGlyph,
  ConsoleWell,
} from "@/components/v2";

type TabId = "rxn" | "prd" | "fig";
const TABS: { id: TabId; label: string }[] = [
  { id: "rxn", label: "Cohort reaction" },
  { id: "prd", label: "Reverse-PRD" },
  { id: "fig", label: "Reverse-Figma" },
];

// Control arm peaks ~0.59; treatment ~0.66 — same value-series the live field
// would re-sort into. Bars are agent counts per reaction bin (240 agents).
const CONTROL_BARS = [
  { x: 20, h: 6 }, { x: 40, h: 13 }, { x: 60, h: 25 }, { x: 80, h: 42 },
  { x: 100, h: 60 }, { x: 120, h: 74 }, { x: 140, h: 66 }, { x: 160, h: 48 },
  { x: 180, h: 30 }, { x: 200, h: 18 }, { x: 220, h: 10 }, { x: 240, h: 5 },
];
const TREAT_BARS = [
  { x: 28, h: 4 }, { x: 48, h: 9 }, { x: 68, h: 18 }, { x: 88, h: 33 },
  { x: 108, h: 50 }, { x: 128, h: 65 }, { x: 148, h: 76 }, { x: 168, h: 68 },
  { x: 188, h: 52 }, { x: 208, h: 34 }, { x: 228, h: 20 }, { x: 248, h: 10 },
  { x: 268, h: 5 },
];

export function ArtifactBrowser() {
  const [tab, setTab] = useState<TabId>("rxn");
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  // ARIA Authoring Practices tabs pattern: ArrowLeft/Right select the
  // adjacent tab AND move DOM focus to it (roving tabindex below).
  const onKey = (e: React.KeyboardEvent, i: number) => {
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      e.preventDefault();
      const dir = e.key === "ArrowRight" ? 1 : -1;
      const nextIdx = (i + dir + TABS.length) % TABS.length;
      setTab(TABS[nextIdx].id);
      tabRefs.current[nextIdx]?.focus();
    }
  };

  return (
    // §6.4 — a dark instrument well sitting inside the light Sheet product page.
    // The well re-asserts the complete Console token scope locally; the tabbed
    // browser (an instrument view) lives inside it, dark, without inverting the
    // route. Provenance inside stays Console-styled (route-mode law).
    <ConsoleWell
      role="group"
      aria-label="Captured capability snapshot"
    >
      {/* one Provenance Bar for the whole reading region (§7.3) */}
      <div
        style={{
          padding: "11px 16px",
          borderBottom: "1px solid var(--console-line-50)",
          background: "rgba(11,18,32,.5)",
        }}
      >
        <ProvenanceBar
          align="end"
          calibrated={false}
          segments={[
            { content: "CAP checkout" },
            { content: "n=240" },
            { content: "seed 0x4f" },
            { content: "groq/llama-3.3" },
          ]}
        />
      </div>

      {/* tablist — the active indicator is INK, not signal: the poster mean
          line is this region's one signal carrier (P2) */}
      <div
        role="tablist"
        aria-label="Artifact view"
        style={{
          display: "flex",
          borderBottom: "1px solid var(--console-line-50)",
          background: "rgba(11,18,32,.25)",
        }}
      >
        {TABS.map((t, i) => {
          const on = t.id === tab;
          return (
            <button
              key={t.id}
              id={`v2-tab-${t.id}`}
              ref={(el) => {
                tabRefs.current[i] = el;
              }}
              role="tab"
              aria-selected={on}
              aria-controls={`v2-tabpanel-${t.id}`}
              tabIndex={on ? 0 : -1}
              onClick={() => setTab(t.id)}
              onKeyDown={(e) => onKey(e, i)}
              style={{
                flex: 1,
                textAlign: "center",
                padding: "10px 8px",
                fontFamily: "var(--v2-font-mono)",
                fontSize: 10.5,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                color: on ? "var(--text-hi)" : "var(--text-mut)",
                cursor: "pointer",
                position: "relative",
                background: "none",
                border: "none",
                transition: "color .14s var(--ease-out)",
              }}
            >
              {t.label}
              {on ? (
                <span
                  aria-hidden
                  style={{
                    position: "absolute",
                    left: 14,
                    right: 14,
                    bottom: -1,
                    height: 2,
                    background: "var(--text-hi)",
                    borderRadius: 2,
                  }}
                />
              ) : null}
            </button>
          );
        })}
      </div>

      <div
        role="tabpanel"
        id={`v2-tabpanel-${tab}`}
        aria-labelledby={`v2-tab-${tab}`}
        tabIndex={0}
        style={{ padding: 20, minHeight: 296 }}
      >
        {tab === "rxn" ? <ReactionPane /> : null}
        {tab === "prd" ? <PrdPane /> : null}
        {tab === "fig" ? <FigPane /> : null}
      </div>
    </ConsoleWell>
  );
}

// ── TEXTURE 1 of 3: A FIGURE — the settled distribution poster ─────────────
function ReactionPane() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <PosterFigure value="0.62" ci="±0.08" verdict="DIRECTIONAL" />

      {/* arm key — tints name the arm (provenance), not valence */}
      <div
        className="v2-mono"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 18,
          flexWrap: "wrap",
          fontSize: 10,
          letterSpacing: "0.04em",
          color: "var(--text-mut)",
        }}
      >
        <ArmKey color="var(--arm-control)" label="CONTROL" value="0.59" ci="±0.09" />
        <ArmKey color="var(--arm-treat)" label="TREATMENT" value="0.66" ci="±0.10" />
        <span style={{ marginLeft: "auto", textTransform: "none", letterSpacing: "0.02em" }}>
          <CalGlyph /> uncalibrated · per-arm means inferred
        </span>
      </div>

      <DistributionPoster
        controlBars={CONTROL_BARS}
        treatBars={TREAT_BARS}
        pooledMeanX={138}
        controlMeanX={123}
        treatMeanX={151}
        pooledMeanLabel="MEAN 0.62"
        calibrated={false}
        footerNote="240 AGENTS · BINNED · BAR HEIGHT = AGENT COUNT"
        ariaLabel="Adoption reaction histogram across 240 grounded agents, binned on a reject-to-adopt axis. Control arm (blue) clusters near 0.59 and treatment arm (magenta) near 0.66; bars are agent counts per bin. Pooled mean 0.62, uncalibrated, with a confidence band."
      />

      {/* recorded facts only → bare provenance bar (P8) */}
      <ProvenanceBar
        segments={[
          { content: <><b style={{ color: "var(--text)", fontWeight: 500 }}>n=240</b> agents</> },
          { content: "snapshot 2026-W25" },
          { content: "STATIC · NO READING RUNNING" },
        ]}
      />
      <p style={{ fontSize: 12.5, color: "var(--text-mut)", lineHeight: 1.5 }}>
        Each bar is a count of the <b style={{ color: "var(--text)", fontWeight: 500 }}>240</b>{" "}
        agents that landed in that reaction bin — a real histogram, not a sketch. The pooled mean
        stays <CalGlyph /> uncalibrated until a real outcome grades it; the count is recorded, the
        means are inferred.
      </p>
    </div>
  );
}

function ArmKey({ color, label, value, ci }: { color: string; label: string; value: string; ci: string }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6, textTransform: "uppercase" }}>
      <i style={{ width: 9, height: 9, borderRadius: 2, flex: "0 0 auto", background: color }} />
      {label}{" "}
      <b className="v2-tnum" style={{ color: "var(--text-hi)", fontWeight: 500 }}>{value}</b>{" "}
      <span className="v2-tnum" style={{ color: "var(--spread)", textTransform: "none" }}>{ci}</span>
    </span>
  );
}

// ── TEXTURE 2 of 3: PROSE — the reverse-PRD reads as a document ────────────
function PrdPane() {
  return (
    <div style={{ fontFamily: "var(--v2-font-sans)" }}>
      <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text-hi)", letterSpacing: "-0.01em", display: "flex", alignItems: "baseline", gap: 10 }}>
        Checkout
        <span className="v2-mono" style={{ fontSize: 10, letterSpacing: "0.06em", color: "var(--text-mut)" }}>
          · as-built · v.2026-W25
        </span>
      </div>
      <p style={{ marginTop: 10, fontSize: 13.5, lineHeight: 1.62, color: "var(--text)" }}>
        A returning customer completes a purchase with saved details. The surface is{" "}
        <b style={{ color: "var(--text-hi)", fontWeight: 550 }}>optimized for completion rate</b>: it
        minimises the steps between cart and a placed order, and pushes failure states (declined card,
        address gap) inline rather than to a separate screen.
      </p>
      <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 11 }}>
        <PrdRow lab="Flow">
          <span className="v2-mono" style={{ fontSize: 11, color: "var(--text-mut)" }}>cart → address → pay → confirm</span>, then a receipt.
        </PrdRow>
        <PrdRow lab="Roles">
          Guest, member, and <span className="v2-mono" style={{ fontSize: 11, color: "var(--text-mut)" }}>pro</span> — pro alone sees the saved-cards panel.
        </PrdRow>
        <PrdRow lab="Edge cases">
          Empty cart, declined card, and a missing-address gap each resolve in place.
        </PrdRow>
      </div>
      <p
        className="v2-mono"
        style={{ marginTop: 16, paddingTop: 13, borderTop: "1px solid var(--console-line-40)", fontSize: 11, letterSpacing: "0.03em", color: "var(--text-mut)" }}
      >
        Δ vs 2026-W24 — <b style={{ color: "var(--spread)", fontWeight: 500 }}>~2 lines of copy</b> reworded; flow and structure unchanged.
      </p>
      <Cap>
        A reverse-PRD: what a PM would write if documenting this surface from scratch — generated
        weekly, never hand-authored.
      </Cap>
    </div>
  );
}

function PrdRow({ lab, children }: { lab: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", gap: 12, alignItems: "baseline" }}>
      <span
        className="v2-mono"
        style={{ flex: "0 0 92px", fontSize: 9.5, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-mut)", paddingTop: 2 }}
      >
        {lab}
      </span>
      <span style={{ fontSize: 13, lineHeight: 1.5, color: "var(--text)" }}>{children}</span>
    </div>
  );
}

// ── TEXTURE 3 of 3: A DIAGRAM — the reverse-Figma reads as a structure tree ─
function FigPane() {
  return (
    <div>
      <div
        className="v2-mono"
        role="img"
        aria-label="Reverse-Figma structure tree for checkout: four screens — Cart, Address, Pay (with a role-gated saved-cards panel, newly added), and Confirm — each carrying default, error, and empty states."
        style={{ fontSize: 11.5, lineHeight: 1, color: "var(--text)" }}
      >
        <NodeRow glyph="▦" label="Cart" states={["default", "empty"]} />
        <NodeRow rail=" └─" glyph="▢" label="line-items · summary · checkout-cta" comp />
        <NodeRow glyph="▦" label="Address" states={["default", "error"]} />
        <NodeRow glyph="▦" label="Pay" gate="pro ▸ saved-cards" states={["default", "error"]} />
        <NodeRow rail=" └─" glyph="＋" label="saved-cards panel" add states={["role-gated"]} />
        <NodeRow glyph="▦" label="Confirm" states={["default"]} />
        <div
          style={{ marginTop: 16, paddingTop: 13, borderTop: "1px solid var(--console-line-40)", fontSize: 10, letterSpacing: "0.04em", color: "var(--text-mut)", display: "flex", gap: 16, flexWrap: "wrap" }}
        >
          <span>4 screens · 14 components</span>
          <span>
            <span style={{ color: "var(--text-hi)" }}>＋</span> 1 component{" "}
            <span style={{ color: "var(--text-mut)" }}>Δ vs 2026-W24</span>
          </span>
        </div>
      </div>
      <Cap>
        A reverse-Figma: the visual + interactive spec at structure level — same shape as the Figma a
        PM submits for a proposed change. No pixels, by design.
      </Cap>
    </div>
  );
}

function NodeRow({
  rail,
  glyph,
  label,
  comp = false,
  add = false,
  gate,
  states = [],
}: {
  rail?: string;
  glyph: string;
  label: string;
  comp?: boolean;
  add?: boolean;
  gate?: string;
  states?: string[];
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 0, height: 26 }}>
      {rail ? (
        <span style={{ flex: "0 0 auto", color: "var(--console-line)", whiteSpace: "pre" }}>{rail}</span>
      ) : null}
      <span style={{ flex: "0 0 16px", textAlign: "center", color: add ? "var(--text-hi)" : undefined }}>{glyph}</span>
      <span style={{ color: add ? "var(--text-hi)" : comp ? "var(--text)" : "var(--text-hi)", fontWeight: comp ? 400 : 500 }}>{label}</span>
      <span style={{ marginLeft: "auto", display: "flex", gap: 6, alignItems: "center", paddingLeft: 14 }}>
        {gate ? (
          <span style={{ fontSize: 8.5, letterSpacing: "0.04em", color: "var(--text-mut)" }}>{gate}</span>
        ) : null}
        {states.map((s) => (
          <span
            key={s}
            style={{ fontSize: 8.5, letterSpacing: "0.04em", color: "var(--text-mut)", border: "1px solid var(--console-line-55)", borderRadius: 2, padding: "1px 4px" }}
          >
            {s}
          </span>
        ))}
      </span>
    </div>
  );
}

function Cap({ children }: { children: React.ReactNode }) {
  return (
    <p style={{ marginTop: 16, paddingTop: 13, borderTop: "1px solid var(--console-line-40)", fontSize: 12.5, color: "var(--text-mut)", lineHeight: 1.5 }}>
      {children}
    </p>
  );
}
