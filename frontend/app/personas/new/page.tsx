"use client";

import { useState } from "react";
import { TOKENS, FONT_SANS } from "@/lib/design";

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
    <main style={{ maxWidth: 960, margin: "48px auto", padding: "0 24px", fontFamily: FONT_SANS }}>
      <h1>New persona pack</h1>
      <p style={{ color: TOKENS.inkMuted }}>
        Walk through 7 steps to build a versioned persona pack from your Snowflake data.
      </p>

      <Stepper current={step} />

      <section
        style={{
          marginTop: 32,
          border: `0.75px solid ${TOKENS.rule}`,
          borderRadius: 4,
          padding: 24,
          minHeight: 280,
          background: TOKENS.paperElevated,
        }}
      >
        <h2 style={{ marginTop: 0 }}>
          Step {step}: {STEPS[step - 1].label}
        </h2>
        <p style={{ color: TOKENS.inkMuted }}>{STEPS[step - 1].description}</p>

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
              borderRadius: 4,
              border: `0.75px solid ${active ? TOKENS.ink : TOKENS.rule}`,
              background: done ? TOKENS.paperRecessed : TOKENS.paperElevated,
              fontSize: 13,
              color: active ? TOKENS.ink : TOKENS.inkMuted,
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
        <Stub message="Connect your Snowflake account — account, user, warehouse, role, database, and schema." />
      );
    case 2:
      return (
        <Stub message="Pick a table from your schemas, or paste SQL that defines the population to model." />
      );
    case 3:
      return (
        <Stub message="Map your columns onto the seven feature groups, with LLM-suggested matches pre-filled for review." />
      );
    case 4:
      return (
        <Stub message="Sanity-check row count, null coverage per column, and distribution skews before committing compute." />
      );
    case 5:
      return (
        <Stub message="Choose the cluster count (or let it auto-select), the stability threshold, the weighting scheme, and the model that names personas." />
      );
    case 6:
      return (
        <Stub message="Watch the build land step by step — encoding users, clustering, naming personas — with the stability score updating as it goes." />
      );
    case 7:
      return (
        <Stub message="Review the resulting personas — names, descriptions, jobs-to-be-done, behavioral snapshots — and promote the pack to active." />
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
        background: TOKENS.paperElevated,
        borderRadius: 4,
        color: TOKENS.inkMuted,
        fontSize: 14,
        lineHeight: 1.6,
      }}
    >
      <strong>This step isn&apos;t wired up yet.</strong> {message}
    </div>
  );
}

function navBtn(disabled: boolean, primary = false): React.CSSProperties {
  return {
    padding: "8px 16px",
    borderRadius: 4,
    border: `0.75px solid ${primary ? TOKENS.ink : TOKENS.rule}`,
    background: disabled ? TOKENS.paperRecessed : primary ? TOKENS.ink : TOKENS.paperElevated,
    color: disabled ? TOKENS.inkMuted : primary ? TOKENS.paper : TOKENS.ink,
    cursor: disabled ? "not-allowed" : "pointer",
    fontWeight: 500,
  };
}
