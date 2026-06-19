import { logEvent } from '../lib/api';

// STUB profiling rooms — Deal room, Trust game, Ambiguity.
// TODO: implement each as a real mechanic→trait beat following the RiskBox /
// InfoCost pattern, emitting its decision-style feature to Table A:
//   - deal_room   → present_bias / patience / deal_sensitivity
//                   (mechanic: take now vs wait/counter for more)
//   - trust_game  → trust / reciprocity / social skepticism
//                   (mechanic: how many tripled coins to send a stranger)
//   - ambiguity   → ambiguity aversion / opaque-system skepticism
//                   (mechanic: known 50% odds vs equal-EV "mystery")
// Until then, this placeholder logs an empty profiling beat so the state
// machine can advance end-to-end during scaffold testing.

const TITLES: Record<string, string> = {
  deal_room: 'The Deal Room',
  trust_game: 'The Trust Game',
  ambiguity: 'The Mystery Box',
};

export function StubRoom({ roomId, playerId, onDone }: { roomId: string; playerId: string; onDone: () => void }) {
  function skip() {
    void logEvent({
      playerId,
      beatId: roomId,
      phase: 'profiling',
      choice: { skipped: true, stub: true },
    }).finally(onDone);
  }
  return (
    <div className="screen">
      <h2>{TITLES[roomId] ?? roomId}</h2>
      <p className="lede">Coming soon in this room.</p>
      <p className="stub-note">STUB: profiling room not yet implemented (TODO — see StubRoom.tsx).</p>
      <div className="spacer" />
      <button className="btn" onClick={skip}>Continue</button>
    </div>
  );
}
