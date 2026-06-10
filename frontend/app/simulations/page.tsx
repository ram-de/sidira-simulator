"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listSimulations, type SimulationListItem } from "@/lib/api";
import { TOKENS, FONT_SANS, FONT_MONO, TNUM } from "@/lib/design";

const STATUS_COLOR: Record<string, string> = {
  pending: TOKENS.inkMuted,
  // Running is a live state, not a semantic outcome — it reads as ink; the
  // sanctioned live treatment is the §9.5 lime carrier, never lime text.
  running: TOKENS.ink,
  complete: TOKENS.success,
  failed: TOKENS.alert,
};

function formatRelative(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diffMs / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

export default function SimulationsIndexPage() {
  const [rows, setRows] = useState<SimulationListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listSimulations()
      .then(setRows)
      .catch((e) => setError(e?.message ?? "Failed to load simulations"));
  }, []);

  return (
    <main style={{ maxWidth: 960, margin: "48px auto", padding: "0 24px", fontFamily: FONT_SANS }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ color: TOKENS.ink }}>Simulations</h1>
        <Link
          href="/simulations/new"
          style={{
            background: TOKENS.ink,
            color: TOKENS.paper,
            padding: "8px 14px",
            borderRadius: 4,
            textDecoration: "none",
            fontWeight: 500,
            fontSize: 13,
          }}
        >
          + New simulation
        </Link>
      </div>
      <p style={{ color: TOKENS.inkMuted }}>
        Submit a hypothesis. Sidira samples your latest persona pack, runs reactions against your
        latest feature pack, and returns a confidence score plus diagnosed weaknesses. Then chat
        with each agent that participated.
      </p>

      {error && (
        <div
          style={{
            marginTop: 24,
            padding: 12,
            border: `0.75px solid ${TOKENS.alert}`,
            background: TOKENS.paperRecessed,
            borderRadius: 4,
            color: TOKENS.alert,
          }}
        >
          Failed to load simulations: {error}
        </div>
      )}

      {rows === null && !error && (
        <p style={{ marginTop: 24, color: TOKENS.inkMuted }}>Loading…</p>
      )}

      {rows !== null && rows.length === 0 && (
        <div
          style={{
            marginTop: 24,
            padding: 24,
            border: `0.75px dashed ${TOKENS.rule}`,
            borderRadius: 4,
            color: TOKENS.inkMuted,
            textAlign: "center",
          }}
        >
          No simulations yet. Click <strong>+ New simulation</strong> to submit your first hypothesis.
        </div>
      )}

      {rows !== null && rows.length > 0 && (
        <table style={{ marginTop: 24, width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: `0.75px solid ${TOKENS.rule}`, fontSize: 13, color: TOKENS.inkMuted }}>
              <th style={{ padding: "10px 8px", fontWeight: 500 }}>Hypothesis</th>
              <th style={{ padding: "10px 8px", fontWeight: 500, width: 110 }}>Capability</th>
              <th style={{ padding: "10px 8px", fontWeight: 500, width: 100 }}>Status</th>
              <th style={{ padding: "10px 8px", fontWeight: 500, width: 80, textAlign: "right" }}>Score</th>
              <th style={{ padding: "10px 8px", fontWeight: 500, width: 110 }}>Created</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} style={{ borderBottom: `0.75px solid ${TOKENS.rule}` }}>
                <td style={{ padding: "12px 8px" }}>
                  <Link
                    href={`/simulations/${row.id}`}
                    style={{ color: TOKENS.ink, textDecoration: "none", fontWeight: 500 }}
                  >
                    {row.hypothesis_prose || <em style={{ color: TOKENS.inkMuted }}>(no prose)</em>}
                  </Link>
                </td>
                <td style={{ padding: "12px 8px", color: TOKENS.inkMuted, fontSize: 14 }}>{row.capability_name}</td>
                <td style={{ padding: "12px 8px" }}>
                  <span
                    style={{
                      color: STATUS_COLOR[row.status] ?? TOKENS.ink,
                      fontWeight: 600,
                      fontSize: 12,
                      textTransform: "uppercase",
                      letterSpacing: 0.4,
                      fontFamily: FONT_MONO,
                      ...TNUM,
                    }}
                  >
                    {row.status}
                  </span>
                </td>
                <td style={{ padding: "12px 8px", textAlign: "right", fontWeight: 500, fontFamily: FONT_MONO, ...TNUM }}>
                  {row.confidence_score !== null ? Math.round(row.confidence_score) : "—"}
                </td>
                <td style={{ padding: "12px 8px", color: TOKENS.inkMuted, fontSize: 13, fontFamily: FONT_MONO, ...TNUM }}>
                  {formatRelative(row.created_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
