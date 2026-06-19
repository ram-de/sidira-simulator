import { useState } from 'react';
import { logEvent } from '../lib/api';
import { useBeat } from '../lib/useBeat';

// ROOM 4 — The Trust Game (#440).
// Mechanic: classic trust game. You hold 10 coins. Whatever you send a stranger
// is TRIPLED on arrival; they then decide how much to send back. You choose how
// many of your 10 coins to send.
// Trait revealed (→ Table A pre-treatment features):
//   - trust            → fraction of coins sent (the new `trust` column).
//   - reciprocity      → inferred from how the player reads the pre-generated
//     partner response (we record the player's own returned-share expectation
//     via the follow-up tap). New `reciprocity` column.
//   - social skepticism → sending little despite the 3x multiplier maps to the
//     existing `reactance` proxy (skepticism of a "too-good" multiplier).
// The partner response is PRE-GENERATED (deterministic, seeded by amount sent) —
// it is framing only, never a real second player and never an outcome.
// PRE-treatment, identical across arms. NO A/B, no outcome, no arm.

const SEND_OPTIONS = [0, 2, 5, 8, 10];

// Pre-generated partner return: a fixed, generous-but-imperfect responder.
// Returns ~40% of the tripled pot. Deterministic so the room is reproducible and
// carries no real-outcome signal.
function partnerReturns(sent: number): number {
  return Math.round(sent * 3 * 0.4);
}

export function TrustGame({ playerId, onDone }: { playerId: string; onDone: () => void }) {
  const beat = useBeat();
  const [sent, setSent] = useState<number | null>(null);
  const [returned, setReturned] = useState<number | null>(null);
  const [done, setDone] = useState(false);

  function choose(amount: number) {
    if (sent != null) return;
    beat.onInspect(`send-${amount}`);
    setSent(amount);
    setReturned(partnerReturns(amount));
  }

  function finish(keptFair: boolean) {
    if (done || sent == null) return;
    setDone(true);
    // trust: fraction of the 10 coins entrusted to the stranger.
    const trust = sent / 10;
    // reciprocity: did the player feel the partner's return was fair (and would
    // reciprocate)? A "felt fair" tap maps to higher reciprocity disposition.
    const reciprocity = keptFair ? 0.8 : 0.3;
    // social skepticism: sending little despite a 3x multiplier → high reactance.
    const reactance = sent <= 2 ? 0.8 : sent >= 8 ? 0.2 : 0.45;
    void logEvent({
      playerId,
      beatId: 'trust_game',
      phase: 'profiling',
      choice: { sent, returned, keptFair },
      ...beat.snapshot(),
      features: {
        trust: round(trust),
        reciprocity: round(reciprocity),
        reactance: round(reactance),
      },
    }).finally(onDone);
  }

  return (
    <div className="screen">
      <h2>The Trust Game</h2>
      {sent == null ? (
        <>
          <p className="lede">
            You have 10 coins. Anything you send a stranger is <strong>tripled</strong> — then they
            decide what to send back. How much do you send?
          </p>
          <div className="choices grid" onTouchStart={beat.onTap} onMouseDown={beat.onTap}>
            {SEND_OPTIONS.map((amt) => (
              <button key={amt} className="choice" onClick={() => choose(amt)}>
                Send {amt}
              </button>
            ))}
          </div>
          <p className="statline">No wrong answer — play how you actually feel.</p>
        </>
      ) : (
        <>
          <p className="lede">
            You sent <strong>{sent}</strong>. It tripled to <strong>{sent * 3}</strong>. The stranger
            sent <strong>{returned}</strong> back.
          </p>
          <div className="card">
            <p>You end with {10 - sent + (returned ?? 0)} coins. Did that feel fair?</p>
          </div>
          <div className="choices" onTouchStart={beat.onTap} onMouseDown={beat.onTap}>
            <button className="btn" onClick={() => finish(true)} disabled={done}>Felt fair</button>
            <button className="btn ghost" onClick={() => finish(false)} disabled={done}>Felt short</button>
          </div>
        </>
      )}
    </div>
  );
}

const round = (x: number) => Math.round(x * 100) / 100;
