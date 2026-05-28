# Agent Chat UI — design spec (Phase 4)

The defining feature: after a simulation, a PM can talk to the agents that participated. This document is the source of truth for the three interaction surfaces and the backend contract they assume. ROADMAP Phase 4 implements it.

> **Status:** Design locked. Implementation tickets in the [Sidira GitHub Project](https://github.com/users/ram-de/projects/), Phase = 4.

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

**What it is:** a chat surface against the *group* of agents that share a persona. The PM types one question; depending on the selected **mode**, the system either produces ONE collective answer in the voice of the persona-as-a-whole (default), or fans out to every individual agent.

### Two modes — one composer

The composer carries an inline toggle:

```
Ask the group as  [● collective | ○ individual fan-out]   [textarea]
```

- **Collective (default).** Single LLM call. The model is given the persona description + every agent's `identity_seed` + every agent's `initial_reaction` + the prior collective turn log, and answers in one voice that speaks for the persona group. The model is required to cite specific agents using `[agent_label]` tokens when it makes claims attributable to individuals ("[maya] said X; [dom] disagreed"). The frontend rewrites every `[label]` token into a `Link href="/agents/{agent_id}"` so the PM can drill into any cited individual without losing the collective conversation.
- **Individual fan-out.** Behavior from #54: one PM message is appended to every agent's individual conversation; each agent replies in their own voice; a one-line counted synthesis is generated from the replies. PM sees every reply side-by-side. Use this when the PM wants disagreement-as-signal ("what would YOU change about checkout?").

**Why two modes:** the original spec locked fan-out because disagreement-within-persona is signal. In practice, meta questions ("what's the consensus?", "who reacted positively?") sent through fan-out produce garbage — each individual agent tries to characterize a group they don't have visibility into, and the answers are guesses. Collective mode is the right tool for meta questions; fan-out is the right tool for in-character ones. Default is collective because that's what PMs reach for first.

### Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ← Result table                                                                │
│                                                                               │
│ Weekend family movie night (n=3)                                              │
│ Hypothesis: Replace Continue Watching rail with a Smart Resume hero…         │
│                                                                               │
│ ┌─[ chat ]──────────────────────────────────────────────────────────────────┐│
│ │  PM: "Which of you reacted negatively, and why?"                          ││
│ │                                                                            ││
│ │  Collective (n=3): Two of us pushed back — [rivka_001] said the family   ││
│ │  browsing ritual is the point and a hero card kills it, and [rivka_002]  ││
│ │  said the kid-profile shortcut sits in that rail. [rivka_003] was OK     ││
│ │  with the change since they use voice search anyway.                      ││
│ │                                                                            ││
│ │  PM: …                                                                     ││
│ │                                                                            ││
│ │  Ask the group as  [● collective | ○ individual fan-out]                  ││
│ │  [composer textarea]                                                       ││
│ └────────────────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────────┘
```

Each `[rivka_NNN]` token in the collective reply renders as a link to `/agents/{agent_id}`. Clicking jumps to Surface 3 for that agent. Coming back to the persona-group page re-fetches the collective turn log from the server — nothing is lost. Composer drafts persist via `sessionStorage` so a mid-typed question survives the round trip.

### Identity-continuity guarantee (preserved with a caveat)

**Fan-out mode** is unchanged from the locked #54 implementation: each PM message is appended to every participating agent's individual conversation log; drilling from a fan-out reply into Surface 3 shows the same turn pair already present.

**Collective mode** does NOT touch individual agent logs — the collective LLM call is a meta layer that reads the agents' frozen identities + initial reactions, but does not append turns to any individual agent's log. The agents whose names appear in a collective reply have NOT had a turn added to their conversation. This is intentional: the collective voice is the persona group speaking; the individuals haven't been independently re-prompted. Drill-down to an individual lands on Surface 3 with that agent's existing conversation log (which carries only the turns from prior `individual` fan-outs, if any).

The collective turn itself, including its `references` (cited agents with IDs), is persisted to the persona-group log so replay is self-contained.

### Backend contract

`POST /simulations/{sim_id}/personas/{persona_id}/messages` accepts a `mode` field:

```json
{ "message": "...", "mode": "collective" | "individual" }
```

Default `mode` is `"collective"` if omitted.

**Collective mode response:**
```json
{
  "role": "collective",
  "content": "Two of us pushed back — [rivka_001] said ...",
  "references": [
    {"agent_id": "uuid-1", "agent_label": "rivka_001"},
    {"agent_id": "uuid-2", "agent_label": "rivka_002"}
  ],
  "created_at": "2026-05-26T19:30:00Z"
}
```

**Individual-fanout mode response** (unchanged from #54):
```json
{
  "synthesis": "3 of 3 said ...",
  "per_agent": [{"agent_id": "...", "agent_label": "...", "content": "...", "error": null}],
  "created_at": "..."
}
```

Both responses are persisted to `customers/<id>/simulations/<sim_id>/persona_groups/<persona_id>/turns.jsonl` with `role` in `{ pm, synthesis, collective }`. A turn of role `collective` carries `content` + `references`; a turn of role `synthesis` carries `content` + `per_agent` (existing).

### Service contract — never raises

Same contract as the #54 synthesis service: `PersonaGroupCollectiveService.collective_reply(...)` NEVER raises into the route. LLM exceptions degrade to a deterministic fallback line; references parse failures degrade to content-only. The collective surface is downstream of any per-agent state — failures here must not invite a client retry that re-runs upstream work.

### Cost note

Collective mode is ONE LLM call per turn regardless of N. Fan-out scales with N (capped at 5 concurrent per #54 codex round-3). For large persona groups (Phase 2.5 N=8-10) collective is the obvious default; fan-out is the explicit override.

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
- **No agent-to-agent chat.** Mirofish does this; we don't. See `docs/mirofish-prior-art.md` "Inter-agent socialization" — Sidira's confidence math assumes independent reactions.
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
