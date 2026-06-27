"use client";

// ───────────────────────────────────────────────────────────────────────────
// /admin — the customer ADMIN CONSOLE v1 (#49).
//
// Scope (council's smallest unblock, sessions/admin-console-council/CONSENSUS.md):
//   1. MEMBERS & ROLES — invite / remove / set roles. We do NOT build a custom
//      member-CRUD backend: Clerk OWNS org membership, so we embed Clerk's
//      <OrganizationProfile> (members + invitations + roles), themed to the dark
//      console. The admin manages seats through Clerk; the backend never mirrors
//      the membership table.
//   2. DATA SOURCES — the workspace's persisted experiment-source connections
//      (#46) + feature-store connections. An admin can connect a new source
//      (kind + non-secret config + write-only credential fields), test it,
//      delete it (quiet two-step confirm), re-import (member-OK), and see the
//      last-import status. A MEMBER sees existence + status only — NO secrets,
//      NO credential fields, NO connect/test/delete.
//
// RBAC (council "configuration = admin; execution = member"):
//   • The route + the admin nav entry are gated on the live Clerk org role
//     (useOrgRole). A non-admin sees a friendly "admins only" panel for the
//     admin-only controls, but the data-source LIST + the Re-import button stay
//     visible (re-import is execution).
//   • The AUTHORITATIVE wall is the backend require_admin — a member's create/
//     test/delete 403s server-side regardless of the UI. The client gate is UX.
//
// HARD RULES (ticket + DESIGN.md):
//   • Secrets are WRITE-ONLY, never echoed. A connected source shows only
//     `set ✓` / non-secret display config (host/database/query) — never the
//     api_key / connection_string. The connect form has the secret field; the
//     read view never does (#488).
//   • NO admin "view all conversations" backdoor — this console has no cross-user
//     conversation surface. /memory stays per-user-private (#42).
//   • Cascade-delete confirm UX: delete is a two-step quiet confirm (Delete →
//     Confirm), dismissed on blur — never a resting destructive button, never a
//     modal (DESIGN.md §7.7 / the §7.4 thread-delete pattern).
//   • Refresh model surfaced in words: "Imported once on connect; Re-import to
//     pull again — on demand, never live" (council §Data-refresh model).
//   • Tokens only; no emoji, no icon library (§7.10) — text glyphs (✓ · → ×)
//     in mono. Reduced-motion respected (no entrance motion here; state changes
//     only).
// ───────────────────────────────────────────────────────────────────────────

import { useCallback, useEffect, useMemo, useState } from "react";
import { OrganizationProfile } from "@clerk/nextjs";

import AppShellV2 from "@/components/v2/AppShellV2";
import { clerkAppearanceConsole, clerkEnabled } from "@/lib/clerk";
import { useOrgRole } from "@/lib/useOrgRole";
import {
  ApiError,
  createExperimentSource,
  deleteExperimentSource,
  getConsoleSummary,
  listExperimentSources,
  listFeatureStores,
  reimportExperimentSource,
  testExperimentSource,
  type ConnectorKind,
  type ConnectionSummary,
  type ConsoleSummary,
  type CreateExperimentSourceRequest,
  type ExperimentSourceSummary,
  type FieldMapping,
} from "@/lib/api";

// The credentialed source kinds the console can CONNECT. CSV is a file-upload
// flow that lives in the existing /memory/connect wizard, not a persisted
// stored-credential source — so the console manages Statsig + SQL.
type CredentialedKind = Extract<ConnectorKind, "statsig" | "sql">;

// Per-kind field model, kept in lockstep with the backend `_SECRET_KEYS`
// (api/experiment_sources.py) + the connector registry. `secret` fields are
// write-only (encrypted at rest, never echoed); `config` fields are non-secret
// display config the read view may show.
const SOURCE_KINDS: Record<
  CredentialedKind,
  {
    label: string;
    summary: string;
    secret: { key: string; label: string; placeholder: string }[];
    config: { key: string; label: string; placeholder: string }[];
  }
> = {
  statsig: {
    label: "Statsig",
    summary: "Pull resolved experiment results from your Statsig Console.",
    secret: [
      { key: "api_key", label: "Console API key", placeholder: "console-…" },
    ],
    config: [],
  },
  sql: {
    label: "SQL database",
    summary: "Run a read-only SELECT against your warehouse and map the columns.",
    secret: [
      {
        key: "connection_string",
        label: "Connection string",
        placeholder: "postgresql://readonly@host/db",
      },
    ],
    config: [
      {
        key: "query",
        label: "Read-only query",
        placeholder: "SELECT … FROM experiments",
      },
    ],
  },
};

// An empty FieldMapping for the persisted-source create. The full column→field
// mapping is confirmed in the /memory/connect wizard for a one-shot import;
// connecting a persisted SOURCE here records an empty mapping the admin can
// refine via the wizard before the first re-import. (Re-import re-applies the
// stored mapping; an empty one imports nothing until mapped — honest, no
// fabrication.)
const EMPTY_MAPPING: FieldMapping = { columns: {}, variant_delimiter: "|" };

function fmtWhen(iso: string | null | undefined): string {
  if (!iso) return "never";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

// Pull a customer-safe message out of an ApiError (the backend returns
// {detail: "…"} or a structured {detail:{message}}); never echoes a secret.
function safeError(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    if (err.status === 403) return "Admins only — this action needs an admin role.";
    try {
      const body = JSON.parse(err.body) as { detail?: unknown };
      const d = body.detail;
      if (typeof d === "string") return d;
      if (d && typeof d === "object" && "message" in d) {
        return String((d as { message: unknown }).message);
      }
    } catch {
      /* non-JSON body — fall through */
    }
    return `${fallback} (HTTP ${err.status}).`;
  }
  return fallback;
}

export default function AdminConsoleV2() {
  const { loading: roleLoading, isAdmin } = useOrgRole();

  return (
    <AppShellV2 activeNav="admin" title="Admin console">
      <div className="adm">
        <p className="adm-lede">
          Admin owns the pipes, the people, and the purse. Manage who can use the
          workspace and the data sources that feed it. Members run simulations,
          crawls, and persona builds against what already exists.
        </p>

        {roleLoading ? (
          <p className="adm-load">RESOLVING ROLE…</p>
        ) : (
          <>
            <MembersSection isAdmin={isAdmin} />
            <DataSourcesSection isAdmin={isAdmin} />
          </>
        )}
      </div>
      <style>{ADM_CSS}</style>
    </AppShellV2>
  );
}

// ── Members & roles ──────────────────────────────────────────────────────────

function MembersSection({ isAdmin }: { isAdmin: boolean }) {
  return (
    <section className="adm-section">
      <header className="adm-section-head">
        <h2 className="mono">MEMBERS &amp; ROLES</h2>
        <span className="adm-section-note">
          Seats, invitations, and roles are managed in your organization.
        </span>
      </header>

      {!isAdmin ? (
        <div className="adm-gate">
          <p>
            <span className="mono adm-gate-tag">ADMINS ONLY</span> Inviting,
            removing, and setting member roles needs an admin role. Ask a
            workspace admin to manage seats.
          </p>
        </div>
      ) : !clerkEnabled() ? (
        <div className="adm-gate">
          <p>
            <span className="mono adm-gate-tag">DEV MODE</span> Member management
            runs through your identity provider, which is not configured in this
            environment. With authentication enabled, the organization profile
            (invite · remove · set roles) renders here.
          </p>
        </div>
      ) : (
        // Clerk OWNS membership — embed its OrganizationProfile so admins invite/
        // remove members + set roles through Clerk. We do NOT mirror membership
        // server-side. Themed to the dark console (reuses the rail's appearance).
        <div className="adm-clerk">
          <OrganizationProfile
            appearance={clerkAppearanceConsole}
            routing="hash"
          />
        </div>
      )}
    </section>
  );
}

// ── Data sources ──────────────────────────────────────────────────────────────

function DataSourcesSection({ isAdmin }: { isAdmin: boolean }) {
  const [sources, setSources] = useState<ExperimentSourceSummary[] | null>(null);
  const [stores, setStores] = useState<ConnectionSummary[] | null>(null);
  const [summary, setSummary] = useState<ConsoleSummary | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showConnect, setShowConnect] = useState(false);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      // The summary is admin-only; the lists are member-readable. Load them
      // independently so a member still sees the lists if the summary 403s.
      const [src, fs] = await Promise.all([
        listExperimentSources(),
        listFeatureStores(),
      ]);
      setSources(src);
      setStores(fs);
    } catch (err) {
      setLoadError(safeError(err, "Could not load data sources"));
      setSources([]);
      setStores([]);
    }
    if (isAdmin) {
      try {
        setSummary(await getConsoleSummary());
      } catch {
        // The aggregate is a convenience; the lists are authoritative. A 403 /
        // hiccup just hides the at-a-glance counts.
        setSummary(null);
      }
    }
  }, [isAdmin]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <section className="adm-section">
      <header className="adm-section-head">
        <h2 className="mono">DATA SOURCES</h2>
        <span className="adm-section-note">
          Imported once on connect; Re-import to pull again — on demand, never
          live.
        </span>
        {isAdmin ? (
          <button
            type="button"
            className="adm-btn primary adm-section-action"
            onClick={() => setShowConnect((v) => !v)}
          >
            {showConnect ? "Close" : "+ Connect a source"}
          </button>
        ) : null}
      </header>

      {summary ? (
        <div className="adm-glance">
          <Glance
            label="EXPERIMENT SOURCES"
            value={`${summary.experiment_sources.total}`}
            sub={
              summary.experiment_sources.error > 0
                ? `${summary.experiment_sources.error} need attention`
                : `${summary.experiment_sources.connected} connected`
            }
          />
          <Glance
            label="FEATURE STORES"
            value={`${summary.feature_stores.total}`}
            sub={
              summary.feature_stores.failed > 0
                ? `${summary.feature_stores.failed} failing`
                : `${summary.feature_stores.ok} ok`
            }
          />
          <Glance
            label="CRAWL"
            value={summary.crawl.configured ? "Configured" : "Not set up"}
            sub={
              summary.crawl.last_run_status
                ? `last run ${summary.crawl.last_run_status}`
                : "no runs yet"
            }
          />
          <Glance
            label="PERSONA PACK"
            value={summary.personas.pack_version ?? "none"}
            sub={`${summary.personas.total_builds} build${
              summary.personas.total_builds === 1 ? "" : "s"
            }`}
          />
        </div>
      ) : null}

      {isAdmin && showConnect ? (
        <ConnectSourceForm
          onDone={() => {
            setShowConnect(false);
            void load();
          }}
        />
      ) : null}

      {loadError ? <p className="adm-err">{loadError}</p> : null}

      <h3 className="adm-sub mono">EXPERIMENT SOURCES</h3>
      {sources === null ? (
        <p className="adm-load">LOADING SOURCES…</p>
      ) : sources.length === 0 ? (
        <p className="adm-empty">
          NO EXPERIMENT SOURCES CONNECTED
          {isAdmin ? " — connect one above." : "."}
        </p>
      ) : (
        <ul className="adm-list">
          {sources.map((s) => (
            <ExperimentSourceRow
              key={s.id}
              source={s}
              isAdmin={isAdmin}
              onChange={() => void load()}
            />
          ))}
        </ul>
      )}

      <h3 className="adm-sub mono">FEATURE STORES</h3>
      {stores === null ? (
        <p className="adm-load">LOADING CONNECTIONS…</p>
      ) : stores.length === 0 ? (
        <p className="adm-empty">NO FEATURE-STORE CONNECTIONS.</p>
      ) : (
        <ul className="adm-list">
          {stores.map((c) => (
            <li key={c.id} className="adm-row">
              <div className="adm-row-main">
                <span className="adm-row-name">{c.name}</span>
                <span className="adm-row-meta mono">
                  SNOWFLAKE · {c.account} · {c.database}
                </span>
              </div>
              <div className="adm-row-status mono">
                {c.last_test_status === "ok"
                  ? "OK ✓"
                  : c.last_test_status === "failed"
                    ? "FAILED"
                    : "UNTESTED"}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Glance({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <div className="adm-glance-cell">
      <div className="adm-glance-label mono">{label}</div>
      <div className="adm-glance-value">{value}</div>
      <div className="adm-glance-sub mono">{sub}</div>
    </div>
  );
}

function ExperimentSourceRow({
  source,
  isAdmin,
  onChange,
}: {
  source: ExperimentSourceSummary;
  isAdmin: boolean;
  onChange: () => void;
}) {
  const [busy, setBusy] = useState<null | "test" | "reimport">(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  const run = async (
    kind: "test" | "reimport",
    fn: () => Promise<unknown>,
    okMsg: string,
  ) => {
    setBusy(kind);
    setNote(null);
    try {
      await fn();
      setNote(okMsg);
      onChange();
    } catch (err) {
      setNote(safeError(err, "Action failed"));
    } finally {
      setBusy(null);
    }
  };

  return (
    <li className="adm-row">
      <div className="adm-row-main">
        <span className="adm-row-name">{source.name}</span>
        <span className="adm-row-meta mono">
          {source.kind.toUpperCase()} · CREDENTIAL{" "}
          {source.credentials_set ? "SET ✓" : "MISSING"} · IMPORTED{" "}
          {fmtWhen(source.last_import_at)}
        </span>
        {note ? <span className="adm-row-note">{note}</span> : null}
      </div>

      <div className="adm-row-actions">
        <span
          className={
            source.status === "error"
              ? "adm-row-status mono is-error"
              : "adm-row-status mono"
          }
        >
          {source.status.toUpperCase()}
        </span>

        {/* Re-import is EXECUTION → member-OK (council). */}
        <button
          type="button"
          className="adm-btn quiet"
          disabled={busy !== null}
          onClick={() =>
            run(
              "reimport",
              () => reimportExperimentSource(source.id),
              "Re-import finished.",
            )
          }
        >
          {busy === "reimport" ? "Re-importing…" : "Re-import"}
        </button>

        {/* Test + delete are CONFIGURATION → admin-only. */}
        {isAdmin ? (
          <>
            <button
              type="button"
              className="adm-btn quiet"
              disabled={busy !== null}
              onClick={() =>
                run(
                  "test",
                  () => testExperimentSource(source.id),
                  "Source is ready.",
                )
              }
            >
              {busy === "test" ? "Testing…" : "Test"}
            </button>

            {/* Quiet two-step confirm — never a resting destructive button. */}
            {confirmDelete ? (
              <button
                type="button"
                className="adm-btn danger"
                onBlur={() => setConfirmDelete(false)}
                onClick={async () => {
                  try {
                    await deleteExperimentSource(source.id);
                    onChange();
                  } catch (err) {
                    setNote(safeError(err, "Delete failed"));
                    setConfirmDelete(false);
                  }
                }}
              >
                Confirm delete
              </button>
            ) : (
              <button
                type="button"
                className="adm-btn quiet"
                onClick={() => setConfirmDelete(true)}
              >
                Delete
              </button>
            )}
          </>
        ) : null}
      </div>
    </li>
  );
}

function ConnectSourceForm({ onDone }: { onDone: () => void }) {
  const [kind, setKind] = useState<CredentialedKind>("statsig");
  const [name, setName] = useState("");
  // Per-field values keyed by field key (covers both secret + config fields).
  const [values, setValues] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const def = SOURCE_KINDS[kind];

  // Reset field values when the kind changes (different field set).
  const setKindReset = (k: CredentialedKind) => {
    setKind(k);
    setValues({});
    setError(null);
  };

  const field = (key: string, value: string) =>
    setValues((prev) => ({ ...prev, [key]: value }));

  const submit = async () => {
    setError(null);
    if (!name.trim()) {
      setError("Give the source a name.");
      return;
    }
    // Build the config from secret + non-secret fields. The backend splits them
    // by kind and encrypts the secret keys — they never come back out.
    const config: Record<string, string> = {};
    for (const f of [...def.secret, ...def.config]) {
      const v = values[f.key]?.trim();
      if (v) config[f.key] = v;
    }
    const req: CreateExperimentSourceRequest = {
      name: name.trim(),
      kind,
      config,
      mapping: EMPTY_MAPPING,
    };
    setSubmitting(true);
    try {
      await createExperimentSource(req);
      onDone();
    } catch (err) {
      setError(safeError(err, "Could not connect the source"));
    } finally {
      setSubmitting(false);
    }
  };

  const secretFields = useMemo(() => def.secret, [def]);
  const configFields = useMemo(() => def.config, [def]);

  return (
    <div className="adm-connect">
      <div className="adm-field">
        <label className="adm-label mono" htmlFor="src-kind">
          SOURCE TYPE
        </label>
        <select
          id="src-kind"
          className="adm-in mono"
          value={kind}
          onChange={(e) => setKindReset(e.target.value as CredentialedKind)}
        >
          {(Object.keys(SOURCE_KINDS) as CredentialedKind[]).map((k) => (
            <option key={k} value={k}>
              {SOURCE_KINDS[k].label}
            </option>
          ))}
        </select>
        <p className="adm-hint">{def.summary}</p>
      </div>

      <div className="adm-field">
        <label className="adm-label mono" htmlFor="src-name">
          NAME
        </label>
        <input
          id="src-name"
          className="adm-in"
          value={name}
          placeholder="e.g. Prod Statsig"
          onChange={(e) => setName(e.target.value)}
        />
      </div>

      {configFields.map((f) => (
        <div className="adm-field" key={f.key}>
          <label className="adm-label mono" htmlFor={`cfg-${f.key}`}>
            {f.label.toUpperCase()}
          </label>
          <input
            id={`cfg-${f.key}`}
            className="adm-in mono"
            value={values[f.key] ?? ""}
            placeholder={f.placeholder}
            onChange={(e) => field(f.key, e.target.value)}
          />
        </div>
      ))}

      {secretFields.map((f) => (
        <div className="adm-field" key={f.key}>
          <label className="adm-label mono" htmlFor={`sec-${f.key}`}>
            {f.label.toUpperCase()}{" "}
            <span className="adm-label-tag">write-only</span>
          </label>
          <input
            id={`sec-${f.key}`}
            className="adm-in mono"
            type="password"
            autoComplete="new-password"
            value={values[f.key] ?? ""}
            placeholder={f.placeholder}
            onChange={(e) => field(f.key, e.target.value)}
          />
          <p className="adm-hint">
            Encrypted at rest and never shown again — you re-enter it to rotate.
          </p>
        </div>
      ))}

      {error ? <p className="adm-err">{error}</p> : null}

      <div className="adm-connect-actions">
        <button
          type="button"
          className="adm-btn primary"
          disabled={submitting}
          onClick={() => void submit()}
        >
          {submitting ? "Connecting…" : "Connect source →"}
        </button>
        <button type="button" className="adm-btn quiet" onClick={onDone}>
          Cancel
        </button>
      </div>
    </div>
  );
}

// ── scoped dark Console tokens + layout. Mirrors the CrawlSetupV2 pattern: the
//    page re-declares the console palette under its own root class so every
//    token resolves inside the .v2-console ancestor. Tokens only — no raw hex
//    outside this token block, no emoji, no icon font (§7.10). ───────────────
const ADM_CSS = `
.adm{
  --console-900:#0B1220; --console-850:#10192A; --console-800:#161F32;
  --console-750:#1D2740; --console-700:#26314C; --console-line:#33405C;
  --text-hi:#F2F4F8; --text:#C6CCD8; --text-mut:#929BAE; --text-faint:#646E84;
  --signal:#48EFCA; --signal-dim:#39B894; --alert:#F0683C; --edge-warn:#C9A227;
  --r-well:4px; --r-panel:8px;
  --font-sans:var(--v2-font-sans,var(--font-sans,"Geist",system-ui,sans-serif));
  --font-mono:var(--v2-font-mono,var(--font-mono,ui-monospace,"Geist Mono",monospace));
  color:var(--text); font-family:var(--font-sans); font-size:15px; line-height:1.55;
  max-width:980px; font-variant-numeric:tabular-nums;
}
.adm *{box-sizing:border-box;}
.adm .mono{font-family:var(--font-mono);}
.adm h2,.adm h3{color:var(--text-hi); text-wrap:balance;}

.adm-lede{color:var(--text-mut); font-size:15px; line-height:1.55; max-width:720px;
  margin:0 0 8px;}
.adm-load{color:var(--text-mut); font-family:var(--font-mono); font-size:11px;
  letter-spacing:.08em;}

.adm-section{margin-top:56px;}
.adm-section:first-of-type{margin-top:32px;}
.adm-section-head{display:flex; align-items:baseline; gap:14px; flex-wrap:wrap;
  padding-bottom:12px; border-bottom:1px solid rgba(51,64,92,.5); margin-bottom:20px;}
.adm-section-head h2{font-size:.95rem; font-weight:550; letter-spacing:.08em;
  text-transform:uppercase; color:var(--text-mut); margin:0;}
.adm-section-note{font-size:13px; color:var(--text-mut);}
.adm-section-action{margin-left:auto;}

.adm-sub{font-size:11px; letter-spacing:.08em; color:var(--text-faint);
  margin:28px 0 12px; font-weight:500;}

/* at-a-glance counts (admin only) — register cells, never filled cards */
.adm-glance{display:grid; grid-template-columns:repeat(4,1fr); gap:0;
  border:1px solid rgba(51,64,92,.6); border-radius:var(--r-panel);
  overflow:hidden; margin-bottom:8px;}
.adm-glance-cell{padding:14px 16px; border-right:1px solid rgba(51,64,92,.5);}
.adm-glance-cell:last-child{border-right:0;}
.adm-glance-label{font-size:10px; letter-spacing:.08em; color:var(--text-faint);}
.adm-glance-value{font-size:1.3rem; font-weight:600; color:var(--text-hi);
  margin-top:6px; line-height:1.1; word-break:break-word;}
.adm-glance-sub{font-size:11px; color:var(--text-mut); margin-top:4px;}
@media (max-width:859px){.adm-glance{grid-template-columns:repeat(2,1fr);}}

/* admins-only / dev gate — border + word, never a fill */
.adm-gate{border-left:2px solid var(--edge-warn); background:var(--console-800);
  border-radius:var(--r-well); padding:14px 16px; max-width:720px;}
.adm-gate p{margin:0; font-size:14px; line-height:1.55; color:var(--text);}
.adm-gate-tag{font-size:10px; letter-spacing:.08em; color:var(--text-mut);
  border:1px solid rgba(51,64,92,.7); border-radius:var(--r-well);
  padding:2px 7px; margin-right:8px;}

/* Clerk org-profile embed — let Clerk own its internal layout */
.adm-clerk{margin-top:4px;}

/* rows — hairline-separated register, no zebra, no cards */
.adm-list{list-style:none; margin:0; padding:0;
  border-top:1px solid rgba(51,64,92,.4);}
.adm-row{display:flex; align-items:center; gap:16px; flex-wrap:wrap;
  padding:14px 2px; border-bottom:1px solid rgba(51,64,92,.4);}
.adm-row-main{min-width:0; flex:1 1 240px; display:flex; flex-direction:column; gap:4px;}
.adm-row-name{color:var(--text-hi); font-size:15px; font-weight:500;}
.adm-row-meta{font-size:11px; letter-spacing:.04em; color:var(--text-mut);}
.adm-row-note{font-size:12px; color:var(--text); margin-top:2px;}
.adm-row-actions{display:flex; align-items:center; gap:10px; flex-wrap:wrap;}
.adm-row-status{font-size:11px; letter-spacing:.06em; color:var(--text-mut);}
.adm-row-status.is-error{color:var(--alert);}

.adm-empty{color:var(--text-mut); font-family:var(--font-mono); font-size:11px;
  letter-spacing:.06em;}
.adm-err{color:var(--text); font-size:13px; line-height:1.5; max-width:620px;
  border-left:2px solid var(--alert); background:var(--console-800);
  border-radius:var(--r-well); padding:10px 14px; margin:12px 0;}

/* connect form */
.adm-connect{border:1px solid rgba(51,64,92,.6); border-radius:var(--r-panel);
  padding:20px; margin-bottom:24px; max-width:620px; background:var(--console-850);}
.adm-field{margin-bottom:18px;}
.adm-field:last-of-type{margin-bottom:0;}
.adm-label{display:block; font-size:11px; letter-spacing:.06em;
  text-transform:uppercase; color:var(--text-mut); margin-bottom:7px;}
.adm-label-tag{text-transform:none; letter-spacing:0; color:var(--text-faint);
  font-size:10px; font-style:italic; margin-left:6px;}
.adm-in{width:100%; height:36px; background:var(--console-700);
  border:2px solid rgba(51,64,92,.7); border-radius:var(--r-well);
  color:var(--text-hi); padding:0 12px; font-size:14px; font-family:var(--font-sans);
  transition:border-color .14s;}
.adm-in.mono{font-family:var(--font-mono); font-size:13px;}
.adm-in:focus{outline:none; border-color:var(--signal-dim);}
select.adm-in{appearance:none; -webkit-appearance:none; cursor:pointer;}
.adm-hint{font-size:13px; color:var(--text-mut); margin:8px 0 0; line-height:1.5;}
.adm-connect-actions{display:flex; gap:12px; margin-top:22px;}

/* buttons — token-driven, no pills, no gradients (§7.7) */
.adm-btn{cursor:pointer; border-radius:var(--r-well); font-family:var(--font-mono);
  font-size:11px; letter-spacing:.05em; padding:8px 14px; transition:.14s;
  border:1px solid rgba(51,64,92,.7); background:transparent; color:var(--text-mut);}
.adm-btn:hover{color:var(--text-hi); border-color:var(--text-mut);}
.adm-btn:focus-visible{outline:1px solid var(--signal); outline-offset:2px;}
.adm-btn:disabled{opacity:.5; cursor:not-allowed;}
.adm-btn.primary{background:var(--text-hi); color:var(--console-900);
  border-color:var(--text-hi); font-weight:600;}
.adm-btn.primary:hover{background:#fff; color:var(--console-900);}
.adm-btn.quiet{font-size:11px;}
.adm-btn.danger{border-color:var(--alert); color:var(--alert);}
.adm-btn.danger:hover{background:var(--alert); color:var(--console-900);
  border-color:var(--alert);}

@media (prefers-reduced-motion:reduce){.adm-btn,.adm-in{transition:none;}}
`;
