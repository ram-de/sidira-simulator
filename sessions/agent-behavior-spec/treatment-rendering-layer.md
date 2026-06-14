# Treatment-rendering layer (spec, draft v1)

**Session:** agent-behavior-spec · 2026-06-13 · spec §1 (the shared-infra piece, drafted first)
**Scope:** the component that turns `(existing state, proposed change)` into the exact text an agent reads. It is the single most reused piece of the three tickets — built once in the harness (#222), consumed identically in production. This draft audits the current path in code, names the gaps, proposes the representation, and locks the choice-set sourcing that §3a (`elicitation-conversion.md`) deferred here.

---

## 0. What the code does today (audited, not assumed)

`services/prompt_composer.py :: compose_identity_prompt(...)` builds one frozen prompt per agent. Structure:

```
PREAMBLE  (both arms, verbatim)
  ## Who you are            persona name + description + jtbd
  ## About you specifically identity_seed (age/locale/tenure/current_state/recent_gripe)
  ## Behavioral snapshot    persona.behavioral_snapshot (k: v lines)
  ## The product today      capability.reverse_prd  +  _summarize_figma(capability)   ← STRUCTURED
TASK BLOCK
  treatment →  ## The proposed change   hypothesis.prose  +  proposed_prd        ← PROSE ONLY
               ## Your task             react to the change
  control   →  ## Your task             react to the product as it is today
```

`_summarize_figma()` renders the current state richly: every screen, every component (`role`, `id`, `text`, `visible_to_roles`), and every transition (`trigger`, `from→to`, role-gating). That is a real structural rendering.

### The three gaps (all code-confirmed)

1. **`proposed_figma` is dropped on the floor.** `Hypothesis.proposed_figma: ReverseFigma | None` exists — the *same type* as `capability.reverse_figma` — but `compose_identity_prompt` never references it. The treatment arm injects only `prose` + `proposed_prd`. So:
   - **The agent sees TODAY in full structure and the PROPOSAL as prose.** It compares a wireframe against a paragraph. Any change whose effect lives in structure (a moved button, a new gate, a removed step, a reordered flow) is invisible unless the prose happens to spell it out — exactly the UI-modality changes the research says are already the hardest regime (r≈0.25–0.34).
2. **No explicit diff. No "held fixed."** The agent gets full-current + change-description and must *infer* the delta. Inference is where confabulation enters (the fabricated-JTBD / hyper-rationality defects): an agent can imagine changes that aren't proposed, or miss ones that are. Nothing states "these things did NOT change."
3. **Arm asymmetry of *format*, not just content.** Control sees structured-today. Treatment sees structured-today + prose-proposal. The paired comparison (#90) assumes the two arms differ *only* in the change — but they also differ in representation density. A treatment agent reasoning over prose and a control agent reasoning over structure are not a clean A/B of the change alone.

> Net: the current renderer is a *control-state* renderer with a prose addendum. There is no treatment-*state* renderer. That is the component to build.

---

## 1. Design principle

**Render both states in the same representation, then render the diff explicitly.** The agent should never have to reverse-engineer what changed. The renderer's output, per arm:

- **control arm:** the current state, structured (≈ today's `_summarize_figma`, unchanged).
- **treatment arm:** the current state, structured **+** the proposed state, structured **+** an explicit changelog (what changed / what is held fixed), all in one vocabulary.

Symmetry requirement: control and treatment differ in *content of the change*, never in *how state is rendered*. This is what makes the #90 paired delta attributable to the change.

---

## 2. The representation: a typed state-diff

Both `capability.reverse_figma` and `hypothesis.proposed_figma` are already `ReverseFigma` (screens / components / transitions). Diff them structurally rather than dumping both:

```
## What's changing

The product team is considering: {hypothesis.prose}

### Concretely, on screen `{screen}`:
  CHANGED   button `checkout_cta`   "Buy now"  →  "Buy now · free returns"
  ADDED     banner `trust_strip`    "10,000 5-star reviews"   [visible to: guest, member]
  REMOVED   field  `promo_code`
  MOVED     `shipping_estimate`     below the price → above the fold

### Explicitly NOT changing
  - the cart flow, the price, the payment step, everything on screen `account`
```

Rules:
- **Structural diff when `proposed_figma` is present** — compute ADDED / REMOVED / CHANGED / MOVED by id-matching screens→components→transitions against `capability.reverse_figma`. This is deterministic; no LLM.
- **Prose-only fallback when `proposed_figma` is absent** — today's behavior, but *labelled as a diff* ("the team describes the change as: …; assume everything else is unchanged"). Still emit the explicit "NOT changing" guard.
- **The "NOT changing" block is mandatory in both modes.** It is the single cheapest defense against the inference-confabulation gap, and it makes the control/treatment boundary legible to the agent.

---

## 3. Per-modality handling

One change can touch several modalities; render each in its native form. Ordered by how well the literature says agents read them:

| Modality | Source fields | Rendering | Reliability regime |
|---|---|---|---|
| **Copy / text** | `component.text` deltas | inline `"old" → "new"` | strong (r≈0.85) — trust most |
| **UI structure** | screen/component/transition adds-removes-moves | the structural changelog above | weak (r≈0.25–0.34) — flag on the result |
| **Mechanics / pricing / gating** | `proposed_prd` prose + `visible_to_roles` / `role_gated` deltas | a "rules that changed" sub-block, stated as before/after | mixed — depends on whether it reduces to a number |
| **Visual style** (color, spacing, imagery) | not in `ReverseFigma` today | **out of scope v1** — say so; do not pretend a text renderer captures a visual restyle | unsupported — must be declared, not faked |

The result card must name which modalities the change touched and carry the *weakest* modality's regime as the confidence ceiling (a copy+UI change inherits the UI ceiling).

---

## 4. Format-identical between benchmark and production (the hard constraint)

The renderer's *input* differs by source; its *output* must be byte-identical in shape:

- **Production:** customer PRD + reverse-figma crawl → `Hypothesis{prose, proposed_prd, proposed_figma}` → renderer.
- **Benchmark (#222):** an archived experiment (e.g. Upworthy headline A vs B) → adapter that builds the *same* `Hypothesis` shape (control headline = current `text`, treatment headline = proposed `text`, everything else "NOT changing") → renderer.

So the adapter work lives at the *edge* (archive → `Hypothesis`), and the renderer is shared. If a benchmark can't be expressed as a `Hypothesis` + state-diff, that's a signal the production path can't represent that change class either — a useful forcing function, not a workaround to route around.

---

## 5. Resolves: the conversion choice-set (`elicitation-conversion.md` §6 Q3)

§3a deferred "where do the realistic alternatives come from" to here. Decision:

- The conversion question's `choice_set` is **derived from the rendered treatment state's transitions** — the screens/actions actually reachable from `decision_point` in `proposed_figma` (e.g. from the cart screen: `checkout`, `continue_shopping`, `remove_item`, exit). These are real on-screen paths, not invented options.
- **Fallback** when transitions are sparse/absent: the curated default `{convert, defer/keep-browsing, leave, comparison-shop}` named in §3a.
- This means the elicitation's realism is bounded by crawl quality — log when the fallback is used so a thin crawl doesn't masquerade as a grounded choice-set.

---

## 5b. Two output views (contract added by §3b blinding)

The renderer must expose its result in **two views**, because §3 (elicitation-templates.md) runs metric prediction *blinded* and chat *unblinded*:

- **standalone-state view** — the treatment state rendered as *just the product*, with NO "what changed / the team is considering" framing. Fed to blinded behavioral agents (§3b default for metric elicitation), so they meet the change cold, as a real user meets a shipped product.
- **state+diff view** — the full structural changelog + "NOT changing" block from §2 above. Fed to the unblinded chat/"why" pass and to the scorer, never to a blinded behavioral agent.

Same `RenderedChange` object, two serializations. Caveat (§3b open Q2 / §3 §5.2): removal-type or pure-mechanic changes ("we removed the confirmation step") may not be expressible as a coherent standalone state — those fall back to unblinded + a flag.

## 6. Build order & touch points

1. `services/treatment_renderer.py` (new) — `render_state_diff(capability, hypothesis) -> RenderedChange` (structural diff + changelog + NOT-changing + modality tags). Pure, deterministic, unit-testable against fixture figmas.
2. `prompt_composer.py` — replace the prose-only `## The proposed change` block with `RenderedChange`. **Run `impact()` on `compose_identity_prompt` first** — it's the frozen-identity entry point (persisted to R2, never recomputed), so any change is high-blast-radius and must not alter the control-arm or #77 opener bytes. The change is additive to the treatment block only.
3. Benchmark adapter (#222) — `archived_experiment -> Hypothesis`, exercising the same renderer.
4. Choice-set extractor — `RenderedChange.transitions @ decision_point -> choice_set` for §3a.

---

## 7. Open questions

1. **MOVED detection fidelity:** id-matching catches add/remove/text-change cleanly; positional "MOVED" needs layout coordinates `ReverseFigma` may not carry. v1 may only reliably emit ADDED/REMOVED/CHANGED and approximate MOVED from transition/order deltas. Acceptable? (recommend: ship A/R/C in v1, treat MOVED as best-effort, flag it.)
2. **Diff granularity in the prompt:** full structural changelog vs. a summarized top-N changes when a PRD touches dozens of components (prompt-length blowup). (recommend: cap at N, list the rest as "+K more minor changes," log the truncation — never silently drop.)
3. **Visual restyle (color/spacing/imagery):** genuinely out of `ReverseFigma`'s reach today. Declare unsupported in v1, or extend the crawl schema to carry style tokens? (recommend: declare unsupported, revisit only if a customer change class demands it.)
