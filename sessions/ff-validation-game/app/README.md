# Split The Loot — the friends-&-family validation game (scaffold)

A ~5-minute mobile-web game that is secretly a **blinded, pre-registered test of
the Sidira simulation engine**. Players run real-consequence economic choices;
the game profiles them (pre-treatment) and runs **counter-intuitive micro-A/Bs**
with real behavioral outcomes. We then ask: *given a persona pack built from
these same players, does the engine predict the DIRECTION of their A/B
behavior?*

Authoritative design spec:
[`../../agent-behavior-spec/ff-app-design/FF_GAME_DESIGN.md`](../../agent-behavior-spec/ff-app-design/FF_GAME_DESIGN.md).

> **Scaffold status.** Structure + core plumbing are complete and runnable.
> Two profiling rooms and two micro-A/Bs are fully implemented as the pattern;
> the rest are stubbed with `TODO`s (see *What's done vs stubbed* below).

## Run it

```bash
npm install
npm run dev        # http://localhost:5180  (single Express port; Vite in middleware mode)
```

A player can complete the happy path end-to-end: intro → 2 real profiling rooms
(+ 3 stub rooms) → micro-A/B battery (2 real + 3 stub, counterbalanced) → 3-tap
Seller Card → persona reveal. Rows land in **both** tables.

```bash
npm run export:features   # writes exports/player_features.csv + exports/player_outcomes.csv
npm run lint              # tsc --noEmit
npm start                 # prod: serves built dist/  (run `npm run build` first)
```

## The leakage firewall (two physically separate tables)

Mirrors the Hillstrom panel discipline — *"the outcome must never enter the
clustering or the pack would leak the answer key."* See `server/db.js`.

| Table | Holds | Fed to `run_pipeline`? |
|---|---|---|
| **A `player_features`** | `player_id` + PRE-treatment features ONLY: demographics, the 5 decision-style scores, gameplay-revealed passive features. **No arm. No outcome. No post-treatment field.** | **Yes — this is the only table the pipeline sees.** |
| **B `player_outcomes`** | `player_id`, `arm`, `task_id`, binary `outcome`, timestamps, `attention_passed`. The **SEALED answer key.** | **Never.** |

Enforcement is at the code boundary: `recordFeature()` throws on any
arm/outcome-shaped key, and `scripts/export_features.js` aborts if a forbidden
column ever appears in Table A.

## The one-link / server-randomization rule

**Do not** send "link A = control, link B = treatment" — whoever routes friends
to links becomes the assignment mechanism (a fatal selection confound). Instead:

- **One link** (or per-recipient tokens that do **not** encode the arm).
- The **server** assigns the between-subject headline arm + within-subject
  counterbalancing on first load (`server/randomize.js`), block-randomized for a
  balanced split at small N, and **sticky** per person (DB + localStorage token).
- The client **never** receives a guessable arm label — only the rendered config
  (`server/screenConfig.js`). The arm is folded into presentation
  (`countdownSeconds`/`showScarcity`), not exposed.
- Repeat visits (same token) resolve to the **same** assignment. Forwarded
  visits are flagged (`is_forwarded`, `referrer`); primary analysis =
  original-token users only.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/session?t=<token>` | Resolve/assign a participant (server-side), return the rendered screen config. Mints a token if none. |
| `POST` | `/api/event` | Per-beat telemetry → `events` (+ derived PRE-treatment features → Table A). Logs choice, latency-to-first-tap, re-tap/scrub, dwell, fine-print-opened, options-inspected, arm, referrer. |
| `POST` | `/api/outcome` | Binary outcome → **Table B** (the only path arm+outcome reach the DB). |
| `POST` | `/api/seller-card` | 3-tap demographics → Table A (pre-treatment, pre-reveal). |

## Sealed / role-separated pre-registration discipline

Personas are built from **features ONLY**. The outcome file is the **sealed
answer key**. The pre-registered run (per the spec's *Sealed win rule*):

1. `npm run export:features` → `player_features.csv` (Table A).
2. Build the pack offline: `run_pipeline(df=features.csv, cfg=friends_family.yaml,
   require_llm=True)` → commit `friends_family_panel_v1.json`.
3. **Seal in one git commit before any outcome is computed:** the pack, per-item
   predicted direction + confidence, the obvious-prior label (set by a
   **non-author**), the primary binary outcome metric per item, the placebo's
   predictions, and the win/stopping rules.
4. A **different** person exports `player_outcomes.csv` (Table B), verifies the
   sealed hash, and scores the **direction hit-rate across K≥5 micro-A/Bs**
   (5/5 → p=0.03; 4/4 → p=0.06). GO iff the hit-rate clears the binomial bar
   **and** beats the "always-pick-obvious" placebo **and** is right on ≥1
   counter-intuitive item. *Any post-seal edit burns the run.*

The named failure mode to guard against: *wanting it to pass.*

## What's done vs stubbed

**Done (the pattern):**
- Full backend plumbing: two-table firewall, server-side block randomization,
  sticky assignment, forwarding detection, per-beat telemetry, feature
  derivation, all four endpoints.
- Frontend screen state machine: intro → profiling → battery → seller card →
  reveal-after-outcomes, 7-dot progress, autosave/resume per beat, tap-only.
- **2 profiling rooms:** Risk Box (`src/rooms/RiskBox.tsx`) and Info-Cost
  (`src/rooms/InfoCost.tsx`) — each maps its mechanic to decision-style features.
- **2 micro-A/Bs:** Choice Overload (`src/microabs/ChoiceOverload.tsx`, 3-vs-24)
  and Countdown Urgency (`src/microabs/CountdownUrgency.tsx`, the between-subject
  headline) — each logs a binary outcome to Table B.
- Export script + this README.

**Stubbed (clear `TODO`s):**
- Profiling rooms: Deal room, Trust game, Ambiguity (`src/rooms/StubRoom.tsx`).
- Micro-A/Bs: default-stickiness, prosocial-backfire, effort-justification
  (`src/microabs/StubMicroAb.tsx`). **Reach K≥5 implemented before sealing.**
- The persona reveal card is a cosmetic client-side heuristic for the forwarding
  loop; the REAL pack is built offline from Table A by `run_pipeline`.
- Probabilistic 20× payout is framing-only (no payout backend).
- `friends_family.yaml` + `friends_family_panel_v1.json` + the cloned
  `hillstrom_panel_loader.py` are the next session's work (offline pipeline).
