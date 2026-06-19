import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The SPA is served by the Express app on a single port (see server/index.js):
// Vite runs in middleware mode in dev, and Express serves the built dist/ in prod.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
  },
});
