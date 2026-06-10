"use client";

// Phase 4 #56 — shared 👍/👎 calibration thumbs.
// Tri-state: True = 👍, False = 👎, null = no thumb. Clicking the
// currently-active thumb toggles it OFF (third state).
//
// Optimistic UX: the parent passes `flag` + an async `onSet`. The
// control applies the change locally on click, then awaits the server.
// On server failure the parent restores the prior flag (we expose that
// via the `onSet` contract: throw to roll back).

import { useState } from "react";

import { TOKENS } from "@/lib/design";

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
        label="👍"
        ariaLabel="Realistic / useful"
        active={upActive}
        disabled={busy}
        size={size}
        onClick={() => setNext(upActive ? null : true)}
      />
      <ThumbButton
        label="👎"
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
            color: TOKENS.alert,
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
        background: active ? TOKENS.paperRecessed : "transparent",
        border: active ? `1px solid ${TOKENS.ink}` : `1px solid ${TOKENS.rule}`,
        borderRadius: 999,
        padding: `2px ${size <= 14 ? 6 : 8}px`,
        fontSize: size,
        lineHeight: 1,
        cursor: disabled ? "wait" : "pointer",
        opacity: disabled ? 0.6 : 1,
        // Native emoji rendering varies wildly across platforms; clamp
        // the line-box so the buttons stay the same height.
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {label}
    </button>
  );
}
