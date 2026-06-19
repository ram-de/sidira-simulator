// ============================================================================
// THE LEAKAGE FIREWALL
// ----------------------------------------------------------------------------
// Two PHYSICALLY SEPARATE tables, mirroring the Hillstrom panel discipline
// ("the outcome must never enter the clustering or the pack would leak the
// answer key" — hillstrom_archive.py). The persona pack is built from
// player_features ONLY; the arm + outcome live in a separate, sealed table.
//
//   Table A  player_features   PRE-TREATMENT features only.
//                              NO arm. NO outcome. NO post-treatment field.
//                              This is the ONLY table run_pipeline ever sees.
//
//   Table B  player_outcomes   The SEALED answer key: arm, task_id, binary
//                              outcome, timestamps, attention_passed.
//                              NEVER fed to the pipeline.
//
// The two writer functions below enforce this at the code boundary:
// recordFeature() refuses any key named like an arm/outcome; outcomes only go
// through recordOutcome() into Table B.
// ============================================================================

import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import Database from 'better-sqlite3';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.resolve(__dirname, '..', 'data');
const DB_PATH = process.env.FF_DB_PATH || path.join(DATA_DIR, 'ff.db');

fs.mkdirSync(DATA_DIR, { recursive: true });

const db = new Database(DB_PATH);
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

db.exec(`
  -- ----------------------------------------------------------------------
  -- Participant registry. The token does NOT encode the arm. The arm is
  -- assigned server-side on first load and stored here, sticky per person.
  -- ----------------------------------------------------------------------
  CREATE TABLE IF NOT EXISTS participants (
    player_id        TEXT PRIMARY KEY,
    token            TEXT UNIQUE NOT NULL,      -- per-recipient token (no arm in it)
    headline_arm     TEXT NOT NULL,             -- between-subject arm (NOT exposed to client)
    counterbalance   TEXT NOT NULL,             -- JSON: within-subject micro-A/B order/variant map
    created_at       TEXT NOT NULL,
    referrer         TEXT,                       -- where they arrived from
    is_forwarded     INTEGER NOT NULL DEFAULT 0, -- 1 if token was reused from a different referrer
    completed_at     TEXT
  );

  -- ----------------------------------------------------------------------
  -- TABLE A — player_features (PRE-TREATMENT ONLY). The pipeline input.
  -- One row per player, columns filled in as beats complete. Every field is
  -- a pre-treatment feature: demographics, the 5 decision-style scores, and
  -- gameplay-revealed passive behavioral features. NO arm. NO outcome.
  -- ----------------------------------------------------------------------
  CREATE TABLE IF NOT EXISTS player_features (
    player_id               TEXT PRIMARY KEY,

    -- demographics (tap-only "Seller Card", post-game but pre-reveal)
    age_band                TEXT,    -- categorical
    locale                  TEXT,    -- categorical
    device                  TEXT,    -- categorical
    tenure_days             INTEGER, -- tenure_days

    -- the 5 decision-style scores (revealed through profiling-room play)
    decision_speed          REAL,    -- score
    deal_sensitivity        REAL,    -- score
    present_bias            REAL,    -- score
    effort_tolerance        REAL,    -- score
    reactance               REAL,    -- score

    -- additional decision-style scores from the Deal / Trust / Ambiguity rooms
    -- (#440). Pre-treatment ONLY, identical across arms, never outcome-shaped.
    patience                REAL,    -- score (Deal room: wait/counter vs take-now)
    trust                   REAL,    -- score (Trust game: tripled coins sent)
    reciprocity             REAL,    -- score (Trust game: returned a fair share back)
    ambiguity_aversion      REAL,    -- score (Ambiguity room: known odds vs mystery)

    -- gameplay-revealed passive behavioral features (can't be gamed)
    warmup_decision_ms      INTEGER, -- count (latency)
    warmup_options_inspected INTEGER,-- count
    warmup_skip_rate        REAL,    -- ratio
    warmup_reread_rate      REAL,    -- ratio

    updated_at              TEXT
    -- INTENTIONALLY ABSENT: arm, outcome, task_id, any post-treatment signal.
  );

  -- ----------------------------------------------------------------------
  -- TABLE B — player_outcomes (the SEALED answer key). NEVER fed to pipeline.
  -- One row per (player, micro-A/B task). Holds the arm + binary outcome.
  -- ----------------------------------------------------------------------
  CREATE TABLE IF NOT EXISTS player_outcomes (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id        TEXT NOT NULL,
    arm              TEXT NOT NULL,    -- the variant the player actually saw
    task_id          TEXT NOT NULL,    -- which micro-A/B
    outcome          INTEGER NOT NULL, -- the primary binary outcome (0/1)
    attention_passed INTEGER,          -- attention check (nullable until known)
    started_at       TEXT,
    decided_at       TEXT,
    UNIQUE (player_id, task_id)
  );

  -- ----------------------------------------------------------------------
  -- Per-beat event log (raw telemetry). Pre-treatment beats feed Table A;
  -- micro-A/B beats are the provenance for Table B. Kept raw + append-only
  -- so the feature derivation is auditable and re-runnable.
  -- ----------------------------------------------------------------------
  CREATE TABLE IF NOT EXISTS events (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id        TEXT NOT NULL,
    beat_id          TEXT NOT NULL,    -- room/task identifier
    phase            TEXT NOT NULL,    -- 'profiling' | 'microab' | 'demographics'
    choice           TEXT,             -- the choice made (JSON-encoded)
    latency_ms       INTEGER,          -- latency to first tap
    retap_count      INTEGER,          -- re-taps / scrubs
    dwell_ms         INTEGER,          -- total dwell on the beat
    fine_print_opened INTEGER,         -- 1 if they expanded fine print
    options_inspected INTEGER,         -- how many options they inspected
    arm              TEXT,             -- arm/variant (for microab beats only)
    referrer         TEXT,
    created_at       TEXT NOT NULL
  );
`);

// ----------------------------------------------------------------------------
// Additive migration: the schema above uses CREATE TABLE IF NOT EXISTS, so a DB
// created before #440 won't have the new pre-treatment score columns. Add any
// missing player_features columns idempotently. (#440 — Deal / Trust / Ambiguity.)
// Pre-treatment scores only; NO arm/outcome columns are ever added here.
// ----------------------------------------------------------------------------
{
  const existing = new Set(
    db.prepare(`PRAGMA table_info(player_features)`).all().map((c) => c.name),
  );
  const ADDED_FEATURE_COLUMNS = [
    ['patience', 'REAL'],
    ['trust', 'REAL'],
    ['reciprocity', 'REAL'],
    ['ambiguity_aversion', 'REAL'],
  ];
  for (const [name, type] of ADDED_FEATURE_COLUMNS) {
    if (!existing.has(name)) {
      db.exec(`ALTER TABLE player_features ADD COLUMN ${name} ${type}`);
    }
  }
}

const isoNow = () => new Date().toISOString();

// ----------------------------------------------------------------------------
// Participant resolution / creation.
// ----------------------------------------------------------------------------
export function findByToken(token) {
  return db.prepare('SELECT * FROM participants WHERE token = ?').get(token);
}

export function createParticipant({ playerId, token, headlineArm, counterbalance, referrer }) {
  db.prepare(
    `INSERT INTO participants
       (player_id, token, headline_arm, counterbalance, created_at, referrer, is_forwarded)
     VALUES (?, ?, ?, ?, ?, ?, 0)`,
  ).run(playerId, token, headlineArm, JSON.stringify(counterbalance), isoNow(), referrer || null);
  // Open the Table A row immediately (features filled in beat-by-beat).
  db.prepare('INSERT OR IGNORE INTO player_features (player_id, updated_at) VALUES (?, ?)').run(
    playerId,
    isoNow(),
  );
  return findByToken(token);
}

// Log a forwarded visit: same token arrived from a different referrer. We keep
// the original sticky assignment (primary analysis = original-token users only)
// but flag it so the analysis can filter forwarded traffic out.
export function markForwarded(playerId, referrer) {
  db.prepare('UPDATE participants SET is_forwarded = 1, referrer = COALESCE(referrer, ?) WHERE player_id = ?').run(
    referrer || null,
    playerId,
  );
}

export function markCompleted(playerId) {
  db.prepare('UPDATE participants SET completed_at = ? WHERE player_id = ?').run(isoNow(), playerId);
}

// ----------------------------------------------------------------------------
// TABLE A writer — pre-treatment features ONLY.
// Hard guard: refuse any column that smells like an arm or outcome. This is the
// code-level enforcement of the leakage firewall.
// ----------------------------------------------------------------------------
const FEATURE_COLUMNS = new Set([
  'age_band', 'locale', 'device', 'tenure_days',
  'decision_speed', 'deal_sensitivity', 'present_bias', 'effort_tolerance', 'reactance',
  // #440 — Deal / Trust / Ambiguity room scores (pre-treatment, never outcome-shaped)
  'patience', 'trust', 'reciprocity', 'ambiguity_aversion',
  'warmup_decision_ms', 'warmup_options_inspected', 'warmup_skip_rate', 'warmup_reread_rate',
]);
// Match arm/outcome-shaped keys, but anchored so legitimate feature names
// aren't false-positives (e.g. "warmup_*" must NOT trip on the "arm" in "warm").
const FORBIDDEN_FEATURE_KEYS = /(^|_)(arm|outcome|task|treatment|variant|reveal|persona)(_|$)/i;

export function recordFeature(playerId, patch) {
  const cols = [];
  const vals = [];
  for (const [k, v] of Object.entries(patch)) {
    if (FORBIDDEN_FEATURE_KEYS.test(k)) {
      // LEAKAGE FIREWALL: an arm/outcome/post-treatment field tried to enter
      // Table A. This is the exact failure mode the firewall exists to stop.
      throw new Error(`LEAKAGE FIREWALL: refusing to write post-treatment key "${k}" into player_features`);
    }
    if (!FEATURE_COLUMNS.has(k)) continue; // ignore unknown keys silently
    cols.push(`${k} = ?`);
    vals.push(v);
  }
  if (cols.length === 0) return;
  vals.push(isoNow(), playerId);
  db.prepare(
    `UPDATE player_features SET ${cols.join(', ')}, updated_at = ? WHERE player_id = ?`,
  ).run(...vals);
}

export function getFeatures(playerId) {
  return db.prepare('SELECT * FROM player_features WHERE player_id = ?').get(playerId);
}

// ----------------------------------------------------------------------------
// TABLE B writer — the sealed answer key. The ONLY path arm+outcome may be
// written. Idempotent per (player, task) so resume/repeat can't double-count.
// ----------------------------------------------------------------------------
export function recordOutcome({ playerId, arm, taskId, outcome, attentionPassed, startedAt, decidedAt }) {
  db.prepare(
    `INSERT INTO player_outcomes (player_id, arm, task_id, outcome, attention_passed, started_at, decided_at)
     VALUES (?, ?, ?, ?, ?, ?, ?)
     ON CONFLICT(player_id, task_id) DO UPDATE SET
       arm = excluded.arm,
       outcome = excluded.outcome,
       attention_passed = excluded.attention_passed,
       decided_at = excluded.decided_at`,
  ).run(
    playerId, arm, taskId, outcome ? 1 : 0,
    attentionPassed == null ? null : (attentionPassed ? 1 : 0),
    startedAt || null, decidedAt || isoNow(),
  );
}

export function getOutcomes(playerId) {
  return db.prepare('SELECT task_id, outcome FROM player_outcomes WHERE player_id = ?').all(playerId);
}

// ----------------------------------------------------------------------------
// Event log writer + the feature derivation it feeds.
// ----------------------------------------------------------------------------
export function recordEvent(playerId, ev) {
  db.prepare(
    `INSERT INTO events
       (player_id, beat_id, phase, choice, latency_ms, retap_count, dwell_ms,
        fine_print_opened, options_inspected, arm, referrer, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
  ).run(
    playerId, ev.beatId, ev.phase,
    ev.choice == null ? null : JSON.stringify(ev.choice),
    ev.latencyMs ?? null, ev.retapCount ?? null, ev.dwellMs ?? null,
    ev.finePrintOpened ? 1 : 0, ev.optionsInspected ?? null,
    ev.arm ?? null, ev.referrer ?? null, isoNow(),
  );
}

// Recompute the passive gameplay-revealed features from the profiling-phase
// event log. Called after each profiling beat so Table A stays current and is
// fully reconstructable from the raw log (auditability).
export function derivePassiveFeatures(playerId) {
  const rows = db
    .prepare(`SELECT latency_ms, options_inspected, choice, dwell_ms FROM events
              WHERE player_id = ? AND phase = 'profiling'`)
    .all(playerId);
  if (rows.length === 0) return;

  const latencies = rows.map((r) => r.latency_ms).filter((x) => x != null);
  const inspected = rows.map((r) => r.options_inspected ?? 0);
  const skips = rows.filter((r) => {
    try {
      const c = r.choice ? JSON.parse(r.choice) : null;
      return c && c.skipped === true;
    } catch {
      return false;
    }
  }).length;

  const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0);
  // reread_rate proxy: dwell well above the median latency suggests re-reading.
  const dwells = rows.map((r) => r.dwell_ms ?? 0);
  const reread = dwells.filter((d) => d > mean(latencies) * 2).length;

  recordFeature(playerId, {
    warmup_decision_ms: Math.round(mean(latencies)),
    warmup_options_inspected: Math.round(mean(inspected)),
    warmup_skip_rate: rows.length ? skips / rows.length : 0,
    warmup_reread_rate: rows.length ? reread / rows.length : 0,
  });
}

export default db;
