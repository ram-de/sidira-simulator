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
session id: 019edd4e-ba6b-7800-97ae-b7c5dcc6b6ad
--------
user
You are a panel of frontier-AI + product-research leaders. Design a FRIENDS-AND-FAMILY app/GAME that secretly IS an experiment to test a behavioral-simulation engine. The founder sends TWO links — one CONTROL experience, one TREATMENT (an A/B). The app must do two woven things: (1) PROFILE each player (capture per-user features to build a "persona pack" — demographics + behavioral traits like decision-style, patience/present-bias, deal-sensitivity, skepticism, attention/effort, ideally via REVEALED gameplay behavior not a survey), and (2) run the A/B to produce a REAL behavioral OUTCOME on a hypothesis. We then build a persona pack from the SAME players and test whether the engine predicts their real A/B behavior — a valid CAPABILITY test on a consistent population (F&F bias is fine; representativeness is a deployment concern, not a capability one).

HARD constraints from our validation campaign:
- The hypothesis MUST be NON-OBVIOUS / counter-intuitive (the obvious / "more-is-better" answer is wrong or 50/50). The engine already nails obvious cases and FAILS counter-intuitive ones, so predicting an obvious A/B proves nothing.
- REAL behavioral outcome (a consequential choice/action), not a stated preference.
- Blinded (engine never sees the winner) + pre-registered (seal prediction + win rule + the persona pack BEFORE the outcome is computed).
- F&F = tiny N (maybe 30–100), biased, social-desirability (they know the founder) — design to mitigate.
- Profile data must map to a buildable persona pack (clusterable per-user feature table) + per-persona identity pools.

Produce a single, concrete, buildable design: (a) the GAME concept (3–7 min, mobile-first, shareable, with a real stake so behavior is genuine); (b) how profiling is woven into gameplay (mechanic → trait map, revealed not stated); (c) the specific NON-OBVIOUS hypothesis + where the A/B lives in the game + the real outcome measured; (d) clean arm assignment via the two links (avoid selection confounds, handle forwarding/repeat visits); (e) what to log per player (pre-treatment features vs outcome, no leakage); (f) the pre-registered win rule for tiny N + the binomial reality of how many micro-A/Bs you need; (g) the simplest tech stack to build it. End with the single best end-to-end concept and the top risks. Be concrete and skeptical; flag anything that would be a hollow win. Output text only. Do NOT modify files. Do NOT read ~/.claude/, ~/.agents/, ~/.codex/, .claude/skills/, agents/.
codex
**Best Concept: “Split The Loot”**

A 3–7 minute mobile game where each player joins a “founder’s friends challenge” to unlock a real shared donation or prize pot. The game looks like a lightweight social puzzle: make a few timed tradeoff decisions, negotiate with anonymous “teammates,” and decide how much of a limited bonus to keep, donate, or allocate to other players.

Secretly, it does two things:

1. Builds a persona pack from revealed behavior.
2. Runs a blinded A/B test on a counter-intuitive behavioral hypothesis using a real consequential choice.

The game is not framed as research. It is framed as:

> “Help us test a quick social decision game. At the end, your choices affect a real donation pool and a small raffle.”

No survey-first feel. No “what kind of person are you?” language.

---

**Game Concept**

Title: **Split The Loot**

Length: 5 minutes.

Format: mobile-first web app.

Real stake:

- Each player receives a small virtual endowment, e.g. `$1.00`.
- At the end, one randomly selected player’s choices are paid out for real:
  - Some amount to the player as a gift card / Venmo / raffle boost.
  - Some amount to a real charity pot.
  - Some amount affects another future player’s starting bonus.
- To avoid operational overhead, use probabilistic payment:
  - “1 in 20 players will have their final allocation paid out at 20x.”
  - This creates real incentive while keeping cost controlled.
- Everyone also sees that their final choice changes a visible group total, so non-selected players still experience consequence.

Core loop:

1. Player gets a small starting pot.
2. They complete 4–6 fast “loot room” decisions.
3. Each room reveals a behavioral trait through action, timing, retries, information search, risk-taking, and allocation.
4. Near the end, they hit the actual A/B treatment.
5. Final outcome is a real choice: whether to claim a personal bonus, give it to the group/charity, or unlock a benefit for later players.

The surface game feels like a party/social choice game, not a survey.

---

**Profiling Woven Into Gameplay**

The profiling should happen before treatment exposure. Everything after treatment is excluded from persona construction except the outcome label.

Each player produces a feature row like:

```text
player_id
arm
device/session metadata
pre_treatment_behavior_features...
outcome_choice
outcome_timestamp
```

The persona pack is built only from pre-treatment features.

**Mechanic 1: Timed Risk Room**

Player sees three locked boxes:

- Safe: guaranteed +10 coins
- Medium: 70% chance +18, 30% chance +0
- Wild: 35% chance +45, 65% chance +0

They choose under a visible 12-second timer.

Trait map:

- Risk tolerance: safe vs medium vs wild
- Deliberation time: latency before choice
- Loss reaction: next-room risk shift after bad outcome
- Impulsivity: very fast high-variance picks
- Probability sensitivity: whether choices respond to expected value

**Mechanic 2: Info Cost Room**

Player can reveal hints before choosing a box.

Example:

- Reveal hint 1: costs 2 coins
- Reveal hint 2: costs 4 coins
- Skip hints and choose now

Trait map:

- Attention / effort: number of hints opened
- Information valuation: coins spent on certainty
- Overconfidence: skips info on ambiguous choice
- Patience: delay accepted for better decision
- Cognitive style: speed vs accuracy

**Mechanic 3: Deal Room**

Player gets a limited-time offer:

> “Trade 20 coins now for a 50% chance at 55 coins later.”

Timer: 8 seconds.

Then a second offer:

> “Wait 20 seconds to improve this offer by 10 coins.”

Trait map:

- Present bias: accepts immediate smaller reward
- Patience: waits for improved offer
- Deal sensitivity: response to bonus size
- Urgency sensitivity: behavior under countdown
- Opportunity-cost sensitivity: abandon/wait behavior

**Mechanic 4: Trust Room**

Player is paired with an anonymous previous/future player.

They choose how many coins to send. Sent coins are tripled. The other player may send some back. Use pre-generated “partner responses” for consistency.

Trait map:

- Trust / cooperation: amount sent
- Reciprocity: response after partner generosity/stinginess
- Fairness preference: equalizing behavior
- Social skepticism: minimal send despite upside
- Punishment tendency: willingness to reduce total pot to punish unfair partner

**Mechanic 5: Ambiguity Room**

Player chooses between:

- Known odds: 50% chance at +24
- Unknown odds: “Mystery box based on today’s player pool”

The mystery box has the same expected value but ambiguous framing.

Trait map:

- Ambiguity aversion
- Novelty seeking
- Skepticism toward opaque systems
- Comfort with unknown mechanisms

**Mechanic 6: Optional Cosmetic / Identity Choice**

Before treatment, the player picks an avatar badge or “crew role” based on game behavior, not demographics.

Example identity pools:

- “Fast Splitters”: low latency, low info cost
- “Careful Openers”: high hint use, slower choices
- “Deal Hunters”: high sensitivity to offer improvements
- “Trust Builders”: high cooperation
- “Fence Sitters”: low variance, middle allocation
- “Skeptical Optimizers”: low trust, high info use

This creates persona identity pools without asking people to self-label.

Optional lightweight demographics can be collected at the very end, after the outcome:

- age band
- country/state
- student / working / founder / investor / other
- familiarity with founder/product

These should not be needed for the primary engine test, but they help persona realism.

---

**The Non-Obvious Hypothesis**

Hypothesis:

> Adding a small “impact explanation” before a prosocial choice will reduce prosocial action compared with a sparse choice screen, because it makes the decision feel more like persuasion/manipulation and triggers skepticism among F&F participants.

This is deliberately counter-intuitive.

The obvious product intuition is:

> “More explanation about impact should increase giving.”

The testable counterclaim is:

> “For a founder’s friends-and-family audience, a polished explanation decreases real contribution because it raises social-desirability suspicion and reactance.”

This is a good capability test because many simulation engines will overpredict “more information → more generosity.”

---

**Where The A/B Lives**

At the final room, every player has earned a real bonus allocation.

They see one of two screens.

**Control: Sparse Allocation Screen**

> “You earned 100 bonus coins.  
> Choose what happens to them.”

Options:

- Keep for your raffle/gift-card chance
- Add to the shared donation pot
- Give to the next player as a starting boost
- Split manually

No persuasion copy. No charity story. No moral framing. Just the choice.

**Treatment: Impact Explanation Screen**

Same options, but above them:

> “Your choice has real impact. Coins added to the shared pot help fund the group donation. Coins passed forward give the next player a stronger start. Most people underestimate how much these small choices compound across the player chain.”

Include a small visual showing the donation pot growing.

Everything else identical.

---

**Real Outcome Measured**

Primary outcome:

> Did the player allocate at least 50% of their final bonus away from themselves?

Binary:

```text
prosocial_majority = donated_or_forwarded_coins >= 0.5 * final_bonus
```

Secondary outcomes:

- continuous percent allocated away from self
- chose charity vs next-player boost
- kept everything
- time to final decision
- changed allocation after opening manual split

The primary outcome must be binary because tiny-N inference is already fragile. Do not let yourself “find” a win in secondary metrics.

---

**Clean Arm Assignment With Two Links**

The founder sends two links, but the links should not directly mean control/treatment if avoidable.

Bad:

```text
/game?arm=control
/game?arm=treatment
```

This creates selection confounds if the founder sends one to closer friends or one gets forwarded more.

Better:

- Link A and Link B are invitation pools.
- Each link maps to a pre-generated invite batch.
- Within each batch, assignment is deterministic but hidden by invite token.

Example:

```text
/s/blue-river
/s/silver-key
```

Each route issues or resolves an anonymous `participant_id`.

Assignment rule:

```text
arm = hash(participant_id + experiment_salt) % 2
```

But the user requested two links, one control and one treatment. If the campaign requires that literally, then mitigate as follows:

- Founder alternates links mechanically in the contact list before sending.
- Pre-register assignment list before send.
- Do not allow the founder to hand-pick which friend gets which arm.
- Use identical preview metadata, titles, thumbnails, and copy.
- Do not label the URLs control/treatment.
- Track source link separately from assigned arm.
- For forwarded visits, preserve original arm but log `forward_likely = true`.

Handling repeat visits:

- First visit creates `participant_id` in server DB and browser localStorage.
- If same browser returns, keep same arm.
- If same email/phone magic code is used, keep same arm.
- If no login, use a completion code and soft fingerprinting:
  - user agent
  - coarse IP hash
  - timezone
  - screen size
- Mark likely duplicates but do not delete unless clearly identical.

Forwarding:

- Every session logs:
  - invite token
  - referrer if available
  - parent participant if shared from in-app share link
  - timestamp
- Forwarded users are allowed, but pre-register whether they are included.
- Best rule:
  - Primary analysis includes only original invite-token users.
  - Secondary analysis includes forwarded users with cluster-robust caution.
- If F&F N is tiny, forwarded users may be useful for power, but they muddy assignment.

---

**What To Log Per Player**

Do not leak treatment or outcome into the persona pack.

**Identity/session**

```text
participant_id
invite_token
source_link_id
assigned_arm
created_at
completed_at
user_agent
device_type
timezone
coarse_geo
likely_duplicate_id
is_forwarded
```

**Pre-treatment behavioral features**

```text
total_pre_treatment_time
median_decision_latency
fast_click_rate
timeout_count
hint_open_count
hint_coin_spend
risk_choice_safe_count
risk_choice_medium_count
risk_choice_wild_count
risk_after_loss_delta
waited_for_better_offer
seconds_waited_total
accepted_immediate_offer
deal_accept_threshold
trust_send_percent
reciprocity_after_generous_partner
reciprocity_after_stingy_partner
punishment_choice
ambiguity_choice_rate
manual_review_count
allocation_practice_pattern
attention_check_behavioral_pass
```

Avoid survey-style “Are you skeptical?” Instead infer skepticism from:

- low trust sends
- high info reveal rate
- avoidance of opaque mystery boxes
- longer latency on claims
- lower response to urgency framing
- higher tendency to inspect terms/details

**Treatment exposure**

```text
treatment_screen_rendered_at
arm
copy_variant_id
visual_variant_id
```

Keep this separate from persona features.

**Outcome**

```text
final_bonus_available
coins_kept
coins_to_charity
coins_to_next_player
prosocial_majority
final_decision_latency
manual_split_used
changed_final_allocation
payment_selected_for_realization
realized_payout_amount
```

**Post-outcome optional demographics**

```text
age_band
country_or_state
relationship_to_founder
occupation_bucket
has_startup_context
charity_affinity_optional
```

These can be used for descriptive analysis or persona enrichment, but the cleanest engine test should run without them unless collected before prediction sealing.

---

**Persona Pack Construction**

Build a per-user feature table, then cluster into 4–6 persona groups.

Example personas:

1. **Fast Maximizers**
   - low latency
   - low hint usage
   - high EV choices
   - low patience for delayed boosts

2. **Careful Verifiers**
   - high hint spend
   - slower decisions
   - ambiguity averse
   - skeptical of opaque offers

3. **Generous Reciprocators**
   - high trust sends
   - high reciprocity
   - fair splits
   - sensitive to social proof

4. **Deal-Driven Optimizers**
   - waits when payoff improves
   - takes favorable risks
   - high deal sensitivity
   - low charity unless framed as leverage

5. **Guarded Controllers**
   - keeps control
   - low trust
   - low ambiguity tolerance
   - high manual allocation edits

Each persona identity pool should include:

```text
persona_id
persona_name
behavioral_summary
feature_centroid
representative_player_ids
demographic_distribution_if_available
pre_treatment_event_traces
```

The simulation engine receives:

- persona definitions
- anonymized persona counts
- behavioral features
- A/B descriptions
- outcome definition
- prediction task

The engine must not receive observed outcome rates.

---

**Pre-Registration**

Before computing outcomes, seal:

1. The hypothesis:
   - Treatment impact explanation will reduce `prosocial_majority` relative to control.

2. The primary outcome:
   - `prosocial_majority = coins_to_charity + coins_to_next_player >= 50% final_bonus`

3. The inclusion rules:
   - completed game
   - reached final allocation screen
   - not clear duplicate
   - original invite only for primary analysis

4. The feature cutoff:
   - persona pack uses only events timestamped before treatment screen render.

5. The engine input:
   - exact persona pack file hash
   - exact prompt/spec sent to engine
   - exact A/B copy
   - exact prediction format

6. The engine prediction:
   - sealed before outcome computation
   - e.g. commit hash, timestamped file, or signed digest

7. The win rule.

---

**Win Rule For Tiny N**

Do not pretend one tiny A/B gives definitive proof.

For a single micro-A/B with 30–100 players, use a directional win rule:

> The engine wins this round if it predicts the correct direction of the treatment effect and the observed absolute difference is at least 8 percentage points.

Example:

```text
control prosocial_majority = 52%
treatment prosocial_majority = 38%
observed effect = -14 pp
engine predicted treatment lower
round = engine directional win
```

But this is not statistically strong at tiny N.

With N=60 total, even a 20-point difference is noisy.

Approximate reality:

- N=30: useful only as smoke test
- N=60: directional signal, high variance
- N=100: still underpowered for modest effects
- To validate capability, you need many micro-A/Bs

Pre-register an aggregate benchmark:

> Run 12–20 independent counter-intuitive micro-A/Bs. The engine must predict the correct direction on at least 75% of eligible tests, with no access to outcomes.

Binomial intuition:

- If direction is random, chance of 9+ correct out of 12 is about 7%.
- 10+ out of 12 is about 2%.
- 15+ out of 20 is about 2%.
- 16+ out of 20 is below 1%.

So a credible campaign might be:

```text
Minimum: 12 micro-A/Bs, pass if >=9 correct
Stronger: 20 micro-A/Bs, pass if >=15 correct
```

Single-test “wins” are demos, not validation.

Also pre-register a “hollow win” exclusion:

- If both arms differ by less than 5 percentage points, the test is inconclusive.
- If fewer than 25 valid completions per arm, the test is inconclusive.
- If the manipulation was not actually seen/rendered, exclude.
- If the hypothesis is obvious after the fact, mark it as non-qualifying.

---

**Simplest Tech Stack**

Use the fastest boring stack.

Frontend:

- Next.js app router
- Mobile-first React
- Inline styles or simple CSS modules
- No auth wall
- LocalStorage for return visits
- Vercel or Amplify deploy

Backend:

- FastAPI or Next.js API routes
- Postgres via Supabase/Neon
- Server-side assignment and event logging
- One append-only `events` table
- One `participants` table
- One `experiments` table

Tables:

```text
participants
- participant_id
- invite_token
- source_link_id
- assigned_arm
- created_at
- completed_at
- duplicate_status

events
- event_id
- participant_id
- event_type
- event_payload_json
- client_timestamp
- server_timestamp
- pre_treatment_boolean

outcomes
- participant_id
- assigned_arm
- final_bonus
- coins_kept
- coins_to_charity
- coins_to_next_player
- prosocial_majority
- computed_at

experiment_seals
- experiment_id
- persona_pack_hash
- prediction_hash
- preregistration_hash
- sealed_at
```

Analysis:

- Python notebook or script
- Pandas
- scipy/statsmodels
- deterministic export to CSV/JSON
- hash persona pack before outcomes are computed

Do not overbuild dashboards. A CSV export, sealed JSON, and one analysis script are enough.

---

**Why This Is The Best End-To-End Concept**

“Split The Loot” is strong because the profiling and outcome are behaviorally aligned. You are not asking people what they value; you are watching them make tradeoffs involving time, risk, trust, skepticism, effort, and money-like stakes.

The A/B is also genuinely non-obvious. Many people would expect richer impact explanation to increase generosity. In a friends-and-family founder context, the opposite is plausible because polished persuasion can trigger skepticism, impression-management discomfort, or “I am being tested” reactance.

Most importantly, the same people generate both:

- the persona pack used by the simulator
- the real A/B outcome used for validation

That makes this a capability test, not a representativeness test.

---

**Top Risks**

1. **The stake is too fake**
   - If players do not believe choices matter, the outcome is hollow.
   - Fix: real probabilistic payout, visible donation receipt, clear rules.

2. **Founder relationship contaminates behavior**
   - Friends may act generous to look good.
   - Fix: anonymous play, no leaderboard by name, sparse framing, no founder-visible individual outcomes.

3. **The treatment becomes too obvious**
   - If the impact copy screams “please donate,” players know what is being tested.
   - Fix: make it plausible product UX, not moral pressure.

4. **The A/B effect is too small**
   - Tiny N cannot resolve small effects.
   - Fix: choose high-reactance copy, binary outcome, and run many micro-A/Bs.

5. **Persona leakage**
   - If post-treatment behavior enters the persona pack, the engine can indirectly see the answer.
   - Fix: hard timestamp cutoff before treatment render.

6. **Selection confound from two links**
   - If the founder sends treatment to one social group and control to another, the result is invalid.
   - Fix: pre-generated assignment list or deterministic randomization hidden behind neutral links.

7. **Obvious hypothesis masquerading as validation**
   - “Bigger reward increases clicks” proves almost nothing.
   - This design avoids that by testing whether more persuasive impact explanation can backfire.

The single best build is **Split The Loot with the impact-explanation backfire A/B**, using real probabilistic stakes, pre-treatment behavioral profiling, sealed persona packs, and a directional benchmark across many small counter-intuitive tests.
tokens used
18,496
**Best Concept: “Split The Loot”**

A 3–7 minute mobile game where each player joins a “founder’s friends challenge” to unlock a real shared donation or prize pot. The game looks like a lightweight social puzzle: make a few timed tradeoff decisions, negotiate with anonymous “teammates,” and decide how much of a limited bonus to keep, donate, or allocate to other players.

Secretly, it does two things:

1. Builds a persona pack from revealed behavior.
2. Runs a blinded A/B test on a counter-intuitive behavioral hypothesis using a real consequential choice.

The game is not framed as research. It is framed as:

> “Help us test a quick social decision game. At the end, your choices affect a real donation pool and a small raffle.”

No survey-first feel. No “what kind of person are you?” language.

---

**Game Concept**

Title: **Split The Loot**

Length: 5 minutes.

Format: mobile-first web app.

Real stake:

- Each player receives a small virtual endowment, e.g. `$1.00`.
- At the end, one randomly selected player’s choices are paid out for real:
  - Some amount to the player as a gift card / Venmo / raffle boost.
  - Some amount to a real charity pot.
  - Some amount affects another future player’s starting bonus.
- To avoid operational overhead, use probabilistic payment:
  - “1 in 20 players will have their final allocation paid out at 20x.”
  - This creates real incentive while keeping cost controlled.
- Everyone also sees that their final choice changes a visible group total, so non-selected players still experience consequence.

Core loop:

1. Player gets a small starting pot.
2. They complete 4–6 fast “loot room” decisions.
3. Each room reveals a behavioral trait through action, timing, retries, information search, risk-taking, and allocation.
4. Near the end, they hit the actual A/B treatment.
5. Final outcome is a real choice: whether to claim a personal bonus, give it to the group/charity, or unlock a benefit for later players.

The surface game feels like a party/social choice game, not a survey.

---

**Profiling Woven Into Gameplay**

The profiling should happen before treatment exposure. Everything after treatment is excluded from persona construction except the outcome label.

Each player produces a feature row like:

```text
player_id
arm
device/session metadata
pre_treatment_behavior_features...
outcome_choice
outcome_timestamp
```

The persona pack is built only from pre-treatment features.

**Mechanic 1: Timed Risk Room**

Player sees three locked boxes:

- Safe: guaranteed +10 coins
- Medium: 70% chance +18, 30% chance +0
- Wild: 35% chance +45, 65% chance +0

They choose under a visible 12-second timer.

Trait map:

- Risk tolerance: safe vs medium vs wild
- Deliberation time: latency before choice
- Loss reaction: next-room risk shift after bad outcome
- Impulsivity: very fast high-variance picks
- Probability sensitivity: whether choices respond to expected value

**Mechanic 2: Info Cost Room**

Player can reveal hints before choosing a box.

Example:

- Reveal hint 1: costs 2 coins
- Reveal hint 2: costs 4 coins
- Skip hints and choose now

Trait map:

- Attention / effort: number of hints opened
- Information valuation: coins spent on certainty
- Overconfidence: skips info on ambiguous choice
- Patience: delay accepted for better decision
- Cognitive style: speed vs accuracy

**Mechanic 3: Deal Room**

Player gets a limited-time offer:

> “Trade 20 coins now for a 50% chance at 55 coins later.”

Timer: 8 seconds.

Then a second offer:

> “Wait 20 seconds to improve this offer by 10 coins.”

Trait map:

- Present bias: accepts immediate smaller reward
- Patience: waits for improved offer
- Deal sensitivity: response to bonus size
- Urgency sensitivity: behavior under countdown
- Opportunity-cost sensitivity: abandon/wait behavior

**Mechanic 4: Trust Room**

Player is paired with an anonymous previous/future player.

They choose how many coins to send. Sent coins are tripled. The other player may send some back. Use pre-generated “partner responses” for consistency.

Trait map:

- Trust / cooperation: amount sent
- Reciprocity: response after partner generosity/stinginess
- Fairness preference: equalizing behavior
- Social skepticism: minimal send despite upside
- Punishment tendency: willingness to reduce total pot to punish unfair partner

**Mechanic 5: Ambiguity Room**

Player chooses between:

- Known odds: 50% chance at +24
- Unknown odds: “Mystery box based on today’s player pool”

The mystery box has the same expected value but ambiguous framing.

Trait map:

- Ambiguity aversion
- Novelty seeking
- Skepticism toward opaque systems
- Comfort with unknown mechanisms

**Mechanic 6: Optional Cosmetic / Identity Choice**

Before treatment, the player picks an avatar badge or “crew role” based on game behavior, not demographics.

Example identity pools:

- “Fast Splitters”: low latency, low info cost
- “Careful Openers”: high hint use, slower choices
- “Deal Hunters”: high sensitivity to offer improvements
- “Trust Builders”: high cooperation
- “Fence Sitters”: low variance, middle allocation
- “Skeptical Optimizers”: low trust, high info use

This creates persona identity pools without asking people to self-label.

Optional lightweight demographics can be collected at the very end, after the outcome:

- age band
- country/state
- student / working / founder / investor / other
- familiarity with founder/product

These should not be needed for the primary engine test, but they help persona realism.

---

**The Non-Obvious Hypothesis**

Hypothesis:

> Adding a small “impact explanation” before a prosocial choice will reduce prosocial action compared with a sparse choice screen, because it makes the decision feel more like persuasion/manipulation and triggers skepticism among F&F participants.

This is deliberately counter-intuitive.

The obvious product intuition is:

> “More explanation about impact should increase giving.”

The testable counterclaim is:

> “For a founder’s friends-and-family audience, a polished explanation decreases real contribution because it raises social-desirability suspicion and reactance.”

This is a good capability test because many simulation engines will overpredict “more information → more generosity.”

---

**Where The A/B Lives**

At the final room, every player has earned a real bonus allocation.

They see one of two screens.

**Control: Sparse Allocation Screen**

> “You earned 100 bonus coins.  
> Choose what happens to them.”

Options:

- Keep for your raffle/gift-card chance
- Add to the shared donation pot
- Give to the next player as a starting boost
- Split manually

No persuasion copy. No charity story. No moral framing. Just the choice.

**Treatment: Impact Explanation Screen**

Same options, but above them:

> “Your choice has real impact. Coins added to the shared pot help fund the group donation. Coins passed forward give the next player a stronger start. Most people underestimate how much these small choices compound across the player chain.”

Include a small visual showing the donation pot growing.

Everything else identical.

---

**Real Outcome Measured**

Primary outcome:

> Did the player allocate at least 50% of their final bonus away from themselves?

Binary:

```text
prosocial_majority = donated_or_forwarded_coins >= 0.5 * final_bonus
```

Secondary outcomes:

- continuous percent allocated away from self
- chose charity vs next-player boost
- kept everything
- time to final decision
- changed allocation after opening manual split

The primary outcome must be binary because tiny-N inference is already fragile. Do not let yourself “find” a win in secondary metrics.

---

**Clean Arm Assignment With Two Links**

The founder sends two links, but the links should not directly mean control/treatment if avoidable.

Bad:

```text
/game?arm=control
/game?arm=treatment
```

This creates selection confounds if the founder sends one to closer friends or one gets forwarded more.

Better:

- Link A and Link B are invitation pools.
- Each link maps to a pre-generated invite batch.
- Within each batch, assignment is deterministic but hidden by invite token.

Example:

```text
/s/blue-river
/s/silver-key
```

Each route issues or resolves an anonymous `participant_id`.

Assignment rule:

```text
arm = hash(participant_id + experiment_salt) % 2
```

But the user requested two links, one control and one treatment. If the campaign requires that literally, then mitigate as follows:

- Founder alternates links mechanically in the contact list before sending.
- Pre-register assignment list before send.
- Do not allow the founder to hand-pick which friend gets which arm.
- Use identical preview metadata, titles, thumbnails, and copy.
- Do not label the URLs control/treatment.
- Track source link separately from assigned arm.
- For forwarded visits, preserve original arm but log `forward_likely = true`.

Handling repeat visits:

- First visit creates `participant_id` in server DB and browser localStorage.
- If same browser returns, keep same arm.
- If same email/phone magic code is used, keep same arm.
- If no login, use a completion code and soft fingerprinting:
  - user agent
  - coarse IP hash
  - timezone
  - screen size
- Mark likely duplicates but do not delete unless clearly identical.

Forwarding:

- Every session logs:
  - invite token
  - referrer if available
  - parent participant if shared from in-app share link
  - timestamp
- Forwarded users are allowed, but pre-register whether they are included.
- Best rule:
  - Primary analysis includes only original invite-token users.
  - Secondary analysis includes forwarded users with cluster-robust caution.
- If F&F N is tiny, forwarded users may be useful for power, but they muddy assignment.

---

**What To Log Per Player**

Do not leak treatment or outcome into the persona pack.

**Identity/session**

```text
participant_id
invite_token
source_link_id
assigned_arm
created_at
completed_at
user_agent
device_type
timezone
coarse_geo
likely_duplicate_id
is_forwarded
```

**Pre-treatment behavioral features**

```text
total_pre_treatment_time
median_decision_latency
fast_click_rate
timeout_count
hint_open_count
hint_coin_spend
risk_choice_safe_count
risk_choice_medium_count
risk_choice_wild_count
risk_after_loss_delta
waited_for_better_offer
seconds_waited_total
accepted_immediate_offer
deal_accept_threshold
trust_send_percent
reciprocity_after_generous_partner
reciprocity_after_stingy_partner
punishment_choice
ambiguity_choice_rate
manual_review_count
allocation_practice_pattern
attention_check_behavioral_pass
```

Avoid survey-style “Are you skeptical?” Instead infer skepticism from:

- low trust sends
- high info reveal rate
- avoidance of opaque mystery boxes
- longer latency on claims
- lower response to urgency framing
- higher tendency to inspect terms/details

**Treatment exposure**

```text
treatment_screen_rendered_at
arm
copy_variant_id
visual_variant_id
```

Keep this separate from persona features.

**Outcome**

```text
final_bonus_available
coins_kept
coins_to_charity
coins_to_next_player
prosocial_majority
final_decision_latency
manual_split_used
changed_final_allocation
payment_selected_for_realization
realized_payout_amount
```

**Post-outcome optional demographics**

```text
age_band
country_or_state
relationship_to_founder
occupation_bucket
has_startup_context
charity_affinity_optional
```

These can be used for descriptive analysis or persona enrichment, but the cleanest engine test should run without them unless collected before prediction sealing.

---

**Persona Pack Construction**

Build a per-user feature table, then cluster into 4–6 persona groups.

Example personas:

1. **Fast Maximizers**
   - low latency
   - low hint usage
   - high EV choices
   - low patience for delayed boosts

2. **Careful Verifiers**
   - high hint spend
   - slower decisions
   - ambiguity averse
   - skeptical of opaque offers

3. **Generous Reciprocators**
   - high trust sends
   - high reciprocity
   - fair splits
   - sensitive to social proof

4. **Deal-Driven Optimizers**
   - waits when payoff improves
   - takes favorable risks
   - high deal sensitivity
   - low charity unless framed as leverage

5. **Guarded Controllers**
   - keeps control
   - low trust
   - low ambiguity tolerance
   - high manual allocation edits

Each persona identity pool should include:

```text
persona_id
persona_name
behavioral_summary
feature_centroid
representative_player_ids
demographic_distribution_if_available
pre_treatment_event_traces
```

The simulation engine receives:

- persona definitions
- anonymized persona counts
- behavioral features
- A/B descriptions
- outcome definition
- prediction task

The engine must not receive observed outcome rates.

---

**Pre-Registration**

Before computing outcomes, seal:

1. The hypothesis:
   - Treatment impact explanation will reduce `prosocial_majority` relative to control.

2. The primary outcome:
   - `prosocial_majority = coins_to_charity + coins_to_next_player >= 50% final_bonus`

3. The inclusion rules:
   - completed game
   - reached final allocation screen
   - not clear duplicate
   - original invite only for primary analysis

4. The feature cutoff:
   - persona pack uses only events timestamped before treatment screen render.

5. The engine input:
   - exact persona pack file hash
   - exact prompt/spec sent to engine
   - exact A/B copy
   - exact prediction format

6. The engine prediction:
   - sealed before outcome computation
   - e.g. commit hash, timestamped file, or signed digest

7. The win rule.

---

**Win Rule For Tiny N**

Do not pretend one tiny A/B gives definitive proof.

For a single micro-A/B with 30–100 players, use a directional win rule:

> The engine wins this round if it predicts the correct direction of the treatment effect and the observed absolute difference is at least 8 percentage points.

Example:

```text
control prosocial_majority = 52%
treatment prosocial_majority = 38%
observed effect = -14 pp
engine predicted treatment lower
round = engine directional win
```

But this is not statistically strong at tiny N.

With N=60 total, even a 20-point difference is noisy.

Approximate reality:

- N=30: useful only as smoke test
- N=60: directional signal, high variance
- N=100: still underpowered for modest effects
- To validate capability, you need many micro-A/Bs

Pre-register an aggregate benchmark:

> Run 12–20 independent counter-intuitive micro-A/Bs. The engine must predict the correct direction on at least 75% of eligible tests, with no access to outcomes.

Binomial intuition:

- If direction is random, chance of 9+ correct out of 12 is about 7%.
- 10+ out of 12 is about 2%.
- 15+ out of 20 is about 2%.
- 16+ out of 20 is below 1%.

So a credible campaign might be:

```text
Minimum: 12 micro-A/Bs, pass if >=9 correct
Stronger: 20 micro-A/Bs, pass if >=15 correct
```

Single-test “wins” are demos, not validation.

Also pre-register a “hollow win” exclusion:

- If both arms differ by less than 5 percentage points, the test is inconclusive.
- If fewer than 25 valid completions per arm, the test is inconclusive.
- If the manipulation was not actually seen/rendered, exclude.
- If the hypothesis is obvious after the fact, mark it as non-qualifying.

---

**Simplest Tech Stack**

Use the fastest boring stack.

Frontend:

- Next.js app router
- Mobile-first React
- Inline styles or simple CSS modules
- No auth wall
- LocalStorage for return visits
- Vercel or Amplify deploy

Backend:

- FastAPI or Next.js API routes
- Postgres via Supabase/Neon
- Server-side assignment and event logging
- One append-only `events` table
- One `participants` table
- One `experiments` table

Tables:

```text
participants
- participant_id
- invite_token
- source_link_id
- assigned_arm
- created_at
- completed_at
- duplicate_status

events
- event_id
- participant_id
- event_type
- event_payload_json
- client_timestamp
- server_timestamp
- pre_treatment_boolean

outcomes
- participant_id
- assigned_arm
- final_bonus
- coins_kept
- coins_to_charity
- coins_to_next_player
- prosocial_majority
- computed_at

experiment_seals
- experiment_id
- persona_pack_hash
- prediction_hash
- preregistration_hash
- sealed_at
```

Analysis:

- Python notebook or script
- Pandas
- scipy/statsmodels
- deterministic export to CSV/JSON
- hash persona pack before outcomes are computed

Do not overbuild dashboards. A CSV export, sealed JSON, and one analysis script are enough.

---

**Why This Is The Best End-To-End Concept**

“Split The Loot” is strong because the profiling and outcome are behaviorally aligned. You are not asking people what they value; you are watching them make tradeoffs involving time, risk, trust, skepticism, effort, and money-like stakes.

The A/B is also genuinely non-obvious. Many people would expect richer impact explanation to increase generosity. In a friends-and-family founder context, the opposite is plausible because polished persuasion can trigger skepticism, impression-management discomfort, or “I am being tested” reactance.

Most importantly, the same people generate both:

- the persona pack used by the simulator
- the real A/B outcome used for validation

That makes this a capability test, not a representativeness test.

---

**Top Risks**

1. **The stake is too fake**
   - If players do not believe choices matter, the outcome is hollow.
   - Fix: real probabilistic payout, visible donation receipt, clear rules.

2. **Founder relationship contaminates behavior**
   - Friends may act generous to look good.
   - Fix: anonymous play, no leaderboard by name, sparse framing, no founder-visible individual outcomes.

3. **The treatment becomes too obvious**
   - If the impact copy screams “please donate,” players know what is being tested.
   - Fix: make it plausible product UX, not moral pressure.

4. **The A/B effect is too small**
   - Tiny N cannot resolve small effects.
   - Fix: choose high-reactance copy, binary outcome, and run many micro-A/Bs.

5. **Persona leakage**
   - If post-treatment behavior enters the persona pack, the engine can indirectly see the answer.
   - Fix: hard timestamp cutoff before treatment render.

6. **Selection confound from two links**
   - If the founder sends treatment to one social group and control to another, the result is invalid.
   - Fix: pre-generated assignment list or deterministic randomization hidden behind neutral links.

7. **Obvious hypothesis masquerading as validation**
   - “Bigger reward increases clicks” proves almost nothing.
   - This design avoids that by testing whether more persuasive impact explanation can backfire.

The single best build is **Split The Loot with the impact-explanation backfire A/B**, using real probabilistic stakes, pre-treatment behavioral profiling, sealed persona packs, and a directional benchmark across many small counter-intuitive tests.
