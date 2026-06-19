// Express API — app factory (exported without listening so it's testable).
// server/index.js wires the client (Vite middleware in dev, static dist/ in
// prod) and listens. Three endpoints, mirroring the spec:
//   GET  /api/session?t=<token>   resolve/assign, return rendered screen config
//   POST /api/event               per-beat telemetry → events (+ Table A)
//   POST /api/outcome             binary outcome → Table B (player_outcomes)

import express from 'express';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
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
  const isProd = process.env.NODE_ENV === 'production';

  // Behind CloudFront/EC2 there is a trusted proxy hop; trust exactly one so
  // express-rate-limit keys off the real client IP (X-Forwarded-For) rather
  // than the proxy's, without trusting an arbitrarily long forwarded chain.
  app.set('trust proxy', 1);

  // --------------------------------------------------------------------------
  // Security headers. The SPA is same-origin (API + static from one port), so
  // we can keep a tight CSP. connect-src 'self' covers the /api/* calls; we
  // allow inline styles because the build inlines critical CSS.
  // --------------------------------------------------------------------------
  app.use(
    helmet({
      contentSecurityPolicy: {
        directives: {
          defaultSrc: ["'self'"],
          scriptSrc: ["'self'"],
          styleSrc: ["'self'", "'unsafe-inline'"],
          imgSrc: ["'self'", 'data:'],
          connectSrc: ["'self'"],
          objectSrc: ["'none'"],
          frameAncestors: ["'none'"],
          baseUri: ["'self'"],
        },
      },
      // CloudFront terminates TLS and serves over HTTPS; let it own HSTS so we
      // don't pin headers when testing the origin over plain HTTP.
      hsts: false,
      crossOriginEmbedderPolicy: false,
    }),
  );

  // --------------------------------------------------------------------------
  // CORS lockdown. In prod everything is same-origin (SPA + API served by this
  // app behind one CloudFront distribution) so there is NO legitimate cross-
  // origin caller — we simply never emit Access-Control-Allow-Origin, which is
  // the strictest, deny-by-default posture. (No cors() package needed.) In dev
  // the Vite middleware serves the SPA from the same origin too.
  // --------------------------------------------------------------------------

  // Payload size limit: every endpoint takes a small JSON body; cap it hard so
  // a malicious client can't OOM the tiny t4g.small with a giant body.
  app.use(express.json({ limit: '16kb' }));

  // --------------------------------------------------------------------------
  // Rate limiting on /api/*. The participant token is the only identity (no
  // auth — this is friends & family), so we throttle per-IP to blunt abuse of
  // the write endpoints (event / outcome / session) without inconveniencing a
  // real player, who fires well under these ceilings over a single sitting.
  // --------------------------------------------------------------------------
  const apiLimiter = rateLimit({
    windowMs: 60 * 1000, // 1 minute
    max: isProd ? 120 : 100000, // ~2 req/s sustained per IP in prod; effectively off in dev
    standardHeaders: true,
    legacyHeaders: false,
    message: { error: 'rate limit exceeded, slow down' },
  });
  app.use('/api/', apiLimiter);

  // --------------------------------------------------------------------------
  // GET /healthz — liveness probe for CloudFront origin health + EC2/systemd.
  // Cheap and dependency-free: if the event loop can answer, we're up. Excluded
  // from the /api rate limiter (mounted on /api/ only) so probes never 429.
  // --------------------------------------------------------------------------
  app.get('/healthz', (_req, res) => {
    res.status(200).json({ ok: true });
  });

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

  // Unknown API route → JSON 404 (the SPA fallback in index.js explicitly skips
  // /api/, so this is the terminal handler for unmatched API calls).
  app.use('/api/', (_req, res) => res.status(404).json({ error: 'not found' }));

  return app;
}
