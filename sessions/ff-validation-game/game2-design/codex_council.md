Reading additional input from stdin...
OpenAI Codex v0.137.0
--------
workdir: /Users/ram/Projects/sidira-simulator/.claude/worktrees/benchmark-gate-validation
model: gpt-5.5
provider: openai
approval: never
sandbox: read-only
reasoning effort: none
reasoning summaries: none
session id: 019edeb3-b5df-7742-9f15-28a7ba26fa94
--------
user
You are a panel of frontier product + behavioral-science researchers. Design a SECOND friends-&-family game (DESIGN ONLY — a mockup, no code) to validate a behavioral-simulation engine. The first game is text/decision-heavy; this one must be MORE INTERACTIVE and LESS VERBAL — traits revealed by HOW players interact (tap timing, drag, hold, explore, risk-in-motion, persistence), not by reading scenarios.

Hard requirements: (1) profiles each player through interaction → per-player behavioral features to build a persona pack (capability test on a consistent population). (2) Bakes in counter-intuitive A/B tests — as UI/INTERACTION-design manipulations where the obvious choice loses or ties (the engine already nails obvious cases and fails counter-intuitive ones). (3) One link, server-side randomized arm (never in URL; a hand-routed two-link design is a fatal selection confound); a battery of >=5 micro-A/Bs (>=half counter-intuitive), within-subject where possible; score hit-rate vs an always-pick-obvious placebo. (4) Two-table leakage firewall (pre-treatment interaction features vs sealed arm+outcome); blinded + sealed role-separated validation; REAL behavioral outcomes not stated preferences. (5) ~3-5 min, mobile-first, taps/drags/holds only, shareable via a persona-reveal.

Produce ONE concrete, buildable design: (a) the game concept + a SCREEN-BY-SCREEN flow concrete enough to mock up; (b) the mechanic->trait profiling map (which interaction reveals which behavioral trait, grounded in validated paradigms like BART/reaction-time/explore-exploit/delay-discounting where they fit) + the exact pre-treatment features to log; (c) the 5-6 counter-intuitive UI/interaction A/Bs (two arms each, the real outcome measured, why counter-intuitive), with between/within-subject assignment over the single link; (d) the per-player data schema (features table vs sealed outcomes table) + leakage hygiene; (e) the sealed win rule at tiny N; (f) the persona-reveal/shareability hook. End with the single best end-to-end concept + top risks. Be concrete and skeptical; flag any hollow-win or leakage risks. Output text only. Do NOT modify files. Do NOT read ~/.claude/, ~/.agents/, ~/.codex/, .claude/skills/, agents/.
codex
**Concept: “Pocket Port”**

A 3-5 minute mobile game where players run a tiny harbor by moving incoming boats into docks before a tide timer expires. It looks like a light arcade puzzle, but the game profiles behavioral traits from interaction style: how long players inspect before acting, whether they grab risky high-value boats, whether they abandon hard moves, whether they explore hidden docks, how precisely they drag under time pressure, and how they respond to friction, scarcity, delays, and ambiguous affordances.

Players never read scenarios. They mostly tap, drag, hold, and choose routes.

The validation target: can the behavioral-simulation engine predict which UI/interaction treatment will produce better real outcomes for each player or segment, using only pre-treatment interaction features?

---

**Screen Flow**

1. **Landing / One-Link Entry**
   - Title: `Pocket Port`
   - One button: `Play`
   - No visible arm info.
   - Server assigns `participant_id`, session seed, and randomized A/B schedule.
   - URL never contains arm assignment.

2. **Calibration: “Wake The Harbor”**
   - A bell appears in random screen positions.
   - Player taps it 6 times.
   - Measures reaction time, tap precision, hesitation, screen familiarity.
   - No scoring shown.

3. **Practice: “Dock Three Boats”**
   - Player drags 3 boats into matching docks.
   - One dock is obvious, one requires a longer drag path, one appears after a short hold.
   - This establishes baseline drag speed, persistence, exploration, and instruction-free learning.

4. **Round 1: Tide Rush**
   - Boats enter from the left.
   - Each boat has a visible coin value and a sinking timer ring.
   - Player drags boats to docks.
   - Some high-value boats are farther away or require more precise placement.
   - Measures risk-under-time, prioritization, motor control, speed-accuracy tradeoff.

5. **Round 2: Fog Docks**
   - Some docks are partially hidden until the player taps or holds nearby.
   - Hidden docks sometimes offer better outcomes, sometimes not.
   - Measures exploration vs exploitation, curiosity, tolerance for ambiguity, persistence after failed discovery.

6. **Round 3: Chain Harbor**
   - Docks have short cooldowns.
   - Player must decide whether to wait for a good dock, use a worse dock immediately, or reroute.
   - Measures delay discounting, impatience, adaptive planning, frustration recovery.

7. **Round 4: Storm Bonus**
   - Optional risky storm boats appear.
   - They are worth more but can wipe out nearby boat progress if mishandled.
   - Mechanical analogue to BART: repeated risk opportunities with escalating reward and chance of loss.
   - Measures risk appetite, loss sensitivity, stopping threshold.

8. **Round 5: Micro-A/B Battery**
   - The player sees 5-6 short interaction variants embedded naturally into play.
   - Some are within-subject, some between-subject to avoid carryover.
   - Outcomes are behavioral: completion, time, retries, abandoned attempts, coins, optional risk uptake.

9. **Persona Reveal**
   - The game generates a shareable “harbor style” persona:
     - `The Fast Sorter`
     - `The Deep Scout`
     - `The Storm Gambler`
     - `The Patient Optimizer`
     - `The Steady Finisher`
     - `The Last-Second Rescuer`
   - It shows 3 trait bars based on interaction data, not stated preferences.
   - Share card contains no experimental arm, no exact scores, no predictive labels.

---

**Mechanic → Trait Map**

| Mechanic | Behavioral construct | Paradigm anchor | Pre-treatment features to log |
|---|---|---|---|
| Tap calibration | Reaction speed, attention, motor confidence | Reaction-time tasks | median tap latency, latency variance, tap miss distance, first-tap delay |
| Drag boats to docks | Speed-accuracy tradeoff, motor planning | Fitts’ law / psychomotor timing | drag start latency, drag duration, path efficiency, drop error distance, correction count |
| Boat prioritization under timer | Urgency response, prioritization | time-pressure decision tasks | value chosen first, timer remaining at pickup, abandoned boats, order entropy |
| Optional storm boats | Risk appetite, stopping threshold | BART-like risk task | risky boat attempts, risk streak length, bust rate, stop-after-win/loss behavior |
| Hidden/fog docks | Exploration vs exploitation | multi-armed bandit / explore-exploit | exploratory taps, hidden dock discovery rate, repeat use after discovery, time spent probing |
| Dock cooldown wait | Delay discounting, impatience | delay-discounting analogue | wait duration before reroute, premature dock attempts, low-value substitution rate |
| Failed placement recovery | Persistence, frustration tolerance | persistence-after-error tasks | retries after failed drop, quit/idle after error, recovery latency |
| Route choice | Planning depth, ambiguity tolerance | spatial planning | route reversals, long-path acceptance, hesitation before ambiguous path |

Only features recorded before each A/B exposure may be used to predict that exposure’s outcome.

---

**Exact Pre-Treatment Feature Set**

For each player, maintain rolling features computed before each randomized treatment:

```text
participant_id
session_id
device_class
viewport_width
viewport_height
round_index
event_index_cutoff

reaction_median_ms
reaction_iqr_ms
tap_precision_px_median
first_action_latency_ms

drag_start_latency_ms_median
drag_duration_ms_median
drag_path_efficiency_mean
drop_error_px_median
correction_count_mean
failed_drop_recovery_ms_median

risk_attempt_rate
risk_stop_threshold
risk_after_loss_delta
risk_after_win_delta
storm_bust_count_pre

exploration_tap_rate
hidden_area_probe_count
new_dock_discovery_rate
repeat_hidden_dock_use_rate

wait_for_better_dock_rate
premature_attempt_rate
low_value_substitution_rate
abandonment_rate
idle_time_rate

score_pre
completion_rate_pre
rounds_seen_pre
```

Do not include treatment arm, post-treatment score, post-treatment timing, outcome labels, or any derived feature that crosses the exposure boundary.

---

**Micro-A/B Battery**

The battery uses one single public link. The backend randomizes assignments after session creation. Assignment is stored server-side only. At least 3 of 6 are counter-intuitive.

### A/B 1: “Big Reward Glow”

**Manipulation**
- Arm A, obvious: high-value boats pulse with a gold glow.
- Arm B, counter-intuitive: high-value boats are plain; low-time boats pulse instead.

**Outcome**
- Total coins earned in 35 seconds.
- Secondary: boats lost, average timer remaining at pickup.

**Why counter-intuitive**
The obvious product instinct is to highlight value. But under time pressure, highlighting urgency may outperform value because players naturally notice value already, while timer decay is harder to track.

**Assignment**
Within-subject. Each player sees both versions in balanced order across two equivalent mini-rounds.

---

### A/B 2: “Hold To Reveal Hidden Dock”

**Manipulation**
- Arm A, obvious: hidden dock has a shimmer hint.
- Arm B, counter-intuitive: hidden dock has no shimmer, but nearby water subtly resists drag, inviting accidental discovery.

**Outcome**
- Hidden dock discovery rate.
- Use rate after discovery.
- Net score gain from hidden dock.

**Why counter-intuitive**
The obvious cue may attract everyone, producing shallow curiosity but also distracting fast exploiters. The friction cue may be discovered by more interaction-sensitive players and lead to better committed use.

**Assignment**
Between-subject for this dock style, because learning the reveal rule contaminates later exposure.

---

### A/B 3: “Risk Boat Confirmation”

**Manipulation**
- Arm A, obvious: risky storm boat requires a confirmation hold before pickup.
- Arm B, counter-intuitive: risky storm boat is directly draggable but has heavier drag physics.

**Outcome**
- Risk attempts.
- Net storm score.
- Busts.
- Abandon-after-risk.

**Why counter-intuitive**
A confirmation hold seems safer and clearer. But explicit confirmation may over-frame the action as dangerous, suppressing useful risk-taking. Heavier drag may create embodied caution without killing uptake.

**Assignment**
Between-subject.

---

### A/B 4: “Dock Cooldown Display”

**Manipulation**
- Arm A, obvious: exact cooldown number shown: `3...2...1`.
- Arm B, counter-intuitive: cooldown shown as a draining ring only.

**Outcome**
- Successful waits.
- Premature attempts.
- Reroute quality.
- Coins per cooldown window.

**Why counter-intuitive**
Exact numbers seem more informative, but they may induce countdown fixation and idle waiting. A ring may support peripheral timing while keeping players scanning the board.

**Assignment**
Within-subject, alternating dock clusters, counterbalanced by player.

---

### A/B 5: “Rescue Path Preview”

**Manipulation**
- Arm A, obvious: show a dotted recommended route to the best dock.
- Arm B, counter-intuitive: show only invalid zones; no suggested route.

**Outcome**
- Completion time.
- Path efficiency.
- Correction count.
- Successful dock rate.

**Why counter-intuitive**
Recommended routes seem helpful, but they may reduce adaptive pathing and create over-trust when boats/docks move. Showing constraints may let skilled players self-route faster.

**Assignment**
Within-subject on matched boat layouts.

---

### A/B 6: “Loss Feedback”

**Manipulation**
- Arm A, obvious: failed drop flashes red and shakes.
- Arm B, counter-intuitive: failed drop quietly snaps back with a small haptic-style visual pulse.

**Outcome**
- Retry rate.
- Recovery latency.
- Subsequent accuracy.
- Quit/idle after failure.

**Why counter-intuitive**
Strong feedback feels clearer, but it may punish error-prone players and reduce persistence. Quiet feedback may preserve flow and improve recovery.

**Assignment**
Between-subject or first-failure only. Repeated exposure creates learning and emotional carryover.

---

**Randomization Plan**

Single link only.

On session creation:

```text
participant_id = UUID
session_seed = secure random
global_order = Latin-square variant
between_subject_arms:
  hidden_dock_cue: A/B
  risk_confirmation: A/B
  loss_feedback: A/B

within_subject_tests:
  reward_glow: AB or BA
  cooldown_display: AB or BA
  path_preview: AB or BA
```

Rules:
- No arm in URL.
- No client-side visible assignment object.
- Client receives only the next screen config needed to render.
- Server records assignment and outcome separately from feature logs.
- Within-subject variants use matched layouts and counterbalanced order.
- Between-subject variants are used where exposure teaches the mechanic or changes later emotion.

---

**Data Schema**

Two-table firewall.

### Table 1: `interaction_features_pre`

Accessible to model builders.

```text
participant_id
session_id
feature_cutoff_id
microtest_id
round_index
timestamp_cutoff

device_class
viewport_width
viewport_height
input_modality

reaction_median_ms
reaction_iqr_ms
tap_precision_px_median
first_action_latency_ms

drag_start_latency_ms_median
drag_duration_ms_median
drag_path_efficiency_mean
drop_error_px_median
correction_count_mean
failed_drop_recovery_ms_median

risk_attempt_rate_pre
risk_stop_threshold_pre
risk_after_loss_delta_pre
risk_after_win_delta_pre

exploration_tap_rate_pre
hidden_area_probe_count_pre
new_dock_discovery_rate_pre
repeat_hidden_dock_use_rate_pre

wait_for_better_dock_rate_pre
premature_attempt_rate_pre
low_value_substitution_rate_pre
abandonment_rate_pre
idle_time_rate_pre

score_pre
completion_rate_pre
```

No arm. No outcome. No post-treatment events.

### Table 2: `sealed_arm_outcomes`

Not accessible to model builders until predictions are locked.

```text
participant_id
session_id
microtest_id
arm
assignment_type
order_position
layout_seed
timestamp_exposed

primary_outcome_name
primary_outcome_value
secondary_outcome_json

valid_exposure
exclusion_reason
client_version
server_version
```

### Table 3, optional: `locked_predictions`

Written before unsealing.

```text
prediction_id
model_version
participant_id
microtest_id
predicted_winning_arm
predicted_effect_direction
confidence_bucket
created_at
hash_of_feature_snapshot
```

---

**Leakage Hygiene**

- Feature extraction service cannot query `sealed_arm_outcomes`.
- Outcome scoring service cannot mutate `interaction_features_pre`.
- Modelers receive only frozen feature snapshots with `microtest_id`, never arm.
- Predictions are committed before unsealing via timestamped file or DB row hash.
- Arm/outcome table is unsealed only after prediction lock.
- Validation analyst compares locked predictions to outcomes.
- Exclude invalid exposures only by pre-registered rules:
  - app backgrounded during test
  - network failure
  - viewport resize during test
  - fewer than required interactions
  - obvious bot-like event timing
- Never exclude because the outcome “looked weird.”

Primary leakage risk: within-subject tests can leak if features for test B include behavior from test A of the same manipulation. Fix by defining each prediction target separately and allowing only features before that exposure, or by using test A behavior only for predicting unrelated later tests.

---

**Sealed Win Rule At Tiny N**

Because friends-and-family N will be small, avoid overclaiming.

Primary metric:

```text
hit_rate = locked predictions correct / valid predictions
placebo = always-pick-obvious-arm
```

Win condition:

1. At least 25 valid participants.
2. At least 100 valid microtest predictions total.
3. Engine beats always-pick-obvious placebo by at least 12 percentage points.
4. Engine beats placebo on at least 4 of 6 microtests.
5. Engine beats placebo on at least 2 of the counter-intuitive tests.
6. No single microtest contributes more than 35% of the total win margin.
7. All exclusions are applied before unsealing.

Tiny-N interpretation:
- Passing means “worth a larger validation,” not “engine proven.”
- Failing on obvious tests is less important than failing counter-intuitive tests.
- A hollow win is possible if one easy segment dominates. Require per-test reporting.

---

**Persona Reveal / Share Hook**

After the game:

```text
Your Harbor Style: The Deep Scout

You found value other players missed.
You moved slower at first, but your best docks came from exploration.

Traits:
Scout Energy: High
Storm Nerve: Medium
Finish Pressure: High
```

Share card:
- Persona name
- 3 visual trait bars
- “I ran Pocket Port in 3:42”
- Invite link

Do not show:
- A/B arm
- exact behavioral feature values
- “you are risk-seeking”
- model prediction correctness

The hook should make players want to compare styles, not optimize the experiment.

---

**Best End-To-End Concept**

Build `Pocket Port` as a tactile harbor sorting game with boats, docks, timers, hidden areas, and storm-risk bonuses. It is interactive enough to produce real behavioral traces, short enough for friends-and-family, and structured enough to run sealed counter-intuitive UI experiments. The strongest validation comes from predicting which non-obvious interaction design works better for which player, using only pre-treatment behavior.

**Top Risks**

- Hollow win: the engine may beat placebo because one obvious arm is globally bad, not because it models personas. Report per-test and per-segment performance.
- Leakage: within-subject tests can accidentally use prior treatment behavior as a feature. Enforce exposure-level cutoffs.
- Motor skill confound: drag precision may dominate outcomes. Normalize by calibration features and report device class.
- Learning effects: players improve over 3-5 minutes. Counterbalance order and use matched layouts.
- Persona overclaiming: share labels should be playful, not psychological diagnosis.
- Friends-and-family bias: useful for capability testing on a consistent population, not external validity.
tokens used
16,120
**Concept: “Pocket Port”**

A 3-5 minute mobile game where players run a tiny harbor by moving incoming boats into docks before a tide timer expires. It looks like a light arcade puzzle, but the game profiles behavioral traits from interaction style: how long players inspect before acting, whether they grab risky high-value boats, whether they abandon hard moves, whether they explore hidden docks, how precisely they drag under time pressure, and how they respond to friction, scarcity, delays, and ambiguous affordances.

Players never read scenarios. They mostly tap, drag, hold, and choose routes.

The validation target: can the behavioral-simulation engine predict which UI/interaction treatment will produce better real outcomes for each player or segment, using only pre-treatment interaction features?

---

**Screen Flow**

1. **Landing / One-Link Entry**
   - Title: `Pocket Port`
   - One button: `Play`
   - No visible arm info.
   - Server assigns `participant_id`, session seed, and randomized A/B schedule.
   - URL never contains arm assignment.

2. **Calibration: “Wake The Harbor”**
   - A bell appears in random screen positions.
   - Player taps it 6 times.
   - Measures reaction time, tap precision, hesitation, screen familiarity.
   - No scoring shown.

3. **Practice: “Dock Three Boats”**
   - Player drags 3 boats into matching docks.
   - One dock is obvious, one requires a longer drag path, one appears after a short hold.
   - This establishes baseline drag speed, persistence, exploration, and instruction-free learning.

4. **Round 1: Tide Rush**
   - Boats enter from the left.
   - Each boat has a visible coin value and a sinking timer ring.
   - Player drags boats to docks.
   - Some high-value boats are farther away or require more precise placement.
   - Measures risk-under-time, prioritization, motor control, speed-accuracy tradeoff.

5. **Round 2: Fog Docks**
   - Some docks are partially hidden until the player taps or holds nearby.
   - Hidden docks sometimes offer better outcomes, sometimes not.
   - Measures exploration vs exploitation, curiosity, tolerance for ambiguity, persistence after failed discovery.

6. **Round 3: Chain Harbor**
   - Docks have short cooldowns.
   - Player must decide whether to wait for a good dock, use a worse dock immediately, or reroute.
   - Measures delay discounting, impatience, adaptive planning, frustration recovery.

7. **Round 4: Storm Bonus**
   - Optional risky storm boats appear.
   - They are worth more but can wipe out nearby boat progress if mishandled.
   - Mechanical analogue to BART: repeated risk opportunities with escalating reward and chance of loss.
   - Measures risk appetite, loss sensitivity, stopping threshold.

8. **Round 5: Micro-A/B Battery**
   - The player sees 5-6 short interaction variants embedded naturally into play.
   - Some are within-subject, some between-subject to avoid carryover.
   - Outcomes are behavioral: completion, time, retries, abandoned attempts, coins, optional risk uptake.

9. **Persona Reveal**
   - The game generates a shareable “harbor style” persona:
     - `The Fast Sorter`
     - `The Deep Scout`
     - `The Storm Gambler`
     - `The Patient Optimizer`
     - `The Steady Finisher`
     - `The Last-Second Rescuer`
   - It shows 3 trait bars based on interaction data, not stated preferences.
   - Share card contains no experimental arm, no exact scores, no predictive labels.

---

**Mechanic → Trait Map**

| Mechanic | Behavioral construct | Paradigm anchor | Pre-treatment features to log |
|---|---|---|---|
| Tap calibration | Reaction speed, attention, motor confidence | Reaction-time tasks | median tap latency, latency variance, tap miss distance, first-tap delay |
| Drag boats to docks | Speed-accuracy tradeoff, motor planning | Fitts’ law / psychomotor timing | drag start latency, drag duration, path efficiency, drop error distance, correction count |
| Boat prioritization under timer | Urgency response, prioritization | time-pressure decision tasks | value chosen first, timer remaining at pickup, abandoned boats, order entropy |
| Optional storm boats | Risk appetite, stopping threshold | BART-like risk task | risky boat attempts, risk streak length, bust rate, stop-after-win/loss behavior |
| Hidden/fog docks | Exploration vs exploitation | multi-armed bandit / explore-exploit | exploratory taps, hidden dock discovery rate, repeat use after discovery, time spent probing |
| Dock cooldown wait | Delay discounting, impatience | delay-discounting analogue | wait duration before reroute, premature dock attempts, low-value substitution rate |
| Failed placement recovery | Persistence, frustration tolerance | persistence-after-error tasks | retries after failed drop, quit/idle after error, recovery latency |
| Route choice | Planning depth, ambiguity tolerance | spatial planning | route reversals, long-path acceptance, hesitation before ambiguous path |

Only features recorded before each A/B exposure may be used to predict that exposure’s outcome.

---

**Exact Pre-Treatment Feature Set**

For each player, maintain rolling features computed before each randomized treatment:

```text
participant_id
session_id
device_class
viewport_width
viewport_height
round_index
event_index_cutoff

reaction_median_ms
reaction_iqr_ms
tap_precision_px_median
first_action_latency_ms

drag_start_latency_ms_median
drag_duration_ms_median
drag_path_efficiency_mean
drop_error_px_median
correction_count_mean
failed_drop_recovery_ms_median

risk_attempt_rate
risk_stop_threshold
risk_after_loss_delta
risk_after_win_delta
storm_bust_count_pre

exploration_tap_rate
hidden_area_probe_count
new_dock_discovery_rate
repeat_hidden_dock_use_rate

wait_for_better_dock_rate
premature_attempt_rate
low_value_substitution_rate
abandonment_rate
idle_time_rate

score_pre
completion_rate_pre
rounds_seen_pre
```

Do not include treatment arm, post-treatment score, post-treatment timing, outcome labels, or any derived feature that crosses the exposure boundary.

---

**Micro-A/B Battery**

The battery uses one single public link. The backend randomizes assignments after session creation. Assignment is stored server-side only. At least 3 of 6 are counter-intuitive.

### A/B 1: “Big Reward Glow”

**Manipulation**
- Arm A, obvious: high-value boats pulse with a gold glow.
- Arm B, counter-intuitive: high-value boats are plain; low-time boats pulse instead.

**Outcome**
- Total coins earned in 35 seconds.
- Secondary: boats lost, average timer remaining at pickup.

**Why counter-intuitive**
The obvious product instinct is to highlight value. But under time pressure, highlighting urgency may outperform value because players naturally notice value already, while timer decay is harder to track.

**Assignment**
Within-subject. Each player sees both versions in balanced order across two equivalent mini-rounds.

---

### A/B 2: “Hold To Reveal Hidden Dock”

**Manipulation**
- Arm A, obvious: hidden dock has a shimmer hint.
- Arm B, counter-intuitive: hidden dock has no shimmer, but nearby water subtly resists drag, inviting accidental discovery.

**Outcome**
- Hidden dock discovery rate.
- Use rate after discovery.
- Net score gain from hidden dock.

**Why counter-intuitive**
The obvious cue may attract everyone, producing shallow curiosity but also distracting fast exploiters. The friction cue may be discovered by more interaction-sensitive players and lead to better committed use.

**Assignment**
Between-subject for this dock style, because learning the reveal rule contaminates later exposure.

---

### A/B 3: “Risk Boat Confirmation”

**Manipulation**
- Arm A, obvious: risky storm boat requires a confirmation hold before pickup.
- Arm B, counter-intuitive: risky storm boat is directly draggable but has heavier drag physics.

**Outcome**
- Risk attempts.
- Net storm score.
- Busts.
- Abandon-after-risk.

**Why counter-intuitive**
A confirmation hold seems safer and clearer. But explicit confirmation may over-frame the action as dangerous, suppressing useful risk-taking. Heavier drag may create embodied caution without killing uptake.

**Assignment**
Between-subject.

---

### A/B 4: “Dock Cooldown Display”

**Manipulation**
- Arm A, obvious: exact cooldown number shown: `3...2...1`.
- Arm B, counter-intuitive: cooldown shown as a draining ring only.

**Outcome**
- Successful waits.
- Premature attempts.
- Reroute quality.
- Coins per cooldown window.

**Why counter-intuitive**
Exact numbers seem more informative, but they may induce countdown fixation and idle waiting. A ring may support peripheral timing while keeping players scanning the board.

**Assignment**
Within-subject, alternating dock clusters, counterbalanced by player.

---

### A/B 5: “Rescue Path Preview”

**Manipulation**
- Arm A, obvious: show a dotted recommended route to the best dock.
- Arm B, counter-intuitive: show only invalid zones; no suggested route.

**Outcome**
- Completion time.
- Path efficiency.
- Correction count.
- Successful dock rate.

**Why counter-intuitive**
Recommended routes seem helpful, but they may reduce adaptive pathing and create over-trust when boats/docks move. Showing constraints may let skilled players self-route faster.

**Assignment**
Within-subject on matched boat layouts.

---

### A/B 6: “Loss Feedback”

**Manipulation**
- Arm A, obvious: failed drop flashes red and shakes.
- Arm B, counter-intuitive: failed drop quietly snaps back with a small haptic-style visual pulse.

**Outcome**
- Retry rate.
- Recovery latency.
- Subsequent accuracy.
- Quit/idle after failure.

**Why counter-intuitive**
Strong feedback feels clearer, but it may punish error-prone players and reduce persistence. Quiet feedback may preserve flow and improve recovery.

**Assignment**
Between-subject or first-failure only. Repeated exposure creates learning and emotional carryover.

---

**Randomization Plan**

Single link only.

On session creation:

```text
participant_id = UUID
session_seed = secure random
global_order = Latin-square variant
between_subject_arms:
  hidden_dock_cue: A/B
  risk_confirmation: A/B
  loss_feedback: A/B

within_subject_tests:
  reward_glow: AB or BA
  cooldown_display: AB or BA
  path_preview: AB or BA
```

Rules:
- No arm in URL.
- No client-side visible assignment object.
- Client receives only the next screen config needed to render.
- Server records assignment and outcome separately from feature logs.
- Within-subject variants use matched layouts and counterbalanced order.
- Between-subject variants are used where exposure teaches the mechanic or changes later emotion.

---

**Data Schema**

Two-table firewall.

### Table 1: `interaction_features_pre`

Accessible to model builders.

```text
participant_id
session_id
feature_cutoff_id
microtest_id
round_index
timestamp_cutoff

device_class
viewport_width
viewport_height
input_modality

reaction_median_ms
reaction_iqr_ms
tap_precision_px_median
first_action_latency_ms

drag_start_latency_ms_median
drag_duration_ms_median
drag_path_efficiency_mean
drop_error_px_median
correction_count_mean
failed_drop_recovery_ms_median

risk_attempt_rate_pre
risk_stop_threshold_pre
risk_after_loss_delta_pre
risk_after_win_delta_pre

exploration_tap_rate_pre
hidden_area_probe_count_pre
new_dock_discovery_rate_pre
repeat_hidden_dock_use_rate_pre

wait_for_better_dock_rate_pre
premature_attempt_rate_pre
low_value_substitution_rate_pre
abandonment_rate_pre
idle_time_rate_pre

score_pre
completion_rate_pre
```

No arm. No outcome. No post-treatment events.

### Table 2: `sealed_arm_outcomes`

Not accessible to model builders until predictions are locked.

```text
participant_id
session_id
microtest_id
arm
assignment_type
order_position
layout_seed
timestamp_exposed

primary_outcome_name
primary_outcome_value
secondary_outcome_json

valid_exposure
exclusion_reason
client_version
server_version
```

### Table 3, optional: `locked_predictions`

Written before unsealing.

```text
prediction_id
model_version
participant_id
microtest_id
predicted_winning_arm
predicted_effect_direction
confidence_bucket
created_at
hash_of_feature_snapshot
```

---

**Leakage Hygiene**

- Feature extraction service cannot query `sealed_arm_outcomes`.
- Outcome scoring service cannot mutate `interaction_features_pre`.
- Modelers receive only frozen feature snapshots with `microtest_id`, never arm.
- Predictions are committed before unsealing via timestamped file or DB row hash.
- Arm/outcome table is unsealed only after prediction lock.
- Validation analyst compares locked predictions to outcomes.
- Exclude invalid exposures only by pre-registered rules:
  - app backgrounded during test
  - network failure
  - viewport resize during test
  - fewer than required interactions
  - obvious bot-like event timing
- Never exclude because the outcome “looked weird.”

Primary leakage risk: within-subject tests can leak if features for test B include behavior from test A of the same manipulation. Fix by defining each prediction target separately and allowing only features before that exposure, or by using test A behavior only for predicting unrelated later tests.

---

**Sealed Win Rule At Tiny N**

Because friends-and-family N will be small, avoid overclaiming.

Primary metric:

```text
hit_rate = locked predictions correct / valid predictions
placebo = always-pick-obvious-arm
```

Win condition:

1. At least 25 valid participants.
2. At least 100 valid microtest predictions total.
3. Engine beats always-pick-obvious placebo by at least 12 percentage points.
4. Engine beats placebo on at least 4 of 6 microtests.
5. Engine beats placebo on at least 2 of the counter-intuitive tests.
6. No single microtest contributes more than 35% of the total win margin.
7. All exclusions are applied before unsealing.

Tiny-N interpretation:
- Passing means “worth a larger validation,” not “engine proven.”
- Failing on obvious tests is less important than failing counter-intuitive tests.
- A hollow win is possible if one easy segment dominates. Require per-test reporting.

---

**Persona Reveal / Share Hook**

After the game:

```text
Your Harbor Style: The Deep Scout

You found value other players missed.
You moved slower at first, but your best docks came from exploration.

Traits:
Scout Energy: High
Storm Nerve: Medium
Finish Pressure: High
```

Share card:
- Persona name
- 3 visual trait bars
- “I ran Pocket Port in 3:42”
- Invite link

Do not show:
- A/B arm
- exact behavioral feature values
- “you are risk-seeking”
- model prediction correctness

The hook should make players want to compare styles, not optimize the experiment.

---

**Best End-To-End Concept**

Build `Pocket Port` as a tactile harbor sorting game with boats, docks, timers, hidden areas, and storm-risk bonuses. It is interactive enough to produce real behavioral traces, short enough for friends-and-family, and structured enough to run sealed counter-intuitive UI experiments. The strongest validation comes from predicting which non-obvious interaction design works better for which player, using only pre-treatment behavior.

**Top Risks**

- Hollow win: the engine may beat placebo because one obvious arm is globally bad, not because it models personas. Report per-test and per-segment performance.
- Leakage: within-subject tests can accidentally use prior treatment behavior as a feature. Enforce exposure-level cutoffs.
- Motor skill confound: drag precision may dominate outcomes. Normalize by calibration features and report device class.
- Learning effects: players improve over 3-5 minutes. Counterbalance order and use matched layouts.
- Persona overclaiming: share labels should be playful, not psychological diagnosis.
- Friends-and-family bias: useful for capability testing on a consistent population, not external validity.
