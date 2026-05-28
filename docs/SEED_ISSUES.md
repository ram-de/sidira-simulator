# GitHub Project — Seed Issues

> Historical note: this was the one-time project-board seed list. Current tickets live directly in the Sidira GitHub Project; old repo names and early-domain placeholders in this file are preserved as historical setup context.

This file is the one-time seed list for the Sidira GitHub Project board. After bulk-creating these issues, delete this file (or keep it as a historical record). All future tickets get created directly in the Project.

## How to create the Project

1. Go to https://github.com/users/ram-de/projects → New project → Board template
2. Name: **Sidira**
3. Visibility: Private (or Public if shipping in the open)
4. Add the three repos as sources: `ram-de/pythia-simulator`, `ram-de/pythia-personas`, `ram-de/pythia-crawler`
5. Add custom fields:
   - **Phase** (single select): 2.5, 4, 4.5, 5, 6, 7, 8, 9, 10
   - **Component** (single select): backend, frontend, schema, infra, docs, eval
   - **Status** (single select; default GitHub fields are fine): Backlog, Next, In progress, In review, Done
6. Default views:
   - "Now" — filter by Status = In progress OR Next
   - "Phase 2.5" — filter by Phase = 2.5
   - "By repo" — group by Repository
7. Add @co-founder as a collaborator

## Issues to create

Copy-paste each block below into a new issue in the indicated repo. Set Phase / Component fields after creation.

---

### Phase 2.5 — Weighted Population Sampling

#### Issue: `feat(schema): replace persona_sample_size with population_size`
**Repo:** pythia-simulator
**Phase:** 2.5
**Component:** schema
**Body:**
The `SimulationRequest` field `persona_sample_size` is a literal agent count. Replace with `population_size` — the customer's modeled userbase size, which the simulator then stratifies down to an actual sample.

Schema changes:
- `SimulationRequest.population_size: int` (ge=1, le=1_000_000)
- `Simulation.population_size: int`
- `Simulation.sampled_agent_count: int`

Remove the existing `persona_sample_size` field. Update frontend wizard accordingly (separate issue).

**Acceptance:**
- Pydantic schema accepts `population_size`, rejects old field
- OpenAPI export regenerated; frontend types regen clean
- Backend tests updated

---

#### Issue: `feat(services): population_sampler with largest-remainder allocation`
**Repo:** pythia-simulator
**Phase:** 2.5
**Component:** backend
**Body:**
Implement `services/population_sampler.py` that takes a `PersonaPack` and a `population_size`, and returns a list of `(persona_id, n_agents)` tuples using the Hamilton largest-remainder method against the pack's weight scheme (default: head_count; allow override).

`min(population_size, MAX_AGENTS)` caps actual agent count. `MAX_AGENTS` env var, default 50.

**Acceptance:**
- Unit tests for allocation math (weights × population = correct allocations, sums to sampled count, ties handled)
- Population=1000 with persona weights `[0.30, 0.25, 0.20, 0.15, 0.05, 0.05]` produces `[15, 13, 10, 7, 3, 2]` (sums to 50) within ±1 rounding
- Edge case: population=10 with 6 personas runs all 6 agents (no clamp)

---

#### Issue: `feat(services): identity_seed for per-agent variance`
**Repo:** pythia-simulator
**Phase:** 2.5
**Component:** backend
**Body:**
Per-agent personal context that makes agents within a persona feel distinct. Injected into the identity prompt alongside the persona profile.

Hybrid approach:
- **Deterministic fields:** age band, locale band, tenure on product, current state (active/dormant/etc.), recent gripe — sampled from a per-persona schema using `(persona_id, sample_index, seed)` as RNG seed for reproducibility
- **Optional LLM prose:** one short paragraph synthesized from the deterministic fields, cached by `(persona_id, identity_seed_hash)`

`AgentInstance.identity_seed: dict` — frozen at creation (memory invariant: chat-time agent = simulation-time agent).

**Open question (block this ticket on):** does per-persona attribute schema live in the pack (pythia-personas v1.1 emits it) or hand-rolled in simulator? Decide in brainstorm before writing code.

**Acceptance:**
- 50 agents within a persona produce 50 distinct identity_seeds
- Re-running the same simulation with same seed produces the same identities (reproducibility)
- Agent prompts visibly differ between agents of the same persona

---

#### Issue: `feat(scoring): Wilson CIs on weakness frequencies, bootstrap on aggregate score`
**Repo:** pythia-simulator
**Phase:** 2.5
**Component:** backend
**Body:**
Replace point estimates with confidence intervals.

- Weakness frequencies: Wilson interval for binomial proportions (95% CI default, configurable)
- Aggregate score: bootstrap (1000 resamples by default) over per-agent contributions

Schema updates:
- `Weakness.frequency: float`, `Weakness.ci_low: float`, `Weakness.ci_high: float`
- `SimulationResult.confidence_score_ci: tuple[float, float]` (or expand into a small object)

**Acceptance:**
- Known-input unit tests produce expected CIs (compare against scipy.stats.binom for Wilson)
- 50-agent simulation produces a CI band that visibly differs from a 6-agent one
- Frontend renders `30 ± 4 (95% CI)` instead of bare 30

---

#### Issue: `fix(adapters): Groq rate-limit backoff with jitter`
**Repo:** pythia-simulator
**Phase:** 2.5
**Component:** infra
**Body:**
Today's `adapters/llm.py` will 429 the Groq free tier when Phase 2.5 raises concurrent LLM calls from 6 to 50.

Add exponential backoff with jitter on 429 responses. Cap at 3 retries. Log retries via structlog at WARN level.

**Acceptance:**
- Synthetic test that simulates a 429 → 200 sequence succeeds without raising
- 50-agent simulation runs cleanly against Groq free tier (or, if free tier still 429s after backoff, log clear guidance to upgrade)

---

#### Issue: `feat(scoring): degradation guard for >50% classification failures`
**Repo:** pythia-simulator
**Phase:** 2.5
**Component:** backend
**Body:**
Currently when weakness/sentiment classifications fail (LLM timeout, JSON parse error), `aggregate()` substitutes neutral values. If every classification fails, the score ends up ~70 (neutral × shrinkage with no flags) — misleadingly high for a totally degraded run.

Add: if `(failed_classifications / total_classifications) > 0.5`, prepend a `underpowered_design` weakness AND discount the confidence_score by 30%.

**Acceptance:**
- Unit test with all-failed analyses produces score < 50 with underpowered_design weakness present
- Unit test with 30% failed analyses still produces a normal score
- Boundary test at exactly 50%

---

#### Issue: `feat(ui): wizard — Sample size field → Population field`
**Repo:** pythia-simulator
**Phase:** 2.5
**Component:** frontend
**Body:**
Replace the `sample_size` number input on `/simulations/new` with a `population_size` input. Helper text explains stratification: "We'll sample up to 50 agents in proportion to your persona weights and infer the full population from them."

Add a small "Sampled agents: 50" sub-line that updates as the user types population.

**Acceptance:**
- Form submits `population_size` (not `persona_sample_size`)
- Helper text matches the new copy
- Min 1, max 10_000_000 with sensible validation

---

#### Issue: `feat(ui): detail view — CI rendering on score + weakness bars`
**Repo:** pythia-simulator
**Phase:** 2.5
**Component:** frontend
**Body:**
Update `/simulations/[id]` to render:
- Score: `30 ± 4 (95% CI)` with a faded band around the big number
- Weakness percentages: bar with CI whiskers (e.g., `67% [63–71%]`)
- Banner: "Population: 1000 (sampled: 50 in proportion)"
- Agent list: virtualized table OR grouped-by-persona ("Discount-driven restaurant regular × 15") — pick one in design phase

**Acceptance:**
- CI band visibly different at N=6 vs N=50
- Agent list scrolls smoothly with 50 entries
- Population banner copy is unambiguous

---

### Carried forward from Magic Moment retro

#### Issue: `infra: CORS prod allowlist via per-customer subdomain`
**Repo:** pythia-simulator
**Phase:** 5
**Component:** infra
**Body:**
Today's CORS default (`localhost:3000,127.0.0.1:3000`) works for one developer. Multi-tenant SaaS needs per-customer subdomain logic.

Design before code: do we use a wildcard pattern (`*.pythia.app`)? A regex? An allowlist looked up per request from Postgres?

**Acceptance:**
- Customer subdomain origins resolve to allow
- Other origins are rejected with the standard CORS error
- Localhost still works in dev mode

---

#### Issue: `feat(memory): Postgres handover — retire InMemorySimulationRepo from prod path`
**Repo:** pythia-simulator
**Phase:** 5
**Component:** backend
**Body:**
Currently the dev backend uses `InMemorySimulationRepo` which loses state on restart. The list view, chat history, and any cross-session feature dies with the process.

Wire `PostgresSimulationRepo` as the prod path. Keep InMemory as the test-only path.

**Acceptance:**
- Backend restart preserves simulation list
- Test suite still uses InMemory and runs in <1s

---

#### Issue: `feat(ui): agent chat surface — the defining feature`
**Repo:** pythia-simulator
**Phase:** 4
**Component:** frontend
**Body:**
The `/agents/{id}` route exists as a stub. Wire the chat UI:
- Show frozen identity + initial reaction at top (collapsible)
- Append-only message thread below
- POST `/agents/{id}/messages` to send + receive
- Identity-continuity guarantee preserved (no re-instantiation from template)

The backend memory model (`AgentMemory` with frozen identity + frozen reaction + appendable log) is already in place. This is mostly frontend work + one backend endpoint.

**Acceptance:**
- PM submits a sim, opens an agent, asks "why did you react that way?" and gets a coherent in-character reply
- Conversation persists in R2 (and Postgres metadata) after page reload
- Chat is responsive on mobile (<640px)

---

#### Issue: `chore(docs): rename _sample_personas to _top_personas_by_weight`
**Repo:** pythia-simulator
**Phase:** 2.5
**Component:** docs
**Body:**
The function `simulation_runner.py:_sample_personas` doesn't sample — it ranks personas by `head_count` weight and truncates. Misleading name. Rename to `_top_personas_by_weight` so future-you stops believing the codebase is calibrated when it isn't.

This becomes moot once `population_sampler.py` replaces it in Phase 2.5 — but for any window before that lands, the rename is honest.

**Acceptance:**
- Function renamed; all call sites updated
- 60 backend tests still pass

---

### pythia-personas — Round 2 enrichment

#### Issue: `feat(adapter): Round 2 source columns — Pricing PSM, loyalty, Hub Notifications`
**Repo:** pythia-personas
**Phase:** 2.5 (optional dependency)
**Component:** backend
**Body:**
Round 1 took stability from 0.439 → 0.670 via Round 1 enrichment. Round 2 candidates flagged in the project context:

- `PRICE_SENSITIVITY_SCORE_PSM`, `PROMO_SENSITIVITY_MODEL_SCORE`, `IS_LOW_ROI_CX`
- All loyalty fields: `HAS_REDEEMED_*`, `POINTS_*`, `ROAS`, `LOYALTY_MEMBER_AOV`, `TOTAL_REDEMPTIONS*`
- `UPSS_LIFESTAGE_ATTRIBUTE`, `UPSS_CHURN_ENGAGEMENT_SCORES`
- Notifications Hub: `HUB_NOTIFICATIONS_SENT`, `HUB_VIEW_TO_CLICK_RATE`, `HUB_REVISIT_RATE`

**Acceptance:**
- Stability >0.75 on a Round 2 run
- P03 (DashPass Healthy) and P06 (Discount-Driven Restaurant) each split into 2+ sub-personas

---

#### Issue: `feat(schema): Persona Pack v1.1 with per-cluster stats`
**Repo:** pythia-personas
**Phase:** 2.5 (enables better simulator variance)
**Component:** schema
**Body:**
Today's pack emits centroid + name + description per persona. Phase 2.5 of simulator wants per-cluster *stats* (means, variances, distributions of key attributes) to draw richer identity seeds from. Optional dependency — the simulator can hand-roll attribute schemas if this doesn't land in time.

**Acceptance:**
- `PersonaPack.schema_version = "1.1"`
- Each persona carries a `cluster_stats: dict` with mean+std for top-N features
- Backward-compat: simulator can read v1.0 packs without `cluster_stats`

---

### Crawler — backlog (when first customer signs)

#### Issue: `feat: Playwright walker (Phase 2)`
**Repo:** pythia-crawler
**Phase:** 7 (first customer)
**Component:** backend
**Body:**
The Phase 2 walker that explores a customer's sandbox by role (guest / member / premium) and emits the raw observations the Phase 3 synthesizer turns into PRDs.

Don't start until a real customer has a product to crawl — the Acme sample is sufficient until then.
