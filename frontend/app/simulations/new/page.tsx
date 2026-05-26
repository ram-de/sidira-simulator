"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiError,
  createSimulation,
  getCapabilities,
  type FeaturePackManifest,
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
  // Phase 4.6 STAGED ROLLOUT GATE: the toggle is DISABLED in this PR
  // because the runner doesn't honor `arm_split` yet — #89 wires the
  // dual-arm orchestrator that consumes this field. Without this gate a
  // PM could click the toggle, submit, get arm_split=0.5 back on the
  // result page, but actually get a single-arm execution — silent
  // user-facing mismatch (codex #93 [P1]). Flip this constant to false
  // when #89 lands.
  const AB_MODE_DISABLED_UNTIL_89 = true;
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

  const capabilities = manifest?.capabilities ?? [];
  const hasCapabilities = capabilities.length > 0;
  const formDisabled = loadingCaps || !hasCapabilities || submitting;

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
          disabled={formDisabled || AB_MODE_DISABLED_UNTIL_89}
          stagedRolloutNote={AB_MODE_DISABLED_UNTIL_89}
        />

        <div style={fieldGroup}>
          {!showAdvanced ? (
            <button
              type="button"
              onClick={() => setShowAdvanced(true)}
              disabled={formDisabled}
              style={toggleBtnStyle}
            >
              + Add proposed PRD
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
              <button
                type="button"
                onClick={() => {
                  setShowAdvanced(false);
                  setProposedPrd("");
                }}
                style={{ ...toggleBtnStyle, marginTop: 8 }}
              >
                - Hide proposed PRD
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
  // parent when AB_MODE_DISABLED_UNTIL_89 is on. Once #89 wires the
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
          A/B execution lands in the next PR (#89 — dual-arm orchestrator
          + control-arm prompt). The request shape is wired here so #89
          plugs in without a follow-up schema migration; the wizard
          toggle is disabled until the runner can honor it.
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
