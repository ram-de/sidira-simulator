"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiError,
  createSimulation,
  getActivePersonas,
  getCapabilities,
  type ActivePersonasResponse,
  type FeaturePackManifest,
  type PersonaSummary,
  type SimulationRequest,
} from "@/lib/api";

export default function NewSimulationPage() {
  const router = useRouter();

  const [manifest, setManifest] = useState<FeaturePackManifest | null>(null);
  const [loadingCaps, setLoadingCaps] = useState(true);
  const [capsError, setCapsError] = useState<string | null>(null);

  const [capability, setCapability] = useState<string>("");
  const [hypothesis, setHypothesis] = useState<string>("");
  // Population state is kept as a string so an empty field stays empty
  // (rather than briefly collapsing to "0" and rendering "0 sampled agents").
  // Parsed to a number only at submit time. Codex P2 (round 1).
  const [populationInput, setPopulationInput] = useState<string>("1000");
  const populationSize = parsePositiveInt(populationInput);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [proposedPrd, setProposedPrd] = useState<string>("");
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
  // Wizard-side mirror of the API's hard per-arm cap. Matches
  // PYTHIA_MAX_AGENTS in the default env (50). The cost preview uses
  // this to show realistic agent counts instead of the unclamped
  // populationSize.
  const WIZARD_PER_ARM_CAP = 50;
  // The "confirm-if-large" threshold from docs/4.6 Q4. When total agents
  // (across both arms) exceeds this, the PM gets an explicit
  // acknowledgement step before submit.
  const CONFIRM_TOTAL_AGENTS_THRESHOLD = 100;
  const [acknowledgedLargeRun, setAcknowledgedLargeRun] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Phase 5 #101: persona filter. Default = all personas selected (today's
  // behavior). PM can uncheck individual personas behind "Advanced options"
  // to run against a narrowed cohort. Submit payload sends
  // `selected_personas: null` when the full set is checked (matches the
  // backend's "None = all" convention and keeps the persisted row tidy);
  // sends an explicit subset when narrowed.
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

  // Phase 5 #101: load the active Persona Pack on mount so the filter
  // checkbox list has names + weights. Default = all checked.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const resp: ActivePersonasResponse = await getActivePersonas();
        if (cancelled) return;
        setActivePersonas(resp.personas);
        setPackVersion(resp.pack_version);
        setSelectedPersonas(new Set(resp.personas.map((p) => p.id)));
      } catch (e) {
        if (cancelled) return;
        // Non-fatal: hide the filter UI, fall back to "all personas"
        // (selected_personas: null on submit).
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
  const formDisabled = loadingCaps || !hasCapabilities || submitting;
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
    // checkbox, refuse to submit -- the API would 422 and the wizard
    // shouldn't trip that.
    if (totalPersonaCount > 0 && noPersonasSelected) {
      setValidationError(
        "Select at least one persona to run the simulation against.",
      );
      return;
    }

    // Phase 4.6 #88: when A/B mode is on, total agents = 2 × per_arm.
    // The PM has to acknowledge the cost if total exceeds the threshold.
    const perArmAgents = Math.min(populationSize, WIZARD_PER_ARM_CAP);
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

    const req: SimulationRequest = {
      hypothesis: {
        capability_name: capability,
        prose: trimmedProse,
        proposed_prd:
          showAdvanced && proposedPrd.trim() ? proposedPrd.trim() : null,
        proposed_figma: null,
      },
      population_size: populationSize,
      arm_split: abMode ? { treatment_fraction: 0.5 } : null,
      selected_personas: personaFilter,
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

  return (
    <main style={{ maxWidth: 720, margin: "48px auto", padding: "0 24px" }}>
      <h1>Run a simulation</h1>
      <p style={{ color: "#555" }}>
        Pick a capability, describe the change you want to test, and a sample of
        personas will react to it.
      </p>

      {loadingCaps && (
        <div style={{ marginTop: 24, color: "#666", fontSize: 14 }}>
          Loading capabilities...
        </div>
      )}

      {!loadingCaps && capsError && (
        <div style={emptyStateStyle}>
          <strong>{capsError}</strong>
        </div>
      )}

      {!loadingCaps && !capsError && !hasCapabilities && (
        <div style={emptyStateStyle}>
          <strong>
            No capabilities found for this customer. Run a crawl first.
          </strong>
        </div>
      )}

      {(submitError || validationError) && (
        <div style={errorBannerStyle}>{submitError ?? validationError}</div>
      )}

      <form
        onSubmit={handleSubmit}
        style={{
          marginTop: 24,
          display: "flex",
          flexDirection: "column",
          gap: 20,
          opacity: formDisabled && !submitting ? 0.6 : 1,
        }}
      >
        <div style={fieldGroup}>
          <label htmlFor="capability" style={labelStyle}>
            Capability
          </label>
          <select
            id="capability"
            value={capability}
            onChange={(e) => setCapability(e.target.value)}
            disabled={formDisabled}
            required
            style={inputStyle}
          >
            {!hasCapabilities && <option value="">(no capabilities)</option>}
            {capabilities.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>

        <div style={fieldGroup}>
          <label htmlFor="hypothesis" style={labelStyle}>
            Hypothesis
          </label>
          <textarea
            id="hypothesis"
            value={hypothesis}
            onChange={(e) => setHypothesis(e.target.value)}
            disabled={formDisabled}
            required
            rows={6}
            placeholder="e.g. If we surface a one-tap reorder CTA on the home screen for users who ordered in the last 14 days, weekly reorder rate will increase."
            style={{ ...inputStyle, resize: "vertical", fontFamily: "inherit" }}
          />
          <div style={helperStyle}>
            Describe the change you want to test. Be specific about who and what.
          </div>
        </div>

        <div style={fieldGroup}>
          <label htmlFor="population-size" style={labelStyle}>
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
            style={{ ...inputStyle, width: 160 }}
          />
          <div style={helperStyle}>
            How many users this hypothesis affects.{" "}
            {populationSize != null && populationSize > 0 ? (
              <>
                We&rsquo;ll stratify down to{" "}
                <strong>
                  {Math.min(populationSize, 50)} sampled agent
                  {Math.min(populationSize, 50) === 1 ? "" : "s"}
                </strong>{" "}
                in proportion to your persona weights.
              </>
            ) : (
              <>Enter a number between 1 and 10,000.</>
            )}
          </div>
        </div>

        {/* Phase 4.6 #88: A/B experiment-mode toggle + cost preview */}
        <ABModeSection
          enabled={abMode}
          onToggle={(next) => {
            setAbMode(next);
            // Clear stale acknowledgement when the user flips the toggle.
            if (!next) setAcknowledgedLargeRun(false);
          }}
          populationSize={populationSize}
          perArmCap={WIZARD_PER_ARM_CAP}
          confirmThreshold={CONFIRM_TOTAL_AGENTS_THRESHOLD}
          acknowledged={acknowledgedLargeRun}
          onAcknowledge={setAcknowledgedLargeRun}
          disabled={formDisabled || AB_MODE_DISABLED_UNTIL_LIFT}
          stagedRolloutNote={AB_MODE_DISABLED_UNTIL_LIFT}
        />

        <div style={fieldGroup}>
          {!showAdvanced ? (
            <button
              type="button"
              onClick={() => setShowAdvanced(true)}
              disabled={formDisabled}
              style={toggleBtnStyle}
            >
              + Advanced options (proposed PRD, persona filter)
            </button>
          ) : (
            <>
              <label htmlFor="proposed-prd" style={labelStyle}>
                Proposed PRD (optional)
              </label>
              <textarea
                id="proposed-prd"
                value={proposedPrd}
                onChange={(e) => setProposedPrd(e.target.value)}
                disabled={formDisabled}
                rows={6}
                placeholder="Paste a draft PRD for richer persona reactions..."
                style={{
                  ...inputStyle,
                  resize: "vertical",
                  fontFamily: "inherit",
                }}
              />

              {/* Phase 5 #101: persona filter checkbox list. Defaults to
                  all checked (today's behavior); narrowing is opt-in. */}
              <PersonaFilterSection
                personas={activePersonas}
                packVersion={packVersion}
                loading={loadingPersonas}
                error={personasError}
                selected={selectedPersonas}
                onChange={setSelectedPersonas}
                disabled={formDisabled}
              />

              <button
                type="button"
                onClick={() => {
                  setShowAdvanced(false);
                  setProposedPrd("");
                  // Reset the persona filter to "all" when the disclosure
                  // closes -- otherwise a narrowed-then-hidden filter would
                  // silently apply at submit without the PM seeing it.
                  setSelectedPersonas(
                    new Set(activePersonas.map((p) => p.id)),
                  );
                }}
                style={{ ...toggleBtnStyle, marginTop: 8 }}
              >
                - Hide advanced options
              </button>
            </>
          )}
        </div>

        <div>
          <button
            type="submit"
            disabled={formDisabled}
            style={{
              ...primaryBtnStyle,
              opacity: formDisabled ? 0.5 : 1,
              cursor: formDisabled ? "not-allowed" : "pointer",
            }}
          >
            {submitting ? "Submitting..." : "Run simulation"}
          </button>
        </div>
      </form>
    </main>
  );
}

// Phase 4.6 #88 — A/B experiment mode toggle + cost preview.
// Surfaces the wizard UX for arm_split. Wizard sends treatment_fraction=0.5
// when enabled (paired sampling per docs/4.6 Q3); slider hidden in v1 since
// non-50/50 splits are statistically wasteful for paired mode.
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
}: {
  enabled: boolean;
  onToggle: (next: boolean) => void;
  populationSize: number | null;
  perArmCap: number;
  confirmThreshold: number;
  acknowledged: boolean;
  onAcknowledge: (next: boolean) => void;
  disabled: boolean;
  // Phase 4.6 STAGED ROLLOUT: when true, the toggle is rendered but
  // checkbox is disabled with a "coming in next PR" badge. Set by the
  // parent when AB_MODE_DISABLED_UNTIL_LIFT is on. Once #89 wires the
  // dual-arm runner, the parent flips this to false.
  stagedRolloutNote: boolean;
}) {
  const perArm =
    populationSize != null ? Math.min(populationSize, perArmCap) : 0;
  const totalAgents = 2 * perArm;
  const isLarge = totalAgents > confirmThreshold;

  return (
    <div style={fieldGroup}>
      <label
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontSize: 14,
          color: disabled ? "#999" : "#333",
          cursor: disabled ? "not-allowed" : "pointer",
        }}
      >
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => onToggle(e.target.checked)}
          disabled={disabled}
          aria-describedby="ab-mode-helper"
        />
        <span>
          Run as an A/B simulation (treatment vs control){" "}
          <span style={{ color: "#888", fontWeight: 400 }}>
            — predicts a lift, costs ~2×
          </span>
          {stagedRolloutNote && (
            <span
              style={{
                marginLeft: 8,
                fontSize: 11,
                padding: "2px 8px",
                borderRadius: 999,
                background: "#f0e6ff",
                color: "#5a2ca0",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: 0.5,
              }}
            >
              Coming next
            </span>
          )}
        </span>
      </label>
      {stagedRolloutNote && (
        <div
          style={{
            ...helperStyle,
            marginLeft: 24,
            color: "#5a2ca0",
          }}
        >
          A/B execution runs end-to-end now (#89), but the result page
          still shows confidence — not lift. The wizard toggle stays
          disabled until #90 (paired lift formula) + #91 (lift display)
          land so PMs never see a single-arm score over a mixed cohort.
        </div>
      )}
      {!stagedRolloutNote && (
        <div id="ab-mode-helper" style={{ ...helperStyle, marginLeft: 24 }}>
          {enabled && populationSize != null && populationSize > 0 ? (
            <>
              ≈ <strong>{perArm} treatment + {perArm} control</strong> ={" "}
              <strong>{totalAgents} LLM agents</strong> for this run. Each
              persona is paired across arms (same identity reacts to BOTH the
              current product and the proposed change), so the lift is a
              within-persona delta — not an apples-to-oranges comparison.
            </>
          ) : enabled ? (
            <>Enter a population size above to see the agent count.</>
          ) : (
            <>
              Off by default. When on, the simulator runs both a treatment
              arm (sees the proposed change) and a control arm (sees the
              current product), and reports a predicted lift between them.
            </>
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
            marginLeft: 24,
            padding: "10px 12px",
            background: "#fff7e6",
            border: "1px solid #f0d090",
            borderRadius: 6,
            fontSize: 13,
            color: "#664500",
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

const inputStyle: React.CSSProperties = {
  padding: "10px 12px",
  borderRadius: 6,
  border: "1px solid #ddd",
  width: "100%",
  fontSize: 14,
  boxSizing: "border-box",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontWeight: 500,
  marginBottom: 6,
  fontSize: 14,
};

const helperStyle: React.CSSProperties = {
  marginTop: 6,
  color: "#666",
  fontSize: 13,
};

const fieldGroup: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
};

const primaryBtnStyle: React.CSSProperties = {
  background: "#111",
  color: "#fff",
  border: "1px solid #111",
  borderRadius: 6,
  padding: "10px 16px",
  fontWeight: 500,
  fontSize: 14,
  cursor: "pointer",
};

const toggleBtnStyle: React.CSSProperties = {
  background: "transparent",
  color: "#111",
  border: "none",
  padding: 0,
  fontWeight: 500,
  fontSize: 14,
  cursor: "pointer",
  textAlign: "left",
  textDecoration: "underline",
  alignSelf: "flex-start",
};

const errorBannerStyle: React.CSSProperties = {
  marginTop: 24,
  padding: "12px 16px",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  borderRadius: 6,
  color: "#991b1b",
  fontSize: 14,
};

const emptyStateStyle: React.CSSProperties = {
  marginTop: 24,
  padding: 16,
  background: "#fafafa",
  borderRadius: 6,
  color: "#666",
  fontSize: 14,
  border: "1px solid #eee",
};

// Phase 5 #101 — Persona filter section.
// Renders inside the wizard's Advanced disclosure. All personas checked by
// default; PM unchecks to narrow the cohort. Submit payload sends `null` for
// "all checked" and an explicit subset only when narrowed (matches backend's
// "None = all" convention, keeps persisted sim row tidy).
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
      <div style={{ marginTop: 16, fontSize: 13, color: "#888" }}>
        Loading personas…
      </div>
    );
  }
  if (error) {
    // Non-fatal: the parent still submits with selected_personas: null
    // (= all personas), so we don't block the form. Surface the error so
    // the PM knows narrowing isn't available.
    return (
      <div
        style={{
          marginTop: 16,
          padding: "8px 12px",
          fontSize: 13,
          color: "#a86b00",
          background: "#fff8e6",
          border: "1px solid #f0d68c",
          borderRadius: 4,
        }}
      >
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
    <div style={{ marginTop: 20 }}>
      <label style={labelStyle}>
        Persona filter (optional)
      </label>
      <div style={{ fontSize: 13, color: "#666", marginBottom: 8 }}>
        Run only against selected personas. Defaults to all{" "}
        {personas.length} personas in pack <code>{packVersion}</code>. When
        narrowed, the simulator re-weights the selected personas and
        allocates the full population across just those.
      </div>
      <div
        style={{
          display: "flex",
          gap: 12,
          fontSize: 12,
          marginBottom: 8,
          color: "#1d4ed8",
        }}
      >
        <button
          type="button"
          onClick={() => onChange(new Set(personas.map((p) => p.id)))}
          disabled={disabled || allChecked}
          style={{
            background: "transparent",
            border: "none",
            color: allChecked ? "#aaa" : "#1d4ed8",
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
            color: noneChecked ? "#aaa" : "#1d4ed8",
            cursor: noneChecked ? "default" : "pointer",
            padding: 0,
            textDecoration: "underline",
            fontSize: 12,
          }}
        >
          Clear all
        </button>
      </div>
      <ul
        style={{
          listStyle: "none",
          padding: 0,
          margin: 0,
          border: "1px solid #eee",
          borderRadius: 6,
        }}
      >
        {personas.map((p, i) => {
          const isChecked = selected.has(p.id);
          return (
            <li
              key={p.id}
              style={{
                padding: "8px 12px",
                borderTop: i === 0 ? "none" : "1px solid #f3f3f3",
              }}
            >
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  cursor: disabled ? "not-allowed" : "pointer",
                  fontSize: 14,
                  color: "#111",
                }}
              >
                <input
                  type="checkbox"
                  checked={isChecked}
                  disabled={disabled}
                  onChange={() => toggle(p.id)}
                />
                <span style={{ flex: 1 }}>{p.name}</span>
                <span
                  style={{
                    fontSize: 12,
                    color: "#888",
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {(p.weight * 100).toFixed(0)}% of population
                </span>
              </label>
            </li>
          );
        })}
      </ul>
      {noneChecked && (
        <div style={{ marginTop: 6, fontSize: 13, color: "#a30000" }}>
          Select at least one persona — empty filter is rejected.
        </div>
      )}
      {!allChecked && !noneChecked && (
        <div style={{ marginTop: 6, fontSize: 12, color: "#666" }}>
          Filtered: {selected.size} of {personas.length} personas. Full
          population_size will be allocated across the selected cohort.
        </div>
      )}
    </div>
  );
}
