# Build Plan — First Design Partner Onboarding

**Canonical tracker:** EPIC [#572](https://github.com/ram-de/sidira-simulator/issues/572) · GitHub milestone *First Design Partner Onboarding*.
**Punted work:** EPIC [#571](https://github.com/ram-de/sidira-simulator/issues/571) (self-serve polish) + #216 / #520 / #563.

---

## Why build-first (the strategy, in one paragraph)

The partner will only share data **once the product is fully working and he can start using it.** That removes the offline-backtest option (validate on his past experiments before building) — we can't validate first because we can't get the data first. So the sequence is unambiguous: **build the grounded product to genuinely-working → onboard him white-glove → the data, accuracy validation, and paid pilot all follow from him using it.** Onboarding *is* the unlock, not a reward for validation.

The good news: two of three repos (personas, crawler) and the entire decision-flow runtime are **already built and deployed** — just **inert**. The chain can't produce a single non-abstain verdict for anyone because **one producing step — the persona worker emitting an estimability manifest — was never built.** This plan closes exactly that gap for one real partner, and nothing more.

## Locked constraints (from the partner profile)

| Dimension | Value | Consequence |
|---|---|---|
| Product surface | **Web app** | Crawler handles it today. **Drop** #216 (native mobile), #520 (telemetry-UI). |
| Treatment/assignment data | **Separate table/warehouse** | **#568 multi-source is a HARD prerequisite**, coupled with the producer. Without the join → all-abstain. |
| "Fully working" bar | **Honest verdicts on his data** | SHIP/NO-SHIP/TEST-IT + honest abstain + grounding shown. **NOT** proven-accuracy. **NOT** self-serve polish. |
| Onboarding | **White-glove** (founder-assisted) | The join, crawl scope, and lever mapping can be founder-configured. Self-serve exposure → #571. |

## Definition of Done (agree in writing with the partner)

1. He connects his warehouse feature store (in place) → **persona pack builds**.
2. He connects/crawls his web product → **capability catalog** appears.
3. He asks a hypothesis → honest **SHIP / NO-SHIP / TEST-IT** verdict + **grounding-sources view** (grounded vs. abstained, and why).
4. Where the data can't answer → it **says "test it"** rather than guessing.
5. He can **chat** with the result.

**Explicitly NOT in the DoD:** proven accuracy on his experiments. That needs his known-outcome data, which only arrives once he's using it. Nail this down with him so "fully working" doesn't silently mean "already proven accurate" (the one thing we can't deliver pre-onboarding).

---

## Sequence

### M1 — Grounded route can fire (THE unlock) · #513 · #512 · #568 · producer
**Build the three coupled tickets + the producer together** — splitting them yields all-abstain.
- Vendor `causal_estimator.py` + `manifest_builder.py` from `research/` into **sidira-personas** (fresh branch off *its* `main`, **not** `friends-family-pack-443`).
- Extend `CandidateEffect` / manifest with NC-guard fields (`neg_controls`, `guard_trips`, `guard_confidence`, …).
- **#568**: manifest builder reads treatment from a **second joined source** (separate table) — v1 join-VIEW contract.
- **#512** (Stage 0 MAP): hypothesis → levers, metric, mechanism features, NC nominations.
- **#513** (Stage 1): wire estimability + NC guard into `SimulationOrchestrator`.
- Backend `persona_builder` writes `estimability_manifest.json` beside the pack in R2.
- **Exit:** for a real pack + joined treatment table, `load_estimability_manifest` returns ≥1 groundable candidate; watchdog can return **CONFIRMS/CONTRADICTS**, not only CANT_VALIDATE.

### M2 — Turn it on in prod + honest surface · #564 · #566 · flag wiring
- Wire `SIDIRA_DECISION_FLOW_ENABLED` into `deploy/ec2-api-deploy.sh` (SSM-only today = **no-op**); redeploy **twice** (script-edit gotcha).
- **#564**: coverage manifest + per-lever grounding-completeness check.
- **#566**: grounding-sources / observable-levers view on sim detail (web).
- **Exit:** flag ON; a hypothesis returns a grounded `DirectionVerdict` surfaced in UI; coverage shows grounded vs. abstained.

### M3 — Steerable + trustworthy · #565
- **#565**: LLM NC/confounder nomination + **reviewable lever card** (he confirms/adjusts).
- Grounded chat (`grounded_agent_chat`) reachable on the verdict.
- **Exit:** he can review/steer NC picks; chat anchored to verdict.

### M4 — White-glove onboarding dry-run on a real web product
- Rebuild a real pack (Streamly or his) + joined treatment table → manifest lands; **count groundable levers** (expect few from warehouse columns alone → justifies #568 and, later, ingesting experiment history #525).
- Founder-assisted: connect warehouse, set crawl scope, eyeball lever mapping.
- **Exit:** end-to-end dry-run yields honest verdicts on a real web product; ready to onboard the partner.

---

## After this epic (next epic, not here)
He uses it → shares outcomes → **accuracy backtest / scorecard** (#517 data contract · #547 Senu pairs · #222 shipped-prediction calibrator) → **paid pilot** → reference logo → partners 2–3.

## Deferred, on purpose
- **#571** self-serve onboarding polish — customer-#5-to-#10 problem.
- **#216** native mobile crawling — until a mobile partner.
- **#520** telemetry-grounded UI prediction.
- **#563** per-persona CATE / heterogeneity overlay — accuracy/differentiation, post-first-customer.

## Dependency map
```
producer (sidira-personas)  ─┐
#568 multi-source join      ─┼─► M1 (grounded route fires) ─► M2 (flag on + honest surface) ─► M4 (dry-run) ─► onboard partner
#512 MAP · #513 guard-wire  ─┘                                    └─► M3 (steer + chat) ┘
```
M1 is the critical unlock; M3 and M4 can overlap once M1 lands.
