# #54 — Persona-group synthesis quality bar

**Status:** Design proposal. Locks the three decisions called out in `sessions/phase-4-agent-chat/context.md` before any code lands.
**Mode:** HOLD SCOPE — `docs/agent-chat-ui-spec.md` is locked. This doc fleshes out the synthesis line; it does not relitigate fan-out vs. synthesis-only.
**Input artifacts:** `docs/agent-chat-ui-spec.md` (Surface 2, lines 62-108), `services/prompt_composer.py` opener fix (#77), `feedback_codex_on_every_pr.md`.

---

## Why this is load-bearing

The synthesis is the FIRST thing the PM reads on `/simulations/[id]/personas/[persona_id]`. The per-agent replies are below. So:

- A bad synthesis stacks on top of N possibly-good replies — the PM forms their opinion from the summary, the replies become confirmation/disconfirmation evidence.
- It's the same failure mode #77 fixed at the agent layer ("Honestly, I'm not too thrilled…"), but **amplified** — one synthesis voice over N personas over M questions per session. Template-y synthesis = AI slop, lost trust, demo dead in the water.
- Fan-out exists to surface **within-persona disagreement**. A synthesis that hides disagreement behind "mixed feelings" defeats the spec's whole reason for not collapsing to a single LLM call.

---

## Decision A — Prompt strategy

### What "good" looks like

A good synthesis has four traits, in priority order:

1. **Counted, not vibed.** Leads with exact `N of M`. Never "most", "some", "a few".
2. **Names the cause, not the polarity.** Not "mostly negative" — "all three said the family browsing ritual is the point". The agents' STATED reason, not a sentiment label.
3. **Honest about splits.** When the group is genuinely divided, says so with named agents. No "mixed".
4. **Quotes the agents, doesn't editorialize.** No "this suggests", no "notably", no "interestingly".

### Examples (from the spec's domain)

✅ "3 of 3 said removing the Continue Watching rail breaks the family browsing ritual; rivka_002 also flagged the kid-profile shortcut sitting in that rail."
✅ "4 of 5 said the Smart Resume hero is faster than scrolling; jordan_disengaged disagreed — said he wants the rail back so he can rediscover shows he'd forgotten."
✅ "3 agents split: maya said the hero saves time, dom said it hides his promo-driven flow, lex said she doesn't know what it does yet."

❌ "The agents have mixed feelings about removing the rail."
❌ "Overall sentiment is negative, with most agents expressing concern."
❌ "This is an interesting hypothesis. Some users like it, others don't."
❌ "Most agents pushed back, though one noted a positive."

### Prompt structure (proposed)

```
You are summarizing N agent replies to one PM question. Your output is ONE
sentence (two only if a single agent flagged something genuinely distinct)
shown to the PM at the top of the page; the full agent replies appear below.

PM question:
{pm_question}

Agent replies:
[{agent_label_1}]: {reply_1}
[{agent_label_2}]: {reply_2}
...

Your synthesis MUST:
- Lead with "N of M" (exact count of agents sharing the core position).
- Name the SPECIFIC cause or scenario the agents pointed to — the noun, the
  flow, the moment — not a sentiment label.
- If the group genuinely splits with no majority, write:
  "N agents split: [label_a] said X, [label_b] said Y, [label_c] said Z."
- If one agent flagged something distinct that the others didn't, append
  " — [label] also flagged [thing]" as the second clause.

Do NOT:
- Hedge: "mixed", "varied", "overall", "somewhat", "generally".
- Editorialize: "this suggests", "indicates", "notably", "interestingly",
  "it appears".
- Use vague counters: "most", "some", "a few", "the majority".
- Restate the PM question.
- Invent consensus when replies are non-substantive — if every reply is
  evasive or off-topic, output exactly:
  "{N} agents gave non-substantive replies — re-ask with more specificity."
```

The prompt mirrors `prompt_composer.py`'s "polite-hedge templates to avoid"
pattern from #77 — explicit negative templates are how we steer LLMs that
otherwise drift to the nearest hedge.

### Post-process (mandatory, cheap)

Regex-extract the count claim (`(\d+) of (\d+)` or `(\d+) agents split`) and
verify against the actual number of replies passed in. **If the synthesis
claims "3 of 5" but the fan-out has 4 replies, the LLM hallucinated counts** —
retry once with `Your previous synthesis counted incorrectly. There were
exactly {N} replies. Try again.` appended. If retry still wrong, log
`synthesis.count_mismatch` and fall back to a deterministic template:
`"{N} agents replied; see individual answers below."` Never ship a wrong
count.

---

## Decision B — Eval rubric

### Offline rubric (pre-ship gate)

Build `backend/tests/test_persona_group_synthesis.py` with 8-12 fixture
scenarios spanning every shape we expect in production:

| Fixture | Shape | Why it's in the suite |
|---|---|---|
| `unanimous_negative` | 3 agents, same complaint | Common case |
| `unanimous_positive` | 3 agents, same praise | Inverse common case |
| `split_3_2_with_cause` | 5 agents, 3 vs 2 with named reasons | Healthy disagreement |
| `outlier_4_vs_1` | 5 agents, 4 align + 1 distinct | Must name the outlier |
| `three_way_split` | 3 agents, 3 different positions | No majority — must list all three |
| `same_polarity_different_cause` | 4 agents all negative for different reasons | Must NOT collapse to "all negative"; must name the divergent causes |
| `non_substantive_replies` | All "I'm not sure" / refusals | Must emit the diagnostic, not fake consensus |
| `one_long_one_short` | 2 agents, one paragraph + one sentence | Must not bias toward the verbose one |
| `agent_referenced_specific_flow` | 3 agents, one names a Figma component by id | Should surface that specificity in synthesis |
| `agent_contradicted_self_in_reply` | 1 agent reply has both pros and cons | Synthesis should pick the dominant stance, not pretend it's a split |

Each fixture asserts against a **trait rubric**, not an exact string:

```python
@dataclass
class SynthesisRubric:
    must_match_regex: list[str]      # e.g. [r"\b3 of 5\b"]
    must_contain_any: list[str]      # at least one of these noun phrases
    must_not_contain: list[str]      # hedges/editorial fillers — none allowed
    must_name_agents: list[str]      # specific agent_labels that should appear
    max_sentences: int               # default 2
    require_count_accuracy: bool     # post-process counter check
```

Globally banned phrases (applied to every fixture):
`["mixed feelings", "overall", "somewhat", "generally", "this suggests", "indicates", "notably", "interestingly", "it appears", "the majority", "most agents", "some agents"]`

Run the actual synthesis LLM (not a mock) against each fixture. Cost: 12
calls × ~$0.005 = ~$0.06 per suite run. Cheap enough to run on every CI.

**Pre-ship gate:** all 12 fixtures pass. If any banned-phrase fixture
regresses on a prompt change, CI blocks merge.

### LLM-judge pair eval (optional, for prompt iteration)

When iterating on the prompt, generate two syntheses per fixture (current
prompt vs. candidate prompt) and have an LLM judge pick the better one
against a brief rubric. Use to A/B prompt variants without hand-grading every
iteration. Not required for the v1 ship — defer to follow-up.

### Online signal (post-ship)

#56 calibration thumbs apply to the synthesis line itself (not just
individual agent replies). Phase 9 reads the👍/👎 rate. This is the only way
to catch "the prompt is fine on fixtures but the LLM drifts on real
hypotheses" — the rubric is necessary but not sufficient.

---

## Decision C — Contradictory replies

The spec explicitly chose fan-out specifically to **surface** within-persona
disagreement. Synthesizing it away breaks the design intent.

Three failure modes and the response to each:

| Mode | Example | Response |
|---|---|---|
| **Genuine N-way split, no majority** | 3 agents, 3 distinct positions | `"3 agents split: maya said X, dom said Y, lex said Z."` Always list every position. Never fold into "mixed". |
| **Majority + outlier** | 4 align, 1 distinct | `"4 of 5 said X because [reason]; [outlier_label] disagreed — [their reason]."` Outlier named, not paraphrased away. |
| **Non-substantive replies** (LLM degenerated — all agents reply "I'm not sure" or refuse the framing) | n=3, all evasive | `"3 agents gave non-substantive replies — re-ask with more specificity."` This is a DIAGNOSTIC, not a synthesis. Do not invent consensus. |

The non-substantive case is the dangerous one — without an explicit branch,
the LLM will hallucinate a synthesis from the evasion ("the agents seem
uncertain about the change"). The prompt's explicit instruction prevents
this; the rubric's `non_substantive_replies` fixture catches regressions.

### What synthesis is NOT allowed to do

- **Refuse.** Synthesis always emits a sentence (one of the 4 shapes above:
  consensus / split / outlier / non-substantive diagnostic).
- **Editorialize beyond what the agents said.** "This suggests the team
  should reconsider…" — out. The PM does the interpretation.
- **Hide a minority position when it's substantive.** A 1-of-5 that names a
  specific flow the others didn't think of is signal, not noise — it gets
  the second-clause callout.

---

## Implementation tasks (synthesized for `/autoplan` aggregation)

- [ ] **T1 (P1, human: ~2h / CC: ~15min)** — `services/persona_group_synthesis.py` — write the synthesis service.
  - Surfaced by: Decision A (prompt + post-process).
  - Files: `backend/pythia_simulator/services/persona_group_synthesis.py` (new).
  - Verify: unit tests in T2 pass.

- [ ] **T2 (P1, human: ~3h / CC: ~25min)** — Synthesis rubric eval suite.
  - Surfaced by: Decision B (pre-ship gate).
  - Files: `backend/tests/test_persona_group_synthesis.py` (new), plus 8-12 fixture JSON files under `backend/tests/fixtures/synthesis/`.
  - Verify: `pytest backend/tests/test_persona_group_synthesis.py -v` — all fixtures green.

- [ ] **T3 (P1, human: ~1h / CC: ~10min)** — Wire synthesis into the persona-group route.
  - Surfaced by: spec line 101-105 (backend contract).
  - Files: `backend/pythia_simulator/api/persona_groups.py` (new) — `POST /simulations/{sim_id}/personas/{persona_id}/messages`.
  - Verify: integration test sends PM message, asserts response shape `{synthesis, per_agent: [...]}` and asserts each agent's `AgentMemory` log got the PM turn + agent turn (identity-continuity preserved).

- [ ] **T4 (P1, human: ~30min / CC: ~5min)** — Persist synthesis to per-persona-group log.
  - Surfaced by: spec line 107 (`turns.jsonl` location).
  - Files: extend `adapters/repositories.py` with `PersonaGroupTurnsRepo` or similar.
  - Verify: after a fan-out, `customers/<id>/simulations/<sim_id>/persona_groups/<persona_id>/turns.jsonl` contains the synthesis + the PM message; agent replies live on individual agents (not duplicated here).

- [ ] **T5 (P2, human: ~30min / CC: ~5min)** — Count-accuracy post-process + retry-once + structlog warn on mismatch.
  - Surfaced by: Decision A post-process section.
  - Files: in `persona_group_synthesis.py`.
  - Verify: synthetic fixture where LLM is mocked to return a wrong count → assert retry happens, second response used; if still wrong, deterministic fallback string used and `synthesis.count_mismatch` logged.

- [ ] **T6 (P3, human: ~2h / CC: ~15min)** — LLM-judge pair eval harness (optional, prompt-iteration tool only).
  - Surfaced by: Decision B follow-up.
  - Files: `backend/scripts/synthesis_judge_eval.py` (new).
  - Verify: manual — generates a side-by-side report.

**P1 = blocks #54 ship. P2 = ships same branch. P3 = follow-up TODO.**

---

## Open items (parked, not blocking)

- **Synthesis-line length cap** (spec open Q line 150): proposal is `max_sentences=2` enforced in rubric. The second sentence is reserved for outlier callout or non-substantive diagnostic. Pick when implementing.
- **Agent labels in synthesis** — use persona_id-derived short labels (`maya`, `dom`, `lex_a`, `lex_b` when n>1 per persona) rather than UUIDs. Falls out of T1.
- **Multi-turn synthesis** — synthesis runs only on the latest PM turn's fan-out replies. Historical turns are not re-synthesized. Confirmed out of scope for v1.

---

## NOT in scope

- Cross-persona synthesis — explicitly rejected by spec line 138-139.
- Synthesis calibration loop — that's #56 + Phase 9.
- Streaming synthesis (drip-render as fan-out replies arrive) — v2; v1 awaits all replies then synthesizes.
- Synthesis editing or branching — append-only per identity-continuity invariant.

---

## What this design buys us

If T1+T2+T3+T4 ship and the rubric stays green:

1. The synthesis line at the top of the persona-group page survives the same
   ship-then-dogfood pattern that surfaced #77/#78 — the rubric catches the
   template-drift class of bug before the PM sees it, and #56 catches the
   real-world drift the rubric missed.
2. The PM's first-glance impression of a persona-group answer is grounded in
   exact counts and named causes, not vibes.
3. Disagreement within a persona is surfaced, not hidden — which is the
   reason fan-out exists.

Cost of getting this wrong: the same "templated AI slop, lost trust" failure
mode as #77, but multiplied by personas × questions × demos. The rubric is
cheap insurance.
