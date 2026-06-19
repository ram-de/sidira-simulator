// ============================================================================
// SERVER-SIDE RANDOMIZATION (the experiment lens's hard correction)
// ----------------------------------------------------------------------------
// "Do NOT use send-link-A = control, link-B = treatment." Whoever routes
// friends to links IS the assignment mechanism → fatal selection confound.
//
// Instead: ONE link (or per-recipient tokens that do NOT encode the arm). The
// SERVER randomizes the between-subject headline arm + the within-subject
// counterbalancing on first load, persists it sticky per person, and NEVER
// returns a guessable arm label to the client — only the rendered config.
//
// Block randomization (permuted blocks) guarantees a balanced split at small N
// — a 26/14 headline split can't happen by chance.
// ============================================================================

import crypto from 'node:crypto';
import db from './db.js';

// The between-subject HEADLINE arm. Spec: the scarcity/deadline-backfire item
// runs BETWEEN-subject ("you can't un-ring the urgency bell"). 'urgent' shows
// the aggressive countdown + "only 3 left"; 'calm' shows the calm variant.
export const HEADLINE_ARMS = ['calm', 'urgent'];
const BLOCK = ['calm', 'urgent', 'urgent', 'calm']; // one permuted block (balanced)

// Within-subject micro-A/Bs are counterbalanced: each player sees a randomized
// order and, where the item has a paired variant, a randomized variant. The
// engine predicts the POPULATION direction; counterbalancing controls order.
// Spec micro-A/B roster (≥5; the 2 fully-built ones are marked DONE):
export const MICRO_ABS = [
  'choice_overload',  // DONE — 3 options vs 24
  'countdown_urgency',// DONE — aggressive countdown vs calm (within-subject framing variant)
  // TODO: stubbed — implement these to reach the K>=5 sealed-win bar:
  'default_stickiness',
  'prosocial_backfire',
  'effort_justification',
];

function pickHeadlineArm() {
  // Permuted-block randomization: count how far into the current block we are
  // (modulo block length), shuffle the block deterministically per fill, and
  // take the next slot. At this scale a fresh shuffled block per participant is
  // enough to keep the split balanced; we seed off the live count for balance.
  const assigned = db.prepare('SELECT COUNT(*) AS n FROM participants').get().n;
  const block = shuffle([...BLOCK], `block-${Math.floor(assigned / BLOCK.length)}`);
  return block[assigned % BLOCK.length];
}

// Deterministic Fisher–Yates from a string seed (so a block is reproducible).
function shuffle(arr, seed) {
  const h = crypto.createHash('sha256').update(seed).digest();
  let i = arr.length;
  let k = 0;
  while (i > 1) {
    const j = h[k % h.length] % i;
    i -= 1;
    [arr[i], arr[j]] = [arr[j], arr[i]];
    k += 1;
  }
  return arr;
}

function buildCounterbalance(playerId) {
  // Randomize the within-subject micro-A/B ORDER, and assign a paired variant
  // where the item is counterbalanced (here: which framing countdown_urgency
  // shows first). Seeded by player_id so it's stable on resume.
  const order = shuffle([...MICRO_ABS], `order-${playerId}`);
  const variants = {
    // countdown_urgency within-subject framing variant (counterbalanced)
    countdown_urgency: shuffle(['scarce', 'calm'], `cu-${playerId}`)[0],
    // choice_overload: each player faces ONE option-count (3 or 24), randomized
    // between players, so the engine predicts the population choose-rate split.
    choice_overload: shuffle(['few', 'many'], `co-${playerId}`)[0],
  };
  return { order, variants };
}

// Resolve an existing participant by token, or create + randomize a new one.
// Returns { participant, created }. The arm is decided HERE, server-side.
export function resolveParticipant(token, referrer) {
  const existing = db.prepare('SELECT * FROM participants WHERE token = ?').get(token);
  if (existing) {
    return { participant: existing, created: false };
  }
  const playerId = crypto.randomUUID();
  const headlineArm = pickHeadlineArm();
  const counterbalance = buildCounterbalance(playerId);
  db.prepare(
    `INSERT INTO participants
       (player_id, token, headline_arm, counterbalance, created_at, referrer, is_forwarded)
     VALUES (?, ?, ?, ?, ?, ?, 0)`,
  ).run(playerId, token, headlineArm, JSON.stringify(counterbalance), new Date().toISOString(), referrer || null);
  db.prepare('INSERT OR IGNORE INTO player_features (player_id, updated_at) VALUES (?, ?)').run(
    playerId,
    new Date().toISOString(),
  );
  const participant = db.prepare('SELECT * FROM participants WHERE token = ?').get(token);
  return { participant, created: true };
}

// Mint a fresh single-use token (used when someone hits the app with no token —
// the "one link" lands here and gets its own server-side assignment).
export function mintToken() {
  return crypto.randomBytes(12).toString('base64url');
}
