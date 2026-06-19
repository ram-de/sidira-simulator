#!/usr/bin/env node
// ============================================================================
// DATA EXPORT — with the leakage firewall preserved at the export boundary.
// ----------------------------------------------------------------------------
// Writes TWO separate files:
//
//   exports/player_features.csv   Table A ONLY. PRE-TREATMENT features. This is
//                                 the shape `sidira-personas run_pipeline`
//                                 ingests. Personas are built from THIS FILE
//                                 ALONE — it contains NO arm and NO outcome.
//
//   exports/player_outcomes.csv   Table B. The SEALED answer key (arm + binary
//                                 outcome per micro-A/B). This file is NEVER fed
//                                 to run_pipeline. Keep it sealed/role-separated:
//                                 the person who runs the engine must not open
//                                 this until predictions are committed.
//
// Run: npm run export:features
// ============================================================================

import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import Database from 'better-sqlite3';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '..');
const DB_PATH = process.env.FF_DB_PATH || path.join(root, 'data', 'ff.db');
const OUT_DIR = path.join(root, 'exports');

if (!fs.existsSync(DB_PATH)) {
  console.error(`No DB at ${DB_PATH}. Run the game first (npm run dev) to generate data.`);
  process.exit(1);
}
fs.mkdirSync(OUT_DIR, { recursive: true });

const db = new Database(DB_PATH, { readonly: true });

function toCsv(rows) {
  if (rows.length === 0) return '';
  const cols = Object.keys(rows[0]);
  const esc = (v) => {
    if (v == null) return '';
    const s = String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [cols.join(','), ...rows.map((r) => cols.map((c) => esc(r[c])).join(','))].join('\n') + '\n';
}

// --- Table A → features CSV (the pipeline input) ---------------------------
const features = db.prepare('SELECT * FROM player_features').all();
// Hard guard: assert no arm/outcome column ever leaked into Table A.
// Anchored so "warmup_*" feature columns aren't false-positives on "arm".
const FORBIDDEN = /(^|_)(arm|outcome|task|treatment|variant)(_|$)/i;
for (const col of features[0] ? Object.keys(features[0]) : []) {
  if (FORBIDDEN.test(col)) {
    console.error(`LEAKAGE FIREWALL VIOLATION: player_features has a forbidden column "${col}". Aborting export.`);
    process.exit(2);
  }
}
const featuresPath = path.join(OUT_DIR, 'player_features.csv');
fs.writeFileSync(featuresPath, toCsv(features));

// --- Table B → SEALED outcomes CSV (the answer key) ------------------------
const outcomes = db.prepare('SELECT * FROM player_outcomes').all();
const outcomesPath = path.join(OUT_DIR, 'player_outcomes.csv');
fs.writeFileSync(outcomesPath, toCsv(outcomes));

console.log(`Table A → ${featuresPath}  (${features.length} players, pipeline input — NO arm/outcome)`);
console.log(`Table B → ${outcomesPath}  (${outcomes.length} outcome rows, SEALED answer key — do NOT feed to run_pipeline)`);
