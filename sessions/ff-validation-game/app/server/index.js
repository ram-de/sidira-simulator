// Server entry — one port for everything.
// Dev:  Vite runs in middleware mode and serves the SPA through this Express app.
// Prod: Express serves the built dist/ alongside the API.

import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import express from 'express';
import { createApp } from './app.js';

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
  app.use(express.static(dist, { index: false }));
  app.use((_req, res) => res.sendFile(indexHtml));
} else {
  const { createServer } = await import('vite');
  const vite = await createServer({
    root,
    appType: 'spa',
    server: { middlewareMode: true },
  });
  app.use(vite.middlewares);
}

app.listen(PORT, () => {
  console.log(`Split The Loot ${isProd ? '(prod)' : '(dev)'} on http://localhost:${PORT}`);
});
