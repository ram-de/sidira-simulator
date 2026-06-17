// ───────────────────────────────────────────────────────────────────────────
// /v2/crawl-setup — the interactive config island (the one "use client" child).
//
// STATIC MOCK ONLY. The inputs are real focusable Console fields so the input
// states (§4.2/§4.11) read true in the preview, but the form never submits and
// never calls an API — onSubmit is prevented, every control is inert. It
// consumes ONLY components/v2 + the scoped v2-theme.css classes and the page's
// own token-driven CSS (no raw hex, no raw font names — CSS vars + tokens only).
//
// WORKING-class (§0.2): brutally quiet config. Ink + hairline + negative space;
// NO Population Field, no signal fill. The saturated accent is reserved for LIVE
// READINGS ONLY (§1.3, §1.9 signal budget) — a crawl setup has no live reading,
// so nothing here breathes. tnum on every numeral (depth, budget, workers, delay).
// ───────────────────────────────────────────────────────────────────────────
"use client";

import { useState, type FormEvent, type ReactNode } from "react";
import { Chip, Designator } from "@/components/v2";

// schedule cadence options — inert Chips; the resting choice carries ink, never
// a saturated fill (§1.9 budget). Cadence is provenance/config, not a reading.
const CADENCES = ["ONE-OFF", "DAILY", "WEEKLY"] as const;
type Cadence = (typeof CADENCES)[number];

export function CrawlSetupForm() {
  // Local-only state so the preview's inputs are genuinely interactive; nothing
  // leaves the island, nothing is submitted, no network request ever fires.
  const [cadence, setCadence] = useState<Cadence>("ONE-OFF");

  // Inert: the mock never dispatches a crawl. Prevent the default so no
  // navigation or network request fires from the (decorative) form element.
  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
  }

  return (
    <form onSubmit={onSubmit} noValidate className="v2-cs-form">
      {/* ── TARGET — where the crawl starts and how far it may reach ────────── */}
      <Group designator="TARGET" hint="Seed and the domain boundary the walk may not cross.">
        <Field
          id="v2-cs-seed"
          label="Seed URL"
          type="url"
          inputMode="url"
          placeholder="https://streamly.example"
          defaultValue="https://streamly.example"
        />
        <Field
          id="v2-cs-scope"
          label="Allowed-domain scope"
          type="text"
          placeholder="streamly.example"
          defaultValue="streamly.example"
        />
        <ToggleRow
          id="v2-cs-robots"
          label="Respect robots.txt"
          hint="Honour the host's crawl directives and disallow rules."
          defaultChecked
        />
      </Group>

      {/* ── SCOPE — the four numeric limits that bound the walk (all tnum) ──── */}
      <Group designator="SCOPE" hint="The limits that bound the walk. Numerals are recorded config, not a reading.">
        <div className="v2-cs-grid">
          <NumField
            id="v2-cs-depth"
            label="Max depth"
            unit="levels"
            defaultValue="4"
            min="1"
            max="12"
          />
          <NumField
            id="v2-cs-budget"
            label="Page budget"
            unit="pages"
            defaultValue="2,500"
          />
          <NumField
            id="v2-cs-workers"
            label="Parallelism"
            unit="workers"
            defaultValue="4"
            min="1"
            max="16"
          />
          <NumField
            id="v2-cs-delay"
            label="Crawl delay"
            unit="ms / page"
            defaultValue="750"
          />
        </div>
      </Group>

      {/* ── SCHEDULE — cadence (inert Chips) + the snapshot label ───────────── */}
      <Group designator="SCHEDULE" hint="Run once now, or recur on a cadence. The label stamps each snapshot.">
        <div className="v2-cs-field">
          <span className="v2-cs-label">Cadence</span>
          <div className="v2-cs-cadence" role="group" aria-label="Crawl cadence">
            {CADENCES.map((c) => {
              const active = c === cadence;
              return (
                <button
                  key={c}
                  type="button"
                  // inert preview affordance: toggles local-only ink emphasis,
                  // never dispatches or persists anything.
                  onClick={() => setCadence(c)}
                  className={
                    active
                      ? "v2-cs-cadence-opt v2-cs-cadence-opt--active"
                      : "v2-cs-cadence-opt"
                  }
                  aria-pressed={active}
                >
                  <Chip>{c}</Chip>
                </button>
              );
            })}
          </div>
        </div>
        <Field
          id="v2-cs-label"
          label="Snapshot label"
          type="text"
          placeholder="streamly · 2026-W25"
          defaultValue="streamly · 2026-W25"
        />
      </Group>
    </form>
  );
}

// ── a labelled config group — a mono designator + one-line hint over fields.
//    WORKING-quiet: hairline-separated, no panel-in-panel (§4.4). ─────────────
function Group({
  designator,
  hint,
  children,
}: {
  designator: string;
  hint: string;
  children: ReactNode;
}) {
  return (
    <section className="v2-cs-group">
      <div className="v2-cs-group-head">
        <Designator>{designator}</Designator>
        <p className="v2-cs-group-hint">{hint}</p>
      </div>
      <div className="v2-cs-group-body">{children}</div>
    </section>
  );
}

// ── a single labelled Console text input (§4.2). defaultValue keeps the field
//    interactive while staying uncontrolled — no state, fully inert. ──────────
function Field({
  id,
  label,
  type,
  placeholder,
  defaultValue,
  inputMode,
}: {
  id: string;
  label: string;
  type: string;
  placeholder: string;
  defaultValue?: string;
  inputMode?: "url" | "text";
}) {
  return (
    <div className="v2-cs-field">
      <label htmlFor={id} className="v2-cs-label">
        {label}
      </label>
      <input
        id={id}
        className="v2-cs-input"
        type={type}
        inputMode={inputMode}
        placeholder={placeholder}
        defaultValue={defaultValue}
        spellCheck={false}
        autoComplete="off"
      />
    </div>
  );
}

// ── a numeric Console input — the value renders in tnum mono; the unit prints
//    as a quiet mono suffix. Inert (uncontrolled defaultValue). ───────────────
function NumField({
  id,
  label,
  unit,
  defaultValue,
  min,
  max,
}: {
  id: string;
  label: string;
  unit: string;
  defaultValue: string;
  min?: string;
  max?: string;
}) {
  return (
    <div className="v2-cs-field">
      <label htmlFor={id} className="v2-cs-label">
        {label}
      </label>
      <div className="v2-cs-numwell">
        <input
          id={id}
          className="v2-cs-input v2-cs-input--num v2-mono v2-tnum"
          type="text"
          inputMode="numeric"
          defaultValue={defaultValue}
          aria-describedby={`${id}-unit`}
          data-min={min}
          data-max={max}
          spellCheck={false}
          autoComplete="off"
        />
        <span id={`${id}-unit`} className="v2-cs-unit v2-mono">
          {unit}
        </span>
      </div>
    </div>
  );
}

// ── a labelled toggle row — a quiet hairline switch (inert). Reads as ink, not
//    signal; the checked state is a neutral fill, never the live accent. ──────
function ToggleRow({
  id,
  label,
  hint,
  defaultChecked = false,
}: {
  id: string;
  label: string;
  hint: string;
  defaultChecked?: boolean;
}) {
  return (
    <label htmlFor={id} className="v2-cs-toggle">
      <span className="v2-cs-toggle-text">
        <span className="v2-cs-label">{label}</span>
        <span className="v2-cs-toggle-hint">{hint}</span>
      </span>
      {/* a native checkbox styled as a Console switch — focusable, inert */}
      <input
        id={id}
        type="checkbox"
        className="v2-cs-switch"
        defaultChecked={defaultChecked}
      />
    </label>
  );
}
