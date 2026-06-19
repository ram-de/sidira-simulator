# Friends-&-Family validation game — synthesized design spec (#342)

Two councils (Claude: experiment-design / gamification / persona-fit / validity; Codex/gpt-5.5)
designed a friends-&-family app/GAME that secretly IS a blinded, pre-registered test of the
simulation engine. This is the de-duplicated consensus, ready to build. Source lenses + the Codex
panel in this folder; grounding precedents are the Hillstrom panel (`hillstrom_archive.py`,
`hillstrom_panel_loader.py`) — the F&F game is a third panel of the SAME shape.

## The one-line goal (don't drift from it)
Given a persona pack built from real players, can the engine predict the DIRECTION of those same
players' A/B behavior on hypotheses where the obvious guess is wrong? Consistent population → a valid
CAPABILITY test even though F&F is biased (representativeness is a deployment concern, not a capability one).

## Concept — an economic-decision game with real stakes
A ~5-min mobile-web game (Codex's "Split The Loot" / Claude's "Stoop Sale" — same skeleton): the
player runs a series of real-consequence economic choices for a **real probabilistic payout**
(e.g. "1 in 20 players' final allocation is paid out at 20×" → real money/charity, low operational
cost, genuine stakes so behavior isn't stated-preference theater). Framed as a fun social game —
**never** as "research / study / experiment" (kills social-desirability). Payoff hook that drives
F&F to finish AND forward: a shareable **"Trader Type" persona-card reveal** at the very end (after
all outcomes — revealing it earlier would contaminate behavior).

## Structure (three phases, in order)
1. **Profiling rooms** (identical for everyone, PRE-treatment) → reveals traits through real choices,
   no Likert feel. These produce the persona-pack features. **No A/B here.**
2. **The micro-A/B battery** (the engine test) — 5–6 counter-intuitive micro-A/Bs.
3. **Persona-card reveal** (after all outcomes) → the forwarding loop.

### Phase 1 — profiling through play (mechanic → trait)
| room | choice | trait revealed (the feature) |
|---|---|---|
| Risk box | safe +10 / 70%·+18 / 35%·+45 under a 12s timer | risk appetite, EV-sensitivity, deliberation latency |
| Info-cost | pay coins to reveal hints vs choose blind | attention/effort, info valuation, overconfidence |
| Deal room | take now vs wait/counter for more | present-bias, patience, deal sensitivity |
| Trust game | how many tripled coins to send a stranger | trust, reciprocity, social skepticism |
| Ambiguity | known 50% odds vs equal-EV "mystery" | ambiguity aversion, skepticism of opaque systems |
Passive (never shown, can't be gamed): decision latency, re-tap/scrub counts, options-inspected,
re-read rate. Plus 3 tap-only demographics post-game on the "Seller Card" (age band, locale, tenure).

### Phase 2 — the micro-A/B battery (5–6 counter-intuitive items; the engine's exam)
Each item is a change where the **obvious / "more-is-better" answer loses or ties** (so a correct
prediction means skill, not the thumb). Candidates (pick ≥5, ≥half counter-intuitive, label each
obvious-prior BEFORE sealing):
- **Scarcity/deadline backfire** (reactance): aggressive countdown + "only 3 left" vs calm — urgency
  *depresses* completion in a F&F "I know I'm being sold to" context. *(experiment lens: run this one
  BETWEEN-subject — you can't un-ring the urgency bell — via the one-link server-randomized arm.)*
- **Choice overload**: 3 options vs 24 — more choice *lowers* the rate of actually choosing.
- **Urgency/default**: pre-checked "safe" default + "most people lock in" vs neutral — default
  *stickiness* beats prospect-theory framing.
- **Prosocial impact-explanation backfire** (Codex): a polished "your impact compounds" blurb *reduces*
  giving vs a sparse screen (reads as persuasion → skepticism).
- **Effort justification**: a tiny bit of earned effort *raises* downstream commitment vs one-tap.
- **Ambiguity/"too-good" deal**: a suspiciously high offer with fine print *lowers* uptake.
**Run the non-headline items WITHIN-subject (counterbalanced order, spaced through the game)** — ~4×
the power of between-subject at this N, and it yields K paired comparisons. The engine predicts each
item's population direction; we score the **hit-rate across the K**, never one fragile A/B.

## Arm assignment & link hygiene (the experiment lens's hard correction)
**Do NOT use "send link A = control, link B = treatment."** Whoever routes friends to links IS the
assignment mechanism → fatal selection confound. Instead:
- **One link** (or per-recipient tokens that do NOT encode the arm). The **server randomizes** the
  between-subject headline arm + the within-subject counterbalancing on first load. Block-randomize
  (permuted blocks) so a 26/14 split can't happen by chance at small N.
- Arm never in the URL (else the blind is gone). Sticky per person; single-use tokens; log
  forwarding (`is_forwarded`, referrer) — primary analysis = original-token users only.
- **Profile features captured BEFORE the arm fires**, identically for both arms (else they're
  post-treatment and leak).

## Data schema — two physically separate tables (the leakage firewall)
Mirror Hillstrom exactly: the feature table is the ONLY thing `run_pipeline` sees; arm+outcome live
in a separate sealed record. (`hillstrom_archive.py:432` — "the outcome must never enter the
clustering or the pack would leak the answer key.")
- **Table A `player_features`** (→ `run_pipeline`, PRE-treatment only): `player_id` (key only) +
  ~10 typed features in 2–3 groups — demographics (age_band, locale, device, tenure_days), the 5
  decision-style scores (decision_speed, deal_sensitivity, present_bias, effort_tolerance,
  reactance), and 3–4 gameplay-revealed (warmup_decision_ms, warmup_options_inspected,
  warmup_skip_rate, warmup_reread_rate). Every field typed to an adapter `mtype`
  (count/score/ratio/flag/categorical/tenure_days). **No arm. No outcome. No post-treatment field.**
- **Table B `player_outcomes`** (the SEALED answer key, never fed to the pipeline): `player_id`, `arm`,
  `task_id`, binary `outcome`, timestamps, `attention_passed`.

## Pack build (reuses everything we just shipped)
`run_pipeline(df=TableA, cfg=friends_family.yaml, require_llm=True)` (cfg modeled on `streamly.yaml`;
**k_range [2,4]**, ≥10 players/cluster, `holdout_frac 0.0`, trust per-cluster Jaccard over the global
mean). `--require-llm` is REQUIRED — it generates `behavioral_seeds` (the PR we just merged) and the
enriched descriptions; a fallback pack scores ~0 for reasons unrelated to the engine. Commit the
derived pack (statistics only — privacy-clean) as `friends_family_panel_v1.json`; clone
`hillstrom_panel_loader.py`. **Score at the PLAYER level** via the `assignments` map
(player_id→persona_id) so you get N comparisons from k personas, not just k.

## Sealed win rule (commit BEFORE outcomes; role-separated)
- Unit of evidence = **direction hit-rate across K≥5 micro-A/Bs**, not any single A/B (each is
  underpowered at N=30–100). Binomial reality: **5/5 → p=0.03**; **4/4 → p=0.06 = proof-of-life**;
  with K<5 you can't beat chance even with a perfect score → design K=5–6.
- **GO** iff: hit-rate clears the binomial bar (clean/one-miss sweep at K≥5) **AND** the engine beats
  the **"always-pick-obvious" placebo** **AND** is right on ≥1 item where the obvious prior is wrong.
- **Seal in one git commit before any outcome is computed:** the persona pack itself, per-item
  predicted direction + confidence, the obvious-prior label (set by a non-author), the primary binary
  outcome metric per item, the placebo's predictions, the win + stopping rules.
- **Role separation:** the founder who runs the engine must NOT run the outcome computation; the
  scorer verifies the sealed hash before scoring. Any post-seal edit to personas/predictions/metrics
  **burns the run.** The named risk: *"the failure mode to watch is wanting it to pass."*
- A **GO licenses the paid PoC / design-partner stage — NOT deployment accuracy, NOT generalization
  beyond F&F.** Proof-of-life, not confirmation.

## Build stack
Small mobile-first SPA (stack-agnostic), server-side randomization + a tiny DB for the two tables +
participant resume + the probabilistic payout. Log per beat: choice, latency, re-tap/scrub, dwell,
fine-print-opened, arm, referrer. Then: export Table A → parquet → `run_pipeline` → pack → loader →
**blinded** engine run (predict each item's direction, sealed) → score vs Table B.

## The three data-killers (flag explicitly)
1. **Two hand-routed links / arm in URL** → one link, server-randomized, arm never in URL.
2. **Persona reveal or any "study" wording leaking** → reveal only after all outcomes; in-character framing.
3. **Profile/outcome contamination or post-hoc tuning** → leakage firewall (two tables) + sealed,
   role-separated run; adversarial leakage audit of feature↔outcome pairs before sealing.

See [[directional-sim-campaign-standing]]. This is the unpaid, owned, fastest path to a first
real-outcome capability read — run it alongside the paid PoC (POC_RUNBOOK.md) + design-partner outreach.
