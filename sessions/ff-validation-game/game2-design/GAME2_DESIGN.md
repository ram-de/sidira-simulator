# Game #2 — "Pocket Port" — synthesized design (DESIGN ONLY, pre-build)

Two councils (Claude: interaction-design / behavioral-measurement / A/B-design / data-fit+validity; Codex)
designed a MORE INTERACTIVE, LESS VERBAL companion to "Split The Loot." Strong convergence on a tactile
arcade of validated behavioral paradigms; this is the de-duplicated synthesis. **Nothing built yet —
awaiting founder sign-off on this mockup + plan.**

## Concept
**Pocket Port** — a ~4-min mobile game where you run a tiny harbor: **drag incoming boats into docks**
before a tide timer runs out. It looks like a cute arcade puzzle; it's actually a behavioral profiler +
a counter-intuitive UI A/B battery. Players **tap, drag, hold** — they never read scenarios. A real
(probabilistic) coin payout threads through so behavior is genuine. Ends on a shareable "harbor style"
persona card. Why it beats a disjoint set of mini-games: one coherent world, drag is universally
intuitive, and the validated paradigms (BART/reaction/explore-exploit/delay-discounting) embed naturally
as "rounds."

## Why this complements game #1 (not a duplicate)
- Different profiling modality: **motor/timing/risk behavior** vs. game #1's stated economic choices.
- A/Bs are **UI/interaction changes** (feedback, progress, urgency, option-count, error UX) — *the literal
  shape of real product changes the engine must predict in production* → a positive here is stronger
  external validity. Two greens on orthogonal modalities is much harder to explain as one shared artifact.

## Screen flow (mockup)
```
 ┌───────────────┐   ┌───────────────┐   ┌─────────────────────┐
 │   POCKET PORT │   │  tap the bell │   │  TIDE RUSH      ⏱▒▒░ │
 │      ⚓        │   │      🔔  →     │   │ 🚤①→   ┌──┐ ┌──┐    │
 │   [  PLAY  ]  │   │   🔔     →     │   │  🚤②→  │D1│ │D2│    │
 │               │   │      🔔  →     │   │ 🚤③→   └──┘ └──┘    │
 │ one link;     │   │ (6 taps;       │   │ drag boats → docks  │
 │ arm assigned  │   │  reaction +    │   │ before they sink ◴  │
 │ server-side   │   │  precision)    │   │ high-value = farther│
 └───────────────┘   └───────────────┘   └─────────────────────┘
   0. Landing          2. Calibration       4. Round 1 (motor + risk-under-time)

 ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────────┐
 │ FOG DOCKS      ░▒▓   │  │ STORM BONUS    ⚡    │  │  YOUR HARBOR STYLE│
 │  🚤  ┌──┐ ░░░?░░     │  │  🚤+++  ┌──┐         │  │   "The Deep Scout"│
 │      │D1│ ░hidden?   │  │ risky storm boat:   │  │   🧭              │
 │ tap/hold to reveal   │  │ worth more, can wipe │  │ risk   ▓▓▓░░      │
 │ hidden docks; some   │  │ nearby progress.     │  │ explore▓▓▓▓▒      │
 │ better, some not     │  │ pump risk → bank/bust│  │ patience ▓▓░░░    │
 │ (explore vs exploit) │  │ (BART analogue)      │  │ [Send a friend in]│
 └─────────────────────┘  └─────────────────────┘  └──────────────────┘
   5. Round 2 (explore)      7. Round 4 (BART risk)    9. Persona reveal + share
```
(Round 3 "Chain Harbor" — docks have cooldowns; wait-for-better vs use-worse-now = delay-discounting —
sits between 5 and 7. Onboarding is **demonstration-by-doing**: each round the game "ghost-plays" the
first action, then hands the thumb back — no tutorial text.)

## Profiling — traits revealed through interaction (PRE-treatment → Table A)
Every feature is a within-player aggregate over ≥5–8 trials, computed from **arm-identical screens before
any A/B fires**, device-normalized (use CVs/slopes/ratios, not raw ms, + a motor-baseline subtract).

| Round / mechanic | Trait (validated paradigm) | Example logged features |
|---|---|---|
| Bell calibration | reaction speed, attention, motor floor | `reaction_median_ms`, `reaction_iqr_ms`, `tap_precision_px`, `first_action_latency_ms` |
| Drag boats→docks | speed–accuracy, motor planning (Fitts) | `drag_path_efficiency`, `drop_error_px`, `correction_count`, `overshoot_rate` |
| Boat prioritization under timer | urgency response, prioritization | `value_chosen_first`, `timer_left_at_pickup`, `abandon_rate`, `order_entropy` |
| Storm boats | risk appetite, loss-chasing (BART) | `risk_attempt_rate`, `risk_stop_threshold`, `risk_after_loss_delta`, `bust_rate` |
| Fog docks | exploration vs exploitation (bandit) | `explore_tap_rate`, `hidden_discovery_rate`, `repeat_after_discovery`, `probe_time` |
| Dock cooldown | patience / delay-discounting | `wait_before_reroute`, `premature_attempt_rate`, `low_value_substitution_rate` |
| Failed-drop recovery | persistence / frustration tolerance | `retries_after_fail`, `recovery_latency`, `idle_after_error_flag` |
| Device covariates (nuisance) | confound control | `input_modality`, `viewport`, `refresh_rate_probe` |
→ ~15 typed features (count/score/ratio/flag/categorical) → `run_pipeline` clusters into k=2–3 personas.
**Each A/B is pre-paired with its theory-linked moderator** (impulsivity↔friction/urgency; risk+explore↔
feedback/uncertainty; patience↔delay; grit↔feedback-removal) so the engine has the covariate to predict
who-responds-how.

## The counter-intuitive A/B battery (UI/interaction changes; ≥5, ≥half counter-intuitive)
Single link; **server-side randomized; arm never in URL.** Headline between-subject; rest within-subject
(counterbalanced) for power. Score hit-rate vs an "always-pick-the-obvious/richer arm" placebo.

| # | manipulation (1 variable) | obvious prior | counter-intuitive hypothesis | real outcome |
|---|---|---|---|---|
| 1 (headline, between) | **progress tracker** on the round sequence: shown vs hidden | progress bar → more completion | tracker reframes a toy as a *chore/test* → MORE dropout | completion of the sequence |
| 2 | **big-reward glow**: high-value boats pulse gold vs plain | glow → players chase value, more coins | glow distracts from the *timer* → worse prioritization, fewer docked | coins / boats docked |
| 3 | **countdown urgency** on a risk choice: timer+haptic vs self-paced | urgency → more bold/risky action | urgency → anxiety → *safe* choice / freeze; self-paced takes more risk | risky-option uptake |
| 4 | **option count** at a dock-choice: many docks vs 3 (+"more") | more options → more engagement | choice overload → *lower* commit rate, slower | committed-and-advanced |
| 5 | **error feedback**: harsh (flash+buzz+penalty) vs soft on a misdrop | harsh → fewer later errors | harsh → over-caution → more *omissions*, slower, fewer coins | post-error omission + total coins |
| 6 | **flashy CTA** on the share/invite: big animated vs calm | bigger → more clicks | flashy reads "ad/desperate" → *fewer* clicks | invite-click / share-open |
All six are real product decisions. One focal arm per player (don't independently randomize all 6 →
64-cell blowup kills power at F&F N); hold the rest at control. Counterbalance round order server-side.

## Data architecture, validity, win rule (same rigor as game #1)
- **Two-table leakage firewall:** `player_features` (Table A, pre-treatment, the ONLY thing the pipeline
  sees) vs sealed `player_outcomes` (arm, task_id, outcome). `run_pipeline` has no credential for outcomes.
- **Interaction-specific leak (the #1 silent risk):** a feature must NOT be the *same physical measurement*
  as an A/B outcome (e.g. don't let "completion"/"risk-taking" be both a feature AND outcome #1/#3). Freeze
  the feature set + a feature↔outcome conflict matrix; an **independent auditor** (not the pack-builder)
  signs off before sealing. Also: features captured strictly before `arm_assigned_at`, from arm-identical
  screens; balance/residualize on `input_modality` (touch users are systematically slower).
- **Small-N reality:** interaction features are noisier per-trial than survey items → aggregate over trials,
  cap feature count, select k by bootstrap stability. Expect *fuzzier* clusters than game #1 at equal N →
  budget ~50+ players or pre-commit to k=2.
- **Sealed, role-separated, blinded** validation; pre-register K + feature set + conflict matrix + win rule.
  **GO iff:** ≥5 resolved A/Bs, engine ≥4/5 (or 5/6) correct, **beats the placebo on the counter-intuitive
  cells**, ≥1 correctly-called against-the-prior reversal, and no outcome↔feature leakage. Proof-of-LIFE,
  not a powered confirmation (report the exact binomial p).

## Top risks (flagged)
1. **Feature↔outcome leakage** (completion/risk are both candidate features AND A/B outcomes) — seal + audit first.
2. **Device/modality confound** on every timing feature — balance arms on modality or residualize.
3. **Per-machine independent randomization** → 64-cell blowup — randomize ONE focal arm per player.
4. **Order/fatigue + house-money** across rounds — counterbalance order, log running-pot as covariate.
5. **Reveal/labels before play** would prime behavior — all verbal content strictly after the last round.
6. **Haptics vary by device** — gate/stratify any haptics-dependent arm.

## Build posture (if approved)
Reuse game #1's stack + the two-table firewall + server-side randomization + the harness verbatim; this is
new front-end (canvas/drag interactions) + the same backend pattern. MVP fallback: ship the **Storm Bonus
(BART)** round alone — single most trait-dense paradigm, carries ~3 of the A/Bs.
