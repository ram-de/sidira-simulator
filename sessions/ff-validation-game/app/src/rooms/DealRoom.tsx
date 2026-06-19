import { useState } from 'react';
import { logEvent } from '../lib/api';
import { useBeat } from '../lib/useBeat';

// ROOM 3 — The Deal Room (#440).
// Mechanic: a buyer offers to take your loot NOW for a sure 12 coins, or you
// can wait/counter for more — a 60% shot at 22 coins (else you get 6).
// Trait revealed (→ Table A pre-treatment features):
//   - present_bias / patience → take-now (present-biased, impatient) vs
//     wait/counter (patient). `present_bias` already exists; `patience` is the
//     new column.
//   - deal_sensitivity        → counter-offering signals haggling/EV chasing.
//   - deliberation latency    → captured passively (warmup_decision_ms).
// PRE-treatment, identical across arms. NO A/B, no outcome, no arm.

const OPTIONS = [
  { id: 'take_now', label: 'Take the offer now: +12 coins, locked in' },
  { id: 'wait', label: 'Wait it out: 60% chance of +22 (else +6)' },
  { id: 'counter', label: 'Counter for more: hold out for +22 or walk' },
];

export function DealRoom({ playerId, onDone }: { playerId: string; onDone: () => void }) {
  const beat = useBeat();
  const [picked, setPicked] = useState<string | null>(null);

  function submit(choiceId: string) {
    if (picked) return;
    setPicked(choiceId);
    // Map the choice to decision-style features (PRE-treatment).
    //   take_now → present-biased + impatient; wait/counter → patient.
    //   counter  → highest deal_sensitivity (actively haggling for a better EV).
    const presentBias = choiceId === 'take_now' ? 0.85 : choiceId === 'wait' ? 0.35 : 0.2;
    const patience = choiceId === 'take_now' ? 0.15 : choiceId === 'wait' ? 0.65 : 0.85;
    const dealSensitivity = choiceId === 'counter' ? 0.9 : choiceId === 'wait' ? 0.5 : 0.2;
    void logEvent({
      playerId,
      beatId: 'deal_room',
      phase: 'profiling',
      choice: { choiceId },
      ...beat.snapshot(),
      features: {
        present_bias: round(presentBias),
        patience: round(patience),
        deal_sensitivity: round(dealSensitivity),
      },
    }).finally(onDone);
  }

  return (
    <div className="screen">
      <h2>The Deal Room</h2>
      <p className="lede">A buyer wants your loot. Take the sure thing now, or hold out for more?</p>
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
