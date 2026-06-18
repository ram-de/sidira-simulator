# Proof-of-concept: self-run A/B benchmark to manufacture a real outcome anchor (#342)

**Purpose.** The campaign exhausted public-data proxies; the value is gated on the directional/
screening claim, validatable only against *real* outcomes. This PoC manufactures real outcomes
cheaply by running our own A/B tests on a panel and building the persona pack from **that same
panel** (internally-consistent population — see the capability-vs-deployment distinction in
[[directional-sim-campaign-standing]]). It is a **GO/NO-GO gate** for a larger powered self-run
benchmark — not the benchmark itself.

## The capability question (clean, population-agnostic)
> Given a persona pack built from population X, can the engine predict population X's behavior on a
> change whose outcome is **not** trivially guessable?

Any consistent population works — the panel does NOT need to match a future customer's audience
(that's a deployment concern, not a capability concern). So a cheap panel is valid here.

## Design principles (locked from the campaign)
1. **Internally consistent population** — recruit a panel, **build the pack from that panel's
   profiling data**, run the A/B on that same panel. Personas and ground truth are the same people.
2. **Non-obvious outcomes ONLY.** "Simple to *run*" = good; "simple/obvious *outcome*" = hollow.
   The sim is already good at intuitive cases and fails on counter-intuitive ones — so a win only
   counts on changes where the naive "more/obvious wins" prior is wrong or 50/50. Use documented
   large-effect counter-intuitive paradigms (keeps N small).
3. **Real behavior, not stated preference** — the participant must DO something (choose/complete),
   incentive-compatible where possible.
4. **Each A/B is powered; the *number* of A/Bs is small.** ~100–150/arm gives a trustworthy winner
   per test; 2–3 tests = a proof-of-life, not a powered confirmation.
5. **Blinded + pre-registered** — winner stripped from the sim's stimulus; win rule sealed first.

## Components

### 1. Panel + profiling
- Recruit ~600–900 participants total (across the 2–3 tests), between-subjects (each sees ONE arm).
- **Profiling micro-survey (5–10 items)** captures per-participant features to build the pack:
  decision style (impulsive↔deliberate), price/deal sensitivity, patience/present-bias,
  attention/effort tolerance, skepticism, plus basic demographics. (You need *features*, not just
  outcomes — the pack pipeline requires them.)
- Strong **attention checks** (cheap panels satisfice/bot — gate aggressively).

### 2. The A/B tasks (2–3 NON-OBVIOUS designs; pick from large-effect counter-intuitive paradigms)
- **T1 — deadline/scarcity backfire:** a redeemable reward with a SHORT vs LONG deadline → measure
  redemption action. (Shorter often wins — counter-intuitive: long deadline → procrastination.)
- **T2 — choice overload:** 6 vs 24 options to pick from → measure completion / made-a-choice rate.
  (Fewer often wins — counter-intuitive.)
- **T3 — urgency/countdown reactance:** identical offer WITH vs WITHOUT a countdown timer →
  measure accept/click. (No-countdown can win for skeptical/autonomy-valuing users.)
Each is a short self-contained web task with a single binary behavioral outcome. Wording neutral,
no leak. (Build on a behavioral-task platform or a thin custom page with an A/B split.)

### 3. Power / sample / cost
- Target effect ≥ ~15pp (typical of these paradigms) → ~100–150/arm, ~300/test.
- Cost: cheap-panel ~$0.50–3/participant + profiling → roughly **$300–1,000/test** → **~$1–3k for the
  PoC (2–3 tests)**. (Verify per-platform; see the company shortlist doc.)

### 4. Sim run
- Map profiling survey → persona-pack features → build the pack (note: a real engineering step —
  the pipeline expects a feature schema; the survey must populate it).
- Run the engine **blinded** (winner stripped) on each A/B → predicted direction.

## Pre-registered win rule (seal BEFORE any result)
- **Primary:** direction accuracy across the 2–3 tests, vs the naive baseline (always-pick-the-
  obvious/richer option) on these specifically-counter-intuitive cases.
- **GO (scale to powered 10–20-test benchmark, ~$10–15k):** sim beats the naive prior on the
  counter-intuitive cases (e.g. ≥2/3 with the obvious-prior wrong) AND the manufactured-data loop
  produced clean per-test winners.
- **NO-GO:** sim at/ below the naive prior (≤1/3) — early, cheap confirmation the capability isn't
  there; do not spend the $10–15k. (3 independent counter-intuitive calls: chance ≈ 1.5/3; 3/3 ≈
  p=0.125 suggestive; 0/3 confirms failure.)
- Also run the **placebo "always-pick-simpler" control** and confirm the sim isn't merely a thumb.

## Honest limits
- 2–3 tests is a proof-of-LIFE, not a powered confirmation — it gates the bigger benchmark.
- Panel-task behavior ≠ real-stakes behavior (demand characteristics) — a win here is "predicts
  panel behavior"; extend to real in-context behavior later.
- This validates the *capability* on a consistent population; deployment to a specific customer
  still needs that customer's audience (the design-partner path remains the primary GTM route).

## Sequencing
Run this PoC **in parallel with design-partner outreach** (DESIGN_PARTNER_OUTREACH.md). The PoC is
the fast/owned hedge; a design partner's history is the free/representative primary. Whichever
yields a clean read first informs the GO/PIVOT/KILL standing in [[directional-sim-campaign-standing]].
