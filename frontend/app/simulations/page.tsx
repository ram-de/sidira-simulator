"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { CSSProperties } from "react";
import { listSimulations, type SimulationListItem } from "@/lib/api";
import { TOKENS, FONT_SANS, FONT_MONO, TNUM } from "@/lib/design";

// ─── The hypotheses register — R2 PR 3 (#165) ──────────────────────────
//
// A paper table of hypotheses (DESIGN.md §7, §8). The governing law here is
// §8.1: a verdict without its decision policy never renders. The list API
// (`SimulationListItem`) carries no persisted decision policy — no threshold,
// no rule, no CI — so completed rows do NOT render a ship/no-ship verdict
// chip. They state the absence honestly ("NO PERSISTED POLICY · NO VERDICT")
// and report the raw agreement score, labeled per §8.3
// ("simulation agreement — raw, UNCALIBRATED (ledger empty)").
// State chips (QUEUED · READING IN PROGRESS · RUN FAILED) are run states,
// not verdicts — §8.6 sanctions them as honest pending text.

// One API page; the list endpoint returns no total, so when a full page
// comes back the header can only honestly claim "latest N" (codex P2).
const PAGE_LIMIT = 50;

// §8.1 explainer, surfaced as a tooltip on the verdict column cells.
const POLICY_GAP_NOTE =
  "A verdict renders only against a persisted decision policy (threshold + " +
  "rule). The backend does not persist one yet, so the agreement score is " +
  "reported raw — uncalibrated, no ship call.";

const AGREEMENT_NOTE =
  "Simulation agreement — raw, uncalibrated (calibration ledger empty). " +
  "Scale 0–100. Not a calibrated probability.";

// Scoped CSS for pseudo-states the inline-style idiom can't express.
// §9.3 row hover (80ms ease-out) + press feedback; §9.5 live carrier —
// the single sanctioned pulse, 3.4s phase-locked, lime as live-state
// carrier only. Reduced motion: static underline at full opacity.
const REGISTER_STYLE = `
  .sidira-register-row { transition: background 80ms ease-out; cursor: pointer; }
  .sidira-register-row:hover { background: ${TOKENS.paperRecessed}; }
  .sidira-register-row:active { transform: translateY(1px); }
  .sidira-new-hyp:active { transform: translateY(1px); }
  @keyframes sidira-carrier { 0%, 100% { opacity: 0.45; } 50% { opacity: 1; } }
  .sidira-carrier { position: relative; }
  .sidira-carrier::after {
    content: ""; position: absolute; left: 0; right: 0; bottom: -4px; height: 2px;
    background: ${TOKENS.signal};
    animation: sidira-carrier 3.4s ease-in-out infinite;
  }
  @media (prefers-reduced-motion: reduce) {
    .sidira-carrier::after { animation: none; opacity: 1; }
    .sidira-register-row { transition: none; }
    .sidira-register-row:active, .sidira-new-hyp:active { transform: none; }
  }
`;

// Mono state chip — radius 2, never a pill (§7.1). `muted` is the resting
// register voice; `alert` is reserved for error severity (§8.5).
const CHIP_BASE: CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 10.5,
  letterSpacing: "0.06em",
  border: `1px solid ${TOKENS.rule}`,
  borderRadius: 2,
  padding: "2px 7px",
  whiteSpace: "nowrap",
  color: TOKENS.inkMuted,
  ...TNUM,
};

function StateChip({
  label,
  tone,
  live,
}: {
  label: string;
  tone: "muted" | "alert";
  live?: boolean;
}) {
  return (
    <span
      className={live ? "sidira-carrier" : undefined}
      style={{
        ...CHIP_BASE,
        ...(tone === "alert"
          ? { borderColor: TOKENS.alert, color: TOKENS.alert }
          : null),
      }}
    >
      {label}
    </span>
  );
}

// Row designator — machine-derived, mono, ink-weight only (§4.3). Built from
// the real simulation id (first 4 hex chars), never a synthesized sequence.
function designator(id: string): string {
  return `HYP-${id.replace(/-/g, "").slice(0, 4).toUpperCase()}`;
}

// Timestamps render as dates in mono (§5.4) — the register is a record.
function isoDate(iso: string | null): string {
  return iso ? iso.slice(0, 10) : "—";
}

const TH_STYLE: CSSProperties = {
  textAlign: "left",
  fontFamily: FONT_MONO,
  fontSize: 11,
  fontWeight: 400,
  letterSpacing: "0.1em",
  textTransform: "uppercase",
  color: TOKENS.inkMuted,
  padding: "10px 16px 6px 0",
  borderBottom: `0.75px solid ${TOKENS.rule}`,
};

const TD_STYLE: CSSProperties = {
  padding: "9px 16px 9px 0",
  borderBottom: `0.75px solid ${TOKENS.rule}`,
  verticalAlign: "baseline",
};

function VerdictCell({ row }: { row: SimulationListItem }) {
  switch (row.status) {
    case "pending":
      return <StateChip label="QUEUED" tone="muted" />;
    case "running":
      // §9.5 live carrier under the running state — lime is live-state only.
      return <StateChip label="READING IN PROGRESS" tone="muted" live />;
    case "failed":
      return <StateChip label="RUN FAILED" tone="alert" />;
    case "complete":
      // §8.1: no persisted policy ⇒ no verdict chip. The absence is stated,
      // not papered over with a frontend-invented threshold.
      return (
        <span
          title={POLICY_GAP_NOTE}
          style={{
            fontFamily: FONT_MONO,
            fontSize: 10.5,
            letterSpacing: "0.06em",
            color: TOKENS.inkMuted,
            whiteSpace: "nowrap",
          }}
        >
          NO PERSISTED POLICY · NO VERDICT
        </span>
      );
    default:
      // Unknown runtime status from the backend — render nothing rather
      // than guess at a state label.
      return null;
  }
}

function AgreementCell({ row }: { row: SimulationListItem }) {
  if (row.status === "complete" && row.confidence_score !== null) {
    return <span style={{ color: TOKENS.ink }}>{Math.round(row.confidence_score)}</span>;
  }
  // §8.6 pending numerals are honest placeholders, never spinners.
  return (
    <span style={{ color: TOKENS.inkMuted }}>
      {row.status === "running" ? "——" : "—"}
    </span>
  );
}

export default function SimulationsIndexPage() {
  const router = useRouter();
  const [rows, setRows] = useState<SimulationListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listSimulations(PAGE_LIMIT)
      .then(setRows)
      .catch((e) => setError(e?.message ?? "Failed to load simulations"));
  }, []);

  // The API returns one page with no total; at the page limit the honest
  // claim is "latest N", not a total count.
  const countClause =
    rows !== null
      ? rows.length >= PAGE_LIMIT
        ? `LATEST ${rows.length} HYPOTHESES · `
        : `${rows.length} ${rows.length === 1 ? "HYPOTHESIS" : "HYPOTHESES"} · `
      : "";

  return (
    <main style={{ fontFamily: FONT_SANS, color: TOKENS.ink }}>
      <style dangerouslySetInnerHTML={{ __html: REGISTER_STYLE }} />

      {/* Page strip — dense, left-aligned instrument header (§7). */}
      <header
        style={{
          padding: "20px 24px 16px",
          borderBottom: `0.75px solid ${TOKENS.rule}`,
          display: "flex",
          alignItems: "baseline",
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <h1 style={{ fontSize: 20, fontWeight: 600, letterSpacing: "-0.01em", margin: 0 }}>
          Hypotheses
        </h1>
        <span
          title={AGREEMENT_NOTE}
          style={{
            fontFamily: FONT_MONO,
            fontSize: 11,
            color: TOKENS.inkMuted,
            letterSpacing: "0.06em",
            ...TNUM,
          }}
        >
          {countClause}SIM AGREEMENT — RAW · UNCALIBRATED · LEDGER EMPTY
        </span>
        <span
          style={{
            marginLeft: "auto",
            fontFamily: FONT_MONO,
            fontSize: 10,
            letterSpacing: "0.08em",
            color: TOKENS.inkMuted,
            border: `1px solid ${TOKENS.rule}`,
            borderRadius: 2,
            padding: "3px 8px",
            whiteSpace: "nowrap",
          }}
        >
          A VERDICT WITHOUT ITS POLICY NEVER RENDERS
        </span>
        <Link
          href="/simulations/new"
          className="sidira-new-hyp"
          style={{
            fontSize: 13,
            fontWeight: 500,
            whiteSpace: "nowrap",
            background: TOKENS.ink,
            color: TOKENS.paper,
            border: `1px solid ${TOKENS.ink}`,
            borderRadius: 2,
            padding: "7px 14px",
            textDecoration: "none",
          }}
        >
          New hypothesis →
        </Link>
      </header>

      <div style={{ padding: 24 }}>
        {error && (
          <div
            style={{
              padding: 12,
              border: `0.75px solid ${TOKENS.alert}`,
              background: TOKENS.paperRecessed,
              borderRadius: 4,
              color: TOKENS.alert,
              fontSize: 14,
            }}
          >
            Failed to load the register: {error}
          </div>
        )}

        {rows === null && !error && (
          <p style={{ margin: 0, color: TOKENS.inkMuted, fontSize: 14 }}>
            Loading the register…
          </p>
        )}

        {rows !== null && (
          <section>
            <span
              style={{
                display: "block",
                fontSize: 11,
                fontWeight: 500,
                letterSpacing: "0.16em",
                textTransform: "uppercase",
                color: TOKENS.inkMuted,
                paddingBottom: 10,
                borderBottom: `0.75px solid ${TOKENS.rule}`,
              }}
            >
              Hypothesis register
            </span>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={{ ...TH_STYLE, width: 90 }}>ID</th>
                  <th style={TH_STYLE}>Hypothesis</th>
                  <th
                    title={AGREEMENT_NOTE}
                    style={{ ...TH_STYLE, width: 150, textAlign: "right" }}
                  >
                    Sim agreement · raw
                  </th>
                  <th style={{ ...TH_STYLE, width: 240 }}>Verdict · policy</th>
                  <th style={{ ...TH_STYLE, width: 120 }}>Last run</th>
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 && (
                  <tr>
                    <td
                      colSpan={5}
                      style={{
                        ...TD_STYLE,
                        padding: "22px 0",
                        color: TOKENS.inkMuted,
                        fontSize: 14,
                      }}
                    >
                      No hypotheses on the register yet.{" "}
                      <Link
                        href="/simulations/new"
                        style={{ color: TOKENS.ink, fontWeight: 500, textDecoration: "none" }}
                      >
                        New hypothesis →
                      </Link>{" "}
                      starts your first reading.
                    </td>
                  </tr>
                )}
                {rows.map((row) => (
                  <tr
                    key={row.id}
                    className="sidira-register-row"
                    onClick={() => router.push(`/simulations/${row.id}`)}
                  >
                    <td
                      title={row.id}
                      style={{
                        ...TD_STYLE,
                        fontFamily: FONT_MONO,
                        fontSize: 12,
                        color: TOKENS.ink,
                        whiteSpace: "nowrap",
                        ...TNUM,
                      }}
                    >
                      {designator(row.id)}
                    </td>
                    <td style={{ ...TD_STYLE, fontWeight: 500, fontSize: 14 }}>
                      <Link
                        href={`/simulations/${row.id}`}
                        onClick={(e) => e.stopPropagation()}
                        style={{ color: TOKENS.ink, textDecoration: "none" }}
                      >
                        {row.hypothesis_prose || (
                          <em style={{ color: TOKENS.inkMuted }}>(no prose)</em>
                        )}
                      </Link>
                      <span
                        style={{
                          display: "block",
                          marginTop: 2,
                          fontFamily: FONT_MONO,
                          fontSize: 11,
                          fontWeight: 400,
                          letterSpacing: "0.04em",
                          color: TOKENS.inkMuted,
                        }}
                      >
                        {row.capability_name}
                      </span>
                    </td>
                    <td
                      style={{
                        ...TD_STYLE,
                        fontFamily: FONT_MONO,
                        fontSize: 13,
                        textAlign: "right",
                        whiteSpace: "nowrap",
                        ...TNUM,
                      }}
                    >
                      <AgreementCell row={row} />
                    </td>
                    <td style={TD_STYLE}>
                      <VerdictCell row={row} />
                    </td>
                    <td
                      style={{
                        ...TD_STYLE,
                        fontFamily: FONT_MONO,
                        fontSize: 11,
                        color: TOKENS.inkMuted,
                        whiteSpace: "nowrap",
                        ...TNUM,
                      }}
                    >
                      {row.status === "running"
                        ? "LIVE"
                        : row.status === "pending"
                          ? "—"
                          : isoDate(row.completed_at ?? row.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
      </div>
    </main>
  );
}
