"use client";

// Persona Builder — self-serve 7-step wizard (Phase 4.5; #26 connect, #27 map,
// #28 review→trigger→watch→promote→done).
//
// The wizard owns ALL shared state here; each step renders against that lifted
// state and a small set of callbacks. Navigation is a top stepper plus Back/
// Next; "Next" is gated per-step (see canContinue) so a step can't be left
// until its contract is satisfied — a connection that TESTED OK (#26), a
// mapping where every column is resolved (#27), a build that reached a
// terminal/promotable state (#28).
//
// Posture: instrument (DESIGN.md §7) — the visual vocabulary is the
// crawl-setup page's, imported from ./wizard-ui. Pending/loading/empty states
// are honest mono text, never spinners (§8.6). Errors use the paper-recessed
// note anatomy: message in ink, severity on the alert border (§4.3/§7.7).

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  createFeatureStore,
  createPersonaBuild,
  getPersonaBuild,
  getPersonaBuildEvents,
  isBuildTerminal,
  previewFeatureStore,
  promotePersonaPack,
  suggestMapping,
  testFeatureStore,
  type BuildConfig,
  type BuildEvent,
  type BuildK,
  type BuildSummary,
  type ColumnAssignment,
  type ColumnProfile,
  type ConnectionSummary,
  type FeatureGroup,
  type LlmProvider,
  type MappingSuggestion,
  type PackSummary,
  type SnowflakeConnectionRequest,
  type WeightScheme,
  FEATURE_GROUPS,
} from "@/lib/api";
import { TOKENS, FONT_SANS, FONT_MONO, TNUM } from "@/lib/design";
import {
  AddButton,
  apiErrorMessage,
  apiErrorParts,
  Chip,
  errorBannerStyle,
  fieldRowStyle,
  fieldStyle,
  hintStyle,
  inputStyle,
  monoInputStyle,
  okBannerStyle,
  primaryBtnStyle,
  railAlertStyle,
  railCaptionStyle,
  secondaryBtnStyle,
  sectionLabelStyle,
  sectionStyle,
  selectStyle,
  statusLineStyle,
  sublabelStyle,
  textareaStyle,
  utcStamp,
} from "./wizard-ui";

// ── step metadata ─────────────────────────────────────────────────────────
const STEPS = [
  { id: 1, label: "Connect" },
  { id: 2, label: "Map" },
  { id: 3, label: "Review" },
  { id: 4, label: "Trigger" },
  { id: 5, label: "Watch" },
  { id: 6, label: "Promote" },
  { id: 7, label: "Done" },
] as const;
const LAST_STEP = STEPS.length;

// Human labels for the 7 canonical feature groups (#27 review/map display).
// The ids stay machine-canonical (column_mapper.FeatureGroup); these are the
// reading-voice names shown in the UI only.
const GROUP_LABELS: Record<FeatureGroup, string> = {
  demographic_identity: "Demographic / identity",
  behavioral_patterns: "Behavioral patterns",
  motivations_jtbd: "Motivations / JTBD",
  pain_points_friction: "Pain points / friction",
  value_sensitivity: "Value sensitivity",
  channel_tech_behavior: "Channel / tech behavior",
  loyalty_lifecycle: "Loyalty / lifecycle",
};

// A column's resolved destination: one of the 7 groups, or explicitly ignored.
type Assignment = FeatureGroup | "ignore";

// The wizard's source choice (#26). Exactly one of table/sql is active.
type SourceMode = "table" | "sql";

// Snapshot of the connection-form values used to mint the last connection id —
// so we know whether any CREDENTIAL field changed and a fresh create is owed
// before the next test (#26: reuse the id if nothing changed).
type CredKey = keyof Pick<
  SnowflakeConnectionRequest,
  "name" | "account" | "user" | "password" | "warehouse" | "role" | "database" | "schema"
>;

interface ConnForm {
  name: string;
  account: string;
  user: string;
  password: string;
  warehouse: string;
  role: string;
  database: string;
  schema: string;
}

const emptyConnForm = (): ConnForm => ({
  name: "",
  account: "",
  user: "",
  password: "",
  warehouse: "",
  role: "",
  database: "",
  schema: "",
});

// The credential fingerprint — if this string changes, the stored connection
// id is stale and a fresh createFeatureStore is owed before testing again.
const credFingerprint = (f: ConnForm, mode: SourceMode, table: string, sql: string) =>
  JSON.stringify([f.name, f.account, f.user, f.password, f.warehouse, f.role, f.database, f.schema, mode, table, sql]);

const POLL_MS = 2500; // #28 watch cadence while pending/running.

export default function NewPersonaPackPage() {
  const [step, setStep] = useState(1);

  // ── Step 1 · Connect (#26) ──────────────────────────────────────────────
  const [conn, setConn] = useState<ConnForm>(emptyConnForm());
  const [sourceMode, setSourceMode] = useState<SourceMode>("table");
  const [tableFqn, setTableFqn] = useState("");
  const [sql, setSql] = useState("");
  const [connection, setConnection] = useState<ConnectionSummary | null>(null);
  // Test lifecycle. `okFingerprint` records the cred fingerprint that PASSED a
  // test — Continue is enabled only while the current fingerprint matches it.
  const [testing, setTesting] = useState(false);
  const [testError, setTestError] = useState<{ kind: string | null; message: string } | null>(null);
  const [okFingerprint, setOkFingerprint] = useState<string | null>(null);
  // The fingerprint that minted `connection` — reused on the next test if the
  // user hasn't touched any field since.
  const [connFingerprint, setConnFingerprint] = useState<string | null>(null);

  // ── Step 2 · Map (#27) ──────────────────────────────────────────────────
  const [columns, setColumns] = useState<ColumnProfile[] | null>(null);
  const [rowCount, setRowCount] = useState<number | null>(null);
  const [suggestion, setSuggestion] = useState<MappingSuggestion | null>(null);
  const [mapping, setMapping] = useState<Record<string, Assignment | "">>({});
  const [mapPhase, setMapPhase] = useState<"idle" | "profiling" | "suggesting" | "ready" | "error">("idle");
  const [mapError, setMapError] = useState<string | null>(null);

  // ── Step 3/4 · config (#28) ─────────────────────────────────────────────
  const [k, setK] = useState<BuildK>("auto");
  const [stabilityThreshold, setStabilityThreshold] = useState(0.65);
  const [llmProvider, setLlmProvider] = useState<LlmProvider>("groq");
  const [weightSchemes] = useState<WeightScheme[]>(["head_count"]);

  // ── Step 5 · Watch (#28) ────────────────────────────────────────────────
  const [build, setBuild] = useState<BuildSummary | null>(null);
  const [events, setEvents] = useState<BuildEvent[]>([]);
  const [triggering, setTriggering] = useState(false);
  const [triggerError, setTriggerError] = useState<string | null>(null);

  // ── Step 6 · Promote (#28) ──────────────────────────────────────────────
  const [promoting, setPromoting] = useState(false);
  const [promoted, setPromoted] = useState<PackSummary | null>(null);
  const [promoteError, setPromoteError] = useState<string | null>(null);

  // The live fingerprint of the connect form (recomputed each render).
  const fingerprint = credFingerprint(conn, sourceMode, tableFqn, sql);
  const testPassed = okFingerprint !== null && okFingerprint === fingerprint;

  // The source body passed to preview/build. Table → SELECT *; SQL verbatim.
  const sourceBody = (): { table_fqn?: string | null; sql?: string | null } =>
    sourceMode === "table" ? { table_fqn: tableFqn.trim() } : { sql: sql.trim() };

  // ── Step 1 handlers ──────────────────────────────────────────────────────
  const setConnField = (key: keyof ConnForm, value: string) => {
    setConn((prev) => ({ ...prev, [key]: value }));
    // Any credential edit invalidates a prior passing test (Continue re-gates).
    setOkFingerprint(null);
    setTestError(null);
  };

  const handleTest = async () => {
    setTestError(null);
    setTesting(true);
    try {
      // Reuse the stored id if nothing changed since the last create; otherwise
      // mint a fresh connection (#26). A changed credential MUST NOT test the
      // old id.
      let active = connection;
      if (!active || connFingerprint !== fingerprint) {
        const req: SnowflakeConnectionRequest = {
          name: conn.name.trim(),
          kind: "snowflake",
          account: conn.account.trim(),
          user: conn.user.trim(),
          password: conn.password, // sent byte-for-byte; whitespace can matter
          warehouse: conn.warehouse.trim(),
          role: conn.role.trim(),
          database: conn.database.trim(),
          schema: conn.schema.trim() || null,
        };
        active = await createFeatureStore(req);
        setConnection(active);
        setConnFingerprint(fingerprint);
        // A fresh connection invalidates a previously-profiled mapping (#27):
        // the columns may differ, so force a re-profile on next Map entry.
        setColumns(null);
        setSuggestion(null);
        setMapping({});
        setMapPhase("idle");
      }
      await testFeatureStore(active.id); // 204 on success, throws on failure
      setOkFingerprint(fingerprint);
    } catch (e) {
      setTestError(apiErrorParts(e));
      setOkFingerprint(null);
    } finally {
      setTesting(false);
    }
  };

  // ── Step 2 · profile + suggest (#27) ─────────────────────────────────────
  // Runs on entry to Map when columns aren't loaded yet. Re-runnable via the
  // retry button if profiling failed.
  const loadMapping = useCallback(async () => {
    if (!connection) return;
    setMapError(null);
    setMapPhase("profiling");
    try {
      const preview = await previewFeatureStore(connection.id, sourceBody());
      setColumns(preview.columns);
      setRowCount(preview.row_count);
      setMapPhase("suggesting");
      const sugg = await suggestMapping(connection.id, preview.columns);
      setSuggestion(sugg);
      // Pre-fill: each suggested group's columns adopt that group; unmapped
      // columns start unresolved ("") and MUST be resolved before Continue.
      const next: Record<string, Assignment | ""> = {};
      for (const col of preview.columns) next[col.name] = "";
      for (const group of FEATURE_GROUPS) {
        for (const a of sugg[group]) next[a.column] = group;
      }
      // unmapped stays "" (already defaulted above).
      setMapping(next);
      setMapPhase("ready");
    } catch (e) {
      setMapError(apiErrorMessage(e));
      setMapPhase("error");
    }
    // sourceBody is derived from current state; intentionally re-created each
    // call. We don't want it in deps (it'd change every render).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connection]);

  // Auto-load the mapping the first time Map is shown (#27 "on entry").
  useEffect(() => {
    if (step === 2 && connection && columns === null && mapPhase === "idle") {
      void loadMapping();
    }
  }, [step, connection, columns, mapPhase, loadMapping]);

  // Build a confidence lookup from the suggestion so each column row can show
  // its model confidence chip (#27).
  const confidenceFor = (colName: string): ColumnAssignment | null => {
    if (!suggestion) return null;
    for (const group of FEATURE_GROUPS) {
      const hit = suggestion[group].find((a) => a.column === colName);
      if (hit) return hit;
    }
    return suggestion.unmapped.find((a) => a.column === colName) ?? null;
  };

  const setColAssignment = (colName: string, value: Assignment | "") =>
    setMapping((prev) => ({ ...prev, [colName]: value }));

  // Every column resolved (one of the 7 groups, or "ignore") → Map may close.
  const allResolved =
    columns !== null && columns.length > 0 && columns.every((c) => mapping[c.name] && mapping[c.name] !== "");

  // ── Step 4 · trigger (#28) ───────────────────────────────────────────────
  const handleStartBuild = async () => {
    if (!connection) return;
    setTriggerError(null);
    setTriggering(true);
    try {
      // column_mapping: each column → its group, "ignore" → null. Only mapped
      // columns are sent with a group; ignored ones go through as null so the
      // backend records the explicit decision.
      const column_mapping: Record<string, FeatureGroup | null> = {};
      if (columns) {
        for (const c of columns) {
          const a = mapping[c.name];
          column_mapping[c.name] = a && a !== "ignore" ? a : null;
        }
      }
      const source_query =
        sourceMode === "sql" ? sql.trim() : `SELECT * FROM ${tableFqn.trim()}`;
      const config: BuildConfig = {
        connection_id: connection.id,
        source_query,
        column_mapping,
        k,
        stability_threshold: stabilityThreshold,
        llm_provider: llmProvider,
        weight_schemes: weightSchemes,
      };
      const summary = await createPersonaBuild(config);
      setBuild(summary);
      setEvents([]);
      setStep(5); // auto-advance to Watch
    } catch (e) {
      setTriggerError(apiErrorMessage(e));
    } finally {
      setTriggering(false);
    }
  };

  // ── Step 5 · watch poll (#28) ────────────────────────────────────────────
  // Polls the build + events every ~2.5s while pending/running; stops on a
  // terminal status. The id is stable so the interval survives across beats.
  const watchId = build && !isBuildTerminal(build.status) ? build.id : null;
  const buildIdRef = useRef<string | null>(null);
  buildIdRef.current = build?.id ?? null;
  useEffect(() => {
    if (!watchId) return;
    let cancelled = false;
    const tick = async () => {
      try {
        const [next, evs] = await Promise.all([
          getPersonaBuild(watchId),
          getPersonaBuildEvents(watchId).catch(() => [] as BuildEvent[]),
        ]);
        if (cancelled) return;
        setBuild(next);
        setEvents(evs);
      } catch {
        // Transient read failure — the next beat retries; the row keeps its
        // last-known status by design.
      }
    };
    void tick(); // immediate first beat so Watch isn't blank for 2.5s
    const interval = setInterval(tick, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [watchId]);

  // ── Step 6 · promote (#28) ───────────────────────────────────────────────
  const handlePromote = async () => {
    if (!build?.pack_version) return;
    setPromoteError(null);
    setPromoting(true);
    try {
      setPromoted(await promotePersonaPack(build.pack_version));
    } catch (e) {
      setPromoteError(apiErrorMessage(e));
    } finally {
      setPromoting(false);
    }
  };

  // ── per-step Continue gating ─────────────────────────────────────────────
  const canContinue = (): boolean => {
    switch (step) {
      case 1:
        return testPassed; // a test must have succeeded for the current values
      case 2:
        return allResolved; // every column assigned or explicitly ignored
      case 3:
        return true; // persona-target always has a value (defaults to auto)
      case 4:
        return false; // advancing happens via Start build, not Next
      case 5:
        return build?.status === "complete"; // Continue→Promote only when done
      case 6:
        return promoted !== null; // Continue→Done only after promote
      case 7:
        return false;
      default:
        return false;
    }
  };

  const goBack = () => setStep((s) => Math.max(1, s - 1));
  const goNext = () => {
    if (canContinue()) setStep((s) => Math.min(LAST_STEP, s + 1));
  };

  // Steps 4 and 7 have no Next furniture (4 uses Start build; 7 is terminal).
  const showNext = step !== 4 && step !== LAST_STEP;

  return (
    <main style={{ fontFamily: FONT_SANS, color: TOKENS.ink }}>
      {/* Page strip — same zone grammar as crawl-setup (DESIGN.md §7) */}
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
        <h1 style={{ margin: 0, fontSize: 20, fontWeight: 600, letterSpacing: "-0.01em" }}>
          New persona pack
        </h1>
        <span
          style={{
            fontFamily: FONT_MONO,
            fontSize: 11,
            color: TOKENS.inkMuted,
            letterSpacing: "0.06em",
            ...TNUM,
          }}
        >
          STEP {String(step).padStart(2, "0")} / {String(LAST_STEP).padStart(2, "0")} ·{" "}
          {STEPS[step - 1].label.toUpperCase()}
        </span>
        <span
          style={{
            marginLeft: "auto",
            fontFamily: FONT_MONO,
            fontSize: 10,
            letterSpacing: "0.08em",
            color: TOKENS.inkMuted,
            border: `0.75px solid ${TOKENS.rule}`,
            borderRadius: 2,
            padding: "3px 8px",
            whiteSpace: "nowrap",
          }}
        >
          GENERATED FROM YOUR DATA — VERSIONED, PROMOTE-GATED
        </span>
      </header>

      <Stepper current={step} />

      {/* Step body. Each step renders inside the form zone; some steps add an
          inspector rail to mirror crawl-setup's two-zone layout. */}
      <div style={{ padding: 24, maxWidth: 760 }}>
        {step === 1 && (
          <StepConnect
            conn={conn}
            sourceMode={sourceMode}
            tableFqn={tableFqn}
            sql={sql}
            testing={testing}
            testPassed={testPassed}
            testError={testError}
            onField={setConnField}
            onSourceMode={(m) => {
              setSourceMode(m);
              setOkFingerprint(null);
            }}
            onTableFqn={(v) => {
              setTableFqn(v);
              setOkFingerprint(null);
            }}
            onSql={(v) => {
              setSql(v);
              setOkFingerprint(null);
            }}
            onTest={handleTest}
          />
        )}

        {step === 2 && (
          <StepMap
            phase={mapPhase}
            error={mapError}
            columns={columns}
            rowCount={rowCount}
            suggestion={suggestion}
            mapping={mapping}
            allResolved={allResolved}
            confidenceFor={confidenceFor}
            onAssign={setColAssignment}
            onRetry={() => {
              setMapPhase("idle");
              setColumns(null);
            }}
          />
        )}

        {step === 3 && (
          <StepReview
            connection={connection}
            sourceMode={sourceMode}
            tableFqn={tableFqn}
            sql={sql}
            columns={columns}
            mapping={mapping}
            k={k}
            onK={setK}
          />
        )}

        {step === 4 && (
          <StepTrigger
            k={k}
            stabilityThreshold={stabilityThreshold}
            llmProvider={llmProvider}
            weightSchemes={weightSchemes}
            triggering={triggering}
            triggerError={triggerError}
            hasBuild={build !== null}
            onStabilityThreshold={setStabilityThreshold}
            onLlmProvider={setLlmProvider}
            onStart={handleStartBuild}
          />
        )}

        {step === 5 && (
          <StepWatch
            build={build}
            events={events}
            onRetry={() => {
              // Re-trigger from step 4 with a clean slate (#28). Clearing the
              // build is what lets Start build run again — Back alone never
              // re-triggers.
              setBuild(null);
              setEvents([]);
              setTriggerError(null);
              setStep(4);
            }}
          />
        )}

        {step === 6 && (
          <StepPromote
            build={build}
            promoting={promoting}
            promoted={promoted}
            promoteError={promoteError}
            onPromote={handlePromote}
          />
        )}

        {step === 7 && <StepDone build={build} promoted={promoted} />}

        {/* ── Back / Next nav ────────────────────────────────────────────── */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginTop: 32,
            paddingTop: 16,
            borderTop: `0.75px solid ${TOKENS.rule}`,
          }}
        >
          <button
            type="button"
            onClick={goBack}
            disabled={step === 1}
            style={{
              ...secondaryBtnStyle,
              opacity: step === 1 ? 0.5 : 1,
              cursor: step === 1 ? "not-allowed" : "pointer",
            }}
          >
            ← Back
          </button>
          {showNext && (
            <button
              type="button"
              onClick={goNext}
              disabled={!canContinue()}
              style={{
                ...primaryBtnStyle,
                opacity: canContinue() ? 1 : 0.5,
                cursor: canContinue() ? "pointer" : "not-allowed",
              }}
            >
              {step === 5 ? "Continue → Promote" : step === 6 ? "Continue → Done" : "Next →"}
            </button>
          )}
        </div>
      </div>
    </main>
  );
}

// ── Stepper — restyled to instrument posture ────────────────────────────────
function Stepper({ current }: { current: number }) {
  return (
    <div
      style={{
        display: "flex",
        gap: 0,
        borderBottom: `0.75px solid ${TOKENS.rule}`,
        background: TOKENS.paperElevated,
      }}
    >
      {STEPS.map((s) => {
        const active = s.id === current;
        const done = s.id < current;
        return (
          <div
            key={s.id}
            style={{
              flex: 1,
              padding: "10px 14px",
              borderRight: s.id < STEPS.length ? `0.75px solid ${TOKENS.rule}` : "none",
              // Active step carries an ink underline (the only emphasis), done
              // steps recess. No color state — meaning rides the wording.
              borderBottom: active ? `1.5px solid ${TOKENS.ink}` : "1.5px solid transparent",
              background: done ? TOKENS.paperRecessed : "transparent",
            }}
          >
            <div
              style={{
                fontFamily: FONT_MONO,
                fontSize: 10,
                letterSpacing: "0.1em",
                color: TOKENS.inkMuted,
                ...TNUM,
              }}
            >
              {String(s.id).padStart(2, "0")}
              {done ? " ✓" : ""}
            </div>
            <div
              style={{
                fontSize: 13,
                marginTop: 2,
                color: active ? TOKENS.ink : TOKENS.inkMuted,
                fontWeight: active ? 600 : 400,
              }}
            >
              {s.label}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Step 1 · Connect (#26)
// ════════════════════════════════════════════════════════════════════════════
function StepConnect({
  conn,
  sourceMode,
  tableFqn,
  sql,
  testing,
  testPassed,
  testError,
  onField,
  onSourceMode,
  onTableFqn,
  onSql,
  onTest,
}: {
  conn: ConnForm;
  sourceMode: SourceMode;
  tableFqn: string;
  sql: string;
  testing: boolean;
  testPassed: boolean;
  testError: { kind: string | null; message: string } | null;
  onField: (k: keyof ConnForm, v: string) => void;
  onSourceMode: (m: SourceMode) => void;
  onTableFqn: (v: string) => void;
  onSql: (v: string) => void;
  onTest: () => void;
}) {
  // Required credential fields must be filled before a test is meaningful;
  // schema is optional. This only enables the Test button — the real gate is
  // a 204 from the backend.
  const credsFilled =
    conn.name.trim() &&
    conn.account.trim() &&
    conn.user.trim() &&
    conn.password &&
    conn.warehouse.trim() &&
    conn.role.trim() &&
    conn.database.trim();
  const sourceFilled = sourceMode === "table" ? tableFqn.trim() : sql.trim();
  const canTest = Boolean(credsFilled && sourceFilled) && !testing;

  const Field = (key: keyof ConnForm, label: string, placeholder: string, type = "text") => (
    <div>
      <label htmlFor={`conn-${key}`} style={sublabelStyle}>
        {label}
      </label>
      <input
        id={`conn-${key}`}
        type={type}
        value={conn[key]}
        onChange={(e) => onField(key, e.target.value)}
        placeholder={placeholder}
        autoComplete="off"
        style={monoInputStyle}
      />
    </div>
  );

  return (
    <div style={{ maxWidth: 620 }}>
      {testError && (
        <div role="alert" style={errorBannerStyle}>
          {testError.kind ? `${testError.kind} · ` : ""}
          {testError.message}
        </div>
      )}

      {/* ── 01 · Snowflake credentials ──────────────────────────────────── */}
      <section>
        <div style={sectionLabelStyle}>01 · Snowflake credentials</div>
        <div style={fieldStyle}>{Field("name", "Connection name", "e.g. prod-analytics")}</div>
        <div style={{ ...fieldStyle, ...fieldRowStyle }}>
          {Field("account", "Account", "xy12345.us-east-1")}
          {Field("user", "User", "SIDIRA_READER")}
        </div>
        <div style={fieldStyle}>{Field("password", "Password", "••••••••", "password")}</div>
        <div style={{ ...fieldStyle, ...fieldRowStyle }}>
          {Field("warehouse", "Warehouse", "COMPUTE_WH")}
          {Field("role", "Role", "SIDIRA_RO")}
        </div>
        <div style={{ ...fieldStyle, ...fieldRowStyle }}>
          {Field("database", "Database", "ANALYTICS")}
          {Field("schema", "Schema (optional)", "PUBLIC")}
        </div>
        <div style={hintStyle}>
          A read-only role on a non-production warehouse is plenty — the builder
          only profiles and samples. The password is sent once to test and store
          the connection; it is never echoed back.
        </div>
      </section>

      {/* ── 02 · Source ─────────────────────────────────────────────────── */}
      <section style={sectionStyle}>
        <div style={sectionLabelStyle}>02 · Source</div>
        <div style={{ ...fieldStyle, display: "flex", gap: 8 }}>
          {(["table", "sql"] as SourceMode[]).map((m) => {
            const active = sourceMode === m;
            return (
              <button
                key={m}
                type="button"
                onClick={() => onSourceMode(m)}
                style={{
                  ...secondaryBtnStyle,
                  fontFamily: FONT_MONO,
                  fontSize: 11,
                  letterSpacing: "0.06em",
                  background: active ? TOKENS.ink : "transparent",
                  color: active ? TOKENS.paper : TOKENS.ink,
                }}
              >
                {m === "table" ? "TABLE" : "SQL"}
              </button>
            );
          })}
        </div>
        {sourceMode === "table" ? (
          <div style={fieldStyle}>
            <label htmlFor="src-table" style={sublabelStyle}>
              Table (fully qualified)
            </label>
            <input
              id="src-table"
              value={tableFqn}
              onChange={(e) => onTableFqn(e.target.value)}
              placeholder="DB.SCHEMA.TABLE"
              style={monoInputStyle}
            />
            <div style={hintStyle}>
              The population to model — one row per user/account. We build the
              persona pack from <code>SELECT * FROM {tableFqn.trim() || "DB.SCHEMA.TABLE"}</code>.
            </div>
          </div>
        ) : (
          <div style={fieldStyle}>
            <label htmlFor="src-sql" style={sublabelStyle}>
              SQL SELECT
            </label>
            <textarea
              id="src-sql"
              value={sql}
              onChange={(e) => onSql(e.target.value)}
              placeholder={"SELECT user_id, plan, mrr, signup_date, last_seen\nFROM analytics.users\nWHERE active"}
              style={textareaStyle}
            />
            <div style={hintStyle}>
              Any SELECT that returns one row per population member. Run exactly
              as written — no wrapping, no LIMIT injected.
            </div>
          </div>
        )}
      </section>

      {/* ── 03 · Test connection ────────────────────────────────────────── */}
      <section style={sectionStyle}>
        <div style={sectionLabelStyle}>03 · Test connection</div>
        <div style={{ ...fieldStyle, display: "flex", alignItems: "center", gap: 12 }}>
          <button
            type="button"
            onClick={onTest}
            disabled={!canTest}
            style={{
              ...secondaryBtnStyle,
              opacity: canTest ? 1 : 0.5,
              cursor: canTest ? "pointer" : "not-allowed",
            }}
          >
            {testing ? "Testing…" : "Test connection"}
          </button>
          {/* Honest-text result line (§8.6) — never a spinner GIF. */}
          {testing && <span style={{ ...statusLineStyle, color: TOKENS.inkMuted }}>TESTING · CONNECTING…</span>}
          {!testing && testPassed && (
            <span style={statusLineStyle}>✓ CONNECTION OK</span>
          )}
        </div>
        <div style={hintStyle}>
          Continue unlocks only after a test succeeds for these exact values —
          edit any field and you&apos;ll need to test again.
        </div>
      </section>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Step 2 · Map (#27)
// ════════════════════════════════════════════════════════════════════════════
function StepMap({
  phase,
  error,
  columns,
  rowCount,
  suggestion,
  mapping,
  allResolved,
  confidenceFor,
  onAssign,
  onRetry,
}: {
  phase: "idle" | "profiling" | "suggesting" | "ready" | "error";
  error: string | null;
  columns: ColumnProfile[] | null;
  rowCount: number | null;
  suggestion: MappingSuggestion | null;
  mapping: Record<string, Assignment | "">;
  allResolved: boolean;
  confidenceFor: (col: string) => ColumnAssignment | null;
  onAssign: (col: string, v: Assignment | "") => void;
  onRetry: () => void;
}) {
  // Honest loading text (§8.6) — a subtle line, no spinner.
  if (phase === "profiling" || phase === "suggesting" || phase === "idle") {
    return (
      <div style={{ ...statusLineStyle, color: TOKENS.inkMuted, marginTop: 8 }}>
        {phase === "suggesting" ? "SUGGESTING COLUMN GROUPS…" : "PROFILING TABLE…"}
      </div>
    );
  }
  if (phase === "error") {
    return (
      <div style={{ maxWidth: 620 }}>
        <div role="alert" style={errorBannerStyle}>
          {error ?? "The table could not be profiled."}
        </div>
        <button type="button" onClick={onRetry} style={secondaryBtnStyle}>
          Retry profiling
        </button>
      </div>
    );
  }
  if (!columns || !suggestion) return null;

  // Group the columns by their CURRENT assignment for display. We render the 7
  // canonical groups in order, an Ignored bucket, then an Unmapped section for
  // columns the model didn't place that are still unresolved.
  const byGroup: Record<FeatureGroup, ColumnProfile[]> = {
    demographic_identity: [],
    behavioral_patterns: [],
    motivations_jtbd: [],
    pain_points_friction: [],
    value_sensitivity: [],
    channel_tech_behavior: [],
    loyalty_lifecycle: [],
  };
  const ignored: ColumnProfile[] = [];
  const unresolved: ColumnProfile[] = [];

  for (const col of columns) {
    const a = mapping[col.name];
    if (a === "ignore") ignored.push(col);
    else if (a) byGroup[a].push(col); // a is a FeatureGroup here
    else unresolved.push(col); // "" — still needs a decision (incl. unmapped)
  }

  const resolvedCount = columns.filter((c) => mapping[c.name] && mapping[c.name] !== "").length;

  return (
    <div style={{ maxWidth: 680 }}>
      <div style={{ ...railCaptionStyle, marginBottom: 4 }}>
        {rowCount !== null ? `${rowCount.toLocaleString()} SAMPLE ROWS · ` : ""}
        {columns.length} COLUMNS · {resolvedCount}/{columns.length} RESOLVED
      </div>
      <div style={hintStyle}>
        Every column must land in one of the seven groups or be set to{" "}
        <strong>ignore</strong>. Suggestions are the model&apos;s best guess — the
        confidence chip tells you how sure it is. Continue unlocks when nothing is
        unresolved.
      </div>

      {/* The 7 canonical groups, in order. */}
      {FEATURE_GROUPS.map((group) => (
        <MapGroup
          key={group}
          title={GROUP_LABELS[group]}
          groupId={group}
          cols={byGroup[group]}
          mapping={mapping}
          confidenceFor={confidenceFor}
          onAssign={onAssign}
        />
      ))}

      {/* Ignored bucket — explicit decisions, not omissions. */}
      {ignored.length > 0 && (
        <MapGroup
          title="Ignored"
          groupId={null}
          cols={ignored}
          mapping={mapping}
          confidenceFor={confidenceFor}
          onAssign={onAssign}
        />
      )}

      {/* Unmapped — columns the model didn't place; start unresolved. */}
      <section style={sectionStyle}>
        <div style={sectionLabelStyle}>
          Unmapped {unresolved.length > 0 ? `· ${unresolved.length} NEED A DECISION` : "· NONE"}
        </div>
        {unresolved.length === 0 ? (
          <div style={{ ...railCaptionStyle, marginTop: 10 }}>
            ALL COLUMNS RESOLVED.
          </div>
        ) : (
          unresolved.map((col) => (
            <ColumnRow
              key={col.name}
              col={col}
              value={mapping[col.name] ?? ""}
              assignment={confidenceFor(col.name)}
              onAssign={(v) => onAssign(col.name, v)}
              unresolved
            />
          ))
        )}
      </section>

      {!allResolved && (
        <div style={{ ...railCaptionStyle, marginTop: 16, color: TOKENS.ink }}>
          {columns.length - resolvedCount} COLUMN(S) STILL UNRESOLVED — ASSIGN OR IGNORE EACH TO CONTINUE.
        </div>
      )}
    </div>
  );
}

function MapGroup({
  title,
  groupId,
  cols,
  mapping,
  confidenceFor,
  onAssign,
}: {
  title: string;
  groupId: FeatureGroup | null;
  cols: ColumnProfile[];
  mapping: Record<string, Assignment | "">;
  confidenceFor: (col: string) => ColumnAssignment | null;
  onAssign: (col: string, v: Assignment | "") => void;
}) {
  return (
    <section style={sectionStyle}>
      <div style={sectionLabelStyle}>
        {title} {cols.length > 0 ? `· ${cols.length}` : "· —"}
      </div>
      {cols.length === 0 ? (
        <div style={{ ...railCaptionStyle, marginTop: 10 }}>NO COLUMNS ASSIGNED.</div>
      ) : (
        cols.map((col) => (
          <ColumnRow
            key={col.name}
            col={col}
            value={mapping[col.name] ?? (groupId ?? "")}
            assignment={confidenceFor(col.name)}
            onAssign={(v) => onAssign(col.name, v)}
          />
        ))
      )}
    </section>
  );
}

function ColumnRow({
  col,
  value,
  assignment,
  onAssign,
  unresolved = false,
}: {
  col: ColumnProfile;
  value: Assignment | "";
  assignment: ColumnAssignment | null;
  onAssign: (v: Assignment | "") => void;
  unresolved?: boolean;
}) {
  const sample =
    col.sample_values && col.sample_values.length > 0 ? col.sample_values[0] : null;
  return (
    <div
      style={{
        ...fieldStyle,
        display: "grid",
        gridTemplateColumns: "1fr auto",
        gap: 12,
        alignItems: "center",
        // Unresolved rows carry an alert hairline (border-only, message in
        // wording) so the eye lands on what still needs a decision (§4.3).
        border: unresolved ? `0.75px solid ${TOKENS.alert}` : "none",
        borderRadius: unresolved ? 2 : 0,
        padding: unresolved ? "8px 10px" : 0,
        background: unresolved ? TOKENS.paperRecessed : "transparent",
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
          <span style={{ fontFamily: FONT_MONO, fontSize: 13, color: TOKENS.ink }}>{col.name}</span>
          <Chip>{col.dtype}</Chip>
          {assignment && <Chip>{assignment.confidence.toUpperCase()}</Chip>}
        </div>
        <div
          style={{
            ...railCaptionStyle,
            marginTop: 3,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {sample !== null ? `e.g. ${String(sample)}` : "no sample value"}
          {col.null_fraction > 0 ? ` · ${Math.round(col.null_fraction * 100)}% null` : ""}
        </div>
      </div>
      <select
        aria-label={`Group for ${col.name}`}
        value={value}
        onChange={(e) => onAssign(e.target.value as Assignment | "")}
        style={{ ...selectStyle, width: 220 }}
      >
        <option value="">— choose —</option>
        {FEATURE_GROUPS.map((g) => (
          <option key={g} value={g}>
            {GROUP_LABELS[g]}
          </option>
        ))}
        <option value="ignore">Ignore this column</option>
      </select>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Step 3 · Review (#28)
// ════════════════════════════════════════════════════════════════════════════
function StepReview({
  connection,
  sourceMode,
  tableFqn,
  sql,
  columns,
  mapping,
  k,
  onK,
}: {
  connection: ConnectionSummary | null;
  sourceMode: SourceMode;
  tableFqn: string;
  sql: string;
  columns: ColumnProfile[] | null;
  mapping: Record<string, Assignment | "">;
  k: BuildK;
  onK: (k: BuildK) => void;
}) {
  // Build the per-group column lists from the resolved mapping.
  const groupCols = (group: FeatureGroup) =>
    (columns ?? []).filter((c) => mapping[c.name] === group).map((c) => c.name);
  const ignoredCols = (columns ?? []).filter((c) => mapping[c.name] === "ignore").map((c) => c.name);

  return (
    <div style={{ maxWidth: 680 }}>
      {/* ── Connection + source recap ───────────────────────────────────── */}
      <section>
        <div style={sectionLabelStyle}>Connection &amp; source</div>
        <dl
          style={{
            margin: 0,
            marginTop: 12,
            display: "grid",
            gridTemplateColumns: "auto 1fr",
            gap: "4px 16px",
          }}
        >
          {[
            ["Connection", connection ? connection.name : "—"],
            ["Account", connection ? connection.account : "—"],
            ["Database", connection ? `${connection.database}${connection.schema ? `.${connection.schema}` : ""}` : "—"],
            ["Warehouse / role", connection ? `${connection.warehouse} · ${connection.role}` : "—"],
            ["Source", sourceMode === "table" ? `TABLE · ${tableFqn.trim()}` : "SQL SELECT"],
          ].map(([dt, dd]) => (
            <div key={dt} style={{ display: "contents" }}>
              <dt style={{ fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", color: TOKENS.inkMuted }}>
                {dt}
              </dt>
              <dd style={{ margin: 0, fontFamily: FONT_MONO, fontSize: 12, color: TOKENS.ink, overflowWrap: "break-word", ...TNUM }}>
                {dd}
              </dd>
            </div>
          ))}
        </dl>
        {sourceMode === "sql" && (
          <pre
            style={{
              marginTop: 10,
              padding: "10px 12px",
              background: TOKENS.paperRecessed,
              border: `0.75px solid ${TOKENS.rule}`,
              borderRadius: 2,
              fontFamily: FONT_MONO,
              fontSize: 12,
              color: TOKENS.ink,
              whiteSpace: "pre-wrap",
              overflowWrap: "break-word",
            }}
          >
            {sql.trim()}
          </pre>
        )}
      </section>

      {/* ── Mapping summary — 7 groups, then ignored ────────────────────── */}
      <section style={sectionStyle}>
        <div style={sectionLabelStyle}>Column mapping</div>
        <dl style={{ margin: 0, marginTop: 12, display: "grid", gridTemplateColumns: "auto 1fr", gap: "6px 16px" }}>
          {FEATURE_GROUPS.map((group) => {
            const cols = groupCols(group);
            return (
              <div key={group} style={{ display: "contents" }}>
                <dt style={{ fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", color: TOKENS.inkMuted }}>
                  {GROUP_LABELS[group]}
                </dt>
                <dd style={{ margin: 0, fontFamily: FONT_MONO, fontSize: 12, color: cols.length ? TOKENS.ink : TOKENS.inkMuted, overflowWrap: "break-word" }}>
                  {cols.length ? cols.join(" · ") : "—"}
                </dd>
              </div>
            );
          })}
          {ignoredCols.length > 0 && (
            <div style={{ display: "contents" }}>
              <dt style={{ fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", color: TOKENS.inkMuted }}>
                Ignored
              </dt>
              <dd style={{ margin: 0, fontFamily: FONT_MONO, fontSize: 12, color: TOKENS.inkMuted, overflowWrap: "break-word" }}>
                {ignoredCols.join(" · ")}
              </dd>
            </div>
          )}
        </dl>
      </section>

      {/* ── Persona target (config.k) ───────────────────────────────────── */}
      <section style={sectionStyle}>
        <div style={sectionLabelStyle}>Persona target</div>
        <div style={fieldStyle}>
          <label htmlFor="persona-k" style={sublabelStyle}>
            How many personas?
          </label>
          <select
            id="persona-k"
            value={String(k)}
            onChange={(e) => onK(e.target.value === "auto" ? "auto" : Number(e.target.value))}
            style={{ ...selectStyle, width: 280 }}
          >
            <option value="auto">AUTO · LET THE PIPELINE CHOOSE</option>
            {[6, 7, 8, 9, 10, 11, 12].map((n) => (
              <option key={n} value={n}>
                {n} PERSONAS
              </option>
            ))}
          </select>
          <div style={hintStyle}>
            Auto picks the count with the best stability for your population.
            Pin a number only if you have a target segmentation in mind.
          </div>
        </div>
      </section>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Step 4 · Trigger (#28)
// ════════════════════════════════════════════════════════════════════════════
function StepTrigger({
  k,
  stabilityThreshold,
  llmProvider,
  weightSchemes,
  triggering,
  triggerError,
  hasBuild,
  onStabilityThreshold,
  onLlmProvider,
  onStart,
}: {
  k: BuildK;
  stabilityThreshold: number;
  llmProvider: LlmProvider;
  weightSchemes: WeightScheme[];
  triggering: boolean;
  triggerError: string | null;
  hasBuild: boolean;
  onStabilityThreshold: (v: number) => void;
  onLlmProvider: (v: LlmProvider) => void;
  onStart: () => void;
}) {
  return (
    <div style={{ maxWidth: 620 }}>
      {triggerError && (
        <div role="alert" style={errorBannerStyle}>
          {triggerError}
        </div>
      )}

      <section>
        <div style={sectionLabelStyle}>Final build config</div>
        <dl style={{ margin: 0, marginTop: 12, display: "grid", gridTemplateColumns: "auto 1fr", gap: "4px 16px" }}>
          {[
            ["Persona target", k === "auto" ? "AUTO" : `${k} PERSONAS`],
            ["Weight schemes", weightSchemes.map((w) => w.toUpperCase()).join(" · ")],
          ].map(([dt, dd]) => (
            <div key={dt} style={{ display: "contents" }}>
              <dt style={{ fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", color: TOKENS.inkMuted }}>
                {dt}
              </dt>
              <dd style={{ margin: 0, fontFamily: FONT_MONO, fontSize: 12, color: TOKENS.ink, ...TNUM }}>{dd}</dd>
            </div>
          ))}
        </dl>

        <div style={{ ...fieldStyle, ...fieldRowStyle }}>
          <div>
            <label htmlFor="stability" style={sublabelStyle}>
              Stability threshold
            </label>
            <input
              id="stability"
              type="number"
              min={0}
              max={1}
              step={0.05}
              value={stabilityThreshold}
              onChange={(e) => onStabilityThreshold(Number(e.target.value))}
              style={monoInputStyle}
            />
          </div>
          <div>
            <label htmlFor="llm" style={sublabelStyle}>
              Naming model
            </label>
            <select
              id="llm"
              value={llmProvider}
              onChange={(e) => onLlmProvider(e.target.value as LlmProvider)}
              style={selectStyle}
            >
              <option value="groq">GROQ · DEFAULT</option>
              <option value="anthropic">ANTHROPIC</option>
            </select>
          </div>
        </div>
        <div style={hintStyle}>
          The threshold (default 0.65) is the floor a clustering must clear to be
          accepted. The naming model writes each persona&apos;s name, description,
          and jobs-to-be-done from its centroid.
        </div>
      </section>

      <section style={sectionStyle}>
        <button
          type="button"
          onClick={onStart}
          disabled={triggering}
          style={{
            ...primaryBtnStyle,
            opacity: triggering ? 0.5 : 1,
            cursor: triggering ? "not-allowed" : "pointer",
          }}
        >
          {triggering ? "Starting…" : "Start build"}
        </button>
        <div style={hintStyle}>
          {hasBuild
            ? "A build was already started from this wizard — starting again creates a NEW build."
            : "The build runs server-side; the next step watches it live. Closing the tab doesn’t stop it."}
        </div>
      </section>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Step 5 · Watch (#28)
// ════════════════════════════════════════════════════════════════════════════

// Map a build status to an honest status line (§8.6).
function buildStatusLine(b: BuildSummary): string {
  switch (b.status) {
    case "pending":
      return "PENDING · QUEUED";
    case "running":
      return "RUNNING · CLUSTERING + NAMING";
    case "complete":
      return b.pack_version
        ? `COMPLETE · PACK ${b.pack_version}`
        : "COMPLETE";
    case "failed":
      return "FAILED";
  }
}

// Render one build event as a readable line (#28) — never raw JSON.
function eventLine(ev: BuildEvent): string {
  const p = ev.payload ?? {};
  switch (ev.type) {
    case "run.started":
      return "BUILD STARTED";
    case "packs.loaded":
      return `LOADED ${p.row_count ?? "?"} SOURCE ROWS`;
    case "score.updated":
      return `STABILITY ${p.stability_score ?? "?"} · ${p.persona_count ?? "?"} PERSONAS`;
    case "run.complete":
      return `COMPLETE · PACK ${p.pack_version ?? "?"} · STABILITY ${p.stability_score ?? "?"}`;
    case "run.failed":
      return `FAILED · ${p.error ?? "unknown error"}`;
    default:
      return String(ev.type).toUpperCase();
  }
}

function StepWatch({
  build,
  events,
  onRetry,
}: {
  build: BuildSummary | null;
  events: BuildEvent[];
  onRetry: () => void;
}) {
  if (!build) {
    return (
      <div style={{ ...statusLineStyle, color: TOKENS.inkMuted }}>
        NO BUILD STARTED YET — GO BACK TO TRIGGER.
      </div>
    );
  }
  const failed = build.status === "failed";

  return (
    <div style={{ maxWidth: 680 }}>
      {/* Honest status line for the current build state (§8.6). */}
      <div style={{ display: "flex", alignItems: "baseline", gap: 12, flexWrap: "wrap" }}>
        <span style={statusLineStyle}>{buildStatusLine(build)}</span>
        <span style={railCaptionStyle}>BUILD {build.id}</span>
        <span style={railCaptionStyle}>STARTED {utcStamp(build.created_at)}</span>
        {build.completed_at && <span style={railCaptionStyle}>SETTLED {utcStamp(build.completed_at)}</span>}
      </div>

      {/* Live readings, when present. */}
      {(build.stability_score !== null || build.persona_count !== null) && (
        <div style={{ ...railCaptionStyle, marginTop: 6, color: TOKENS.ink }}>
          {build.stability_score !== null ? `STABILITY ${build.stability_score}` : ""}
          {build.stability_score !== null && build.persona_count !== null ? " · " : ""}
          {build.persona_count !== null ? `${build.persona_count} PERSONAS` : ""}
        </div>
      )}

      {/* Failure — surface the build's error and offer Retry (→ step 4). */}
      {failed && (
        <div style={{ marginTop: 14 }}>
          <div role="alert" style={errorBannerStyle}>
            {build.error ?? "The build failed without a reported reason."}
          </div>
          <button type="button" onClick={onRetry} style={secondaryBtnStyle}>
            Retry build
          </button>
        </div>
      )}

      {/* Event log — readable lines, newest last, each stamped UTC. */}
      <section style={sectionStyle}>
        <div style={sectionLabelStyle}>Build log</div>
        {events.length === 0 ? (
          <div style={{ ...statusLineStyle, color: TOKENS.inkMuted, marginTop: 10 }}>
            {isBuildTerminal(build.status) ? "NO EVENTS RECORDED." : "WAITING FOR THE FIRST EVENT…"}
          </div>
        ) : (
          <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 4 }}>
            {events.map((ev, i) => (
              <div key={`${ev.at}-${i}`} style={{ display: "flex", gap: 12 }}>
                <span style={{ ...railCaptionStyle, flexShrink: 0, width: 150 }}>{utcStamp(ev.at)}</span>
                <span style={{ fontFamily: FONT_MONO, fontSize: 12, color: TOKENS.ink, ...TNUM }}>
                  {eventLine(ev)}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {build.status === "complete" && (
        <div style={{ ...railCaptionStyle, marginTop: 14, color: TOKENS.ink }}>
          BUILD COMPLETE — CONTINUE TO PROMOTE THE PACK.
        </div>
      )}
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Step 6 · Promote (#28)
// ════════════════════════════════════════════════════════════════════════════
function StepPromote({
  build,
  promoting,
  promoted,
  promoteError,
  onPromote,
}: {
  build: BuildSummary | null;
  promoting: boolean;
  promoted: PackSummary | null;
  promoteError: string | null;
  onPromote: () => void;
}) {
  if (!build || build.status !== "complete" || !build.pack_version) {
    return (
      <div style={{ ...statusLineStyle, color: TOKENS.inkMuted }}>
        NO COMPLETE BUILD TO PROMOTE — GO BACK TO WATCH.
      </div>
    );
  }
  return (
    <div style={{ maxWidth: 620 }}>
      {promoteError && (
        <div role="alert" style={errorBannerStyle}>
          {promoteError}
        </div>
      )}
      <section>
        <div style={sectionLabelStyle}>Promote to latest</div>
        <div style={{ ...railCaptionStyle, marginTop: 12, color: TOKENS.ink }}>
          PACK {build.pack_version}
          {build.stability_score !== null ? ` · STABILITY ${build.stability_score}` : ""}
          {build.persona_count !== null ? ` · ${build.persona_count} PERSONAS` : ""}
        </div>
        <div style={hintStyle}>
          Promoting flips this pack to the latest pointer — new simulations pick
          it up. Existing simulations keep their frozen pack either way.
        </div>
        <div style={{ ...fieldStyle, display: "flex", alignItems: "center", gap: 12 }}>
          <button
            type="button"
            onClick={onPromote}
            disabled={promoting || promoted !== null}
            style={{
              ...primaryBtnStyle,
              opacity: promoting || promoted !== null ? 0.5 : 1,
              cursor: promoting || promoted !== null ? "not-allowed" : "pointer",
            }}
          >
            {promoting ? "Promoting…" : promoted ? "Promoted" : "Promote to latest"}
          </button>
          {promoted && (
            <span style={statusLineStyle}>
              ✓ PROMOTED · {promoted.version}
              {promoted.is_latest ? " · IS LATEST" : ""}
            </span>
          )}
        </div>
        {promoted && (
          <div style={{ ...okBannerStyle, marginTop: 12 }}>
            {promoted.version} is now the latest persona pack
            {promoted.promoted_at ? ` (promoted ${utcStamp(promoted.promoted_at)})` : ""}. Continue to finish.
          </div>
        )}
      </section>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Step 7 · Done (#28)
// ════════════════════════════════════════════════════════════════════════════
function StepDone({ build, promoted }: { build: BuildSummary | null; promoted: PackSummary | null }) {
  const version = promoted?.version ?? build?.pack_version ?? null;
  const stability = promoted?.stability_score ?? build?.stability_score ?? null;
  const personas = promoted?.persona_count ?? build?.persona_count ?? null;

  return (
    <div style={{ maxWidth: 620 }}>
      <section>
        <div style={sectionLabelStyle}>Pack ready</div>
        <div style={{ ...okBannerStyle, marginTop: 12 }}>
          Your persona pack is built and promoted. Point a simulation at it to put
          it to work.
        </div>
        <dl style={{ margin: 0, marginTop: 14, display: "grid", gridTemplateColumns: "auto 1fr", gap: "4px 16px" }}>
          {[
            ["Pack version", version ?? "—"],
            ["Stability", stability !== null ? String(stability) : "—"],
            ["Personas", personas !== null ? String(personas) : "—"],
          ].map(([dt, dd]) => (
            <div key={dt} style={{ display: "contents" }}>
              <dt style={{ fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", color: TOKENS.inkMuted }}>
                {dt}
              </dt>
              <dd style={{ margin: 0, fontFamily: FONT_MONO, fontSize: 12, color: TOKENS.ink, ...TNUM }}>{dd}</dd>
            </div>
          ))}
        </dl>

        <div style={{ ...fieldStyle, display: "flex", gap: 10, flexWrap: "wrap" }}>
          {version && (
            <a href={`/personas/${encodeURIComponent(version)}`} style={{ ...secondaryBtnStyle, textDecoration: "none", display: "inline-block" }}>
              View the pack →
            </a>
          )}
          <a href="/simulations/new" style={{ ...primaryBtnStyle, textDecoration: "none", display: "inline-block" }}>
            Run a simulation →
          </a>
        </div>
      </section>
    </div>
  );
}
