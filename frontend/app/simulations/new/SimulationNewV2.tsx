"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ApiError,
  createSimulation,
  DEFAULT_SETUP_ID,
  getActivePersonas,
  getCapabilities,
  getSimulation,
  getSimulationLimits,
  listCrawlSetups,
  listSupportedModels,
  parseNeedsInput,
  preflightSimulation,
  type ActivePersonasResponse,
  type CrawlSetupListItem,
  type FeaturePackManifest,
  type Hypothesis,
  type ModelInfo,
  type NeedsInputDetail,
  type PersonaSummary,
  type PreflightResponse,
  type ReverseFigma,
  type SimulationLimitsResponse,
  type SimulationRequest,
} from "@/lib/api";
import { FONT_SANS, FONT_MONO, TNUM } from "@/lib/design";
import SampleWorkspaceCard from "@/components/SampleWorkspaceCard";
import AppShellV2 from "@/components/v2/AppShellV2";

// ───────────────────────────────────────────────────────────────────────────
// /simulations/new — the v2 dark "Reading Console" reskin of the run wizard.
//
// FORK-AND-RESTYLE of SimulationNewLegacy.tsx (the FROZEN source of truth for
// ALL behaviour). This file reproduces every state value, field binding,
// validation rule, honesty/answerability gate, submit/override mutation,
// error/loading/empty branch, <Link>/button/onClick and draft-persistence path
// of the legacy wizard — byte-for-byte in LOGIC — and changes ONLY presentation
// (markup + style values + layout) into the dark Console language of
// design-rethink/mocks/simulations-new.html.
//
// It renders INSIDE AppShellV2 surface="console" (the shell owns the dark rail +
// appbar). The body is scoped under a single `.rconsole` wrapper so the copied
// RCONSOLE_CSS applies to the embedded form controls (dark <select> arrow,
// ::selection, focus rings). The wizard's JSX still drives its presentation
// through the shared style objects below — so the SOLE restyle vector is the
// dark token map `TOKENS` (overriding the light @/lib/design tokens by name) +
// the ~5 active-state cells handled explicitly inline. Every JSX node, prop,
// handler and conditional is identical to the legacy.
//
// Honesty law (DESIGN.md §8.1 / §9): no fabricated fields, no verdict color
// (the only signal accent is the action-button border), and every
// answerability / disclosure / completeness copy string survives verbatim. The
// mock's decorative Population-Field canvas is intentionally NOT ported here —
// it shows fabricated cohort data the legacy wizard does not have, which §8.1
// forbids inventing.
// ───────────────────────────────────────────────────────────────────────────

// ── dark Console token map (verbatim hues from the simulations-new mock +
//    SimulationDetailV2 RCONSOLE_CSS). It overrides the LIGHT @/lib/design
//    TOKENS *by name*, so every inline style that reads `TOKENS.ink` /
//    `TOKENS.paper…` etc. re-renders on the dark surface with ZERO JSX edits.
//    Names keep their light-mode semantics (ink = primary text, paper = idle
//    control surface, paperElevated = panels, paperRecessed = wells), so the
//    wizard's existing usages map cleanly. `success`/`warn`/`alert` are the
//    mock's signal/edge/alert hues — accent-only, never a fill (DESIGN.md §4.3).
const TOKENS = {
  ink: "#E7ECF5", // primary text  (--text-hi)
  inkMuted: "#929BAE", // secondary text (--text-mut)
  paper: "#161F32", // page / control idle surface (--console-800)
  paperElevated: "#161F32", // panels (--console-800)
  paperRecessed: "#0B1220", // recessed wells (--console-900)
  rule: "#33405C", // hairline (--console-line)
  alert: "#F0683C", // alert accent  (--alert)
  warn: "#C9A227", // edge accent   (--edge-warn)
  success: "#39B894", // signal-dim    (--signal-dim)
} as const;

// scoped console tokens + form-control chrome for the embedded wizard. Mirrors
// the simulations-new mock's dark <select> arrow, focus ring, placeholder, and
// ::selection so the native inputs read as Console instruments, not OS defaults.
const RCONSOLE_CSS = `
.rconsole{
  --console-900:#0B1220; --console-850:#10192A; --console-800:#161F32;
  --console-750:#1D2740; --console-700:#26314C; --console-line:#33405C;
  --text-hi:#E7ECF5; --text:#C6CCD8; --text-mut:#929BAE; --text-faint:#646E84;
  --signal:#48EFCA; --signal-dim:#39B894; --signal-wash:rgba(72,239,202,.12);
  --spread:#C8B68A; --spread-dim:#90815F;
  --arm-control:#4FA8E0; --arm-treat:#E08BC4;
  --edge-warn:#C9A227; --alert:#F0683C;
  --r-well:4px; --r-panel:8px;
  color:var(--text);
  font-variant-numeric:tabular-nums;
}
.rconsole *{box-sizing:border-box; font-variant-numeric:tabular-nums;}
.rconsole ::selection{background:var(--signal-wash); color:var(--text-hi);}
.rconsole input::placeholder, .rconsole textarea::placeholder{
  color:rgba(146,155,174,.7);}
/* native control focus ring → console signal-dim (matches the mock) */
.rconsole input:focus-visible, .rconsole textarea:focus-visible,
.rconsole select:focus-visible{
  border-color:var(--signal-dim);
  box-shadow:0 0 0 2px rgba(57,184,148,.28);}
.rconsole a:focus-visible, .rconsole button:focus-visible{
  outline:2px solid var(--signal-dim); outline-offset:2px;}
/* dark dropdown chevron for every <select> (light theme's is invisible here) */
.rconsole select{
  appearance:none; -webkit-appearance:none;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='%23929BAE' stroke-width='2'><path d='M6 9l6 6 6-6'/></svg>");
  background-repeat:no-repeat; background-position:right 11px center;
  padding-right:34px;}
.rconsole select option{background:var(--console-800); color:var(--text-hi);}
.rconsole select option:disabled{color:var(--text-faint);}
/* tame the native checkbox tint to the signal accent on the large-run ack */
.rconsole input[type=checkbox]{accent-color:var(--signal-dim);}
/* full-bleed work area: negative margin MUST track AppShellV2's responsive
   .v2-appmain padding (--space-section desktop → --space-room ≤1024px), else
   the wizard overflows the content column on tablet/mobile (codex P2). */
.rconsole .fullbleed-main{margin:calc(-1 * var(--space-section,48px));}
@media (max-width:1024px){
  .rconsole .fullbleed-main{margin:calc(-1 * var(--space-room,24px));}
}
@media (max-width:1080px){
  .rconsole form{flex-direction:column!important;}
  .rconsole .rc-rail{
    width:auto!important; border-left:none!important;
    border-top:1px solid var(--console-line)!important;}
  .rconsole .rc-rail-sticky{position:static!important;}
}
@media (prefers-reduced-motion:reduce){
  .rconsole *{animation:none!important; transition-duration:1ms!important;}
}
`;

// Design R2 PR 5 (#167) — wizard recompose per DESIGN.md §7.4 "configuring a
// run": two-zone layout (620px evidence form with numbered sections + live
// Reading-manifest inspector rail). Presentational only — every field, its
// state handling, validation, and the submit payload are unchanged from the
// pre-R2 wizard.

// ── #279 metric registry mirror ─────────────────────────────────────────────
// A thin frontend mirror of `backend/sidira_simulator/services/metric_registry.py`.
// `metric_name` is the closed Literal from `schemas.simulation.Hypothesis`
// (conversion · retention · ctr); None = sentiment-only. `REQUIRED_METRIC_FIELDS`
// mirrors each descriptor's `required_template_fields` 1:1 so the wizard's
// validation matches the backend's `Hypothesis._validate_metric` exactly:
//   - conversion → conversion_action + conversion_action_label + decision_point
//   - retention  → decision_point only (the "return" label is OPTIONAL, reuses
//                  conversion_action_label; registry default "return next week")
//   - ctr        → decision_point only (the click label is OPTIONAL, reuses
//                  conversion_action_label; registry default "click it")
// `choice_set` is optional for every metric (empty → the registry default).
type MetricKey = "conversion" | "retention" | "ctr";
type MetricName = MetricKey | null;
type MetricFieldName =
  | "conversion_action"
  | "conversion_action_label"
  | "decision_point";

const METRIC_LABELS: Record<MetricKey, string> = {
  conversion: "Conversion",
  retention: "Retention",
  ctr: "CTR",
};

const REQUIRED_METRIC_FIELDS: Record<MetricKey, MetricFieldName[]> = {
  conversion: [
    "conversion_action",
    "conversion_action_label",
    "decision_point",
  ],
  retention: ["decision_point"],
  ctr: ["decision_point"],
};

const METRIC_FIELD_LABELS: Record<MetricFieldName, string> = {
  conversion_action: "a conversion event",
  conversion_action_label: "an in-character label",
  decision_point: "a decision point",
};

// ── #313 / T4: structured claim composer ────────────────────────────────────
// Epic #309 found that free-text claims slide into vague or framing-led prose
// that the answerability gate (T1) blocks. The wizard's default authoring mode
// is now four structured fields following the falsifiable template:
//   "If [change] for [cohort], then [OEC metric] [direction]."
// `composeClaimProse` folds them into the single `prose` string the API still
// expects — no schema change, byte-compatible with a hand-written claim. The
// free-text escape hatch (`claimFreeText`) bypasses the composer verbatim so a
// terse expert hypothesis is never over-constrained.
type ClaimDirection = "increases" | "decreases" | "changes";

const CLAIM_DIRECTION_LABELS: Record<ClaimDirection, string> = {
  increases: "increases",
  decreases: "decreases",
  changes: "changes",
};

interface StructuredClaim {
  change: string;
  cohort: string;
  metric: string;
  direction: ClaimDirection;
}

function composeClaimProse(c: StructuredClaim): string {
  const change = c.change.trim();
  const cohort = c.cohort.trim();
  const metric = c.metric.trim();
  // The cohort clause is optional — a product-wide change reads "If [change],
  // then…". Everything else is required for a falsifiable claim (enforced in
  // handleSubmit before this runs).
  const cohortClause = cohort ? ` for ${cohort}` : "";
  return `If ${change}${cohortClause}, then ${metric} ${CLAIM_DIRECTION_LABELS[c.direction]}.`;
}

// ── #337 / T6: glanceable completeness checklist ─────────────────────────────
// A DISPLAY-ONLY affordance (epic #309). It shows "N of M essentials present"
// with a per-item present/absent list so the PM can see at a glance what their
// hypothesis is missing before they run it.
//
// HARD CONSTRAINTS (epic #309): this is deterministic, ZERO-LLM, NO backend.
// The `present` count is a human-glance number — it is NEVER fed to
// confidence_score, the verdict, or persisted, and it does NOT gate submit (the
// authoritative block/override path lives in the T4 needs_input/422 surface).
// Each item is derived purely from (a) the wizard's current form state and
// (b) the EXISTING live POST /simulations/preflight response (T4 already wires
// that call — we REUSE its result; no second call).
//
// `proposed_figma` has no authoring path in the wizard yet (#183), so the
// "conditional design attached" item reuses the preflight gate's own signal: the
// structurally-invisible-change check is the `structurally_invisible_change`
// reason code (backend services/answerability.py). Its PRESENCE means the
// structural change still needs a figma → item absent; its ABSENCE (the prose
// reads as non-structural, OR a design is attached) → item satisfied. This is
// "conditional": for a non-structural change there is nothing to attach, so the
// item is satisfied by construction — exactly what the gate already decided.
const REASON_STRUCTURALLY_INVISIBLE = "structurally_invisible_change";

interface CompletenessItem {
  key: string;
  label: string;
  present: boolean;
  // Advisory items are presentational-only-distinct: they never block (the
  // actual block/override lives in the T4 needs_input/422 path) and are not
  // counted toward "essentials present". Mechanism is the one advisory item.
  advisory?: boolean;
}

// Deterministic direction-keyword probe for the free-text escape hatch, where
// there is no direction <select>. Mirrors CLAIM_DIRECTION_LABELS plus the
// common predicted-direction verbs a terse expert claim uses. Pure string match
// — no LLM, no scoring.
function proseDeclaresDirection(prose: string): boolean {
  const p = prose.toLowerCase();
  return [
    "increase",
    "decrease",
    "raise",
    "lower",
    "improve",
    "reduce",
    "lift",
    "drop",
    "go up",
    "go down",
    "higher",
    "lower",
    "change",
  ].some((w) => p.includes(w));
}

function deriveCompleteness(args: {
  claimMode: "structured" | "freetext";
  claimChange: string;
  claimCohort: string;
  claimMetric: string;
  freeText: string;
  metricName: MetricName;
  showAdvanced: boolean;
  proposedPrd: string;
  preflight: PreflightResponse | null;
  preflightStale: boolean;
}): CompletenessItem[] {
  const {
    claimMode,
    claimChange,
    claimCohort,
    claimMetric,
    freeText,
    metricName,
    showAdvanced,
    proposedPrd,
    preflight,
    preflightStale,
  } = args;

  const structured = claimMode === "structured";

  // 1. Change — the proposed change is described. Structured: the `change`
  //    field. Free-text: any prose at all (the claim itself carries the change).
  const changePresent = structured
    ? claimChange.trim().length > 0
    : freeText.trim().length > 0;

  // 2. Cohort — a `for [cohort]` is specified. Structured: the cohort field.
  //    Free-text: a "for …" clause anywhere in the prose.
  const cohortPresent = structured
    ? claimCohort.trim().length > 0
    : /\bfor\b/i.test(freeText);

  // 3. OEC metric — the surfaced conversion-metric bundle is declared via the
  //    05 · Outcome metric picker. (The structured claim's free-text "then …
  //    metric" phrase is the prose OEC, but the answerability gate routes on the
  //    declared `metric_name`, so we glance on the declared bundle.)
  const metricPresent = metricName != null;

  // 4. Direction — the predicted direction is set. Structured mode always has a
  //    direction <select>, but it is only meaningful once an outcome phrase is
  //    named, so we tie it to the metric phrase being filled. Free-text: a
  //    direction keyword is present in the prose.
  const directionPresent = structured
    ? claimMetric.trim().length > 0
    : proseDeclaresDirection(freeText);

  // 5. Conditional design attached — REUSE the preflight gate's own structural
  //    signal rather than re-deriving the regime classifier on the client. The
  //    item is satisfied only once the CURRENT claim has actually been assessed
  //    (a fresh, non-stale preflight verdict is in hand) AND that verdict did
  //    NOT flag a structurally-invisible change. Before assessment — an empty /
  //    too-short claim with no preflight, or the debounce window after an edit —
  //    we report it MISSING rather than vacuously satisfied, so an empty form
  //    glances as 0 of N and a just-edited claim doesn't briefly claim a stale
  //    "present". For a non-structural change the gate omits the
  //    structurally_invisible_change code, so the item satisfies by
  //    construction. The authoritative block is the T4 422, not this glance.
  const assessed = preflight != null && !preflightStale;
  const figmaNeeded =
    preflight?.reason_codes.includes(REASON_STRUCTURALLY_INVISIBLE) ?? false;
  const designPresent = assessed && !figmaNeeded;

  // 6. Advisory mechanism — a mechanism / "why" is provided. The wizard's only
  //    mechanism-bearing field is the stimulus PRD-delta (treatment text), which
  //    explains HOW/WHY the change moves the outcome. Advisory: ✓/✗ but never
  //    blocks, never counted toward essentials.
  const mechanismPresent = showAdvanced && proposedPrd.trim().length > 0;

  return [
    { key: "change", label: "Change described", present: changePresent },
    { key: "cohort", label: "Cohort specified", present: cohortPresent },
    { key: "metric", label: "OEC metric declared", present: metricPresent },
    {
      key: "direction",
      label: "Predicted direction set",
      present: directionPresent,
    },
    {
      key: "design",
      label: "Conditional design attached",
      present: designPresent,
    },
    {
      key: "mechanism",
      label: "Mechanism / why (advisory)",
      present: mechanismPresent,
      advisory: true,
    },
  ];
}

export default function SimulationNewV2() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // #44 refinement carry-through: the result page's "Try this" CTA opens this
  // wizard with ?parent=<sim id>&prose=<refinement text>. We read both ONCE on
  // mount — the parent id is threaded onto the create payload so the new run is
  // LINKED to its parent (the Phase-8 lineage chain). Reading once (not on every
  // searchParams change) means the PM's later edits are never clobbered.
  const parentSimulationId = useRef<string | null>(null);
  const consumedPrefill = useRef(false);

  // refinement-inherit (follow-up to #44): the refined claim text from ?prose
  // REPLACES the parent's claim; everything else (OEC metric + its fields,
  // proposed_figma, proposed_prd, capability, crawl setup_id) is INHERITED from
  // the parent's full hypothesis so a refinement of an answerable run stays
  // answerable instead of dead-ending at the #309 gate. We fetch the parent via
  // getSimulation(parentId) once; the inherited fields flow into BOTH visible
  // wizard state AND the submitted request. Each inherited field is guarded by
  // its own one-time ref so the prefill never clobbers the PM's later edits and
  // so the capability/setup seeds can wait for their async option lists.
  const consumedRefinementProse = useRef(false);
  const appliedInheritedCapability = useRef(false);
  const appliedInheritedSetup = useRef(false);
  // The parent's hypothesis, fetched once. Drives the inherit effects below.
  const [inheritedHypothesis, setInheritedHypothesis] =
    useState<Hypothesis | null>(null);
  // proposed_figma has no authoring path in the wizard (#183), so an inherited
  // figma is held here and threaded straight into buildHypothesis — without it
  // the answerability gate (#309) would still fire on a figma-only parent.
  const inheritedFigma = useRef<ReverseFigma | null>(null);
  // The crawl setup the parent ran against; applied once the setup roster loads.
  const inheritedSetupId = useRef<string | null>(null);
  // True for the life of the wizard when opened from a refinement CTA. Drives
  // the answerability fallback: a refinement must ALWAYS be runnable on Begin
  // reading, so a non-answerable refinement submits with run_as_generic_reception.
  const [isRefinement, setIsRefinement] = useState(false);

  const [manifest, setManifest] = useState<FeaturePackManifest | null>(null);
  const [loadingCaps, setLoadingCaps] = useState(true);
  const [capsError, setCapsError] = useState<string | null>(null);

  // sessions/sample-workspace: sample seeding is offered only when BOTH
  // /capabilities and /personas 404 — a truly empty tenant. A tenant with
  // one real pack (e.g. personas built, crawl pending) would just hit the
  // backend's 409, so don't offer the button. (codex R1-P3)
  const [capsNotFound, setCapsNotFound] = useState(false);
  const [personasNotFound, setPersonasNotFound] = useState(false);
  // #212: an empty tenant gets a starter pack (200, is_starter) instead of a
  // 404, so "no real personas yet" is now starter-OR-404, not 404 alone.
  const [personasAreStarter, setPersonasAreStarter] = useState(false);

  // #215/#245 PR 3b: which crawl setup this sim targets. Defaults to the
  // "default" anchor, so a default-only org behaves EXACTLY as today (the setup
  // picker stays hidden and `setup_id` is omitted from the request). When the
  // org has >1 setup, the PM picks one; its capabilities are fetched scoped to
  // it and the sim is created against it.
  const [setups, setSetups] = useState<CrawlSetupListItem[]>([]);
  const [setupId, setSetupId] = useState<string>(DEFAULT_SETUP_ID);
  // Honest state for the roster fetch: a failure must not silently route a
  // multi-setup org to "default", so we surface a quiet note rather than
  // swallowing it (a default-only org never sees this — it just runs default).
  const [setupsError, setSetupsError] = useState<string | null>(null);

  const [capability, setCapability] = useState<string>("");
  // #313 / T4: structured claim authoring is the default; the free-text
  // escape hatch (`claimMode === "freetext"`) bypasses the composer for terse
  // expert hypotheses. `hypothesis` holds the composed/raw prose the API gets.
  const [claimMode, setClaimMode] = useState<"structured" | "freetext">(
    "structured",
  );
  const [claimChange, setClaimChange] = useState<string>("");
  const [claimCohort, setClaimCohort] = useState<string>("");
  const [claimMetric, setClaimMetric] = useState<string>("");
  const [claimDirection, setClaimDirection] =
    useState<ClaimDirection>("increases");
  const [hypothesis, setHypothesis] = useState<string>("");

  // refinement carry-through: consume the ?parent / ?prose carry ONCE on mount.
  // The refined prose seeds the free-text claim (editable; never locked). When a
  // parent id is present we ALSO fetch the parent sim and inherit its full
  // structured hypothesis (metric/figma/prd/capability/setup) so a refinement of
  // an answerable run stays answerable. Reading once (not on every searchParams
  // change) plus the per-field guards below means the PM's later edits are never
  // clobbered. The parent fetch is fully defensive — a 404/owned-by-no-one/
  // network failure falls back to today's prose-only prefill and never crashes.
  useEffect(() => {
    if (consumedPrefill.current) return;
    consumedPrefill.current = true;
    const parent = searchParams?.get("parent");
    const prose = searchParams?.get("prose");
    if (parent) {
      parentSimulationId.current = parent;
      setIsRefinement(true);
    }
    if (prose && prose.trim()) {
      consumedRefinementProse.current = true;
      setClaimMode("freetext");
      setHypothesis(prose);
    }
    if (!parent) return;

    let cancelled = false;
    (async () => {
      try {
        const sim = await getSimulation(parent);
        if (cancelled) return;
        const hyp = sim.hypothesis;
        // Inherit proposed_figma straight into the submit thread (no authoring
        // path here, #183) so a figma-bearing parent stays answerable.
        inheritedFigma.current = hyp.proposed_figma ?? null;
        // Inherit the crawl setup the parent ran against (applied once the setup
        // roster loads — see the setup-apply effect).
        if (sim.setup_id) inheritedSetupId.current = sim.setup_id;
        // Inherit proposed_prd into the stimulus well so it reaches the payload
        // AND the PM can see/edit it (showAdvanced gates whether it is sent).
        if (hyp.proposed_prd && hyp.proposed_prd.trim()) {
          setShowAdvanced(true);
          setProposedPrd(hyp.proposed_prd);
        }
        // Inherit the OEC metric + its template fields. The wizard's metric
        // picker only represents conversion/retention/ctr; the backend's fourth
        // value ("visit") and null have no picker — leave the metric unset for
        // those (the answerability fallback below keeps the run unblocked).
        if (
          hyp.metric_name === "conversion" ||
          hyp.metric_name === "retention" ||
          hyp.metric_name === "ctr"
        ) {
          setMetricName(hyp.metric_name);
          if (hyp.conversion_action)
            setConversionAction(hyp.conversion_action);
          if (hyp.conversion_action_label)
            setConversionActionLabel(hyp.conversion_action_label);
          if (hyp.decision_point) setDecisionPoint(hyp.decision_point);
          if (hyp.choice_set && hyp.choice_set.length > 0)
            setChoiceSetText(hyp.choice_set.join("\n"));
        }
        // Capability is inherited via a dedicated effect that waits for the
        // feature pack to load (it can only be set once it exists in the pack).
        setInheritedHypothesis(hyp);
        // If the CTA didn't carry a refined prose, fall back to the parent's
        // own claim so the wizard isn't blank.
        if (!consumedRefinementProse.current && hyp.prose && hyp.prose.trim()) {
          setClaimMode("freetext");
          setHypothesis(hyp.prose);
        }
      } catch {
        // Defensive: a failed parent fetch leaves the wizard in today's
        // prose-only behavior. The parent id still rides the create payload so
        // the lineage link survives; the run is just authored from scratch.
        if (!cancelled) setInheritedHypothesis(null);
      }
    })();
    return () => {
      cancelled = true;
    };
    // searchParams is stable for the life of the route; read once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Inherit the parent's crawl setup once the roster has loaded — only when the
  // setup actually exists in this org's roster (else keep the default anchor).
  // Guarded so a later manual setup switch is never overwritten. (capabilities
  // are inherited by a sibling effect below, after `capabilities` is derived.)
  useEffect(() => {
    if (appliedInheritedSetup.current) return;
    const want = inheritedSetupId.current;
    if (!want || want === DEFAULT_SETUP_ID) return;
    if (setups.length === 0) return;
    appliedInheritedSetup.current = true;
    if (setups.some((s) => s.setup_id === want)) {
      // Re-arm the capability inherit so it re-applies against the parent
      // setup's freshly-loaded pack (the setupId-change reloads capabilities and
      // resets the selection to caps[0]); without this the inherited capability
      // would be lost on a multi-setup refinement.
      appliedInheritedCapability.current = false;
      setSetupId(want);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setups]);

  // The prose actually submitted: composed from the structured fields, or the
  // free-text box verbatim. Derived so the preflight lint + manifest + submit
  // all read one source of truth.
  const structuredClaim: StructuredClaim = {
    change: claimChange,
    cohort: claimCohort,
    metric: claimMetric,
    direction: claimDirection,
  };
  const composedProse =
    claimMode === "structured"
      ? claimChange.trim() && claimMetric.trim()
        ? composeClaimProse(structuredClaim)
        : ""
      : hypothesis;
  // Population state is kept as a string so an empty field stays empty
  // (rather than briefly collapsing to "0" and rendering "0 sampled agents").
  // Parsed to a number only at submit time. Codex P2 (round 1).
  const [populationInput, setPopulationInput] = useState<string>("1000");
  const populationSize = parsePositiveInt(populationInput);
  // Second cohort knob alongside population: how many LLM agents to actually
  // materialize. Kept as a string so an empty field means "use the backend cap"
  // (the historical derive-from-population behavior) rather than collapsing to 0.
  // When set, the realized sample is min(population, agentCount, cap) — the env
  // cap stays a hard ceiling this value can lower but never exceed.
  const [agentCountInput, setAgentCountInput] = useState<string>("");
  const requestedAgentCount = parsePositiveInt(agentCountInput);
  // R2 #167: `showAdvanced` is now the "+ new stimulus…" inline authoring
  // well in 02 · Subject (formerly the "Advanced options" disclosure). Same
  // state, same payload semantics: proposed_prd is sent only when the well
  // is open AND the treatment textarea has prose.
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [proposedPrd, setProposedPrd] = useState<string>("");
  // R2 #167/#183: presentational-only stimulus designator. It names the
  // stimulus in the reading manifest; it is NOT part of the submit
  // payload (MVP stimuli live on the Hypothesis as prose + proposed_prd —
  // DESIGN.md §7.6).
  const [stimName, setStimName] = useState<string>("");
  // Phase 4.6 #88: A/B experiment mode toggle. When on, the request gets
  // `arm_split: { treatment_fraction: 0.5 }` and the simulator runs both
  // a treatment arm (sees the proposed change) and a control arm (sees
  // the current product). Cost is ~2× single-arm.
  //
  // Wizard ships v1 with treatment_fraction baked at 0.5 (paired sampling
  // makes other splits statistically wasteful per docs/4.6 Q3). The
  // schema accepts other values for future flexibility.
  //
  // Phase 4.6 staged rollout gate: #89 wires the dual-arm runner
  // (composer → orchestrator → dual-arm allocation → arm-tagged
  // AgentInstance rows), but ScoringService still runs the
  // single-arm path. If we enabled the toggle now, the result page
  // would render confidence_score over a mixed treatment+control
  // cohort — a number that looks like predicted lift but isn't.
  // Codex P1 on PR #95 flagged this; we re-gate until #90 (paired
  // lift formula) + #91 (lift display on result page) land.
  // Direct API still accepts arm_split for #89's dual-arm runner
  // tests — only the wizard UI is locked.
  // Phase 4.6 #91 (2026-05-26): flipped to false. #90 (paired lift formula)
  // + #91 (result-page lift card + arm-split table) are both on main, so
  // the wizard A/B toggle now produces a result the PM can read end-to-end.
  // Keep the constant + the staged-rollout note plumbing so a future
  // emergency rollback is a one-line flip.
  const AB_MODE_DISABLED_UNTIL_LIFT = false;
  const [abMode, setAbMode] = useState(false);

  // #279: OPTIONAL per-metric outcome elicitation. The backend
  // (services.metric_registry / schemas.simulation.Hypothesis) supports a
  // structured target metric ALONGSIDE the sentiment confidence_score. None =
  // today's sentiment-only behavior and is the default — when `metricName` is
  // null the submit payload carries no metric_name and is byte-identical to a
  // pre-#279 request.
  //
  // #313 / T4: the picker is NO LONGER gated to A/B mode. The answerability
  // gate (epic #309 T1) blocks a run with `oec_undeclared` whenever no
  // `metric_name` is declared, regardless of arm count — so a single-arm run
  // must be able to declare an OEC to clear that block. The picker is now
  // offered in both modes; the metric-lift DELTA is still A/B-only (a paired
  // treatment − control number), but the OEC declaration itself is mode-free.
  const [metricName, setMetricName] = useState<MetricName>(null);
  // The metric's in-character template fields. `conversionAction` /
  // `conversionActionLabel` reuse the generic Hypothesis label fields the
  // registry reads for every metric (conversion: action + label; retention:
  // the "return" label via conversion_action_label; ctr: the click label via
  // conversion_action_label). `decisionPoint` is required by every registered
  // metric. `choiceSet` is optional (one alternative per line) — empty falls
  // back to the metric's registry default choice set.
  const [conversionAction, setConversionAction] = useState<string>("");
  const [conversionActionLabel, setConversionActionLabel] = useState<string>("");
  const [decisionPoint, setDecisionPoint] = useState<string>("");
  const [choiceSetText, setChoiceSetText] = useState<string>("");

  // The "confirm-if-large" threshold from docs/4.6 Q4. When total agents
  // (across both arms) exceeds this, the PM gets an explicit
  // acknowledgement step before submit.
  const CONFIRM_TOTAL_AGENTS_THRESHOLD = 100;
  const [acknowledgedLargeRun, setAcknowledgedLargeRun] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  // #313 / T4 (deliverable 3 — the deploy-unblocker): when POST /simulations
  // returns the epic #309 T1 needs_input 422, the parsed detail lands here so
  // the wizard renders the named reasons + fixes inline as authoring guidance
  // (never a dead-end) and, when `allow_override`, offers a one-tap "run anyway
  // as generic reception" affordance that resubmits with the override flag.
  const [needsInput, setNeedsInput] = useState<NeedsInputDetail | null>(null);
  // "Begin reading" lives at the bottom of the manifest rail, but the gate /
  // validation banners render at the top of the form. Without this, a gated
  // submit (e.g. oec_undeclared) silently paints a banner off-screen and the
  // button looks dead. Scroll the alert region into view and focus it (the
  // WCAG error-summary pattern) whenever a blocking message appears.
  const alertRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (needsInput || validationError || submitError) {
      // Honor prefers-reduced-motion — the theme disables other motion for it,
      // so a smooth bottom-to-top jump would be an out-of-place vestibular risk.
      const reduceMotion =
        typeof window !== "undefined" &&
        window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
      alertRef.current?.scrollIntoView({
        behavior: reduceMotion ? "auto" : "smooth",
        block: "center",
      });
      alertRef.current?.focus({ preventScroll: true });
    }
  }, [needsInput, validationError, submitError]);
  // #313 / T4 (deliverable 4 — inline lint): the deterministic, zero-LLM
  // POST /simulations/preflight verdict, refreshed (debounced) as the user
  // authors. It surfaces the SAME answerability reasons/fixes + the separable
  // leading-framing lint BEFORE submit, so authoring guidance is live.
  const [preflight, setPreflight] = useState<PreflightResponse | null>(null);
  const [preflightStale, setPreflightStale] = useState(false);

  const [models, setModels] = useState<ModelInfo[]>([]);
  const [defaultModelId, setDefaultModelId] = useState<string | null>(null);
  const [selectedModelId, setSelectedModelId] = useState<string>("");
  const [loadingModels, setLoadingModels] = useState(true);
  const [modelsError, setModelsError] = useState<string | null>(null);

  const [simulationLimits, setSimulationLimits] =
    useState<SimulationLimitsResponse | null>(null);
  const [loadingLimits, setLoadingLimits] = useState(true);
  const [limitsError, setLimitsError] = useState<string | null>(null);

  // Phase 5 #101: persona filter. Default = all personas selected (today's
  // behavior). PM can deselect individual personas (R2: filter chips in
  // 03 · Cohort, always visible) to run against a narrowed cohort. Submit
  // payload sends `selected_personas: null` when the full set is checked
  // (matches the backend's "None = all" convention and keeps the persisted
  // row tidy); sends an explicit subset when narrowed.
  const [activePersonas, setActivePersonas] = useState<PersonaSummary[]>([]);
  const [packVersion, setPackVersion] = useState<string | null>(null);
  const [loadingPersonas, setLoadingPersonas] = useState(true);
  const [personasError, setPersonasError] = useState<string | null>(null);
  const [selectedPersonas, setSelectedPersonas] = useState<Set<string>>(
    new Set(),
  );

  // #215/#245 PR 3b: load the org's crawl setups once. Non-fatal — if the list
  // call fails or returns only the default anchor, the picker stays hidden and
  // the wizard runs against "default" exactly as before this PR.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const rows = await listCrawlSetups();
        if (cancelled) return;
        setSetups(rows);
        // Default the selection to the "default" anchor when present (the
        // common case), else the first setup — so the capability load below
        // always targets a setup that exists.
        if (rows.length > 0 && !rows.some((r) => r.setup_id === DEFAULT_SETUP_ID)) {
          setSetupId(rows[0].setup_id);
        }
      } catch (e) {
        if (cancelled) return;
        // Don't silently route a possibly-multi-setup org to "default" — record
        // the failure so the wizard can disclose it. The run still targets the
        // default anchor (the safe legacy behavior); a default-only org's
        // experience is unchanged because the note only renders on error.
        setSetupsError(
          e instanceof Error ? e.message : "could not list crawl setups",
        );
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Capabilities are scoped to the SELECTED setup (#215/#245 PR 3b). Re-runs
  // when the setup changes so switching setups re-lists THAT setup's pack. An
  // omitted/`"default"` id keeps the request byte-identical to pre-#215 prod.
  useEffect(() => {
    let cancelled = false;
    setLoadingCaps(true);
    setCapsError(null);
    setCapsNotFound(false);
    setCapability("");
    (async () => {
      try {
        const m = await getCapabilities(false, setupId);
        if (cancelled) return;
        setManifest(m);
        if (m.capabilities && m.capabilities.length > 0) {
          setCapability(m.capabilities[0]);
        }
      } catch (e) {
        if (cancelled) return;
        setManifest(null);
        if (e instanceof ApiError) {
          if (e.status === 404) setCapsNotFound(true);
          setCapsError(
            e.status === 404
              ? "No capabilities found for this setup. Run a crawl first."
              : `Failed to load capabilities: ${e.message}`,
          );
        } else if (e instanceof Error) {
          setCapsError(`Failed to load capabilities: ${e.message}`);
        } else {
          setCapsError("Failed to load capabilities.");
        }
      } finally {
        if (!cancelled) setLoadingCaps(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [setupId]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const resp = await listSupportedModels();
        if (cancelled) return;
        setModels(resp.models);
        setDefaultModelId(resp.default_model_id);
        const selected =
          resp.models.find((m) => m.is_default)?.id ??
          resp.models[0]?.id ??
          "";
        setSelectedModelId(selected);
      } catch (e) {
        if (cancelled) return;
        if (e instanceof Error) {
          setModelsError(`Could not load model list: ${e.message}`);
        } else {
          setModelsError("Could not load model list.");
        }
      } finally {
        if (!cancelled) setLoadingModels(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const resp = await getSimulationLimits();
        if (cancelled) return;
        setSimulationLimits(resp);
      } catch (e) {
        if (cancelled) return;
        if (e instanceof Error) {
          setLimitsError(`Could not load simulation limits: ${e.message}`);
        } else {
          setLimitsError("Could not load simulation limits.");
        }
      } finally {
        if (!cancelled) setLoadingLimits(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Phase 5 #101: load the active Persona Pack on mount so the filter
  // chip list has names + weights. Default = all selected.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const resp: ActivePersonasResponse = await getActivePersonas();
        if (cancelled) return;
        setActivePersonas(resp.personas);
        setPackVersion(resp.pack_version);
        setPersonasAreStarter(resp.is_starter ?? false);
        setSelectedPersonas(new Set(resp.personas.map((p) => p.id)));
      } catch (e) {
        if (cancelled) return;
        // Non-fatal: hide the filter UI, fall back to "all personas"
        // (selected_personas: null on submit).
        if (e instanceof ApiError && e.status === 404) {
          setPersonasNotFound(true);
        }
        if (e instanceof Error) {
          setPersonasError(`Could not load personas: ${e.message}`);
        } else {
          setPersonasError("Could not load personas.");
        }
      } finally {
        if (!cancelled) setLoadingPersonas(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const capabilities = manifest?.capabilities ?? [];
  const hasCapabilities = capabilities.length > 0;

  // Inherit the parent's capability once the feature pack has loaded — a
  // capability can only be selected if it exists in THIS setup's pack. Guarded
  // so a later manual change is never overwritten. If the parent's capability
  // isn't in the pack (e.g. the setup changed), we leave the default selection.
  // Placed here (after `capabilities` is derived) so it sees the loaded pack.
  useEffect(() => {
    if (appliedInheritedCapability.current) return;
    const want = inheritedHypothesis?.capability_name;
    if (!want) return;
    if (capabilities.length === 0) return;
    appliedInheritedCapability.current = true;
    if (capabilities.includes(want)) setCapability(want);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inheritedHypothesis, capabilities]);
  // #215/#245 PR 3b: the setup picker only appears when the org actually has
  // more than one crawl setup. A default-only org sees no new control.
  const hasMultipleSetups = setups.length > 1;
  const setupLabelFor = (s: CrawlSetupListItem): string =>
    s.name?.trim() ||
    (s.setup_id === DEFAULT_SETUP_ID ? "Default setup" : s.setup_id);
  const activePerArmCap = simulationLimits?.max_agents_per_arm ?? null;
  // Realized agents per arm = min(modeled population, user-requested agent
  // count, env cap). `requestedAgentCount == null` (empty field) means "use the
  // cap" — the historical derive-from-population behavior. Null when inputs
  // aren't ready (population blank or limits unloaded) so callers can fall back
  // to a loading/placeholder state. Single source of truth for the display +
  // the A/B cost calc so they can't drift.
  const realizedAgentCount =
    populationSize != null && populationSize > 0 && activePerArmCap != null
      ? Math.min(
          populationSize,
          requestedAgentCount ?? activePerArmCap,
          activePerArmCap,
        )
      : null;
  const formDisabled =
    loadingCaps ||
    loadingModels ||
    loadingLimits ||
    simulationLimits == null ||
    !hasCapabilities ||
    submitting;
  // Phase 5 #101: derive filter state.
  const totalPersonaCount = activePersonas.length;
  const selectedCount = selectedPersonas.size;
  const allPersonasSelected =
    totalPersonaCount > 0 && selectedCount === totalPersonaCount;
  const noPersonasSelected = totalPersonaCount > 0 && selectedCount === 0;

  // #313 / T4: the OEC metric declaration is no longer A/B-gated (see the
  // metricName state note). A metric declared in either mode satisfies the
  // answerability gate's `oec_undeclared` check; the paired metric-lift DELTA
  // is still only meaningful (and computed) in A/B mode.
  const effectiveMetric: MetricName = metricName;

  // #313 / T4: single source of truth for the Hypothesis payload, shared by
  // the live preflight lint and the real submit so the inline guidance matches
  // exactly what the create path will route on. Returns null when the claim
  // prose is too short to assess (the field-level validators handle that).
  function buildHypothesis(): Hypothesis | null {
    const prose = composedProse.trim();
    if (!capability || prose.length < 20) return null;

    // Mirror the registry's required-template-fields contract (see
    // REQUIRED_METRIC_FIELDS) — same assembly the pre-#313 submit used, now
    // mode-free for the declaration. choice_set is one alternative per line.
    let metricFields: Partial<Hypothesis> = {};
    if (effectiveMetric) {
      const choiceSet = choiceSetText
        .split("\n")
        .map((s) => s.trim())
        .filter((s) => s.length > 0);
      metricFields = {
        metric_name: effectiveMetric,
        decision_point: decisionPoint.trim(),
        choice_set: choiceSet,
      };
      if (effectiveMetric === "conversion") {
        metricFields.conversion_action = conversionAction.trim();
        metricFields.conversion_action_label = conversionActionLabel.trim();
      } else if (conversionActionLabel.trim()) {
        metricFields.conversion_action_label = conversionActionLabel.trim();
      }
    }

    return {
      capability_name: capability,
      prose,
      proposed_prd:
        showAdvanced && proposedPrd.trim() ? proposedPrd.trim() : null,
      // The wizard has no figma authoring path (#183), but a refinement inherits
      // the parent's proposed_figma so a figma-bearing parent stays answerable —
      // thread it into the payload (null for a normal, non-refinement create).
      proposed_figma: inheritedFigma.current,
      ...metricFields,
    };
  }

  // #313 / T4 (deliverable 4): live inline lint. Debounced POST /preflight as
  // the claim / metric fields change. Deterministic + zero-LLM + no persist
  // (the backend endpoint runs ONLY assess_answerability + the separable
  // leading-framing lint), so it is safe to call on every authoring pause.
  // `run_as_generic_reception` is intentionally NOT sent here — the preview
  // reflects the un-overridden state so the guidance shows what to fix; the
  // override is an explicit post-submit choice (deliverable 3).
  const preflightProse = composedProse.trim();
  const preflightMetric = effectiveMetric;
  const preflightDecision = decisionPoint.trim();
  const preflightConvAction = conversionAction.trim();
  const preflightConvLabel = conversionActionLabel.trim();
  const preflightChoice = choiceSetText;
  useEffect(() => {
    const hyp = buildHypothesis();
    if (!hyp) {
      setPreflight(null);
      setPreflightStale(false);
      return;
    }
    setPreflightStale(true);
    let cancelled = false;
    const handle = setTimeout(async () => {
      try {
        const resp = await preflightSimulation({ hypothesis: hyp });
        if (!cancelled) {
          setPreflight(resp);
          setPreflightStale(false);
        }
      } catch {
        // Preflight is advisory — a transient failure must never block
        // authoring. Drop the stale verdict and let the user submit; the POST
        // path's own 422 (deliverable 3) is the authoritative gate.
        if (!cancelled) {
          setPreflight(null);
          setPreflightStale(false);
        }
      }
    }, 450);
    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    capability,
    preflightProse,
    preflightMetric,
    preflightDecision,
    preflightConvAction,
    preflightConvLabel,
    preflightChoice,
    showAdvanced,
    proposedPrd,
  ]);

  // #313 / T4: build the create payload once, shared by the normal submit and
  // the needs_input override resubmit. `runAsGenericReception` threads the
  // epic #309 T1 override flag onto the request (the field name is supplied by
  // the 422 payload's `override_field`, but it is always
  // `run_as_generic_reception` for this gate). Returns null when a field-level
  // validation fails (it sets the validation error itself).
  function buildRequest(runAsGenericReception: boolean): SimulationRequest | null {
    if (!capability) {
      setValidationError("Please select a capability.");
      return null;
    }
    const hyp = buildHypothesis();
    if (!hyp) {
      setValidationError(
        claimMode === "structured"
          ? "Fill in the change and the expected metric — the composed claim must be at least 20 characters."
          : "Hypothesis must be at least 20 characters of prose.",
      );
      return null;
    }
    if (
      populationSize == null ||
      populationSize < 1 ||
      populationSize > 10_000
    ) {
      setValidationError("Population must be between 1 and 10,000.");
      return null;
    }
    // Agent count is optional (empty = use the backend cap). But a non-empty
    // field that isn't a whole number ≥ 1 is a typo, not "use the cap" —
    // surface it inline rather than silently falling back or letting a 0 reach
    // the backend (schema ge=1) as a raw 422. parsePositiveInt("0") returns 0,
    // so guard `< 1` explicitly, mirroring the population check above.
    if (
      agentCountInput.trim() !== "" &&
      (requestedAgentCount == null || requestedAgentCount < 1)
    ) {
      setValidationError("Agents must be a whole number of at least 1.");
      return null;
    }
    // Phase 5 #101: if the persona pack loaded and the PM cleared every
    // chip, refuse to submit -- the API would 422 and the wizard
    // shouldn't trip that.
    if (totalPersonaCount > 0 && noPersonasSelected) {
      setValidationError(
        "Select at least one persona to run the simulation against.",
      );
      return null;
    }
    if (activePerArmCap == null) {
      setValidationError(
        "Simulation limits are unavailable. Reload after the backend is reachable.",
      );
      return null;
    }

    // Phase 4.6 #88: when A/B mode is on, total agents = 2 × per_arm.
    // The PM has to acknowledge the cost if total exceeds the threshold. The
    // per-arm count honors the optional agent-count knob (min of population,
    // request, cap) so the acknowledgement reflects the real LLM fan-out.
    const perArmAgents = Math.min(
      populationSize,
      requestedAgentCount ?? activePerArmCap,
      activePerArmCap,
    );
    const totalAgents = abMode ? 2 * perArmAgents : perArmAgents;
    if (
      abMode &&
      totalAgents > CONFIRM_TOTAL_AGENTS_THRESHOLD &&
      !acknowledgedLargeRun
    ) {
      setValidationError(
        `This A/B run uses ≈ ${totalAgents} LLM agents (2× a single-arm sim). Tick the acknowledgement below to continue.`,
      );
      return null;
    }

    // #279: when a metric is selected, the registry's required template fields
    // must be non-empty — mirror the backend's `Hypothesis._validate_metric`
    // (driven by `required_template_fields`) so the wizard never trips the
    // API's 422. #313: the metric is now mode-free, so validate whenever one
    // is declared (not only in A/B mode).
    const metricFieldValues: Record<MetricFieldName, string> = {
      conversion_action: conversionAction,
      conversion_action_label: conversionActionLabel,
      decision_point: decisionPoint,
    };
    if (effectiveMetric) {
      const missing = REQUIRED_METRIC_FIELDS[effectiveMetric].filter(
        (f) => !metricFieldValues[f].trim(),
      );
      if (missing.length > 0) {
        setValidationError(
          `${METRIC_LABELS[effectiveMetric]} needs ${missing
            .map((f) => METRIC_FIELD_LABELS[f])
            .join(", ")}.`,
        );
        return null;
      }
    }

    // Phase 5 #101: send `selected_personas: null` when:
    //   (1) ALL personas are checked (= "no filter"), OR
    //   (2) the /personas fetch hasn't loaded yet / failed, so we don't
    //       know the full set and the PM can't actually be filtering --
    //       falling back to "null = all personas" is the correct
    //       backwards-compat behavior. (codex R1-P2 on #101)
    const personaFilter: string[] | null =
      totalPersonaCount === 0 || allPersonasSelected
        ? null
        : Array.from(selectedPersonas);

    return {
      hypothesis: hyp,
      population_size: populationSize,
      // Only send the agent-count knob when the user set it; omitting it keeps
      // the payload byte-identical to a pre-knob request (backend derives the
      // sample from the cap). The backend re-clamps to the env ceiling.
      ...(requestedAgentCount != null
        ? { sampled_agent_count: requestedAgentCount }
        : {}),
      arm_split: abMode ? { treatment_fraction: 0.5 } : null,
      selected_personas: personaFilter,
      model_id: selectedModelId || null,
      // #215/#245 PR 3b: target the selected crawl setup. Only sent for a
      // non-default setup so a default-only run is byte-identical to a
      // pre-#215 request (the backend defaults setup_id to "default").
      ...(setupId && setupId !== DEFAULT_SETUP_ID
        ? { setup_id: setupId }
        : {}),
      // #44: link the new run to its parent when the wizard was opened from a
      // refinement "Try this" CTA. Omitted otherwise, so a normal create is
      // byte-identical to a pre-#479 request.
      ...(parentSimulationId.current
        ? { parent_simulation_id: parentSimulationId.current }
        : {}),
      // #313 / T4: the epic #309 T1 override. Only set when the user took the
      // explicit "run anyway as generic reception" affordance; otherwise the
      // payload is byte-identical to a pre-#313 request (false is the default
      // and the gate treats absent === false).
      ...(runAsGenericReception
        ? { run_as_generic_reception: true }
        : {}),
    } as SimulationRequest;
  }

  // Shared create + routing, used by both the normal submit and the override
  // resubmit. Parses the epic #309 T1 needs_input 422 into inline guidance
  // (deliverable 3) rather than dumping a raw error string.
  async function submitRequest(req: SimulationRequest) {
    setSubmitting(true);
    try {
      const res = await createSimulation(req);
      router.push(`/simulations/${res.id}`);
    } catch (e) {
      if (e instanceof ApiError) {
        const detail = e.body ? parseNeedsInput(e.body) : null;
        if (detail) {
          // refinement guarantee: a refinement must NEVER hard-block. If the
          // #309 gate fires on a refinement run that wasn't already overridden,
          // auto-resubmit ONCE with the generic-reception override so Begin
          // reading always runs (the client-side answerability proxy may miss
          // an edge the backend gate catches). This is refinement-only — a
          // normal create still surfaces the inline guidance + explicit "run
          // anyway" affordance unchanged.
          if (
            isRefinement &&
            detail.allow_override &&
            req.run_as_generic_reception !== true
          ) {
            await submitRequest({ ...req, run_as_generic_reception: true });
            return;
          }
          // The deploy-unblocker: surface the named reasons + fixes inline as
          // authoring guidance, NOT a dead-end. The override affordance (when
          // allow_override) lets the user resubmit as generic reception.
          setNeedsInput(detail);
          setSubmitError(null);
        } else {
          setSubmitError(
            `Submission failed (HTTP ${e.status}): ${e.body || e.message}`,
          );
        }
      } else if (e instanceof Error) {
        setSubmitError(`Submission failed: ${e.message}`);
      } else {
        setSubmitError("Submission failed.");
      }
      setSubmitting(false);
    }
  }

  // refinement answerability fallback: a refinement must ALWAYS be runnable on
  // Begin reading (never hard-block at the #309 gate). The inherited structured
  // context makes an answerable parent answerable; but if the current hypothesis
  // carries no representable OEC, no inherited figma, and no proposed_prd (e.g.
  // the parent ran sentiment-only, or the OEC was the unrepresentable "visit"),
  // we submit with run_as_generic_reception so the gate doesn't 422. Mirrors the
  // backend's answerability check client-side. Non-refinement creates are
  // unaffected (this is false for them, preserving the explicit-override path).
  // The PM can still upgrade a sentiment-only refinement by adding an OEC — once
  // a metric is declared this returns false and the run is calibrated, not
  // generic.
  function refinementNeedsGenericOverride(): boolean {
    if (!isRefinement) return false;
    const hasOec = effectiveMetric != null;
    const hasFigma = inheritedFigma.current != null;
    const hasPrd = showAdvanced && proposedPrd.trim().length > 0;
    return !hasOec && !hasFigma && !hasPrd;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    setValidationError(null);
    setNeedsInput(null);

    const req = buildRequest(refinementNeedsGenericOverride());
    if (!req) return;
    await submitRequest(req);
  }

  // #313 / T4 (deliverable 3): the "run anyway as generic reception" override.
  // Resubmits the SAME request with the gate's override field set, clearing the
  // needs_input guidance first so the user sees the run start, not stale text.
  async function handleRunAnyway() {
    setNeedsInput(null);
    setSubmitError(null);
    setValidationError(null);
    const req = buildRequest(true);
    if (!req) return;
    await submitRequest(req);
  }

  // R2 #167: live manifest values — every row is a real, currently-configured
  // value (DESIGN.md §8: no decorative furniture, no copy thresholds). The
  // per-arm preview honors the optional agent-count knob via realizedAgentCount.
  const perArmPreview = realizedAgentCount;
  const manifestRows: Array<[string, string]> = [
    ["Designator", "DRAFT · UNCOMMITTED"],
    ["Mode", abMode ? "A/B — PAIRED" : "SINGLE ARM"],
    // Only surface the setup row when there's a choice to make — a default-only
    // org's manifest is unchanged (#215/#245 PR 3b).
    ...(hasMultipleSetups
      ? ([["Setup", setupId]] as Array<[string, string]>)
      : []),
    ["Capability", capability || "—"],
    [
      "Slice",
      manifest != null
        ? `${manifest.snapshot_version} · FREEZES AT RUN`
        : "—",
    ],
    [
      "Stimulus",
      showAdvanced
        ? `${stimName.trim() || "untitled"} · NEW · ${
            abMode ? "2 ARMS" : "1 ARM"
          }`
        : "CLAIM TEXT ONLY",
    ],
    [
      "Cohort",
      packVersion != null && totalPersonaCount > 0
        ? `${packVersion} · ${selectedCount} OF ${totalPersonaCount}`
        : "ALL PERSONAS",
    ],
    [
      "Metric",
      metricName
        ? abMode
          ? `${METRIC_LABELS[metricName].toUpperCase()} LIFT · PAIRED`
          : `${METRIC_LABELS[metricName].toUpperCase()} · OEC`
        : "SENTIMENT ONLY",
    ],
    [
      "Population",
      populationSize != null && populationSize > 0
        ? `${populationSize.toLocaleString()} · HAMILTON`
        : "—",
    ],
    [
      "Agents",
      perArmPreview != null
        ? abMode
          ? `${perArmPreview} × 2 ARMS = ${2 * perArmPreview}`
          : `${perArmPreview} SAMPLED`
        : "—",
    ],
    ["Model", selectedModelId || "BACKEND DEFAULT"],
  ];

  // #337 / T6: glanceable completeness — deterministic, display-only, never fed
  // to any score/decision. Derived from form state + the SAME live preflight
  // verdict the inline lint already fetched (no second call).
  const completenessItems = deriveCompleteness({
    claimMode,
    claimChange,
    claimCohort,
    claimMetric,
    freeText: hypothesis,
    metricName,
    showAdvanced,
    proposedPrd,
    preflight,
    preflightStale,
  });

  return (
    <AppShellV2
      activeNav="simulations"
      title="New hypothesis"
      surface="console"
    >
      <div className="rconsole">
        <style>{RCONSOLE_CSS}</style>
        <main
          className="fullbleed-main"
          style={{
            fontFamily: FONT_SANS,
            color: TOKENS.ink,
            // break out of the .v2-appmain section padding so the wizard's own
            // hairline-bordered header strip + two-zone form span the console
            // main edge-to-edge, exactly as the mock's full-bleed work area.
            // Margin lives in .fullbleed-main (RCONSOLE_CSS) so it tracks the
            // shell's responsive padding at the ≤1024px breakpoint (codex P2).
          }}
        >
          {/* Page strip — hypothesis-header zone (DESIGN.md §7) */}
      <header
        style={{
          padding: "20px 24px 16px",
          borderBottom: `0.75px solid ${TOKENS.rule}`,
          display: "flex",
          alignItems: "baseline",
          gap: 16,
        }}
      >
        <h1
          style={{
            margin: 0,
            fontSize: 20,
            fontWeight: 600,
            letterSpacing: "-0.01em",
          }}
        >
          New hypothesis
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
          DRAFT · COMMITS ON BEGIN READING
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
          READINGS ARE PAIRED BY PERSONA + SEED
        </span>
      </header>

      {/* Two-zone panel: evidence form + reading-manifest inspector rail */}
      <form
        onSubmit={handleSubmit}
        style={{ display: "flex", alignItems: "stretch", margin: 0 }}
      >
        <div style={{ flex: 1, minWidth: 0, padding: 24 }}>
          {loadingCaps && (
            <div style={{ color: TOKENS.inkMuted, fontSize: 14 }}>
              Loading capabilities...
            </div>
          )}

          {!loadingCaps && capsError && (
            <div style={emptyStateStyle}>
              <strong>{capsError}</strong>
            </div>
          )}

          {/* sessions/sample-workspace: both packs missing = empty tenant. A
              starter pack (#212) counts as "no real personas yet". */}
          {!loadingCaps &&
            !loadingPersonas &&
            capsNotFound &&
            (personasNotFound || personasAreStarter) && <SampleWorkspaceCard />}

          {!loadingCaps && !capsError && !hasCapabilities && (
            <div style={emptyStateStyle}>
              <strong>
                No capabilities found for this customer. Run a crawl first.
              </strong>
            </div>
          )}

          {/* Ref'd, focusable alert region: a gated/invalid "Begin reading"
              scrolls this into view (see the alertRef effect) so the message is
              never painted off-screen below the fold. tabIndex=-1 lets it take
              focus without becoming a tab stop. */}
          <div ref={alertRef} tabIndex={-1} style={{ outline: "none" }}>
            {(submitError || validationError) && (
              <div role="alert" style={errorBannerStyle}>
                {submitError ?? validationError}
              </div>
            )}

            {/* #313 / T4 (deliverable 3 — the deploy-unblocker): the epic #309
                T1 needs_input 422 rendered as inline authoring guidance, NOT a
                dead-end. §7.7 disclosure anatomy (rule border, paper-recessed,
                message in ink). When allow_override, the "run anyway as generic
                reception" affordance resubmits with the override flag. */}
            {needsInput && (
              <NeedsInputNote
                detail={needsInput}
                submitting={submitting}
                onRunAnyway={handleRunAnyway}
                onDismiss={() => setNeedsInput(null)}
              />
            )}
          </div>

          <div
            style={{
              maxWidth: 620,
              opacity: formDisabled && !submitting ? 0.6 : 1,
            }}
          >
            {/* ── 01 · Claim ─────────────────────────────── */}
            {/* #313 / T4: structured falsifiable-claim authoring is the
                default (deliverable 1). The four fields compose into the prose
                the API expects via composeClaimProse; the free-text toggle is
                the escape hatch so a terse expert claim is never
                over-constrained. The live preflight lint (deliverable 4)
                renders below as §7.7 disclosure notes. */}
            <section>
              <div
                style={{
                  ...sectionLabelStyle,
                  display: "flex",
                  alignItems: "baseline",
                  justifyContent: "space-between",
                }}
              >
                <span>01 · Claim</span>
                <button
                  type="button"
                  onClick={() =>
                    setClaimMode((m) =>
                      m === "structured" ? "freetext" : "structured",
                    )
                  }
                  disabled={formDisabled}
                  style={claimModeToggleStyle}
                >
                  {claimMode === "structured"
                    ? "Free-text instead →"
                    : "← Guided fields"}
                </button>
              </div>

              {claimMode === "structured" ? (
                <>
                  <div style={fieldStyle}>
                    <label htmlFor="claim-change" style={sublabelStyle}>
                      If we change…
                    </label>
                    <input
                      id="claim-change"
                      type="text"
                      value={claimChange}
                      onChange={(e) => setClaimChange(e.target.value)}
                      disabled={formDisabled}
                      placeholder="e.g. surface a one-tap reorder CTA on the home screen"
                      style={inputStyle}
                    />
                    <div style={hintStyle}>
                      The concrete product change agents react to — be specific
                      about what is different.
                    </div>
                  </div>
                  <div style={fieldStyle}>
                    <label htmlFor="claim-cohort" style={sublabelStyle}>
                      For — cohort (optional)
                    </label>
                    <input
                      id="claim-cohort"
                      type="text"
                      value={claimCohort}
                      onChange={(e) => setClaimCohort(e.target.value)}
                      disabled={formDisabled}
                      placeholder="e.g. users who ordered in the last 14 days"
                      style={inputStyle}
                    />
                    <div style={hintStyle}>
                      Who the change targets. Leave blank for a product-wide
                      change.
                    </div>
                  </div>
                  <div style={{ ...fieldStyle, ...fieldRowStyle }}>
                    <div style={{ minWidth: 0 }}>
                      <label htmlFor="claim-metric" style={sublabelStyle}>
                        Then — outcome metric
                      </label>
                      <input
                        id="claim-metric"
                        type="text"
                        value={claimMetric}
                        onChange={(e) => setClaimMetric(e.target.value)}
                        disabled={formDisabled}
                        placeholder="e.g. weekly reorder rate"
                        style={inputStyle}
                      />
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <label htmlFor="claim-direction" style={sublabelStyle}>
                        Direction
                      </label>
                      <select
                        id="claim-direction"
                        value={claimDirection}
                        onChange={(e) =>
                          setClaimDirection(
                            e.target.value as ClaimDirection,
                          )
                        }
                        disabled={formDisabled}
                        style={selectStyle}
                      >
                        <option value="increases">increases</option>
                        <option value="decreases">decreases</option>
                        <option value="changes">changes</option>
                      </select>
                    </div>
                  </div>
                  <div style={hintStyle}>
                    The observable outcome the claim predicts moves — this is
                    what the verdict prints against.
                  </div>
                  {/* Live composed preview — the exact prose the API receives. */}
                  <div style={composedPreviewStyle}>
                    <div style={composedPreviewLabelStyle}>Composed claim</div>
                    <div style={composedPreviewBodyStyle}>
                      {composedProse ||
                        "Fill in the change and outcome metric to compose the claim."}
                    </div>
                  </div>
                </>
              ) : (
                <div style={fieldStyle}>
                  <label htmlFor="hypothesis" style={sublabelStyle}>
                    Hypothesis — free text
                  </label>
                  <textarea
                    id="hypothesis"
                    value={hypothesis}
                    onChange={(e) => setHypothesis(e.target.value)}
                    disabled={formDisabled}
                    rows={3}
                    placeholder="e.g. If we surface a one-tap reorder CTA on the home screen for users who ordered in the last 14 days, weekly reorder rate will increase."
                    style={{
                      ...inputStyle,
                      resize: "vertical",
                      lineHeight: 1.45,
                    }}
                  />
                  <div style={hintStyle}>
                    State a falsifiable prediction — be specific about who and
                    what, since the verdict prints against it. Guided fields
                    enforce the falsifiable shape if you prefer.
                  </div>
                </div>
              )}

              {/* #313 / T4 (deliverable 4): live inline answerability lint. */}
              <ClaimLintNotes preflight={preflight} stale={preflightStale} />
            </section>

            {/* ── 02 · Subject ───────────────────────────── */}
            <section style={sectionStyle}>
              <div style={sectionLabelStyle}>02 · Subject</div>
              {/* #215/#245 PR 3b: crawl-setup target. Shown only when the org
                  has >1 setup; a default-only org sees no new control (the
                  capability picker is the first field, exactly as today). */}
              {hasMultipleSetups && (
                <div style={fieldStyle}>
                  <label htmlFor="setup" style={sublabelStyle}>
                    Crawl setup
                  </label>
                  {/* Setup names are user-authored prose, not machine
                      designators — render in the body font (§5.4), unlike the
                      capability/model selects which carry machine slugs. */}
                  <select
                    id="setup"
                    value={setupId}
                    onChange={(e) => setSetupId(e.target.value)}
                    disabled={loadingCaps || submitting}
                    style={inputStyle}
                  >
                    {setups.map((s) => (
                      <option key={s.setup_id} value={s.setup_id}>
                        {setupLabelFor(s)}
                        {s.setup_id === DEFAULT_SETUP_ID ? " · default" : ""}
                      </option>
                    ))}
                  </select>
                  <div style={hintStyle}>
                    Which crawl setup&rsquo;s feature pack this run reads as the
                    as-built control. The capabilities below are this
                    setup&rsquo;s.
                  </div>
                </div>
              )}
              {/* Honest disclosure: the roster fetch failed, so the run targets
                  the default setup. Never blocks (a multi-setup org can still
                  run default); a default-only org never reaches this. */}
              {setupsError && (
                <div style={{ ...warnNoteStyle, marginTop: 14 }}>
                  Could not load this org&rsquo;s crawl setups
                  {hasMultipleSetups ? "" : " — this run will target the default setup"}.
                  Reload to choose a different setup. ({setupsError})
                </div>
              )}
              <div style={{ ...fieldStyle, ...fieldRowStyle }}>
                <div style={{ minWidth: 0 }}>
                  <label htmlFor="capability" style={sublabelStyle}>
                    Capability under test
                  </label>
                  <select
                    id="capability"
                    value={capability}
                    onChange={(e) => setCapability(e.target.value)}
                    disabled={formDisabled}
                    required
                    style={selectStyle}
                  >
                    {!hasCapabilities && (
                      <option value="">(no capabilities)</option>
                    )}
                    {capabilities.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                  <div style={hintStyle}>
                    From the feature pack — agents read its as-built capability
                    as context.
                  </div>
                </div>
                <div style={{ minWidth: 0 }}>
                  <label htmlFor="stimulus" style={sublabelStyle}>
                    Stimulus
                  </label>
                  <select
                    id="stimulus"
                    value={showAdvanced ? "new" : "prose"}
                    onChange={(e) => {
                      if (e.target.value === "new") {
                        setShowAdvanced(true);
                      } else {
                        // Closing the well clears its draft so a hidden
                        // treatment never silently applies at submit
                        // (same invariant as the old Advanced disclosure).
                        setShowAdvanced(false);
                        setProposedPrd("");
                        setStimName("");
                      }
                    }}
                    disabled={formDisabled}
                    style={selectStyle}
                  >
                    <option value="prose">Claim text only — no PRD delta</option>
                    <option value="new">+ new stimulus…</option>
                  </select>
                  <div style={hintStyle}>
                    What agents react to. By default they read the claim above
                    as-is; a new stimulus adds a PRD-delta describing the
                    proposed change.
                  </div>
                </div>
              </div>

              {/* Inline stimulus authoring well — disclosure, not a modal.
                  The fields live on the Hypothesis (proposed_prd). */}
              {showAdvanced && (
                <div
                  style={{
                    marginTop: 14,
                    padding: "16px 16px 14px",
                    border: `1px dashed ${TOKENS.rule}`,
                    borderRadius: 2,
                    background: TOKENS.paper,
                  }}
                >
                  <div style={fieldRowStyle}>
                    <div style={{ minWidth: 0 }}>
                      <label htmlFor="stim-name" style={sublabelStyle}>
                        Name
                      </label>
                      <input
                        id="stim-name"
                        type="text"
                        value={stimName}
                        onChange={(e) => setStimName(e.target.value)}
                        disabled={formDisabled}
                        placeholder="e.g. sample-workspace-v2"
                        style={{ ...inputStyle, fontFamily: FONT_MONO, fontSize: 13 }}
                      />
                    </div>
                  </div>
                  <div style={hintStyle}>
                    The name prints on the reading manifest — the treatment
                    text below is what agents actually read.
                  </div>
                  <div style={fieldStyle}>
                    <label htmlFor="proposed-prd" style={sublabelStyle}>
                      Treatment — proposed change
                    </label>
                    <textarea
                      id="proposed-prd"
                      value={proposedPrd}
                      onChange={(e) => setProposedPrd(e.target.value)}
                      disabled={formDisabled}
                      rows={4}
                      placeholder="Describe the proposed change as a PRD delta..."
                      style={{
                        ...inputStyle,
                        resize: "vertical",
                        lineHeight: 1.45,
                      }}
                    />
                    <div style={hintStyle}>
                      Written like a PRD delta — treatment-arm agents read this
                      alongside the capability&rsquo;s as-built PRD.
                    </div>
                  </div>
                  {/* #183: no false affordance — proposed_figma has no
                      authoring path here (the wizard always submits null).
                      First-class stimuli with a screens editor are #169. */}
                  <div style={fieldStyle}>
                    <span style={sublabelStyle}>Screens — not yet</span>
                    <div style={hintStyle}>
                      Screen flows can&rsquo;t be attached here yet — agents
                      read the PRD-delta text only. Attachable screens arrive
                      with first-class stimuli.
                    </div>
                  </div>
                  <div
                    style={{
                      fontFamily: FONT_MONO,
                      fontSize: 10.5,
                      letterSpacing: "0.06em",
                      color: TOKENS.inkMuted,
                      marginTop: 14,
                      paddingTop: 10,
                      borderTop: `0.75px solid ${TOKENS.rule}`,
                    }}
                  >
                    CONTROL ARM = AS-BUILT CAPABILITY FROM THE FROZEN SLICE —
                    NEVER AUTHORED
                  </div>
                </div>
              )}

              {/* Phase 4.6 #88: A/B experiment-mode toggle + cost preview */}
              <ABModeSection
                enabled={abMode}
                onToggle={(next) => {
                  setAbMode(next);
                  // Clear stale acknowledgement when the user flips the toggle.
                  // #313 / T4: the metric picker is NO LONGER A/B-only — a
                  // single-arm run declares the metric as its OEC to clear the
                  // answerability gate, so the selection is PRESERVED across the
                  // toggle (only the A/B-specific large-run acknowledgement is
                  // reset). Leaving A/B mode keeps the declared OEC; only the
                  // paired-lift delta (vs. single-arm rate) changes.
                  if (!next) {
                    setAcknowledgedLargeRun(false);
                  }
                }}
                populationSize={populationSize}
                perArmCap={activePerArmCap}
                confirmThreshold={CONFIRM_TOTAL_AGENTS_THRESHOLD}
                acknowledged={acknowledgedLargeRun}
                onAcknowledge={setAcknowledgedLargeRun}
                disabled={formDisabled || AB_MODE_DISABLED_UNTIL_LIFT}
                stagedRolloutNote={AB_MODE_DISABLED_UNTIL_LIFT}
                capError={limitsError}
              />
            </section>

            {/* ── 03 · Cohort ────────────────────────────── */}
            <section style={sectionStyle}>
              <div style={sectionLabelStyle}>03 · Cohort</div>
              <PersonaFilterSection
                personas={activePersonas}
                packVersion={packVersion}
                loading={loadingPersonas}
                error={personasError}
                selected={selectedPersonas}
                onChange={setSelectedPersonas}
                disabled={formDisabled}
              />
            </section>

            {/* ── 04 · Reading ───────────────────────────── */}
            <section style={sectionStyle}>
              <div style={sectionLabelStyle}>04 · Reading</div>
              <div style={{ ...fieldStyle, ...fieldRowStyle }}>
                <div style={fieldRowStyle}>
                  <div style={{ minWidth: 0 }}>
                    <label htmlFor="population-size" style={sublabelStyle}>
                      Population
                    </label>
                    <input
                      id="population-size"
                      type="number"
                      min={1}
                      max={10_000}
                      value={populationInput}
                      onChange={(e) => setPopulationInput(e.target.value)}
                      disabled={formDisabled}
                      style={{
                        ...inputStyle,
                        fontFamily: FONT_MONO,
                        fontSize: 13,
                        ...TNUM,
                      }}
                    />
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <label htmlFor="agent-count" style={sublabelStyle}>
                      Agents
                    </label>
                    <input
                      id="agent-count"
                      type="number"
                      min={1}
                      max={activePerArmCap ?? undefined}
                      value={agentCountInput}
                      placeholder={
                        activePerArmCap != null
                          ? `cap ${activePerArmCap}`
                          : "cap"
                      }
                      onChange={(e) => setAgentCountInput(e.target.value)}
                      disabled={formDisabled}
                      style={{
                        ...inputStyle,
                        fontFamily: FONT_MONO,
                        fontSize: 13,
                        ...TNUM,
                      }}
                    />
                  </div>
                </div>
                <ModelSelectorSection
                  models={models}
                  selectedModelId={selectedModelId}
                  defaultModelId={defaultModelId}
                  loading={loadingModels}
                  error={modelsError}
                  onChange={setSelectedModelId}
                  disabled={formDisabled}
                />
              </div>
              <div style={hintStyle}>
                Population is how many users this hypothesis affects; Agents is
                how many synthetic agents to actually run (blank = backend cap).{" "}
                {loadingLimits ? (
                  <>Loading simulation limits...</>
                ) : limitsError ? (
                  <>Simulation limits are unavailable; run is disabled.</>
                ) : realizedAgentCount != null ? (
                  <>
                    We&rsquo;ll stratify down to{" "}
                    <strong>
                      {realizedAgentCount} sampled agent
                      {realizedAgentCount === 1 ? "" : "s"}
                    </strong>{" "}
                    in proportion to your persona weights (Hamilton
                    allocation).
                    {activePerArmCap != null &&
                      realizedAgentCount === activePerArmCap &&
                      Math.min(
                        populationSize ?? Infinity,
                        requestedAgentCount ?? Infinity,
                      ) > activePerArmCap && (
                        <> Backend cap: {activePerArmCap} agents.</>
                      )}
                  </>
                ) : (
                  <>Enter a population between 1 and 10,000.</>
                )}
              </div>
              {limitsError && (
                <div style={{ ...hintStyle, marginTop: 4 }}>
                  {limitsError} Reload after the backend is reachable.
                </div>
              )}
            </section>

            {/* ── 05 · Outcome metric ────────────────────── */}
            <section style={sectionStyle}>
              <div style={sectionLabelStyle}>05 · Outcome metric</div>
              <MetricSection
                abMode={abMode}
                metricName={metricName}
                onChangeMetric={setMetricName}
                conversionAction={conversionAction}
                onChangeConversionAction={setConversionAction}
                conversionActionLabel={conversionActionLabel}
                onChangeConversionActionLabel={setConversionActionLabel}
                decisionPoint={decisionPoint}
                onChangeDecisionPoint={setDecisionPoint}
                choiceSetText={choiceSetText}
                onChangeChoiceSet={setChoiceSetText}
                disabled={formDisabled}
              />
            </section>
          </div>
        </div>

        {/* ── Reading manifest — inspector rail ──────────── */}
        <aside
          className="rc-rail"
          style={{
            width: 340,
            flexShrink: 0,
            borderLeft: `0.75px solid ${TOKENS.rule}`,
            background: TOKENS.paperElevated,
            boxShadow: "inset 0 1px 0 rgba(255, 255, 255, 0.04)",
          }}
        >
          <div
            className="rc-rail-sticky"
            style={{
              position: "sticky",
              top: 0,
              display: "flex",
              flexDirection: "column",
            }}
          >
            <div
              style={{
                padding: "16px 20px 12px",
                borderBottom: `0.75px solid ${TOKENS.rule}`,
              }}
            >
              <span style={{ ...sectionLabelStyle, border: "none", paddingBottom: 0 }}>
                Reading manifest
              </span>
            </div>
            <dl
              style={{
                margin: 0,
                padding: "14px 20px 16px",
                display: "grid",
                gridTemplateColumns: "auto 1fr",
                gap: "3px 16px",
                alignContent: "start",
              }}
            >
              {manifestRows.map(([dt, dd]) => (
                <div key={dt} style={{ display: "contents" }}>
                  <dt
                    style={{
                      fontSize: 11,
                      letterSpacing: "0.1em",
                      textTransform: "uppercase",
                      color: TOKENS.inkMuted,
                      paddingTop: 1,
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
                      minWidth: 0,
                      overflowWrap: "break-word",
                      ...TNUM,
                    }}
                  >
                    {dd}
                  </dd>
                </div>
              ))}
            </dl>
            <CompletenessChecklist items={completenessItems} />
            <div
              style={{
                padding: "16px 20px",
                borderTop: `0.75px solid ${TOKENS.rule}`,
                display: "flex",
                flexDirection: "column",
                gap: 8,
              }}
            >
              <button
                type="submit"
                disabled={formDisabled}
                style={{
                  ...primaryBtnStyle,
                  opacity: formDisabled ? 0.5 : 1,
                  cursor: formDisabled ? "not-allowed" : "pointer",
                }}
              >
                {submitting ? "Submitting..." : "Begin reading →"}
              </button>
              <div
                style={{
                  fontFamily: FONT_MONO,
                  fontSize: 10.5,
                  color: TOKENS.inkMuted,
                  letterSpacing: "0.04em",
                  lineHeight: 1.5,
                  ...TNUM,
                }}
              >
                EST. 4–6 MIN — THE TRACE PLOTS AS BATCHES LAND. NO SPINNERS.
              </div>
            </div>
          </div>
        </aside>
      </form>
        </main>
      </div>
    </AppShellV2>
  );
}

function ModelSelectorSection({
  models,
  selectedModelId,
  defaultModelId,
  loading,
  error,
  onChange,
  disabled,
}: {
  models: ModelInfo[];
  selectedModelId: string;
  defaultModelId: string | null;
  loading: boolean;
  error: string | null;
  onChange: (next: string) => void;
  disabled: boolean;
}) {
  if (loading) {
    return (
      <div style={{ minWidth: 0 }}>
        <div style={sublabelStyle}>Model</div>
        <div style={hintStyle}>Loading available models…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ minWidth: 0 }}>
        <div style={sublabelStyle}>Model</div>
        <div style={warnNoteStyle}>
          {error} The backend will use its configured default.
        </div>
      </div>
    );
  }

  if (models.length === 0) {
    return (
      <div style={{ minWidth: 0 }}>
        <div style={sublabelStyle}>Model</div>
        <div style={warnNoteStyle}>
          No provider API keys are configured. Submitting without a model
          selection will use backend default resolution.
        </div>
      </div>
    );
  }

  const selected = models.find((m) => m.id === selectedModelId) ?? models[0];
  const providers: ModelInfo["provider"][] = ["anthropic", "openai", "groq"];

  return (
    <div style={{ minWidth: 0 }}>
      <label htmlFor="model-id" style={sublabelStyle}>
        Model
      </label>
      <select
        id="model-id"
        value={selectedModelId || selected.id}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        style={selectStyle}
      >
        {providers.map((provider) => {
          const providerModels = models.filter((m) => m.provider === provider);
          if (providerModels.length === 0) return null;
          return (
            <optgroup key={provider} label={providerLabel(provider)}>
              {providerModels.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.label}
                  {model.id === defaultModelId ? " (default)" : ""}
                </option>
              ))}
            </optgroup>
          );
        })}
      </select>
      <div style={hintStyle}>
        {selected.description} Speed: {selected.speed_label}; cost:{" "}
        {selected.cost_label}. A/B simulations use this same model for both
        arms.
      </div>
    </div>
  );
}

function providerLabel(provider: ModelInfo["provider"]): string {
  if (provider === "anthropic") return "Anthropic";
  if (provider === "openai") return "OpenAI";
  return "Groq";
}

// Phase 4.6 #88 — A/B experiment mode toggle + cost preview.
// Surfaces the wizard UX for arm_split. Wizard sends treatment_fraction=0.5
// when enabled (paired sampling per docs/4.6 Q3); slider hidden in v1 since
// non-50/50 splits are statistically wasteful for paired mode.
// R2 #167: rendered as the mock's segmented Mode control (SINGLE ARM /
// A/B — TREATMENT VS CONTROL). Same boolean state, same payload.
function ABModeSection({
  enabled,
  onToggle,
  populationSize,
  perArmCap,
  confirmThreshold,
  acknowledged,
  onAcknowledge,
  disabled,
  stagedRolloutNote,
  capError,
}: {
  enabled: boolean;
  onToggle: (next: boolean) => void;
  populationSize: number | null;
  perArmCap: number | null;
  confirmThreshold: number;
  acknowledged: boolean;
  onAcknowledge: (next: boolean) => void;
  disabled: boolean;
  // Phase 4.6 STAGED ROLLOUT: when true, the toggle is rendered but
  // disabled with a "coming next" note. Set by the parent when
  // AB_MODE_DISABLED_UNTIL_LIFT is on. Once #89 wires the dual-arm runner,
  // the parent flips this to false.
  stagedRolloutNote: boolean;
  capError: string | null;
}) {
  const perArm =
    populationSize != null && perArmCap != null
      ? Math.min(populationSize, perArmCap)
      : 0;
  const totalAgents = 2 * perArm;
  const isLarge = totalAgents > confirmThreshold;

  const segBtnBase: React.CSSProperties = {
    fontFamily: FONT_MONO,
    fontSize: 11,
    letterSpacing: "0.06em",
    border: "none",
    padding: "7px 14px",
    transition: "background 80ms ease-out, color 80ms ease-out",
    cursor: disabled ? "not-allowed" : "pointer",
  };

  return (
    <div style={fieldStyle}>
      <span style={sublabelStyle} id="ab-mode-label">
        Mode
      </span>
      <span
        role="group"
        aria-labelledby="ab-mode-label"
        aria-describedby="ab-mode-helper"
        style={{
          display: "inline-flex",
          border: `0.75px solid ${TOKENS.rule}`,
          borderRadius: 2,
          overflow: "hidden",
        }}
      >
        <button
          type="button"
          onClick={() => onToggle(false)}
          disabled={disabled}
          aria-pressed={!enabled}
          style={{
            ...segBtnBase,
            // dark Console segmented active = raised --console-750 fill + hi
            // text; idle = transparent + muted (mock .seg button rules).
            background: !enabled ? "#1D2740" : "transparent",
            color: !enabled ? TOKENS.ink : TOKENS.inkMuted,
          }}
        >
          SINGLE ARM
        </button>
        <button
          type="button"
          onClick={() => onToggle(true)}
          disabled={disabled}
          aria-pressed={enabled}
          style={{
            ...segBtnBase,
            borderLeft: `0.75px solid ${TOKENS.rule}`,
            background: enabled ? "#1D2740" : "transparent",
            color: enabled ? TOKENS.ink : TOKENS.inkMuted,
          }}
        >
          A/B — TREATMENT VS CONTROL
        </button>
      </span>
      {stagedRolloutNote && (
        <div style={hintStyle}>
          A/B execution runs end-to-end now (#89), but the result page
          still shows confidence — not lift. The wizard toggle stays
          disabled until #90 (paired lift formula) + #91 (lift display)
          land so PMs never see a single-arm score over a mixed cohort.
        </div>
      )}
      {!stagedRolloutNote && (
        <div id="ab-mode-helper" style={hintStyle}>
          {enabled && capError ? (
            <>Simulation limits are unavailable; A/B preview is disabled.</>
          ) : enabled &&
            populationSize != null &&
            populationSize > 0 &&
            perArmCap != null ? (
            <>
              ≈ <strong>{perArm} treatment + {perArm} control</strong> ={" "}
              <strong>{totalAgents} LLM agents</strong> for this run. Each
              persona is paired across arms (same identity reacts to BOTH the
              current product and the proposed change), so the lift is a
              within-persona delta — not an apples-to-oranges comparison.
              {populationSize > perArmCap && (
                <>
                  {" "}Backend cap applies: requested population{" "}
                  {populationSize.toLocaleString()} is capped at {perArm} agents
                  per arm.
                </>
              )}
            </>
          ) : enabled ? (
            <>Enter a population size above to see the agent count.</>
          ) : (
            <>
              A/B pairs every reading — same persona, same seed, both arms —
              and reports a predicted lift between them. Costs ~2× a
              single-arm run.
            </>
          )}
          {capError && (
            <div style={{ marginTop: 6 }}>
              {capError} Reload after the backend is reachable.
            </div>
          )}
        </div>
      )}
      {enabled && isLarge && (
        <label
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 8,
            marginTop: 10,
            padding: "10px 12px",
            background: TOKENS.paperRecessed,
            border: `0.75px solid ${TOKENS.warn}`,
            borderRadius: 2,
            fontSize: 13,
            color: TOKENS.ink,
          }}
        >
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(e) => onAcknowledge(e.target.checked)}
            disabled={disabled}
            aria-describedby="ab-confirm-large-helper"
            style={{ marginTop: 2 }}
          />
          <span id="ab-confirm-large-helper">
            <strong>Large run.</strong> This A/B sim uses{" "}
            {totalAgents} LLM agents (2× a single-arm run). Tick to
            acknowledge the ~2× LLM cost before submitting.
          </span>
        </label>
      )}
    </div>
  );
}

// #279 / #313 — Per-metric outcome elicitation picker. OPTIONAL. Declaring a
// metric here also declares the OEC, which clears the epic #309 T1
// `oec_undeclared` answerability block (the deploy-unblocker) — so the picker
// is now offered in BOTH single-arm and A/B mode (#313 / T4 decoupled it from
// A/B). None is the default; selecting a metric reveals exactly the
// registry-required template fields. The metric-lift DELTA (treatment −
// control) is still only computed in A/B mode; outside it, the metric is the
// OEC for the sentiment-aligned reading and a single-arm rate.
function MetricSection({
  abMode,
  metricName,
  onChangeMetric,
  conversionAction,
  onChangeConversionAction,
  conversionActionLabel,
  onChangeConversionActionLabel,
  decisionPoint,
  onChangeDecisionPoint,
  choiceSetText,
  onChangeChoiceSet,
  disabled,
}: {
  abMode: boolean;
  metricName: MetricName;
  onChangeMetric: (next: MetricName) => void;
  conversionAction: string;
  onChangeConversionAction: (next: string) => void;
  conversionActionLabel: string;
  onChangeConversionActionLabel: (next: string) => void;
  decisionPoint: string;
  onChangeDecisionPoint: (next: string) => void;
  choiceSetText: string;
  onChangeChoiceSet: (next: string) => void;
  disabled: boolean;
}) {
  // #313 / T4: the picker is no longer A/B-gated — declaring an OEC must work
  // single-arm to clear the answerability gate. It is inert only while the
  // form itself is loading/submitting.
  const pickerDisabled = disabled;

  const segBtnBase: React.CSSProperties = {
    fontFamily: FONT_MONO,
    fontSize: 11,
    letterSpacing: "0.06em",
    border: "none",
    padding: "7px 14px",
    transition: "background 80ms ease-out, color 80ms ease-out",
    cursor: pickerDisabled ? "not-allowed" : "pointer",
  };

  // None + the three registered metrics, in registry order.
  const options: Array<{ value: MetricName; label: string }> = [
    { value: null, label: "NONE" },
    { value: "conversion", label: "CONVERSION" },
    { value: "retention", label: "RETENTION" },
    { value: "ctr", label: "CTR" },
  ];

  const labelFieldShown = metricName != null;
  // conversion_action (the machine event) is only required/shown for conversion.
  const eventFieldShown = metricName === "conversion";
  // The reused label field's prompt differs per metric (the registry reads
  // conversion_action_label as the conversion label / retention "return" label /
  // ctr click label). Conversion requires it; retention + ctr make it optional.
  const labelMeta: Record<
    MetricKey,
    { label: string; placeholder: string; hint: string; required: boolean }
  > = {
    conversion: {
      label: "Conversion label — in-character",
      placeholder: "e.g. check out now",
      hint: "How agents phrase the conversion choice in-character (prepended to the alternatives below).",
      required: true,
    },
    retention: {
      label: "Return label — optional",
      placeholder: "e.g. return next week",
      hint: 'The "return" choice agents pick to come back. Leave blank to use the default "return next week".',
      required: false,
    },
    ctr: {
      label: "Click label — optional",
      placeholder: "e.g. tap the new banner",
      hint: 'How agents phrase the click on the element under test. Leave blank to use the default "click it".',
      required: false,
    },
  };
  const decisionMeta: Record<MetricKey, { hint: string; placeholder: string }> =
    {
      conversion: {
        placeholder: "e.g. you've added 2 items to your cart",
        hint: "The moment the agent is at when the conversion choice is offered.",
      },
      retention: {
        placeholder: "e.g. you've just finished tonight's session",
        hint: "The post-experience moment — the agent decides whether to come back from here.",
      },
      ctr: {
        placeholder: "e.g. the new banner is on screen above the feed",
        hint: "The on-screen moment the rendered element sits at when the click choice is offered.",
      },
    };

  return (
    <div style={{ opacity: pickerDisabled ? 0.5 : 1 }}>
      <span style={sublabelStyle} id="metric-label">
        Target metric — optional
      </span>
      <span
        role="group"
        aria-labelledby="metric-label"
        aria-describedby="metric-helper"
        style={{
          display: "inline-flex",
          border: `0.75px solid ${TOKENS.rule}`,
          borderRadius: 2,
          overflow: "hidden",
        }}
      >
        {options.map((opt, i) => {
          const active = metricName === opt.value;
          return (
            <button
              key={opt.label}
              type="button"
              onClick={() => onChangeMetric(opt.value)}
              disabled={pickerDisabled}
              aria-pressed={active}
              style={{
                ...segBtnBase,
                borderLeft:
                  i === 0 ? "none" : `0.75px solid ${TOKENS.rule}`,
                // dark Console segmented active = raised --console-750 + hi text
                background: active ? "#1D2740" : "transparent",
                color: active ? TOKENS.ink : TOKENS.inkMuted,
              }}
            >
              {opt.label}
            </button>
          );
        })}
      </span>
      <div id="metric-helper" style={hintStyle}>
        {metricName == null ? (
          <>
            None reports the sentiment confidence score only (today&rsquo;s
            default). Declaring a metric names the OEC the run is answerable
            against and elicits a blinded, in-character decision.
            {!abMode && (
              <>
                {" "}
                In single-arm mode it reports the metric rate alongside
                sentiment; switch Mode to <strong>A/B</strong> above to also get
                the paired treatment − control lift.
              </>
            )}
          </>
        ) : (
          <>
            Agents answer a blinded in-character question on turn 2; the scorer
            reports the {METRIC_LABELS[metricName].toLowerCase()}{" "}
            {abMode ? (
              <>
                lift as a paired treatment − control delta
              </>
            ) : (
              <>
                rate (single-arm) alongside the sentiment score
              </>
            )}
            . Magnitude is uncalibrated — read it as rank + direction.
          </>
        )}
      </div>

      {metricName != null && (
        <div style={{ marginTop: 14 }}>
          {eventFieldShown && (
            <div style={fieldStyle}>
              <label htmlFor="conversion-action" style={sublabelStyle}>
                Conversion event
              </label>
              <input
                id="conversion-action"
                type="text"
                value={conversionAction}
                onChange={(e) => onChangeConversionAction(e.target.value)}
                disabled={disabled}
                placeholder="e.g. complete checkout"
                style={inputStyle}
              />
              <div style={hintStyle}>
                The event that counts as a conversion (the scorer measures its
                paired rate).
              </div>
            </div>
          )}
          {labelFieldShown && metricName && (
            <div style={fieldStyle}>
              <label
                htmlFor="conversion-action-label"
                style={sublabelStyle}
              >
                {labelMeta[metricName].label}
              </label>
              <input
                id="conversion-action-label"
                type="text"
                value={conversionActionLabel}
                onChange={(e) =>
                  onChangeConversionActionLabel(e.target.value)
                }
                disabled={disabled}
                placeholder={labelMeta[metricName].placeholder}
                style={inputStyle}
              />
              <div style={hintStyle}>{labelMeta[metricName].hint}</div>
            </div>
          )}
          {metricName && (
            <div style={fieldStyle}>
              <label htmlFor="decision-point" style={sublabelStyle}>
                Decision point
              </label>
              <input
                id="decision-point"
                type="text"
                value={decisionPoint}
                onChange={(e) => onChangeDecisionPoint(e.target.value)}
                disabled={disabled}
                placeholder={decisionMeta[metricName].placeholder}
                style={inputStyle}
              />
              <div style={hintStyle}>{decisionMeta[metricName].hint}</div>
            </div>
          )}
          <div style={fieldStyle}>
            <label htmlFor="choice-set" style={sublabelStyle}>
              Alternatives — optional
            </label>
            <textarea
              id="choice-set"
              value={choiceSetText}
              onChange={(e) => onChangeChoiceSet(e.target.value)}
              disabled={disabled}
              rows={3}
              placeholder={
                "One non-target alternative per line —\n" +
                "e.g. keep browsing / decide later\n" +
                "leave without doing anything"
              }
              style={{ ...inputStyle, resize: "vertical", lineHeight: 1.45 }}
            />
            <div style={hintStyle}>
              Realistic choices an agent takes INSTEAD of the target, one per
              line. Leave blank to use the metric&rsquo;s default set.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// #313 / T4 (deliverable 4) — live inline answerability lint. Renders the
// deterministic POST /preflight verdict beside the claim as the user authors.
// Pure §7.7 disclosure anatomy (rule border, paper-recessed fill, mono label,
// ink body) — a data caution, never an alarm: no semantic fill, no pill, no
// icon, no alert-red. The advisory state never blocks; it is guidance only.
function ClaimLintNotes({
  preflight,
  stale,
}: {
  preflight: PreflightResponse | null;
  stale: boolean;
}) {
  if (!preflight) return null;

  // The answerability verdict's own reasons/fixes (needs_input / out_of_scope)
  // and the separable leading-framing lint, surfaced as two notes. A clean
  // answerable verdict with no framing flags renders a quiet confirmation.
  const hasAnswerability = preflight.reasons.length > 0;
  const hasFraming = preflight.leading_framing_reasons.length > 0;

  const header =
    preflight.state === "needs_input"
      ? "needs a detail before it can be read"
      : preflight.state === "out_of_scope"
        ? "outside this instrument's measurement scope"
        : "advisory — clarify before you run";

  return (
    <div style={{ marginTop: 14, opacity: stale ? 0.55 : 1 }}>
      {hasAnswerability && (
        <div style={disclosureNoteStyle}>
          <div style={disclosureLabelStyle}>{header}</div>
          <ReasonFixList
            reasons={preflight.reasons}
            fixes={preflight.fixes}
          />
        </div>
      )}
      {hasFraming && (
        <div style={{ ...disclosureNoteStyle, marginTop: hasAnswerability ? 8 : 0 }}>
          <div style={disclosureLabelStyle}>
            leading framing — may bias the reading
          </div>
          <ReasonFixList
            reasons={preflight.leading_framing_reasons}
            fixes={preflight.leading_framing_fixes}
          />
        </div>
      )}
      {!hasAnswerability && !hasFraming && (
        <div style={disclosureNoteStyle}>
          <div style={disclosureLabelStyle}>reads cleanly</div>
          <div style={disclosureBodyTextStyle}>
            This claim is answerable as written — no missing detail and no
            leading framing detected.
          </div>
        </div>
      )}
    </div>
  );
}

// #313 / T4 (deliverable 3) — the needs_input 422 surface. Same §7.7
// disclosure anatomy as the inline lint. NOT a dead-end: it names the blocking
// reasons + fixes, and when `allow_override` it offers the explicit "run anyway
// as generic reception" affordance (resubmits with run_as_generic_reception).
function NeedsInputNote({
  detail,
  submitting,
  onRunAnyway,
  onDismiss,
}: {
  detail: NeedsInputDetail;
  submitting: boolean;
  onRunAnyway: () => void;
  onDismiss: () => void;
}) {
  return (
    <div
      role="alert"
      style={{ ...disclosureNoteStyle, maxWidth: 620, marginBottom: 16 }}
    >
      <div style={disclosureLabelStyle}>
        one detail needed before this can be read
      </div>
      <ReasonFixList reasons={detail.reasons} fixes={detail.fixes} />
      <div
        style={{
          marginTop: 12,
          display: "flex",
          gap: 12,
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <button
          type="button"
          onClick={onDismiss}
          disabled={submitting}
          style={quietBtnStyle}
        >
          Edit the claim
        </button>
        {detail.allow_override && (
          <button
            type="button"
            onClick={onRunAnyway}
            disabled={submitting}
            style={quietBtnStyle}
          >
            {submitting ? "Submitting…" : "Run anyway as generic reception"}
          </button>
        )}
      </div>
      {detail.allow_override && (
        <div style={{ ...disclosureBodyTextStyle, marginTop: 8 }}>
          Running as generic reception reports sentiment only — it is not
          aligned to a declared outcome metric.
        </div>
      )}
    </div>
  );
}

// Shared reasons + fixes body for the §7.7 disclosure notes. Reasons read in
// ink; fixes are the actionable guidance beneath them (ink-muted).
function ReasonFixList({
  reasons,
  fixes,
}: {
  reasons: string[];
  fixes: string[];
}) {
  return (
    <>
      {reasons.length > 0 && (
        <ul style={disclosureListStyle}>
          {reasons.map((r, i) => (
            <li key={`r-${i}`}>{r}</li>
          ))}
        </ul>
      )}
      {fixes.length > 0 && (
        <ul style={{ ...disclosureListStyle, color: TOKENS.inkMuted }}>
          {fixes.map((f, i) => (
            <li key={`f-${i}`}>{f}</li>
          ))}
        </ul>
      )}
    </>
  );
}

// #337 / T6 — glanceable completeness checklist. DISPLAY-ONLY (epic #309): the
// "N of M" is a human-glance count, never fed to confidence_score / the verdict
// / persistence, and never gates submit. Lives in the manifest rail above the
// primary action — the "glance before you run" spot.
//
// DESIGN.md: the count is a §8.2 panel-verdict-chip (mono, paper-recessed fill,
// rule border — a paper tone, never a semantic fill). Per-item rows use the
// §7.10 text-glyph register (no icon library): present = a `✓` glyph + `ink`
// label; absent = a `·` glyph + `ink-muted` label. Color never carries state
// alone — the glyph + the wording carry it (§4.3 / §7.8). The advisory item
// (mechanism) is visually distinguished by an `· advisory` mono tag, purely
// presentational; the actual block/override behavior lives in the T4 path.
function CompletenessChecklist({ items }: { items: CompletenessItem[] }) {
  // Only the non-advisory items count toward "essentials present" — the
  // advisory mechanism is shown but excluded from the glance count.
  const essentials = items.filter((it) => !it.advisory);
  const presentCount = essentials.filter((it) => it.present).length;
  const totalCount = essentials.length;

  return (
    <div
      style={{
        padding: "16px 20px",
        borderTop: `0.75px solid ${TOKENS.rule}`,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          gap: 12,
          marginBottom: 10,
        }}
      >
        <span
          style={{ ...sectionLabelStyle, border: "none", paddingBottom: 0 }}
        >
          Completeness
        </span>
        <span
          style={{
            fontFamily: FONT_MONO,
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: "0.06em",
            color: TOKENS.ink,
            border: `0.75px solid ${TOKENS.rule}`,
            background: TOKENS.paperRecessed,
            borderRadius: 2,
            padding: "3px 8px",
            whiteSpace: "nowrap",
            ...TNUM,
          }}
        >
          {presentCount} OF {totalCount} ESSENTIALS
        </span>
      </div>
      <ul
        style={{
          listStyle: "none",
          margin: 0,
          padding: 0,
          display: "flex",
          flexDirection: "column",
          gap: 5,
        }}
      >
        {items.map((it) => (
          <li
            key={it.key}
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: 8,
              fontSize: 13,
              lineHeight: 1.4,
              color: it.present ? TOKENS.ink : TOKENS.inkMuted,
            }}
          >
            <span
              aria-hidden="true"
              style={{
                fontFamily: FONT_MONO,
                fontSize: 12,
                width: "1ch",
                flexShrink: 0,
                color: it.present ? TOKENS.success : TOKENS.inkMuted,
              }}
            >
              {it.present ? "✓" : "·"}
            </span>
            <span>
              {/* Wording carries state, not color alone (§4.3 / §7.8): the
                  glyph + this present/absent prefix are the real signal. */}
              <span
                style={{
                  fontFamily: FONT_MONO,
                  fontSize: 9.5,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  color: TOKENS.inkMuted,
                  marginRight: 6,
                }}
              >
                {it.present ? "present" : "missing"}
              </span>
              {it.label}
              {it.advisory && (
                <span
                  style={{
                    fontFamily: FONT_MONO,
                    fontSize: 9.5,
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    color: TOKENS.inkMuted,
                    marginLeft: 6,
                  }}
                >
                  · advisory
                </span>
              )}
            </span>
          </li>
        ))}
      </ul>
      <div
        style={{
          ...hintStyle,
          marginTop: 10,
          maxWidth: "none",
        }}
      >
        A glance at what your hypothesis declares — it never gates the run or
        feeds the verdict.
      </div>
    </div>
  );
}

function parsePositiveInt(raw: string): number | null {
  const trimmed = raw.trim();
  if (trimmed === "") return null;
  // Strict: reject "12abc", "1.5", "1e3", and anything else that isn't
  // purely digits. `Number.parseInt` would otherwise silently truncate.
  // (codex P2 round 2)
  if (!/^\d+$/.test(trimmed)) return null;
  const n = Number.parseInt(trimmed, 10);
  if (!Number.isFinite(n) || n < 0) return null;
  return n;
}

// Phase 5 #101 — Persona filter (R2: chips in 03 · Cohort, always visible).
// All personas selected by default; PM deselects to narrow the cohort.
// Submit payload sends `null` for "all selected" and an explicit subset only
// when narrowed (matches backend's "None = all" convention, keeps persisted
// sim row tidy).
function PersonaFilterSection({
  personas,
  packVersion,
  loading,
  error,
  selected,
  onChange,
  disabled,
}: {
  personas: PersonaSummary[];
  packVersion: string | null;
  loading: boolean;
  error: string | null;
  selected: Set<string>;
  onChange: (next: Set<string>) => void;
  disabled: boolean;
}) {
  if (loading) {
    return (
      <div style={{ ...hintStyle, marginTop: 16 }}>Loading personas…</div>
    );
  }
  if (error) {
    // Non-fatal: the parent still submits with selected_personas: null
    // (= all personas), so we don't block the form. Surface the error so
    // the PM knows narrowing isn't available.
    return (
      <div style={{ ...warnNoteStyle, marginTop: 16 }}>
        {error} (Will run against all personas.)
      </div>
    );
  }
  if (personas.length === 0) {
    return null;
  }

  const allChecked = selected.size === personas.length;
  const noneChecked = selected.size === 0;

  function toggle(id: string) {
    const next = new Set(selected);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    onChange(next);
  }

  return (
    <>
      <div style={fieldStyle}>
        <span style={sublabelStyle}>Persona pack</span>
        <div
          style={{
            fontFamily: FONT_MONO,
            fontSize: 13,
            color: TOKENS.ink,
            ...TNUM,
          }}
        >
          {packVersion} · {personas.length} PERSONAS
        </div>
      </div>
      <div style={fieldStyle}>
        <span style={sublabelStyle}>Filter</span>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {personas.map((p) => {
            const isOn = selected.has(p.id);
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => toggle(p.id)}
                disabled={disabled}
                aria-pressed={isOn}
                style={{
                  fontFamily: FONT_MONO,
                  fontSize: 11,
                  letterSpacing: "0.04em",
                  cursor: disabled ? "not-allowed" : "pointer",
                  // dark Console chip: selected = raised --console-750 fill +
                  // line border + hi text; idle = --console-800 + muted. The
                  // border stays at the hairline rule even when pressed (the
                  // mock never brightens a chip border to ink).
                  border: `0.75px solid ${TOKENS.rule}`,
                  borderRadius: 2,
                  padding: "4px 9px",
                  color: isOn ? TOKENS.ink : TOKENS.inkMuted,
                  background: isOn ? "#1D2740" : TOKENS.paper,
                  opacity: isOn ? 1 : 0.7,
                  transition:
                    "border-color 80ms ease-out, color 80ms ease-out",
                  ...TNUM,
                }}
              >
                {p.name} · {(p.weight * 100).toFixed(0)}%
              </button>
            );
          })}
        </div>
        <div
          style={{
            display: "flex",
            gap: 12,
            fontSize: 12,
            marginTop: 8,
          }}
        >
          <button
            type="button"
            onClick={() => onChange(new Set(personas.map((p) => p.id)))}
            disabled={disabled || allChecked}
            style={{
              background: "transparent",
              border: "none",
              color: allChecked ? TOKENS.inkMuted : TOKENS.ink,
              cursor: allChecked ? "default" : "pointer",
              padding: 0,
              textDecoration: "underline",
              fontSize: 12,
            }}
          >
            Select all
          </button>
          <button
            type="button"
            onClick={() => onChange(new Set())}
            disabled={disabled || noneChecked}
            style={{
              background: "transparent",
              border: "none",
              color: noneChecked ? TOKENS.inkMuted : TOKENS.ink,
              cursor: noneChecked ? "default" : "pointer",
              padding: 0,
              textDecoration: "underline",
              fontSize: 12,
            }}
          >
            Clear all
          </button>
        </div>
        <div style={hintStyle}>
          Deselect personas to narrow the reading — weights renormalize via
          Hamilton allocation over the subset, so the full population is
          allocated across just those.
        </div>
        {noneChecked && (
          <div
            role="alert"
            style={{
              marginTop: 6,
              fontSize: 13,
              color: TOKENS.ink,
              padding: "8px 12px",
              background: TOKENS.paperRecessed,
              border: `0.75px solid ${TOKENS.alert}`,
              borderRadius: 2,
              maxWidth: "52ch",
            }}
          >
            Select at least one persona — empty filter is rejected.
          </div>
        )}
        {!allChecked && !noneChecked && (
          <div style={{ ...hintStyle, ...TNUM }}>
            Filtered: {selected.size} of {personas.length} personas.
          </div>
        )}
      </div>
    </>
  );
}

// ── shared styles — instrument posture (DESIGN.md §7.4) ──────────────
// Paper-elevated inputs, radius 2, no inset shadow; sentence-case
// body-font hints; mono reserved for designators and measurements.

const inputStyle: React.CSSProperties = {
  width: "100%",
  fontFamily: FONT_SANS,
  fontSize: 14,
  color: TOKENS.ink,
  // dark Console filled control (mock textarea/input/select): --console-700
  // surface, hairline border, radius 4. Focus ring is the scoped .rconsole
  // input:focus-visible rule (signal-dim), so no per-field focus handler.
  background: "#26314C",
  border: `1px solid ${TOKENS.rule}`,
  borderRadius: 4,
  padding: "8px 11px",
  boxSizing: "border-box",
  outline: "none",
};

// Selects carry machine designators (capability names, model ids, stimulus
// types) — mono per DESIGN.md §5.4.
const selectStyle: React.CSSProperties = {
  ...inputStyle,
  fontFamily: FONT_MONO,
  fontSize: 13,
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
  color: TOKENS.inkMuted,
  paddingBottom: 8,
  borderBottom: `0.75px solid ${TOKENS.rule}`,
  ...TNUM,
};

const sublabelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 10,
  fontWeight: 500,
  letterSpacing: "0.14em",
  textTransform: "uppercase",
  color: TOKENS.inkMuted,
  marginBottom: 6,
};

const hintStyle: React.CSSProperties = {
  fontSize: 12,
  color: TOKENS.inkMuted,
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

// The wizard's ONE action accent (DESIGN.md §4.3 / mock .btn-run): the
// "Begin reading" button is the sole place --signal appears — a hollow
// signal-bordered control, never a filled verdict block.
const primaryBtnStyle: React.CSSProperties = {
  background: "transparent",
  color: "#48EFCA",
  border: `1px solid #48EFCA`,
  borderRadius: 4,
  padding: "9px 14px",
  fontWeight: 500,
  fontSize: 14,
  fontFamily: FONT_SANS,
  cursor: "pointer",
};

const warnNoteStyle: React.CSSProperties = {
  ...hintStyle,
  padding: "8px 12px",
  // warn is accent-only (border) — text stays ink-muted (DESIGN.md §4.3).
  border: `0.75px solid ${TOKENS.warn}`,
  borderRadius: 2,
  background: TOKENS.paperRecessed,
};

const errorBannerStyle: React.CSSProperties = {
  marginBottom: 16,
  padding: "12px 16px",
  background: TOKENS.paperRecessed,
  // alert is accent-only (border) — the message reads in ink (DESIGN.md §4.3/§7.7).
  border: `0.75px solid ${TOKENS.alert}`,
  borderRadius: 2,
  color: TOKENS.ink,
  fontSize: 14,
  maxWidth: 620,
  boxSizing: "border-box",
};

const emptyStateStyle: React.CSSProperties = {
  marginBottom: 16,
  padding: 16,
  background: TOKENS.paperElevated,
  borderRadius: 4,
  color: TOKENS.inkMuted,
  fontSize: 14,
  border: `0.75px solid ${TOKENS.rule}`,
  maxWidth: 620,
  boxSizing: "border-box",
};

// #313 / T4 — claim mode toggle: a quiet text link (DESIGN.md §7.7 quiet
// control), not a button chrome. Sits in the section header.
const claimModeToggleStyle: React.CSSProperties = {
  background: "none",
  border: "none",
  padding: 0,
  fontFamily: FONT_MONO,
  fontSize: 10.5,
  letterSpacing: "0.06em",
  textTransform: "none",
  color: TOKENS.inkMuted,
  cursor: "pointer",
  textDecoration: "underline",
  textUnderlineOffset: 2,
};

// #313 / T4 — composed-claim preview: the exact prose the API receives, shown
// so the structured fields are never a black box. Paper-recessed, mono body
// (it is the literal payload string — a machine value per §5.4).
const composedPreviewStyle: React.CSSProperties = {
  marginTop: 14,
  padding: "10px 12px",
  border: `0.75px solid ${TOKENS.rule}`,
  background: TOKENS.paperRecessed,
  borderRadius: 2,
};

const composedPreviewLabelStyle: React.CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 10,
  fontWeight: 500,
  letterSpacing: "0.14em",
  textTransform: "uppercase",
  color: TOKENS.inkMuted,
  marginBottom: 6,
};

const composedPreviewBodyStyle: React.CSSProperties = {
  fontSize: 14,
  color: TOKENS.ink,
  lineHeight: 1.45,
};

// #313 / T4 — the §7.7 disclosure note anatomy, reused verbatim for BOTH the
// live inline lint (deliverable 4) and the needs_input surface (deliverable 3):
// 0.75px rule border, paper-recessed fill, mono label, ink body. A data
// caution, never an alarm — no semantic fill, no pill, no icon, no alert-red.
const disclosureNoteStyle: React.CSSProperties = {
  border: `0.75px solid ${TOKENS.rule}`,
  background: TOKENS.paperRecessed,
  borderRadius: 2,
  padding: "10px 12px",
};

const disclosureLabelStyle: React.CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 10,
  fontWeight: 500,
  letterSpacing: "0.14em",
  textTransform: "uppercase",
  color: TOKENS.inkMuted,
};

const disclosureBodyTextStyle: React.CSSProperties = {
  fontSize: 13,
  color: TOKENS.ink,
  lineHeight: 1.5,
  marginTop: 6,
};

const disclosureListStyle: React.CSSProperties = {
  margin: "6px 0 0",
  paddingLeft: 18,
  fontSize: 13,
  color: TOKENS.ink,
  lineHeight: 1.5,
};

// #313 / T4 — quiet secondary control for the needs_input affordances (DESIGN.md
// §7.7 quiet/secondary): hairline rule border, ink text, no fill.
const quietBtnStyle: React.CSSProperties = {
  background: TOKENS.paper,
  border: `0.75px solid ${TOKENS.rule}`,
  borderRadius: 2,
  padding: "6px 12px",
  fontFamily: FONT_SANS,
  fontSize: 13,
  fontWeight: 500,
  color: TOKENS.ink,
  cursor: "pointer",
};
