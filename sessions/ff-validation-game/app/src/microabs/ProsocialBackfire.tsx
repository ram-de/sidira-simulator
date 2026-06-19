import { useState } from 'react';
import { logOutcome } from '../lib/api';
import { useBeat } from '../lib/useBeat';
import type { MicroAbConfig } from '../lib/types';

// MICRO-A/B 4 — Prosocial Impact Backfire (#441), within-subject.
// Counter-intuitive: a polished "your impact compounds" blurb REDUCES giving vs
// a sparse screen — the persuasion reads as a pitch and triggers skepticism in
// an F&F "I know I'm being sold to" audience.
// Obvious prior (the "more-is-better/obvious" observer): the POLISHED arm wins
// (a vivid impact story lifts generosity). We bet the SPARSE arm gives more.
//
// Each player sees ONE arm, randomized server-side (config.present.variant):
//   'polished' → a glossy "your impact compounds" explanation.
//   'sparse'   → a bare "split your bonus" screen, no persuasion.
// Mechanic: the player splits a 10-coin bonus between THEMSELVES and a shared
// pool. Binary OUTCOME → Table B measures the spec's "≥50% allocated away from
// self": 1 = gave at least half to the pool, 0 = kept more than half.
// Arm recorded is the presentation label, never the server's headline-arm name.

const SPLITS = [0, 2, 5, 8, 10]; // coins given AWAY to the shared pool (of 10)

export function ProsocialBackfire({
  playerId, config, onDone, isLast,
}: { playerId: string; config: MicroAbConfig; onDone: () => void; isLast: boolean }) {
  const beat = useBeat();
  const variant = (config.present.variant as string) === 'polished' ? 'polished' : 'sparse';
  const startedAt = useState(() => new Date().toISOString())[0];
  const [done, setDone] = useState(false);

  function finish(given: number) {
    if (done) return;
    setDone(true);
    // Primary binary outcome: allocated AT LEAST HALF away from self (spec: "≥50%
    // allocated away from self"). 5 of 10 coins given → outcome 1.
    const outcome: 0 | 1 = given >= 5 ? 1 : 0;
    void logOutcome({
      playerId,
      arm: `prosocial:${variant}`,
      taskId: 'prosocial_backfire',
      outcome,
      startedAt,
      decidedAt: new Date().toISOString(),
      done: isLast,
    }).finally(onDone);
  }

  return (
    <div className="screen">
      <h2>Split your bonus</h2>
      {variant === 'polished' ? (
        <div className="card">
          <p>
            Every coin you share into the pool <strong>compounds</strong> — it&apos;s matched, pooled,
            and pays forward to every player. Your impact grows far beyond what you give.
          </p>
        </div>
      ) : (
        <p className="lede">You have a 10-coin bonus. Keep it, or share some into the pool.</p>
      )}
      <p className="statline">How many of your 10 coins go to the shared pool?</p>
      <div className="choices grid" onTouchStart={beat.onTap} onMouseDown={beat.onTap}>
        {SPLITS.map((g) => (
          <button
            key={g}
            className="choice"
            onClick={() => { beat.onInspect(`give-${g}`); finish(g); }}
            disabled={done}
          >
            Give {g}
          </button>
        ))}
      </div>
    </div>
  );
}
