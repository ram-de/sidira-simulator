"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiError,
  createSimulation,
  getActivePersonas,
  getCapabilities,
  getSimulationLimits,
  listSupportedModels,
  type ActivePersonasResponse,
  type FeaturePackManifest,
  type Hypothesis,
  type ModelInfo,
  type PersonaSummary,
  type SimulationLimitsResponse,
  type SimulationRequest,
} from "@/lib/api";
import { TOKENS, FONT_SANS, FONT_MONO, TNUM } from "@/lib/design";
import SampleWorkspaceCard from "@/components/SampleWorkspaceCard";

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

export default function NewSimulationPage() {
  const router = useRouter();

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

  const [capability, setCapability] = useState<string>("");
  const [hypothesis, setHypothesis] = useState<string>("");
  // Population state is kept as a string so an empty field stays empty
  // (rather than briefly collapsing to "0" and rendering "0 sampled agents").
  // Parsed to a number only at submit time. Codex P2 (round 1).
  const [populationInput, setPopulationInput] = useState<string>("1000");
  const populationSize = parsePositiveInt(populationInput);
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
  // pre-#279 request. The paired metric-lift delta is only populated by the
  // scorer when the run is A/B mode (treatment − control), so the picker is
  // offered ONLY in A/B mode; flipping back to single-arm clears it.
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

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const m = await getCapabilities();
        if (cancelled) return;
        setManifest(m);
        if (m.capabilities && m.capabilities.length > 0) {
          setCapability(m.capabilities[0]);
        }
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError) {
          if (e.status === 404) setCapsNotFound(true);
          setCapsError(
            e.status === 404
              ? "No capabilities found for this customer. Run a crawl first."
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
  }, []);

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
  const activePerArmCap = simulationLimits?.max_agents_per_arm ?? null;
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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    setValidationError(null);

    if (!capability) {
      setValidationError("Please select a capability.");
      return;
    }
    const trimmedProse = hypothesis.trim();
    if (trimmedProse.length < 20) {
      setValidationError(
        "Hypothesis must be at least 20 characters of prose.",
      );
      return;
    }
    if (
      populationSize == null ||
      populationSize < 1 ||
      populationSize > 10_000
    ) {
      setValidationError("Population must be between 1 and 10,000.");
      return;
    }
    // Phase 5 #101: if the persona pack loaded and the PM cleared every
    // chip, refuse to submit -- the API would 422 and the wizard
    // shouldn't trip that.
    if (totalPersonaCount > 0 && noPersonasSelected) {
      setValidationError(
        "Select at least one persona to run the simulation against.",
      );
      return;
    }
    if (activePerArmCap == null) {
      setValidationError(
        "Simulation limits are unavailable. Reload after the backend is reachable.",
      );
      return;
    }

    // Phase 4.6 #88: when A/B mode is on, total agents = 2 × per_arm.
    // The PM has to acknowledge the cost if total exceeds the threshold.
    const perArmAgents = Math.min(populationSize, activePerArmCap);
    const totalAgents = abMode ? 2 * perArmAgents : perArmAgents;
    if (
      abMode &&
      totalAgents > CONFIRM_TOTAL_AGENTS_THRESHOLD &&
      !acknowledgedLargeRun
    ) {
      setValidationError(
        `This A/B run uses ≈ ${totalAgents} LLM agents (2× a single-arm sim). Tick the acknowledgement below to continue.`,
      );
      return;
    }

    // #279: when a metric is selected, the registry's required template fields
    // must be non-empty — mirror the backend's `Hypothesis._validate_metric`
    // (driven by `required_template_fields`) so the wizard never trips the
    // API's 422. The metric is A/B-only, so an effective metric only exists in
    // A/B mode (single-arm resets it to None on toggle, but guard here too).
    const effectiveMetric: MetricName = abMode ? metricName : null;
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
        return;
      }
    }

    // Phase 5 #101: send `selected_personas: null` when:
    //   (1) ALL personas are checked (= "no filter"), OR
    //   (2) the /personas fetch hasn't loaded yet / failed, so we don't
    //       know the full set and the PM can't actually be filtering --
    //       falling back to "null = all personas" is the correct
    //       backwards-compat behavior. (codex R1-P2 on #101: without this,
    //       a still-loading or errored /personas call left
    //       selectedPersonas empty, and the wizard submitted
    //       selected_personas: [] which the API 422-rejects -- breaking
    //       the exact fallback path the error UI promised would "run
    //       against all personas.")
    // Send the explicit subset only when the PM has actually narrowed.
    const personaFilter: string[] | null =
      totalPersonaCount === 0 || allPersonasSelected
        ? null
        : Array.from(selectedPersonas);

    // #279: assemble the optional per-metric outcome elicitation block. When no
    // metric is selected, `metricFields` is empty and the hypothesis payload is
    // byte-identical to a pre-#279 request (no metric_name key). Each metric
    // only sends its registry-required fields plus the optional choice_set; the
    // choice set is one alternative per non-empty line (empty → the metric's
    // registry default applies server-side).
    const metricFields: Partial<Hypothesis> = effectiveMetric
      ? {
          metric_name: effectiveMetric,
          conversion_action: conversionAction.trim() || null,
          conversion_action_label: conversionActionLabel.trim() || null,
          decision_point: decisionPoint.trim() || null,
          choice_set: choiceSetText
            .split("\n")
            .map((s) => s.trim())
            .filter((s) => s.length > 0),
        }
      : {};

    const req: SimulationRequest = {
      hypothesis: {
        capability_name: capability,
        prose: trimmedProse,
        proposed_prd:
          showAdvanced && proposedPrd.trim() ? proposedPrd.trim() : null,
        proposed_figma: null,
        ...metricFields,
      },
      population_size: populationSize,
      arm_split: abMode ? { treatment_fraction: 0.5 } : null,
      selected_personas: personaFilter,
      model_id: selectedModelId || null,
    };

    setSubmitting(true);
    try {
      const res = await createSimulation(req);
      router.push(`/simulations/${res.id}`);
    } catch (e) {
      if (e instanceof ApiError) {
        setSubmitError(
          `Submission failed (HTTP ${e.status}): ${e.body || e.message}`,
        );
      } else if (e instanceof Error) {
        setSubmitError(`Submission failed: ${e.message}`);
      } else {
        setSubmitError("Submission failed.");
      }
      setSubmitting(false);
    }
  }

  // R2 #167: live manifest values — every row is a real, currently-configured
  // value (DESIGN.md §8: no decorative furniture, no copy thresholds).
  const perArmPreview =
    populationSize != null && populationSize > 0 && activePerArmCap != null
      ? Math.min(populationSize, activePerArmCap)
      : null;
  const manifestRows: Array<[string, string]> = [
    ["Designator", "DRAFT · UNCOMMITTED"],
    ["Mode", abMode ? "A/B — PAIRED" : "SINGLE ARM"],
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
      abMode && metricName
        ? `${METRIC_LABELS[metricName].toUpperCase()} LIFT · PAIRED`
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

  return (
    <main style={{ fontFamily: FONT_SANS, color: TOKENS.ink }}>
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

          {(submitError || validationError) && (
            <div role="alert" style={errorBannerStyle}>
              {submitError ?? validationError}
            </div>
          )}

          <div
            style={{
              maxWidth: 620,
              opacity: formDisabled && !submitting ? 0.6 : 1,
            }}
          >
            {/* ── 01 · Claim ─────────────────────────────── */}
            <section>
              <div style={sectionLabelStyle}>01 · Claim</div>
              <div style={fieldStyle}>
                <label htmlFor="hypothesis" style={sublabelStyle}>
                  Hypothesis
                </label>
                <textarea
                  id="hypothesis"
                  value={hypothesis}
                  onChange={(e) => setHypothesis(e.target.value)}
                  disabled={formDisabled}
                  required
                  rows={3}
                  placeholder="e.g. If we surface a one-tap reorder CTA on the home screen for users who ordered in the last 14 days, weekly reorder rate will increase."
                  style={{ ...inputStyle, resize: "vertical", lineHeight: 1.45 }}
                />
                <div style={hintStyle}>
                  State a falsifiable prediction — be specific about who and
                  what, since the verdict prints against it.
                </div>
              </div>
            </section>

            {/* ── 02 · Subject ───────────────────────────── */}
            <section style={sectionStyle}>
              <div style={sectionLabelStyle}>02 · Subject</div>
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
                  // #279: the metric picker is A/B-only (the paired metric-lift
                  // delta has no meaning single-arm), so leaving A/B mode resets
                  // the metric selection back to None — the payload returns to
                  // sentiment-only, byte-identical to a pre-#279 request.
                  if (!next) {
                    setAcknowledgedLargeRun(false);
                    setMetricName(null);
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
                How many users this hypothesis affects.{" "}
                {loadingLimits ? (
                  <>Loading simulation limits...</>
                ) : limitsError ? (
                  <>Simulation limits are unavailable; run is disabled.</>
                ) : activePerArmCap != null &&
                  populationSize != null &&
                  populationSize > 0 ? (
                  <>
                    We&rsquo;ll stratify down to{" "}
                    <strong>
                      {Math.min(populationSize, activePerArmCap)} sampled agent
                      {Math.min(populationSize, activePerArmCap) === 1
                        ? ""
                        : "s"}
                    </strong>{" "}
                    in proportion to your persona weights (Hamilton
                    allocation).
                    {populationSize > activePerArmCap && (
                      <> Backend cap: {activePerArmCap} agents.</>
                    )}
                  </>
                ) : (
                  <>Enter a number between 1 and 10,000.</>
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
          style={{
            width: 340,
            flexShrink: 0,
            borderLeft: `0.75px solid ${TOKENS.rule}`,
            background: TOKENS.paperElevated,
            boxShadow: "inset 1px 1px 0 rgba(255, 255, 255, 0.55)",
          }}
        >
          <div
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
            background: !enabled ? TOKENS.ink : TOKENS.paper,
            color: !enabled ? TOKENS.paper : TOKENS.inkMuted,
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
            background: enabled ? TOKENS.ink : TOKENS.paper,
            color: enabled ? TOKENS.paper : TOKENS.inkMuted,
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

// #279 — Per-metric outcome elicitation picker. OPTIONAL and A/B-only: the
// paired metric-lift delta (treatment − control) only has meaning when both
// arms run, so outside A/B mode the picker greys out with an explanatory note
// (DESIGN.md §7.7 disabled = opacity 0.5 + not-allowed, honest about existing —
// never hidden, never recolored). None is the default; selecting a metric
// reveals exactly the registry-required template fields for it.
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
  // The picker is inert outside A/B mode (the metric-lift delta needs paired
  // arms). Greyed, not hidden — DESIGN.md §7.7.
  const pickerDisabled = disabled || !abMode;

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
                background: active ? TOKENS.ink : TOKENS.paper,
                color: active ? TOKENS.paper : TOKENS.inkMuted,
              }}
            >
              {opt.label}
            </button>
          );
        })}
      </span>
      <div id="metric-helper" style={hintStyle}>
        {!abMode ? (
          <>
            Outcome metrics need A/B mode — the lift is a paired treatment −
            control delta, so switch Mode to <strong>A/B</strong> above to
            elicit one. Without a metric, the run reports sentiment only.
          </>
        ) : metricName == null ? (
          <>
            None reports the sentiment confidence score only (today&rsquo;s
            default). Pick a metric to ALSO elicit a paired, in-character
            decision and report its treatment − control lift alongside
            sentiment.
          </>
        ) : (
          <>
            Agents answer a blinded in-character question on turn 2; the scorer
            reports the paired {METRIC_LABELS[metricName].toLowerCase()} lift
            alongside the sentiment score. Magnitude is uncalibrated — read it
            as rank + direction.
          </>
        )}
      </div>

      {abMode && metricName != null && (
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
                  border: `0.75px solid ${isOn ? TOKENS.ink : TOKENS.rule}`,
                  borderRadius: 2,
                  padding: "4px 9px",
                  color: isOn ? TOKENS.ink : TOKENS.inkMuted,
                  background: isOn ? TOKENS.paperRecessed : TOKENS.paper,
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
  background: TOKENS.paperElevated,
  border: `0.75px solid ${TOKENS.rule}`,
  borderRadius: 2,
  padding: "8px 11px",
  boxSizing: "border-box",
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

const primaryBtnStyle: React.CSSProperties = {
  background: TOKENS.ink,
  color: TOKENS.paper,
  border: `0.75px solid ${TOKENS.ink}`,
  borderRadius: 2,
  padding: "7px 14px",
  fontWeight: 500,
  fontSize: 13,
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
