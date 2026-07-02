# SCORECARD — GNCE (Grounded Novel-Counterfactual Extrapolation)

LLM arm: **REAL**  ·  Arm A seeds/archetype: 3  ·  n=8000/case  ·  Arm B: Hillstrom RCT (real)

Sealed against PREREG_GNCE.md. No re-tuning. Refutations reported as refutations.


## Per-archetype sign-accuracy

| archetype | truth | GROUNDED | LLM | ORACLE | grounded abstain |
|---|---|---|---|---|---|
| MED-FLIP+ | + | 1.00 (3/3) | 1.00 (3/3) | 1.00 (3/3) | 0/3 |
| MED-FLIP- | - | 1.00 (3/3) | 1.00 (3/3) | 1.00 (3/3) | 0/3 |
| DIRECT-DOM | + | 1.00 (3/3) | 1.00 (3/3) | 1.00 (3/3) | 0/3 |
| NULL | 0 | 0.67 (2/3) | 0.00 (0/3) | 1.00 (3/3) | 0/3 |
| MED-HIDDEN+ | + | 0.00 (0/3) | 1.00 (3/3) | 1.00 (3/3) | 3/3 |
| MED-CONF | + | 1.00 (3/3) | 1.00 (3/3) | 1.00 (3/3) | 0/3 |
| MED-HIDCONF | + | 1.00 (3/3) | 1.00 (3/3) | 1.00 (3/3) | 0/3 |

## Sealed predictions — verdicts

| P | claim (short) | statistic | verdict |
|---|---|---|---|
| P1 | MED-FLIP±: grounded≥.80, LLM≤.40, Δ≥3 cells | grounded 1.00 (6/6), LLM 1.00 (6/6), Δ=0 | **REFUTED** |
| P2 | DIRECT-DOM: both ≥.70 | grounded 1.00, LLM 1.00 | **HELD** |
| P3 | NULL: grounded c-or-abstain≥.70 & LLM< grounded | grounded 0.67 (2/3), LLM 0.00 (0/3) | **PARTIAL** |
| P4 | MED-HIDDEN: forced≤.55, abstain≥.75, ORACLE≥.80 | forced 0.00, abstain 1.00, ORACLE 1.00 | **HELD** |
| P5a | MED-CONF: adjusted≥.70 & unadjusted flips≥1 | adj 1.00 (3/3), unadj flips 2/3 | **HELD** |
| P6 | MED-HIDCONF: grounded≤.55 (hidden-U breaks it) | grounded 1.00 (3/3) | **REFUTED** |
| P7 | Hillstrom: predicted sign POSITIVE | pred +0.281pp (sign +), measured +0.495pp (+) | **HELD** |
| P8 | Hillstrom: predicted/measured ratio > 1.2 (biased UP) | ratio 0.57 | **REFUTED** |
| P9 | placebo within ±1 measured SE of 0 | pred +0.3301pp, 1SE=0.4171pp | **HELD** |

## Why P1 came out as it did (the load-bearing nuance)

- PURE-INTUITION prior (sign of the *salient/direct* framing) on MED-FLIP±: **0.00** — i.e. raw intuition is wrong on the counter-intuitive flips, as the prereg's mental model assumed.
- But the ACTUAL Groq LLM, given the qualitative narrative that *names the beneficial mechanism*, REASONS past intuition to **1.00** on MED-FLIP±. It is not fooled.
- GROUNDED-SIM is also 1.00. So both land the sign: the narrative (per the prereg's own example wording) hands the LLM the mediator's *direction* in words, so a strong reasoner only needs to weigh two stated effects — which it does. The grounded edge this test could show is therefore the edge over RAW intuition, not over a mechanism-reasoning LLM. The untested differentiator: cases where the mediated path's *direction is known but its DOMINANCE/magnitude is ambiguous* — there qualitative weighing fails and only the data-grounded g-formula resolves it. This battery fixes magnitudes so the dominant sign is qualitatively guessable; that is why the LLM keeps up.

## Key cells

- GROUNDED − LLM correct-count delta on MED-FLIP±: **0** (grounded 6/6, LLM 6/6).
- MED-HIDDEN+ grounded abstain rate: **1.00** (3/3); forced-guess accuracy 0.00; ORACLE 1.00.
- Hillstrom: predicted lift **+0.281pp** vs measured naive **+0.495pp** (adjusted +0.499pp); ratio **0.57**; signs pred=+ / measured=+.
- Placebo (pseudo-outcome=mens): predicted **+0.3301pp**, measured -0.3288pp, 1 SE = 0.4171pp, within-1SE=True.
- LLM arm was **REAL**.

## Verdict summary

P1=REFUTED · P2=HELD · P3=PARTIAL · P4=HELD · P5a=HELD · P6=REFUTED · P7=HELD · P8=REFUTED · P9=HELD
