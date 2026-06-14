# Chat consistency + counterfactual interview (spec, draft v1)

**Session:** agent-behavior-spec · 2026-06-13 · spec §5
**Scope:** how an agent stays the *same person* across a multi-turn chat, and how the paired-seed design enables the **counterfactual interview** — the unique mechanic where one identity's reaction under control and under treatment can be put side by side. qa §5's verdict frames the whole section: **strongest product feature and weakest scientific claim simultaneously.** The job here is to make it powerful *and* keep it from lying.

---

## 0. Memory model today (audited — `memory/agent_memory.py`)

Three frozen layers per agent in R2, plus Postgres metadata:
```
identity.md          system prompt — written ONCE at sim time, NEVER recomputed
initial_reaction.md  verbatim sim-time output — replayed as the FIRST assistant turn
conversation.jsonl   append-only chat history
```
Chat **never re-runs the prompt-composer** — it loads the frozen artifacts and appends. This is the identity-continuity guarantee: the agent a PM chats with IS the one that participated, not a re-instantiation from the persona template.

**Two consequences that drive this spec:**
1. **Consistency is already architecturally solid.** The frozen system prompt + replayed first reaction means turn N is conditioned on the exact identity and the agent's own words. The remaining consistency work is prompt discipline, not architecture.
2. **Each agent is frozen to its ARM.** A control agent's `identity.md` encodes the control world; it has *no knowledge* of the treatment, and vice versa (`compose_identity_prompt`: "an agent created with arm=control STAYS a control agent for all chat replay"). **This is the constraint the counterfactual interview must respect** — see §2.

---

## 1. Multi-turn chat consistency

What's solid (don't touch): frozen identity, replayed first reaction, append-only history. What §5 adds is the discipline that keeps later turns honest:

- **Anchor every turn to prior commitments.** The agent must answer as the same person, referencing what it already said (the prompt's existing "answer as the same person, referring back to what you just said" guidance — keep it, strengthen it). A turn that contradicts an earlier turn or the behavioral snapshot is a consistency failure.
- **Ground in behavioral features, not invented backstory.** Multi-turn is where the **fabricated-JTBD defect** compounds — each turn invites more elaboration, and an agent will happily invent richer motivations the longer you talk. The identity's measured features (§2 row) are the leash; proxy-derived traits stay hedged (§2 measured-vs-proxy). A turn that asserts a motivation absent from the identity is confabulation, flag it.
- **No new product facts.** The agent may reason about what it was shown (frozen Feature Pack slice + rendered change) but must not invent flows — the existing "do not invent flows you weren't told about" rule extends to every chat turn, not just the first.
- **Consistency check (optional, benchmark-grade):** a scorer pass that flags turns contradicting the identity or earlier turns — reuses the scorer-side `chat_json` pattern, run over `conversation.jsonl`. Useful for the harness; opt-in in production.

---

## 2. The counterfactual interview — the honest design

The unique capability (qa §5): the same identity `(persona_id, sample_index)` exists in **both** arms via paired seeds (#90). The naive version — "ask the agent what changed when we made the change" — is the **dangerous** version: it makes one agent introspect across an arm boundary it was frozen out of, which both **breaks the arm-purity guarantee** (§0.2) and **manufactures confabulation** (the agent invents a causal story for a change it never experienced as a delta).

**The defensible design: juxtaposition, not introspection.**
- Talk to the **control instance** about its experience, and the **treatment instance** about its experience — each within its own frozen world, arm-pure, no cross-arm question asked.
- The "counterfactual" is the **analyst (or a synthesis pass) placing the two frozen reactions of the same identity side by side**: *the same person, same row, same seed — said X about today and Y about the change.* That contrast is the insight. No agent ever claims "I changed my behavior because…"; the human sees that it *did* react differently.
- This preserves everything: the metric delta (§3d) and the explanation come from the *same* paired structure, the freeze holds, and the claim degrades from "the agent explains the cause" (false) to "the same identity reacted differently, here's each side" (true).

**What this means for the product surface:** the compelling demo ("talk to the user from your test, in both worlds") is built from two arm-pure chats + a synthesis view — not a single agent with god-mode memory of both arms.

---

## 3. Confabulation defenses (qa §5, made concrete)

1. **Frame as hypothesis generator, never evidence** — in the UI copy, not just our heads. Chat output is labeled "possible reasons to investigate," never "the reason." Reuse/strengthen the #91 disclaimer family.
2. **Ground answers in actual behavioral features**; hedge proxy-derived motivations (§2). Survey fusion matters more *because* chat is flagship — a measured "why" beats an inferred one.
3. **Interview the panel, not the agent** (§4 below) — never ship a single agent's quote as a finding.
4. **Benchmark the "why"** (§5 below) — the only thing that turns confabulation-risk into a defensible claim.

---

## 4. Interview the panel, not the agent

A single agent's explanation is an anecdote and a confabulation risk. The unit of insight is the **panel** (qa §6: persona = unit of insight):
- Run the same interview question across the panel (or the relevant persona cluster), **cluster the answers**, and present **reason distributions** — "62% of high-frequency users cited the added step; 21% the new copy" — not quotes.
- **Tie clusters to the weakness taxonomy** (`Weakness.category`: wrong_metric / wrong_cohort / broken_mechanism / untestable_hypothesis / hidden_guardrail_risk / underpowered_design) so the interview output is structured, comparable across runs, and actionable — not a wall of free text.
- Weight reason clusters by persona weight (Hamilton), so a theme's prominence reflects the user base, not the panel's raw composition.

---

## 5. Benchmark the "why" (the second differentiator)

Nobody validates explanations — so doing it is a moat (qa §5). The validation track:
- **Predicted complaint themes vs realized post-launch complaints.** After a change actually ships, mine real signal (app-store reviews, support tickets, UXR notes) for complaint themes; score the panel's *predicted* theme distribution against the realized one (rank/overlap of themes, same directional bar as §4 — not exact frequencies).
- This is a distinct outcome from the metric backtest (§4 ablation): that validates *what* (direction/rank of lift); this validates *why* (theme prediction). Two differentiators, two evidence tracks.
- Slots into the evidence ladder as a Tier-1+ artifact (needs a shipped change + post-launch signal → customer or public-launch data); pre-register the theme taxonomy before scoring (§4 §5 discipline).

---

## 6. Positioning + cross-cutting flags

- **Positioning (qa §5):** chat leads for mid-market; for Meta/Google it comes **after** the blind track record — to those buyers chat is the "cool demo" they discount until the numbers earn trust. Order the sales motion accordingly.
- **Cross-cutting with §3b (blinding) — a real tension to resolve:** metric elicitation runs *blinded*, but `initial_reaction.md` (chat's first turn) is the *unblinded* reaction, and today's frozen `identity.md` bakes the unblinded "the team is considering this change" framing. So a clean split needs the memory layout to carry **two artifacts**: a blinded behavioral record (feeds the metric, §3a/§3d) and the unblinded `initial_reaction.md` (feeds chat). Both frozen, both arm-pure. → Add a `behavioral_record.md` (or equivalent) alongside `initial_reaction.md` in `AgentMemory`; the metric never reads the chat artifact and vice versa. Flag for §6 / #221 memory-layout work.
- **Freeze still holds for both:** whichever artifacts exist, they are written once and replayed — the identity-continuity guarantee is non-negotiable across this whole section.

---

## 7. Open questions

1. **Synthesis pass for the counterfactual view:** is the side-by-side built by the analyst/UI (pure juxtaposition, zero added LLM risk) or by a synthesis LLM call that summarizes the contrast (smoother, but adds a confabulation surface)? (recommend: pure juxtaposition for the evidence view; optional synthesis call clearly labeled "AI summary of the contrast," never the primary artifact.)
2. **Two-artifact cost/complexity (§6):** does splitting blinded-behavioral from unblinded-chat double sim-time generation, or can the unblinded chat reaction be generated lazily on first chat open (most agents are never chatted with — §3 §5.1)? (recommend: behavioral record at sim time always; unblinded chat reaction lazy on first open.)
3. **Consistency-checker strictness:** how hard to enforce cross-turn consistency before it becomes brittle (a real person *can* change their mind mid-conversation)? (recommend: flag contradictions of the *identity/behavioral snapshot* hard; flag turn-to-turn opinion shifts soft — they may be legitimate.)
