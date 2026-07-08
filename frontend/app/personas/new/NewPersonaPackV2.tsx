"use client";

// ───────────────────────────────────────────────────────────────────────────
// /personas/new — the v2 dark "Reading Console" reskin of the persona-pack
// builder wizard.
//
// FORK-AND-RESTYLE of NewPersonaPackLegacy.tsx (the FROZEN source of truth for
// ALL behaviour). This file reproduces every step, state branch, form-field
// binding, validation gate, mutation/submit call, poll loop, error/loading
// branch, <Link>/button/onClick and navigation the legacy wizard has —
// byte-for-byte in LOGIC — and changes ONLY the presentation (markup + the
// style objects + the wizard chrome) into the dark Console language of
// design-rethink/mocks/personas-new.html.
//
// It renders INSIDE AppShellV2 surface="console" (the shell owns the dark rail +
// appbar). The whole body is scoped under a single `.rconsole` wrapper so the
// dark token block applies; we do NOT emit the console's own rail/topbar.
//
// The pure-logic helpers (apiErrorMessage/apiErrorParts/utcStamp) are imported
// verbatim from ./wizard-ui — they carry no presentation. Every PRESENTATION
// primitive the legacy imported from ./wizard-ui (Chip, AddButton, RemoveButton,
// and the style objects: inputStyle, selectStyle, monoInputStyle, textareaStyle,
// sectionStyle, sectionLabelStyle, sublabelStyle, hintStyle, fieldStyle,
// fieldRowStyle, primaryBtnStyle, secondaryBtnStyle, railAlertStyle,
// railCaptionStyle, errorBannerStyle, okBannerStyle, statusLineStyle) is
// re-declared LOCALLY here against the dark Console tokens — same name, same
// shape, only the colour/surface values change. No wizard behaviour is touched.
//
// Honesty law (DESIGN.md §8.1/§9): confidence + distinctiveness ride the WORDING
// never colour; no verdict fill; errors carry the alert hairline with the
// message in ink; pending states are honest mono text (no spinners). All
// disclosure copy is preserved verbatim from the legacy.
// ───────────────────────────────────────────────────────────────────────────

import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  createFeatureStore,
  createPersonaBuild,
  deleteFeatureStore,
  extractDocuments,
  getPersonaBuild,
  getPersonaBuildEvents,
  getPersonaPackDetail,
  isBuildTerminal,
  listFeatureStores,
  previewFeatureStore,
  promotePersonaPack,
  suggestMapping,
  suggestMappingForColumns,
  testFeatureStore,
  type BuildConfig,
  type BuildEvent,
  type BuildK,
  type BuildSummary,
  type ColumnAssignment,
  type ColumnProfile,
  type ConnectionSummary,
  type EntityDocument,
  type EstimabilityBuildConfig,
  type ExtractionField,
  type FeatureGroup,
  type LeverRegistryEntry,
  type LlmProvider,
  type MappingSuggestion,
  type MetricRegistryEntry,
  type MetricType,
  type PackSummary,
  type PersonaPackDetail,
  type PersonaProfileView,
  type ProfileBlockView,
  type SnowflakeConnectionRequest,
  type WeightScheme,
  FEATURE_GROUPS,
  METRIC_TYPES,
} from "@/lib/api";
import AppShellV2 from "@/components/v2/AppShellV2";
// Pure-logic helpers only — these carry NO presentation, so they stay shared.
import { apiErrorMessage, apiErrorParts, utcStamp } from "./wizard-ui";

// ── scoped dark Console tokens + wizard chrome ──────────────────────────────
// Mirrors design-rethink/mocks/personas-new.html. The body lives under
// `.rconsole`; AppShellV2 owns the rail/appbar, so we only emit the stepper +
// header strip + body scaffold here.
const RCONSOLE_CSS = `
.rconsole{
  --console-900:#0B1220; --console-850:#10192A; --console-800:#161F32;
  --console-750:#1D2740; --console-700:#26314C; --console-line:#33405C;
  --text-hi:#F2F4F8; --text:#C6CCD8; --text-mut:#929BAE; --text-faint:#646E84;
  --signal:#48EFCA; --signal-dim:#39B894;
  --spread:#C8B68A; --spread-dim:#90815F;
  --edge-warn:#C9A227; --alert:#F0683C;
  --r-well:4px; --r-panel:8px; --r-frame:10px;
  --font-sans:var(--v2-font-sans,var(--font-sans,system-ui,sans-serif));
  --font-mono:var(--v2-font-mono,var(--font-mono,ui-monospace,"JetBrains Mono",SFMono-Regular,monospace));
  color:var(--text);
  font-family:var(--font-sans); font-size:15px; line-height:1.55;
  -webkit-font-smoothing:antialiased;
  font-variant-numeric:tabular-nums;
}
.rconsole *{box-sizing:border-box; font-variant-numeric:tabular-nums;}
.rconsole a{color:inherit; text-decoration:none;}
.rconsole ::selection{background:rgba(72,239,202,.18); color:var(--text-hi);}
.rconsole code{font-family:var(--font-mono);}

/* page header strip */
.rconsole .pagehead{padding:24px 28px 18px;
  border-bottom:1px solid var(--console-line); display:flex;
  align-items:baseline; gap:16px; flex-wrap:wrap;}
.rconsole .pagehead h1{margin:0; font-size:24px; font-weight:600;
  letter-spacing:-.02em; color:var(--text-hi);}
.rconsole .pagehead .desig{font-family:var(--font-mono); font-size:11px;
  letter-spacing:.06em; color:var(--text-mut);}
.rconsole .pagehead .stamp{margin-left:auto; font-family:var(--font-mono);
  font-size:10px; letter-spacing:.08em; color:var(--text-mut);
  border:1px solid var(--console-line); border-radius:var(--r-well);
  padding:3px 8px; white-space:nowrap;}

/* stepper — the genuine ordered flow keeps numerals (§2.3) */
.rconsole .stepper{display:flex; background:var(--console-800);
  border-bottom:1px solid var(--console-line);}
.rconsole .step{flex:1; padding:10px 14px;
  border-right:1px solid var(--console-line); position:relative;}
.rconsole .step:last-child{border-right:none;}
.rconsole .step.done{background:var(--console-850);}
.rconsole .step.active::after{content:""; position:absolute; left:0; right:0;
  bottom:-1px; height:2px; background:var(--signal-dim);}
.rconsole .step .num{font-family:var(--font-mono); font-size:10px;
  letter-spacing:.1em; color:var(--text-mut);}
.rconsole .step .lbl{font-size:13px; margin-top:2px; color:var(--text-mut);}
.rconsole .step.active .lbl{color:var(--text-hi); font-weight:600;}
.rconsole .step.done .lbl{color:var(--text);}

/* body column */
.rconsole .bodywrap{padding:24px 28px 96px;}

/* Ground step: form column + compact manifest rail (§7.4 wizard posture).
   Collapses to one stacked column at the §7.9 rail threshold (§7.5). */
.rconsole .groundgrid{display:grid; grid-template-columns:minmax(0,1fr) 240px;
  gap:28px; max-width:1048px; align-items:start;}
@media (max-width:1023px){
  .rconsole .groundgrid{grid-template-columns:minmax(0,1fr); max-width:760px;}
  .rconsole .groundrail{position:static;}
}

/* focus rings */
.rconsole a:focus-visible, .rconsole button:focus-visible,
.rconsole input:focus-visible, .rconsole select:focus-visible,
.rconsole textarea:focus-visible{
  outline:2px solid var(--signal-dim); outline-offset:2px;
  border-radius:var(--r-well);}

@media (prefers-reduced-motion:reduce){
  .rconsole *{animation:none!important;}
}
`;

// ── dark-console fonts (mirrors lib/design FONT_* but resolved to the v2 vars) ─
const FONT_SANS = "var(--v2-font-sans, var(--font-sans), system-ui, sans-serif)";
const FONT_MONO =
  "var(--v2-font-mono, var(--font-mono), ui-monospace, monospace)";
const TNUM: React.CSSProperties = {
  fontVariantNumeric: "tabular-nums",
};

// ── dark-console token map — the wizard-ui palette restated for the Console ───
const C = {
  textHi: "var(--text-hi)",
  text: "var(--text)",
  textMut: "var(--text-mut)",
  line: "var(--console-line)",
  panel: "var(--console-800)",
  panelRaised: "var(--console-750)",
  panelRecessed: "var(--console-900)",
  signal: "var(--signal)",
  signalDim: "var(--signal-dim)",
  alert: "var(--alert)",
  success: "var(--signal-dim)",
} as const;

// A bordered mono confidence/status chip — NOT a colored fill. Confidence is
// carried by the wording (HIGH / MED / LOW), never by color (§4.3).
function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span
      style={{
        fontFamily: FONT_MONO,
        fontSize: 10,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        color: C.textMut,
        border: `1px solid ${C.line}`,
        borderRadius: 4,
        padding: "1px 6px",
        whiteSpace: "nowrap",
        ...TNUM,
      }}
    >
      {children}
    </span>
  );
}

// ── restyled shared styles — dark Console form controls ──────────────────────
const inputStyle: React.CSSProperties = {
  width: "100%",
  fontFamily: FONT_SANS,
  fontSize: 14,
  color: C.textHi,
  background: C.panelRecessed,
  border: `1px solid ${C.line}`,
  borderRadius: 4,
  padding: "8px 11px",
  boxSizing: "border-box",
};

const selectStyle: React.CSSProperties = {
  ...inputStyle,
  fontFamily: FONT_MONO,
  fontSize: 13,
};

const monoInputStyle: React.CSSProperties = {
  ...inputStyle,
  fontFamily: FONT_MONO,
  fontSize: 13,
};

const textareaStyle: React.CSSProperties = {
  ...monoInputStyle,
  minHeight: 120,
  resize: "vertical",
  lineHeight: 1.5,
};

const sectionStyle: React.CSSProperties = {
  marginTop: 28,
};

const sectionLabelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 11,
  fontWeight: 500,
  letterSpacing: "0.16em",
  textTransform: "uppercase",
  color: C.textMut,
  paddingBottom: 8,
  borderBottom: `1px solid ${C.line}`,
  ...TNUM,
};

const sublabelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 10,
  fontWeight: 500,
  letterSpacing: "0.14em",
  textTransform: "uppercase",
  color: C.textMut,
  marginBottom: 6,
};

const hintStyle: React.CSSProperties = {
  fontSize: 12,
  color: C.textMut,
  marginTop: 6,
  lineHeight: 1.45,
  maxWidth: "52ch",
};

const fieldStyle: React.CSSProperties = {
  marginTop: 16,
};

const fieldRowStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: 16,
};

const primaryBtnStyle: React.CSSProperties = {
  background: C.panelRaised,
  color: C.textHi,
  border: `1px solid ${C.line}`,
  borderRadius: 4,
  padding: "8px 16px",
  fontWeight: 500,
  fontSize: 13,
  fontFamily: FONT_SANS,
  cursor: "pointer",
};

const secondaryBtnStyle: React.CSSProperties = {
  background: "transparent",
  color: C.text,
  border: `1px solid ${C.line}`,
  borderRadius: 4,
  padding: "8px 16px",
  fontWeight: 500,
  fontSize: 13,
  fontFamily: FONT_SANS,
  cursor: "pointer",
};

const railAlertStyle: React.CSSProperties = {
  padding: "8px 10px",
  background: C.panelRecessed,
  border: `1px solid var(--alert)`,
  borderRadius: 4,
  // alert is accent-only (border) — the message reads in ink (§4.3/§7.7).
  color: C.text,
  fontSize: 12,
  lineHeight: 1.45,
  overflowWrap: "break-word",
};

const railCaptionStyle: React.CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 10.5,
  color: C.textMut,
  letterSpacing: "0.04em",
  lineHeight: 1.5,
  ...TNUM,
};

const errorBannerStyle: React.CSSProperties = {
  marginBottom: 16,
  padding: "12px 16px",
  background: C.panelRecessed,
  border: `1px solid var(--alert)`,
  borderRadius: 4,
  // alert is accent-only (border) — the message reads in ink (§4.3/§7.7).
  color: C.text,
  fontSize: 14,
  maxWidth: 620,
  boxSizing: "border-box",
};

// A success/confirmation note — honest text (§8.6). Border carries the accent;
// the message still reads in ink so meaning never rides on color alone (§4.3).
const okBannerStyle: React.CSSProperties = {
  padding: "10px 12px",
  background: C.panelRecessed,
  border: `1px solid ${C.signalDim}`,
  borderRadius: 4,
  color: C.text,
  fontSize: 13,
  lineHeight: 1.45,
  overflowWrap: "break-word",
};

// Honest-text status line, mono uppercase — the §8.6 "no spinners" primitive.
const statusLineStyle: React.CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 12,
  letterSpacing: "0.06em",
  color: C.textHi,
  ...TNUM,
};

// ── step metadata ─────────────────────────────────────────────────────────
const STEPS = [
  { id: 1, label: "Connect" },
  { id: 2, label: "Map" },
  { id: 3, label: "Ground" },
  { id: 4, label: "Build" },
  { id: 5, label: "Evaluate" },
  { id: 6, label: "Promote" },
] as const;
const LAST_STEP = STEPS.length;

const GROUP_LABELS: Record<FeatureGroup, string> = {
  demographic_identity: "Demographic / identity",
  behavioral_patterns: "Behavioral patterns",
  motivations_jtbd: "Motivations / JTBD",
  pain_points_friction: "Pain points / friction",
  value_sensitivity: "Value sensitivity",
  channel_tech_behavior: "Channel / tech behavior",
  loyalty_lifecycle: "Loyalty / lifecycle",
};

type Assignment = FeatureGroup | "ignore";
type SourceMode = "table" | "sql";
// #3 doc feeder: where the population rows come from — a Snowflake feature store
// (the existing flow) or unstructured documents extracted into feature rows.
type SourceKind = "feature_store" | "documents";

// A draft extraction field in the schema builder (type may be unselected while
// editing, hence the "" option that the form rejects before continuing).
interface DraftField {
  name: string;
  type: MetricType | "";
  description: string;
}

const METRIC_TYPE_HINTS: Record<MetricType, string> = {
  count: "a count of occurrences (≥ 0)",
  score: "a numeric rating / level",
  ratio: "a fraction between 0 and 1",
  flag: "true / false",
  categorical: "a single short label",
  json_ratios: "{label: fraction} object",
  json_counts: "{label: count} object",
  tenure_days: "a number of days",
};

const emptyDraftField = (): DraftField => ({ name: "", type: "", description: "" });
const emptyDocEntity = (): EntityDocument => ({ entity_id: "", text: "" });

// ── Step 3 · Ground (#596/#597) — estimability declaration drafts ───────────
// Draft state per column, keyed by column name. Optional fields ride the
// payload only when non-empty; a draft with selected=false never rides at all.
interface MetricDraft {
  selected: boolean;
  displayName: string;
  semanticType: "" | NonNullable<MetricRegistryEntry["semantic_type"]>;
  description: string;
  synonyms: string; // comma-separated in the form → string[] in the payload
  prePeriodColumn: string; // "" = none declared → the metric builds UNGUARDED
}

interface LeverDraft {
  selected: boolean;
  displayName: string;
  description: string;
}

const emptyMetricDraft = (): MetricDraft => ({
  selected: false,
  displayName: "",
  semanticType: "",
  description: "",
  synonyms: "",
  prePeriodColumn: "",
});

const emptyLeverDraft = (): LeverDraft => ({
  selected: false,
  displayName: "",
  description: "",
});

const SEMANTIC_TYPES: {
  id: NonNullable<MetricRegistryEntry["semantic_type"]>;
  label: string;
}[] = [
  { id: "rate", label: "Rate" },
  { id: "duration", label: "Duration" },
  { id: "cumulative", label: "Cumulative" },
  { id: "count", label: "Count" },
];

// dtype strings come from two producers: the Snowflake preview derives them
// from the sampled Python values (`type(v).__name__` → "int" / "float" /
// "bool" / "Decimal" / "str" / "unknown"), and the documents extractor reports
// the declared metric type ("count" / "score" / "ratio" / "flag" /
// "tenure_days" / "categorical" / …). Numeric-ish = anything that could carry
// an outcome metric reading.
const NUMERIC_METRIC_DTYPES = new Set(["count", "score", "ratio", "flag", "tenure_days"]);
const isNumericDtype = (dtype: string): boolean => {
  const d = dtype.toLowerCase();
  return (
    d.includes("int") ||
    d.includes("float") ||
    d.includes("number") ||
    d.includes("numeric") ||
    d.includes("decimal") ||
    d.includes("double") ||
    d.includes("real") ||
    d.includes("bool") ||
    NUMERIC_METRIC_DTYPES.has(d)
  );
};

// A lever candidate is a binary exposure flag: bool-typed, or ≤ 2 distinct
// values in the sample (distinct_count is null when the values are unhashable).
const isLeverCandidate = (c: ColumnProfile): boolean => {
  const d = c.dtype.toLowerCase();
  if (d.includes("bool") || d === "flag") return true;
  return c.distinct_count != null && c.distinct_count <= 2;
};

const splitSynonyms = (raw: string): string[] =>
  raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

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

const credFingerprint = (f: ConnForm) =>
  JSON.stringify([f.name, f.account, f.user, f.password, f.warehouse, f.role, f.database, f.schema]);

const testFingerprint = (f: ConnForm, mode: SourceMode, table: string, sql: string) =>
  JSON.stringify([credFingerprint(f), mode, table, sql]);

const connectionIdentity = (c: ConnectionSummary): string => {
  const db = c.schema ? `${c.database}.${c.schema}` : c.database;
  return `${c.name} · ${db} · ${c.warehouse} · ${c.role}`;
};

const connectionSubline = (c: ConnectionSummary): string => {
  const idTail = c.id.replace(/^fs-/, "").slice(0, 8);
  return `${c.account} · ${c.user} · ${idTail}`;
};

const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

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

const connMatchesFilter = (c: ConnectionSummary, q: string): boolean => {
  const needle = q.trim().toLowerCase();
  if (!needle) return true;
  const hay = [c.name, c.account, c.user, c.database, c.schema ?? "", c.warehouse, c.role]
    .join(" ")
    .toLowerCase();
  return hay.includes(needle);
};

const POLL_MS = 2500; // #28 watch cadence while pending/running.

export default function NewPersonaPackV2() {
  const [step, setStep] = useState(1);

  // ── Step 1 · source kind (#3 doc feeder) ────────────────────────────────
  const [sourceKind, setSourceKind] = useState<SourceKind>("feature_store");

  // ── Step 1 · Connect (#26) ──────────────────────────────────────────────
  const [conn, setConn] = useState<ConnForm>(emptyConnForm());
  const [sourceMode, setSourceMode] = useState<SourceMode>("table");
  const [tableFqn, setTableFqn] = useState("");
  const [sql, setSql] = useState("");
  const [connection, setConnection] = useState<ConnectionSummary | null>(null);
  const [testing, setTesting] = useState(false);
  const [testError, setTestError] = useState<{ kind: string | null; message: string } | null>(null);
  const [okFingerprint, setOkFingerprint] = useState<string | null>(null);
  const [connFingerprint, setConnFingerprint] = useState<string | null>(null);
  const [savedConns, setSavedConns] = useState<ConnectionSummary[]>([]);
  const [connsPhase, setConnsPhase] = useState<"loading" | "ready" | "error">("loading");
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<{ id: string; message: string } | null>(null);
  const [testingRowId, setTestingRowId] = useState<string | null>(null);
  const [rowTestError, setRowTestError] = useState<{ id: string; message: string } | null>(null);

  // ── Step 1 · Documents (#3 doc feeder) ──────────────────────────────────
  const [docEntities, setDocEntities] = useState<EntityDocument[]>([emptyDocEntity()]);
  const [docFields, setDocFields] = useState<DraftField[]>([emptyDraftField()]);

  // ── Step 2 · Map (#27) ──────────────────────────────────────────────────
  const [columns, setColumns] = useState<ColumnProfile[] | null>(null);
  const [rowCount, setRowCount] = useState<number | null>(null);
  const [suggestion, setSuggestion] = useState<MappingSuggestion | null>(null);
  const [mapping, setMapping] = useState<Record<string, Assignment | "">>({});
  const [mapPhase, setMapPhase] = useState<"idle" | "profiling" | "suggesting" | "ready" | "error">("idle");
  const [mapError, setMapError] = useState<string | null>(null);

  // ── Step 3 · Ground (#596/#597) — opt-in estimability declaration ───────
  const [groundEnabled, setGroundEnabled] = useState(false);
  const [metricDrafts, setMetricDrafts] = useState<Record<string, MetricDraft>>({});
  const [leverDrafts, setLeverDrafts] = useState<Record<string, LeverDraft>>({});

  // ── Step 4 · Build config (#28) ─────────────────────────────────────────
  const [k, setK] = useState<BuildK>("auto");
  const [stabilityThreshold, setStabilityThreshold] = useState(0.65);
  const [llmProvider, setLlmProvider] = useState<LlmProvider>("groq");
  const [weightSchemes] = useState<WeightScheme[]>(["head_count"]);

  // ── Step 4 · Build watch (#28) ──────────────────────────────────────────
  const [build, setBuild] = useState<BuildSummary | null>(null);
  const [events, setEvents] = useState<BuildEvent[]>([]);
  const [triggering, setTriggering] = useState(false);
  const [triggerError, setTriggerError] = useState<string | null>(null);

  // ── Step 5 · Evaluate (NEW) ─────────────────────────────────────────────
  const [evalPack, setEvalPack] = useState<PersonaPackDetail | null>(null);
  const [evalPhase, setEvalPhase] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [evalError, setEvalError] = useState<string | null>(null);
  const evalReqRef = useRef<string | null>(null);

  // ── Step 6 · Promote (#28) ──────────────────────────────────────────────
  const [promoting, setPromoting] = useState(false);
  const [promoted, setPromoted] = useState<PackSummary | null>(null);
  const [promoteError, setPromoteError] = useState<string | null>(null);

  const credFp = credFingerprint(conn);
  const testFp = testFingerprint(conn, sourceMode, tableFqn, sql);
  const testPassed = okFingerprint !== null && okFingerprint === testFp;
  const reusingSaved = connection !== null && connFingerprint === credFp;

  const sourceBody = (): { table_fqn?: string | null; sql?: string | null } =>
    sourceMode === "table" ? { table_fqn: tableFqn.trim() } : { sql: sql.trim() };

  // ── documents-source derived state (#3) ──────────────────────────────────
  const validDocEntities = docEntities.filter(
    (d) => d.entity_id.trim() && d.text.trim(),
  );
  const validDocFields = docFields.filter(
    (f): f is { name: string; type: MetricType; description: string } =>
      f.name.trim() !== "" && f.type !== "",
  );
  const dupFieldName =
    new Set(validDocFields.map((f) => f.name.trim())).size !== validDocFields.length;
  // Ready to extract: at least one entity with text, at least one well-formed
  // field, no duplicate field names, and no field colliding with the entity key.
  const docsValid =
    validDocEntities.length > 0 &&
    validDocFields.length > 0 &&
    !dupFieldName &&
    !validDocFields.some((f) => f.name.trim() === "entity_id");

  const buildExtractionRequest = () => ({
    documents: validDocEntities.map((d) => ({
      entity_id: d.entity_id.trim(),
      text: d.text.trim(),
    })),
    extraction_schema: {
      fields: validDocFields.map((f) => ({
        name: f.name.trim(),
        type: f.type,
        description: f.description.trim() || undefined,
      })) as ExtractionField[],
      entity_key: "entity_id",
    },
  });

  const clearBuild = useCallback(() => {
    setBuild(null);
    setEvents([]);
    setTriggerError(null);
    setEvalPack(null);
    setEvalPhase("idle");
    setEvalError(null);
    evalReqRef.current = null;
    setPromoted(null);
    setPromoteError(null);
  }, []);

  // ── Step 1 · load saved connections on mount (#304) ──────────────────────
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
    setOkFingerprint(null);
    setTestError(null);
  };

  const invalidateMappingAndBuild = () => {
    setColumns(null);
    setSuggestion(null);
    setMapping({});
    setMapPhase("idle");
    // Ground declarations name columns of THIS source — a new source resets
    // them to the default (off), so no stale declaration ever rides a build.
    setGroundEnabled(false);
    setMetricDrafts({});
    setLeverDrafts({});
    clearBuild();
  };

  const invalidateSource = () => {
    setOkFingerprint(null);
    invalidateMappingAndBuild();
  };

  const invalidateConnection = () => {
    invalidateMappingAndBuild();
  };

  // ── Step 1 · documents handlers (#3) ─────────────────────────────────────
  // Any edit to the documents or the schema invalidates the downstream extract
  // + mapping, exactly as editing a Snowflake source does.
  const onDocEntity = (i: number, patch: Partial<EntityDocument>) => {
    setDocEntities((prev) => prev.map((d, j) => (j === i ? { ...d, ...patch } : d)));
    invalidateMappingAndBuild();
  };
  const onAddDocEntity = () => setDocEntities((prev) => [...prev, emptyDocEntity()]);
  const onRemoveDocEntity = (i: number) => {
    setDocEntities((prev) => (prev.length <= 1 ? prev : prev.filter((_, j) => j !== i)));
    invalidateMappingAndBuild();
  };
  const onDocField = (i: number, patch: Partial<DraftField>) => {
    setDocFields((prev) => prev.map((f, j) => (j === i ? { ...f, ...patch } : f)));
    invalidateMappingAndBuild();
  };
  const onAddDocField = () => setDocFields((prev) => [...prev, emptyDraftField()]);
  const onRemoveDocField = (i: number) => {
    setDocFields((prev) => (prev.length <= 1 ? prev : prev.filter((_, j) => j !== i)));
    invalidateMappingAndBuild();
  };

  const onSourceKind = (kind: SourceKind) => {
    setSourceKind(kind);
    invalidateMappingAndBuild();
  };

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
    setConnFingerprint(credFingerprint(prefilled));
    setOkFingerprint(null);
    setTestError(null);
    invalidateConnection();
  };

  const handleNewConnection = () => {
    setConn(emptyConnForm());
    setConnection(null);
    setConnFingerprint(null);
    setOkFingerprint(null);
    setTestError(null);
    invalidateConnection();
  };

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

  const handleDeleteConnection = async (id: string) => {
    setDeleteError(null);
    setDeletingId(id);
    try {
      await deleteFeatureStore(id);
      setSavedConns((prev) => prev.filter((c) => c.id !== id));
      setConfirmDeleteId(null);
      if (connection?.id === id) handleNewConnection();
    } catch (e) {
      setDeleteError({ id, message: apiErrorMessage(e) });
    } finally {
      setDeletingId(null);
    }
  };

  const handleTestRow = async (id: string) => {
    setTestingRowId(id);
    setRowTestError(null);
    let caught: string | null = null;
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
      // A failed refresh leaves the prior status line in place.
    }
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
    let testedId: string | null = null;
    try {
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
        setSavedConns((prev) =>
          prev.some((c) => c.id === active!.id) ? prev : [active!, ...prev],
        );
        invalidateConnection();
      }
      testedId = active.id;
      await testFeatureStore(active.id); // 204 on success, throws on failure
      setOkFingerprint(testFp);
    } catch (e) {
      setTestError(apiErrorParts(e));
      setOkFingerprint(null);
    } finally {
      setTesting(false);
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

  // ── Step 2 · profile + suggest (#27, +#3 documents) ──────────────────────
  // Both sources converge on the SAME (columns, row_count) shape, so the only
  // difference is how the columns are produced: a Snowflake preview vs. a
  // document extraction. Mapping suggestion + assignment is identical after that.
  const loadMapping = useCallback(async () => {
    setMapError(null);
    setMapPhase("profiling");
    try {
      let cols: ColumnProfile[];
      let count: number;
      let sugg: MappingSuggestion;
      if (sourceKind === "documents") {
        const extracted = await extractDocuments(buildExtractionRequest());
        cols = extracted.columns;
        count = extracted.row_count;
        setColumns(cols);
        setRowCount(count);
        setMapPhase("suggesting");
        sugg = await suggestMappingForColumns(cols);
      } else {
        if (!connection) return;
        const preview = await previewFeatureStore(connection.id, sourceBody());
        cols = preview.columns;
        count = preview.row_count;
        setColumns(cols);
        setRowCount(count);
        setMapPhase("suggesting");
        sugg = await suggestMapping(connection.id, cols);
      }
      setSuggestion(sugg);
      const next: Record<string, Assignment | ""> = {};
      for (const col of cols) next[col.name] = "";
      for (const group of FEATURE_GROUPS) {
        for (const a of sugg[group]) next[a.column] = group;
      }
      setMapping(next);
      setMapPhase("ready");
    } catch (e) {
      setMapError(apiErrorMessage(e));
      setMapPhase("error");
    }
    // docEntities/docFields are deps so the documents request is never built
    // from a stale closure (the empty state captured when sourceKind flipped).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connection, sourceKind, docEntities, docFields]);

  useEffect(() => {
    const sourceReady = sourceKind === "documents" ? docsValid : connection !== null;
    if (step === 2 && sourceReady && columns === null && mapPhase === "idle") {
      void loadMapping();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, connection, sourceKind, docsValid, columns, mapPhase, loadMapping]);

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

  const allResolved =
    columns !== null && columns.length > 0 && columns.every((c) => mapping[c.name] && mapping[c.name] !== "");

  // ── Step 3 · Ground derived state (#596/#597) ────────────────────────────
  const metricCandidateCols = useMemo(
    () => (columns ?? []).filter((c) => isNumericDtype(c.dtype)),
    [columns],
  );
  const leverCandidateCols = useMemo(
    () => (columns ?? []).filter((c) => isLeverCandidate(c)),
    [columns],
  );
  // Selections are read THROUGH the candidate lists, so a draft for a column
  // that no longer exists (or no longer qualifies) can never ride the payload.
  const selectedMetricCols = metricCandidateCols.filter((c) => metricDrafts[c.name]?.selected);
  const selectedLeverCols = leverCandidateCols.filter((c) => leverDrafts[c.name]?.selected);
  const unguardedMetricCount = selectedMetricCols.filter(
    (c) => !(metricDrafts[c.name]?.prePeriodColumn ?? "").trim(),
  ).length;

  const onMetricDraft = (col: string, patch: Partial<MetricDraft>) =>
    setMetricDrafts((prev) => ({
      ...prev,
      [col]: { ...(prev[col] ?? emptyMetricDraft()), ...patch },
    }));
  const onLeverDraft = (col: string, patch: Partial<LeverDraft>) =>
    setLeverDrafts((prev) => ({
      ...prev,
      [col]: { ...(prev[col] ?? emptyLeverDraft()), ...patch },
    }));

  // ── Step 4 · start build (#28) ───────────────────────────────────────────
  const handleStartBuild = async () => {
    if (!connection) return;
    setTriggerError(null);
    setTriggering(true);
    try {
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
      // #596/#597 — the Ground step's declaration rides the build only when the
      // customer opted in; with the toggle off the payload is byte-identical to
      // the pre-Ground wizard (no estimability key at all).
      if (groundEnabled) {
        const metric_registry: MetricRegistryEntry[] = selectedMetricCols.map((c) => {
          const d = metricDrafts[c.name] ?? emptyMetricDraft();
          const synonyms = splitSynonyms(d.synonyms);
          return {
            column: c.name,
            ...(d.displayName.trim() ? { display_name: d.displayName.trim() } : {}),
            ...(d.semanticType ? { semantic_type: d.semanticType } : {}),
            ...(d.description.trim() ? { description: d.description.trim() } : {}),
            ...(synonyms.length > 0 ? { synonyms } : {}),
            ...(d.prePeriodColumn.trim() ? { pre_period_column: d.prePeriodColumn.trim() } : {}),
          };
        });
        const lever_registry: LeverRegistryEntry[] = selectedLeverCols.map((c) => {
          const d = leverDrafts[c.name] ?? emptyLeverDraft();
          return {
            column: c.name,
            ...(d.displayName.trim() ? { display_name: d.displayName.trim() } : {}),
            ...(d.description.trim() ? { description: d.description.trim() } : {}),
          };
        });
        const estimability: EstimabilityBuildConfig = {
          enabled: true,
          ...(metric_registry.length > 0 ? { metric_registry } : {}),
          ...(lever_registry.length > 0 ? { lever_registry } : {}),
          nc_diagnostics: true,
        };
        config.estimability = estimability;
      }
      const summary = await createPersonaBuild(config);
      setBuild(summary);
      setEvents([]);
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

  // ── Step 4 · watch poll (#28) ────────────────────────────────────────────
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
        // Transient read failure — the next beat retries.
      }
    };
    void tick(); // immediate first beat so the watch isn't blank for 2.5s
    const interval = setInterval(tick, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [watchId]);

  // ── Step 5 · load the unpromoted pack for evaluation (NEW) ───────────────
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
      step === 5 &&
      build?.status === "complete" &&
      packVersion &&
      evalPhase === "idle"
    ) {
      void loadEvaluation(packVersion);
    }
  }, [step, build?.status, packVersion, evalPhase, loadEvaluation]);

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
        // Documents: ready once there's ≥1 entity with text + a valid schema.
        // Feature store: a connection test must have succeeded for the values.
        return sourceKind === "documents" ? docsValid : testPassed;
      case 2:
        return allResolved; // every column assigned or explicitly ignored
      case 3:
        // Ground is opt-in: skipping is always allowed. Opted-in, a declaration
        // needs at least one metric AND one lever — UNGUARDED metrics may pass
        // (the guard review shows that state honestly; it never blocks).
        return !groundEnabled || (selectedMetricCols.length > 0 && selectedLeverCols.length > 0);
      case 4:
        return build?.status === "complete"; // Continue→Evaluate only when done
      case 5:
        return evalPhase === "ready" && !!evalPack && evalPack.version === build?.pack_version;
      case 6:
        return false; // terminal — Promote has no Next
      default:
        return false;
    }
  };

  const goBack = () => setStep((s) => Math.max(1, s - 1));
  const goNext = () => {
    if (canContinue()) setStep((s) => Math.min(LAST_STEP, s + 1));
  };

  // Documents are preview-only: step 4 (extraction + mapping summary) is the
  // terminal state. There's no build to complete, so don't offer a dead Next.
  const documentsTerminal = sourceKind === "documents" && step === 4;
  const showNext = step !== LAST_STEP && !documentsTerminal;

  const nextLabel =
    step === 4 ? "Continue → Evaluate" : step === 5 ? "These look right → Promote" : "Next →";

  // The compact Ground manifest block rides a right-hand rail while grounding
  // is being configured (step 3) and while the build that would carry it is
  // configured/watched (step 4, feature-store path only — the documents path
  // has no build for a declaration to ride).
  const showGroundRail = (step === 3 || step === 4) && sourceKind === "feature_store";

  return (
    <AppShellV2 activeNav="personas" title="New persona pack" surface="console">
      <div className="rconsole">
        <style>{RCONSOLE_CSS}</style>

        <main style={{ fontFamily: FONT_SANS, color: C.text }}>
          {/* Page strip — the dark Console header band */}
          <header className="pagehead">
            <h1>New persona pack</h1>
            <span className="desig" style={TNUM}>
              STEP {String(step).padStart(2, "0")} / {String(LAST_STEP).padStart(2, "0")} ·{" "}
              {STEPS[step - 1].label.toUpperCase()}
            </span>
            <span className="stamp">
              GENERATED FROM YOUR DATA — VERSIONED, EVALUATE-THEN-PROMOTE
            </span>
          </header>

          <Stepper current={step} />

          {/* Step body. Each step renders inside the form zone. On the Ground
              step (and the Build step that carries its declaration) the form
              column pairs with a compact manifest rail (§7.4 wizard posture). */}
          <div className="bodywrap">
            <div className={showGroundRail ? "groundgrid" : undefined} style={showGroundRail ? undefined : { maxWidth: 760 }}>
            <div style={{ minWidth: 0, maxWidth: 760 }}>
            {step === 1 && (
              <>
                <SourceKindToggle kind={sourceKind} onKind={onSourceKind} />
                {sourceKind === "documents" ? (
                  <StepDocuments
                    entities={docEntities}
                    fields={docFields}
                    docsValid={docsValid}
                    dupFieldName={dupFieldName}
                    validEntityCount={validDocEntities.length}
                    validFieldCount={validDocFields.length}
                    onEntity={onDocEntity}
                    onAddEntity={onAddDocEntity}
                    onRemoveEntity={onRemoveDocEntity}
                    onField={onDocField}
                    onAddField={onAddDocField}
                    onRemoveField={onRemoveDocField}
                  />
                ) : (
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
              </>
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
              <StepGround
                sourceKind={sourceKind}
                columns={columns}
                enabled={groundEnabled}
                onEnabled={setGroundEnabled}
                metricCandidates={metricCandidateCols}
                leverCandidates={leverCandidateCols}
                metricDrafts={metricDrafts}
                leverDrafts={leverDrafts}
                onMetricDraft={onMetricDraft}
                onLeverDraft={onLeverDraft}
                selectedMetricCols={selectedMetricCols}
                selectedLeverCols={selectedLeverCols}
                unguardedMetricCount={unguardedMetricCount}
              />
            )}

            {step === 4 && (
              <StepBuild
                connection={connection}
                sourceKind={sourceKind}
                sourceMode={sourceMode}
                tableFqn={tableFqn}
                sql={sql}
                columns={columns}
                rowCount={rowCount}
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
                build={build}
                events={events}
                onRetry={clearBuild}
                onReconfigure={clearBuild}
              />
            )}

            {step === 5 && (
              <StepEvaluate
                build={build}
                phase={evalPhase}
                error={evalError}
                pack={evalPack}
                onRerun={() => {
                  clearBuild();
                  setStep(4);
                }}
                onRetry={() => {
                  setEvalPhase("idle");
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

            {/* ── Back / Next nav ────────────────────────────────────────── */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginTop: 32,
                paddingTop: 16,
                borderTop: `1px solid ${C.line}`,
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

            {showGroundRail && (
              <GroundRail
                enabled={groundEnabled}
                metricCount={selectedMetricCols.length}
                leverCount={selectedLeverCols.length}
                unguardedCount={unguardedMetricCount}
              />
            )}
            </div>
          </div>
        </main>
      </div>
    </AppShellV2>
  );
}

// ── Stepper — dark Console stepper ──────────────────────────────────────────
function Stepper({ current }: { current: number }) {
  return (
    <div className="stepper">
      {STEPS.map((s) => {
        const active = s.id === current;
        const done = s.id < current;
        return (
          <div
            key={s.id}
            className={`step${active ? " active" : ""}${done ? " done" : ""}`}
          >
            <div className="num" style={TNUM}>
              {String(s.id).padStart(2, "0")}
              {done ? " ✓" : ""}
            </div>
            <div className="lbl">{s.label}</div>
          </div>
        );
      })}
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Step 1 · Connect (#26)
// ════════════════════════════════════════════════════════════════════════════
// ── #3 doc feeder · source-kind toggle ──────────────────────────────────────
function SourceKindToggle({
  kind,
  onKind,
}: {
  kind: SourceKind;
  onKind: (k: SourceKind) => void;
}) {
  const opts: { id: SourceKind; label: string; hint: string }[] = [
    {
      id: "feature_store",
      label: "Feature store",
      hint: "A Snowflake table or query — one row per user or account.",
    },
    {
      id: "documents",
      label: "Documents",
      hint: "Interviews, tickets, notes — extracted into feature rows.",
    },
  ];
  return (
    <section style={{ maxWidth: 620, marginBottom: 4 }}>
      <div style={sectionLabelStyle}>01 · Source kind</div>
      <div style={{ ...fieldStyle, display: "flex", gap: 8 }}>
        {opts.map((o) => {
          const active = kind === o.id;
          return (
            <button
              key={o.id}
              type="button"
              onClick={() => onKind(o.id)}
              aria-pressed={active}
              style={{
                ...secondaryBtnStyle,
                flex: 1,
                textAlign: "left",
                background: active ? C.panelRaised : "transparent",
                color: active ? C.textHi : C.text,
                borderColor: active ? C.textMut : C.line,
              }}
            >
              <div style={{ fontWeight: 600, fontSize: 13 }}>{o.label}</div>
              <div style={{ ...hintStyle, marginTop: 4 }}>{o.hint}</div>
            </button>
          );
        })}
      </div>
    </section>
  );
}

// ── #3 doc feeder · documents + extraction-schema entry ──────────────────────
function StepDocuments({
  entities,
  fields,
  docsValid,
  dupFieldName,
  validEntityCount,
  validFieldCount,
  onEntity,
  onAddEntity,
  onRemoveEntity,
  onField,
  onAddField,
  onRemoveField,
}: {
  entities: EntityDocument[];
  fields: DraftField[];
  docsValid: boolean;
  dupFieldName: boolean;
  validEntityCount: number;
  validFieldCount: number;
  onEntity: (i: number, patch: Partial<EntityDocument>) => void;
  onAddEntity: () => void;
  onRemoveEntity: (i: number) => void;
  onField: (i: number, patch: Partial<DraftField>) => void;
  onAddField: () => void;
  onRemoveField: (i: number) => void;
}) {
  const addBtn: React.CSSProperties = {
    ...secondaryBtnStyle,
    fontFamily: FONT_MONO,
    fontSize: 11,
    letterSpacing: "0.06em",
    padding: "6px 12px",
    marginTop: 12,
  };
  const removeBtn: React.CSSProperties = {
    ...secondaryBtnStyle,
    fontFamily: FONT_MONO,
    fontSize: 11,
    padding: "4px 9px",
    color: C.textMut,
  };

  return (
    <div style={{ maxWidth: 620 }}>
      {/* ── 02 · Documents ───────────────────────────────────────────────── */}
      <section style={sectionStyle}>
        <div style={sectionLabelStyle}>02 · Documents</div>
        <div style={hintStyle}>
          One entry per population member. The entity id labels the resulting
          feature row; the text is everything known about them (interview notes,
          tickets, survey answers). Empty entries are ignored.
        </div>
        {entities.map((d, i) => (
          <div key={i} style={fieldStyle}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <input
                aria-label={`Entity id ${i + 1}`}
                value={d.entity_id}
                onChange={(e) => onEntity(i, { entity_id: e.target.value })}
                placeholder="entity id (e.g. user_8123)"
                style={{ ...monoInputStyle, flex: 1 }}
              />
              {entities.length > 1 && (
                <button type="button" style={removeBtn} onClick={() => onRemoveEntity(i)}>
                  REMOVE
                </button>
              )}
            </div>
            <textarea
              aria-label={`Documents for entity ${i + 1}`}
              value={d.text}
              onChange={(e) => onEntity(i, { text: e.target.value })}
              placeholder="Paste this entity's documents — interview notes, support tickets, survey answers…"
              style={{ ...textareaStyle, marginTop: 8, fontFamily: FONT_SANS, fontSize: 14 }}
            />
          </div>
        ))}
        <button type="button" style={addBtn} onClick={onAddEntity}>
          + ADD ENTITY
        </button>
      </section>

      {/* ── 03 · Extraction schema ───────────────────────────────────────── */}
      <section style={sectionStyle}>
        <div style={sectionLabelStyle}>03 · Extraction schema</div>
        <div style={hintStyle}>
          The closed set of features to pull from each entity&apos;s documents.
          Extraction is extractive, never generative — a field not evidenced in
          the text is left null, never guessed. Each field declares one metric
          type so the column re-enters the existing build pipeline.
        </div>
        {fields.map((f, i) => (
          <div key={i} style={{ ...fieldStyle, display: "grid", gap: 8 }}>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                aria-label={`Field name ${i + 1}`}
                value={f.name}
                onChange={(e) => onField(i, { name: e.target.value })}
                placeholder="field name (e.g. orders_count)"
                style={{ ...monoInputStyle, flex: 2 }}
              />
              <select
                aria-label={`Field type ${i + 1}`}
                value={f.type}
                onChange={(e) => onField(i, { type: e.target.value as MetricType | "" })}
                style={{ ...selectStyle, flex: 1 }}
              >
                <option value="">type…</option>
                {METRIC_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              {fields.length > 1 && (
                <button type="button" style={removeBtn} onClick={() => onRemoveField(i)}>
                  ×
                </button>
              )}
            </div>
            <input
              aria-label={`Field description ${i + 1}`}
              value={f.description}
              onChange={(e) => onField(i, { description: e.target.value })}
              placeholder="what evidence to look for (optional)"
              style={inputStyle}
            />
            {f.type && (
              <div style={{ ...railCaptionStyle, color: C.textMut }}>
                {f.type.toUpperCase()} — {METRIC_TYPE_HINTS[f.type]}
              </div>
            )}
          </div>
        ))}
        <button type="button" style={addBtn} onClick={onAddField}>
          + ADD FIELD
        </button>
        {dupFieldName && (
          <div role="alert" style={{ ...railAlertStyle, marginTop: 12 }}>
            Field names must be unique — two fields share a name.
          </div>
        )}
      </section>

      {/* ── readiness — honest status, no spinner (§8.6) ─────────────────── */}
      <section style={sectionStyle}>
        <div style={{ ...statusLineStyle, color: docsValid ? C.textHi : C.textMut }}>
          {docsValid
            ? `READY — ${validEntityCount} ENTIT${validEntityCount === 1 ? "Y" : "IES"} · ${validFieldCount} FIELD${validFieldCount === 1 ? "" : "S"} → CONTINUE TO MAP`
            : "ADD AT LEAST ONE ENTITY WITH TEXT AND ONE TYPED FIELD TO CONTINUE"}
        </div>
      </section>
    </div>
  );
}

// ── #3 doc feeder · build step notice (preview-only, build deferred) ─────────
function DocumentsBuildNotice({
  columns,
  rowCount,
  mapping,
}: {
  columns: ColumnProfile[] | null;
  rowCount: number | null;
  mapping: Record<string, Assignment | "">;
}) {
  const mapped = (columns ?? []).filter(
    (c) => mapping[c.name] && mapping[c.name] !== "ignore",
  );
  const ignored = (columns ?? []).filter((c) => mapping[c.name] === "ignore");
  return (
    <div style={{ maxWidth: 680 }}>
      <section>
        <div style={sectionLabelStyle}>Extraction complete</div>
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
            ["Source", "DOCUMENTS"],
            ["Rows extracted", rowCount === null ? "—" : String(rowCount)],
            ["Columns mapped", String(mapped.length)],
            ["Columns ignored", String(ignored.length)],
          ].map(([k2, v]) => (
            <Fragment key={k2}>
              <dt style={{ ...railCaptionStyle, color: C.textMut }}>{k2}</dt>
              <dd style={{ margin: 0, ...statusLineStyle }}>{v}</dd>
            </Fragment>
          ))}
        </dl>
      </section>

      <section style={sectionStyle}>
        <div style={okBannerStyle}>
          Your documents were extracted into feature rows and mapped to the
          canonical groups using the live extractor — the #3 path works
          end-to-end up to here. Persisting a persona pack from a documents
          source isn&apos;t enabled yet: it needs the persona-build store to
          accept a non-connection source (a small migration) plus the
          persona-pipeline binding. Those are tracked follow-ups. Until then this
          flow validates extraction and mapping, not the final build — this is
          the end of the documents preview. Use Back to adjust the documents or
          schema and re-extract.
        </div>
      </section>
    </div>
  );
}

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

  const dupDesignators = duplicateDesignators(savedConns);

  const collapsed =
    reusingSaved && selectedConn !== null && savedConns.some((c) => c.id === selectedConn.id);

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

      {connsPhase === "loading" && (
        <div style={{ ...statusLineStyle, color: C.textMut, marginBottom: 4 }}>
          LOADING SAVED CONNECTIONS…
        </div>
      )}

      {collapsed && selectedConn && (
        <SavedConnectionSummary
          conn={selectedConn}
          designator={dupDesignators[selectedConn.id] ?? ""}
          focusOnMount={justPickedRef.current}
          onFocusConsumed={() => {
            justPickedRef.current = false;
          }}
          onUseDifferent={onNewConnection}
          onEditAsNew={onEditAsNew}
        />
      )}

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
                  background: active ? C.panelRaised : "transparent",
                  color: active ? C.textHi : C.text,
                  borderColor: active ? C.line : C.line,
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
          {testing && <span style={{ ...statusLineStyle, color: C.textMut }}>TESTING · CONNECTING…</span>}
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
  const [activeIndex, setActiveIndex] = useState(-1);

  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const filterRef = useRef<HTMLInputElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const optionRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const sorted = useMemo(() => sortConnsForPicker(conns), [conns]);
  const filtered = useMemo(
    () => sorted.filter((c) => connMatchesFilter(c, filter)),
    [sorted, filter],
  );
  optionRefs.current = [];

  const selectedConn = selectedConnId ? conns.find((c) => c.id === selectedConnId) ?? null : null;
  const triggerLabel = selectedConn
    ? `${selectedConn.name}${dupDesignators[selectedConn.id] ?? ""} · ${conns.length} saved`
    : `Choose a saved connection (${conns.length})`;

  const closeAndRefocus = useCallback(() => {
    setOpen(false);
    setActiveIndex(-1);
    triggerRef.current?.focus();
  }, []);

  const openPanel = useCallback(() => {
    setOpen(true);
    setActiveIndex(-1);
    requestAnimationFrame(() => filterRef.current?.focus());
  }, []);

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

  useEffect(() => {
    if (!open || activeIndex < 0) return;
    optionRefs.current[activeIndex]?.focus();
  }, [open, activeIndex, filtered.length]);

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

  const onTriggerKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      openPanel();
    }
  };

  const onPanelKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape") {
      e.preventDefault();
      closeAndRefocus();
    }
  };

  const onFilterKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      moveActive(1);
    }
  };

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
          <span aria-hidden="true" style={{ fontFamily: FONT_MONO, fontSize: 11, color: C.textMut }}>
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
              border: `1px solid ${C.line}`,
              borderRadius: 4,
              background: C.panel,
              overflow: "hidden",
            }}
          >
            <div style={{ padding: 8, borderBottom: `1px solid ${C.line}` }}>
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
  const rowActionStyle: React.CSSProperties = {
    background: "transparent",
    border: `1px solid ${C.line}`,
    borderRadius: 4,
    padding: "2px 8px",
    fontFamily: FONT_MONO,
    fontSize: 10,
    letterSpacing: "0.06em",
    textTransform: "uppercase",
    color: C.textMut,
    cursor: "pointer",
    whiteSpace: "nowrap",
  };

  const identity = connectionIdentity(conn);
  const subline = connectionSubline(conn);
  const healthLine = testing ? "TESTING…" : connectionHealthLine(conn);

  const cancelRef = useRef<HTMLButtonElement | null>(null);
  const deleteBtnRef = useRef<HTMLButtonElement | null>(null);
  const wasConfirming = useRef(false);
  useEffect(() => {
    if (confirmingDelete) {
      cancelRef.current?.focus();
    } else if (wasConfirming.current) {
      deleteBtnRef.current?.focus();
    }
    wasConfirming.current = confirmingDelete;
  }, [confirmingDelete]);

  if (confirmingDelete) {
    return (
      <div
        style={{
          borderBottom: `1px solid ${C.line}`,
          ...railAlertStyle,
          borderTopWidth: 0,
          borderLeftWidth: 0,
          borderRightWidth: 0,
          borderRadius: 0,
        }}
        role="alertdialog"
        aria-label={`Confirm delete ${conn.name}`}
      >
        <div style={{ fontSize: 13, color: C.text, lineHeight: 1.45 }}>
          Delete saved connection <strong style={{ color: C.textHi }}>{conn.name}</strong>
          {designator ? <span style={railCaptionStyle}>{designator.trim()}</span> : null}? Existing
          persona builds keep their records; future builds can&apos;t use this credential.
        </div>
        {deleteError && (
          <div style={{ ...railCaptionStyle, marginTop: 6, color: C.text }}>
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
              color: C.textHi,
              borderColor: C.textHi,
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
        borderBottom: `1px solid ${C.line}`,
        background: selected ? C.panelRaised : "transparent",
        borderLeft: `2px solid ${selected ? C.signalDim : "transparent"}`,
      }}
    >
      <button
        type="button"
        onClick={onSelect}
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
          <span style={{ fontSize: 13.5, fontWeight: 600, color: C.textHi }}>
            {identity}
            {designator ? <span style={{ color: C.textMut }}>{designator}</span> : null}
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
        <div style={{ ...railCaptionStyle, textTransform: "uppercase" }}>{healthLine}</div>
        {testError && (
          <div style={{ ...railCaptionStyle, color: C.text }}>
            TEST FAILED · {testError.toUpperCase()}
          </div>
        )}
      </button>
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
  const headingRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (!focusOnMount) return;
    headingRef.current?.focus();
    onFocusConsumed?.();
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
          background: C.panelRaised,
          border: `1px solid ${C.line}`,
          borderLeft: `2px solid ${C.signalDim}`,
          borderRadius: 4,
          padding: "12px 14px",
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: C.textHi }}>
            {conn.name}
            {designator ? <span style={{ color: C.textMut }}>{designator}</span> : null}
          </span>
          <Chip>{conn.kind.toUpperCase()}</Chip>
          <Chip>REUSING — NO PASSWORD NEEDED</Chip>
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
                  color: C.textMut,
                }}
              >
                {dt}
              </dt>
              <dd
                style={{
                  margin: 0,
                  fontFamily: FONT_MONO,
                  fontSize: 12,
                  color: C.textHi,
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
  if (phase === "profiling" || phase === "suggesting" || phase === "idle") {
    return (
      <div style={{ ...statusLineStyle, color: C.textMut, marginTop: 8 }}>
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
        <strong style={{ color: C.text }}>ignore</strong>. Suggestions are the model&apos;s best guess — the
        confidence chip tells you how sure it is. Continue unlocks when nothing is
        unresolved.
      </div>

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
        <div style={{ ...railCaptionStyle, marginTop: 16, color: C.text }}>
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
        // Unresolved rows carry an alert hairline (border-only) so the eye lands
        // on what still needs a decision (§4.3).
        border: unresolved ? `1px solid var(--alert)` : "none",
        borderRadius: unresolved ? 4 : 0,
        padding: unresolved ? "8px 10px" : 0,
        background: unresolved ? C.panelRecessed : "transparent",
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
          <span style={{ fontFamily: FONT_MONO, fontSize: 13, color: C.textHi }}>{col.name}</span>
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
// Step 3 · Ground (#596/#597) — opt-in estimability declaration.
// Metrics first (deliberately before levers), then levers, then a read-only
// guard review. Toggle off (the default) = the build behaves exactly as today.
// ════════════════════════════════════════════════════════════════════════════

// Quiet mono row-action toggle (§7.7 register — matches REMOVE / + ADD ENTITY).
const groundRowActionStyle: React.CSSProperties = {
  ...secondaryBtnStyle,
  fontFamily: FONT_MONO,
  fontSize: 10,
  letterSpacing: "0.06em",
  textTransform: "uppercase",
  padding: "4px 9px",
  color: C.textMut,
  whiteSpace: "nowrap",
};

// The §7.7 note anatomy in the dark-console register: hairline rule border,
// recessed fill, message in ink — no icon, no pill, no semantic color.
const groundNoteStyle: React.CSSProperties = {
  padding: "10px 12px",
  background: C.panelRecessed,
  border: `1px solid ${C.line}`,
  borderRadius: 4,
  color: C.text,
  fontSize: 12.5,
  lineHeight: 1.5,
  overflowWrap: "break-word",
};

function StepGround({
  sourceKind,
  columns,
  enabled,
  onEnabled,
  metricCandidates,
  leverCandidates,
  metricDrafts,
  leverDrafts,
  onMetricDraft,
  onLeverDraft,
  selectedMetricCols,
  selectedLeverCols,
  unguardedMetricCount,
}: {
  sourceKind: SourceKind;
  columns: ColumnProfile[] | null;
  enabled: boolean;
  onEnabled: (v: boolean) => void;
  metricCandidates: ColumnProfile[];
  leverCandidates: ColumnProfile[];
  metricDrafts: Record<string, MetricDraft>;
  leverDrafts: Record<string, LeverDraft>;
  onMetricDraft: (col: string, patch: Partial<MetricDraft>) => void;
  onLeverDraft: (col: string, patch: Partial<LeverDraft>) => void;
  selectedMetricCols: ColumnProfile[];
  selectedLeverCols: ColumnProfile[];
  unguardedMetricCount: number;
}) {
  // Documents packs are preview-only — there is no build for a declaration to
  // ride. Say so and let Next pass (Ground stays off for this source kind).
  if (sourceKind === "documents") {
    return (
      <div style={{ maxWidth: 680 }}>
        <div style={sectionLabelStyle}>Grounding</div>
        <div style={{ ...groundNoteStyle, marginTop: 12 }}>
          Grounding applies to warehouse builds only. Documents packs are
          preview-only — there is no build for a metric or lever declaration to
          ride. Continue to the extraction summary.
        </div>
      </div>
    );
  }
  if (!columns || columns.length === 0) {
    return (
      <div style={{ ...statusLineStyle, color: C.textMut }}>
        NO COLUMNS PROFILED — GO BACK TO MAP.
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 680 }}>
      {/* ── master toggle — opt-in, off by default ───────────────────────── */}
      <section>
        <div style={sectionLabelStyle}>Grounding (optional)</div>
        <div style={{ ...fieldStyle, display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <button
            type="button"
            aria-pressed={enabled}
            onClick={() => onEnabled(!enabled)}
            style={{
              ...secondaryBtnStyle,
              background: enabled ? C.panelRaised : "transparent",
              color: enabled ? C.textHi : C.text,
              borderColor: enabled ? C.textMut : C.line,
            }}
          >
            Declare metrics &amp; levers for grounding
          </button>
          <span style={{ ...statusLineStyle, color: enabled ? C.textHi : C.textMut }}>
            {enabled ? "ON" : "OFF — BUILD RUNS UNGROUNDED"}
          </span>
        </div>
        <div style={hintStyle}>
          Off by default — skip straight to Build and it behaves exactly as
          today. Opt in to declare the outcome metrics you care about and the
          binary exposure levers that might move them; the build then
          precomputes grounded, guard-checked effect candidates for the lever
          cards.
        </div>
      </section>

      {enabled && (
        <>
          {/* ── 01 · Outcome metrics — deliberately before levers ─────────── */}
          <section style={sectionStyle}>
            <div style={sectionLabelStyle}>01 · Outcome metrics</div>
            <div style={hintStyle}>
              Which numeric columns are outcomes worth predicting? Declare a
              pre-period column (the same reading captured before exposure)
              wherever one exists — it compiles into a negative control that
              guards the estimate.
            </div>
            {metricCandidates.length === 0 ? (
              <div style={{ ...statusLineStyle, color: C.textMut, marginTop: 12 }}>
                NO NUMERIC COLUMNS IN THIS SOURCE — NOTHING TO DECLARE AS A METRIC.
              </div>
            ) : (
              metricCandidates.map((col, i) => (
                <MetricGroundRow
                  key={col.name}
                  idx={i}
                  col={col}
                  draft={metricDrafts[col.name] ?? emptyMetricDraft()}
                  prePeriodOptions={metricCandidates.filter((c) => c.name !== col.name)}
                  onDraft={(patch) => onMetricDraft(col.name, patch)}
                />
              ))
            )}
          </section>

          {/* ── 02 · Levers ───────────────────────────────────────────────── */}
          <section style={sectionStyle}>
            <div style={sectionLabelStyle}>02 · Levers</div>
            <div style={hintStyle}>
              Levers must be binary exposure flags — 1 = the user had the
              feature, 0 = they did not. Only bool or two-valued columns
              qualify.
            </div>
            {leverCandidates.length === 0 ? (
              <div style={{ ...statusLineStyle, color: C.textMut, marginTop: 12 }}>
                NO BINARY COLUMNS IN THIS SOURCE — NOTHING TO DECLARE AS A LEVER.
              </div>
            ) : (
              leverCandidates.map((col, i) => (
                <LeverGroundRow
                  key={col.name}
                  idx={i}
                  col={col}
                  draft={leverDrafts[col.name] ?? emptyLeverDraft()}
                  onDraft={(patch) => onLeverDraft(col.name, patch)}
                />
              ))
            )}
          </section>

          {/* ── 03 · Guard review — read-only summary ─────────────────────── */}
          <section style={sectionStyle}>
            <div style={sectionLabelStyle}>03 · Guard review</div>
            {selectedMetricCols.length === 0 && selectedLeverCols.length === 0 ? (
              <div style={{ ...statusLineStyle, color: C.textMut, marginTop: 12 }}>
                NOTHING DECLARED YET — SELECT AT LEAST ONE METRIC AND ONE LEVER.
              </div>
            ) : (
              <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 8 }}>
                {selectedMetricCols.map((col) => {
                  const pre = (metricDrafts[col.name]?.prePeriodColumn ?? "").trim();
                  return (
                    <GuardReviewRow
                      key={`m-${col.name}`}
                      word={pre ? "GUARDED" : "UNGUARDED"}
                      glyph={pre ? "✓" : "·"}
                      glyphColor={pre ? C.success : C.textMut}
                      textColor={pre ? C.text : C.textMut}
                    >
                      <span style={{ fontFamily: FONT_MONO, color: C.textHi }}>{col.name}</span>{" "}
                      {pre
                        ? `— pre-period: ${pre}`
                        : "— will build unverified — no negative control declared"}
                    </GuardReviewRow>
                  );
                })}
                {selectedLeverCols.map((col) => (
                  <GuardReviewRow
                    key={`l-${col.name}`}
                    word="DECLARED"
                    glyph="✓"
                    glyphColor={C.success}
                    textColor={C.text}
                  >
                    <span style={{ fontFamily: FONT_MONO, color: C.textHi }}>{col.name}</span>
                    {(leverDrafts[col.name]?.displayName ?? "").trim()
                      ? ` — ${leverDrafts[col.name]!.displayName.trim()}`
                      : ""}
                  </GuardReviewRow>
                ))}
              </div>
            )}
            {unguardedMetricCount > 0 && (
              <div style={{ ...railCaptionStyle, marginTop: 10, textTransform: "uppercase" }}>
                {unguardedMetricCount} METRIC{unguardedMetricCount === 1 ? "" : "S"} UNGUARDED —
                ALLOWED, BUT THE ESTIMATES CARRY NO NEGATIVE CONTROL.
              </div>
            )}
            <div style={{ ...groundNoteStyle, marginTop: 14 }}>
              Negative controls are compiled from pre-period links; explicit
              review happens on the lever card after the build.
            </div>
          </section>
        </>
      )}
    </div>
  );
}

// One read-only guard-review row: mono word first (the PRESENT/MISSING idiom —
// the wording + glyph carry the state, never color alone, §4.3/§7.8).
function GuardReviewRow({
  word,
  glyph,
  glyphColor,
  textColor,
  children,
}: {
  word: string;
  glyph: string;
  glyphColor: string;
  textColor: string;
  children: React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
      <span aria-hidden="true" style={{ fontFamily: FONT_MONO, fontSize: 12, color: glyphColor, width: 10, flexShrink: 0, textAlign: "center" }}>
        {glyph}
      </span>
      <span
        style={{
          fontFamily: FONT_MONO,
          fontSize: 11,
          letterSpacing: "0.06em",
          color: C.textHi,
          width: 92,
          flexShrink: 0,
          ...TNUM,
        }}
      >
        {word}
      </span>
      <span style={{ fontSize: 12.5, lineHeight: 1.45, color: textColor, minWidth: 0, overflowWrap: "break-word" }}>
        {children}
      </span>
    </div>
  );
}

// ── 01 · one metric candidate row ───────────────────────────────────────────
function MetricGroundRow({
  idx,
  col,
  draft,
  prePeriodOptions,
  onDraft,
}: {
  idx: number;
  col: ColumnProfile;
  draft: MetricDraft;
  prePeriodOptions: ColumnProfile[];
  onDraft: (patch: Partial<MetricDraft>) => void;
}) {
  const id = (suffix: string) => `ground-metric-${idx}-${suffix}`;
  return (
    <div
      style={{
        ...fieldStyle,
        border: `1px solid ${C.line}`,
        borderRadius: 4,
        padding: "10px 12px",
        background: draft.selected ? C.panel : "transparent",
      }}
    >
      <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
        <span style={{ fontFamily: FONT_MONO, fontSize: 13, color: C.textHi }}>{col.name}</span>
        <Chip>{col.dtype}</Chip>
        {draft.selected && <Chip>OUTCOME METRIC</Chip>}
        <span style={{ marginLeft: "auto" }}>
          <button
            type="button"
            aria-pressed={draft.selected}
            aria-label={`${draft.selected ? "Remove" : "Mark"} ${col.name} as an outcome metric`}
            onClick={() => onDraft({ selected: !draft.selected })}
            style={groundRowActionStyle}
          >
            {draft.selected ? "REMOVE" : "+ MARK AS METRIC"}
          </button>
        </span>
      </div>

      {draft.selected && (
        <div style={{ marginTop: 12, display: "grid", gap: 12 }}>
          <div style={fieldRowStyle}>
            <div>
              <label htmlFor={id("dname")} style={sublabelStyle}>
                Display name
              </label>
              <input
                id={id("dname")}
                value={draft.displayName}
                onChange={(e) => onDraft({ displayName: e.target.value })}
                placeholder="e.g. Weekly watch hours"
                style={inputStyle}
              />
            </div>
            <div>
              <label htmlFor={id("stype")} style={sublabelStyle}>
                Semantic type
              </label>
              <select
                id={id("stype")}
                value={draft.semanticType}
                onChange={(e) =>
                  onDraft({ semanticType: e.target.value as MetricDraft["semanticType"] })
                }
                style={selectStyle}
              >
                <option value="">— choose —</option>
                {SEMANTIC_TYPES.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label htmlFor={id("desc")} style={sublabelStyle}>
              Description
            </label>
            <input
              id={id("desc")}
              value={draft.description}
              onChange={(e) => onDraft({ description: e.target.value })}
              placeholder="what this metric measures (optional)"
              style={inputStyle}
            />
          </div>
          <div style={fieldRowStyle}>
            <div>
              <label htmlFor={id("syn")} style={sublabelStyle}>
                Synonyms (comma separated)
              </label>
              <input
                id={id("syn")}
                value={draft.synonyms}
                onChange={(e) => onDraft({ synonyms: e.target.value })}
                placeholder="engagement, watch time"
                style={inputStyle}
              />
            </div>
            <div>
              <label htmlFor={id("pre")} style={sublabelStyle}>
                Pre-period column
              </label>
              <select
                id={id("pre")}
                value={draft.prePeriodColumn}
                onChange={(e) => onDraft({ prePeriodColumn: e.target.value })}
                style={selectStyle}
              >
                <option value="">— none —</option>
                {prePeriodOptions.map((c) => (
                  <option key={c.name} value={c.name}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── 02 · one lever candidate row ────────────────────────────────────────────
function LeverGroundRow({
  idx,
  col,
  draft,
  onDraft,
}: {
  idx: number;
  col: ColumnProfile;
  draft: LeverDraft;
  onDraft: (patch: Partial<LeverDraft>) => void;
}) {
  const id = (suffix: string) => `ground-lever-${idx}-${suffix}`;
  const sample =
    col.sample_values && col.sample_values.length > 0
      ? col.sample_values.slice(0, 2).map(String).join(" / ")
      : null;
  return (
    <div
      style={{
        ...fieldStyle,
        border: `1px solid ${C.line}`,
        borderRadius: 4,
        padding: "10px 12px",
        background: draft.selected ? C.panel : "transparent",
      }}
    >
      <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
        <span style={{ fontFamily: FONT_MONO, fontSize: 13, color: C.textHi }}>{col.name}</span>
        <Chip>{col.dtype}</Chip>
        {col.distinct_count != null && <Chip>{col.distinct_count} DISTINCT</Chip>}
        {draft.selected && <Chip>LEVER</Chip>}
        <span style={{ marginLeft: "auto" }}>
          <button
            type="button"
            aria-pressed={draft.selected}
            aria-label={`${draft.selected ? "Remove" : "Mark"} ${col.name} as a lever`}
            onClick={() => onDraft({ selected: !draft.selected })}
            style={groundRowActionStyle}
          >
            {draft.selected ? "REMOVE" : "+ MARK AS LEVER"}
          </button>
        </span>
      </div>
      {sample !== null && (
        <div style={{ ...railCaptionStyle, marginTop: 3 }}>e.g. {sample}</div>
      )}

      {draft.selected && (
        <div style={{ marginTop: 12, ...fieldRowStyle }}>
          <div>
            <label htmlFor={id("dname")} style={sublabelStyle}>
              Display name
            </label>
            <input
              id={id("dname")}
              value={draft.displayName}
              onChange={(e) => onDraft({ displayName: e.target.value })}
              placeholder="e.g. Offline downloads"
              style={inputStyle}
            />
          </div>
          <div>
            <label htmlFor={id("desc")} style={sublabelStyle}>
              Description
            </label>
            <input
              id={id("desc")}
              value={draft.description}
              onChange={(e) => onDraft({ description: e.target.value })}
              placeholder="what exposure this flag records (optional)"
              style={inputStyle}
            />
          </div>
        </div>
      )}
    </div>
  );
}

// ── compact Ground manifest block — right-hand rail (§8.2 chip idiom) ────────
function GroundRail({
  enabled,
  metricCount,
  leverCount,
  unguardedCount,
}: {
  enabled: boolean;
  metricCount: number;
  leverCount: number;
  unguardedCount: number;
}) {
  const rows: [string, string][] = enabled
    ? [
        ["METRICS", String(metricCount)],
        ["LEVERS", String(leverCount)],
        ["UNGUARDED", String(unguardedCount)],
      ]
    : [];
  return (
    <aside
      className="groundrail"
      aria-label="Grounding manifest"
      style={{ position: "sticky", top: 24, alignSelf: "start" }}
    >
      <div
        style={{
          background: C.panel,
          border: `1px solid ${C.line}`,
          borderRadius: 8,
          padding: "12px 14px",
        }}
      >
        <div style={{ ...sublabelStyle, marginBottom: 8 }}>Ground</div>
        {/* Panel-verdict-chip register: mono, recessed fill, rule border — a
            surface tone, never a semantic fill (§8.2). The words carry state. */}
        <span
          style={{
            display: "inline-block",
            fontFamily: FONT_MONO,
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: "0.06em",
            color: C.textHi,
            background: C.panelRecessed,
            border: `1px solid ${C.line}`,
            borderRadius: 4,
            padding: "3px 8px",
            ...TNUM,
          }}
        >
          {enabled
            ? `${metricCount} METRIC${metricCount === 1 ? "" : "S"} · ${leverCount} LEVER${leverCount === 1 ? "" : "S"}`
            : "OFF"}
        </span>
        {enabled ? (
          <dl
            style={{
              margin: 0,
              marginTop: 10,
              display: "grid",
              gridTemplateColumns: "auto 1fr",
              gap: "4px 12px",
            }}
          >
            {rows.map(([dt, dd]) => (
              <Fragment key={dt}>
                <dt style={railCaptionStyle}>{dt}</dt>
                <dd style={{ margin: 0, fontFamily: FONT_MONO, fontSize: 11, color: C.textHi, textAlign: "right", ...TNUM }}>
                  {dd}
                </dd>
              </Fragment>
            ))}
          </dl>
        ) : (
          <div style={{ ...railCaptionStyle, marginTop: 10 }}>
            NOT DECLARED — THE BUILD RUNS UNGROUNDED (DEFAULT).
          </div>
        )}
        {enabled && unguardedCount > 0 && (
          <div style={{ ...railCaptionStyle, marginTop: 8 }}>
            UNGUARDED METRICS BUILD UNVERIFIED — NO NEGATIVE CONTROL.
          </div>
        )}
      </div>
    </aside>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Step 4 · Build (#28) — config + live watch on ONE fire-and-watch step.
// ════════════════════════════════════════════════════════════════════════════

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
  sourceKind,
  sourceMode,
  tableFqn,
  sql,
  columns,
  rowCount,
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
  sourceKind: SourceKind;
  sourceMode: SourceMode;
  tableFqn: string;
  sql: string;
  columns: ColumnProfile[] | null;
  rowCount: number | null;
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
  // #3 doc feeder: extraction + mapping run end-to-end, but persisting a pack
  // from documents needs the persona-build store + pipeline binding (deferred),
  // so the build is honestly preview-only here rather than faked.
  if (sourceKind === "documents") {
    return <DocumentsBuildNotice columns={columns} rowCount={rowCount} mapping={mapping} />;
  }
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
              <dt style={{ fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", color: C.textMut }}>
                {dt}
              </dt>
              <dd style={{ margin: 0, fontFamily: FONT_MONO, fontSize: 12, color: C.textHi, overflowWrap: "break-word", ...TNUM }}>
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
              background: C.panelRecessed,
              border: `1px solid ${C.line}`,
              borderRadius: 4,
              fontFamily: FONT_MONO,
              fontSize: 12,
              color: C.textHi,
              whiteSpace: "pre-wrap",
              overflowWrap: "break-word",
            }}
          >
            {sql.trim()}
          </pre>
        )}
      </section>

      <section style={sectionStyle}>
        <div style={sectionLabelStyle}>Column mapping</div>
        <dl style={{ margin: 0, marginTop: 12, display: "grid", gridTemplateColumns: "auto 1fr", gap: "6px 16px" }}>
          {FEATURE_GROUPS.map((group) => {
            const cols = groupCols(group);
            return (
              <div key={group} style={{ display: "contents" }}>
                <dt style={{ fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", color: C.textMut }}>
                  {GROUP_LABELS[group]}
                </dt>
                <dd style={{ margin: 0, fontFamily: FONT_MONO, fontSize: 12, color: cols.length ? C.textHi : C.textMut, overflowWrap: "break-word" }}>
                  {cols.length ? cols.join(" · ") : "—"}
                </dd>
              </div>
            );
          })}
          {ignoredCols.length > 0 && (
            <div style={{ display: "contents" }}>
              <dt style={{ fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", color: C.textMut }}>
                Ignored
              </dt>
              <dd style={{ margin: 0, fontFamily: FONT_MONO, fontSize: 12, color: C.textMut, overflowWrap: "break-word" }}>
                {ignoredCols.join(" · ")}
              </dd>
            </div>
          )}
        </dl>
      </section>

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
      <div style={{ display: "flex", alignItems: "baseline", gap: 12, flexWrap: "wrap" }}>
        <span style={statusLineStyle}>{buildStatusLine(build)}</span>
        <span style={railCaptionStyle}>BUILD {build.id}</span>
        <span style={railCaptionStyle}>STARTED {utcStamp(build.created_at)}</span>
        {build.completed_at && <span style={railCaptionStyle}>SETTLED {utcStamp(build.completed_at)}</span>}
      </div>

      {(build.stability_score !== null || build.persona_count !== null) && (
        <div style={{ ...railCaptionStyle, marginTop: 6, color: C.text }}>
          {build.stability_score !== null ? `STABILITY ${build.stability_score}` : ""}
          {build.stability_score !== null && build.persona_count !== null ? " · " : ""}
          {build.persona_count !== null ? `${build.persona_count} PERSONAS` : ""}
        </div>
      )}

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

      <section style={sectionStyle}>
        <div style={sectionLabelStyle}>Build log</div>
        {events.length === 0 ? (
          <div style={{ ...statusLineStyle, color: C.textMut, marginTop: 10 }}>
            {isBuildTerminal(build.status) ? "NO EVENTS RECORDED." : "WAITING FOR THE FIRST EVENT…"}
          </div>
        ) : (
          <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 4 }}>
            {events.map((ev, i) => (
              <div key={`${ev.at}-${i}`} style={{ display: "flex", gap: 12 }}>
                <span style={{ ...railCaptionStyle, flexShrink: 0, width: 150 }}>{utcStamp(ev.at)}</span>
                <span style={{ fontFamily: FONT_MONO, fontSize: 12, color: C.textHi, ...TNUM }}>
                  {eventLine(ev)}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {build.status === "complete" && (
        <div style={{ ...railCaptionStyle, marginTop: 14, color: C.text }}>
          BUILD COMPLETE — CONTINUE TO EVALUATE THE PACK BEFORE PROMOTING.
        </div>
      )}

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
// Step 5 · Evaluate (NEW) — read before you promote (#27/#28).
// ════════════════════════════════════════════════════════════════════════════

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
  if (!build || build.status !== "complete" || !build.pack_version) {
    return (
      <div style={{ ...statusLineStyle, color: C.textMut }}>
        NO COMPLETE BUILD TO EVALUATE — GO BACK TO BUILD.
      </div>
    );
  }

  if (phase === "loading" || phase === "idle") {
    return (
      <div style={{ ...statusLineStyle, color: C.textMut, marginTop: 8 }}>
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

  const availableSchemes = pack.weight_schemes.filter((s) => s.available);

  return (
    <div style={{ maxWidth: 720 }}>
      <div style={{ ...railCaptionStyle, color: C.text }}>
        STABILITY {pack.stability_score.toFixed(2)} · {pack.persona_count} PERSONA
        {pack.persona_count === 1 ? "" : "S"} · SCHEMA {pack.schema_version} ·{" "}
        {pack.version.toUpperCase()}
      </div>
      <div style={hintStyle}>
        This pack is built but <strong style={{ color: C.text }}>not yet promoted</strong> — read it here
        before you commit. Each persona shows its share, a one-line summary, and
        how distinctive it is from the population.
      </div>

      <div style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 18 }}>
        {pack.personas.map((persona) => (
          <EvaluatePersona key={persona.id} persona={persona} schemes={availableSchemes} />
        ))}
      </div>

      <div style={{ ...okBannerStyle, marginTop: 22, borderColor: C.line }}>
        Stability ({pack.stability_score.toFixed(2)}) is the quality signal
        available today — how reproducible the clustering is. Calibration against
        a holdout (Jaccard overlap) is tracked separately and is not shown here
        yet, so it isn&apos;t reported as a number you don&apos;t have.
      </div>

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
        background: C.panel,
        border: `1px solid ${C.line}`,
        borderRadius: 8,
        padding: "14px 18px 16px",
      }}
    >
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
        <span style={{ fontSize: 15, fontWeight: 600, letterSpacing: "-0.01em", color: C.textHi }}>
          {persona.name}
        </span>
        <Designator>{persona.id}</Designator>
        {shareChips.map((c) => (
          <Designator key={c.key}>
            {(c.pct * 100).toFixed(0)}% {c.label.toUpperCase()}
          </Designator>
        ))}
      </div>

      <p style={{ margin: "10px 0 0", fontSize: 14, lineHeight: 1.5, color: C.text }}>
        {persona.description}
      </p>

      <p style={{ margin: "8px 0 0", fontSize: 13, lineHeight: 1.5, color: C.textMut }}>
        {distinctivenessLine(persona.distinctive)}
      </p>
    </div>
  );
}

function Designator({ children }: { children: React.ReactNode }) {
  return (
    <span
      style={{
        fontFamily: FONT_MONO,
        fontSize: 10.5,
        letterSpacing: "0.04em",
        border: `1px solid ${C.line}`,
        color: C.textMut,
        borderRadius: 4,
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
// Step 6 · Promote (#28) — terminal. Folds in the old Done content.
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
      <div style={{ ...statusLineStyle, color: C.textMut }}>
        NO COMPLETE BUILD TO PROMOTE — GO BACK TO BUILD.
      </div>
    );
  }

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
                <dt style={{ fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", color: C.textMut }}>
                  {dt}
                </dt>
                <dd style={{ margin: 0, fontFamily: FONT_MONO, fontSize: 12, color: C.textHi, ...TNUM }}>{dd}</dd>
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

  return (
    <div style={{ maxWidth: 620 }}>
      {promoteError && (
        <div role="alert" style={errorBannerStyle}>
          {promoteError}
        </div>
      )}
      <section>
        <div style={sectionLabelStyle}>Promote to latest</div>
        <div style={{ ...railCaptionStyle, marginTop: 12, color: C.text }}>
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
