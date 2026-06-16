"use client";

// Persona Builder — self-serve 5-step wizard (Phase 4.5; #26 connect, #27 map,
// #28 build/promote, redesigned around EVALUATE-BEFORE-PROMOTE per #27/#28).
//
// REDESIGN RATIONALE (evaluate-before-promote): the original 7-step flow
// (Connect · Map · Review · Trigger · Watch · Promote · Done) promoted a pack
// the PM had never actually READ — Trigger/Watch were mechanical, and the only
// place to inspect the result was AFTER promotion. The point of a builder is
// judgement, not plumbing. So the flow collapses to 5 steps that put the
// reading where the decision is:
//
//   Connect · Map · Build · Evaluate · Promote
//
//   • Build merges the old Trigger+Watch — config and the live watch live on
//     ONE fire-and-watch step (the watch renders inline once a build exists).
//   • Evaluate is the NEW step and the whole reason for the redesign: it reads
//     the UNPROMOTED pack straight from R2 (getPersonaPackDetail works
//     pre-promote) and renders a COMPACT evaluation — shares, descriptions, a
//     distinctiveness one-liner per persona — so "these look right" is an
//     informed act, not a leap of faith.
//   • Promote folds in the old Done content (confirmation + the View / Run-a-
//     simulation CTAs) — promotion IS the terminal step.
//
// The wizard still owns ALL shared state here; each step renders against that
// lifted state and a small set of callbacks. Navigation is a top stepper plus
// Back/Next; "Next" is gated per-step (see canContinue) so a step can't be left
// until its contract is satisfied — a connection that TESTED OK (#26), a
// mapping where every column is resolved (#27), a build that reached
// `complete` (#28). On Evaluate, continuing IS the accept, so it's always open.
//
// Posture: instrument (DESIGN.md §7) — the visual vocabulary is the
// crawl-setup page's, imported from ./wizard-ui. Pending/loading/empty states
// are honest mono text, never spinners (§8.6). Errors use the paper-recessed
// note anatomy: message in ink, severity on the alert border (§4.3/§7.7).
// Confidence and distinctiveness ride the WORDING, never color.

import { useCallback, useEffect, useRef, useState } from "react";
import {
  createFeatureStore,
  createPersonaBuild,
  getPersonaBuild,
  getPersonaBuildEvents,
  getPersonaPackDetail,
  isBuildTerminal,
  listFeatureStores,
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
  type PersonaPackDetail,
  type PersonaProfileView,
  type ProfileBlockView,
  type SnowflakeConnectionRequest,
  type WeightScheme,
  FEATURE_GROUPS,
} from "@/lib/api";
import { TOKENS, FONT_SANS, FONT_MONO, TNUM } from "@/lib/design";
import {
  apiErrorMessage,
  apiErrorParts,
  Chip,
  errorBannerStyle,
  fieldRowStyle,
  fieldStyle,
  hintStyle,
  monoInputStyle,
  okBannerStyle,
  primaryBtnStyle,
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
// The redesigned 5-step flow. Build absorbs the old Trigger+Watch; Evaluate is
// the new reading step; Promote is terminal (folds in the old Done).
const STEPS = [
  { id: 1, label: "Connect" },
  { id: 2, label: "Map" },
  { id: 3, label: "Build" },
  { id: 4, label: "Evaluate" },
  { id: 5, label: "Promote" },
] as const;
const LAST_STEP = STEPS.length;

// Human labels for the 7 canonical feature groups (#27 map display). The ids
// stay machine-canonical (column_mapper.FeatureGroup); these are the
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
  // Saved connections (#304). These are the customer's persisted feature-store
  // rows — the server keeps the encrypted password (password_enc) and never
  // returns it, so a ConnectionSummary is everything we need to REUSE a
  // connection by id. listFeatureStores was defined but never called; surfacing
  // it here is the whole fix — select a saved row and you skip createFeatureStore
  // (and the password) entirely, because test/preview/mapping/build all operate
  // on connection.id against the stored credential.
  const [savedConns, setSavedConns] = useState<ConnectionSummary[]>([]);
  const [connsPhase, setConnsPhase] = useState<"loading" | "ready" | "error">("loading");

  // ── Step 2 · Map (#27) ──────────────────────────────────────────────────
  const [columns, setColumns] = useState<ColumnProfile[] | null>(null);
  const [rowCount, setRowCount] = useState<number | null>(null);
  const [suggestion, setSuggestion] = useState<MappingSuggestion | null>(null);
  const [mapping, setMapping] = useState<Record<string, Assignment | "">>({});
  const [mapPhase, setMapPhase] = useState<"idle" | "profiling" | "suggesting" | "ready" | "error">("idle");
  const [mapError, setMapError] = useState<string | null>(null);

  // ── Step 3 · Build config (#28) ─────────────────────────────────────────
  // The persona-target (k) moved here from the old Review step; it defaults to
  // AUTO (the recommended value).
  const [k, setK] = useState<BuildK>("auto");
  const [stabilityThreshold, setStabilityThreshold] = useState(0.65);
  const [llmProvider, setLlmProvider] = useState<LlmProvider>("groq");
  const [weightSchemes] = useState<WeightScheme[]>(["head_count"]);

  // ── Step 3 · Build watch (#28) ──────────────────────────────────────────
  const [build, setBuild] = useState<BuildSummary | null>(null);
  const [events, setEvents] = useState<BuildEvent[]>([]);
  const [triggering, setTriggering] = useState(false);
  const [triggerError, setTriggerError] = useState<string | null>(null);

  // ── Step 4 · Evaluate (NEW) ─────────────────────────────────────────────
  // The unpromoted pack read straight from R2 by version, for the compact
  // reading. Re-loaded whenever the build's pack_version changes.
  const [evalPack, setEvalPack] = useState<PersonaPackDetail | null>(null);
  const [evalPhase, setEvalPhase] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [evalError, setEvalError] = useState<string | null>(null);
  // The version whose pack read is currently in flight. A rerun/reconfigure
  // changes build.pack_version and supersedes any earlier read — when an older
  // request resolves we drop it rather than show build A's personas under
  // build B (the Evaluate effect only refires on evalPhase==="idle", so a late
  // A response could otherwise stick). clearBuild() nulls this to invalidate
  // any read in flight at reset time.
  const evalReqRef = useRef<string | null>(null);

  // ── Step 5 · Promote (#28) ──────────────────────────────────────────────
  const [promoting, setPromoting] = useState(false);
  const [promoted, setPromoted] = useState<PackSummary | null>(null);
  const [promoteError, setPromoteError] = useState<string | null>(null);

  // The live fingerprint of the connect form (recomputed each render).
  const fingerprint = credFingerprint(conn, sourceMode, tableFqn, sql);
  const testPassed = okFingerprint !== null && okFingerprint === fingerprint;
  // Reusing a saved/already-minted connection (#304): a `connection` exists and
  // the form hasn't diverged from the fingerprint that owns it. On this path the
  // password is intentionally blank (the server holds password_enc), so the Test
  // button must NOT require a password — Test runs against connection.id. Edit a
  // credential field and the fingerprint diverges, flipping us back to the
  // create path where a password is required again (handleTest re-mints).
  const reusingSaved = connection !== null && connFingerprint === fingerprint;

  // The source body passed to preview/build. Table → SELECT *; SQL verbatim.
  const sourceBody = (): { table_fqn?: string | null; sql?: string | null } =>
    sourceMode === "table" ? { table_fqn: tableFqn.trim() } : { sql: sql.trim() };

  // Clear the current build → returns the Build step to its config form. Used
  // by Retry (failed build), Reconfigure (change settings), and Re-run (from
  // Evaluate). Also drops any stale evaluation + promotion so the next build
  // owns its own pack. Never re-triggers on its own — Start build does that.
  const clearBuild = useCallback(() => {
    setBuild(null);
    setEvents([]);
    setTriggerError(null);
    setEvalPack(null);
    setEvalPhase("idle");
    setEvalError(null);
    // Invalidate any in-flight pack read so a late response for the cleared
    // build can't reapply itself after the reset (see loadEvaluation guard).
    evalReqRef.current = null;
    setPromoted(null);
    setPromoteError(null);
  }, []);

  // ── Step 1 · load saved connections on mount (#304) ──────────────────────
  // Fetch the customer's persisted connections once. A failed fetch must NOT
  // block the wizard — we fall back to the blank form (connsPhase "error" just
  // hides the saved-list section), so the original enter-everything path always
  // remains available.
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const rows = await listFeatureStores();
        if (cancelled) return;
        setSavedConns(rows);
        setConnsPhase("ready");
      } catch {
        if (cancelled) return;
        setConnsPhase("error"); // graceful: section hides, form stays usable
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // ── Step 1 handlers ──────────────────────────────────────────────────────
  const setConnField = (key: keyof ConnForm, value: string) => {
    setConn((prev) => ({ ...prev, [key]: value }));
    // Any credential edit invalidates a prior passing test (Continue re-gates).
    setOkFingerprint(null);
    setTestError(null);
  };

  // Reuse a saved connection (#304). The server already holds this row's
  // encrypted password, and every downstream call (test/preview/suggest/build)
  // works off connection.id — so we set `connection` to the saved row DIRECTLY,
  // skipping createFeatureStore and the password entirely.
  //
  // The fingerprint dance is the load-bearing part: handleTest mints a fresh
  // connection only when `connFingerprint !== fingerprint`. We prefill the form
  // with the row's non-secret fields (password left blank — it's never returned)
  // and set `connFingerprint` to the fingerprint of THAT password-blank form
  // (with the current source mode/table/sql). Now the live `fingerprint` matches
  // `connFingerprint`, so handleTest reuses connection.id against the stored
  // credential instead of re-minting — and the user reaches build with zero
  // password re-entry. (If they later edit a credential field the fingerprint
  // diverges and the existing mint-on-test path correctly takes back over, which
  // is when a password would be required again — matching existing behavior.)
  const handleSelectSaved = (c: ConnectionSummary) => {
    const prefilled: ConnForm = {
      name: c.name,
      account: c.account,
      user: c.user,
      password: "", // never returned by GET — stays blank; reuse needs no password
      warehouse: c.warehouse,
      role: c.role,
      database: c.database,
      schema: c.schema ?? "",
    };
    setConn(prefilled);
    setConnection(c);
    // Pin both fingerprints to the password-blank form against the current
    // source. okFingerprint isn't set here — Continue still gates on an actual
    // 204 from Test, so the user confirms the saved row connects before moving on.
    const fp = credFingerprint(prefilled, sourceMode, tableFqn, sql);
    setConnFingerprint(fp);
    setOkFingerprint(null);
    setTestError(null);
    // A different connection invalidates any prior profiled mapping (#27) — the
    // columns may differ, so force a re-profile on next Map entry (mirrors the
    // reset handleTest does after a fresh mint).
    setColumns(null);
    setSuggestion(null);
    setMapping({});
    setMapPhase("idle");
  };

  // Return to the blank-form path (#304) — "Enter a different connection". Drops
  // the selected/minted connection so the next Test mints fresh from the form.
  const handleNewConnection = () => {
    setConn(emptyConnForm());
    setConnection(null);
    setConnFingerprint(null);
    setOkFingerprint(null);
    setTestError(null);
    setColumns(null);
    setSuggestion(null);
    setMapping({});
    setMapPhase("idle");
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

  // ── Step 3 · start build (#28) ───────────────────────────────────────────
  // Assembles the BuildConfig, fires it, stores the build, and resets any prior
  // promotion — but does NOT advance: the watch renders inline on the SAME
  // step. (Old Trigger auto-advanced to Watch; here the two are one step.)
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
      // A new build supersedes any prior promotion AND any prior evaluation —
      // otherwise the stale `promoted` would disable the new Promote button
      // (while Continue stays enabled) and Promote would report the OLD pack
      // version, and the stale evalPack would show the wrong personas. Reset
      // both so this build owns its own pack. (codex P2 + #27 evaluate.)
      setEvalPack(null);
      setEvalPhase("idle");
      setEvalError(null);
      setPromoted(null);
      setPromoteError(null);
      // No setStep — the watch renders inline on this step (#28 redesign).
    } catch (e) {
      setTriggerError(apiErrorMessage(e));
    } finally {
      setTriggering(false);
    }
  };

  // ── Step 3 · watch poll (#28) ────────────────────────────────────────────
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
    void tick(); // immediate first beat so the watch isn't blank for 2.5s
    const interval = setInterval(tick, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [watchId]);

  // ── Step 4 · load the unpromoted pack for evaluation (NEW) ───────────────
  // On entry to Evaluate, read the pack straight from R2 by version. This works
  // PRE-PROMOTE — getPersonaPackDetail resolves an explicit version regardless
  // of the latest pointer — which is the whole point: read before you promote.
  const loadEvaluation = useCallback(async (version: string) => {
    evalReqRef.current = version;
    setEvalError(null);
    setEvalPhase("loading");
    try {
      const detail = await getPersonaPackDetail(version);
      if (evalReqRef.current !== version) return; // superseded — ignore
      setEvalPack(detail);
      setEvalPhase("ready");
    } catch (e) {
      if (evalReqRef.current !== version) return; // superseded — ignore
      setEvalError(apiErrorMessage(e));
      setEvalPhase("error");
    }
  }, []);

  const packVersion = build?.pack_version ?? null;
  useEffect(() => {
    if (
      step === 4 &&
      build?.status === "complete" &&
      packVersion &&
      evalPhase === "idle"
    ) {
      void loadEvaluation(packVersion);
    }
  }, [step, build?.status, packVersion, evalPhase, loadEvaluation]);

  // ── Step 5 · promote (#28) ───────────────────────────────────────────────
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
        return build?.status === "complete"; // Continue→Evaluate only when done
      case 4:
        // Evaluate gates Promote: continuing IS the accept — but only of
        // something you were actually shown. Promote stays out of reach while
        // the pack is loading, on a read error, or if the loaded pack is a
        // stale read for a superseded build (version must match the build).
        return evalPhase === "ready" && !!evalPack && evalPack.version === build?.pack_version;
      case 5:
        return false; // terminal — Promote has no Next
      default:
        return false;
    }
  };

  const goBack = () => setStep((s) => Math.max(1, s - 1));
  const goNext = () => {
    if (canContinue()) setStep((s) => Math.min(LAST_STEP, s + 1));
  };

  // The Promote step (terminal) has no Next furniture. Every other step does,
  // including Build (its Next appears once the build is complete) — Start build
  // is a primary action WITHIN the step, not the step's navigation.
  const showNext = step !== LAST_STEP;

  // Per-step Next label — the wording carries the destination (instrument
  // posture: meaning in words, not chrome).
  const nextLabel =
    step === 3 ? "Continue → Evaluate" : step === 4 ? "These look right → Promote" : "Next →";

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
          GENERATED FROM YOUR DATA — VERSIONED, EVALUATE-THEN-PROMOTE
        </span>
      </header>

      <Stepper current={step} />

      {/* Step body. Each step renders inside the form zone. */}
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
            savedConns={savedConns}
            connsPhase={connsPhase}
            selectedConnId={connection?.id ?? null}
            reusingSaved={reusingSaved}
            onSelectSaved={handleSelectSaved}
            onNewConnection={handleNewConnection}
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
          <StepBuild
            // config
            connection={connection}
            sourceMode={sourceMode}
            tableFqn={tableFqn}
            sql={sql}
            columns={columns}
            mapping={mapping}
            k={k}
            stabilityThreshold={stabilityThreshold}
            llmProvider={llmProvider}
            weightSchemes={weightSchemes}
            triggering={triggering}
            triggerError={triggerError}
            onK={setK}
            onStabilityThreshold={setStabilityThreshold}
            onLlmProvider={setLlmProvider}
            onStart={handleStartBuild}
            // watch
            build={build}
            events={events}
            onRetry={clearBuild}
            onReconfigure={clearBuild}
          />
        )}

        {step === 4 && (
          <StepEvaluate
            build={build}
            phase={evalPhase}
            error={evalError}
            pack={evalPack}
            onRerun={() => {
              // Re-run with different settings: clear the build and return to
              // Build's config form (#27 evaluate → tune → rebuild loop).
              clearBuild();
              setStep(3);
            }}
            onRetry={() => {
              // Re-attempt the R2 read (transient fetch failure) without
              // touching the build.
              setEvalPhase("idle");
            }}
          />
        )}

        {step === 5 && (
          <StepPromote
            build={build}
            promoting={promoting}
            promoted={promoted}
            promoteError={promoteError}
            onPromote={handlePromote}
          />
        )}

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
              {nextLabel}
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
  savedConns,
  connsPhase,
  selectedConnId,
  reusingSaved,
  onSelectSaved,
  onNewConnection,
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
  savedConns: ConnectionSummary[];
  connsPhase: "loading" | "ready" | "error";
  selectedConnId: string | null;
  reusingSaved: boolean;
  onSelectSaved: (c: ConnectionSummary) => void;
  onNewConnection: () => void;
  onField: (k: keyof ConnForm, v: string) => void;
  onSourceMode: (m: SourceMode) => void;
  onTableFqn: (v: string) => void;
  onSql: (v: string) => void;
  onTest: () => void;
}) {
  // Required credential fields must be filled before a test is meaningful;
  // schema is optional. This only enables the Test button — the real gate is
  // a 204 from the backend. The password is required ONLY on the create path:
  // when reusing a saved connection (#304) it's intentionally blank — Test runs
  // against the saved connection.id using the server's stored credential — so we
  // drop it from the gate in that case (else Test would be permanently disabled
  // for every reused connection).
  const credsFilled =
    conn.name.trim() &&
    conn.account.trim() &&
    conn.user.trim() &&
    (reusingSaved || conn.password) &&
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

      {/* ── 00 · Saved connections (#304) ───────────────────────────────────
          The customer's persisted feature stores. Selecting one reuses it by
          id — the server holds the encrypted password, so test/preview/build
          all run against the stored credential with NO password re-entry. The
          section only renders when there's something to offer (or while the
          first read is in flight); an empty list or a failed fetch falls
          straight through to the form below — no empty-state clutter, never a
          blocked wizard (§8.6 honest text, no spinners). */}
      {connsPhase === "loading" && (
        <div style={{ ...statusLineStyle, color: TOKENS.inkMuted, marginBottom: 4 }}>
          LOADING SAVED CONNECTIONS…
        </div>
      )}
      {connsPhase === "ready" && savedConns.length > 0 && (
        <section style={{ marginBottom: 4 }}>
          <div style={sectionLabelStyle}>Saved connections</div>
          <div style={hintStyle}>
            Reuse a connection you&apos;ve already saved — no need to re-enter its
            password. Pick one, then test and continue. Or enter a different
            connection below.
          </div>
          <div style={{ ...fieldStyle, display: "flex", flexDirection: "column", gap: 8 }}>
            {savedConns.map((c) => {
              const selected = c.id === selectedConnId;
              return (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => onSelectSaved(c)}
                  aria-pressed={selected}
                  style={{
                    textAlign: "left",
                    background: selected ? TOKENS.paperRecessed : TOKENS.paperElevated,
                    // Selection rides an ink hairline (the only emphasis) — no
                    // color state; meaning is in the wording/border (§4.3).
                    border: `${selected ? "1px" : "0.75px"} solid ${selected ? TOKENS.ink : TOKENS.rule}`,
                    borderRadius: 4,
                    padding: "10px 12px",
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    gap: 4,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
                    <span style={{ fontSize: 14, fontWeight: 600, color: TOKENS.ink }}>{c.name}</span>
                    <Chip>{c.kind.toUpperCase()}</Chip>
                    {selected && <Chip>SELECTED</Chip>}
                  </div>
                  <div style={railCaptionStyle}>
                    {c.account} · {c.warehouse} · {c.database}
                    {c.schema ? `.${c.schema}` : ""} · {c.role}
                  </div>
                </button>
              );
            })}
          </div>
          <div style={{ ...fieldStyle }}>
            <button type="button" onClick={onNewConnection} style={secondaryBtnStyle}>
              + Enter a different connection
            </button>
          </div>
        </section>
      )}

      {/* ── 01 · Snowflake credentials ──────────────────────────────────── */}
      <section style={connsPhase === "ready" && savedConns.length > 0 ? sectionStyle : undefined}>
        <div style={sectionLabelStyle}>01 · Snowflake credentials</div>
        <div style={fieldStyle}>{Field("name", "Connection name", "e.g. prod-analytics")}</div>
        <div style={{ ...fieldStyle, ...fieldRowStyle }}>
          {Field("account", "Account", "xy12345.us-east-1")}
          {Field("user", "User", "SIDIRA_READER")}
        </div>
        <div style={fieldStyle}>
          {Field(
            "password",
            "Password",
            // On reuse the saved credential lives server-side — leaving the field
            // blank is correct; type a value only to re-key/rotate the connection.
            reusingSaved ? "kept securely — leave blank to reuse" : "••••••••",
            "password",
          )}
        </div>
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
          {reusingSaved
            ? " You're reusing a saved connection, so its password stays on the server — leave the field blank and just test. Editing any field switches back to creating a new connection (password required again)."
            : ""}
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
// Step 3 · Build (#28) — config + live watch on ONE fire-and-watch step.
//
// MERGES the old Trigger + Watch. Before a build exists this is the config form
// with a prominent Start build; once a build exists the live watch renders
// inline on the SAME step (no auto-advance). Continue (→ Evaluate) is gated on
// the build reaching `complete`. The persona-target (k) lives here now — it
// moved off the old Review step.
// ════════════════════════════════════════════════════════════════════════════

// Map a build status to an honest status line (§8.6).
function buildStatusLine(b: BuildSummary): string {
  switch (b.status) {
    case "pending":
      return "PENDING · QUEUED";
    case "running":
      return "RUNNING · CLUSTERING + NAMING";
    case "complete":
      return b.pack_version ? `COMPLETE · PACK ${b.pack_version}` : "COMPLETE";
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

function StepBuild({
  connection,
  sourceMode,
  tableFqn,
  sql,
  columns,
  mapping,
  k,
  stabilityThreshold,
  llmProvider,
  weightSchemes,
  triggering,
  triggerError,
  onK,
  onStabilityThreshold,
  onLlmProvider,
  onStart,
  build,
  events,
  onRetry,
  onReconfigure,
}: {
  connection: ConnectionSummary | null;
  sourceMode: SourceMode;
  tableFqn: string;
  sql: string;
  columns: ColumnProfile[] | null;
  mapping: Record<string, Assignment | "">;
  k: BuildK;
  stabilityThreshold: number;
  llmProvider: LlmProvider;
  weightSchemes: WeightScheme[];
  triggering: boolean;
  triggerError: string | null;
  onK: (k: BuildK) => void;
  onStabilityThreshold: (v: number) => void;
  onLlmProvider: (v: LlmProvider) => void;
  onStart: () => void;
  build: BuildSummary | null;
  events: BuildEvent[];
  onRetry: () => void;
  onReconfigure: () => void;
}) {
  // Once a build exists, the watch owns this step; otherwise the config form.
  if (build) {
    return (
      <BuildWatch build={build} events={events} onRetry={onRetry} onReconfigure={onReconfigure} />
    );
  }
  return (
    <BuildConfigForm
      connection={connection}
      sourceMode={sourceMode}
      tableFqn={tableFqn}
      sql={sql}
      columns={columns}
      mapping={mapping}
      k={k}
      stabilityThreshold={stabilityThreshold}
      llmProvider={llmProvider}
      weightSchemes={weightSchemes}
      triggering={triggering}
      triggerError={triggerError}
      onK={onK}
      onStabilityThreshold={onStabilityThreshold}
      onLlmProvider={onLlmProvider}
      onStart={onStart}
    />
  );
}

// ── Build · config form (before a build exists) ────────────────────────────
function BuildConfigForm({
  connection,
  sourceMode,
  tableFqn,
  sql,
  columns,
  mapping,
  k,
  stabilityThreshold,
  llmProvider,
  weightSchemes,
  triggering,
  triggerError,
  onK,
  onStabilityThreshold,
  onLlmProvider,
  onStart,
}: {
  connection: ConnectionSummary | null;
  sourceMode: SourceMode;
  tableFqn: string;
  sql: string;
  columns: ColumnProfile[] | null;
  mapping: Record<string, Assignment | "">;
  k: BuildK;
  stabilityThreshold: number;
  llmProvider: LlmProvider;
  weightSchemes: WeightScheme[];
  triggering: boolean;
  triggerError: string | null;
  onK: (k: BuildK) => void;
  onStabilityThreshold: (v: number) => void;
  onLlmProvider: (v: LlmProvider) => void;
  onStart: () => void;
}) {
  // Per-group + ignored column lists, recapped from the resolved mapping so the
  // PM sees exactly what's going in without bouncing back to Map.
  const groupCols = (group: FeatureGroup) =>
    (columns ?? []).filter((c) => mapping[c.name] === group).map((c) => c.name);
  const ignoredCols = (columns ?? []).filter((c) => mapping[c.name] === "ignore").map((c) => c.name);

  return (
    <div style={{ maxWidth: 680 }}>
      {triggerError && (
        <div role="alert" style={errorBannerStyle}>
          {triggerError}
        </div>
      )}

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

      {/* ── Persona target (config.k) — moved here from the old Review step ── */}
      <section style={sectionStyle}>
        <div style={sectionLabelStyle}>Persona count</div>
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
            <option value="auto">AUTO · RECOMMENDED</option>
            {[6, 7, 8, 9, 10, 11, 12].map((n) => (
              <option key={n} value={n}>
                {n} PERSONAS
              </option>
            ))}
          </select>
          <div style={hintStyle}>
            Auto picks the count with the best stability for your population —
            leave it here unless you have a target segmentation in mind.
          </div>
        </div>
      </section>

      {/* ── Advanced — threshold + naming model ─────────────────────────── */}
      <section style={sectionStyle}>
        <div style={sectionLabelStyle}>Advanced</div>
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
          and jobs-to-be-done from its centroid. Weight scheme:{" "}
          {weightSchemes.map((w) => w.toUpperCase()).join(" · ")}.
        </div>
      </section>

      {/* ── Start build ─────────────────────────────────────────────────── */}
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
          The build runs server-side and the watch appears right here — closing
          the tab doesn&apos;t stop it. You&apos;ll read the result on the next
          step before deciding whether to promote it.
        </div>
      </section>
    </div>
  );
}

// ── Build · live watch (once a build exists), inline on the same step ───────
function BuildWatch({
  build,
  events,
  onRetry,
  onReconfigure,
}: {
  build: BuildSummary;
  events: BuildEvent[];
  onRetry: () => void;
  onReconfigure: () => void;
}) {
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

      {/* Failure — surface the build's error and offer Retry (→ config form). */}
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
          BUILD COMPLETE — CONTINUE TO EVALUATE THE PACK BEFORE PROMOTING.
        </div>
      )}

      {/* Reconfigure / new build — clears the build → back to the config form
          on this same step, so the PM can change settings without re-treading
          Connect/Map. Never re-triggers on its own (Back is safe). */}
      {!failed && (
        <div style={{ marginTop: 14 }}>
          <button type="button" onClick={onReconfigure} style={secondaryBtnStyle}>
            Reconfigure / new build
          </button>
        </div>
      )}
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Step 4 · Evaluate (NEW) — read before you promote (#27/#28).
//
// On entry, when the build is complete, the wizard loads the UNPROMOTED pack
// from R2 by version (getPersonaPackDetail works pre-promote). This renders a
// COMPACT evaluation — not the full record sheets of /personas/[id] — so the PM
// can judge whether the personas look right. Continuing IS the accept.
// ════════════════════════════════════════════════════════════════════════════

// Build a distinctiveness one-liner from a persona's `distinctive` block. The
// honest fallback when the renderer found nothing salient (block is null) is
// the whole reason we read this here: an undistinctive persona should SAY so,
// not be dressed up (§2 no-silent-degradation).
function distinctivenessLine(block: ProfileBlockView | null | undefined): string {
  if (!block || block.deltas.length === 0) {
    return "Sits within the typical range on measured traits — not strongly distinctive.";
  }
  const top = block.deltas.slice(0, 2).map((d) => `${d.magnitude} ${d.direction} ${d.label}`);
  return `${block.heading}: ${top.join(", ")}.`;
}

function StepEvaluate({
  build,
  phase,
  error,
  pack,
  onRerun,
  onRetry,
}: {
  build: BuildSummary | null;
  phase: "idle" | "loading" | "ready" | "error";
  error: string | null;
  pack: PersonaPackDetail | null;
  onRerun: () => void;
  onRetry: () => void;
}) {
  // No complete build to read — shouldn't be reachable (Continue gates on
  // complete) but stay honest if a Back/forward dance lands here.
  if (!build || build.status !== "complete" || !build.pack_version) {
    return (
      <div style={{ ...statusLineStyle, color: TOKENS.inkMuted }}>
        NO COMPLETE BUILD TO EVALUATE — GO BACK TO BUILD.
      </div>
    );
  }

  if (phase === "loading" || phase === "idle") {
    return (
      <div style={{ ...statusLineStyle, color: TOKENS.inkMuted, marginTop: 8 }}>
        READING THE PACK…
      </div>
    );
  }

  if (phase === "error" || !pack) {
    return (
      <div style={{ maxWidth: 620 }}>
        <div role="alert" style={errorBannerStyle}>
          {error ?? "The pack could not be read for evaluation."}
        </div>
        <button type="button" onClick={onRetry} style={secondaryBtnStyle}>
          Retry reading
        </button>
      </div>
    );
  }

  // Available weight schemes only — share chips render per available scheme,
  // single-sourced from the pack's scheme labels (mirrors the detail page).
  const availableSchemes = pack.weight_schemes.filter((s) => s.available);

  return (
    <div style={{ maxWidth: 720 }}>
      {/* Pack header line — the available quality signal at a glance. */}
      <div style={{ ...railCaptionStyle, color: TOKENS.ink }}>
        STABILITY {pack.stability_score.toFixed(2)} · {pack.persona_count} PERSONA
        {pack.persona_count === 1 ? "" : "S"} · SCHEMA {pack.schema_version} ·{" "}
        {pack.version.toUpperCase()}
      </div>
      <div style={hintStyle}>
        This pack is built but <strong>not yet promoted</strong> — read it here
        before you commit. Each persona shows its share, a one-line summary, and
        how distinctive it is from the population.
      </div>

      {/* Per-persona compact reading. */}
      <div style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 18 }}>
        {pack.personas.map((persona) => (
          <EvaluatePersona key={persona.id} persona={persona} schemes={availableSchemes} />
        ))}
      </div>

      {/* Honesty note — stability is the signal we have; calibration/holdout
          (Jaccard) is tracked separately under #7 and is NOT yet shown. Do not
          fabricate a holdout number (§2 no-silent-degradation). */}
      <div style={{ ...okBannerStyle, marginTop: 22, borderColor: TOKENS.rule }}>
        Stability ({pack.stability_score.toFixed(2)}) is the quality signal
        available today — how reproducible the clustering is. Calibration against
        a holdout (Jaccard overlap) is tracked separately and is not shown here
        yet, so it isn&apos;t reported as a number you don&apos;t have.
      </div>

      {/* Actions — deep dive, re-run, and (via Next) accept-then-promote. */}
      <section style={sectionStyle}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <a
            href={`/personas/${encodeURIComponent(build.pack_version)}`}
            target="_blank"
            rel="noopener noreferrer"
            style={{ ...secondaryBtnStyle, textDecoration: "none", display: "inline-block" }}
          >
            View full pack ↗
          </a>
          <button type="button" onClick={onRerun} style={secondaryBtnStyle}>
            Re-run with different settings
          </button>
        </div>
        <div style={hintStyle}>
          The full pack opens in a new tab — every persona&apos;s jobs-to-be-done,
          behavioral snapshot, and complete comparison blocks. If these don&apos;t
          look right, re-run with a different persona count or threshold rather
          than promoting. Otherwise continue to promote this pack.
        </div>
      </section>
    </div>
  );
}

// One persona, compact: name + id designator + share chip(s), description, and
// a distinctiveness one-liner. Bordered-mono Chip / Designator vocabulary, no
// color state (matches the detail page's record voice, condensed).
function EvaluatePersona({
  persona,
  schemes,
}: {
  persona: PersonaProfileView;
  schemes: PersonaPackDetail["weight_schemes"];
}) {
  const shareChips = schemes
    .filter((s) => typeof persona.shares[s.key] === "number")
    .map((s) => ({ key: s.key, label: s.label, pct: persona.shares[s.key] }));

  return (
    <div
      style={{
        background: TOKENS.paperElevated,
        border: `0.75px solid ${TOKENS.rule}`,
        borderRadius: 4,
        padding: "14px 18px 16px",
      }}
    >
      {/* Designator header — the one place mono appears (§7.6, condensed). */}
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
        <span style={{ fontSize: 15, fontWeight: 600, letterSpacing: "-0.01em" }}>
          {persona.name}
        </span>
        <Designator>{persona.id}</Designator>
        {shareChips.map((c) => (
          <Designator key={c.key}>
            {(c.pct * 100).toFixed(0)}% {c.label.toUpperCase()}
          </Designator>
        ))}
      </div>

      {/* Description — 1–2 lines, sans prose. */}
      <p style={{ margin: "10px 0 0", fontSize: 14, lineHeight: 1.5, color: TOKENS.ink }}>
        {persona.description}
      </p>

      {/* Distinctiveness one-liner — honest when there's nothing salient. */}
      <p style={{ margin: "8px 0 0", fontSize: 13, lineHeight: 1.5, color: TOKENS.inkMuted }}>
        {distinctivenessLine(persona.distinctive)}
      </p>
    </div>
  );
}

// Local designator chip — mirrors the detail page's Designator at the wizard's
// hairline weight (0.75px) so the Evaluate reading stays in lockstep with both
// the wizard vocabulary and /personas/[id].
function Designator({ children }: { children: React.ReactNode }) {
  return (
    <span
      style={{
        fontFamily: FONT_MONO,
        fontSize: 10.5,
        letterSpacing: "0.04em",
        border: `0.75px solid ${TOKENS.rule}`,
        color: TOKENS.inkMuted,
        borderRadius: 2,
        padding: "2px 7px",
        whiteSpace: "nowrap",
        ...TNUM,
      }}
    >
      {children}
    </span>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Step 5 · Promote (#28) — terminal. Folds in the old Done content.
//
// Before promoting: the promote button + a recap. After promoting: the
// confirmation and the View-the-pack / Run-a-simulation CTAs (the old Done
// page). A new build supersedes any prior promotion (the safety reset lives in
// handleStartBuild).
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
        NO COMPLETE BUILD TO PROMOTE — GO BACK TO BUILD.
      </div>
    );
  }

  // ── After promotion: the folded-in Done content ──────────────────────────
  if (promoted) {
    return (
      <div style={{ maxWidth: 620 }}>
        <section>
          <div style={sectionLabelStyle}>Pack promoted</div>
          <div style={{ ...okBannerStyle, marginTop: 12 }}>
            {promoted.version} is now the latest persona pack
            {promoted.promoted_at ? ` (promoted ${utcStamp(promoted.promoted_at)})` : ""}. Point a
            simulation at it to put it to work — existing simulations keep their frozen pack.
          </div>
          <dl style={{ margin: 0, marginTop: 14, display: "grid", gridTemplateColumns: "auto 1fr", gap: "4px 16px" }}>
            {[
              ["Pack version", promoted.version],
              ["Stability", String(promoted.stability_score)],
              ["Personas", String(promoted.persona_count)],
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
            <a
              href={`/personas/${encodeURIComponent(promoted.version)}`}
              style={{ ...secondaryBtnStyle, textDecoration: "none", display: "inline-block" }}
            >
              View the pack →
            </a>
            <a href="/simulations/new" style={{ ...primaryBtnStyle, textDecoration: "none", display: "inline-block" }}>
              Run a simulation →
            </a>
          </div>
        </section>
      </div>
    );
  }

  // ── Before promotion: the promote action ─────────────────────────────────
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
          You evaluated this pack on the previous step. Promoting flips it to the
          latest pointer — new simulations pick it up. Existing simulations keep
          their frozen pack either way.
        </div>
        <div style={{ ...fieldStyle, display: "flex", alignItems: "center", gap: 12 }}>
          <button
            type="button"
            onClick={onPromote}
            disabled={promoting}
            style={{
              ...primaryBtnStyle,
              opacity: promoting ? 0.5 : 1,
              cursor: promoting ? "not-allowed" : "pointer",
            }}
          >
            {promoting ? "Promoting…" : "Promote to latest"}
          </button>
        </div>
      </section>
    </div>
  );
}
