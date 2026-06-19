---
type: session
domain: ff-validation-game
status: active
started: 2026-06-18
owner: ram-de
---

# Session: ff-validation-game — a friends-&-family game that manufactures a real-outcome test of the simulation engine

## Goal
Build a friends-&-family app/GAME that secretly IS a blinded, pre-registered test of the simulation
engine: it profiles each player (→ a persona pack) AND runs counter-intuitive A/Bs with real
behavioral outcomes, so we can ask "given a pack built from these players, does the engine predict
their real A/B behavior?" The unpaid, owned, fastest path to the first real-outcome capability read.
(Spun out of [[directional-sim-campaign-standing]] — the #342 campaign exhausted public-data proxies;
value is gated on a real-outcome validation.)

## In Progress
— **✅ DESIGN COMPLETE via two councils (2026-06-18).** Claude council (4 lenses: experiment-design,
gamification/UX, persona-pack data-fit, validity) + Codex/gpt-5.5 panel. Strong convergence →
synthesized into `ff-app-design/FF_GAME_DESIGN.md`. Headlines: (1) **one link, server-randomized**
(the founder's "two links = control/treatment" is a fatal selection confound — arm never in URL);
(2) economic-decision game (~5 min, real probabilistic payout) where profiling is REVEALED through
play (risk box / info-cost / deal / trust / ambiguity rooms) + a shareable "Trader Type" reveal
(after outcomes) drives the F&F forwarding loop; (3) the engine test = **a battery of 5–6
COUNTER-INTUITIVE micro-A/Bs** (scarcity-backfire, choice-overload, default-stickiness,
prosocial-impact-backfire, effort-justification) — score the **hit-rate across K**, not one fragile
A/B; headline item between-subject, rest within-subject (~4× power at tiny N); (4) **two-table
leakage firewall** (Table A pre-treatment features → run_pipeline; Table B arm+outcome SEALED) mirror
of the Hillstrom panel; (5) **sealed, role-separated, proof-of-life win rule** (K≥5: 5/5→p=0.03,
4/4→p=0.06; must beat the "always-pick-obvious" placebo + be right on ≥1 counter-intuitive item).

## Completed
- Two-council design + synthesis → `FF_GAME_DESIGN.md` (+ source `codex_council.md`).

## Next Steps
1. Build the mobile-web SPA: server-side randomization + tiny DB (two tables) + resume + probabilistic payout; log per-beat (choice, latency, scrub, dwell, fine-print, arm, referrer).
2. Author the profiling rooms (mechanic→trait map) + the 5–6 counter-intuitive micro-A/Bs (label each obvious-prior; non-author does the labeling + a feature↔outcome leakage audit BEFORE sealing).
3. `friends_family.yaml` (modeled on streamly.yaml; k_range [2,4]); run `run_pipeline(require_llm=True)` → pack (v1.1 quad + behavioral_seeds) → commit `friends_family_panel_v1.json`; clone `hillstrom_panel_loader.py`.
4. SEAL (one git commit, role-separated): pack + per-item predicted direction + obvious-prior labels + placebo predictions + win/stopping rules — BEFORE any outcome is computed.
5. Field the link → blinded engine run (predict each item's direction) → score hit-rate vs Table B at the PLAYER level (via the assignments map) → GO/NO-GO per the sealed rule.

## Key Files
- `sessions/agent-behavior-spec/ff-app-design/FF_GAME_DESIGN.md` — the synthesized buildable spec.
- `sessions/agent-behavior-spec/ff-app-design/codex_council.md` — Codex panel source.
- Precedent to clone: `backend/sidira_simulator/services/hillstrom_archive.py`, `adapters/hillstrom_panel_loader.py`; example config `~/Projects/sidira-personas/config/streamly.yaml`.
- `sessions/agent-behavior-spec/POC_RUNBOOK.md` / `POC_VENDOR_SHORTLIST.md` — the paid PoC (run in parallel).

## Key Context
- **This is a CAPABILITY test on a consistent population** (build pack from the same players you test) — F&F bias is fine; representativeness is a deployment concern. A GO licenses the paid PoC / design-partner stage, NOT deployment accuracy.
- Hard lessons baked in: hypotheses MUST be non-obvious (else a correct prediction is hollow); real behavioral outcome not stated preference; blinded + pre-registered + role-separated (the campaign already proved we can fool ourselves on counter-intuitive cases).
- The `behavioral_seeds` pipeline fix (sidira-personas#18 + sidira-simulator#435, merged 2026-06-18) feeds straight into this — run with `--require-llm` so packs carry rich per-persona identity pools.

## For my cofounder
The #342 campaign concluded the cheap technical levers are exhausted; the engine's value is gated on a
real-outcome validation. This session is the cheapest/owned way to get one: a F&F game. Design is done
(two-council synthesis in `FF_GAME_DESIGN.md`) — next is building the SPA + sealing a pre-registered
run. The non-negotiables: one link (server-randomized, arm never in URL), ≥5 counter-intuitive
micro-A/Bs scored on hit-rate vs the obvious-prior placebo, the two-table leakage firewall, and a
sealed role-separated run. Watch the one failure mode the validity lens named: *wanting it to pass.*
