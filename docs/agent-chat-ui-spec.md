# Agent Chat UI — design spec (Phase 4)

The defining feature: after a simulation, a PM can talk to the agents that participated. This document is the source of truth for the three interaction surfaces and the backend contract they assume. ROADMAP Phase 4 implements it.

> **Status:** Design locked. Implementation tickets in the [Pythia GitHub Project](https://github.com/users/ram-de/projects/), Phase = 4.

---

## The three surfaces

```
/simulations/[id]                    →  Result table (the landing page after a run)
  └── per-persona row → opens persona-group chat
       └── per-agent row → opens individual chat at /agents/[id]
/agents/[id]                         →  Individual-agent chat (identity-frozen)
```

The PM's natural path: run a sim → land on the result table → notice a persona reacting badly → ask the *group* a clarifying question ("walk me through Friday night") → if one specific agent in the group says something interesting, drill into them → continue with the individual.

### Why three surfaces, not one

A flat list of N reactions doesn't scale past 6 agents. Grouping by persona collapses the cognitive load (5-6 personas, not 50 agents) and matches how PMs actually think — they reason about user segments, not individuals. The individual surface stays because some agents will say something so specific it's worth a follow-up; collapsing everything to the persona level would lose that.

---

## Surface 1 — Result table

**Lives at:** `/simulations/[id]` (replaces the current "Agents that participated" section).

**Replaces:** the current bare list of 8-char agent UUIDs. That list is not a result, it's debug output.

**Layout:** a table grouped by persona. One sticky row per persona (the "group header"), expandable into one row per agent within that persona.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Persona                       │ N │ Sentiment │ Top quote                  │  │
├──────────────────────────────────────────────────────────────────────────────┤
│ ▶ Daily binge marathoner       │ 1 │ ▮▮▮▮▯ +  │ "Finally — just play the…" │ 💬 │ ← group row
│ ▶ Weekend family movie night   │ 1 │ ▮▮▯▯▯ -  │ "Where did the row go?"    │ 💬 │
│ ▼ Niche genre loyalist         │ 1 │ ▮▮▮▯▯ ~  │ "Doesn't fix my problem."  │ 💬 │
│     └ noor — niche genre…      │   │ neutral  │ "Doesn't fix my problem."  │ 💬 │ ← agent row
│ ▶ Background / second-screen   │ 1 │ ▮▮▮▮▯ +  │ "One less remote tap."     │ 💬 │
│ ▶ New trialer (first 14 days)  │ 1 │ ▮▮▯▯▯ -  │ "I keep getting pinned…"   │ 💬 │
│ ▶ Price-sensitive lapser       │ 1 │ ▮▮▮▯▯ ~  │ "Not why I might cancel."  │ 💬 │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Columns:**
- **Persona** — name from the Persona Pack. Caret expands.
- **N** — number of agents in this persona that participated (will be >1 when Phase 2.5's weighted sampling lands; today usually 1 per persona).
- **Sentiment** — five-step bar (`--, -, ~, +, ++`), derived from the same per-agent classification the scoring service already produces. Group sentiment is the order-weighted average of its agents.
- **Top quote** — pinned to the agent's frozen initial reaction. For the group row: the most-cited or longest verbatim across the group; for the agent row: their own opener. Click expands inline (no nav).
- **💬** — opens the chat surface. On a group row → persona-group chat. On an agent row → individual chat.

**Empty / failure states:**
- If an agent's reaction failed, their row renders as `failed — <error>` with no chat button.
- If the whole sim failed, the table doesn't render — keep the existing failure card.
- Live (mid-sim) state: rows appear as agents complete; sentiment column is `—` until classification finishes for that agent.

---

## Surface 2 — Persona-group chat

**Lives at:** `/simulations/[id]/personas/[persona_id]` (new route).

**What it is:** a chat surface against the *group* of agents that share a persona. The PM types one question; the system fans out to every agent in the group, collects responses, and presents them side-by-side with a one-line synthesis at the top.

This is **fan-out, not synthesis-only.** Each agent answers individually; we surface all answers so the PM sees disagreement within the persona (which would otherwise hide behind a mean). A short synthesis line ("3 of 3 said the rail removal would make Friday harder; one suggested keeping a small ⋯ menu") is generated *after* the fan-out from the answers themselves — it's a summary of real responses, not a replacement for them.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ← Result table                                                                │
│                                                                               │
│ Weekend family movie night (n=1)                                              │
│ Hypothesis: Replace Continue Watching rail with a Smart Resume hero…         │
│ Initial sentiment: negative                                                   │
│                                                                               │
│ ┌─[ chat ]──────────────────────────────────────────────────────────────────┐│
│ │  PM: "If the rail is gone from the top of home, how do you decide what    ││
│ │       to watch tonight? Walk me through Friday."                          ││
│ │                                                                            ││
│ │  Synthesis (3 of 3 agents): All three said the ritual of browsing as a   ││
│ │  family is the point — collapsing it to one hero card breaks that.       ││
│ │                                                                            ││
│ │  [rivka_001]  We always scroll the row together. If it's gone we'll just ││
│ │               watch The Office reruns again.                              ││
│ │  [rivka_002]  …                                                            ││
│ │  [rivka_003]  …                                                            ││
│ │                                                                            ││
│ │  PM: …                                                                     ││
│ └────────────────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────────┘
```

**Identity-continuity guarantee (preserved):** each agent in the group is still the same frozen agent that ran in the simulation. Persona-group chat does NOT create a new aggregate entity. Each PM message is appended to *every* participating agent's individual conversation log, and the agent's reply is what the individual would have said. Drilling from a group answer into the individual chat surface shows the same turn already present.

**Why this matters:** if we synthesized at the LLM layer instead of fanning out, we'd lose the audit trail and we'd lose drill-down. The PM should always be able to click on any group answer and land on the specific agent who said it.

**Cost note:** fan-out scales with `N` agents per persona. At today's `N=1` it's identical to single-agent chat. At Phase 2.5's `N=8-10` per persona we'll need (a) Groq rate-limit backoff and (b) a "compose then send" UX (the PM writes once; the fan-out is one request from their perspective).

**Backend contract:** `POST /simulations/{sim_id}/personas/{persona_id}/messages` →
- fans out to each agent in the group, awaits all,
- writes each agent's turn via `AgentMemory.append_turn`,
- computes the one-line synthesis as a separate LLM call against the just-completed answers,
- returns `{synthesis: str, per_agent: [{agent_id, content}]}`.

The synthesis is **not** persisted on any individual agent — it lives in a per-persona-group conversation log at `customers/<id>/simulations/<sim_id>/persona_groups/<persona_id>/turns.jsonl`.

---

## Surface 3 — Individual-agent chat

**Lives at:** `/agents/[id]` (replaces today's stub).

**Layout, top to bottom:**
1. **Identity card** — pinned. Persona name, persona description, the agent's behavioral_snapshot key fields (3-4 of them), `lifestage`. Read-only.
2. **Initial reaction** — pinned. Verbatim from the simulation, with the hypothesis prose immediately above it so the PM has both in view.
3. **Chat** — scrollable. PM messages and agent replies. Newest at the bottom; auto-scroll on new turn. Each agent reply is *appended* to the conversation log on the backend; identity is never re-instantiated.

**Identity-continuity guarantee:** confirmed by `AgentMemory.build_replay_messages` — every reply is generated with the frozen identity_prompt + the frozen initial_reaction + the full conversation log. The `_CHAT_GUARD_PREFIX` keeps the model in character.

**Calibration ("realistic / not realistic" flags):** out of scope for the v1 chat UI. Tracked separately as Phase-4 ticket (see ticket list). The hook into `AgentFeedbackRepo` exists; the UI affordance is the late add.

---

## Reusable primitives across surfaces

- **Identity card component.** Same component on `/agents/[id]` (pinned, top) and on the persona-group page (pinned, top, but showing the persona aggregate instead of an individual). Single source of truth.
- **Chat composer.** Shared between persona-group and individual surfaces. Handles enter-to-send, multi-line, disabled state during in-flight, error toast.
- **Message bubble.** Shared. Prop: `author` (PM / agent / system synthesis / error).
- **Sentiment chip / bar.** Shared between result table cells and the persona-group header.

---

## What this surface does NOT do

Decisions we're making explicitly, so we don't drift into them later:

- **No cross-persona chat.** "Talk to everyone who reacted badly" is tempting; we're rejecting it for v1 because there's no honest aggregation across personas (they have different weights and different sample sizes). Use the per-persona surface and read across.
- **No agent-to-agent chat.** Mirofish does this; we don't. See `docs/mirofish-prior-art.md` "Inter-agent socialization" — Pythia's confidence math assumes independent reactions.
- **No "regenerate" or "branch" of an agent's reply.** Identity-continuity means the conversation log is append-only. If a reply is wrong, the PM disagrees in the next turn — they don't rewrite history.
- **No proactive agent messages.** Agents reply only when asked. They don't surface "you might also want to know X" — that would break the "I'm the user, you're the PM" frame.

---

## Open questions (parked, not blocking design)

- Sentiment chip — five-step or three-step? Today's scoring service emits five-class; UI may collapse to three for legibility.
- Top-quote selection algorithm — longest sentence vs. highest-attention span vs. first sentence. Pick when implementing the table.
- Synthesis-line length cap — 1 sentence vs. 2. Pick when implementing the group chat.
- Persona-group page URL — `/simulations/[id]/personas/[persona_id]` (clean) vs. `/simulations/[id]?persona=…` (sticky on result page). Pick when implementing the route.

---

## Implementation order (locked)

1. **Result table** (refactor `/simulations/[id]`). Existing data; no new backend.
2. **Individual chat surface** (`/agents/[id]`). Wires the already-existing `AgentChatService` to the already-stubbed `POST /agents/{id}/messages` route, then builds the UI.
3. **Persona-group chat surface.** New backend route + new frontend route. Depends on #2 because the fan-out reuses the single-agent send path.
4. **Calibration flags.** Last; doesn't block the rest.

Each step ships independently. The result table is the highest-leverage first step — it makes the existing simulation result legibly useful even before any chat ships.
