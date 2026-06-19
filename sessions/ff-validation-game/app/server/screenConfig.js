// ============================================================================
// SCREEN CONFIG BUILDER
// ----------------------------------------------------------------------------
// Translates the server-side assignment into a RENDERED config for the client.
// Critical blind rule: the client receives only what to render — never a
// guessable arm label ("control"/"treatment"/"calm"/"urgent"). The headline
// arm shapes the countdown_urgency micro-A/B presentation; the client cannot
// reverse it into the arm name.
// ============================================================================

// The fixed, identical-for-everyone profiling rooms (PRE-treatment, no A/B).
// Two are fully implemented as the pattern; the rest are stubbed (see client).
const PROFILING_ROOMS = [
  { id: 'risk_box', status: 'done' },     // DONE — risk appetite / EV-sensitivity / latency
  { id: 'info_cost', status: 'done' },    // DONE — attention/effort / info valuation / overconfidence
  { id: 'deal_room', status: 'stub' },    // TODO — present-bias / patience / deal sensitivity
  { id: 'trust_game', status: 'stub' },   // TODO — trust / reciprocity / social skepticism
  { id: 'ambiguity', status: 'stub' },    // TODO — ambiguity aversion / opaque-system skepticism
];

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
      // TODO: stubbed micro-A/Bs — render a placeholder beat that still logs a
      // (neutral) outcome so the state machine completes; replace with the real
      // counter-intuitive mechanic before sealing.
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
