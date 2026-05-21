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
  const [sampleSize, setSampleSize] = useState<number>(6);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [proposedPrd, setProposedPrd] = useState<string>("");

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
    if (sampleSize < 1 || sampleSize > 50 || Number.isNaN(sampleSize)) {
      setValidationError("Sample size must be between 1 and 50.");
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
      persona_sample_size: sampleSize,
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
          <label htmlFor="sample-size" style={labelStyle}>
            Sample size
          </label>
          <input
            id="sample-size"
            type="number"
            min={1}
            max={50}
            value={sampleSize}
            onChange={(e) => setSampleSize(parseInt(e.target.value, 10) || 0)}
            disabled={formDisabled}
            style={{ ...inputStyle, width: 120 }}
          />
          <div style={helperStyle}>
            How many personas should react (6-10 is a good starting point).
          </div>
        </div>

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
