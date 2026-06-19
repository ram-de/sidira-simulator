// Express API — app factory (exported without listening so it's testable).
// server/index.js wires the client (Vite middleware in dev, static dist/ in
// prod) and listens. Three endpoints, mirroring the spec:
//   GET  /api/session?t=<token>   resolve/assign, return rendered screen config
//   POST /api/event               per-beat telemetry → events (+ Table A)
//   POST /api/outcome             binary outcome → Table B (player_outcomes)

import express from 'express';
import {
  recordEvent,
  recordFeature,
  derivePassiveFeatures,
  recordOutcome,
  markForwarded,
  markCompleted,
} from './db.js';
import { resolveParticipant, mintToken } from './randomize.js';
import { buildScreenConfig } from './screenConfig.js';

export function createApp() {
  const app = express();
  app.use(express.json());

  // --------------------------------------------------------------------------
  // GET /api/session — the single entry point. ONE link; the server resolves
  // the per-recipient token (minting one if absent), assigns the arm server-
  // side on first load, and returns ONLY the rendered config (never the arm).
  // Repeat visits with the same token return the same sticky assignment.
  // --------------------------------------------------------------------------
  app.get('/api/session', (req, res) => {
    let token = typeof req.query.t === 'string' && req.query.t ? req.query.t : null;
    const referrer = req.get('referer') || null;

    // No token → the "one link" case. Mint a fresh token server-side and tell
    // the client to remember it (sticky via localStorage on the client).
    let minted = false;
    if (!token) {
      token = mintToken();
      minted = true;
    }

    const { participant, created } = resolveParticipant(token, referrer);

    // Forwarding detection: an existing token arriving from a NEW referrer is
    // likely forwarded. Keep the sticky assignment; flag it for the analysis
    // (primary analysis = original-token users only).
    if (!created && referrer && participant.referrer && referrer !== participant.referrer) {
      markForwarded(participant.player_id, referrer);
    }

    const config = buildScreenConfig(participant);
    res.json({ token, minted, config });
  });

  // --------------------------------------------------------------------------
  // POST /api/event — per-beat telemetry. Logs choice, latency-to-first-tap,
  // re-tap/scrub count, dwell, fine-print-opened, arm (microab beats only),
  // referrer. Profiling beats also carry derived pre-treatment feature values
  // which we write to Table A; passive features are recomputed from the log.
  //   body: { playerId, beatId, phase, choice, latencyMs, retapCount, dwellMs,
  //           finePrintOpened, optionsInspected, arm, referrer, features }
  // --------------------------------------------------------------------------
  app.post('/api/event', (req, res) => {
    const b = req.body || {};
    if (!b.playerId || !b.beatId || !b.phase) {
      return res.status(400).json({ error: 'playerId, beatId, phase required' });
    }
    recordEvent(b.playerId, b);

    // Profiling beats may carry derived decision-style features (e.g. the Risk
    // Box emits a risk-appetite score). Those go to Table A. recordFeature()
    // enforces the firewall: any arm/outcome-shaped key throws.
    if (b.phase === 'profiling') {
      if (b.features && typeof b.features === 'object') {
        recordFeature(b.playerId, b.features);
      }
      derivePassiveFeatures(b.playerId);
    }
    res.json({ ok: true });
  });

  // --------------------------------------------------------------------------
  // POST /api/outcome — the SEALED answer key. ONLY path arm+outcome reach the
  // DB; goes straight to Table B (player_outcomes), never Table A.
  //   body: { playerId, arm, taskId, outcome, attentionPassed, startedAt, decidedAt, done }
  // `done: true` marks the participant complete (gates the persona reveal).
  // --------------------------------------------------------------------------
  app.post('/api/outcome', (req, res) => {
    const b = req.body || {};
    if (!b.playerId || !b.taskId || b.outcome == null || !b.arm) {
      return res.status(400).json({ error: 'playerId, arm, taskId, outcome required' });
    }
    recordOutcome({
      playerId: b.playerId,
      arm: b.arm,
      taskId: b.taskId,
      outcome: b.outcome,
      attentionPassed: b.attentionPassed,
      startedAt: b.startedAt,
      decidedAt: b.decidedAt,
    });
    if (b.done) markCompleted(b.playerId);
    res.json({ ok: true });
  });

  // --------------------------------------------------------------------------
  // POST /api/seller-card — the 3-tap demographics, captured POST-game but
  // PRE-reveal. Pre-treatment demographics → Table A.
  //   body: { playerId, ageBand, locale, device, tenureDays }
  // --------------------------------------------------------------------------
  app.post('/api/seller-card', (req, res) => {
    const b = req.body || {};
    if (!b.playerId) return res.status(400).json({ error: 'playerId required' });
    recordFeature(b.playerId, {
      age_band: b.ageBand ?? null,
      locale: b.locale ?? null,
      device: b.device ?? null,
      tenure_days: b.tenureDays ?? null,
    });
    res.json({ ok: true });
  });

  return app;
}
