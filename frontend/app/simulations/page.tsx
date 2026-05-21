"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listSimulations, type SimulationListItem } from "@/lib/api";

const STATUS_COLOR: Record<string, string> = {
  pending: "#888",
  running: "#1d4ed8",
  complete: "#15803d",
  failed: "#b91c1c",
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
    <main style={{ maxWidth: 960, margin: "48px auto", padding: "0 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>Simulations</h1>
        <Link
          href="/simulations/new"
          style={{
            background: "#111",
            color: "#fff",
            padding: "8px 14px",
            borderRadius: 6,
            textDecoration: "none",
            fontWeight: 500,
          }}
        >
          + New simulation
        </Link>
      </div>
      <p style={{ color: "#555" }}>
        Submit a hypothesis. Pythia samples your latest persona pack, runs reactions against your
        latest feature pack, and returns a confidence score plus diagnosed weaknesses. Then chat
        with each agent that participated.
      </p>

      {error && (
        <div
          style={{
            marginTop: 24,
            padding: 12,
            border: "1px solid #fca5a5",
            background: "#fef2f2",
            borderRadius: 6,
            color: "#991b1b",
          }}
        >
          Failed to load simulations: {error}
        </div>
      )}

      {rows === null && !error && (
        <p style={{ marginTop: 24, color: "#888" }}>Loading…</p>
      )}

      {rows !== null && rows.length === 0 && (
        <div
          style={{
            marginTop: 24,
            padding: 24,
            border: "1px dashed #d4d4d8",
            borderRadius: 6,
            color: "#666",
            textAlign: "center",
          }}
        >
          No simulations yet. Click <strong>+ New simulation</strong> to submit your first hypothesis.
        </div>
      )}

      {rows !== null && rows.length > 0 && (
        <table style={{ marginTop: 24, width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid #e4e4e7", fontSize: 13, color: "#52525b" }}>
              <th style={{ padding: "10px 8px", fontWeight: 500 }}>Hypothesis</th>
              <th style={{ padding: "10px 8px", fontWeight: 500, width: 110 }}>Capability</th>
              <th style={{ padding: "10px 8px", fontWeight: 500, width: 100 }}>Status</th>
              <th style={{ padding: "10px 8px", fontWeight: 500, width: 80, textAlign: "right" }}>Score</th>
              <th style={{ padding: "10px 8px", fontWeight: 500, width: 110 }}>Created</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} style={{ borderBottom: "1px solid #f4f4f5" }}>
                <td style={{ padding: "12px 8px" }}>
                  <Link
                    href={`/simulations/${row.id}`}
                    style={{ color: "#111", textDecoration: "none", fontWeight: 500 }}
                  >
                    {row.hypothesis_prose || <em style={{ color: "#888" }}>(no prose)</em>}
                  </Link>
                </td>
                <td style={{ padding: "12px 8px", color: "#52525b", fontSize: 14 }}>{row.capability_name}</td>
                <td style={{ padding: "12px 8px" }}>
                  <span
                    style={{
                      color: STATUS_COLOR[row.status] ?? "#000",
                      fontWeight: 600,
                      fontSize: 12,
                      textTransform: "uppercase",
                      letterSpacing: 0.4,
                    }}
                  >
                    {row.status}
                  </span>
                </td>
                <td style={{ padding: "12px 8px", textAlign: "right", fontWeight: 500 }}>
                  {row.confidence_score !== null ? Math.round(row.confidence_score) : "—"}
                </td>
                <td style={{ padding: "12px 8px", color: "#71717a", fontSize: 13 }}>
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
