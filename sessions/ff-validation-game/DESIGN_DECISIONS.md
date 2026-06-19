# F&F validation game — design decisions (ADR)

A running log of every material design choice + its rationale, so the reasoning is recoverable.
Companion to `ff-app-design/FF_GAME_DESIGN.md` (the spec) and the session `context.md`. Decisions
are grouped; each has the **choice**, the **why**, and **alternatives rejected**.

## A. Purpose & framing
- **A1. The game IS a blinded, pre-registered test of the simulation engine.** Why: the #342 campaign
  exhausted public-data proxies; value is gated on a real-outcome validation, and a game is the
  cheapest/owned way to manufacture real outcomes. Rejected: keep chasing public datasets (exhausted);
  wait for a design partner (slower; this runs in parallel).
- **A2. It is a CAPABILITY test on a *consistent* population, not a deployment test.** Build the persona
  pack from the SAME players whose A/B behavior we score. Why: makes F&F bias irrelevant to the
  question "given a pack of these players, does the engine predict them." A GO licenses the paid PoC /
  design-partner stage — NOT deployment accuracy, NOT generalization beyond the pool.
- **A3. Hard rule: never mix pools.** Personas are built from the exact pool tested. A US+India F&F mix
  is fine (one consistent pool); building from one group and testing another is the one thing that
  invalidates it.

## B. Validation methodology
- **B1. Hypotheses must be NON-OBVIOUS / counter-intuitive.** Why: the engine already nails obvious
  cases and fails counter-intuitive ones (the "more-is-better" prior); a correct prediction on an
  obvious A/B is hollow. The independent audit (#442) confirmed 4/5 items genuinely counter-intuitive
  (default_stickiness is obvious → excluded from the "≥1 counter-intuitive win" credit).
- **B2. Score hit-rate across K≥5 micro-A/Bs vs the "always-pick-obvious" placebo — not one A/B.** Why:
  each A/B is underpowered at N=30–100; the binomial reality is 5/5→p=0.03, 4/4→p=0.06 (proof-of-life).
  The placebo comparison defends against the "engine is just a pro-simpler thumb" artifact.
- **B3. GO rule:** K≥5 sweep beats chance AND engine beats placebo AND engine is right on ≥1 *genuinely*
  counter-intuitive item. It's proof-of-LIFE, not a powered confirmation.
- **B4. Sealed, role-separated pre-registration.** The engine-runner seals (git commit) the pack +
  per-item predicted direction + audited obvious-priors + placebo + win rule BEFORE any outcome is
  computed; a DIFFERENT person runs the scorer and verifies the committed hash. Why: the campaign
  proved we can fool ourselves on counter-intuitive cases; the named failure mode is "wanting it to
  pass." Mechanically defeats HARKing, post-hoc persona edits, metric-shopping, optional stopping.
- **B5. Real behavioral outcome, not stated preference** (a consequential in-game action). Why: behavior
  is far harder to fake than survey answers under social desirability (F&F know the founder).

## C. Game & experience
- **C1. An economic-decision game with a real (probabilistic) payout** ("Split The Loot" skeleton). Why:
  real stakes make choices genuine; probabilistic payout (e.g. 1-in-20 paid at 20×) gives real incentive
  at low cost. Rejected: a survey (stated preference, social-desirability-contaminated).
- **C2. Profiling is REVEALED through play, not asked.** Mechanic→trait: risk box→risk/EV-sensitivity;
  info-cost→attention/effort; deal room→present-bias/patience; trust game→trust/reciprocity;
  ambiguity→ambiguity-aversion; plus passive latency/scrub/dwell (can't be gamed). decision_speed is
  derived from RiskBox first-tap latency (#442 fix). Why: in-character economic choices neutralize
  social desirability; revealed > stated.
- **C3. A shareable "persona-card" reveal AFTER all outcomes.** Why: drives the F&F forwarding loop for
  sample size. Strictly after outcomes — revealing it earlier would contaminate behavior.
- **C4. ~5 min, mobile-first, taps/sliders only, 7-dot progress, autosave/resume.** Why: F&F bail on
  long/typing-heavy flows; completion is the #1 sample-size lever.

## D. Experiment design
- **D1. ONE link, server-side randomized — NOT two links (control/treatment).** Why: two hand-routed
  links make the founder's routing the assignment mechanism → fatal selection confound. The arm is
  block-randomized server-side and **never encoded in the URL or sent to the client** (folded into
  rendered config in `screenConfig.js`). Sticky per token/cookie; single-use tokens; forwarding logged.
- **D2. Headline A/B (countdown-urgency) between-subject; the rest within-subject (counterbalanced).**
  Why: you can't un-ring the urgency bell (between), but within-subject ~4×'s power at tiny N and yields
  the K paired comparisons. Within-subject variants assigned deterministically per player_id+task_id.
- **D3. Block randomization** (not pure Bernoulli). Why: at small N pure random can hand a 26/14 split.

## E. Data architecture
- **E1. Two physically separate tables = the leakage firewall.** `player_features` (pre-treatment only;
  the ONLY thing run_pipeline sees) vs sealed `player_outcomes` (arm + binary outcome). Mirrors the
  Hillstrom panel precedent. Enforced at the code boundary: `recordFeature()` rejects any arm/outcome-
  shaped key (anchored regex, allow-list) and the export aborts on a forbidden column.
- **E2. Features captured BEFORE the arm fires, identical across arms.** Why: anything logged after the
  player crosses into an arm is post-treatment and leaks. The #442 independent audit confirmed all
  features are pre-treatment and no feature is an outcome-proxy.
- **E3. PII (payout contact) kept in a separate table, never in the feature export.** Why: privacy +
  no leakage; only the de-identified feature table leaves for the pack build.

## F. Pack pipeline
- **F1. Reuse the production pipeline:** `run_pipeline(friends_family.yaml, require_llm=True)`. **--require-llm
  is REQUIRED** — it emits behavioral_seeds (PR sidira-personas#18) + enriched descriptions; a fallback
  pack scores ~0 for reasons unrelated to the engine.
- **F2. k_range [2,4]** (not [4,8] like streamly) and **embedding_dim_per_group: 2** (not 4). Why: at
  N≈60 the default 12-D space made BIC over-split; 6-D yields a stable k=3 (Jaccard 0.95–0.99, ≥10/cluster).
  `holdout_frac: 0.0` (a holdout starves the fit at small N; rely on per-cluster Jaccard).
- **F3. Built/tested on SYNTHETIC data first.** Why: validates the whole pipeline end-to-end before real
  players exist; the committed `friends_family_panel_v1.json` is clearly labelled synthetic and real
  packs rebuild from the real Table A export at run time.
- **F4. Score at the PLAYER level via the assignments map** (player_id→persona_id), not only at k
  personas. Why: gives N comparisons from few clusters at F&F scale.

## G. Sealed-run harness
- **G1. Full engine (SimulationRunner) conditioned on the friends_family pack** — NOT a population-level
  forecaster. Why: the whole claim is "given THIS pack, does the engine predict THESE players"; a
  population forecaster wouldn't test pack-conditioning. `predict.py` never reads outcomes; `score.py`
  is the separate, role-separated tool that verifies the sealed hash first.

## H. Deploy (chosen 2026-06-18: AWS-minimal)
- **H1. Single t4g.small EC2 + SQLite on a durable EBS volume + CloudFront/TLS.** Why: cheapest
  (~$10–15/mo), fastest to ship, durable across restarts, fine for F&F + up to a few hundred players.
  Rejected: AWS-managed (Amplify+App Runner+RDS) — more robust/scalable but more setup/cost, premature
  for the pilot; PaaS (Render/Fly) — breaks all-AWS consistency. Upgrade path to RDS/managed is open if
  worldwide ad-recruitment scales big.
- **H2. SQLite hardening:** WAL mode + checkpoint-on-graceful-shutdown + configurable DB path on the EBS
  mount + EBS snapshot backups. Why: durability without a managed DB at this scale.
- **H3. Standalone deploy, separate from api.sidira.ai.** Why: it's a data-collection tool, not the core
  product — no risk to the production backend, no api redeploy implicated.
- **H4. Recruitment:** F&F via direct per-recipient links (free). Paid scale-up — US via Prolific/
  CloudResearch, India/Chennai via Meta geo-ads (cheapest, ~$3–5/valid completion) or Cint. The same
  hosted link scales worldwide via Meta geo-ads. See `INDIA_CHENNAI_RECRUITMENT.md` /
  `POC_VENDOR_SHORTLIST.md`.

## I. Open items / known limits
- Proof-of-LIFE only — a GO gates the paid PoC, not deployment accuracy.
- Panel-task behavior ≠ real-stakes behavior (demand characteristics) — a win is "predicts game
  behavior," to extend later.
- US+India mix at small N may cluster on locale + cross-cultural effects can cancel some micro-A/Bs into
  ties → recruit enough to keep K≥5 callable items.
- Live AWS provisioning (EC2/EBS/CloudFront/ACM/DNS) is a documented runbook step the founder triggers —
  not auto-provisioned in the build loop.
