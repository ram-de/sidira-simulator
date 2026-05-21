"use client";

import { useState } from "react";

const STEPS = [
  { id: 1, label: "Connect", description: "Snowflake credentials" },
  { id: 2, label: "Source", description: "Pick a table or paste SQL" },
  { id: 3, label: "Map", description: "Columns → 7 feature groups" },
  { id: 4, label: "Preview", description: "Population stats + skews" },
  { id: 5, label: "Configure", description: "k, stability, weights, LLM" },
  { id: 6, label: "Build", description: "Live progress" },
  { id: 7, label: "Review", description: "Personas + promote" },
] as const;

export default function NewPersonaPackPage() {
  const [step, setStep] = useState(1);

  return (
    <main style={{ maxWidth: 960, margin: "48px auto", padding: "0 24px" }}>
      <h1>New persona pack</h1>
      <p style={{ color: "#555" }}>
        Walk through 7 steps to build a versioned persona pack from your Snowflake data.
      </p>

      <Stepper current={step} />

      <section
        style={{
          marginTop: 32,
          border: "1px solid #eee",
          borderRadius: 8,
          padding: 24,
          minHeight: 280,
        }}
      >
        <h2 style={{ marginTop: 0 }}>
          Step {step}: {STEPS[step - 1].label}
        </h2>
        <p style={{ color: "#666" }}>{STEPS[step - 1].description}</p>

        <StepBody step={step} />

        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 32 }}>
          <button
            onClick={() => setStep((s) => Math.max(1, s - 1))}
            disabled={step === 1}
            style={navBtn(step === 1)}
          >
            ← Back
          </button>
          <button
            onClick={() => setStep((s) => Math.min(STEPS.length, s + 1))}
            disabled={step === STEPS.length}
            style={navBtn(step === STEPS.length, true)}
          >
            Next →
          </button>
        </div>
      </section>
    </main>
  );
}

function Stepper({ current }: { current: number }) {
  return (
    <div style={{ display: "flex", gap: 8, marginTop: 24 }}>
      {STEPS.map((s) => {
        const active = s.id === current;
        const done = s.id < current;
        return (
          <div
            key={s.id}
            style={{
              flex: 1,
              padding: "10px 12px",
              borderRadius: 6,
              border: "1px solid " + (active ? "#111" : "#ddd"),
              background: done ? "#f4f4f4" : "#fff",
              fontSize: 13,
              color: active ? "#111" : "#666",
              fontWeight: active ? 600 : 400,
            }}
          >
            <div>Step {s.id}</div>
            <div>{s.label}</div>
          </div>
        );
      })}
    </div>
  );
}

function StepBody({ step }: { step: number }) {
  switch (step) {
    case 1:
      return (
        <Stub
          message="Snowflake credentials form: account, user, password, warehouse, role, database, schema. POST /feature-stores."
        />
      );
    case 2:
      return (
        <Stub message="Table picker (browse schemas) OR SQL textarea. Hits POST /feature-stores/{id}/preview." />
      );
    case 3:
      return (
        <Stub message="7 feature groups on the left, your columns on the right. LLM suggestions pre-filled via POST /feature-stores/{id}/suggest-mapping." />
      );
    case 4:
      return (
        <Stub message="Row count, NULL coverage per column, distribution skews (e.g. 88% Active in the DoorDash sample). Sanity-check before committing compute." />
      );
    case 5:
      return (
        <Stub message="k (or auto), stability threshold (default 0.65), LLM provider (Groq / Anthropic), weight schemes (head_count / order_weighted / revenue_weighted)." />
      );
    case 6:
      return (
        <Stub message="Streams JobRun events: 'Encoding 10K users', 'Clustering k=7', 'Naming P03 via Groq', stability score updating live." />
      );
    case 7:
      return (
        <Stub message="Resulting personas with names, descriptions, JTBD, behavioral snapshots, stability score. CTA: Promote to latest." />
      );
    default:
      return null;
  }
}

function Stub({ message }: { message: string }) {
  return (
    <div
      style={{
        marginTop: 24,
        padding: 16,
        background: "#fafafa",
        borderRadius: 6,
        color: "#666",
        fontSize: 14,
        lineHeight: 1.6,
      }}
    >
      <strong>Phase 4.5 placeholder.</strong> {message}
    </div>
  );
}

function navBtn(disabled: boolean, primary = false): React.CSSProperties {
  return {
    padding: "8px 16px",
    borderRadius: 6,
    border: primary ? "1px solid #111" : "1px solid #ddd",
    background: disabled ? "#f4f4f4" : primary ? "#111" : "#fff",
    color: disabled ? "#aaa" : primary ? "#fff" : "#111",
    cursor: disabled ? "not-allowed" : "pointer",
    fontWeight: 500,
  };
}
