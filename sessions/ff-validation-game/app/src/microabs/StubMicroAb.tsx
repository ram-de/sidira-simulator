import { useState } from 'react';
import { logOutcome } from '../lib/api';
import type { MicroAbConfig } from '../lib/types';

// STUB micro-A/Bs — default_stickiness, prosocial_backfire, effort_justification.
// TODO: implement each as a real COUNTER-INTUITIVE beat that logs a binary
// outcome to Table B, with the obvious-prior labeled by a non-author BEFORE
// sealing. Reaching K>=5 fully-implemented items is required for the sealed-win
// bar (5/5 → p=0.03; 4/4 → p=0.06). Spec mechanics to build:
//   - default_stickiness    : pre-checked "safe" default + "most people lock
//                             in" vs neutral — default stickiness beats framing.
//   - prosocial_backfire    : polished "your impact compounds" blurb REDUCES
//                             giving vs a sparse screen (reads as persuasion).
//   - effort_justification  : a tiny earned effort RAISES downstream commitment
//                             vs one-tap.
// Until built, this logs a neutral outcome (0) so the battery completes during
// scaffold testing. A stub outcome must NEVER be scored in a sealed run.

export function StubMicroAb({
  playerId, config, onDone, isLast,
}: { playerId: string; config: MicroAbConfig; onDone: () => void; isLast: boolean }) {
  const [done, setDone] = useState(false);
  function finish() {
    if (done) return;
    setDone(true);
    void logOutcome({
      playerId,
      arm: 'stub',
      taskId: config.taskId,
      outcome: 0,
      done: isLast,
    }).finally(onDone);
  }
  return (
    <div className="screen">
      <h2>{config.taskId.replace(/_/g, ' ')}</h2>
      <p className="lede">A quick decision…</p>
      <p className="stub-note">STUB: micro-A/B not yet implemented (TODO — see StubMicroAb.tsx). Do not score.</p>
      <div className="spacer" />
      <button className="btn" onClick={finish}>Continue</button>
    </div>
  );
}
