"use client";

// Sample-workspace seeding card (sessions/sample-workspace).
//
// Shown only on empty-workspace surfaces. The seeding itself is strictly
// click-triggered — nothing is generated until the PM presses the button.
// On success we hard-reload so every mount-time fetch (capabilities,
// personas, models) picks up the freshly seeded packs.
//
// `detectEmpty` mode is for pages that can't tell whether the tenant has
// data (e.g. the personas index): the card probes GET /personas AND
// GET /capabilities on mount and renders only when BOTH 404 — a truly
// empty tenant. A tenant with one real pack would just hit the backend's
// 409, so the button isn't offered. (codex R1-P3) Pages that already
// established both-empty themselves (the wizard) render it directly.

import { useEffect, useState } from "react";
import {
  ApiError,
  generateSampleWorkspace,
  getActivePersonas,
  getCapabilities,
  type SampleWorkspaceResponse,
} from "@/lib/api";
import { TOKENS } from "@/lib/design";

export default function SampleWorkspaceCard({
  detectEmpty = false,
}: {
  detectEmpty?: boolean;
}) {
  // "unknown" only matters in detectEmpty mode; otherwise we start visible.
  const [visible, setVisible] = useState(!detectEmpty);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [seeded, setSeeded] = useState<SampleWorkspaceResponse | null>(null);

  useEffect(() => {
    if (!detectEmpty) return;
    let cancelled = false;
    const is404 = async (probe: () => Promise<unknown>) => {
      try {
        await probe();
        return false; // pack exists — nothing to seed
      } catch (e) {
        // Other errors (auth, network): treat as "not empty" rather than
        // offering a button that will fail.
        return e instanceof ApiError && e.status === 404;
      }
    };
    (async () => {
      const [noPersonas, noCapabilities] = await Promise.all([
        is404(getActivePersonas),
        is404(getCapabilities),
      ]);
      if (!cancelled && noPersonas && noCapabilities) {
        setVisible(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [detectEmpty]);

  if (!visible) return null;

  async function handleGenerate() {
    setWorking(true);
    setError(null);
    try {
      const res = await generateSampleWorkspace();
      setSeeded(res);
      // Give the PM a beat to read the confirmation, then refetch the page.
      window.setTimeout(() => window.location.reload(), 1600);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setError(
          "This workspace already has data — the sample is only for empty workspaces.",
        );
      } else if (e instanceof Error) {
        setError(`Could not generate the sample workspace: ${e.message}`);
      } else {
        setError("Could not generate the sample workspace.");
      }
      setWorking(false);
    }
  }

  return (
    <div
      style={{
        marginTop: 16,
        padding: 16,
        background: TOKENS.paperElevated,
        border: `0.75px solid ${TOKENS.rule}`,
        borderRadius: 4,
      }}
    >
      <div style={{ fontWeight: 500, fontSize: 14, color: TOKENS.ink }}>
        Try a sample workspace
      </div>
      <p style={{ margin: "6px 0 12px", fontSize: 13, color: TOKENS.inkMuted }}>
        Seed this workspace with Streamly, a sample streaming product — 6
        personas and 2 crawled capabilities — so you can run simulations right
        away. Nothing is generated until you click.
      </p>
      {seeded ? (
        <div style={{ fontSize: 13, color: TOKENS.ink }}>
          Seeded {seeded.persona_count} personas (pack{" "}
          <code>{seeded.persona_pack_version}</code>) and{" "}
          {seeded.capabilities.length} capabilities (pack{" "}
          <code>{seeded.feature_pack_version}</code>). Reloading…
        </div>
      ) : (
        <button
          type="button"
          onClick={handleGenerate}
          disabled={working}
          style={{
            background: TOKENS.ink,
            color: TOKENS.paper,
            border: `0.75px solid ${TOKENS.ink}`,
            borderRadius: 4,
            padding: "8px 14px",
            fontWeight: 500,
            fontSize: 13,
            cursor: working ? "wait" : "pointer",
            opacity: working ? 0.6 : 1,
          }}
        >
          {working ? "Generating…" : "Generate sample workspace"}
        </button>
      )}
      {error && (
        <div style={{ marginTop: 10, fontSize: 13, color: TOKENS.alert }}>
          {error}
        </div>
      )}
    </div>
  );
}
