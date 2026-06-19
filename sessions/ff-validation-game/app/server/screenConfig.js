// ============================================================================
// SCREEN CONFIG BUILDER
// ----------------------------------------------------------------------------
// Translates the server-side assignment into a RENDERED config for the client.
// Critical blind rule: the client receives only what to render — never a
// guessable arm label ("control"/"treatment"/"calm"/"urgent"). The headline
// arm shapes the countdown_urgency micro-A/B presentation; the client cannot
// reverse it into the arm name.
// ============================================================================

import crypto from 'node:crypto';

// The fixed, identical-for-everyone profiling rooms (PRE-treatment, no A/B).
// All five are now implemented (#440). Identical across arms.
const PROFILING_ROOMS = [
  { id: 'risk_box', status: 'done' },     // DONE — risk appetite / EV-sensitivity / latency
  { id: 'info_cost', status: 'done' },    // DONE — attention/effort / info valuation / overconfidence
  { id: 'deal_room', status: 'done' },    // DONE — present-bias / patience / deal sensitivity
  { id: 'trust_game', status: 'done' },   // DONE — trust / reciprocity / social skepticism
  { id: 'ambiguity', status: 'done' },    // DONE — ambiguity aversion / opaque-system skepticism
];

// Deterministic within-subject variant pick for the micro-A/Bs added in #441.
// Seeded by player_id + task_id so it is STICKY per person (stable on resume)
// without touching the between-subject headline arm or the block randomization
// in randomize.js. Returns one of the two presentation variants. The variant is
// a presentation label only — the client never receives the headline-arm name.
function pickVariant(playerId, taskId, variants) {
  const h = crypto.createHash('sha256').update(`${taskId}-${playerId}`).digest();
  return variants[h[0] % variants.length];
}

export function buildScreenConfig(participant) {
  const counterbalance = JSON.parse(participant.counterbalance);
  const headlineArm = participant.headline_arm; // NEVER sent to client as-is.

  // Build the micro-A/B battery config in the counterbalanced order. For each
  // item we emit a `present` blob the client renders verbatim. The headline
  // arm (between-subject) controls the countdown_urgency framing; we fold it in
  // here so the client never sees the arm name.
  const microabs = counterbalance.order.map((taskId) => {
    switch (taskId) {
      case 'choice_overload':
        // Within-subject: every player decides this; the engine predicts the
        // population direction (3 options → higher choose-rate than 24).
        // The variant the player sees here is the headline-independent paired
        // assignment; we counterbalance which set renders first via the seed.
        return {
          taskId,
          status: 'done',
          present: {
            kind: 'choice_overload',
            // choice_overload runs as a single decision under ONE option-count,
            // randomized per player (between players, within the battery).
            optionCount: counterbalance.variants.choice_overload === 'few' ? 3 : 24,
          },
        };
      case 'countdown_urgency': {
        // The BETWEEN-subject headline arm drives the framing. 'urgent' = an
        // aggressive countdown + "only 3 left"; 'calm' = no pressure. We map
        // arm → rendered framing without ever sending the arm label.
        const scarce = headlineArm === 'urgent';
        return {
          taskId,
          status: 'done',
          present: {
            kind: 'countdown_urgency',
            countdownSeconds: scarce ? 10 : 0,
            showScarcity: scarce,
          },
        };
      }
      // Within-subject micro-A/Bs added in #441. Each player sees ONE variant,
      // assigned deterministically (sticky) per player_id+task_id. The variant
      // is a presentation label only; the headline arm name is never leaked.
      case 'default_stickiness':
        return {
          taskId,
          status: 'done',
          present: {
            kind: 'default_stickiness',
            variant: pickVariant(participant.player_id, taskId, ['default', 'framing']),
          },
        };
      case 'prosocial_backfire':
        return {
          taskId,
          status: 'done',
          present: {
            kind: 'prosocial_backfire',
            variant: pickVariant(participant.player_id, taskId, ['polished', 'sparse']),
          },
        };
      case 'effort_justification':
        return {
          taskId,
          status: 'done',
          present: {
            kind: 'effort_justification',
            variant: pickVariant(participant.player_id, taskId, ['effort', 'one_tap']),
          },
        };
      default:
        return { taskId, status: 'stub', present: { kind: 'stub', taskId } };
    }
  });

  return {
    playerId: participant.player_id,
    completed: !!participant.completed_at,
    profilingRooms: PROFILING_ROOMS,
    microabs,
    // The 7-dot progress map the client renders. intro + 5 rooms + battery +
    // seller card + reveal collapse into 7 logical steps; the client owns the
    // exact dot mapping.
    steps: ['intro', 'profiling', 'microabs', 'sellercard', 'reveal'],
  };
}
