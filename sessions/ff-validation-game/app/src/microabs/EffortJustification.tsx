import { useState } from 'react';
import { logOutcome } from '../lib/api';
import { useBeat } from '../lib/useBeat';
import type { MicroAbConfig } from '../lib/types';

// MICRO-A/B 5 — Effort Justification (#441), within-subject.
// Counter-intuitive: a tiny bit of EARNED effort RAISES downstream commitment vs
// a frictionless one-tap — adding friction lifts follow-through (IKEA / effort-
// justification effect), the opposite of the "remove all friction" reflex.
// Obvious prior (the "more-is-better/obvious" observer): the ONE-TAP arm wins
// (less friction = more completion). We bet the EFFORT arm commits more.
//
// Each player sees ONE arm, randomized server-side (config.present.variant):
//   'effort'  → a tiny earned step (tap to "build" your badge in 3 taps) before
//               the commit ask.
//   'one_tap' → straight to the commit ask, no earned step.
// Binary OUTCOME → Table B: 1 = committed (joined the next round), 0 = declined.
// Arm recorded is the presentation label, never the server's headline-arm name.

const STEPS = 3;

export function EffortJustification({
  playerId, config, onDone, isLast,
}: { playerId: string; config: MicroAbConfig; onDone: () => void; isLast: boolean }) {
  const beat = useBeat();
  const variant = (config.present.variant as string) === 'effort' ? 'effort' : 'one_tap';
  const startedAt = useState(() => new Date().toISOString())[0];
  const [built, setBuilt] = useState(variant === 'effort' ? 0 : STEPS);
  const [done, setDone] = useState(false);

  const earned = built >= STEPS;

  function build() {
    beat.onTap();
    setBuilt((n) => Math.min(n + 1, STEPS));
  }

  function finish(outcome: 0 | 1) {
    if (done) return;
    setDone(true);
    void logOutcome({
      playerId,
      arm: `effort:${variant}`,
      taskId: 'effort_justification',
      outcome,
      startedAt,
      decidedAt: new Date().toISOString(),
      done: isLast,
    }).finally(onDone);
  }

  return (
    <div className="screen">
      <h2>Join the next round?</h2>
      {variant === 'effort' && !earned ? (
        <>
          <p className="lede">Build your player badge to unlock the next round — {built}/{STEPS} taps.</p>
          <div className="card">
            <button className="btn ghost" onClick={build}>Tap to build ({built}/{STEPS})</button>
          </div>
        </>
      ) : (
        <>
          <p className="lede">
            {variant === 'effort'
              ? 'Your badge is ready. Lock in for the next round?'
              : 'One tap to join the next round.'}
          </p>
          <div className="choices" onTouchStart={beat.onTap} onMouseDown={beat.onTap}>
            <button className="btn" onClick={() => finish(1)} disabled={done}>Count me in</button>
            <button className="btn ghost" onClick={() => finish(0)} disabled={done}>Not this time</button>
          </div>
        </>
      )}
    </div>
  );
}
