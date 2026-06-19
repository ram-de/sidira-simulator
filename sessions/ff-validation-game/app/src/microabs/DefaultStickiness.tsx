import { useState } from 'react';
import { logOutcome } from '../lib/api';
import { useBeat } from '../lib/useBeat';
import type { MicroAbConfig } from '../lib/types';

// MICRO-A/B 3 — Default Stickiness (#441), within-subject.
// Counter-intuitive: a pre-checked "safe" default + "most people lock in" social
// proof produces stickier behavior than a clean prospect-theory framing — i.e.
// DEFAULT stickiness beats the framing the obvious bettor would back.
// Obvious prior (the "more-is-better/obvious" observer): the polished
// prospect-theory FRAMING arm wins (a persuasive, gain-framed pitch lifts
// lock-in more than a quiet pre-checked box). We bet the DEFAULT arm wins.
//
// Each player sees ONE arm, randomized server-side (config.present.variant):
//   'default' → a pre-checked "Keep my coins safe" box + "most players lock in".
//   'framing' → a neutral screen with a gain-framed prospect-theory pitch.
// Binary OUTCOME → Table B: 1 = stayed locked in (kept the safe choice),
//                            0 = opted out / changed it.
// Arm recorded is the presentation label ('default'/'framing'), never the
// server's internal headline-arm name.

export function DefaultStickiness({
  playerId, config, onDone, isLast,
}: { playerId: string; config: MicroAbConfig; onDone: () => void; isLast: boolean }) {
  const beat = useBeat();
  const variant = (config.present.variant as string) === 'framing' ? 'framing' : 'default';
  const startedAt = useState(() => new Date().toISOString())[0];
  const [done, setDone] = useState(false);

  function finish(outcome: 0 | 1) {
    if (done) return;
    setDone(true);
    void logOutcome({
      playerId,
      arm: `stickiness:${variant}`,
      taskId: 'default_stickiness',
      outcome,
      startedAt,
      decidedAt: new Date().toISOString(),
      done: isLast,
    }).finally(onDone);
  }

  return (
    <div className="screen">
      <h2>Lock your coins in?</h2>
      {variant === 'default' ? (
        <>
          <p className="lede">
            <label className="checkrow">
              <input type="checkbox" defaultChecked readOnly /> Keep my coins safely locked in
            </label>
          </p>
          <p className="statline">Most players lock in and keep this on.</p>
        </>
      ) : (
        <p className="lede">
          Lock in now and you secure a guaranteed gain — leave them out and you risk losing the
          ground you&apos;ve made.
        </p>
      )}
      <div className="choices" onTouchStart={beat.onTap} onMouseDown={beat.onTap}>
        <button className="btn" onClick={() => finish(1)} disabled={done}>Keep it locked in</button>
        <button className="btn ghost" onClick={() => finish(0)} disabled={done}>Take them back out</button>
      </div>
    </div>
  );
}
