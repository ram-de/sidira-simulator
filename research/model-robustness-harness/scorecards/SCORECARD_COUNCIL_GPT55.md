# SCORECARD — gpt-5.5 LLM-ARM SWAP + gpt-5.5×Opus ABSTAIN-GATE COUNCIL

Sealed, blind re-run of the existing AMBDOM + GNCE batteries with the LLM arm set to **`gpt-5.5`**,
then a two-model (gpt-5.5 × Opus) council abstain-gate analysis. Grounded-sim, truth, Opus, and llama
signs are unchanged (read verbatim from `opus_llm_log.jsonl`). gpt-5.5 saw ONLY the verbatim narrative
(same prose the other arms saw, no magnitudes) with the identical system message. 59 cases; 8 distinct
narratives (batteries reuse symmetric templates by design → cache-by-narrative, 8 live calls broadcast
to 59). Log: `council_gpt55_log.jsonl`. Coverage: **59/59, 0 empty-content, 0 failed calls.**

**Faithfulness deviation (documented, necessary — mirrors Opus dropping `temperature`):**
gpt-5.5 is a reasoning model. Verbatim body except: **no `temperature`** (reasoning models reject
`temperature:0`, HTTP 400); **`max_completion_tokens:3000`** instead of `max_tokens:20` (reasoning
tokens count against the budget; a tiny budget returns empty content); **`reasoning_effort:"low"`**
(accepted — used, to speed sequential calls). Same endpoint, same SYSMSG, same parse rule
(uppercase → DOWN⇒−1 elif UP⇒+1 else 0; first float in [0,1] = confidence). Empty-retry-at-6000 path
present but never triggered (0 empties at 3000). Exact model string recorded per row: `gpt-5.5`.

Cell taxonomy (as specified): **FLIP** = AMBDOM DISAGREE-{WIDE,NARROW,CONF,HIDCONF} = 24 (clean flip =
WIDE+NARROW = 12); **GUESSABLE** = GNCE non-null (18) + AMBDOM AGREE-WIDE (6) = 24; **NULL** = KNIFE (6)
+ GNCE NULL (3) = 9 (excluded from accuracy); **REAL** = B1-cookiecats + B2-streamly = 2 (separate).

---

## PART 1 — gpt-5.5 SOLO

### 1. Bias tally — optimist, pessimist, or balanced?

| arm | AMBDOM (38) UP/DOWN/UNSURE | GNCE (21) | TOTAL (59) |
|---|---|---|---|
| **gpt-5.5** | 1 / 18 / 19 | 15 / 3 / 3 | **16 / 21 / 22** |
| Opus | 2 / 36 / 0 | 15 / 3 / 3 | 17 / 39 / 3 |
| llama | 19 / 0 / 19 | 18 / 3 / 0 | 37 / 3 / 19 |

**gpt-5.5 is neither optimistic nor pessimistic — it is the BALANCED / ABSTAINING arm.** On ambiguous
AMBDOM prose it splits **UNSURE (19) vs DOWN (18) and says UP exactly once**. It is the mirror of
neither prior arm: llama is UP-heavy (structural pro-feature optimism, 0 DOWN on AMBDOM), Opus is
constant-DOWN pessimism (36 DOWN on AMBDOM). gpt-5.5 instead **refuses to call UP on ambiguous prose**
and defaults to abstain-or-decline — the most calibrated *stance* of the three, but see §2.

### 2. Directional accuracy (sign match; null excluded)

| slice | gpt-5.5 | Opus | llama | grounded-sim |
|---|---|---|---|---|
| OVERALL (50) | 0.42 (21/50) | **0.68** | 0.42 | **0.92** |
| AMBDOM (32) | 0.09 (3/32) | 0.50 | 0.09 | **0.97** |
| GNCE (18) | **1.00** (18/18) | 1.00 | 1.00 | 0.83 |
| **clean FLIP (12)** | **0.00** (0/12) | 0.50 | 0.00 | **1.00** |
| all FLIP (24) | 0.00 (0/24) | 0.50 | 0.00 | 0.96 |
| GUESSABLE (24) | 0.88 (21/24) | 0.88 | 0.88 | 0.88 |
| REAL (2) | 0.00 (0/2) | 0.50 | 0.00 | **1.00** |

**gpt-5.5 does NOT beat the flip-cell chance ceiling — it lands at 0.00, below Opus's 0.50.** On the 12
clean-flip cells it abstains on all 6 salient-harm-template cells (UNSURE) and calls DOWN on all 6
salient-help-template cells whose truth is UP → **0 correct**. Its abstention stance means it *forfeits*
the coin-flip Opus banks with a constant-DOWN policy. Either way the message is identical: a
narrative-only predictor is **structurally capped at chance on magnitude flips**, and gpt-5.5 confirms
the ceiling — it is magnitude-blind. Only grounded-sim (reads the withheld magnitudes) clears it (1.00).

On REAL, gpt-5.5 **misses Cookie Cats** (predicts UP, truth DOWN — the counter-intuitive negative it
cannot see) and abstains on streamly. grounded recovers both.

### 3. GNCE / GUESSABLE accuracy

gpt-5.5 = **1.00 on GNCE (18/18)**, tying Opus and llama. Where the narrative names a concrete, dominant
mechanism the sign is guessable from prose and all three LLMs read it perfectly (and edge out grounded's
0.83, which correctly abstains on MED-HIDDEN+). GUESSABLE overall (incl. AMBDOM AGREE-WIDE) = 0.88, a
four-way tie. **GNCE does not separate the models.**

---

## PART 2 — gpt-5.5 × Opus COUNCIL (the real question)

### 4. Agreement structure (gpt-5.5 vs Opus)

| slice | agree | disagree | gate-shape read |
|---|---|---|---|
| FLIP (24) | 12/24 = **0.50** | 0.50 | disagree only HALF the time |
| clean FLIP (12) | 6/12 = 0.50 | 0.50 | |
| GUESSABLE (24) | **21/24 = 0.88** | 0.12 | agree, as wanted |
| NULL (9) | 6/9 = 0.67 | 0.33 | |
| REAL (2) | 1/2 = 0.50 | 0.50 | |

The gate has the *right shape* directionally (more agreement on GUESSABLE, less on FLIP) — **but the
FLIP disagreement rate is only 0.50, not high.** Half the flip cells slip through as agreement.

### 5. False-confidence check — the dangerous number

**Among the 12 FLIP cells where gpt-5.5 AGREES with Opus, the agreed sign is correct 0/12 (0.00).**
These are the pol1 flip cells: both models answer **DOWN**, truth is **UP**, on all 12. **When these two
frontier models agree on a flip cell, they are jointly, confidently WRONG 100% of the time.** Agreement
is not a safety signal here — it is a *danger* signal on exactly the cells that matter.

### 6. Abstain-gate value  (rule: abstain when gpt-5.5 ≠ Opus, else take the agreed sign)

| metric | value |
|---|---|
| KEPT set (scored, models agree) | 34 cases |
| **KEPT-set accuracy** | **21/34 = 0.62** |
| baseline: gpt-5.5 solo (scored) | 0.42 |
| baseline: Opus solo (scored) | **0.68** |
| FLIP cells correctly abstained (disagree) | 12/24 = **0.50** |
| GUESSABLE kept-and-right | 21/24 = **0.88** |
| grounded-sim on the FLIP cells the gate discards | 23/24 = **0.96** |

**The 2-model abstain-gate does NOT lift accuracy — 0.62 kept vs 0.68 Opus-solo, a small DROP.** It
works on the easy side (keeps 0.88 of GUESSABLE, correctly right) but **fails on the hard side**: it
correctly abstains on only half the flips, and the half it *keeps* are the §5 cells that are 0/12
wrong. So the gate poisons its own kept set with confidently-wrong flip calls. Worse, the flips it
throws away are exactly the ones grounded-sim solves 0.96 — the gate discards recoverable signal and
retains the toxic signal. **A same-family (words-only) council cannot gate itself on magnitude flips.**

### 7. 3-way note — does adding llama sharpen the flag?

| slice | 2-model flag (gpt55≠opus) | 3-model flag (not all 3 equal) |
|---|---|---|
| FLIP (24) | 0.50 | **1.00** |
| clean FLIP (12) | 0.50 | **1.00** |
| GUESSABLE (24) | 0.12 | 0.25 |

3-way KEPT set (all-3-agree): **19 cases, accuracy 18/19 = 0.95.**

**Adding llama sharpens the flip flag decisively: any-of-3-disagree flags 100% of FLIP cells** (vs 50%
for 2-model), because llama's optimism breaks whatever agreement gpt-5.5 and Opus reach — on the
salient-harm template Opus+gpt-5.5 both say DOWN but llama does not, restoring the disagreement. The
cost is modest extra flagging on GUESSABLE (0.25 vs 0.12), and the all-3-agree KEPT set is still 0.95.
So a **3-model heterogeneous** any-disagree gate is a far better abstain trigger than the 2-model one —
**but note it works by DIVERSITY of bias, not by any model actually knowing the flip answer.** None of
the three recovers a single flip; the 3-way gate is a good *abstain* detector, not a *predictor*.

---

## VERDICT

**(a) Does gpt-5.5 beat the flip-cell chance ceiling, or is it also magnitude-blind?**
**Magnitude-blind. It does not beat — or even reach — chance on flips: 0.00 on the clean-flip slice
(vs Opus 0.50, grounded 1.00).** gpt-5.5's distinctive behavior is a *balanced/abstaining* stance (it
almost never calls UP on ambiguous prose; splits UNSURE/DOWN), which is the most calibrated posture of
the three arms — but on the decisive magnitude-flip cells that stance just converts Opus's at-chance
coin-flip into an at-zero forfeit. The structural result holds across a **third frontier LLM**: no
words-only predictor reads the magnitude the prose withholds; only the grounded g-formula sim does.

**(b) Is gpt-5.5↔Opus disagreement a reliable abstain gate, or do two frontier models agree
confidently-wrong on the flips?** **The 2-model gate is NOT reliable — the two frontier models agree
confidently-WRONG on the flips.** On 12 of 24 FLIP cells gpt-5.5 and Opus agree, and on those 12 the
agreed sign is **0/12 correct** (both call DOWN, truth UP). The gate keeps those toxic cells and
discards the flips grounded-sim would solve (0.96), netting 0.62 kept-accuracy — *below* Opus-solo
0.68. Agreement between same-modality (words-only) models is not independence; it is shared blindness.
The one repair that works is **heterogeneity**: adding llama makes any-of-3-disagree flag 100% of flips
(all-3-agree kept set = 0.95) — a good *abstain trigger*, still not a *predictor*. The durable product
behavior remains: **detect the flip and abstain (best via diverse-model disagreement), then hand the
magnitude question to the grounded sim** — never let a council of words-only models vote a sign on a
counter-intuitive flip.
