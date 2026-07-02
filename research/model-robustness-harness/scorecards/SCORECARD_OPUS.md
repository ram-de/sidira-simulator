# SCORECARD — OPUS LLM-ARM SWAP (blind re-test of AMBDOM + GNCE)

Sealed, blind re-run of the **existing** experiment batteries with **only the LLM arm swapped**:
`llama-3.3-70b-versatile` → `claude-opus-4-8`. Grounded-sim and truth are unchanged (read from
`bakeoff_ambdom_results.json` / `bakeoff_gnce_results.json`). Opus saw ONLY the verbatim narrative
from the original log — the same prose llama saw, no magnitudes, only a "salient" surface cue — with
the identical system message. 59 cases; 8 distinct narratives (the batteries reuse symmetric prose
templates by design). Log: `opus_llm_log.jsonl`.

**Faithfulness deviation (one, forced):** `claude-opus-4-8` rejects the `temperature` parameter
(`temperature is deprecated for this model`, HTTP 400), so the `temperature:0` field was dropped.
Everything else is verbatim: same endpoint, `max_tokens:20`, same SYSMSG, same parse rule
(uppercase → DOWN⇒−1 elif UP⇒+1 else 0; first float in [0,1] = confidence), sequential, 2 retries.

---

## 1. Optimism tally — the headline question

Prior finding: **llama NEVER confidently predicts DOWN** on AMBDOM (structural pro-feature optimism).

| arm | battery | UP | DOWN | UNSURE |
|---|---|---|---|---|
| **Opus** | AMBDOM (38) | 2 | **36** | 0 |
| llama | AMBDOM (38) | 19 | **0** | 19 |
| **Opus** | GNCE (21) | 15 | **3** | 3 |
| llama | GNCE (21) | 18 | 3 | 0 |
| **Opus** | TOTAL (59) | 17 | **39** | 3 |
| llama | TOTAL (59) | 37 | 3 | 19 |

**Does Opus EVER predict DOWN? YES — 39 times (36 AMBDOM + 3 GNCE).** The exact opposite of llama,
which called DOWN only 3× total and **0× in all of AMBDOM**. On the ambiguous AMBDOM prose Opus is not
merely un-optimistic — it flips to a **constant-DOWN / pessimism policy**: it answered DOWN to *both*
symmetric templates (salient-help AND salient-harm), reserving its only 2 AMBDOM UPs for the two
concrete real-world scenarios (B1 Cookie Cats, B2 streamly). So the "LLMs are structurally
pro-feature optimistic" result is **llama-specific, not a universal LLM property**.

---

## 2. Directional accuracy (sign match = correct; true-null / ≈0 cells excluded from denominator)

| slice | n scored | excluded (null) | **Opus** | llama | grounded-sim |
|---|---|---|---|---|---|
| OVERALL (both batteries) | 50 | 9 | **0.68** (34/50) | 0.42 (21/50) | **0.92** (46/50) |
| AMBDOM (all cells) | 32 | 6 (KNIFE) | **0.50** (16/32) | 0.09 (3/32) | **0.97** (31/32) |
| GNCE (all cells) | 18 | 3 (NULL) | **1.00** (18/18) | 1.00 (18/18) | 0.83 (15/18) |

Opus beats llama overall (0.68 vs 0.42) and on AMBDOM (0.50 vs 0.09) — but read section 3 before
crediting reasoning: on AMBDOM the entire Opus gain comes from a constant-DOWN policy paying off on a
**sign-balanced** cell set (16 truth-UP / 16 truth-DOWN among the 32 non-null), not from resolving
anything. Grounded-sim (0.92 / 0.97) is untouched by the swap and remains far ahead on AMBDOM.

---

## 3. AMBDOM magnitude-flip regime — the decisive slice

The DISAGREE cells: two mechanisms oppose, the salient surface cue points **against** the true net
sign, and the winner is decided purely by unstated per-unit magnitudes. A cue/intuition follower is
wrong by construction; only the grounded g-formula, which reads mediator strengths from data, recovers
the flip.

| slice | n | **Opus** | llama | grounded-sim |
|---|---|---|---|---|
| **clean DISAGREE (WIDE + NARROW)** | 12 | **0.50** (6/12) | **0.00** (0/12) | **1.00** (12/12) |
| all-DISAGREE (+ CONF + HIDCONF) | 24 | 0.50 (12/24) | 0.00 (0/24) | 0.96 (23/24) |

**Opus sits exactly AT chance (0.50).** It does not cross chance and does not approach grounded (1.00).
Mechanically: Opus answers DOWN to both templates, so it banks the 6 truth-DOWN cells and misses the 6
truth-UP cells — a coin flip delivered by a constant answer on a balanced set. Its 0.50 "beats" llama's
0.00 only because llama's optimism lands **below** chance on this ⟂-cue set; swapping a below-chance
optimism bias for an at-chance pessimism bias is not magnitude reasoning. Because each template maps to
BOTH truth polarities, **no narrative-only predictor can exceed 0.50 here** — the ceiling is structural.
Grounded-sim clears it because it reads the magnitudes the prose withholds.

---

## 4. GNCE accuracy comparison

| archetype | truth | **Opus** | llama | grounded | note |
|---|---|---|---|---|---|
| MED-FLIP+ | + | 3/3 | 3/3 | 3/3 | mediator dominates, cue concrete |
| MED-FLIP− | − | 3/3 | 3/3 | 3/3 | Opus + llama both call DOWN |
| DIRECT-DOM | + | 3/3 | 3/3 | 3/3 | Opus conf 0.88 (highest) |
| MED-HIDDEN+ | + | 3/3 | 3/3 | **0/3** | grounded abstains (mediator unobserved) |
| MED-CONF | + | 3/3 | 3/3 | 3/3 | |
| MED-HIDCONF | + | 3/3 | 3/3 | 3/3 | |
| NULL | 0 | excl | excl | excl | Opus UNSURE (0.5); llama UP |
| **GNCE total** | | **1.00 (18/18)** | **1.00 (18/18)** | **0.83 (15/18)** | |

On GNCE the narrative names a *concrete, dominant* directional mechanism, so both LLMs read the sign
perfectly and **tie** — and both edge out grounded, which correctly **abstains** on MED-HIDDEN+ (the
mediator proxy is unobserved). GNCE does not separate the two LLMs: its signs are guessable from prose.

---

## 5. VERDICT

**(a) Is Opus less optimistically biased than llama — does it ever call a decline?**
**Yes, decisively.** Opus predicts DOWN 39× (vs llama 3×), including on **all 36** AMBDOM arm-A cases
where llama called DOWN **zero** times. Opus shows no pro-feature optimism; on ambiguous prose it
exhibits the mirror-image bias — a **constant-DOWN pessimism**. The prior "structural pro-feature
optimism, never confidently predicts a decline" finding is a property of the llama arm, **not** of LLMs
in general. It does not replicate under Opus.

**(b) Does Opus cross chance / beat llama / approach grounded on the counter-intuitive slice?**
**Beats llama, but does NOT cross chance and does NOT approach grounded.** On the clean magnitude-flip
slice Opus = **0.50**, llama = 0.00, grounded = 1.00. Opus's win over llama is not reasoning — it is a
degenerate constant-DOWN answer that scores exactly at chance because the flip cells are sign-balanced;
llama's identical-style constant-UP/UNSURE answer just happens to land below chance on the ⟂-cue set.
**Both LLMs are magnitude-blind here.** Opus is stuck at chance on the decisive slice.

**Net:** swapping llama → Opus **erases the optimism-bias story** (Opus freely predicts declines) but
**leaves the core wedge intact**: on magnitude-driven counter-intuitive flips, no LLM — llama at 0.00,
Opus at 0.50 (chance) — recovers the true sign, while the grounded g-formula sim recovers 12/12. The
frontier-LLM swap changes the *flavor* of the LLM's failure, not the *fact* of it. Grounded sim remains
the only arm that reads the magnitude the prose withholds.
