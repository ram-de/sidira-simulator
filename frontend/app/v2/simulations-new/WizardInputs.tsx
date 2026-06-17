// ───────────────────────────────────────────────────────────────────────────
// /v2/simulations-new — the interactive (but INERT) wizard inputs.
//
// STATIC MOCK ONLY. These are real focusable Console fields so the input states
// (§4.2/§4.11) read true in the preview, but nothing here submits and nothing
// calls an API: the form's onSubmit is prevented, the radios/textarea/text
// fields hold local-only state, and the "Run reading" affordance lives in the
// AppFrame top bar as an inert link. This island exists ONLY so the page above
// can stay a server component.
//
// Consumes ONLY components/v2 + the scoped v2-theme.css classes (.v2-new-*).
// No raw hex, no raw font names — every value is a CSS var or a token class.
// ───────────────────────────────────────────────────────────────────────────
"use client";

import { useState, type FormEvent } from "react";
import { Chip, CalGlyph } from "@/components/v2";

// ── static option data (consts) ─────────────────────────────────────────────

type Pack = { id: string; name: string; n: string; note: string };
const PACKS: Pack[] = [
  { id: "streamly-w25", name: "Streamly · synthetic 6-segment", n: "2,500", note: "v_2 · 2026-W25" },
  { id: "founders-v1", name: "Founders · real persona pack", n: "1,840", note: "v_1 · org_3Ev" },
  { id: "cookie-cats", name: "Cookie Cats · gate cohort", n: "9,040", note: "v_1 · external A/B" },
];

type Metric = { id: string; name: string; unit: string; blinded: boolean };
const METRICS: Metric[] = [
  { id: "retention", name: "Day-7 retention", unit: "pp", blinded: true },
  { id: "intent", name: "Purchase intent", unit: "pp", blinded: false },
  { id: "ctr", name: "Headline CTR", unit: "ρ", blinded: false },
];

// ── the wizard form (one prevented submit, all inputs inert) ─────────────────

export function WizardInputs() {
  const [pack, setPack] = useState(PACKS[0].id);
  const [hypothesis, setHypothesis] = useState(
    "Moving the cookie gate from level 30 to level 40 raises day-7 retention " +
      "for new players, because it defers the first paywall past the habit-" +
      "forming early sessions.",
  );
  const [metric, setMetric] = useState(METRICS[0].id);
  const [control, setControl] = useState("Gate at level 30 (current production build).");
  const [treatment, setTreatment] = useState("Gate at level 40 (deferred first paywall).");

  // Inert: the mock never runs a reading. Prevent the default so no navigation
  // or network request ever fires.
  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
  }

  const hLen = hypothesis.trim().length;
  // a small, static answerability hint — NOT a score (input answerability gate).
  const answerable = hLen >= 80 && /because|raises|lowers|because|defers|so that/i.test(hypothesis);

  return (
    <form className="v2-new-form" onSubmit={onSubmit} noValidate>
      {/* ── Step 1 · Population ───────────────────────────────────────────── */}
      <fieldset className="v2-new-field" id="step-population">
        <legend className="v2-new-legend">Persona pack</legend>
        <div className="v2-new-radios" role="radiogroup" aria-label="Persona pack">
          {PACKS.map((p) => {
            const on = p.id === pack;
            return (
              <label
                key={p.id}
                className={on ? "v2-new-radio v2-new-radio--on" : "v2-new-radio"}
              >
                <input
                  type="radio"
                  name="v2-new-pack"
                  value={p.id}
                  checked={on}
                  onChange={() => setPack(p.id)}
                  className="v2-new-radio-input"
                />
                <span className="v2-new-radio-mark" aria-hidden />
                <span className="v2-new-radio-body">
                  <span className="v2-new-radio-name">{p.name}</span>
                  <span className="v2-new-radio-meta v2-mono">
                    <span className="v2-tnum">{p.n}</span> agents · {p.note}
                  </span>
                </span>
              </label>
            );
          })}
        </div>
      </fieldset>

      {/* ── Step 2 · Hypothesis ───────────────────────────────────────────── */}
      <fieldset className="v2-new-field" id="step-hypothesis">
        <legend className="v2-new-legend">Composed hypothesis</legend>
        <textarea
          id="v2-new-hypothesis"
          className="v2-new-textarea"
          rows={4}
          value={hypothesis}
          onChange={(e) => setHypothesis(e.target.value)}
          spellCheck={false}
          aria-describedby="v2-new-answerability"
        />
        <p id="v2-new-answerability" className="v2-new-hint">
          <span className="v2-new-hint-mark" aria-hidden>
            {answerable ? "▣" : "▢"}
          </span>
          <span className="v2-new-hint-text">
            {answerable
              ? "Answerable — states a directional claim with a mechanism. This is a gate, not a score."
              : "Add a directional claim and a mechanism (“because…”) so the reading can answer it."}
          </span>
        </p>
      </fieldset>

      {/* ── Step 3 · Metric ───────────────────────────────────────────────── */}
      <fieldset className="v2-new-field" id="step-metric">
        <legend className="v2-new-legend">Outcome metric</legend>
        <div className="v2-new-radios" role="radiogroup" aria-label="Outcome metric">
          {METRICS.map((m) => {
            const on = m.id === metric;
            return (
              <label
                key={m.id}
                className={on ? "v2-new-radio v2-new-radio--on" : "v2-new-radio"}
              >
                <input
                  type="radio"
                  name="v2-new-metric"
                  value={m.id}
                  checked={on}
                  onChange={() => setMetric(m.id)}
                  className="v2-new-radio-input"
                />
                <span className="v2-new-radio-mark" aria-hidden />
                <span className="v2-new-radio-body">
                  <span className="v2-new-radio-name">
                    {m.name}{" "}
                    <span className="v2-new-radio-unit v2-mono">/ {m.unit}</span>
                  </span>
                  <span className="v2-new-radio-meta">
                    {m.blinded ? (
                      <>
                        <CalGlyph /> blinded-pass available — read alongside
                        sentiment, never alone
                      </>
                    ) : (
                      "direct read — no blinded-pass calibration on this metric"
                    )}
                  </span>
                </span>
              </label>
            );
          })}
        </div>
      </fieldset>

      {/* ── Step 4 · Variants (A/B) ───────────────────────────────────────── */}
      <fieldset className="v2-new-field" id="step-variants">
        <legend className="v2-new-legend">Variants</legend>
        <div className="v2-new-variants">
          <div className="v2-new-variant">
            <div className="v2-new-variant-head">
              <Chip>CONTROL · A</Chip>
            </div>
            <textarea
              id="v2-new-control"
              className="v2-new-textarea v2-new-textarea--sm"
              rows={2}
              value={control}
              onChange={(e) => setControl(e.target.value)}
              spellCheck={false}
              aria-label="Control variant description"
            />
          </div>
          <div className="v2-new-variant">
            <div className="v2-new-variant-head">
              <Chip>TREATMENT · B</Chip>
            </div>
            <textarea
              id="v2-new-treatment"
              className="v2-new-textarea v2-new-textarea--sm"
              rows={2}
              value={treatment}
              onChange={(e) => setTreatment(e.target.value)}
              spellCheck={false}
              aria-label="Treatment variant description"
            />
          </div>
        </div>
      </fieldset>
    </form>
  );
}
