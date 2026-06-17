"use client";

// ───────────────────────────────────────────────────────────────────────────
// /simulations — the hypotheses register, v2 "Reading Console" reskin (#372).
//
// A faithful port of SimulationsListLegacy onto the v2 Console surface: SAME
// data (listSimulations(50)), SAME states (loading · error · empty · count
// clause), SAME §8.1 HONESTY LAW. The four REAL run statuses map onto v2
// primitives (StatusBadge / StatusDot live), but the LABEL strings and the
// no-verdict clause are carried over verbatim — never the mock's fabricated
// live/hold/settled/Refuted words, and NEVER a directional-reading / lift
// column (a verdict without a persisted policy does not render).
//
// Token-driven only; table layout + carrier pulse live in styles/v2-theme.css
// (.v2-sims-*), so this island ships no inline <style> (no hydration risk).
// The whole subtree sits under AppShellV2 → ConsoleShell's `.v2-console`.
// ───────────────────────────────────────────────────────────────────────────

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { listSimulations, type SimulationListItem } from "@/lib/api";
import AppShellV2 from "@/components/v2/AppShellV2";
import {
  Panel,
  StatusBadge,
  StatusDot,
  Button,
} from "@/components/v2";

// One API page; the list endpoint returns no total, so at a full page the
// header can only honestly claim "latest N" (codex P2).
const PAGE_LIMIT = 50;

// §8.1 explainer, surfaced as a tooltip on the verdict column cells.
const POLICY_GAP_NOTE =
  "A verdict renders only against a persisted decision policy (threshold + " +
  "rule). The backend does not persist one yet, so the agreement score is " +
  "reported raw — uncalibrated, no ship call.";

const AGREEMENT_NOTE =
  "Simulation agreement — raw, uncalibrated (calibration ledger empty). " +
  "Scale 0–100. Not a calibrated probability.";

// Row designator — machine-derived, mono, ink-weight only (§4.3). Built from
// the real simulation id (first 8 hex chars), never a synthesized sequence.
function designator(id: string): string {
  return `HYP-${id.replace(/-/g, "").slice(0, 8).toUpperCase()}`;
}

// Timestamps render as dates — the register is a record.
function isoDate(iso: string | null): string {
  return iso ? iso.slice(0, 10) : "—";
}

// §8.1: status → run-state primitive + the REAL label string. `complete` never
// renders a verdict — it states the absence ("NO PERSISTED POLICY · NO VERDICT")
// with the POLICY_GAP_NOTE tooltip. State chips are run states, not verdicts.
function VerdictCell({ row }: { row: SimulationListItem }) {
  switch (row.status) {
    case "pending":
      return (
        <span className="v2-sims-state">
          <StatusBadge kind="neutral">QUEUED</StatusBadge>
        </span>
      );
    case "running":
      // live carrier under the running state — signal is live-state only (§1.9).
      return (
        <span className="v2-sims-state v2-sims-carrier">
          <StatusDot live />
          <StatusBadge kind="live">READING IN PROGRESS</StatusBadge>
        </span>
      );
    case "failed":
      return (
        <span className="v2-sims-state">
          <StatusBadge kind="failed">RUN FAILED</StatusBadge>
        </span>
      );
    case "complete":
      // §8.1: no persisted policy ⇒ no verdict chip; the absence is stated.
      return (
        <span className="v2-sims-nopolicy v2-mono" title={POLICY_GAP_NOTE}>
          NO PERSISTED POLICY · NO VERDICT
        </span>
      );
    default:
      // Unknown runtime status — render nothing rather than guess at a label.
      return null;
  }
}

// Raw agreement numeral, labeled RAW · UNCALIBRATED (§8.3). Only complete rows
// with a score show a number; running → "——"; everything else → "—".
function AgreementCell({ row }: { row: SimulationListItem }) {
  if (row.status === "complete" && row.confidence_score !== null) {
    return (
      <>
        <span className="v2-tnum">{Math.round(row.confidence_score)}</span>
        <span className="v2-sims-agree-tag v2-mono">RAW · UNCAL</span>
      </>
    );
  }
  return (
    <span className="v2-tnum">{row.status === "running" ? "——" : "—"}</span>
  );
}

export default function SimulationsListV2() {
  const router = useRouter();
  const [rows, setRows] = useState<SimulationListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listSimulations(PAGE_LIMIT)
      .then(setRows)
      .catch((e) => setError(e?.message ?? "Failed to load simulations"));
  }, []);

  // The API returns one page with no total; at the page limit the honest claim
  // is "latest N", not a total count.
  const countClause =
    rows !== null
      ? rows.length >= PAGE_LIMIT
        ? `LATEST ${rows.length} HYPOTHESES · `
        : `${rows.length} ${rows.length === 1 ? "HYPOTHESIS" : "HYPOTHESES"} · `
      : "";

  return (
    <AppShellV2
      activeNav="simulations"
      title="Hypotheses"
      provenance={{
        label: "SIM AGREEMENT · RAW",
        calibrated: false,
        live: rows?.some((r) => r.status === "running") ?? false,
      }}
      actions={
        <Button as="a" href="/simulations/new" variant="primary">
          New hypothesis →
        </Button>
      }
    >
      <div className="v2-sims">
        <div className="v2-sims-head">
          <span className="v2-sims-count" title={AGREEMENT_NOTE}>
            <span className="v2-mono v2-tnum">{countClause}</span>
            SIM AGREEMENT — RAW · UNCALIBRATED · LEDGER EMPTY
          </span>
          <span className="v2-sims-law v2-mono">
            A VERDICT WITHOUT ITS POLICY NEVER RENDERS
          </span>
        </div>

        {error && (
          <div role="alert" className="v2-sims-alert">
            Failed to load the register: {error}
          </div>
        )}

        {rows === null && !error && (
          <p className="v2-sims-loading">Loading the register…</p>
        )}

        {rows !== null && (
          <Panel className="v2-sims-panel">
            <div className="v2-sims-table" role="table" aria-label="Hypothesis register">
              <div className="v2-sims-row v2-sims-row--head" role="row">
                <span className="v2-sims-c-id v2-desig" role="columnheader">
                  ID
                </span>
                <span className="v2-sims-c-name v2-desig" role="columnheader">
                  Hypothesis
                </span>
                <span
                  className="v2-sims-c-agree v2-desig"
                  role="columnheader"
                  title={AGREEMENT_NOTE}
                >
                  Sim agreement · raw
                </span>
                <span className="v2-sims-c-verdict v2-desig" role="columnheader">
                  Verdict · policy
                </span>
                <span className="v2-sims-c-when v2-desig" role="columnheader">
                  Last run
                </span>
              </div>

              {rows.length === 0 && (
                <div className="v2-sims-empty" role="row">
                  No hypotheses on the register yet.{" "}
                  <Link href="/simulations/new">New hypothesis →</Link> starts
                  your first reading.
                </div>
              )}

              {rows.map((row) => (
                <div
                  key={row.id}
                  className="v2-sims-row v2-sims-row--link"
                  role="row"
                  onClick={() => router.push(`/simulations/${row.id}`)}
                >
                  <span
                    className="v2-sims-c-id v2-mono v2-tnum"
                    role="cell"
                    title={row.id}
                  >
                    {designator(row.id)}
                  </span>

                  <span className="v2-sims-c-name" role="cell">
                    <span className="v2-sims-name">
                      <Link
                        href={`/simulations/${row.id}`}
                        onClick={(e) => e.stopPropagation()}
                      >
                        {row.hypothesis_prose || (
                          <em className="v2-sims-name-empty">(no prose)</em>
                        )}
                      </Link>
                    </span>
                    <span className="v2-sims-cap v2-mono">
                      {row.capability_name}
                    </span>
                  </span>

                  <span
                    className={
                      row.status === "complete" && row.confidence_score !== null
                        ? "v2-sims-c-agree v2-mono"
                        : "v2-sims-c-agree v2-sims-c-agree--muted v2-mono"
                    }
                    role="cell"
                  >
                    <AgreementCell row={row} />
                  </span>

                  <span className="v2-sims-c-verdict" role="cell">
                    <VerdictCell row={row} />
                  </span>

                  <span className="v2-sims-c-when v2-mono v2-tnum" role="cell">
                    {row.status === "running"
                      ? "LIVE"
                      : row.status === "pending"
                        ? "—"
                        : isoDate(row.completed_at ?? row.created_at)}
                  </span>
                </div>
              ))}
            </div>
          </Panel>
        )}
      </div>
    </AppShellV2>
  );
}
