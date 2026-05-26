---
type: session
domain: ab-experiment-mode
status: closed
started: 2026-05-26
closed: 2026-05-26
owner: ram-de
---

# Session: ab-experiment-mode — should Pythia become an A/B experimentation tool?

## Goal
Decide whether to evolve Pythia from a hypothesis-scoring tool into a tool that (a) simulates a full A/B experiment (treatment arm + control arm) and (b) doubles as a "plug-and-play" analyzer for real A/B test results run elsewhere. Frame the strategic tradeoff cleanly enough to pick a direction before any code.

## In Progress
— session complete. Strategic decision captured: Product B deferred to Phase 9, Product A deferred to post-Phase-4 revisit. ROADMAP.md updated. Scoping happens when Phase 4 (agent chat) is shipping and we've watched real PMs interpret agent transcripts.

## Completed
- [x] **Surfaced the bundling.** The original pitch packed two products into one sentence: Product A (A/B simulator extension — treatment arm + control arm + simulated lift) and Product B (plug-and-play analyzer for real A/B test data). Different strategic profiles, different competitive landscapes, different scope. Worth evaluating separately.
- [x] **Product B deferred (decision 2026-05-26).** No PM has asked for it; not in MVP scope. The plug-and-play A/B analyzer would put Pythia in Eppo/GrowthBook/Statsig territory and dilute the agent-simulation moat. If we ever build it, the natural home is **Phase 9 Layer-3 calibration** — "what we predicted vs what actually happened" — using real A/B data as the ground truth signal for tuning the simulator. Captured as a Phase 8-9 question, not a Phase 4 question.

## Next Steps
— session complete. **When Phase 4 (agent chat) is shipping, re-open a scoping session** for Product A:
- Control-arm artifact design (what the LLM gets prompted with to react to the *current* product). Probably an explicit "current-state product description" doc per capability, separate from the proposed-change prose. Possibly auto-derivable from the Feature Pack.
- Score-formula redesign: paired-bootstrap on per-agent delta? Welch's t-test on arm-level sentiment? Bayesian credible interval on the lift proportion? `/plan-eng-review` it before code.
- Paired vs independent sampling decision: same `(persona_id, sample_index, run_seed)` → same identity_seed in both arms (paired), or fresh draws (independent). Paired is the cleaner statistical comparison; independent matches real-A/B more closely. This is a `/plan-ceo-review` taste call.
- Cost: a 50-population sim becomes 100 agents (2× LLM cost + latency). Worth pricing before we sign customers.

## Key Files
(none yet — design conversation only)

## Key Context
The proposal as the founder framed it has three parts:
1. Wizard input change: percentage or absolute count for test + control groups.
2. Simulate BOTH arms: agents react WITH the change (treatment) and WITHOUT (control).
3. New Analysis tab interprets the simulated A/B AND accepts real A/B test data as input ("plug and play for real A/B tests too").

## For my cofounder
We're deciding whether Pythia stops being a hypothesis-scoring tool and becomes an A/B experimentation suite. This is a Phase-shift conversation. Outcomes range from "yes, do all of it now" to "yes but only the simulation half" to "tempting but no — finish Phase 4 first."
