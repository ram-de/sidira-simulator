"use client";

// ───────────────────────────────────────────────────────────────────────
// EXPERIMENTAL PREVIEW — "THE READING CONSOLE" simulation-results variant.
//
// This is an ISOLATED, UNLINKED preview route (reachable only by typing
// /simulations/<id>/console). It renders the SAME live simulation data as the
// production results page, in the clean-sheet "Reading Console" design language
// explored under design-rethink/. It deliberately uses a SEPARATE, locally
// SCOPED visual system (dark Console / candor law) and does NOT touch the
// production DESIGN.md "paper" system, lib/design.ts, or the live results page.
//
// Nothing links here; production is untouched. Delete this folder to remove.
// ───────────────────────────────────────────────────────────────────────

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  ApiError,
  getSimulation,
  isTerminalStatus,
  type Simulation,
} from "@/lib/api";
import { ReadingConsoleResults } from "./ReadingConsoleResults";

export default function SimulationConsolePage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;

  const [sim, setSim] = useState<Simulation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!id) return;
    // Guard against late responses landing after unmount or an id change —
    // mirrors the production results page's cancellation pattern.
    let cancelled = false;

    const load = async () => {
      try {
        const next = await getSimulation(id);
        if (cancelled) return;
        setSim(next);
        setError(null);
        // Stop polling once the run reaches a terminal state.
        if (isTerminalStatus(next.status) && pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      } catch (e) {
        if (cancelled) return;
        setError(
          e instanceof ApiError ? e.message : "Failed to load simulation.",
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    // Light poll while a run may still be in flight; cleared on terminal status.
    pollRef.current = setInterval(() => void load(), 4000);
    return () => {
      cancelled = true;
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [id]);

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#0B1220",
        color: "#E7ECF5",
        fontFamily:
          "var(--font-mono), ui-monospace, 'JetBrains Mono', monospace",
      }}
    >
      {loading && !sim ? (
        <div style={{ padding: 64, opacity: 0.6, fontSize: 13 }}>
          Loading reading…
        </div>
      ) : error ? (
        <div style={{ padding: 64 }}>
          <div style={{ color: "#E0A8A0", fontSize: 13, marginBottom: 12 }}>
            {error}
          </div>
          <Link
            href={id ? `/simulations/${id}` : "/simulations"}
            style={{ color: "#9AA6BD", fontSize: 12 }}
          >
            ← back to results
          </Link>
        </div>
      ) : sim ? (
        <ReadingConsoleResults sim={sim} />
      ) : null}
    </main>
  );
}
