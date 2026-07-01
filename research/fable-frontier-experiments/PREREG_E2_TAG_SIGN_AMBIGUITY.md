# PREREG — E2: Same-Tag, Opposite-Sign Library Audit

**Campaign:** fable-research data-efficiency frontier (sessions/fable-research/PAPER.md §7-E2)
**Date sealed:** 2026-07-01, before any tagging call is made.

## Question

If the effect library retrieves "similar mechanism" cases by taxonomy tag, can the tag ever be allowed to pick a sign? Measured as: how often do cases carrying the **same mechanism tag** have **opposite-signed true effects**?

## Case material

**Primary arm (real cases, headline number):** the 15 scored portfolio cases in `sessions/agent-behavior-spec/portfolio-benchmark/PORTFOLIO_CASES_V3.json` (each with `real_winner` ground truth) + Hillstrom (2 outcome-level cases: email→visit +, email→conversion + / spend ~0 — encoded per the sealed spike results) + Cookie Cats gate-move (already in portfolio; not double-counted). Truth = `real_winner` (treatment=+, control=−).

**Secondary arm (density, labeled synthetic):** the 24 generated E1 composition cells (tag density is guaranteed by construction there; reported separately, never pooled with the real arm).

## Tagging procedure

Tagger = translator-style LLM classifier (claude-opus-4-8, temperature 0), mirroring the production `mechanism_translator.py` posture (structured JSON out, no predicted sign, no outcome information in the prompt). Input: control description + treatment description + metric name ONLY (no effect, no winner, no `counter_intuitive` field — leakage guard). Output per case:

- `family`: one of {mix_shift, gross_vs_net, trade_down_cannibalization, friction_change, salience_attention, trust_signal, habit_loop, layout_navigation, personalization, other} (10-way; pre-registered closed set)
- `mediator_role`: the named behavioral lever (free text, normalized to lowercase snake_case)
- **Tag = `family` alone (primary grain)** and `family+mediator_role` (secondary, finer grain — reported for context).

Stability: 3 tagging runs; a case's tag = majority; no majority → tag `unstable` (reported, excluded from ambiguity denominator, counted separately).

## Pre-registered metric

For each tag group with ≥2 members (real arm, primary grain): group is **sign-ambiguous** if it contains both a `+` and a `−` true effect.

**AMBIGUITY = (# cases in sign-ambiguous groups) / (# cases in groups of ≥2)**

## Pre-registered outcomes

- **KILL (ban tag-retrieval from sign selection):** AMBIGUITY > 30% on the real arm → mechanism-tag retrieval is permanently banned from selecting a sign; taxonomy remains an ensemble/uncertainty axis only (paper rule R2 hardens into a measured result).
- **SURVIVE:** AMBIGUITY ≤ 30% AND ≥5 real cases live in ≥2-member groups → tag-conditioned sign priors may be *investigated* (never shipped without E3-class validation).
- **UNMEASURABLE:** if <5 real cases fall in ≥2-member groups, the real arm is declared underpowered; report the synthetic arm as directional evidence only and the verdict defaults to the conservative branch (tags stay an uncertainty axis).
- Secondary reads (informational): finer-grain ambiguity; tag stability rate; per-family sign base rates (the "always-up families exist?" question).

## Leakage guards

Tagger prompt contains no outcome, no winner, no effect size, no counter-intuitive flag; prompts logged verbatim in the results JSON for audit.
