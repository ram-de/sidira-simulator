import { useState } from 'react';
import { logEvent } from '../lib/api';
import { useBeat } from '../lib/useBeat';

// ROOM 2 — Info-Cost (DONE, the second profiling pattern).
// Mechanic: pay coins to reveal hints vs choose blind.
// Trait revealed (→ Table A pre-treatment features):
//   - attention / effort, info valuation → `effort_tolerance`
//   - overconfidence (choosing blind)    → `reactance` proxy (skepticism of help)
//   - options inspected                  → passive (warmup_options_inspected)
// NO A/B here.

const DOORS = ['A', 'B', 'C'];
const HINT_COST = 3;

export function InfoCost({ playerId, onDone }: { playerId: string; onDone: () => void }) {
  const beat = useBeat();
  const [hintsBought, setHintsBought] = useState(0);
  const [picked, setPicked] = useState<string | null>(null);

  function buyHint() {
    beat.onTap();
    setHintsBought((n) => Math.min(n + 1, DOORS.length));
    beat.onInspect(`hint-${hintsBought}`);
  }

  function choose(door: string) {
    if (picked) return;
    setPicked(door);
    // info valuation: more hints bought → higher effort_tolerance. Choosing
    // blind (0 hints) → higher overconfidence/skepticism (reactance proxy).
    const effortTolerance = hintsBought / DOORS.length;
    void logEvent({
      playerId,
      beatId: 'info_cost',
      phase: 'profiling',
      choice: { door, hintsBought, paid: hintsBought * HINT_COST },
      ...beat.snapshot(),
      features: {
        effort_tolerance: round(effortTolerance),
        reactance: round(hintsBought === 0 ? 0.8 : 0.3),
      },
    }).finally(onDone);
  }

  return (
    <div className="screen">
      <h2>Three Doors</h2>
      <p className="lede">
        One door pays big. You can buy hints ({HINT_COST} coins each) — or back yourself and pick blind.
      </p>
      <div className="card">
        <p className="statline">Hints bought: {hintsBought} · spent {hintsBought * HINT_COST} coins</p>
        <button className="btn ghost" onClick={buyHint} disabled={hintsBought >= DOORS.length || !!picked}>
          Buy a hint (−{HINT_COST})
        </button>
      </div>
      <div className="choices grid" onTouchStart={beat.onTap} onMouseDown={beat.onTap}>
        {DOORS.map((d) => (
          <button
            key={d}
            className={`choice ${picked === d ? 'selected' : ''}`}
            onClick={() => choose(d)}
            disabled={!!picked}
          >
            Door {d}
          </button>
        ))}
      </div>
    </div>
  );
}

const round = (x: number) => Math.round(x * 100) / 100;
