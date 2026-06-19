// Shared client types. Mirrors the server's rendered config — note there is NO
// arm field anywhere the client can read: the blind is preserved by construction.

export type Phase = 'profiling' | 'microab' | 'demographics';

export interface RoomConfig {
  id: string;
  status: 'done' | 'stub';
}

export interface MicroAbConfig {
  taskId: string;
  status: 'done' | 'stub';
  // `present` is what to render — never the arm name. The countdown_urgency
  // framing (countdownSeconds/showScarcity) is derived server-side from the
  // headline arm; the client cannot invert it back to the arm label.
  present: Record<string, unknown> & { kind: string };
}

export interface ScreenConfig {
  playerId: string;
  completed: boolean;
  profilingRooms: RoomConfig[];
  microabs: MicroAbConfig[];
  steps: string[];
}

export interface SessionResponse {
  token: string;
  minted: boolean;
  config: ScreenConfig;
}

// A per-beat telemetry payload. `arm` is set only by micro-A/B beats, and it is
// the variant the player SAW (e.g. 'scarce'/'calm', '3'/'24') — a presentation
// label, not the server's internal headline-arm name.
export interface BeatEvent {
  playerId: string;
  beatId: string;
  phase: Phase;
  choice?: unknown;
  latencyMs?: number;
  retapCount?: number;
  dwellMs?: number;
  finePrintOpened?: boolean;
  optionsInspected?: number;
  arm?: string;
  referrer?: string;
  features?: Record<string, number | string | null>;
}

export interface OutcomePayload {
  playerId: string;
  arm: string;
  taskId: string;
  outcome: 0 | 1;
  attentionPassed?: boolean;
  startedAt?: string;
  decidedAt?: string;
  done?: boolean;
}
