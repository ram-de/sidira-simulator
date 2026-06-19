#!/usr/bin/env node
// ============================================================================
// SYNTHETIC player_features.csv GENERATOR — FOR PIPELINE TESTING ONLY.
// ----------------------------------------------------------------------------
// ⚠️  THIS IS SYNTHETIC DATA. NOT REAL PLAYERS. NOT REAL OUTCOMES.  ⚠️
//
// It exists so the data → persona-pack → engine-loader path (ticket #443) can
// be wired and tested end-to-end BEFORE any friend or family member has played
// the game. The moment real players exist, the real `player_features.csv` is
// produced by `npm run export:features` (Table A) and the pack is rebuilt from
// THAT — this file and the pack derived from it are throwaway test scaffolding.
//
// The emitted CSV is shaped EXACTLY like the real export
// (`scripts/export_features.js` → `exports/player_features.csv`): the same
// pre-treatment columns, in the same order, with the same types/ranges. It
// carries the leakage firewall by construction — there is NO arm, NO outcome,
// NO task/treatment/variant column. (The same FORBIDDEN guard the real export
// uses is re-asserted here before writing.)
//
// To make the clustering meaningful (and the per-cluster Jaccard sane at
// k ∈ [2,4]), the rows are drawn from a small mixture of latent "play styles"
// with PLAUSIBLE COVARIATION across the demographic + 5 decision-style + #440
// + gameplay-revealed features (e.g. a decisive player taps fast → high
// decision_speed AND low warmup_decision_ms AND inspects fewer options). The
// latent style label is deliberately NOT emitted — the pipeline must discover
// the segments.
//
//   Run:  node scripts/gen_synthetic_features.js [N] [outPath]
//   e.g.  node scripts/gen_synthetic_features.js 60 ../friends_family_synthetic_features.csv
// ============================================================================

import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const N = Number.parseInt(process.argv[2] ?? '60', 10);
const OUT = process.argv[3]
  ? path.resolve(process.cwd(), process.argv[3])
  : path.join(__dirname, '..', 'exports', 'player_features.csv');

// Column order MUST mirror Table A (`server/db.js` player_features), minus the
// bookkeeping `updated_at` (which `export_features.js` carries, but which the
// pipeline ignores — we keep player_id + the feature columns the pack uses).
const COLUMNS = [
  'player_id',
  // demographics
  'age_band', 'locale', 'device', 'tenure_days',
  // the 5 decision-style scores
  'decision_speed', 'deal_sensitivity', 'present_bias', 'effort_tolerance', 'reactance',
  // #440 Deal / Trust / Ambiguity room scores
  'patience', 'trust', 'reciprocity', 'ambiguity_aversion',
  // gameplay-revealed passive features
  'warmup_decision_ms', 'warmup_options_inspected', 'warmup_skip_rate', 'warmup_reread_rate',
];

// Same anchored firewall regex as db.recordFeature / export_features.js.
const FORBIDDEN = /(^|_)(arm|outcome|task|treatment|variant|reveal|persona)(_|$)/i;
for (const c of COLUMNS) {
  if (FORBIDDEN.test(c)) {
    throw new Error(`SYNTHETIC GENERATOR: forbidden column "${c}" — would breach the leakage firewall`);
  }
}

// --- a tiny seeded RNG so the synthetic CSV is reproducible -----------------
function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rng = mulberry32(443);
const rand = () => rng();
const randn = () => {
  // Box-Muller, clamped to keep draws in-distribution.
  const u = Math.max(rand(), 1e-9);
  const v = rand();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
};
const clamp01 = (x) => Math.max(0, Math.min(1, x));
const round2 = (x) => Math.round(clamp01(x) * 100) / 100;
const pick = (arr) => arr[Math.floor(rand() * arr.length)];
const weightedPick = (pairs) => {
  // pairs: [[value, weight], ...]
  const total = pairs.reduce((s, [, w]) => s + w, 0);
  let r = rand() * total;
  for (const [val, w] of pairs) {
    if ((r -= w) <= 0) return val;
  }
  return pairs[pairs.length - 1][0];
};

const AGE = ['18-24', '25-34', '35-44', '45-54', '55+'];
const LOCALE = ['US', 'EU', 'UK', 'APAC', 'Other'];
const DEVICE = ['mobile', 'desktop'];
const TENURE = [0, 30, 365]; // SellerCard maps the 3 history taps to these day counts.

// ----------------------------------------------------------------------------
// Three latent "play styles". Each carries a center for every continuous score
// plus skewed demographic/gameplay tendencies. The styles are intentionally
// SEPARABLE on the decision-style axes (so GMM can recover them) yet overlap
// enough that per-cluster Jaccard stays realistic (not a trivial 1.0).
//
//   decisive   — fast, deal-driven, present-biased, low effort tolerance, low
//                ambiguity aversion; taps quickly, inspects little, skips more.
//   deliberate — slow, patient, high effort tolerance, inspects everything,
//                rereads; trusting + reciprocal, ambiguity-averse.
//   contrarian — reactant, low trust, middling speed; moderate on most axes but
//                pushes back (high reactance, low reciprocity).
// ----------------------------------------------------------------------------
// The three styles are well-SEPARATED on the decision-style axes (centers pushed
// apart, tight within-style spread) so the GMM recovers them as three stable,
// roughly-equal-sized clusters (≥~10 players each, per-cluster Jaccard well above
// the 0.6 floor) AND so BIC over k∈[2,4] lands on k=3 rather than over-splitting.
// They still differ across the full feature set (not just one axis) so the
// covariation is realistic, not a single toy gradient.
const STYLES = [
  {
    name: 'decisive', mix: 0.34,
    c: { decision_speed: 0.88, deal_sensitivity: 0.82, present_bias: 0.80,
         effort_tolerance: 0.18, reactance: 0.30, patience: 0.20, trust: 0.55,
         reciprocity: 0.55, ambiguity_aversion: 0.22 },
    age: [['18-24', 3], ['25-34', 4], ['35-44', 2], ['45-54', 1], ['55+', 1]],
    device: [['mobile', 4], ['desktop', 1]],
    tenure: [[0, 3], [30, 2], [365, 1]],
  },
  {
    name: 'deliberate', mix: 0.33,
    c: { decision_speed: 0.18, deal_sensitivity: 0.38, present_bias: 0.20,
         effort_tolerance: 0.88, reactance: 0.22, patience: 0.84, trust: 0.78,
         reciprocity: 0.80, ambiguity_aversion: 0.80 },
    age: [['18-24', 1], ['25-34', 2], ['35-44', 3], ['45-54', 3], ['55+', 2]],
    device: [['mobile', 2], ['desktop', 3]],
    tenure: [[0, 1], [30, 2], [365, 3]],
  },
  {
    name: 'contrarian', mix: 0.33,
    c: { decision_speed: 0.50, deal_sensitivity: 0.52, present_bias: 0.50,
         effort_tolerance: 0.48, reactance: 0.88, patience: 0.46, trust: 0.18,
         reciprocity: 0.20, ambiguity_aversion: 0.50 },
    age: [['18-24', 2], ['25-34', 3], ['35-44', 2], ['45-54', 2], ['55+', 1]],
    device: [['mobile', 3], ['desktop', 2]],
    tenure: [[0, 2], [30, 2], [365, 1]],
  },
];

function chooseStyle() {
  const total = STYLES.reduce((s, st) => s + st.mix, 0);
  let r = rand() * total;
  for (const st of STYLES) {
    if ((r -= st.mix) <= 0) return st;
  }
  return STYLES[STYLES.length - 1];
}

const SCORE_SIGMA = 0.075; // within-style spread on the 0..1 scores (tight → separable).
const draw = (center) => round2(center + randn() * SCORE_SIGMA);

function makeRow(i) {
  const st = chooseStyle();

  // 5 decision-style scores + #440 scores, drawn around the style centers.
  const decision_speed = draw(st.c.decision_speed);
  const deal_sensitivity = draw(st.c.deal_sensitivity);
  const present_bias = draw(st.c.present_bias);
  const effort_tolerance = draw(st.c.effort_tolerance);
  const reactance = draw(st.c.reactance);
  const patience = draw(st.c.patience);
  const trust = draw(st.c.trust);
  const reciprocity = draw(st.c.reciprocity);
  const ambiguity_aversion = draw(st.c.ambiguity_aversion);

  // Gameplay-revealed features, COVARYING with the latent style (the same
  // signal the real rooms produce): a fast decision_speed ⇒ low first-tap
  // latency; high effort_tolerance ⇒ more options inspected + more rereads;
  // a present-biased/impatient player skips more. Mirrors db.derivePassiveFeatures.
  const warmup_decision_ms = Math.max(
    200,
    Math.round((1 - decision_speed) * 5200 + 300 + randn() * 450),
  );
  const warmup_options_inspected = Math.max(
    0,
    Math.round(1 + effort_tolerance * 4 + randn() * 0.8),
  );
  const warmup_skip_rate = round2(
    clamp01(0.05 + present_bias * 0.35 + (1 - patience) * 0.15 + randn() * 0.06),
  );
  const warmup_reread_rate = round2(
    clamp01(effort_tolerance * 0.45 + ambiguity_aversion * 0.15 + randn() * 0.06),
  );

  return {
    player_id: `synthetic-${String(i + 1).padStart(3, '0')}`,
    age_band: weightedPick(st.age),
    locale: weightedPick([['US', 4], ['EU', 2], ['UK', 2], ['APAC', 1], ['Other', 1]]),
    device: weightedPick(st.device),
    tenure_days: weightedPick(st.tenure),
    decision_speed,
    deal_sensitivity,
    present_bias,
    effort_tolerance,
    reactance,
    patience,
    trust,
    reciprocity,
    ambiguity_aversion,
    warmup_decision_ms,
    warmup_options_inspected,
    warmup_skip_rate,
    warmup_reread_rate,
  };
}

function toCsv(rows) {
  const esc = (v) => {
    if (v == null) return '';
    const s = String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [COLUMNS.join(','), ...rows.map((r) => COLUMNS.map((c) => esc(r[c])).join(','))].join('\n') + '\n';
}

const rows = Array.from({ length: N }, (_, i) => makeRow(i));
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, toCsv(rows));
console.log(`SYNTHETIC player_features.csv → ${OUT}`);
console.log(`  ${rows.length} synthetic rows, ${COLUMNS.length} columns (pre-treatment ONLY, NO arm/outcome).`);
console.log('  ⚠️  SYNTHETIC DATA for pipeline testing only — not real players, not real outcomes.');
