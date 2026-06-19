# Independent audit — obvious priors + feature↔outcome leakage (ticket #442)

**Auditor:** independent reviewer (#442). Did NOT author the game.
**Scope:** `sessions/ff-validation-game/app` (merged to main).
**Inputs read:** `FF_GAME_DESIGN.md`; the 5 profiling rooms (`src/rooms/*.tsx`);
the 5 micro-A/Bs (`src/microabs/*.tsx`) + `obvious_priors.json`; `server/db.js`
(`player_features` schema + `recordFeature` allow-list + firewall regex);
`server/app.js` (event/outcome routing); `server/screenConfig.js`;
`server/randomize.js`; `scripts/export_features.js`.

---

## AUDIT 1 — feature ↔ outcome leakage

### 1a. Are all features genuinely PRE-treatment?

YES. Verified by tracing the write paths, not by reading comments:

- `recordFeature()` (the ONLY Table A writer) is called from exactly two places
  in `server/app.js`: the `POST /api/event` handler **gated on
  `phase === 'profiling'`**, and `POST /api/seller-card` (tap-only demographics,
  post-game but pre-reveal). Micro-A/B screens call `logOutcome()` →
  `POST /api/outcome` → `recordOutcome()`, which writes Table B **only**. No
  micro-A/B beat carries a `features` payload, and even if one did, the
  `phase` gate would drop it.
- All 5 feature-emitting rooms (RiskBox, InfoCost, DealRoom, TrustGame,
  AmbiguityRoom) are in `PROFILING_ROOMS` and are **identical for every player**
  — `buildScreenConfig` applies no arm/variant to them. They render and log
  before the micro-A/B battery, so every feature is captured on arm-identical
  screens before any arm fires.
- The between-subject headline arm and within-subject variants are assigned at
  session creation but only *consumed* by the micro-A/B screens, never by a
  profiling room. So a feature value cannot depend on the arm.

### 1b. Did any arm/outcome-shaped column slip into `player_features`?

NO. The schema is fully declared statically in `db.js` (one `CREATE TABLE` plus
one additive `ALTER` block adding `patience, trust, reciprocity,
ambiguity_aversion`). The complete column set is:

```
player_id, age_band, locale, device, tenure_days,
decision_speed, deal_sensitivity, present_bias, effort_tolerance, reactance,
patience, trust, reciprocity, ambiguity_aversion,
warmup_decision_ms, warmup_options_inspected, warmup_skip_rate, warmup_reread_rate,
updated_at
```

Regex-checked all 19 against the firewall pattern
`/(^|_)(arm|outcome|task|treatment|variant)(_|$)/i` (the export guard) **and**
the stricter db.js pattern (adds `reveal|persona`): **zero matches**. The
anchoring is correct — `warmup_*` does NOT false-trip on the "arm" substring
(confirmed). `recordFeature`'s allow-list (`FEATURE_COLUMNS`) is a strict subset
of the real columns, and unknown keys are dropped; arm/outcome-shaped keys throw.
Table B (`player_outcomes`: `arm`, `task_id`, `outcome`, `attention_passed`) is
physically separate and is the only place arm/outcome live. Export writes the two
CSVs separately with the same abort-on-forbidden-column guard. **Firewall holds.**

Minor (non-leakage) note: `decision_speed` is declared in the schema but never
written by any room (latency is captured as `warmup_decision_ms` instead). It is
a harmless always-NULL column, not a leak. Flagged for tidiness only.

### 1c. Per-pair verdicts (each PRE-treatment feature × each micro-A/B outcome)

The bar applied: a pair is **BAD (leakage)** only if the feature *restates /
encodes / near-transcribes* the outcome (same question asked twice, or a feature
derived from a screen seen only inside an arm). It is **GOOD** if the feature is
an upstream trait that *plausibly causes* the outcome — that is the entire point
of the test.

The feature-emitting rooms and what each logs:
- **RiskBox** → `deal_sensitivity` (EV-chase), `present_bias` (grab-sure-thing).
- **InfoCost** → `effort_tolerance` (hints bought), `reactance` (pick blind).
- **DealRoom** → `present_bias`, `patience`, `deal_sensitivity` (take-now vs wait/counter).
- **TrustGame** → `trust`, `reciprocity`, `reactance` (send-little skepticism).
- **AmbiguityRoom** → `ambiguity_aversion`, `reactance` (known vs mystery box).
- Passive: `warmup_decision_ms / _options_inspected / _skip_rate / _reread_rate`.
- Demographics: `age_band, locale, device, tenure_days`.

| micro-A/B (outcome) | most-relevant feature(s) | verdict |
|---|---|---|
| **choice_overload** (claim vs skip a reward) | `deal_sensitivity`, `warmup_options_inspected`, `decision_speed/latency` | GOOD — upstream choice-style traits plausibly drive choose-vs-skip. The reward-claim screen is a *different* task from any profiling room; nothing restates "did you claim". No transcription. |
| **countdown_urgency** (lock in vs pass) | `reactance`, `present_bias`, `patience` | GOOD — reactance is the hypothesized causal mediator (the whole bet); present_bias/patience plausibly drive lock-in. The Deal Room measures intertemporal preference via a *haggling* mechanic, not "do you respond to a countdown" — no overlap with the urgency screen. Legitimate. |
| **default_stickiness** (keep safe default vs opt out) | `present_bias`, `patience`, `reactance` | GOOD — staying with a pre-checked safe option is plausibly *caused* by present-bias/low-patience and by low reactance to social proof. The Deal Room never shows a pre-checked default or social-proof line; it is not the same question. Upstream trait, not a proxy. |
| **prosocial_backfire** (gave ≥50% to pool vs kept) | `trust`, `reciprocity`, `reactance` | GOOD — generosity/reciprocity disposition (TrustGame) and reactance-to-persuasion plausibly cause giving. **Watch item:** TrustGame's `trust` (fraction of 10 coins *sent*) and the prosocial outcome (≥5 of 10 coins *given to a pool*) share a give-coins-to-others surface. I judged this GOOD, not BAD: TrustGame is a tripled-return *investment/trust* decision with a partner who reciprocates, whereas prosocial is a one-shot *donation* split with no return; different incentive structure, different construct (trust vs altruism). It is a strong upstream predictor, not a transcription of the same question — which is exactly the legitimate case the spec calls for. Borderline but PASS. |
| **effort_justification** (commit vs decline next round) | `effort_tolerance`, `decision_speed/latency` | GOOD — effort tolerance (hints bought in InfoCost) plausibly causes downstream commitment after an earned step. Different mechanic (buying hints vs tapping to build a badge); no shared screen, no restatement. |

Cross-cutting: `reactance` feeds three rooms (InfoCost, TrustGame, AmbiguityRoom)
and predicts three outcomes. That is *concentration of a causal trait*, not
leakage — none of those rooms shows the micro-A/B outcome screen, and the trait
is logged before any arm fires.

### AUDIT 1 RESULT: **LEAKAGE-CLEAN. No BAD pairs.**

All feature↔outcome pairs are upstream-trait→outcome (GOOD). One borderline pair
(TrustGame `trust`/`reciprocity` → prosocial giving) was scrutinized and cleared:
distinct construct and mechanic, not an outcome transcription. Features are all
pre-treatment (phase-gated + arm-identical screens). No arm/outcome/post-treatment
column exists in `player_features` (PRAGMA-equivalent static-schema + dual-regex
check). The two-table firewall and both code guards are correctly implemented.

---

## AUDIT 2 — obvious-prior labels (independent judgment)

For each item I independently answer: (a) which arm does a *naive
"more-is-better / obvious"* observer back to produce more `outcome=1`? and
(b) is the item genuinely counter-intuitive (the obvious answer is plausibly
wrong / a coin-flip), or is it actually obvious (a hollow test)?

### 1. choice_overload — `outcome 1 = claimed`, arms `opts:3` / `opts:24`
- **Naive obvious arm:** `opts:24` ("more options = more value/engagement →
  more likely to claim"). **CONFIRM** the proposed label.
- **Counter-intuitive?** YES. Choice overload (Iyengar–Lepper) is a well-known
  *result* but the naive lay intuition genuinely runs the other way — a casual
  observer expects more choice to help, not paralyze. The obvious answer is
  plausibly wrong. CONFIRMED counter-intuitive.

### 2. countdown_urgency — `outcome 1 = locked in`, arms `framing:scarce` / `framing:calm`
- **Naive obvious arm:** `framing:scarce` ("scarcity + countdown is the classic
  conversion lever"). **CONFIRM.**
- **Counter-intuitive?** YES, *conditioned on the F&F-reactance context*. In a
  generic stranger funnel, scarcity-wins is nearly obvious and would be a hollow
  test; but the bet here is that an audience that *knows it's being sold to by a
  friend* reacts against the pressure. That reactance reversal is non-obvious.
  CONFIRMED counter-intuitive — with the caveat that its counter-intuitiveness
  rests entirely on the audience, which the engine must capture via `reactance`.

### 3. default_stickiness — `outcome 1 = stayed locked in`, arms `stickiness:default` / `stickiness:framing`
- **Naive obvious arm:** the AUTHOR proposed `stickiness:framing` (a persuasive
  gain-framed pitch reads as "more motivating" than a quiet pre-checked box).
  **REVISE → `stickiness:default`.**
- **Why I revise:** The outcome is `1 = stayed locked in / kept the safe choice`.
  The `default` arm *starts the player already in the locked-in state* (pre-checked
  "keep my coins safe" box) and adds "most players lock in" social proof. The
  naive "more-is-better/obvious" observer knows the power of a pre-checked default
  + bandwagon line — that is itself the textbook "obvious" conversion move, every
  bit as much as a gain-frame. Pointed at *this* outcome (stickiness/inertia), the
  obvious bettor backs the arm that defaults you in and tells you everyone stays:
  `stickiness:default`. The author's own thesis even says "DEFAULT stickiness
  beats framing," i.e. the authors bet `default` — but they labeled `default` as
  *their* bet AND labeled the obvious arm as `framing`, which would make the item
  counter-intuitive only if the obvious observer truly favored framing. I do not
  think a smart naive observer favors a wordy prospect-theory paragraph over a
  pre-checked box + "most people do this" for an *inertia/stay-locked-in* outcome.
- **Counter-intuitive? → NO (hollow as currently framed).** Once the obvious arm
  is corrected to `default`, the author's bet (`default` wins) *coincides* with
  the obvious prior. A smart observer would say "well, obviously the pre-checked,
  socially-proofed default is stickier." This item does **not** clear the
  counter-intuitive bar. It is a legitimate A/B, but it is an *obvious* one — it
  cannot demonstrate skill-beyond-the-thumb, because the thumb and the engine
  agree. **Marked NOT counter-intuitive.**

### 4. prosocial_backfire — `outcome 1 = gave ≥50%`, arms `prosocial:polished` / `prosocial:sparse`
- **Naive obvious arm:** `prosocial:polished` ("a vivid impact story lifts
  giving"). **CONFIRM.**
- **Counter-intuitive?** YES. The naive observer expects a polished "your impact
  compounds" appeal to raise generosity; the bet is that it reads as a sales pitch
  and *suppresses* giving (persuasion-backfire / reactance). Plausibly wrong-or-
  50-50 to a lay observer. CONFIRMED counter-intuitive.

### 5. effort_justification — `outcome 1 = committed`, arms `effort:effort` / `effort:one_tap`
- **Naive obvious arm:** `effort:one_tap` ("remove friction → more completion").
  **CONFIRM.**
- **Counter-intuitive?** YES. The dominant product reflex is friction-kills-
  conversion, so the naive bet is one_tap. The effort-justification / IKEA effect
  (a little earned effort *raises* commitment) is the non-obvious reversal.
  CONFIRMED counter-intuitive.

### AUDIT 2 confirmed-label summary

| task_id | obvious_prior_arm (CONFIRMED) | changed? | counter-intuitive (CONFIRMED) |
|---|---|---|---|
| choice_overload | `opts:24` | confirmed | YES |
| countdown_urgency | `framing:scarce` | confirmed | YES |
| default_stickiness | **`stickiness:default`** | **REVISED** (was `stickiness:framing`) | **NO** |
| prosocial_backfire | `prosocial:polished` | confirmed | YES |
| effort_justification | `effort:one_tap` | confirmed | YES |

- **K (total micro-A/Bs):** 5 → meets **K ≥ 5**.
- **Counter-intuitive count (CONFIRMED):** 4 of 5 = 0.80 → meets **≥ half**.
- The author's claimed `counter_intuitive_count: 5 / fraction 1.0` is **overstated
  by one**: `default_stickiness` is NOT counter-intuitive once its obvious prior is
  corrected. Corrected to 4/5.

---

## OVERALL VERDICT: **PASS** (with one correction folded in)

- **Leakage-clean:** PASS. No BAD feature↔outcome pairs; all features
  pre-treatment; no arm/outcome column in `player_features`; firewall intact.
- **K ≥ 5 with ≥ half counter-intuitive:** PASS. K = 5; 4/5 (0.80) confirmed
  counter-intuitive after revising `default_stickiness` to NOT counter-intuitive
  and its obvious prior to `stickiness:default`.

### Conditions / notes for the sealer (not blockers)
1. **`default_stickiness` carries no counter-intuitive evidentiary weight.** The
   K≥5 / ≥half bar is still met (4/5), but per `FF_GAME_DESIGN.md` the GO rule
   requires the engine be right on **≥1 item where the obvious prior is wrong**.
   That credit must come from one of the four genuinely counter-intuitive items
   (choice_overload, countdown_urgency, prosocial_backfire, effort_justification),
   NOT from default_stickiness, since there the obvious prior and the engine agree.
2. **countdown_urgency** is counter-intuitive only because of the F&F-reactance
   audience; its label is sound but its evidentiary value depends on the engine
   actually modeling reactance rather than generic scarcity-wins.
3. Tidy-up (non-blocking): `decision_speed` is an always-NULL declared column.
