import type { BeatEvent, OutcomePayload, SessionResponse } from './types';

const TOKEN_KEY = 'stl.token';
const PROGRESS_KEY = 'stl.progress';

// Sticky token: the server mints one if the URL has none; we persist it so
// repeat visits resolve to the SAME server-side assignment (same arm).
export function storedToken(): string | null {
  const fromUrl = new URLSearchParams(window.location.search).get('t');
  if (fromUrl) {
    localStorage.setItem(TOKEN_KEY, fromUrl);
    return fromUrl;
  }
  return localStorage.getItem(TOKEN_KEY);
}

export async function fetchSession(): Promise<SessionResponse> {
  const t = storedToken();
  const url = t ? `/api/session?t=${encodeURIComponent(t)}` : '/api/session';
  const res = await fetch(url);
  if (!res.ok) throw new Error(`session ${res.status}`);
  const data: SessionResponse = await res.json();
  localStorage.setItem(TOKEN_KEY, data.token); // persist minted/echoed token
  return data;
}

export async function logEvent(ev: BeatEvent): Promise<void> {
  ev.referrer = ev.referrer ?? document.referrer ?? undefined;
  await fetch('/api/event', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(ev),
  });
}

export async function logOutcome(payload: OutcomePayload): Promise<void> {
  await fetch('/api/outcome', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function postSellerCard(playerId: string, card: {
  ageBand?: string; locale?: string; device?: string; tenureDays?: number;
}): Promise<void> {
  await fetch('/api/seller-card', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ playerId, ...card }),
  });
}

// ----------------------------------------------------------------------------
// Autosave / resume: which beats are done, persisted per player so a refresh
// resumes exactly where the player left off (spec: "autosave/resume per beat").
// ----------------------------------------------------------------------------
export function loadProgress(playerId: string): Set<string> {
  try {
    const raw = localStorage.getItem(`${PROGRESS_KEY}.${playerId}`);
    return new Set(raw ? (JSON.parse(raw) as string[]) : []);
  } catch {
    return new Set();
  }
}

export function saveProgress(playerId: string, done: Set<string>): void {
  localStorage.setItem(`${PROGRESS_KEY}.${playerId}`, JSON.stringify([...done]));
}
