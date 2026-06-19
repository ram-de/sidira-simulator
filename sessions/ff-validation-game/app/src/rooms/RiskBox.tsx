import { useEffect, useState } from 'react';
import { logEvent } from '../lib/api';
import { useBeat } from '../lib/useBeat';

// ROOM 1 — Risk Box (DONE, the pattern for profiling rooms).
// Mechanic: safe +10 / 70%·+18 / 35%·+45 under a 12s timer.
// Trait revealed (→ Table A pre-treatment features):
//   - risk appetite + EV-sensitivity  → decision-style score `deal_sensitivity`
//     (EV-chasing) and an inverse risk signal folded into `present_bias` proxy
//   - deliberation latency            → captured passively (warmup_decision_ms)
// NO A/B here. Identical for everyone.

const OPTIONS = [
  { id: 'safe', label: 'Take +10 coins, guaranteed', ev: 10 },
  { id: 'mid', label: '70% chance of +18 coins', ev: 0.7 * 18 },
  { id: 'bold', label: '35% chance of +45 coins', ev: 0.35 * 45 },
];

export function RiskBox({ playerId, onDone }: { playerId: string; onDone: () => void }) {
  const beat = useBeat();
  const [secs, setSecs] = useState(12);
  const [picked, setPicked] = useState<string | null>(null);

  useEffect(() => {
    if (picked) return;
    if (secs <= 0) {
      // Timed out without deciding → counts as a skip (passive skip-rate).
      submit(null, true);
      return;
    }
    const id = setTimeout(() => setSecs((s) => s - 1), 1000);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [secs, picked]);

  function submit(choiceId: string | null, skipped = false) {
    if (picked) return;
    setPicked(choiceId ?? 'timeout');
    const chosen = OPTIONS.find((o) => o.id === choiceId);
    // Map the choice to decision-style features. Bolder pick (higher EV
    // variance) → higher EV-sensitivity & risk appetite. These are PRE-treatment.
    const evChase = chosen ? chosen.ev / 12.6 : 0; // normalized vs the boldest EV
    const riskAppetite = choiceId === 'bold' ? 1 : choiceId === 'mid' ? 0.6 : choiceId === 'safe' ? 0.15 : 0.3;
    void logEvent({
      playerId,
      beatId: 'risk_box',
      phase: 'profiling',
      choice: { choiceId, skipped },
      ...beat.snapshot(),
      features: {
        // deal_sensitivity here proxies EV-chasing; present_bias proxies the
        // "grab the sure thing now" reflex (low = patient/risk-tolerant).
        deal_sensitivity: round(evChase),
        present_bias: round(1 - riskAppetite),
      },
    }).finally(onDone);
  }

  return (
    <div className="screen">
      <h2>The Risk Box</h2>
      <p className="lede">
        Pick your payout before the box locks. <span className="timer">{secs}s</span>
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
