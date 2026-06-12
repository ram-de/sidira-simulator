"use client";

// Phase 4 #56 — shared calibration feedback control.
// Tri-state: True = "+" (realistic / useful), False = "−" (off /
// unrealistic), null = no rating. Clicking the currently-active chip
// toggles it OFF (third state).
//
// R2 #170 restyle: typographic +/− glyphs on radius-2 mono chips per
// DESIGN.md §8.5 (sentiment is ink-weight data, never emoji, never
// alert-red) and §10 (no border-radius: 9999px pills, no emoji
// affordances). Behavior, props, and aria contract are unchanged.
//
// Optimistic UX: the parent passes `flag` + an async `onSet`. The
// control applies the change locally on click, then awaits the server.
// On server failure the parent restores the prior flag (we expose that
// via the `onSet` contract: throw to roll back).

import { useState } from "react";

import { FONT_MONO, TOKENS } from "@/lib/design";

export function ThumbsControl({
  flag,
  onSet,
  size = 14,
  ariaLabel,
}: {
  flag: boolean | null;
  // Returns a promise; if it rejects, we roll back to the prior value.
  onSet: (next: boolean | null) => Promise<void>;
  size?: number;
  ariaLabel?: string;
}) {
  // We mirror the prop into local state so optimistic updates feel
  // instant — but we keep a ref to the last server-confirmed value so
  // a failed POST can roll back cleanly without flicker.
  const [optimistic, setOptimistic] = useState<boolean | null>(flag);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // Sync incoming prop changes (e.g. canonical state from a server
  // refetch) into the optimistic state. Doing this in render is OK here
  // because the only writes are user-driven within this component.
  if (!busy && flag !== optimistic && err === null) {
    setOptimistic(flag);
  }

  async function setNext(next: boolean | null) {
    if (busy) return;
    const prior = optimistic;
    setOptimistic(next);
    setErr(null);
    setBusy(true);
    try {
      await onSet(next);
    } catch (e) {
      setOptimistic(prior);
      setErr(e instanceof Error ? e.message : "Feedback failed.");
    } finally {
      setBusy(false);
    }
  }

  const upActive = optimistic === true;
  const downActive = optimistic === false;

  return (
    <span
      role="group"
      aria-label={ariaLabel ?? "Calibration feedback"}
      style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
    >
      <ThumbButton
        label="+"
        ariaLabel="Realistic / useful"
        active={upActive}
        disabled={busy}
        size={size}
        onClick={() => setNext(upActive ? null : true)}
      />
      <ThumbButton
        label="−"
        ariaLabel="Off / unrealistic"
        active={downActive}
        disabled={busy}
        size={size}
        onClick={() => setNext(downActive ? null : false)}
      />
      {err && (
        <span
          aria-live="polite"
          style={{
            fontSize: 11,
            // §4.3 — alert text is reserved for mono designators/chips; this
            // sans label co-signals by wording, so it reads in muted ink.
            color: TOKENS.inkMuted,
            marginLeft: 4,
          }}
          title={err}
        >
          (failed)
        </span>
      )}
    </span>
  );
}

function ThumbButton({
  label,
  ariaLabel,
  active,
  disabled,
  size,
  onClick,
}: {
  label: string;
  ariaLabel: string;
  active: boolean;
  disabled: boolean;
  size: number;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
      style={{
        // Active is ink-weight, not color-coded — sentiment polarity never
        // gets a semantic color (DESIGN.md §8.5; negative is never alert).
        background: active ? TOKENS.paperRecessed : "transparent",
        border: active ? `1px solid ${TOKENS.ink}` : `1px solid ${TOKENS.rule}`,
        color: active ? TOKENS.ink : TOKENS.inkMuted,
        borderRadius: 2,
        padding: "2px 7px",
        fontFamily: FONT_MONO,
        // The `size` prop historically sized 14px-ish emoji; mono glyph
        // chips read right a step smaller, floored at the 10px type floor.
        fontSize: Math.max(10, Math.round(size * 0.8)),
        lineHeight: 1.4,
        cursor: disabled ? "wait" : "pointer",
        opacity: disabled ? 0.6 : 1,
        transition: "border-color 80ms ease-out, color 80ms ease-out",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {label}
    </button>
  );
}
