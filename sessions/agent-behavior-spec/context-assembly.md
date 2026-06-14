# Agent-context assembly (spec, draft v1)

**Session:** agent-behavior-spec · 2026-06-13 · spec §2
**Scope:** how an agent's *identity* is assembled — the merge of feature pack + rendered change (§1) + persona narrative + the individual sampled row + the elicitation (§3a) into one frozen prompt. §1 defined what change the agent reads; §3a defined what we ask it; this defines **who the agent is when it reads them.** This is the hierarchical-conditioning lever the research named the single highest-leverage accuracy component (analysis §3.2).

---

## 0. What the code assembles today (audited)

`compose_identity_prompt` (prompt_composer.py) builds the frozen identity from exactly four identity inputs:

| Block | Source | Nature |
|---|---|---|
| Who you are | `persona.name` + `persona.description` + `persona.jtbd` | qualitative gestalt, **shared by every agent in the persona** |
| About you specifically | `IdentitySeed{age_band, locale_band, tenure_band, current_state, recent_gripe}` | demographic bands + two free-text lines |
| Behavioral snapshot | `persona.behavioral_snapshot` (k→v) | **shared by every agent in the persona** |
| The product today | `capability.reverse_prd` + `_summarize_figma` | product context (not identity) |

`IdentitySeed` is drawn deterministically from `persona.behavioral_seeds` pools by `(persona_id, sample_index, run_seed)` — **each field drawn independently** from its own pool.

### The two gaps (code-confirmed)

1. **No individual behavioral row → no within-persona quantitative variety.** Of the four identity blocks, two are persona-level constants and the third (`IdentitySeed`) is thin demographic texture. Two agents in the same persona differ only by a few demographic bands + two free-text lines + LLM temperature. The research's core finding is that accuracy comes from *individual* conditioning — each agent carrying one real user's behavioral texture (the fee-transparency worked example, qa §6: same persona, promo-code Android user vs DashPass holder → opposite grounded reactions). That signal does not exist in the current assembly.
   - **`Persona.centroid_features: dict[str, float]` already exists and is never read by the composer.** It's the cluster *mean* — every agent would share it anyway. What's missing is a per-agent *draw* and its *deviation* from that mean.

2. **Independent pool-draws destroy the joint distribution.** `IdentitySeed` draws age, locale, tenure, state, gripe each from a separate marginal pool. Real users aren't marginal products — a "new + mobile + price-sensitive" cluster has correlated features. Independent draws can manufacture incoherent agents (a 10-year-tenure user with a brand-new-user gripe). The fix is to sample one *joint* row, not five marginals.

---

## 1. The hierarchical-conditioning stack (target assembly)

Five layers, outermost (shared) → innermost (individual):

```
1. PRODUCT          feature pack: reverse_prd + reverse_figma           (shared, all agents)
2. CHANGE           §1 rendered state-diff (treatment) / nothing (control)
3. PERSONA GESTALT  persona.description + jtbd + behavioral_snapshot     (shared within persona)
4. INDIVIDUAL ROW   one sampled row + its deltas from the centroid       (UNIQUE per agent)  ← the new piece
5. ELICITATION      §3a reaction + behavioral decision
```

Layers 1–3 and 5 exist (1–2 via §1, 3 today, 5 via §3a). **Layer 4 is what §2 adds.** The design principle: the gestalt (layer 3) says what's *typical* for this persona; the row (layer 4) says where *this individual diverges* from typical. The two must not restate each other — the row is rendered as **deltas**, not as a full feature dump.

---

## 2. The individual row

**Source (degradation path — this is also the benchmark↔prod contract):**

| Tier | Row source | What it tests |
|---|---|---|
| Production / Tier-0 artifact #5 (Hillstrom, Criteo) | one **real anonymized** user row from the persona's GMM component | the full pipeline end-to-end (real user features → response) |
| Synthetic | one row **sampled from the fitted GMM component** (joint, covariance-aware) — privacy-clean, qa §2 | engine behavior with realistic joint texture |
| Tier-0 artifacts 1–4 (demographic-synthetic) | no behavioral row available → demographic bands only | honest lower bound (engine only) |
| Ablation floor (§4) | persona gestalt only, row suppressed | the archetype-only baseline to beat |

The assembler takes whichever is available and **degrades gracefully**, logging which tier was used (a thin source must never masquerade as a grounded row — same honesty rule as §1's choice-set fallback).

**Rendering — deltas above a salience threshold, in natural language:**

- For each feature, z = (row_value − `centroid_features`[f]) / scale[f]. Render features with **|z| ≳ 0.5** as plain-language deltas ("you order about 3× as often as the typical {persona}"; "you've never used the promo-code flow, unlike most of this group"). Drop |z| < 0.5 — the gestalt already covers the typical, and dumping every feature dilutes the salient ones and inflates prompt length.
- Render **direction and rough magnitude**, not raw numbers ("much more often," "rarely," "about average except…") — agents read calibrated comparatives better than decimals, same lesson as §3a's 10-trial framing.
- **`scale[f]` (per-feature std/dispersion) is not on `Persona` today** — only `centroid_features` (the mean). Computing z needs per-component scale → **dependency on #7** (personas hygiene): the pack must emit per-feature dispersion alongside the centroid, or the soft-posterior covariance the GMM already has internally. Until then, deltas are rank-only ("high/low for this group"), not z-scaled.

**Measured vs proxy (analysis §3 feature-role distinction):** tag each rendered delta as observed behavior vs proxy-derived inference, and hedge the proxy ones ("we infer you're price-sensitive" vs "you abandoned 4 of your last 5 carts"). Confabulation (the fabricated-JTBD defect) enters through proxy features stated as fact.

---

## 3. Joint sampling replaces independent pool-draws

`IdentitySeed`'s five independent draws become a **projection of the one sampled row**:

- Draw one joint row (real or GMM-sampled) → derive `age_band`/`locale_band`/`tenure_band`/`current_state`/`recent_gripe` as *views* of that row, so they're mutually coherent by construction.
- Keep the deterministic `(persona_id, sample_index, run_seed)` keying — paired-seed A/B (#90) and identity continuity (R2 freeze) both depend on it. The change is *what* is drawn (one joint row vs five marginals), not *how it's seeded*.
- `behavioral_seeds` pools remain the fallback for v1.0 packs with no row data (degrades to today's behavior, logged).

---

## 4. Soft membership (ties to #7, killed-hard-assignment finding)

The analysis killed hard GMM assignment as the *conditioning* mechanism. For assembly:

- **Gestalt (layer 3): hard-assign for v1** — one persona = one cast member, which keeps chat legible and the panel composition interpretable (personas-as-scaffolding, qa §6). A soft-blended narrative is hard to read and harder to chat with.
- **Row (layer 4): carries its soft posterior.** The row is sampled from the component it actually belongs to; if an agent sits between two components (posterior 0.7/0.3), that's a real signal — note it as a hedge ("you mostly behave like {A}, with a streak of {B}"). This is where the soft-posterior value lands without sacrificing legibility.
- Decision rule: **legibility from hard gestalt, accuracy from the soft-posterior row.** Don't blend the narrative; do carry the posterior on the row.

---

## 5. Where this plugs into the code

- `compose_identity_prompt` gains an individual-row block between "Behavioral snapshot" and "The product today." Additive; the persona/seed/#77-opener bytes are untouched (same constraint as §1).
- **`compose_identity_prompt` is the frozen-identity entry point (R2-persisted, never recomputed) → high blast radius. Run `impact({target: "compose_identity_prompt", direction: "upstream"})` before any edit** and report the radius, per the repo rule. §1 and §2 both land here — sequence them as one change to that function, not two.
- New: a row-sampling + delta-rendering service (consumes persona + GMM component + run seed → rendered-delta block). Pure/deterministic given the seed; unit-testable against fixture components.
- **Depends on #7** for per-feature scale (z-scoring) and the soft posterior on the row. Until #7 ships those, §2 ships in rank-only mode (high/low-for-group deltas, no z, no posterior hedge) — still a strict improvement over no row at all.

---

## 6. Open questions

1. **Salience threshold |z| ≳ 0.5** — tune on the harness (#222); too low = prompt bloat + diluted signal, too high = agents collapse back toward the gestalt. (recommend: 0.5 start, treat as a tunable, measure on Tier-0 artifact #5.)
2. **Real-row privacy in production** — anonymized real rows carry re-identification risk at the tail (whales, rare segments). GMM-sampled synthetic rows are privacy-clean but one step removed from reality. (recommend: synthetic-by-default in production; real rows only for the Hillstrom/Criteo benchmark where the data is already public/consented.)
3. **Prompt-length budget** — row deltas + §1 state-diff + persona + product can blow the context window on rich features. Need a per-block cap and a priority order when trimming (recommend keep: salient deltas > change-diff > gestalt detail; log any truncation, never silent).
