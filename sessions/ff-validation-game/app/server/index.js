// Server entry — one port for everything.
// Dev:  Vite runs in middleware mode and serves the SPA through this Express app.
// Prod: Express serves the built dist/ alongside the API.

import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import express from 'express';
import { createApp } from './app.js';
import { checkpointAndClose, DB_PATH } from './db.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '..');

const PORT = Number(process.env.PORT) || 5180;
const isProd = process.env.NODE_ENV === 'production';

const app = createApp();

if (isProd) {
  const dist = path.join(root, 'dist');
  const indexHtml = path.join(dist, 'index.html');
  if (!fs.existsSync(indexHtml)) {
    console.error('dist/index.html not found — run `npm run build` first.');
    process.exit(1);
  }
  // Hashed Vite assets are immutable; index.html must never be cached so a new
  // deploy is picked up immediately.
  app.use(
    express.static(dist, {
      index: false,
      setHeaders: (res, filePath) => {
        if (filePath.endsWith('index.html')) {
          res.setHeader('Cache-Control', 'no-cache');
        } else {
          res.setHeader('Cache-Control', 'public, max-age=31536000, immutable');
        }
      },
    }),
  );
  // SPA fallback for client-side routes — but never mask an unknown API route
  // (those should 404 as JSON, not silently return the HTML shell).
  app.use((req, res, next) => {
    if (req.path.startsWith('/api/')) return next();
    res.setHeader('Cache-Control', 'no-cache');
    res.sendFile(indexHtml);
  });
} else {
  const { createServer } = await import('vite');
  const vite = await createServer({
    root,
    appType: 'spa',
    server: { middlewareMode: true },
  });
  app.use(vite.middlewares);
}

const server = app.listen(PORT, () => {
  console.log(`Split The Loot ${isProd ? '(prod)' : '(dev)'} on http://localhost:${PORT}`);
  console.log(`SQLite at ${DB_PATH}`);
});

// ----------------------------------------------------------------------------
// Graceful shutdown. systemd sends SIGTERM on stop/restart; Ctrl-C sends
// SIGINT. We stop accepting connections, then checkpoint + close SQLite so the
// WAL is folded back into the main DB file and no committed write is lost.
// ----------------------------------------------------------------------------
let shuttingDown = false;
function shutdown(signal) {
  if (shuttingDown) return;
  shuttingDown = true;
  console.log(`\n${signal} received — shutting down gracefully…`);
  server.close(() => {
    checkpointAndClose();
    console.log('HTTP server closed, SQLite checkpointed + closed. Bye.');
    process.exit(0);
  });
  // Don't hang forever if a connection won't drain.
  setTimeout(() => {
    console.error('Shutdown timed out — forcing checkpoint + exit.');
    checkpointAndClose();
    process.exit(1);
  }, 10_000).unref();
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
