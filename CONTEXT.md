# CONTEXT — Current Sprint Narrative

**This file is the team's shared running context.** Both founders read it. AI agents read it before picking up work. Keep it short (2–3 screens), keep it current.

**Last updated:** 2026-05-21

---

## What just shipped

✅ **Magic Moment Sprint — Phases 2 + 3 done in one sitting (2026-05-21).**
A PM can submit a hypothesis through `/simulations/new`, see 6 personas react via real Groq LLM calls, and get a confidence score + 3 diagnosed weaknesses + 3 refinement suggestions rendered live on `/simulations/[id]`. Verified end-to-end with sim `63c778c8` returning score 30/100.

Waves 0–6 landed:
- Wave 0: 8 architecture decisions locked via `/plan-eng-review` (commit `6de33f8`)
- Waves 1–3: Postgres schema, Repository Protocol pattern, end-to-end POST /simulations (commits `69b34d8`, `cbabb2c`)
- Wave 4: Scoring + refinement services with locked `0.6 sentiment + 0.4 (1-weakness)` formula. Codex review fixups applied (`8c03641`, `71325b9`, PR #1)
- Wave 5: Frontend submit + result view + live polling, built via 2 parallel sub-agents (`808f689`, PR #2)
- Wave 6: T12 e2e demo, `/qa`, `/review`, `/retro`. Discovered + fixed CORS bug (`2713752`), shipped the simulation list view (`6b458a9`), three review fixups (`b39db2b`).

60/60 backend tests passing. Frontend typecheck clean. All on `main`.

Retrospective: `git show b39db2b` in conversation history, plus the lessons captured in the next section.

Current gaps live in the [GitHub Project](https://github.com/users/ram-de/projects/) under their respective Phase tags (2.5 / 4 / 4.5 / 5). `ROADMAP.md` has the strategic "where we are today" view.

---

## What's next

**Phase 2.5 — Weighted Population Sampling.** Replace `sample_size` with `population_size`. Stratified allocation via largest-remainder. Per-agent identity_seed for variance. Confidence intervals on score + weakness frequencies.

Decisions locked:
- Single input: `population_size` (PM specifies "imagine N users facing this hypothesis")
- Cap: `min(population, 50)` agents actually run; configurable via env var
- Variance: per-agent `identity_seed` blob (age band, locale band, tenure, recent gripe) injected into persona prompt
- Aggregation: Wilson CI on weakness frequencies, bootstrap on aggregate score

Open questions to brainstorm before code:
1. `identity_seed` — rule-based draws or hybrid (deterministic fields + LLM-generated prose)?
2. Per-persona attribute schema — emit from pythia-personas v1.1 or hand-roll in simulator?
3. Detail-view UX for 50 agents — virtualized list or grouped by persona?

Hard constraints:
- Groq rate-limit backoff lands BEFORE the 50-agent run (3 LLM calls per agent × 50 = 150 bursts will 429 the free tier)
- Scoring degradation guard for >50% classification failures (today's code silently produces a misleading ~70 when everything fails)

Tickets to start with live in the [GitHub Project](https://github.com/users/ram-de/projects/) under Phase 2.5.

---

## Lessons we keep paying attention to

From the Magic Moment retro:
1. **Lock decisions first, code second.** `/plan-eng-review` before any phase >1 day of work. Eliminates mid-implementation second-guessing.
2. **Cross-model review at PR boundaries.** `/codex` review caught 5 P2/P3 issues in the scoring formula in 19 minutes, before Wave 5 doubled down on a flawed foundation.
3. **Parallel sub-agents work when the contract is locked.** Wave 5's 2,468 lines of frontend shipped in ~1h05m because the API contract was decided in Wave 0.
4. **`/qa` before the demo, not after.** Curl-based smoke tests miss browser-origin bugs (CORS).
5. **Name placeholders honestly in code.** A function called `_sample_personas` that doesn't sample is a lie. Future-you blames past-you.

---

## How to use this file

- **Updating this file is the last step of every sprint.** "What just shipped" advances, "What's next" gets refreshed from ROADMAP, "Lessons" gets at most 1–2 new entries.
- **Don't dump scratch notes here.** Personal scratch lives in your own notes app or Obsidian vault. CONTEXT.md is the shared, durable thread.
- **Co-founder + AI agents read this first** when picking up work. Make sure the next person walking in cold can orient in 2 minutes.
