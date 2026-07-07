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
- [ ] M4 white-glove dry-run on a real web product (FOUNDER-GATED: needs a vouched `neg_control_map` on a real pack + the #568 separate-table join exercised on live partner data)

## Completed
- [x] Cross-repo + ticket + GTM recon (3 scouts); partner profile locked: **web app · separate treatment table · "fully working" = honest verdicts · white-glove**; EPIC #572 + milestone filed; punt EPIC #571; BUILD_PLAN.md.
- [x] **M1 — the grounded route can fire (2026-07-05→06, iters 1–10):** estimability producer vendored + hardened in sidira-personas (#22–#26: guard contract, config-gated emit + auto-NC, config-driven outcome/lever discovery, NC-in-covariates false-trust fix, NC diagnostics) + consumer wiring in sidira-simulator (#574 schema compat, #575 fix propagation, #576 estimability build-config → `_build_pipeline_config` (#568 v1 — a Snowflake join-VIEW already works as a source, so v1 separate-table is an onboarding pattern, not code), #577 read-only lever card, #578 human vouch/reject (honesty asymmetry: reject force-abstains, vouch never upgrades), #579 reject wired into runtime `decide()`).
- [x] **M2 — flag ON + honest surface (2026-07-06→07):** #580 `SIDIRA_DECISION_FLOW_ENABLED` inverted to **default-ON** (env var = emergency kill-switch, wired into `ec2-api-deploy.sh`), deployed + verified in-container. **#564** coverage manifest + per-lever grounding-completeness: producer personas#27 (top-level `coverage` with structural/behavioural/present missingness + `grounding_complete`/`grounding_gaps` tokens per candidate, ungroundable stub rows) + consumer sim#581 (schema tri-state, watchdog `CANT_VALIDATE` names the gaps before supportability, token-allowlisted `DirectionVerdict.grounding_gap_reason` sidecar field — producer free text can never reach the customer verdict; lever-card API carries gaps + bounded coverage summary). **#566** grounding-sources view sim#583: per-lever panel on simulation detail (capability → columns-or-gaps → guard verdict with bound policy → grounded/abstain route), coverage line, `GROUNDING GAP:` under the verdict WHY line; legacy/404 degrade honestly (not-assessed / render-nothing).
- [x] M3's build parts landed early under M1/M2: #565 lever card + vouch/reject + runtime override all merged.

## Next Steps
1. **⚠️ Backend redeploy pending** — sim#581 touches `backend/` (schema + watchdog + lever-card API). Code-only, no migration. Until deployed, prod serves the pre-#564 payload (the #566 UI degrades gracefully).
2. **[FOUNDER] M4 dry-run** — rebuild a real pack (Streamly or partner) with an estimability declaration + joined treatment VIEW; review the lever cards; vouch a real `neg_control_map` (auto-NC over/under-abstains — iter-3/5 findings). This is the step that turns CANT_VALIDATE into real CONFIRMS/CONTRADICTS.
3. **[FOUNDER, in parallel]** partner agreement in writing that "fully working" = honest verdicts on his data (not proven-accuracy).
4. Grounded chat on the verdict (M3 exit criterion) — `grounded_agent_chat` service exists behind the flag; check whether the chat surface is reachable from the verdict panel and wire if not.
5. Housekeeping: #582 (stale `test_deploy_config.py` basic_auth assertions failing on pristine main).

## Key Files
- EPIC #572 (canonical tracker) · milestone "First Design Partner Onboarding"
- `sessions/design-partner-onboarding/BUILD_PLAN.md` · `SEPARATE_TABLE_ONBOARDING.md` (white-glove runbook)
- `sessions/watchdog-productization/GROUNDED_DECISION_ARCHITECTURE.md` — the build spec (§4 = coverage/completeness)
- Producer: `sidira-personas/sidira_personas/estimability/manifest_builder.py` (main `75b650e`)
- Consumer: `backend/sidira_simulator/schemas/estimability.py` · `services/negative_control_watchdog.py` · `services/lever_card_view.py`
- UI: `frontend/app/simulations/[id]/SimulationDetailV2.tsx` (grounding panel) · `frontend/app/personas/[id]/PersonaPackDetailV2.tsx` (lever card)

## Key Context
- **The entire build spine of EPIC #572 is now merged and (except sim#581) deployed**: producer → manifest → consumer → lever card → human vouch/reject → runtime override → coverage/completeness honesty → grounding-sources UI, with the decision flow ON by default in prod.
- What remains is deliberately founder-gated, because it needs a human/partner in the loop: a **vouched neg_control_map on a real pack** (LLM/auto NC nomination proven unsafe alone — iter-5) and **#568 exercised on live partner data**. Without those, every lever honestly resolves CANT_VALIDATE → LLM fallback — which is correct behavior, now visibly explained per-lever in the UI.
- Accuracy is deliberately NOT in the DoD: it needs his known-outcome experiments, which arrive only once he's using it. Validation (#517/#547/#222) and paid pilot are the *next* epic.

## For my cofounder
The product now *shows its work*: every lever on a sim tells you whether it was grounded on real columns, and if not, exactly why (never-tracked column, no vouched negative control, …) — and abstains instead of guessing. The one thing standing between this and a real grounded SHIP/NO-SHIP for the partner is sitting with a real pack and vouching the negative controls (M4, white-glove, needs you). Also: redeploy the backend for sim#581 when convenient.
