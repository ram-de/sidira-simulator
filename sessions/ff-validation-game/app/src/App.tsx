import { useEffect, useMemo, useState } from 'react';
import { fetchSession, loadProgress, saveProgress } from './lib/api';
import type { ScreenConfig } from './lib/types';
import { Intro } from './screens/Intro';
import { SellerCard } from './screens/SellerCard';
import { PersonaReveal } from './screens/PersonaReveal';
import { RiskBox } from './rooms/RiskBox';
import { InfoCost } from './rooms/InfoCost';
import { StubRoom } from './rooms/StubRoom';
import { ChoiceOverload } from './microabs/ChoiceOverload';
import { CountdownUrgency } from './microabs/CountdownUrgency';
import { StubMicroAb } from './microabs/StubMicroAb';

// THE SCREEN STATE MACHINE
// intro → profiling rooms → micro-A/B battery → seller card → persona reveal.
// The reveal is gated on completion of ALL outcomes (never before — see
// PersonaReveal.tsx). 7-dot progress; autosave/resume per beat.
type Stage = 'loading' | 'intro' | 'profiling' | 'microabs' | 'sellercard' | 'reveal';

const ROOM_DONE = new Set(['risk_box', 'info_cost']);

export function App() {
  const [config, setConfig] = useState<ScreenConfig | null>(null);
  const [stage, setStage] = useState<Stage>('loading');
  const [roomIdx, setRoomIdx] = useState(0);
  const [abIdx, setAbIdx] = useState(0);

  useEffect(() => {
    fetchSession()
      .then(({ config }) => {
        setConfig(config);
        // Resume: if the server already has this participant complete, jump to
        // the reveal. Otherwise resume from saved per-beat progress.
        if (config.completed) {
          setStage('reveal');
          return;
        }
        const done = loadProgress(config.playerId);
        const roomsDone = config.profilingRooms.every((r) => done.has(`room:${r.id}`));
        const absDone = config.microabs.every((m) => done.has(`ab:${m.taskId}`));
        if (absDone) setStage('sellercard');
        else if (roomsDone) { setStage('microabs'); setAbIdx(firstUndone(config.microabs.map((m) => `ab:${m.taskId}`), done)); }
        else if (done.size > 0) { setStage('profiling'); setRoomIdx(firstUndone(config.profilingRooms.map((r) => `room:${r.id}`), done)); }
        else setStage('intro');
      })
      .catch(() => setStage('intro'));
  }, []);

  function mark(beatKey: string) {
    if (!config) return;
    const done = loadProgress(config.playerId);
    done.add(beatKey);
    saveProgress(config.playerId, done);
  }

  // 7-dot progress: intro, 5 rooms collapsed to 3 dots of progress + battery +
  // card + reveal. We render exactly 7 dots mapped to coarse milestones.
  const dotState = useMemo(() => computeDots(stage, roomIdx, abIdx, config), [stage, roomIdx, abIdx, config]);

  if (!config || stage === 'loading') {
    return <div className="app"><div className="screen"><p className="lede">Loading…</p></div></div>;
  }

  function advanceRoom() {
    const next = roomIdx + 1;
    if (next >= config!.profilingRooms.length) setStage('microabs');
    else setRoomIdx(next);
  }
  function advanceAb() {
    const next = abIdx + 1;
    if (next >= config!.microabs.length) setStage('sellercard');
    else setAbIdx(next);
  }

  return (
    <div className="app">
      <div className="dots">
        {dotState.map((s, i) => <div key={i} className={`dot ${s}`} />)}
      </div>

      {stage === 'intro' && <Intro onStart={() => setStage('profiling')} />}

      {stage === 'profiling' && (() => {
        const room = config.profilingRooms[roomIdx];
        const onDone = () => { mark(`room:${room.id}`); advanceRoom(); };
        if (room.id === 'risk_box') return <RiskBox playerId={config.playerId} onDone={onDone} />;
        if (room.id === 'info_cost') return <InfoCost playerId={config.playerId} onDone={onDone} />;
        return <StubRoom roomId={room.id} playerId={config.playerId} onDone={onDone} />;
      })()}

      {stage === 'microabs' && (() => {
        const ab = config.microabs[abIdx];
        const isLast = abIdx === config.microabs.length - 1;
        const onDone = () => { mark(`ab:${ab.taskId}`); advanceAb(); };
        if (ab.taskId === 'choice_overload') return <ChoiceOverload playerId={config.playerId} config={ab} onDone={onDone} />;
        if (ab.taskId === 'countdown_urgency') return <CountdownUrgency playerId={config.playerId} config={ab} onDone={onDone} isLast={isLast} />;
        return <StubMicroAb playerId={config.playerId} config={ab} onDone={onDone} isLast={isLast} />;
      })()}

      {stage === 'sellercard' && (
        <SellerCard playerId={config.playerId} onDone={() => setStage('reveal')} />
      )}

      {/* Reveal renders ONLY after all outcomes — gated by reaching this stage. */}
      {stage === 'reveal' && <PersonaReveal playerId={config.playerId} />}
    </div>
  );
}

function firstUndone(keys: string[], done: Set<string>): number {
  const i = keys.findIndex((k) => !done.has(k));
  return i < 0 ? 0 : i;
}

// Reference to the spec's room-done set (kept for clarity; both done rooms are
// implemented above).
void ROOM_DONE;

function computeDots(stage: Stage, roomIdx: number, abIdx: number, config: ScreenConfig | null): string[] {
  // 7 dots: [intro][profiling 1][profiling 2][battery 1][battery 2][card][reveal]
  const order: Stage[] = ['intro', 'profiling', 'microabs', 'sellercard', 'reveal'];
  const stageIdx = order.indexOf(stage);
  const dots = new Array(7).fill('');
  // Coarse mapping: fill done dots up to the current milestone.
  const milestone = stage === 'intro' ? 0
    : stage === 'profiling' ? 1 + Math.min(roomIdx, 1)
    : stage === 'microabs' ? 3 + Math.min(abIdx, 1)
    : stage === 'sellercard' ? 5
    : 6;
  for (let i = 0; i < 7; i++) {
    if (i < milestone) dots[i] = 'done';
    else if (i === milestone) dots[i] = 'active';
  }
  void stageIdx; void config;
  return dots;
}
