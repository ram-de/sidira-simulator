---
type: session
domain: weighted_population
status: active
started: 2026-05-22
owner: rmkmar
---

# Session: weighted_population — Phase 2.5 weighted population sampling

## Goal
Replace `persona_sample_size` (a literal agent count) with `population_size` (modeled userbase size that gets stratified down to N actual agents), add per-agent `identity_seed` variance, and aggregate with proper confidence intervals — so simulation scores stop being a single point estimate against the top-6 personas.

## In Progress
- [ ] [#63](https://github.com/ram-de/pythia-simulator/pull/63) open — re-lands #62's P2 fix commit (`2da6502`) onto `main`. **Why a third PR:** #62 was based on `feat/2.5-population-sampler` and merged into that stale branch instead of auto-retargeting to `main` (GitHub only auto-retargets when the base branch is *deleted*). #63 cherry-picks the fix onto a fresh branch off main. 29/29 sampler tests green locally. Awaiting CI + `/codex review` + merge.

## Completed
- [x] Surveyed current state: `_top_personas_by_weight` truncates by head_count weight (not real stratification); 60 backend tests baseline.
- [x] Resolved the three open ROADMAP questions in chat: hybrid deterministic+optional-prose identity_seed; emit `behavioral_seeds` from pythia-personas v1.1 with simulator-side fallback; use Phase 4's persona-grouped table (#51) for the detail view (merge #10 into #51).
- [x] Created three new tickets: simulator [#57](https://github.com/ram-de/pythia-simulator/issues/57) (schema swap), simulator [#58](https://github.com/ram-de/pythia-simulator/issues/58) (population_sampler), pythia-personas [#4](https://github.com/ram-de/pythia-personas/issues/4) (behavioral_seeds in v1.1).
- [x] **#7 (Groq backoff) merged** as `54c2e61`. `_retry_on_rate_limit` wraps both GroqChat + AnthropicChat; exp backoff + jitter; cap 3 retries; structlog WARN. 4 new tests.
- [x] **#57 (schema swap) merged** as `f10cbe9`. SimulationRequest.population_size (1..10_000_000, `extra="forbid"`), Simulation.population_size/sampled_agent_count plumbed end-to-end. 11 new tests. Codex: 0 P1, 4 P2 (2 fixed, 2 deferred).
- [x] **MCP identity routing fixed:** added second MCP server `github_ramde` to `~/.claude.json` for `ram-de/*` writes. Routing rule documented in `.claude/skills/pythia-session/SKILL.md` § MCP identity routing.
- [x] Implemented **#58 (population_sampler)**. Hamilton largest-remainder allocation in `services/population_sampler.py`. Codex review: 1 P1 + 3 P2 (P1 + 2 P2 fixed; 1 P2 documented). 27 new tests.
- [x] **#58 merged via [#61](https://github.com/ram-de/pythia-simulator/pull/61)** as `041041e`. PR authored as `ram-de` via `mcp__github_ramde__create_pull_request` — MCP identity routing proven end-to-end.
- [x] **Codex P2 fixes on #61:** dedup persona ids + normalize-near-1 weights. Opened as **[#62](https://github.com/ram-de/pythia-simulator/pull/62)** stacked on `feat/2.5-population-sampler`. 2 new tests, `/codex review` clean (0 P1, 0 P2).
- [x] **#62 merged into `feat/2.5-population-sampler`** as `0fb3bbb` at 20:16 UTC — but that branch was already orphaned (#61 had merged to main at 19:17). **GitHub did NOT auto-retarget #62 to main** because auto-retarget only triggers when the base branch is deleted. Net result: commit `2da6502` (the actual fix) never reached main.
- [x] **Caught the gap on resume** by diffing `origin/feat/2.5-population-sampler ^main` — fix commit was missing from main. Cherry-picked `2da6502` to fresh branch `fix/2.5-sampler-codex-p2-to-main` off main, ran 29/29 sampler tests, opened **[#63](https://github.com/ram-de/pythia-simulator/pull/63)** with base=main.

## Next Steps
1. Wait for CI on [#63](https://github.com/ram-de/pythia-simulator/pull/63), run `/codex review`, merge.
2. After #63 merges: delete the orphaned `feat/2.5-population-sampler` and `fix/2.5-sampler-codex-p2` remote branches (close the confusion source).
3. **Founder rotates the PAT** that was pasted in chat during MCP setup (one-time security hygiene).
4. Start **#5 (identity_seed)** — design-heavy. Run `/plan-eng-review` before code (RNG seeding, fallback semantics, prompt-splicing each have real failure modes).
5. Then #6 (scoring CIs), #8 (degradation guard), then frontend (#9 + re-scoped #51).

## Key Files
- `backend/pythia_simulator/services/population_sampler.py` (Hamilton allocator — on main as of #61)
- `backend/pythia_simulator/services/simulation_runner.py` (orchestrator wiring — TODO, separate PR)
- `backend/pythia_simulator/services/scoring.py` (point-estimate scoring — #6 will add CIs)
- `backend/pythia_simulator/schemas/simulation.py` (population_size + identity_seed + behavioral_seeds fields landed in #57)
- `backend/pythia_simulator/adapters/llm.py` (Groq backoff — landed in #7)
- `frontend/app/simulations/new/page.tsx` (sample-size input → population-size input — #9 scope)
- `ROADMAP.md` § "Phase 2.5"

## Key Context
- ROADMAP locked: single input `population_size`, hard cap `min(population, MAX_AGENTS)` with `MAX_AGENTS` env default 50, per-agent identity_seed variance, Wilson CI on weakness frequencies + bootstrap on aggregate score.
- Open questions for #5: identity_seed rule-based vs hybrid; per-persona attribute schema source (pythia-personas v1.1 vs hand-roll); 50-agent detail-view UX (now leaning toward persona-grouped table from `docs/agent-chat-ui-spec.md`).
- Hard constraints: Groq backoff must precede 50-agent run (3 LLM calls × 50 = 150 bursts → 429 on free tier). Scoring degradation guard for >50% classification failures (today silently produces ~70).
- **Process lesson:** stacked PRs do NOT auto-retarget to main unless the base branch is *deleted*. For future stacks, either (a) delete the base branch before merging the upstream PR, or (b) plan to manually retarget post-merge, or (c) just open the second PR directly against main after the first merges. Documented in this session for future reference.

## For my cofounder
Three PRs landed on this sub-sprint:
- **#61 (population_sampler core)** — merged to main.
- **#62 (codex P2 fixes)** — accidentally merged into the now-stale feat branch, NOT main.
- **#63 (re-land of #62 fix on main)** — open, awaiting CI/codex/merge.

After #63 lands, main will have the complete, codex-clean sampler. Next major issue is **#5 (identity_seed)** which deserves a `/plan-eng-review` before any code.
