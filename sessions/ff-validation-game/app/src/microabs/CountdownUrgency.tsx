import { useEffect, useState } from 'react';
import { logOutcome } from '../lib/api';
import { useBeat } from '../lib/useBeat';
import type { MicroAbConfig } from '../lib/types';

// MICRO-A/B 2 — Countdown Urgency (DONE, fully working).
// Counter-intuitive (reactance): aggressive urgency DEPRESSES completion in a
// F&F "I know I'm being sold to" context.
// Obvious prior (placebo): "scarcity + countdown lifts conversion." We bet the
// opposite for this audience.
//
// This is the BETWEEN-subject HEADLINE item. The framing (countdownSeconds /
// showScarcity) arrives in config.present, derived server-side from the headline
// arm — the client NEVER receives the arm name. We record the arm as the
// presentation label ('framing:scarce' / 'framing:calm').
// Binary OUTCOME → Table B: 1 = locked in the deal, 0 = passed.

export function CountdownUrgency({
  playerId, config, onDone, isLast,
}: { playerId: string; config: MicroAbConfig; onDone: () => void; isLast: boolean }) {
  const beat = useBeat();
  const scarce = !!config.present.showScarcity;
  const countdownStart = (config.present.countdownSeconds as number) ?? 0;
  const [secs, setSecs] = useState(countdownStart);
  const startedAt = useState(() => new Date().toISOString())[0];
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!scarce || done || secs <= 0) return;
    const id = setTimeout(() => setSecs((s) => s - 1), 1000);
    return () => clearTimeout(id);
  }, [secs, scarce, done]);

  function finish(outcome: 0 | 1) {
    if (done) return;
    setDone(true);
    void logOutcome({
      playerId,
      arm: scarce ? 'framing:scarce' : 'framing:calm',
      taskId: 'countdown_urgency',
      outcome,
      startedAt,
      decidedAt: new Date().toISOString(),
      done: isLast, // last beat in the battery → marks the participant complete
    }).finally(onDone);
  }

  return (
    <div className="screen">
      <h2>Lock in the loot pool</h2>
      {scarce ? (
        <p className="lede">
          <span className="scarce">Only 3 spots left!</span>{' '}
          <span className="timer">Offer expires in {Math.max(secs, 0)}s</span>
        </p>
      ) : (
        <p className="lede">You can add your coins to the shared loot pool. No rush — take your time.</p>
      )}
      <div className="card">
        <p>Add your coins to the pool for a shot at the 20× payout.</p>
      </div>
      <div className="choices" onTouchStart={beat.onTap} onMouseDown={beat.onTap}>
        <button className="btn" onClick={() => finish(1)} disabled={done}>Lock it in</button>
        <button className="btn ghost" onClick={() => finish(0)} disabled={done}>Pass for now</button>
      </div>
    </div>
  );
}
