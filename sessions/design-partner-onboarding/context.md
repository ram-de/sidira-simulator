---
type: session
domain: design-partner-onboarding
status: active
started: 2026-07-05
owner: ram-de
---

# Session: design-partner-onboarding — build the grounded product to "fully working" so the first design partner can onboard and use it

## Goal
Get one real design partner onboarded onto a genuinely-working grounded product (honest SHIP / NO-SHIP / TEST-IT verdicts on his data), because he will only share data once the product works and he can start using it. Onboarding him is the unlock for accuracy validation + paid pilot.

## In Progress
- [ ] M1 (the unlock): producer + guard wiring + multi-source join — #513 · #512 · #568 (build together)

## Completed
- [x] Cross-repo + ticket + GTM recon (3 scouts): personas/crawler/runtime are built + deployed but inert; the one missing piece is the estimability-manifest producer.
- [x] Partner profile locked: **web app · treatment data in a separate table · "fully working" = honest verdicts on his data (option 1), NOT proven-accuracy · white-glove onboarding.**
- [x] Filed delivery EPIC #572 + GitHub milestone "First Design Partner Onboarding" (M1–M4); scoped 6 child tickets (#512/#513/#568/#564/#566/#565) into it with per-ticket constraint comments.
- [x] Filed punt EPIC #571 (self-serve onboarding polish, post-first-partner); noted #216/#520/#563 as also-deferred.
- [x] BUILD_PLAN.md written (this folder).

## Next Steps
1. **Start M1** — vendor `causal_estimator.py` + `manifest_builder.py` from `research/` into **sidira-personas** (fresh branch off *its* `main`, not `friends-family-pack-443`); extend `CandidateEffect` with NC-guard fields; add the #568 join-VIEW so the manifest reads treatment from the separate table; wire #512 MAP + #513 guard into the orchestrator; `persona_builder` writes `estimability_manifest.json` to R2.
2. Rebuild a real pack + joined treatment table → confirm ≥1 groundable candidate lands (M4 dry-run substrate).
3. M2: wire `SIDIRA_DECISION_FLOW_ENABLED` into `deploy/ec2-api-deploy.sh` + coverage (#564) + grounding-sources UI (#566); flip on; redeploy twice.
4. **[FOUNDER, in parallel]** get the partner to agree in writing that "fully working" = honest verdicts on his data (not proven-accuracy — that needs his outcome data, which comes *after* he's using it).

## Key Files
- EPIC #572 (canonical tracker) · milestone "First Design Partner Onboarding"
- `sessions/design-partner-onboarding/BUILD_PLAN.md` — full sequenced plan + strategic rationale
- `sessions/watchdog-productization/GROUNDED_DECISION_ARCHITECTURE.md` — the build spec
- `founder-readout/why-sidira-beats-pm-insight.md` — positioning (§11 build-vs-buy)
- producer source to vendor: `research/empirical-uplift-spike/causal_estimator.py` (+ `manifest_builder.py`)
- break point: `backend/sidira_simulator/services/grounded_predictor.py` (`load_estimability_manifest`)

## Key Context
- The offline-backtest hedge (validate on his past experiments first) is **off the table** — he won't share data until the product works. So the sequence is unambiguously **build → onboard → data/validation/paid**, not validate-first.
- Load-bearing gap: the estimability-manifest **producer is unbuilt in sidira-personas**; without it every verdict abstains and falls to the (disproven) LLM. #513/#512/#568 must be built **together** or the result is all-abstain.
- Flag `SIDIRA_DECISION_FLOW_ENABLED` is OFF **and not wired into the deploy script** (SSM-only = no-op) — flipping on needs a deploy-script edit + redeploy twice.
- Accuracy is deliberately NOT in the DoD: it needs his known-outcome experiments, which arrive only once he's using it. Validation (#517/#547/#222) and paid pilot are the *next* epic, not this one.

## For my cofounder
This epic is the whole distance between "impressive inert architecture" and "one real partner sees a grounded verdict." The critical unlock is M1 (#513+#512+#568) — the persona worker emitting an estimability manifest that reads treatment from a separate joined table. Everything else is honest-surface + steering + a white-glove dry-run. Do NOT build self-serve polish (#571) or per-persona (#563) for this partner.
