"use client";

// ───────────────────────────────────────────────────────────────────────────
// /memory/connect — Experiment-archive ONBOARDING (#19), v2 Console.
//
// A five-step ingestion flow, all under AppShellV2:
//   1. SOURCE   — pick a connector (CSV active · Statsig/SQL need credentials)
//   2. CONNECT  — CSV: upload a file · Statsig: API key · SQL: connection + query
//   3. MAP      — confirm/edit the source-column -> Experiment-field mapping
//   4. PREVIEW  — verify mapped rows in a §8.8 register before committing
//   5. IMPORT   — write to the archive; honest result (imported / failed / needs)
//
// HONEST by construction: the credentialed connectors render their real
// "needs credentials" message and never fabricate an import. The two-table
// firewall is visible in the mapping step — input fields and outcome fields are
// grouped and mapped independently.
//
// Token-driven only; all layout lives in styles/v2-theme.css (.v2-connect-*),
// so this island ships no inline <style>. No emoji, no icon library — text
// glyphs only (DESIGN.md §7.10).
// ───────────────────────────────────────────────────────────────────────────

import { useEffect, useMemo, useState } from "react";

import {
  csvSampleUrl,
  csvTemplateUrl,
  listConnectors,
  previewCsv,
  previewConnectorImport,
  runConnectorImport,
  validateConnector,
  TARGET_FIELDS,
  type CsvColumnProfile,
  type ConnectorDescriptor,
  type ConnectorKind,
  type CsvPreviewResponse,
  type Experiment,
  type FieldMapping,
  type ImportResult,
  type RowError,
} from "@/lib/api";
import AppShellV2 from "@/components/v2/AppShellV2";
import { Button, StatusBadge } from "@/components/v2";

// The nine target fields, split along the two-table firewall (DESIGN.md §8.9).
const INPUT_FIELDS = ["change_description", "variants", "primary_metric", "category"];
const OUTCOME_FIELDS = ["winner", "result", "effect_size_pct", "n", "date"];

const FIELD_LABEL: Record<string, string> = {
  change_description: "Change description",
  variants: "Variants (arms)",
  primary_metric: "Primary metric",
  category: "Category",
  winner: "Winner",
  result: "Result",
  effect_size_pct: "Effect size (%)",
  n: "Sample size (n)",
  date: "Date",
};

const RESULT_LABEL: Record<string, string> = { win: "WON", loss: "LOST", flat: "FLAT" };

const STEPS = ["SOURCE", "CONNECT", "MAP", "PREVIEW", "IMPORT"] as const;
type Step = (typeof STEPS)[number];

function pct(value: number): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`;
}

// ── step rail (mono designators, no icons) ──────────────────────────────────
function StepRail({ current }: { current: Step }) {
  const idx = STEPS.indexOf(current);
  return (
    <ol className="v2-connect-steps" aria-label="Onboarding steps">
      {STEPS.map((s, i) => {
        const state = i < idx ? "done" : i === idx ? "current" : "upcoming";
        return (
          <li
            key={s}
            className={`v2-connect-step v2-connect-step--${state}`}
            aria-current={state === "current" ? "step" : undefined}
          >
            <span className="v2-connect-step-n v2-mono v2-tnum">
              {String(i + 1).padStart(2, "0")}
            </span>
            <span className="v2-connect-step-label v2-mono">{s}</span>
          </li>
        );
      })}
    </ol>
  );
}

export default function ConnectFlowV2() {
  const [step, setStep] = useState<Step>("SOURCE");
  const [connectors, setConnectors] = useState<ConnectorDescriptor[] | null>(null);
  const [connectorsError, setConnectorsError] = useState<string | null>(null);
  const [kind, setKind] = useState<ConnectorKind | null>(null);

  // CONNECT state
  const [config, setConfig] = useState<Record<string, string>>({});
  const [csvRows, setCsvRows] = useState<Record<string, string>[]>([]);
  const [csvColumns, setCsvColumns] = useState<CsvColumnProfile[]>([]);
  const [csvPreview, setCsvPreview] = useState<CsvPreviewResponse | null>(null);
  const [connectMessage, setConnectMessage] = useState<string | null>(null);
  const [connectErr, setConnectErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // MAP state — Experiment field -> source column name
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [delimiter, setDelimiter] = useState("|");

  // PREVIEW + IMPORT state
  const [preview, setPreview] = useState<Experiment[]>([]);
  const [previewErrors, setPreviewErrors] = useState<RowError[]>([]);
  // Honest dry-run message for credentialed connectors (Statsig/SQL): the
  // preview pulls + maps rows but persists nothing (MAJOR 5).
  const [previewMessage, setPreviewMessage] = useState<string | null>(null);
  const [previewReady, setPreviewReady] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);

  useEffect(() => {
    listConnectors()
      .then((r) => setConnectors(r.connectors))
      .catch((e) => setConnectorsError((e as Error)?.message ?? "Could not load connectors"));
  }, []);

  const descriptor = useMemo(
    () => connectors?.find((c) => c.kind === kind) ?? null,
    [connectors, kind],
  );

  const reset = () => {
    setConfig({});
    setCsvRows([]);
    setCsvColumns([]);
    setCsvPreview(null);
    setConnectMessage(null);
    setConnectErr(null);
    setMapping({});
    setDelimiter("|");
    setPreview([]);
    setPreviewErrors([]);
    setPreviewMessage(null);
    setPreviewReady(false);
    setResult(null);
  };

  const pickSource = (c: ConnectorDescriptor) => {
    reset();
    setKind(c.kind);
    setStep("CONNECT");
  };

  // ── CONNECT: CSV upload ──
  const onUpload = async (file: File) => {
    setConnectErr(null);
    setBusy(true);
    try {
      const res = await previewCsv(file, delimiter);
      setCsvPreview(res);
      setCsvColumns(res.columns);
      setMapping(res.suggested_mapping.columns);
      setDelimiter(res.suggested_mapping.variant_delimiter);
      // Re-parse the raw file into rows for the import payload (the preview only
      // returns the first few mapped rows). We keep the file's rows client-side
      // by reading them from the preview's column profiles is not enough, so we
      // re-read the file as text.
      const text = await file.text();
      setCsvRows(parseCsvRows(text));
      setConnectMessage(`Parsed ${res.row_count} row(s).`);
    } catch (e) {
      setConnectErr((e as Error)?.message ?? "Could not read the CSV");
    } finally {
      setBusy(false);
    }
  };

  // ── CONNECT: Statsig / SQL validate ──
  const onValidate = async () => {
    if (!kind) return;
    setConnectErr(null);
    setBusy(true);
    try {
      const res = await validateConnector(kind, config);
      setConnectMessage(res.message);
      if (!res.ok) {
        setConnectErr(null); // needs-credentials is honest guidance, not an error
      }
    } catch (e) {
      setConnectErr((e as Error)?.message ?? "Validation failed");
    } finally {
      setBusy(false);
    }
  };

  const canProceedFromConnect = (): boolean => {
    if (kind === "csv") return csvRows.length > 0;
    // Statsig/SQL: require the credential fields to be filled before mapping.
    return (descriptor?.credential_fields ?? []).every((f) => (config[f] ?? "").trim());
  };

  const goToMap = () => {
    // Seed a mapping for Statsig/SQL (identity over the canonical target fields)
    // so the customer can confirm; CSV already seeded it from the suggestion.
    if (kind !== "csv" && Object.keys(mapping).length === 0) {
      const seed: Record<string, string> = {};
      TARGET_FIELDS.forEach((f) => (seed[f] = f));
      setMapping(seed);
    }
    setStep("MAP");
  };

  // ── PREVIEW: CSV is previewed locally via the /csv/preview result. For
  // credentialed connectors (Statsig/SQL) we run a real DRY-RUN against
  // /connectors/{kind}/preview: it pulls + maps the first rows with the
  // customer's credentials but writes NOTHING to the archive (MAJOR 5). The
  // customer verifies the mapped result, then explicitly confirms via /import. ──
  const goToPreview = async () => {
    if (kind === "csv") {
      if (csvPreview) {
        setPreview(csvPreview.preview);
        setPreviewErrors(csvPreview.errors);
      }
      setPreviewReady(true);
      setPreviewMessage(null);
      setStep("PREVIEW");
      return;
    }
    if (!kind) return;
    // Credentialed connector: dry-run pull + map, persist nothing.
    setBusy(true);
    setConnectErr(null);
    setPreviewReady(false);
    setStep("PREVIEW");
    try {
      const fieldMapping: FieldMapping = { columns: mapping, variant_delimiter: delimiter };
      const res = await previewConnectorImport(kind, { mapping: fieldMapping, config });
      setPreview(res.experiments);
      setPreviewErrors(res.errors);
      setPreviewMessage(res.message);
      // Only let the customer confirm the import once a non-error preview ran.
      setPreviewReady(res.state !== "needs_credentials");
    } catch (e) {
      setConnectErr((e as Error)?.message ?? "Preview failed");
    } finally {
      setBusy(false);
    }
  };

  const runImport = async () => {
    if (!kind) return;
    setBusy(true);
    try {
      const fieldMapping: FieldMapping = { columns: mapping, variant_delimiter: delimiter };
      const res = await runConnectorImport(kind, {
        mapping: fieldMapping,
        rows: kind === "csv" ? csvRows : undefined,
        config: kind === "csv" ? undefined : config,
      });
      setResult(res);
      setStep("IMPORT");
    } catch (e) {
      setConnectErr((e as Error)?.message ?? "Import failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppShellV2
      activeNav="memory"
      title="Connect a source"
      provenance={{ label: "INGESTION · YOUR RECORDED OUTCOMES", calibrated: false, live: false }}
    >
      <div className="v2-connect">
        <p className="v2-mem-law v2-mono">
          INGESTION ONLY · WE MAP YOUR RECORDED OUTCOMES · WE NEVER FABRICATE A
          RESULT · REAL DATA NEEDS YOUR CREDENTIALS
        </p>

        <StepRail current={step} />

        {/* ── STEP 1 · SOURCE ─────────────────────────────────────────────── */}
        {step === "SOURCE" && (
          <section className="v2-connect-section" aria-labelledby="v2-connect-src-h">
            <h2 id="v2-connect-src-h" className="v2-mem-section-title">
              Pick a source
            </h2>
            <p className="v2-mem-section-sub">
              Bring your past experiments into the archive. CSV works right now.
              Statsig and a SQL database connect the moment you supply your own
              credentials — until then they are listed but inactive.
            </p>

            {connectorsError && (
              <div role="alert" className="v2-mem-alert">
                Could not load connectors: {connectorsError}
              </div>
            )}

            {!connectors && !connectorsError && (
              <p className="v2-connect-pending v2-mono">LOADING CONNECTORS…</p>
            )}

            <div className="v2-connect-sources">
              {connectors?.map((c) => (
                <button
                  key={c.kind}
                  type="button"
                  className="v2-connect-source"
                  onClick={() => pickSource(c)}
                  aria-label={`Connect ${c.name}`}
                >
                  <div className="v2-connect-source-head">
                    <span className="v2-connect-source-name">{c.name}</span>
                    {c.state === "active" ? (
                      <StatusBadge kind="neutral">READY</StatusBadge>
                    ) : (
                      <StatusBadge kind="hold">NEEDS CREDENTIALS</StatusBadge>
                    )}
                  </div>
                  <p className="v2-connect-source-sub">{c.summary}</p>
                  <span className="v2-connect-source-go v2-mono" aria-hidden>
                    SELECT →
                  </span>
                </button>
              ))}
            </div>
          </section>
        )}

        {/* ── STEP 2 · CONNECT ────────────────────────────────────────────── */}
        {step === "CONNECT" && descriptor && (
          <section className="v2-connect-section" aria-labelledby="v2-connect-conn-h">
            <h2 id="v2-connect-conn-h" className="v2-mem-section-title">
              {descriptor.name}
            </h2>

            {kind === "csv" && (
              <>
                <p className="v2-mem-section-sub">
                  Upload a CSV with one row per resolved experiment. Need the
                  shape? Download the{" "}
                  <a className="v2-connect-link" href={csvTemplateUrl}>
                    template
                  </a>{" "}
                  or a{" "}
                  <a className="v2-connect-link" href={csvSampleUrl}>
                    filled-in sample
                  </a>
                  .
                </p>
                <label className="v2-connect-upload">
                  <input
                    type="file"
                    accept=".csv,text/csv"
                    className="v2-connect-file"
                    onChange={(ev) => {
                      const f = ev.target.files?.[0];
                      if (f) onUpload(f);
                    }}
                  />
                  <span className="v2-mono">CHOOSE A CSV FILE</span>
                </label>
              </>
            )}

            {kind !== "csv" && (
              <>
                <p className="v2-mem-section-sub">{descriptor.needs_message}</p>
                <div className="v2-connect-fields">
                  {descriptor.credential_fields.map((field) => {
                    const isQuery = field === "query";
                    const isSecret = field === "api_key" || field === "connection_string";
                    return (
                      <label key={field} className="v2-connect-field">
                        <span className="v2-connect-field-label v2-mono">
                          {field.replace(/_/g, " ").toUpperCase()}
                        </span>
                        {isQuery ? (
                          <textarea
                            className="v2-mem-input"
                            rows={3}
                            placeholder="SELECT change, arms, metric, … FROM experiments"
                            value={config[field] ?? ""}
                            onChange={(ev) =>
                              setConfig((c) => ({ ...c, [field]: ev.target.value }))
                            }
                          />
                        ) : (
                          <input
                            className="v2-connect-input"
                            type={isSecret ? "password" : "text"}
                            autoComplete="off"
                            placeholder={
                              field === "api_key"
                                ? "Your Statsig Console API key"
                                : field === "connection_string"
                                  ? "postgresql://readonly:…@host/db"
                                  : ""
                            }
                            value={config[field] ?? ""}
                            onChange={(ev) =>
                              setConfig((c) => ({ ...c, [field]: ev.target.value }))
                            }
                          />
                        )}
                      </label>
                    );
                  })}
                </div>
                <div className="v2-connect-actions">
                  <Button variant="secondary" onClick={onValidate}>
                    {busy ? "Checking…" : "Validate credentials"}
                  </Button>
                </div>
              </>
            )}

            {connectMessage && (
              <p className="v2-connect-note" role="status">
                {connectMessage}
              </p>
            )}
            {connectErr && (
              <div role="alert" className="v2-mem-alert">
                {connectErr}
              </div>
            )}

            <div className="v2-connect-nav">
              <Button variant="ghost" onClick={() => setStep("SOURCE")}>
                ← Back
              </Button>
              <Button
                variant="primary"
                onClick={goToMap}
                disabled={!canProceedFromConnect()}
              >
                Map fields →
              </Button>
            </div>
          </section>
        )}

        {/* ── STEP 3 · MAP ────────────────────────────────────────────────── */}
        {step === "MAP" && (
          <section className="v2-connect-section" aria-labelledby="v2-connect-map-h">
            <h2 id="v2-connect-map-h" className="v2-mem-section-title">
              Map fields
            </h2>
            <p className="v2-mem-section-sub">
              Match your source columns to the archive&apos;s fields. The input
              side (what changed) and the outcome side (what happened) are mapped
              independently — we never derive one from the other.
            </p>

            <MapGroup
              title="INPUT · WHAT CHANGED"
              fields={INPUT_FIELDS}
              mapping={mapping}
              columns={csvColumns}
              kind={kind}
              onChange={(field, col) => setMapping((m) => ({ ...m, [field]: col }))}
            />
            <MapGroup
              title="OUTCOME · WHAT HAPPENED"
              fields={OUTCOME_FIELDS}
              mapping={mapping}
              columns={csvColumns}
              kind={kind}
              onChange={(field, col) => setMapping((m) => ({ ...m, [field]: col }))}
            />

            <label className="v2-connect-field v2-connect-field--inline">
              <span className="v2-connect-field-label v2-mono">VARIANTS DELIMITER</span>
              <input
                className="v2-connect-input v2-connect-input--narrow"
                value={delimiter}
                onChange={(ev) => setDelimiter(ev.target.value || "|")}
                aria-label="Variants delimiter"
              />
            </label>

            <div className="v2-connect-nav">
              <Button variant="ghost" onClick={() => setStep("CONNECT")}>
                ← Back
              </Button>
              <Button variant="primary" onClick={goToPreview}>
                {kind === "csv" ? "Preview →" : "Continue →"}
              </Button>
            </div>
          </section>
        )}

        {/* ── STEP 4 · PREVIEW ────────────────────────────────────────────── */}
        {step === "PREVIEW" && (
          <section className="v2-connect-section" aria-labelledby="v2-connect-prev-h">
            <h2 id="v2-connect-prev-h" className="v2-mem-section-title">
              Preview
            </h2>
            {kind === "csv" ? (
              <p className="v2-mem-section-sub">
                Verify the mapping reads your rows correctly before importing.
                {csvPreview ? ` Showing up to ${preview.length} of ${csvPreview.row_count}.` : ""}
              </p>
            ) : (
              <p className="v2-mem-section-sub">
                {busy
                  ? `Pulling a sample from ${descriptor?.name} with your credentials — nothing is imported yet.`
                  : (previewMessage ??
                    `${descriptor?.name} rows are pulled with your credentials. This is a dry run — nothing is imported until you confirm.`)}
              </p>
            )}

            {busy && kind !== "csv" && (
              <p className="v2-connect-pending v2-mono">PREVIEWING — NOTHING IMPORTED YET</p>
            )}

            {!busy && preview.length > 0 && (
              <PreviewRegister experiments={preview} />
            )}

            {!busy && preview.length === 0 && (
              <p className="v2-connect-pending v2-mono">
                NO ROWS MAPPED — CHECK THE MAPPING
              </p>
            )}

            {previewErrors.length > 0 && (
              <div className="v2-connect-rowerrors" role="note">
                <span className="v2-mono v2-connect-rowerrors-h">
                  {previewErrors.length} ROW(S) WILL BE SKIPPED
                </span>
                <ul>
                  {previewErrors.map((e) => (
                    <li key={e.row}>
                      <span className="v2-mono v2-tnum">ROW {e.row}</span> — {e.message}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="v2-connect-nav">
              <Button variant="ghost" onClick={() => setStep("MAP")}>
                ← Back
              </Button>
              <Button
                variant="primary"
                onClick={runImport}
                disabled={busy || !previewReady}
              >
                {busy ? "Working…" : "Confirm & import to archive →"}
              </Button>
            </div>
          </section>
        )}

        {/* ── STEP 5 · IMPORT (result) ────────────────────────────────────── */}
        {step === "IMPORT" && result && (
          <section className="v2-connect-section" aria-labelledby="v2-connect-done-h">
            <h2 id="v2-connect-done-h" className="v2-mem-section-title">
              {result.state === "needs_credentials" ? "Needs credentials" : "Import complete"}
            </h2>

            {result.state === "needs_credentials" ? (
              <p className="v2-connect-note" role="status">
                {result.message}
              </p>
            ) : (
              <>
                <div className="v2-connect-result" role="status">
                  <span className="v2-connect-result-n v2-mono v2-tnum">
                    {result.imported}
                  </span>
                  <span className="v2-connect-result-label">
                    experiment{result.imported === 1 ? "" : "s"} imported into the
                    archive{result.failed > 0 ? `; ${result.failed} skipped` : ""}.
                  </span>
                </div>
                {result.experiments.length > 0 && (
                  <PreviewRegister experiments={result.experiments.slice(0, 10)} />
                )}
              </>
            )}

            {result.errors.length > 0 && (
              <div className="v2-connect-rowerrors" role="note">
                <span className="v2-mono v2-connect-rowerrors-h">
                  {result.errors.length} ROW(S) SKIPPED
                </span>
                <ul>
                  {result.errors.slice(0, 20).map((e) => (
                    <li key={e.row}>
                      <span className="v2-mono v2-tnum">ROW {e.row}</span> — {e.message}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="v2-connect-nav">
              <Button
                variant="secondary"
                onClick={() => {
                  reset();
                  setKind(null);
                  setStep("SOURCE");
                }}
              >
                Connect another source
              </Button>
              <Button as="a" variant="primary" href="/memory">
                Back to memory →
              </Button>
            </div>
          </section>
        )}
      </div>
    </AppShellV2>
  );
}

// ── mapping group (input / outcome) — a select per target field ─────────────
function MapGroup({
  title,
  fields,
  mapping,
  columns,
  kind,
  onChange,
}: {
  title: string;
  fields: string[];
  mapping: Record<string, string>;
  columns: CsvColumnProfile[];
  kind: ConnectorKind | null;
  onChange: (field: string, col: string) => void;
}) {
  return (
    <div className="v2-connect-mapgroup">
      <span className="v2-connect-mapgroup-h v2-mono">{title}</span>
      <div className="v2-connect-maprows">
        {fields.map((field) => (
          <div key={field} className="v2-connect-maprow">
            <span className="v2-connect-maprow-field">{FIELD_LABEL[field]}</span>
            {/* For CSV we offer the detected columns as a select; for Statsig/SQL
                the columns are the connector's normalized names, so a text input
                lets the customer name them. */}
            {kind === "csv" && columns.length > 0 ? (
              <select
                className="v2-connect-select v2-mono"
                value={mapping[field] ?? ""}
                onChange={(ev) => onChange(field, ev.target.value)}
                aria-label={`Source column for ${FIELD_LABEL[field]}`}
              >
                <option value="">— unmapped —</option>
                {columns.map((c) => (
                  <option key={c.name} value={c.name}>
                    {c.name}
                  </option>
                ))}
              </select>
            ) : (
              <input
                className="v2-connect-input v2-mono"
                value={mapping[field] ?? ""}
                onChange={(ev) => onChange(field, ev.target.value)}
                placeholder="source column"
                aria-label={`Source column for ${FIELD_LABEL[field]}`}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── preview register (§8.8 register treatment) ──────────────────────────────
function PreviewRegister({ experiments }: { experiments: Experiment[] }) {
  return (
    <div className="v2-connect-register" role="table" aria-label="Mapped experiments preview">
      <div className="v2-connect-reg-head" role="row">
        <span role="columnheader">Change</span>
        <span role="columnheader">Metric</span>
        <span role="columnheader" className="v2-connect-reg-num">Result</span>
        <span role="columnheader" className="v2-connect-reg-num">Effect</span>
        <span role="columnheader" className="v2-connect-reg-num">n</span>
      </div>
      {experiments.map((e) => (
        <div key={e.id} className="v2-connect-reg-row" role="row">
          <span role="cell" className="v2-connect-reg-change">{e.change_description}</span>
          <span role="cell" className="v2-connect-reg-metric">{e.primary_metric}</span>
          <span role="cell" className="v2-connect-reg-num v2-mono">
            {RESULT_LABEL[e.result] ?? e.result.toUpperCase()}
          </span>
          <span role="cell" className="v2-connect-reg-num v2-mono v2-tnum">
            {pct(e.effect_size_pct)}
          </span>
          <span role="cell" className="v2-connect-reg-num v2-mono v2-tnum">
            {e.n.toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  );
}

// Minimal CSV row parser for building the import payload client-side. Mirrors
// the backend's normalization (header row -> stripped string cells). Handles
// quoted fields with embedded commas/quotes; the authoritative parse + mapping
// still happens server-side at import.
function parseCsvRows(text: string): Record<string, string>[] {
  const lines = splitCsvLines(text);
  if (lines.length === 0) return [];
  const header = lines[0].map((h) => h.trim());
  const rows: Record<string, string>[] = [];
  for (let i = 1; i < lines.length; i++) {
    const cells = lines[i];
    if (cells.length === 1 && cells[0].trim() === "") continue;
    const row: Record<string, string> = {};
    header.forEach((h, j) => {
      row[h] = (cells[j] ?? "").trim();
    });
    rows.push(row);
  }
  return rows;
}

function splitCsvLines(text: string): string[][] {
  const out: string[][] = [];
  let field = "";
  let row: string[] = [];
  let inQuotes = false;
  const clean = text.replace(/^﻿/, "");
  for (let i = 0; i < clean.length; i++) {
    const ch = clean[i];
    if (inQuotes) {
      if (ch === '"') {
        if (clean[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        field += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && clean[i + 1] === "\n") i++;
      row.push(field);
      out.push(row);
      row = [];
      field = "";
    } else {
      field += ch;
    }
  }
  if (field !== "" || row.length > 0) {
    row.push(field);
    out.push(row);
  }
  return out;
}
