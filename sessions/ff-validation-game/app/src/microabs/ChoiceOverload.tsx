import { useState } from 'react';
import { logOutcome } from '../lib/api';
import { useBeat } from '../lib/useBeat';
import type { MicroAbConfig } from '../lib/types';

// MICRO-A/B 1 — Choice Overload (DONE, fully working).
// Counter-intuitive: MORE choice LOWERS the rate of actually choosing.
// Obvious prior (the "always-pick-obvious" placebo): "more options = more
// engagement → higher choose-rate." We bet the opposite.
//
// Mechanic: the player is offered a bonus reward to claim. Each player sees ONE
// option-count (3 or 24), randomized server-side (config.present.optionCount).
// Binary OUTCOME → Table B: 1 = claimed a reward, 0 = skipped ("none for now").
// The arm recorded is the presentation label ('opts:3' / 'opts:24'), never the
// server's internal headline-arm name.

export function ChoiceOverload({
  playerId, config, onDone, isLast,
}: { playerId: string; config: MicroAbConfig; onDone: () => void; isLast: boolean }) {
  const beat = useBeat();
  const optionCount = (config.present.optionCount as number) ?? 3;
  const startedAt = useState(() => new Date().toISOString())[0];
  const [done, setDone] = useState(false);

  const rewards = Array.from({ length: optionCount }, (_, i) => `Reward #${i + 1}`);

  function finish(outcome: 0 | 1) {
    if (done) return;
    setDone(true);
    void logOutcome({
      playerId,
      arm: `opts:${optionCount}`,
      taskId: 'choice_overload',
      outcome,
      startedAt,
      decidedAt: new Date().toISOString(),
      done: isLast, // mark complete if this is the last beat in the battery
    }).finally(onDone);
  }

  return (
    <div className="screen">
      <h2>Claim a bonus</h2>
      <p className="lede">You earned a bonus reward. Pick one to lock it in — or skip.</p>
      <div
        className="choices grid"
        style={{ maxHeight: 320, overflowY: 'auto' }}
        onTouchStart={beat.onTap}
        onMouseDown={beat.onTap}
      >
        {rewards.map((r, i) => (
          <button
            key={r}
            className="choice"
            onClick={() => { beat.onInspect(`r${i}`); finish(1); }}
            disabled={done}
          >
            {r}
          </button>
        ))}
      </div>
      <button className="btn ghost" onClick={() => finish(0)} disabled={done}>
        None for now
      </button>
    </div>
  );
}
