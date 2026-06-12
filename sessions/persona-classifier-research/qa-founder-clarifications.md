# Founder Q&A — clarifications on the persona/benchmark analysis

Companion to `analysis.md`. Captures the founder discussion of 2026-06-11 in plain language — read this first if you want the 5-minute version.

## 1. Product intent: directional, never statistically significant

Founder clarification: Sidira is never intended to produce statistically significant results — only promising, directionally correct reads. **This matches the evidence exactly** (aggregate direction works, r=0.85; individual clones don't, r≈0.20). One trap to avoid: at big tech, only 8–33% of experiments win, so "always predict flat" is directionally correct 67–92% of the time while being useless. The directional claim must therefore be framed as *"we re-rank your backlog better than your current heuristics"* — measured against the always-flat baseline, not against zero. The bar is low (their own people predict below chance) but must be beaten demonstrably.

## 2. "How do 1,000 agents represent millions of users?"

You don't feed millions of users to agents — you sample, like a pollster. Precision scales with √(sample size), not population size (Gallup: 1,000 people → 250M adults, ±3%). Mechanics: fit the GMM on millions of rows (cheap, no LLM); the fitted mixture IS the compressed representation; draw ~1K–10K agents from it via Hamilton weights; each agent gets ONE user-level row (real anonymized, or synthetic sampled from the GMM — privacy-clean). "Individual conditioning" means each agent carries one user's texture, not one agent per user. Caveats: oversample rare valuable segments (whales) with weight correction; past a few thousand agents the noise floor is the LLM itself, not sampling error.

## 3. Win-rate math: yes, the uplift arithmetic is the pitch

Cutting 30% of the backlog (if all cuts are losers) lifts win rate p → p/0.7: 8%→11.4%, 33%→47%. That's a board-level number. Three refinements so it survives scrutiny: (a) the arithmetic assumes zero winners cut — and 2% of ideas drive ~75% of gains (Bing/Azevedo), so one buried 10× winner can make the filter net-negative; (b) the dodge is **re-rank, never eliminate** — likely winners ship first, the back of the queue is merely delayed; (c) translate uplift into dollars via test cost (engineering weeks + scarce test slots), not just hit rate.

## 4. "If we only re-rank, everything eventually gets tested — where's the savings?"

"Eventually" never arrives: backlogs grow faster than test capacity drains them, so the back of a re-ranked queue gets overtaken, goes stale, or its surface gets redesigned — de-facto elimination without Sidira owning the kill decision. The savings channels:
1. **Time-value of lift** (the big one): a winner moved from month 9 to month 1 banks 8 extra months of its metric improvement. Order is most of the value even with identical test sets.
2. **Cheaper individual experiments**: (i) *arm pruning* — simulate 6 button variants, real-test only the top 2 → traffic splits 2 ways not 6, answer in 2 weeks not 6; (ii) *bandit warm-start* — simulation as the opening prior, real traffic corrects it live (the LOLA architecture that beat both pure A/B and pure LLM); (iii) *pre-build iteration* — simulate 10 checkout mockups for dollars, build only the 2 survivors, saving the engineer-months that dominate experiment cost.
3. **For non-FAANG customers** traffic itself is scarce (10–20 powered tests/yr) — there, ranking decides what ever gets tested.

## 5. Agent chat ("talk to the agents from the test")

Verdict: **strongest product feature and weakest scientific claim simultaneously.**
- *Why valuable*: A/B tests say WHAT, never WHY; chat fills the explanation gap their platforms don't cover. Unique capability hiding in our paired-seed design: **the counterfactual interview** — the same agent identity experienced both control and treatment, so you can ask it what changed. No real-world UXR can do that. Make this the centerpiece.
- *Why dangerous*: an agent's explanation is a post-hoc rationalization, not a cause; LLMs confabulate fluent reasons for any outcome (hyper-rationality + caricature distortions). Chat also amplifies the fabricated-JTBD defect — agents will elaborate invented motivations persuasively.
- *Defenses*: (1) frame as hypothesis generator, never evidence; (2) ground answers in actual behavioral features, hedge proxy-derived motivations (→ survey fusion matters more if chat is flagship); (3) interview the panel, not the agent — cluster all 50 answers, show reason distributions tied to the weakness taxonomy; (4) benchmark the "why": predicted complaint themes vs realized post-launch complaints (reviews, tickets, UXR) — nobody validates explanations; second differentiator.
- *Positioning*: chat leads for mid-market; for Meta/Google it comes AFTER the blind track record — chat IS the "cool demo" those buyers discount.

## 6. "Are we doing away with personas?"

**No.** What's retired: the persona archetype as the *only* conditioning signal, and ARI-chasing as the goal. What personas still do (all load-bearing): (1) sampling backbone — the GMM is the compression layer that answers Q2; (2) half of every agent's prompt — the gestalt that makes an individual row coherent; (3) the unit of insight PMs can act on ("alienates high-frequency DashPass users, 44% of volume"); (4) the container where measured response priors accumulate (the long-term moat); (5) the legible cast for the chat feature. One line: **personas are the scaffolding, not the engine** — accuracy comes from individual conditioning + calibration + elicitation; personas make the system organized, explainable, and sellable.

Worked example (fee-transparency test): old way, 20 "Frugal Foodie" agents share one archetype sentence → one stereotype asked 20 times. New way, each agent = persona + one real row → the promo-code Android user says upfront fees kill browsing, the DashPass holder likes them. Same persona, opposite grounded reactions — within-group variety is where accuracy comes from; the persona still decided panel composition, framed the rows, phrased the verdict, and files the post-test learning.

## 7. What the analysis does and doesn't contain

Has: the full behavioral architecture (hierarchical conditioning, soft sampling, distribution elicitation, delta prediction, shrinkage) and the feature framework — decision rule: *a feature earns its place if it improves held-out experiment prediction, not cluster stability*; three distinct feature roles (clustering basis ≠ conditioning signal ≠ response priors); measured-vs-proxy flagging; survey fusion.
Missing (deliberately — depends on adoption decisions): actual prompt templates, the feature-pack+persona-pack → agent-context merge spec, step-by-step ablation protocol, multi-turn chat consistency mechanics, per-modality handling (screenshot vs copy vs pricing). → That's the **agent behavior spec**, the next session after the Now-items decision.

## 8. Benchmark inputs & the treatment-rendering gap (2026-06-12, full detail in analysis.md §6)

Q: public benchmarks need (existing state, proposed change, personas) — where do they come from? A: proposed changes are in the archives (headline texts, stimuli, message texts); existing state is reconstructable (Wayback Machine for Upworthy; survey/program frames elsewhere); **personas are the gap** — no public archive has user-level behavioral data, so Tier-0 artifacts 1–4 run on demographic-calibrated synthetic panels and validate the *simulation engine* only (an honest lower bound). **Hillstrom (64K customers, real RFM features) and Criteo Uplift (13M users) are the only public end-to-end tests of the full persona pipeline** → added as Tier-0 artifact #5. Q: did the analysis audit how the current-feature PRD / change PRD are ingested? A: it covers how the description should be used (unblinding, paraphrase ensembles, linting, OEC scoring) but did NOT audit the ingestion/rendering path — the **treatment-rendering layer** (state + change → what the agent reads) is a newly named component; it must be format-identical between benchmark and production (build it once, in the harness, first) and is now in scope for the agent behavior spec.

## 9. Agreed next steps

1. Founder reads `analysis.md` (§1, §4.1, §5 especially).
2. Adoption decision on the three "Now" items: simulator elicitation fixes; sidira-personas hygiene (soft posteriors, per-cluster Jaccard, holdout, tests); Tier-0 benchmark harness (green-light first if only one — it's the criterion everything else is judged on, and the start of the sales artifact).
3. On "go": (a) file tickets in sidira-personas + sidira-simulator as ram-de; (b) new session for the agent behavior spec.
4. Close this session, roll decisions into CONTEXT.md.
