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
— **🚀 DEPLOYED LIVE to prod via AWS CLI (2026-06-19) — https://play.sidira.ai.** EC2 t4g.small `i-07d2a5b4c5f2ff946` (us-east-1, acct 897729137726) + durable 10GB /data EBS + Caddy auto-TLS (valid Let's Encrypt) + Route53 A `play.sidira.ai`→13.222.172.200 + SG 80/443 + SSM instance profile (no inbound SSH). Self-deployed from `ram-de/sidira-ff-game` via cloud-init + read-only deploy key. **Verified in prod:** HTTPS+cert, SPA 200, /healthz 200, fresh players get a server-assigned arm (never leaked), services active, /data mounted, **two-table firewall HOLDS** (`player_features` has no arm/outcome/task_id; `FEATURES_HAS_ARM_OR_OUTCOME=false`). ~$12/mo, all tagged `project=ff-validation-game`. Ops record (resources, **test-data reset before the real run**, SSM data-pull, teardown) in `LIVE_DEPLOYMENT.md`. **REMAINING (founder): (a) wipe the ~9/5 smoke-test rows (LIVE_DEPLOYMENT §reset); (b) recruit players (send the link); (c) rebuild pack from real Table A → SEALED ROLE-SEPARATED validation (you seal predict.py → a different person runs score.py) → GO/NO-GO.** The autonomous /loop's stop condition (demo-ready + deployed to prod) is now MET.
— **✅ BUILD COMPLETE — game extracted to its own repo, demo-ready + deploy-runbook-ready (2026-06-19).** Autonomous /loop completed all 7 tickets (#439 scaffold → #440 rooms → #441 micro-A/Bs → #442 independent audit → #443 pipeline/pack/loader → #444 sealed harness → #445 prod-harden). The game now lives at **`ram-de/sidira-ff-game`** (extracted from `sessions/ff-validation-game/app/`, which is now a pointer) — builds + boots standalone (SPA 200, /healthz 200, rows in both tables). Code-enforced: two-table leakage firewall, server-side block randomization (arm never in URL), 5 profiling rooms + 5 micro-A/Bs (independent audit: 4/5 genuinely counter-intuitive), pack via run_pipeline(--require-llm) (v1.1 quad + behavioral_seeds, k=3 on synthetic), blinded predict.py + role-separated score.py + **synthetic-pack seal-guard** (refuses a real seal on the synthetic pack). Deploy = AWS-minimal (t4g.small + SQLite-on-EBS + CloudFront/TLS, ~$11–15/mo) per `sidira-ff-game/deploy/DEPLOY.md`. Decisions logged in `DESIGN_DECISIONS.md`; recruitment in `INDIA_CHENNAI_RECRUITMENT.md` + `POC_VENDOR_SHORTLIST.md`. **REMAINING (all founder-triggered, #445 + epic #438):** (a) provision live AWS infra per DEPLOY.md; (b) recruit players (F&F direct links; paid scale via Meta geo-ads / US panels); (c) once real data lands — rebuild the pack from the real Table A export, run the SEALED ROLE-SEPARATED validation (engine-runner seals predict.py → a DIFFERENT person runs score.py), report GO/NO-GO. Known nit: 2 stale `app/` path refs in `backend/services/friends_family_archive.py` comments (cosmetic; left per backend-scope constraint). MCP gitnexus was unavailable all session → manual impact analysis throughout.
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
