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

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  createFeatureStore,
  createPersonaBuild,
  deleteFeatureStore,
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

// The CREDENTIAL fingerprint — connection fields ONLY (no source). If this
// changes, the stored connection id is stale and a fresh createFeatureStore is
// owed before testing again (or, for #304 reuse, the form has diverged from the
// saved row). Deliberately excludes mode/table/sql: the source query feeds
// preview/build, not which connection to test — conflating them was the bug
// that broke saved-connection reuse when the user typed the source after
// picking a connection (the password gate snapped back on).
const credFingerprint = (f: ConnForm) =>
  JSON.stringify([f.name, f.account, f.user, f.password, f.warehouse, f.role, f.database, f.schema]);

// The TEST fingerprint — credentials + source. Continue (Step 1) gates on a
// test having passed for these EXACT values including the source, so editing
// the table/SQL re-gates Continue (a profiled source must match what was
// tested). This is the existing okFingerprint behavior, kept intact.
const testFingerprint = (f: ConnForm, mode: SourceMode, table: string, sql: string) =>
  JSON.stringify([credFingerprint(f), mode, table, sql]);

// ── saved-connection identity (#327) ───────────────────────────────────────
// The live picker showed several cards all titled `prod-analytics`, tellable
// apart only by a casing wobble in one mono subline — and there was no way to
// delete a dead/duplicate row. The fix is to render a CANONICAL identity, not
// just the name, so near-identical rows are legible at a glance.

// The primary identity line: `name · DATABASE.SCHEMA · WAREHOUSE · ROLE`. The
// schema clause is dropped when empty. This is what the eye reads first — the
// connection's actual target, not just its label.
const connectionIdentity = (c: ConnectionSummary): string => {
  const db = c.schema ? `${c.database}.${c.schema}` : c.database;
  return `${c.name} · ${db} · ${c.warehouse} · ${c.role}`;
};

// The secondary mono line: `account · user · <id-8hex>`. The 8-hex id tail is
// the last-resort tiebreaker (4-hex collides on a page — DESIGN.md §8.8); we
// take the first 8 chars AFTER the `fs-` prefix so two rows minted seconds
// apart still differ here.
const connectionSubline = (c: ConnectionSummary): string => {
  const idTail = c.id.replace(/^fs-/, "").slice(0, 8);
  return `${c.account} · ${c.user} · ${idTail}`;
};

// ── per-connection health, in words (#328) ──────────────────────────────────
// Users reported "some connections don't work" with nothing signalling WHICH
// until the Test step. The register now carries the last-known state of each
// row as TEXT (DESIGN.md §4.3/§10: no green/red dots, no color-coded fill — the
// words carry the meaning). Derived purely from the persisted health fields.

const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

// Terse absolute date — `JUN 15` (today/yesterday spelled out when close, since
// "TESTED TODAY" reads faster than a date for the common just-tested case). No
// time-of-day: the register is scanned, not audited to the minute. There's no
// shared date helper in the codebase, so this is the minimal local one.
const terseTestedDate = (iso: string): string => {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const now = new Date();
  const startOf = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const dayDiff = Math.round((startOf(now) - startOf(d)) / 86_400_000);
  if (dayDiff === 0) return "TODAY";
  if (dayDiff === 1) return "YESTERDAY";
  return `${MONTHS[d.getMonth()]} ${d.getDate()}`;
};

// The honest-text status line for one row. UNTESTED when never tested;
// `OK · TESTED JUN 15` on a pass; `FAILED · AUTH` (or the raw kind) on a fail.
// Returned uppercase to sit in the mono caption rail.
const connectionHealthLine = (c: ConnectionSummary): string => {
  if (c.last_test_status === "ok") {
    const when = c.last_tested_at ? terseTestedDate(c.last_tested_at) : "";
    return when ? `OK · TESTED ${when}` : "OK";
  }
  if (c.last_test_status === "failed") {
    const kind = (c.last_error_kind ?? "").trim().toUpperCase();
    return kind ? `FAILED · ${kind}` : "FAILED";
  }
  return "UNTESTED";
};

// When two saved rows share the same `name` (case-insensitively, trimmed —
// DISPLAY normalization only; the stored values are never touched), append a
// stable duplicate designator (`01`, `02`, …) so the eye stops decoding casing.
// Order is the list's own stable order (server returns newest-first), so the
// designators don't reshuffle between renders. Returns a map id → " NN" suffix
// (empty string when the name is unique in the list).
const duplicateDesignators = (conns: ConnectionSummary[]): Record<string, string> => {
  const byName = new Map<string, ConnectionSummary[]>();
  for (const c of conns) {
    const key = c.name.trim().toLowerCase();
    const bucket = byName.get(key);
    if (bucket) bucket.push(c);
    else byName.set(key, [c]);
  }
  const out: Record<string, string> = {};
  for (const bucket of byName.values()) {
    if (bucket.length < 2) {
      out[bucket[0].id] = "";
      continue;
    }
    bucket.forEach((c, i) => {
      out[c.id] = ` ${String(i + 1).padStart(2, "0")}`;
    });
  }
  return out;
};

// ── picker order + filter (#332) ────────────────────────────────────────────
// At rest the step shows ONE control (a trigger), not the whole register — see
// ConnectionPicker. Inside the open popover the rows need a sensible default
// order and a substring filter, since the list can run to 20+ connections.

// Most-recently-tested first (last_tested_at desc, NULLs last), stable fallback
// by name then id so the order is deterministic across renders. This puts the
// connection the user most likely wants (the one they just tested / used) at the
// top of the popover. Returns a NEW array — never mutates the source list, whose
// own newest-first order still feeds duplicateDesignators (so designators stay
// stable regardless of how the picker sorts for display). DISPLAY order only.
const sortConnsForPicker = (conns: ConnectionSummary[]): ConnectionSummary[] =>
  [...conns].sort((a, b) => {
    const ta = a.last_tested_at ? Date.parse(a.last_tested_at) : NaN;
    const tb = b.last_tested_at ? Date.parse(b.last_tested_at) : NaN;
    const aHas = !Number.isNaN(ta);
    const bHas = !Number.isNaN(tb);
    if (aHas && bHas && ta !== tb) return tb - ta; // newer test first
    if (aHas !== bHas) return aHas ? -1 : 1; // tested rows ahead of never-tested
    const byName = a.name.trim().toLowerCase().localeCompare(b.name.trim().toLowerCase());
    if (byName !== 0) return byName;
    return a.id.localeCompare(b.id); // last-resort total order
  });

// Case-insensitive substring match across the fields the eye scans — name,
// account, user, database, schema, warehouse, role. The 20-connection case is
// the whole reason the filter exists; it narrows on whatever the user remembers.
const connMatchesFilter = (c: ConnectionSummary, q: string): boolean => {
  const needle = q.trim().toLowerCase();
  if (!needle) return true;
  const hay = [c.name, c.account, c.user, c.database, c.schema ?? "", c.warehouse, c.role]
    .join(" ")
    .toLowerCase();
  return hay.includes(needle);
};

const POLL_MS = 2500; // #28 watch cadence while pending/running.

export default function NewPersonaPackPage() {
  const [step, setStep] = useState(1);

  // ── Step 1 · Connect (#26) ──────────────────────────────────────────────
  const [conn, setConn] = useState<ConnForm>(emptyConnForm());
  const [sourceMode, setSourceMode] = useState<SourceMode>("table");
  const [tableFqn, setTableFqn] = useState("");
  const [sql, setSql] = useState("");
  const [connection, setConnection] = useState<ConnectionSummary | null>(null);
  // Test lifecycle. `okFingerprint` records the TEST fingerprint (creds + source)
  // that PASSED a test — Continue is enabled only while the current one matches.
  const [testing, setTesting] = useState(false);
  const [testError, setTestError] = useState<{ kind: string | null; message: string } | null>(null);
  const [okFingerprint, setOkFingerprint] = useState<string | null>(null);
  // The CREDENTIAL fingerprint that minted (or selected, #304) `connection` —
  // reused on the next test if the user hasn't touched any credential field
  // since. Source edits do NOT invalidate it (the connection is the same).
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
  // Delete a saved connection (#327). `confirmDeleteId` is the row whose inline
  // honest-text confirm is open (only one at a time; null when none). `deleting`
  // is the id currently being deleted (disables that row's action). `deleteError`
  // is a per-row failure message keyed by id — surfaced inline, never a banner.
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<{ id: string; message: string } | null>(null);
  // Per-row connectivity test (#328). `testingRowId` is the row whose in-place
  // TEST is in flight (disables just that affordance; null when none). The
  // server persists the outcome and GET returns it, so a successful test re-
  // fetches the list and the row's status line updates without leaving the
  // picker or selecting the connection.
  const [testingRowId, setTestingRowId] = useState<string | null>(null);
  // Per-row test failure surfaced ONLY as a fallback (#328): normally a failed
  // row-test is shown by the refreshed status line (FAILED · KIND), since the
  // server persists the outcome. But that persistence is best-effort and the
  // refresh can fail — if the refreshed row doesn't reflect the failure, we keep
  // the caught error here so the verdict is never silently swallowed. Keyed by id.
  const [rowTestError, setRowTestError] = useState<{ id: string; message: string } | null>(null);

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

  // The live fingerprints of the connect form (recomputed each render). The
  // credential fingerprint drives the mint/reuse decision; the test fingerprint
  // (creds + source) drives Continue gating.
  const credFp = credFingerprint(conn);
  const testFp = testFingerprint(conn, sourceMode, tableFqn, sql);
  const testPassed = okFingerprint !== null && okFingerprint === testFp;
  // Reusing a saved/already-minted connection (#304): a `connection` exists and
  // the CREDENTIAL fields haven't diverged from the fingerprint that owns it. On
  // this path the password is intentionally blank (the server holds
  // password_enc), so the Test button must NOT require a password — Test runs
  // against connection.id. Crucially this ignores the source, so typing the
  // table/SQL after picking a saved connection does NOT snap the password gate
  // back on. Edit a CREDENTIAL field and it diverges, flipping us back to the
  // create path where a password is required again (handleTest re-mints).
  const reusingSaved = connection !== null && connFingerprint === credFp;

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

  // A source (table/SQL/mode) edit invalidates a prior passing test (Continue
  // re-gates) AND any profiled mapping — the columns are sourced from the OLD
  // query, so Step 2 must re-profile and Step 3 must not build the new source
  // with the old column mapping. Before the #304 credential/source fingerprint
  // split, a source change re-minted the connection in handleTest, which cleared
  // this state as a side effect; now that source-only edits keep the same
  // connection, the reset has to happen explicitly here (codex P1).
  // Drop the profiled mapping (columns/suggestion/mapping/phase) so Step 2
  // re-profiles, AND any completed build/evaluation/promotion (clearBuild) so a
  // finished build can't survive a changed input — otherwise Step 3 keeps
  // rendering the old BuildWatch and Promote could ship a pack built from the
  // previous source/connection (codex P1). Shared by the source- and
  // connection-invalidation paths.
  const invalidateMappingAndBuild = () => {
    setColumns(null);
    setSuggestion(null);
    setMapping({});
    setMapPhase("idle");
    clearBuild();
  };

  // A source (table/SQL/mode) edit invalidates a prior passing test (Continue
  // re-gates) plus the mapping and build (the columns came from the old query).
  const invalidateSource = () => {
    setOkFingerprint(null);
    invalidateMappingAndBuild();
  };

  // A connection change (select saved / new / fresh mint) likewise invalidates
  // the mapping + build — the columns may differ on a different connection.
  const invalidateConnection = () => {
    invalidateMappingAndBuild();
  };

  // Reuse a saved connection (#304). The server already holds this row's
  // encrypted password, and every downstream call (test/preview/suggest/build)
  // works off connection.id — so we set `connection` to the saved row DIRECTLY,
  // skipping createFeatureStore and the password entirely.
  //
  // The fingerprint dance is the load-bearing part: handleTest mints a fresh
  // connection only when `connFingerprint !== credFp`. We prefill the form with
  // the row's non-secret fields (password left blank — it's never returned) and
  // set `connFingerprint` to the CREDENTIAL fingerprint of THAT password-blank
  // form. Now the live `credFp` matches `connFingerprint`, so handleTest reuses
  // connection.id against the stored credential instead of re-minting — and the
  // user reaches build with zero password re-entry. Because the fingerprint is
  // credential-only, typing the source (table/SQL) afterward does NOT break the
  // reuse. (Edit a credential field and it diverges, so the existing
  // mint-on-test path correctly takes back over — a password is required again,
  // matching existing behavior.)
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
    // Pin connFingerprint to the password-blank form's CREDENTIAL fingerprint.
    // okFingerprint isn't set here — Continue still gates on an actual 204 from
    // Test, so the user confirms the saved row connects before moving on.
    setConnFingerprint(credFingerprint(prefilled));
    setOkFingerprint(null);
    setTestError(null);
    // A different connection invalidates any prior profiled mapping AND any
    // completed build (#27/#304) — the columns may differ.
    invalidateConnection();
  };

  // Return to the blank-form path (#304) — "Enter a different connection". Drops
  // the selected/minted connection so the next Test mints fresh from the form.
  const handleNewConnection = () => {
    setConn(emptyConnForm());
    setConnection(null);
    setConnFingerprint(null);
    setOkFingerprint(null);
    setTestError(null);
    invalidateConnection();
  };

  // "Edit as new" (#327): open the full credential form PREFILLED from a saved
  // connection's non-secret fields, but as a NEW connection mint — drop the
  // selected `connection`/`connFingerprint` so the next Test creates a fresh row
  // (a new password + a unique name are required; the name uniqueness guard will
  // reject a verbatim re-save, which is exactly the point — edit it). The
  // password stays blank (it's never returned). This is distinct from
  // handleNewConnection, which clears the form to blank.
  const handleEditAsNew = (c: ConnectionSummary) => {
    setConn({
      name: c.name,
      account: c.account,
      user: c.user,
      password: "",
      warehouse: c.warehouse,
      role: c.role,
      database: c.database,
      schema: c.schema ?? "",
    });
    setConnection(null);
    setConnFingerprint(null);
    setOkFingerprint(null);
    setTestError(null);
    invalidateConnection();
  };

  // Delete a saved connection (#327). Customer-scoped server-side (404 if it
  // isn't ours). On success we drop the row from the list, AND — if it was the
  // SELECTED connection — clear the selection back to the blank form so the
  // wizard can't carry a credential that no longer exists into Map/Build. The
  // inline confirm is the only gate; no browser confirm(), no modal (§10).
  const handleDeleteConnection = async (id: string) => {
    setDeleteError(null);
    setDeletingId(id);
    try {
      await deleteFeatureStore(id);
      setSavedConns((prev) => prev.filter((c) => c.id !== id));
      setConfirmDeleteId(null);
      // If the deleted row was the active connection, reset the form — its
      // credential is gone, so any in-progress Test/Map/Build is stale.
      if (connection?.id === id) handleNewConnection();
    } catch (e) {
      setDeleteError({ id, message: apiErrorMessage(e) });
    } finally {
      setDeletingId(null);
    }
  };

  // Test a saved connection IN PLACE from its register row (#328). This does NOT
  // select the row or leave the picker — it just re-runs the connectivity test
  // (testFeatureStore is a no-body POST against the stored credential) and lets
  // the server persist the outcome. We then re-fetch the list so the row's
  // status line reflects the new state (OK · TESTED … or FAILED · KIND). The
  // route returns the same 204/structured-error contract whether or not the
  // test passes; either way the persisted health changed, so we refresh
  // regardless. A failed test surfaces only through the refreshed row's
  // FAILED · … line — no banner, since this is one row in a register, not the
  // wizard's own 03 · Test step (which keeps its existing testError banner).
  const handleTestRow = async (id: string) => {
    setTestingRowId(id);
    setRowTestError(null);
    // Capture the connectivity verdict locally so it's never lost: normally the
    // refreshed status line carries it, but if persistence/refresh fails we fall
    // back to surfacing this error inline (the row must never silently swallow a
    // failed test — the prior masking gap).
    let caught: string | null = null;
    // Remember this row's last_tested_at BEFORE the test so we can tell whether
    // the refresh actually captured THIS run. A row already FAILED from an
    // earlier test would otherwise mask a fresh, unpersisted failure (codex P2).
    const priorTestedAt = savedConns.find((r) => r.id === id)?.last_tested_at ?? null;
    try {
      await testFeatureStore(id); // 204 on success, throws on failure
    } catch (e) {
      caught = apiErrorMessage(e);
    }
    let refreshed: ConnectionSummary[] | null = null;
    try {
      refreshed = await listFeatureStores();
      setSavedConns(refreshed);
    } catch {
      // A failed refresh leaves the prior status line in place — the wizard is
      // never blocked by it (mirrors the mount-load graceful fallback).
    }
    // Surface the inline fallback ONLY when the test failed and the refreshed
    // row does NOT reflect THIS run as failed. "This run" means the row is
    // FAILED *and* its last_tested_at advanced past the pre-test value — so a
    // stale prior FAILED from an earlier test (with an unpersisted new failure)
    // still surfaces the fresh verdict. On the clean path the status line shows
    // it and we stay quiet.
    if (caught) {
      const fresh = refreshed?.find((r) => r.id === id);
      const capturedThisRun =
        fresh?.last_test_status === "failed" &&
        fresh.last_tested_at != null &&
        fresh.last_tested_at !== priorTestedAt;
      if (!capturedThisRun) {
        setRowTestError({ id, message: caught });
      }
    }
    setTestingRowId(null);
  };

  const handleTest = async () => {
    setTestError(null);
    setTesting(true);
    // The id actually tested (set once `active` is resolved/minted below) — the
    // finally uses it to refresh that row's health (#328), since the `connection`
    // state captured in this closure is stale after a fresh mint.
    let testedId: string | null = null;
    try {
      // Reuse the stored id if no CREDENTIAL changed since the last create /
      // saved-connection select; otherwise mint a fresh connection (#26). A
      // changed credential MUST NOT test the old id. Source-only edits keep the
      // same connection, so they don't force a re-mint here.
      let active = connection;
      if (!active || connFingerprint !== credFp) {
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
        setConnFingerprint(credFp);
        // Register the freshly-minted row in the saved list immediately (#327
        // codex P1). The row is PERSISTED the moment createFeatureStore returns,
        // even if the connectivity test that follows fails — and the unique-name
        // guard means re-creating it under the same name would 409. So if it
        // doesn't already appear (it won't, on a fresh mint), surface it now: the
        // register lists it, "Use different connection" returns to that list, and
        // the row's Delete affordance is the in-UI escape from a bad password —
        // no page reload, no trapped name. (Newest-first, mirroring the server.)
        setSavedConns((prev) =>
          prev.some((c) => c.id === active!.id) ? prev : [active!, ...prev],
        );
        // A fresh connection invalidates a previously-profiled mapping AND any
        // completed build (#27/#304): the columns may differ, so force a
        // re-profile on next Map entry and drop any stale build.
        invalidateConnection();
      }
      testedId = active.id;
      await testFeatureStore(active.id); // 204 on success, throws on failure
      // Continue gates on the full test fingerprint (creds + source), so a later
      // source edit re-gates Continue (existing behavior).
      setOkFingerprint(testFp);
    } catch (e) {
      setTestError(apiErrorParts(e));
      setOkFingerprint(null);
    } finally {
      setTesting(false);
      // The server persisted this test's outcome (#328) whether it passed or
      // failed. Refresh the saved list so the register row / collapsed summary
      // for the active connection shows its new health state (OK · TESTED … or
      // FAILED · KIND) instead of a stale UNTESTED — otherwise the wizard's own
      // 03 · Test path would leave the picker behind it out of date. We also
      // re-point `connection` at the refreshed row so the collapsed summary's
      // health chip updates in place. Best-effort: a failed refresh leaves the
      // prior state and never blocks the wizard (mirrors the mount-load
      // fallback). `testedId` is the id actually tested (incl. a fresh mint),
      // so the refresh is correct even when `connection` (closure) was stale.
      // Only re-point `connection` when it still refers to the tested row — a
      // mid-flight switch must not be clobbered.
      if (testedId) {
        const refreshId = testedId;
        void (async () => {
          try {
            const rows = await listFeatureStores();
            setSavedConns(rows);
            const fresh = rows.find((r) => r.id === refreshId);
            if (fresh) setConnection((prev) => (prev?.id === refreshId ? fresh : prev));
          } catch {
            // leave prior state; never block
          }
        })();
      }
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
            selectedConn={connection}
            reusingSaved={reusingSaved}
            confirmDeleteId={confirmDeleteId}
            deletingId={deletingId}
            deleteError={deleteError}
            testingRowId={testingRowId}
            rowTestError={rowTestError}
            onTestRow={handleTestRow}
            onSelectSaved={handleSelectSaved}
            onNewConnection={handleNewConnection}
            onRequestDelete={(id) => {
              setDeleteError(null);
              setConfirmDeleteId(id);
            }}
            onCancelDelete={() => {
              setConfirmDeleteId(null);
              setDeleteError(null);
            }}
            onConfirmDelete={handleDeleteConnection}
            onEditAsNew={() => {
              if (connection) handleEditAsNew(connection);
            }}
            onField={setConnField}
            onSourceMode={(m) => {
              setSourceMode(m);
              invalidateSource();
            }}
            onTableFqn={(v) => {
              setTableFqn(v);
              invalidateSource();
            }}
            onSql={(v) => {
              setSql(v);
              invalidateSource();
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
  selectedConn,
  reusingSaved,
  confirmDeleteId,
  deletingId,
  deleteError,
  testingRowId,
  rowTestError,
  onTestRow,
  onSelectSaved,
  onNewConnection,
  onRequestDelete,
  onCancelDelete,
  onConfirmDelete,
  onEditAsNew,
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
  selectedConn: ConnectionSummary | null;
  reusingSaved: boolean;
  confirmDeleteId: string | null;
  deletingId: string | null;
  deleteError: { id: string; message: string } | null;
  testingRowId: string | null;
  rowTestError: { id: string; message: string } | null;
  onTestRow: (id: string) => void;
  onSelectSaved: (c: ConnectionSummary) => void;
  onNewConnection: () => void;
  onRequestDelete: (id: string) => void;
  onCancelDelete: () => void;
  onConfirmDelete: (id: string) => void;
  onEditAsNew: () => void;
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

  // Stable per-name duplicate designators for the register (#327) — only the
  // saved list feeds this, computed once per render.
  const dupDesignators = duplicateDesignators(savedConns);

  // Collapse-on-select (#327): when a SAVED connection is selected and the
  // credentials still match it (reusingSaved), we don't render the prefilled
  // credential form — that's what made the picker read like a gallery of
  // near-identical forms. Instead we show a compact "Using saved connection"
  // summary record. The full form returns only via "Use different connection"
  // (a fresh blank mint) or "Edit as new" (form prefilled as a NEW connection).
  // We need `selectedConn` (the ConnectionSummary) to render the summary, so the
  // collapse also requires the selected id to be a row we hold in the saved list
  // — a connection that isn't listed (it should always be, post-mint) keeps the
  // editable form so the user is never stuck behind a summary for a row they
  // can't see or delete (#327 codex P1).
  const collapsed =
    reusingSaved && selectedConn !== null && savedConns.some((c) => c.id === selectedConn.id);

  // Explicit "the user just selected from the picker" signal (#332/codex P2). The
  // picker's selected row unmounts before the collapsed summary mounts, so the
  // summary can't reliably infer the path from document.activeElement (it's
  // already <body> on the keyboard path). This ref carries the intent across that
  // unmount/mount so the summary focuses its heading ONLY when collapse follows a
  // real selection — never on a cold page load with a pre-selected connection.
  const justPickedRef = useRef(false);

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

      {/* ── 00 · Saved connections — a register, not a gallery (#304/#327) ───
          The customer's persisted feature stores. Selecting one reuses it by
          id — the server holds the encrypted password, so test/preview/build
          all run against the stored credential with NO password re-entry.

          #327 redesign: this reads like a register you scan (dense paper rows,
          0.75px hairline rules, mono metadata, radius ≤4, a single ink-hairline
          selected state), and each row carries a canonical IDENTITY line
          (name · DB.SCHEMA · WAREHOUSE · ROLE) plus a mono subline
          (account · user · id-8hex) so near-identical rows are tellable apart.
          Duplicate names get a stable `NN` designator. Each row also carries a
          quiet delete affordance (an ink-hairline text button — no red fill, no
          trash icon, no emoji — §10) gated behind an inline honest-text confirm.

          The section only renders when there's something to offer (or while the
          first read is in flight); an empty list or a failed fetch falls
          straight through to the form below — no empty-state clutter, never a
          blocked wizard (§8.6 honest text, no spinners). When a saved row is
          SELECTED, the picker hides and a compact summary takes over (collapse-
          on-select) — see below. */}
      {connsPhase === "loading" && (
        <div style={{ ...statusLineStyle, color: TOKENS.inkMuted, marginBottom: 4 }}>
          LOADING SAVED CONNECTIONS…
        </div>
      )}

      {/* Collapse-on-select: a compact "Using saved connection" record instead
          of the full prefilled form. Keeps the wizard from showing a credential
          form under a selected row (which is what made the picker unreadable). */}
      {collapsed && selectedConn && (
        <SavedConnectionSummary
          conn={selectedConn}
          designator={dupDesignators[selectedConn.id] ?? ""}
          // Focus the summary heading on mount ONLY when this collapse followed a
          // picker selection (consume the one-shot ref so a later re-render or a
          // cold load never re-grabs focus).
          focusOnMount={justPickedRef.current}
          onFocusConsumed={() => {
            justPickedRef.current = false;
          }}
          onUseDifferent={onNewConnection}
          onEditAsNew={onEditAsNew}
        />
      )}

      {/* The picker — shown only when NOT collapsed (i.e. while creating or
          editing a connection). A selected row collapses into the summary above
          instead of living here.

          #332: at REST this renders ONE control — a `Choose a saved connection
          (N) ▾` trigger — NOT the whole register. With 6, 20, or 40 saved rows
          the inline ledger dominated the Connect step; a connection picker is
          management surface, not the step's primary content. The register rows
          (canonical identity · health line · per-row TEST · DELETE) all still
          exist — they move INTO a custom popover the trigger opens, capped to a
          few rows with internal scroll, sorted most-recently-tested-first, and
          fronted by a substring filter. Selecting a row collapses to the #327
          summary exactly as before. We use a CUSTOM combobox, not a native
          <select>, because a native option can carry none of that — no two-line
          identity, no status line, no per-row Test/Delete, no on-brand paper
          styling (§10 also bans the native-select chrome here). */}
      {!collapsed && connsPhase === "ready" && savedConns.length > 0 && (
        <ConnectionPicker
          conns={savedConns}
          dupDesignators={dupDesignators}
          selectedConnId={selectedConnId}
          confirmDeleteId={confirmDeleteId}
          deletingId={deletingId}
          deleteError={deleteError}
          testingRowId={testingRowId}
          rowTestError={rowTestError}
          onSelectSaved={(c) => {
            // Mark that the next collapse came from a picker selection, so the
            // summary rescues keyboard focus (codex P2). Consumed in the summary.
            justPickedRef.current = true;
            onSelectSaved(c);
          }}
          onTestRow={onTestRow}
          onRequestDelete={onRequestDelete}
          onCancelDelete={onCancelDelete}
          onConfirmDelete={onConfirmDelete}
          onNewConnection={onNewConnection}
        />
      )}

      {/* ── 01 · Snowflake credentials ──────────────────────────────────────
          The full credential form renders ONLY when NOT collapsed — i.e. when
          creating a new connection or editing as new. Under a selected saved row
          the SavedConnectionSummary above stands in its place (#327). */}
      {!collapsed && (
        <section style={connsPhase === "ready" && savedConns.length > 0 ? sectionStyle : undefined}>
          <div style={sectionLabelStyle}>01 · Snowflake credentials</div>
          <div style={fieldStyle}>{Field("name", "Connection name", "e.g. prod-analytics")}</div>
          <div style={{ ...fieldStyle, ...fieldRowStyle }}>
            {Field("account", "Account", "xy12345.us-east-1")}
            {Field("user", "User", "SIDIRA_READER")}
          </div>
          <div style={fieldStyle}>
            {Field("password", "Password", "••••••••", "password")}
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
            the connection; it is never echoed back. Connection names are unique
            per workspace — reuse the saved one above rather than re-creating it.
          </div>
        </section>
      )}

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

// ── connection picker — custom searchable combobox (#332) ───────────────────
// At REST this renders ONE control: a `Choose a saved connection (N) ▾` trigger.
// Zero register rows are visible whether the customer has 4 or 40 connections —
// a picker is management surface, not the Connect step's primary content. The
// trigger opens a CUSTOM popover (never a native <select>: a native option can
// carry none of the two-line canonical identity, the health line, or the per-row
// TEST/DELETE affordances, and can't be styled on paper — DESIGN.md §10). The
// popover is a labelled non-modal dialog holding the existing SavedConnectionRow
// rows, now height-capped with internal scroll (~4 rows), sorted
// most-recently-tested first, and fronted by a substring filter for the
// 20-connection case.
//
// a11y model: the trigger is a real <button> with aria-haspopup="dialog" /
// aria-expanded. Enter/Space/ArrowDown open it; on open focus lands on the
// filter input. We deliberately do NOT use role="listbox"/role="option" — each
// row carries its own Test/Delete buttons and can morph into a confirm
// alertdialog, which a strict listbox may not contain (codex). Instead the panel
// is role="dialog", the row list is role="group", and the selected row carries
// aria-current. ArrowUp/ArrowDown still move focus through the FILTERED rows
// (each row's select button takes a roving tabindex); Enter on a focused row
// selects it (the row's own onClick); typing in the filter narrows. A
// panel-level onKeyDown makes Esc close from ANY focused control inside the
// popover, returning focus to the trigger; an outside click closes without
// returning focus. Selecting a row collapses the picker (unmounting the
// trigger), so focus is handed to the collapsed summary instead. Focus-visible
// rides the browser default ink outline — never color-coded state (§4.3). The
// caret is a text ▾, not an imported icon.
function ConnectionPicker({
  conns,
  dupDesignators,
  selectedConnId,
  confirmDeleteId,
  deletingId,
  deleteError,
  testingRowId,
  rowTestError,
  onSelectSaved,
  onTestRow,
  onRequestDelete,
  onCancelDelete,
  onConfirmDelete,
  onNewConnection,
}: {
  conns: ConnectionSummary[];
  dupDesignators: Record<string, string>;
  selectedConnId: string | null;
  confirmDeleteId: string | null;
  deletingId: string | null;
  deleteError: { id: string; message: string } | null;
  testingRowId: string | null;
  rowTestError: { id: string; message: string } | null;
  onSelectSaved: (c: ConnectionSummary) => void;
  onTestRow: (id: string) => void;
  onRequestDelete: (id: string) => void;
  onCancelDelete: () => void;
  onConfirmDelete: (id: string) => void;
  onNewConnection: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState("");
  // The option whose select button currently holds (or should hold) DOM focus —
  // the index into the FILTERED list. Roving tabindex follows it; Arrow keys move
  // it. -1 means focus is on the filter input (the open default), not a row.
  const [activeIndex, setActiveIndex] = useState(-1);

  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const filterRef = useRef<HTMLInputElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);
  // One ref slot per FILTERED option, rebuilt each render so Arrow-key focus
  // always targets the row actually on screen (filtering reshuffles the list).
  const optionRefs = useRef<(HTMLButtonElement | null)[]>([]);

  // Sort once (MRU), then filter — both are display-only and never mutate the
  // source list (which still feeds duplicateDesignators in its own order).
  const sorted = useMemo(() => sortConnsForPicker(conns), [conns]);
  const filtered = useMemo(
    () => sorted.filter((c) => connMatchesFilter(c, filter)),
    [sorted, filter],
  );
  optionRefs.current = [];

  // The trigger's standing label: the SELECTED connection's identity when one is
  // pinned (so the rest-state control still says which is in use), else the count
  // prompt. N is the total saved count, not the filtered count — the trigger is a
  // rest-state control, it shouldn't flicker as the (closed) filter changes.
  const selectedConn = selectedConnId ? conns.find((c) => c.id === selectedConnId) ?? null : null;
  const triggerLabel = selectedConn
    ? `${selectedConn.name}${dupDesignators[selectedConn.id] ?? ""} · ${conns.length} saved`
    : `Choose a saved connection (${conns.length})`;

  // Close + return focus to the trigger (the keyboard-correct close: Esc, or
  // selecting a row, should land the user back on the control they opened).
  const closeAndRefocus = useCallback(() => {
    setOpen(false);
    setActiveIndex(-1);
    triggerRef.current?.focus();
  }, []);

  // Open and, on the next frame, focus the filter input (the typing-first
  // default; Arrow keys then step into the rows).
  const openPanel = useCallback(() => {
    setOpen(true);
    setActiveIndex(-1);
    requestAnimationFrame(() => filterRef.current?.focus());
  }, []);

  // Outside-click closes WITHOUT returning focus (the user clicked elsewhere on
  // purpose — yanking focus back to the trigger would be surprising).
  useEffect(() => {
    if (!open) return;
    const onDocPointer = (e: MouseEvent) => {
      const t = e.target as Node;
      if (panelRef.current?.contains(t) || triggerRef.current?.contains(t)) return;
      setOpen(false);
      setActiveIndex(-1);
    };
    document.addEventListener("mousedown", onDocPointer);
    return () => document.removeEventListener("mousedown", onDocPointer);
  }, [open]);

  // Whenever the active option index changes (Arrow nav), pull DOM focus to that
  // row's select button so the roving tabindex and real focus stay in lockstep.
  useEffect(() => {
    if (!open || activeIndex < 0) return;
    optionRefs.current[activeIndex]?.focus();
  }, [open, activeIndex, filtered.length]);

  // If the filter narrows the list below the active index (or to empty), pull the
  // active index back into range so Arrow nav never points at a vanished row.
  useEffect(() => {
    if (activeIndex >= filtered.length) setActiveIndex(filtered.length > 0 ? filtered.length - 1 : -1);
  }, [filtered.length, activeIndex]);

  const moveActive = (delta: number) => {
    if (filtered.length === 0) return;
    setActiveIndex((i) => {
      const start = i < 0 ? (delta > 0 ? 0 : filtered.length - 1) : i + delta;
      return Math.max(0, Math.min(filtered.length - 1, start));
    });
  };

  // Keydown on the TRIGGER: Enter/Space/Down open (Down lands focus on filter).
  const onTriggerKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      openPanel();
    }
  };

  // Panel-level Esc — fires regardless of which inner control holds focus
  // (filter input, an option row, or a row's Test/Delete/confirm button), so Esc
  // always closes the popover and returns focus to the trigger (codex P2). Bound
  // on the panel container, which sees the bubbled keydown from any child.
  const onPanelKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape") {
      e.preventDefault();
      closeAndRefocus();
    }
  };

  // Keydown on the FILTER input: Down steps into the first row; typing falls
  // through to narrow. Up from the filter is a no-op (already top). Esc is
  // handled at the panel level above.
  const onFilterKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      moveActive(1);
    }
  };

  // Keydown on a row's select button: Arrow nav; Enter selects (handled by the
  // button's own onClick, so we let it fall through); Up from the first row
  // returns to the filter input. Esc is handled at the panel level above.
  const onOptionKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      moveActive(1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (activeIndex <= 0) {
        setActiveIndex(-1);
        filterRef.current?.focus();
      } else {
        moveActive(-1);
      }
    }
    // Enter/Space: the native <button> fires its onClick (handleSelectSaved →
    // collapse), so we don't intercept them here. Esc bubbles to onPanelKeyDown.
  };

  const panelId = "saved-connection-panel";
  const listId = "saved-connection-list";

  return (
    <section style={{ marginBottom: 4 }}>
      <div style={sectionLabelStyle}>Saved connections</div>
      <div style={hintStyle}>
        Reuse a connection you&apos;ve already saved — no need to re-enter its
        password. Pick one, then test and continue. Or enter a different
        connection below.
      </div>

      <div style={{ ...fieldStyle, position: "relative" }}>
        {/* The rest-state control — ONE button, no rows. ▾ is a text glyph, not
            an imported icon (§10). */}
        <button
          ref={triggerRef}
          type="button"
          onClick={() => (open ? closeAndRefocus() : openPanel())}
          onKeyDown={onTriggerKeyDown}
          aria-haspopup="dialog"
          aria-expanded={open}
          aria-controls={open ? panelId : undefined}
          style={{
            ...secondaryBtnStyle,
            width: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            textAlign: "left",
            fontWeight: 500,
          }}
        >
          <span
            style={{
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {triggerLabel}
          </span>
          <span aria-hidden="true" style={{ fontFamily: FONT_MONO, fontSize: 11, color: TOKENS.inkMuted }}>
            {open ? "▴" : "▾"}
          </span>
        </button>

        {open && (
          <div
            ref={panelRef}
            id={panelId}
            role="dialog"
            aria-label="Saved connections"
            onKeyDown={onPanelKeyDown}
            style={{
              marginTop: 6,
              border: `0.75px solid ${TOKENS.rule}`,
              borderRadius: 4,
              background: TOKENS.paperElevated,
              overflow: "hidden",
            }}
          >
            {/* Filter — always present (cheap), the part the 20-connection case
                needs. Plain mono input; narrows by name/account/db/role. */}
            <div style={{ padding: 8, borderBottom: `0.75px solid ${TOKENS.rule}` }}>
              <label htmlFor="conn-filter" style={{ ...sublabelStyle, marginBottom: 4 }}>
                Filter connections
              </label>
              <input
                id="conn-filter"
                ref={filterRef}
                type="text"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                onKeyDown={onFilterKeyDown}
                placeholder="name · account · database · role"
                autoComplete="off"
                aria-controls={listId}
                style={monoInputStyle}
              />
            </div>

            {/* The register, relocated into the popover: height-capped to ~4
                rows with internal scroll so it never grows unbounded. A plain
                grouped list of row buttons (NOT role="listbox" — the rows carry
                their own Test/Delete actions and can become a confirm dialog,
                which a strict listbox may not contain; codex P2). */}
            <div
              id={listId}
              role="group"
              aria-label="Saved connections"
              style={{ maxHeight: 268, overflowY: "auto" }}
            >
              {filtered.length === 0 ? (
                <div style={{ ...railCaptionStyle, padding: "12px", textTransform: "uppercase" }}>
                  No connections match
                </div>
              ) : (
                filtered.map((c, i) => (
                  <SavedConnectionRow
                    key={c.id}
                    conn={c}
                    designator={dupDesignators[c.id] ?? ""}
                    selected={c.id === selectedConnId}
                    confirmingDelete={confirmDeleteId === c.id}
                    deleting={deletingId === c.id}
                    deleteError={deleteError && deleteError.id === c.id ? deleteError.message : null}
                    testing={testingRowId === c.id}
                    testError={rowTestError && rowTestError.id === c.id ? rowTestError.message : null}
                    onSelect={() => {
                      // Select collapses the whole picker into the #327 "Using
                      // saved connection" summary, which UNMOUNTS this trigger —
                      // so we must NOT refocus it (that would land focus on a
                      // detached node / fall to <body>; codex P3). Just close;
                      // collapse swaps in the summary section in its place.
                      setOpen(false);
                      setActiveIndex(-1);
                      onSelectSaved(c);
                    }}
                    onTest={() => onTestRow(c.id)}
                    onRequestDelete={() => onRequestDelete(c.id)}
                    onCancelDelete={onCancelDelete}
                    onConfirmDelete={() => onConfirmDelete(c.id)}
                    optionTabIndex={activeIndex === i ? 0 : -1}
                    optionRef={(el) => {
                      optionRefs.current[i] = el;
                    }}
                    onOptionKeyDown={onOptionKeyDown}
                  />
                ))
              )}
            </div>
          </div>
        )}
      </div>

      <div style={{ ...fieldStyle }}>
        <button type="button" onClick={onNewConnection} style={secondaryBtnStyle}>
          + Enter a different connection
        </button>
      </div>
    </section>
  );
}

// ── one register row (#327) ─────────────────────────────────────────────────
// A dense ~2-line paper row: the canonical identity line, then a mono subline,
// with a quiet delete affordance. Selection rides a single ink hairline (the
// recessed-paper fill + ink left edge) — no color-coded background. The whole
// row is a real <button> (keyboard-reachable, §7.8); the delete affordance is a
// sibling text button (not nested — a button can't contain a button). Deleting
// opens an INLINE honest-text confirm in place of the row body (§7.7/§10): no
// browser confirm(), no modal, no red fill, no icon.
function SavedConnectionRow({
  conn,
  designator,
  selected,
  confirmingDelete,
  deleting,
  deleteError,
  testing,
  testError,
  onSelect,
  onTest,
  onRequestDelete,
  onCancelDelete,
  onConfirmDelete,
  // #332 listbox-option wiring (optional — only set when the row lives inside
  // the ConnectionPicker popover). `optionTabIndex` carries roving tabindex (the
  // active option is 0, the rest -1); `optionRef` lets the picker move DOM focus
  // through the filtered rows on Arrow keys; `onOptionKeyDown` routes those keys.
  optionTabIndex,
  optionRef,
  onOptionKeyDown,
}: {
  conn: ConnectionSummary;
  designator: string;
  selected: boolean;
  confirmingDelete: boolean;
  deleting: boolean;
  deleteError: string | null;
  testing: boolean;
  testError: string | null;
  onSelect: () => void;
  onTest: () => void;
  onRequestDelete: () => void;
  onCancelDelete: () => void;
  onConfirmDelete: () => void;
  optionTabIndex?: number;
  optionRef?: (el: HTMLButtonElement | null) => void;
  onOptionKeyDown?: (e: React.KeyboardEvent<HTMLButtonElement>) => void;
}) {
  // Quiet row action — mono designator button at hairline weight (§7.7). Used
  // for both the Delete trigger and the confirm/cancel pair so the affordance
  // language stays consistent.
  const rowActionStyle: React.CSSProperties = {
    background: "transparent",
    border: `0.75px solid ${TOKENS.rule}`,
    borderRadius: 2,
    padding: "2px 8px",
    fontFamily: FONT_MONO,
    fontSize: 10,
    letterSpacing: "0.06em",
    textTransform: "uppercase",
    color: TOKENS.inkMuted,
    cursor: "pointer",
    whiteSpace: "nowrap",
  };

  const identity = connectionIdentity(conn);
  const subline = connectionSubline(conn);
  // Last-known health in words (#328) — never a dot or colored fill (§4.3/§10).
  // While a per-row test is in flight we say so honestly (§8.6: no spinners).
  const healthLine = testing ? "TESTING…" : connectionHealthLine(conn);

  // Keyboard focus handoff for the inline delete confirm (#332/codex P2).
  // Opening the confirm REPLACES the focused Delete button with the alertdialog,
  // which would drop focus to <body> — especially jarring inside the otherwise
  // keyboard-managed picker popover. So we focus Cancel when the confirm mounts.
  // When the confirm CLOSES without unmounting the row — i.e. the user cancelled
  // — we return focus to the row's Delete button. The other two outcomes need no
  // restore: a successful delete unmounts the whole row (nothing to return to),
  // and a delete ERROR keeps confirmingDelete true (the dialog stays open showing
  // COULD NOT DELETE · …, with focus still on Cancel) — so this effect only fires
  // on the cancel transition, which is exactly right. Runs on each transition.
  const cancelRef = useRef<HTMLButtonElement | null>(null);
  const deleteBtnRef = useRef<HTMLButtonElement | null>(null);
  const wasConfirming = useRef(false);
  useEffect(() => {
    if (confirmingDelete) {
      // Focus Cancel both when the confirm first opens AND when a delete attempt
      // fails (deleteError appears): the focus was on the confirm Delete button,
      // and a failed delete leaves the dialog open — so we pull focus back to the
      // safe Cancel action, where the COULD NOT DELETE · … message sits adjacent
      // for the screen reader (codex). deleteError is in deps so the error
      // transition refocuses too.
      cancelRef.current?.focus();
    } else if (wasConfirming.current) {
      // Confirm closed without unmounting the row → the user cancelled; restore
      // focus to the Delete affordance they came from.
      deleteBtnRef.current?.focus();
    }
    wasConfirming.current = confirmingDelete;
  }, [confirmingDelete, deleteError]);

  // The inline confirm replaces the row's clickable body so a mis-click can't
  // select-and-delete in one motion. Honest text states the exact scope (§7.7).
  if (confirmingDelete) {
    return (
      <div
        style={{
          borderBottom: `0.75px solid ${TOKENS.rule}`,
          // alert as a border designator only — the words carry the meaning (§4.3).
          ...railAlertStyle,
          borderTopWidth: 0,
          borderLeftWidth: 0,
          borderRightWidth: 0,
          borderRadius: 0,
        }}
        role="alertdialog"
        aria-label={`Confirm delete ${conn.name}`}
      >
        <div style={{ fontSize: 13, color: TOKENS.ink, lineHeight: 1.45 }}>
          Delete saved connection <strong>{conn.name}</strong>
          {designator ? <span style={railCaptionStyle}>{designator.trim()}</span> : null}? Existing
          persona builds keep their records; future builds can&apos;t use this credential.
        </div>
        {deleteError && (
          <div style={{ ...railCaptionStyle, marginTop: 6, color: TOKENS.ink }}>
            COULD NOT DELETE · {deleteError.toUpperCase()}
          </div>
        )}
        <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
          <button
            ref={cancelRef}
            type="button"
            onClick={onCancelDelete}
            disabled={deleting}
            style={rowActionStyle}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirmDelete}
            disabled={deleting}
            style={{
              ...rowActionStyle,
              color: TOKENS.ink,
              borderColor: TOKENS.ink,
              opacity: deleting ? 0.5 : 1,
              cursor: deleting ? "not-allowed" : "pointer",
            }}
          >
            {deleting ? "Deleting…" : "Delete"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr auto",
        alignItems: "center",
        gap: 10,
        borderBottom: `0.75px solid ${TOKENS.rule}`,
        background: selected ? TOKENS.paperRecessed : "transparent",
        // The single selected-state emphasis: a 2px ink left edge. No color fill,
        // no border recolor beyond the recessed-paper treatment (§7/#327 fix 4).
        borderLeft: `2px solid ${selected ? TOKENS.ink : "transparent"}`,
      }}
    >
      <button
        type="button"
        onClick={onSelect}
        // In the picker popover this button is the row's primary action inside a
        // non-modal dialog (NOT an ARIA listbox option — the row also carries
        // sibling Test/Delete buttons and can morph into a confirm dialog, which
        // a strict listbox/option may not contain; codex P2). It takes a roving
        // tabindex so Arrow keys step focus through the rows, and aria-current
        // marks the pinned connection. Standalone (no optionRef) it stays a plain
        // pressed toggle, exactly as #327 shipped it.
        {...(optionRef
          ? {
              "aria-current": selected ? ("true" as const) : undefined,
              tabIndex: optionTabIndex ?? -1,
              ref: optionRef,
              onKeyDown: onOptionKeyDown,
            }
          : { "aria-pressed": selected })}
        style={{
          textAlign: "left",
          background: "transparent",
          border: "none",
          padding: "9px 12px",
          cursor: "pointer",
          minWidth: 0,
          display: "flex",
          flexDirection: "column",
          gap: 3,
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
          <span style={{ fontSize: 13.5, fontWeight: 600, color: TOKENS.ink }}>
            {identity}
            {designator ? <span style={{ color: TOKENS.inkMuted }}>{designator}</span> : null}
          </span>
          {selected && <Chip>SELECTED</Chip>}
        </div>
        <div
          style={{
            ...railCaptionStyle,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {subline}
        </div>
        {/* Health line (#328) — honest text in the mono caption rail. The
            status reads in WORDS (OK · TESTED … / FAILED · AUTH / UNTESTED);
            meaning never rides on color or a dot (§4.3/§10). */}
        <div style={{ ...railCaptionStyle, textTransform: "uppercase" }}>{healthLine}</div>
        {/* Fallback verdict (#328): only shown when a row-test failed but the
            persisted/refreshed status line didn't pick it up (best-effort
            persistence or a failed refresh) — so the verdict is never silently
            lost. Honest text, ink (no color-coded fill). */}
        {testError && (
          <div style={{ ...railCaptionStyle, color: TOKENS.ink }}>
            TEST FAILED · {testError.toUpperCase()}
          </div>
        )}
      </button>
      {/* Row actions: a quiet in-place TEST (re-runs the connectivity test and
          refreshes this row's status without selecting it), then Delete. Both
          are hairline mono text buttons — no fills, no icons (§7.7/§10). */}
      <div style={{ display: "flex", gap: 6, marginRight: 12 }}>
        <button
          type="button"
          onClick={onTest}
          disabled={testing}
          aria-label={`Test saved connection ${conn.name}`}
          style={{ ...rowActionStyle, opacity: testing ? 0.5 : 1, cursor: testing ? "not-allowed" : "pointer" }}
        >
          {testing ? "Testing…" : "Test"}
        </button>
        <button
          ref={deleteBtnRef}
          type="button"
          onClick={onRequestDelete}
          aria-label={`Delete saved connection ${conn.name}`}
          style={rowActionStyle}
        >
          Delete
        </button>
      </div>
    </div>
  );
}

// ── collapse-on-select summary (#327) ───────────────────────────────────────
// Replaces the full prefilled credential form when a saved connection is in use.
// A compact record: the canonical identity, a key/value grid of the connection's
// fields, and two actions — "Use different connection" (back to the picker /
// blank form) and "Edit as new" (the full form, prefilled as a NEW mint). The
// password never appears (it's never returned); reuse needs none.
function SavedConnectionSummary({
  conn,
  designator,
  focusOnMount,
  onFocusConsumed,
  onUseDifferent,
  onEditAsNew,
}: {
  conn: ConnectionSummary;
  designator: string;
  focusOnMount?: boolean;
  onFocusConsumed?: () => void;
  onUseDifferent: () => void;
  onEditAsNew: () => void;
}) {
  const rows: [string, string][] = [
    ["Account", conn.account],
    ["User", conn.user],
    ["Database", conn.schema ? `${conn.database}.${conn.schema}` : conn.database],
    ["Warehouse / role", `${conn.warehouse} · ${conn.role}`],
  ];
  // Focus landing after a picker selection collapses to this summary (#332/codex
  // P2): the row button the user clicked unmounts with the picker, so on the
  // keyboard path focus would fall to <body>. When the parent signals the
  // collapse came from a picker selection (focusOnMount), we move focus to this
  // summary's heading (focusable but non-tabbable). We do NOT infer the path from
  // document.activeElement — it's already <body> by mount, which is exactly the
  // case we need to rescue — so the explicit flag is the reliable signal; a cold
  // load with a pre-selected connection passes focusOnMount=false and is left
  // alone. onFocusConsumed clears the one-shot flag in the parent.
  const headingRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (!focusOnMount) return;
    headingRef.current?.focus();
    onFocusConsumed?.();
    // Run once on mount for the selection that triggered the collapse.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <section style={{ marginBottom: 4 }}>
      <div ref={headingRef} tabIndex={-1} style={{ ...sectionLabelStyle, outline: "none" }}>
        Using saved connection
      </div>
      <div
        style={{
          ...fieldStyle,
          background: TOKENS.paperRecessed,
          border: `0.75px solid ${TOKENS.rule}`,
          borderLeft: `2px solid ${TOKENS.ink}`,
          borderRadius: 4,
          padding: "12px 14px",
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: TOKENS.ink }}>
            {conn.name}
            {designator ? <span style={{ color: TOKENS.inkMuted }}>{designator}</span> : null}
          </span>
          <Chip>{conn.kind.toUpperCase()}</Chip>
          <Chip>REUSING — NO PASSWORD NEEDED</Chip>
          {/* Last-known health in words (#328) — a bordered mono chip, not a
              colored dot (§4.3/§10). Re-test from the 03 · Test step below. */}
          <Chip>{connectionHealthLine(conn)}</Chip>
        </div>
        <dl
          style={{
            margin: 0,
            marginTop: 10,
            display: "grid",
            gridTemplateColumns: "auto 1fr",
            gap: "4px 16px",
          }}
        >
          {rows.map(([dt, dd]) => (
            <div key={dt} style={{ display: "contents" }}>
              <dt
                style={{
                  fontSize: 10,
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  color: TOKENS.inkMuted,
                }}
              >
                {dt}
              </dt>
              <dd
                style={{
                  margin: 0,
                  fontFamily: FONT_MONO,
                  fontSize: 12,
                  color: TOKENS.ink,
                  overflowWrap: "break-word",
                  ...TNUM,
                }}
              >
                {dd}
              </dd>
            </div>
          ))}
        </dl>
      </div>
      <div style={{ ...fieldStyle, display: "flex", gap: 10, flexWrap: "wrap" }}>
        <button type="button" onClick={onUseDifferent} style={secondaryBtnStyle}>
          Use different connection
        </button>
        <button type="button" onClick={onEditAsNew} style={secondaryBtnStyle}>
          Edit as new
        </button>
      </div>
      <div style={hintStyle}>
        Reusing this connection — its password stays on the server, so just test
        and continue. &ldquo;Edit as new&rdquo; opens a fresh form prefilled from these
        values to mint a separate connection (a new password, a new name).
      </div>
    </section>
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
