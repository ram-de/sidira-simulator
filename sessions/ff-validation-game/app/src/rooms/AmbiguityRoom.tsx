import { useState } from 'react';
import { logEvent } from '../lib/api';
import { useBeat } from '../lib/useBeat';

// ROOM 5 — The Mystery Box (#440), the Ellsberg ambiguity room.
// Mechanic: two boxes, EQUAL expected value. The KNOWN box pays +15 on a stated
// 50% draw. The MYSTERY box pays +15 on an unstated ("could be anywhere") draw
// that is in fact also 50% EV. Preferring the known box at equal EV = ambiguity
// aversion. Preferring the mystery box = ambiguity seeking / low skepticism.
// Trait revealed (→ Table A pre-treatment features):
//   - ambiguity aversion → the new `ambiguity_aversion` column.
//   - skepticism of opaque systems → an unstated-odds choice that still picks
//     the mystery reads as low reactance; picking known reads as higher.
// PRE-treatment, identical across arms. NO A/B, no outcome, no arm.

const OPTIONS = [
  { id: 'known', label: 'Known box: stated 50% chance of +15 coins' },
  { id: 'mystery', label: 'Mystery box: unknown odds, same +15 payout' },
];

export function AmbiguityRoom({ playerId, onDone }: { playerId: string; onDone: () => void }) {
  const beat = useBeat();
  const [picked, setPicked] = useState<string | null>(null);

  function submit(choiceId: string) {
    if (picked) return;
    setPicked(choiceId);
    // At equal EV, preferring the KNOWN box → ambiguity-averse; preferring the
    // MYSTERY box → ambiguity-tolerant. Skepticism of the opaque option folds
    // into the existing `reactance` proxy.
    const ambiguityAversion = choiceId === 'known' ? 0.85 : 0.2;
    const reactance = choiceId === 'known' ? 0.6 : 0.25;
    void logEvent({
      playerId,
      beatId: 'ambiguity',
      phase: 'profiling',
      choice: { choiceId },
      ...beat.snapshot(),
      features: {
        ambiguity_aversion: round(ambiguityAversion),
        reactance: round(reactance),
      },
    }).finally(onDone);
  }

  return (
    <div className="screen">
      <h2>The Mystery Box</h2>
      <p className="lede">
        Two boxes pay the same +15 — but one tells you the odds and one keeps them hidden. Which do
        you open?
      </p>
      <div className="choices" onTouchStart={beat.onTap} onMouseDown={beat.onTap}>
        {OPTIONS.map((o) => (
          <button
            key={o.id}
            className={`choice ${picked === o.id ? 'selected' : ''}`}
            onClick={() => { beat.onInspect(o.id); submit(o.id); }}
            disabled={!!picked}
          >
            {o.label}
          </button>
        ))}
      </div>
      <p className="statline">No wrong answer — play how you actually feel.</p>
    </div>
  );
}

const round = (x: number) => Math.round(x * 100) / 100;
