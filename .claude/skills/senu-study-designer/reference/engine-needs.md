# Engine needs — the taxonomy, the wedge, and the standing gaps

*Read this before proposing a study. It encodes what the engine can do, what it can't yet, and therefore
what data is most valuable to manufacture. Keep it in sync with `research/engine-strength-campaign/LEDGER.md`
and `founder-readout/simulation-engine-where-we-landed.md`.*

## The wedge (what the engine is uniquely good at)

**Magnitude-driven trade-offs.** When a change helps through one mechanism and hurts through another and the
net sign depends on *unstated magnitudes*, no words-only predictor (human PM or any LLM — llama, Opus,
gpt-5.5 all measured at/below chance) can call it; the grounded g-formula sim, reading mediator strengths
from real data, gets it (1.00 on the AMBDOM flip cells). **The most valuable Senu cases are ones that sit in
this regime** — real, per-user, two-mechanism, magnitude-decides-the-sign.

## The counter-intuitive taxonomy (~12 recurring failure modes)

The 80/20 bet: ~80% of consequential surprises fall into a small finite set. Over-sample these; each Senu
study should target one (or a realistic combination) and be labeled with it.

1. **Cannibalization** — a new option steals from a more valuable existing one (net revenue down though usage up).
2. **Trade-down** — users shift to a cheaper/lower-margin path.
3. **Cross-channel / feature substitution** — gains in one surface are losses in another.
4. **Novelty / primacy decay** — early lift fades; the real steady-state is flat or negative.
5. **Gross-vs-net economics** — engagement up, unit economics down (the boundary case; edge = estimability).
6. **Segment-mix sign-flip** — +for one segment, −for another; the net flips on the population mix.
7. **Declutter / relevance paradox** — removing content raises per-item relevance but lowers total.
8. **Friction-as-filter** — added friction lowers volume but raises downstream quality/conversion (or vice versa).
9. **Congestion / capacity** — more demand degrades the experience that drove it.
10. **Habit disruption** — a "better" flow breaks an ingrained one, hurting retention short-term.
11. **Anchoring / reference-point** — the change moves the comparison, not the absolute.
12. **Paywall / nudge removal** — removing a friction that was secretly the conversion trigger (skip-cap case).

If a proposed study doesn't map to one of these (or a deliberate new pattern), say so — it may be low-value.

## Standing gaps (highest-value targets, priority order)

1. **The dominance-flip / B2 gap (TOP PRIORITY).** The wedge is proven on synthetic + n=1 real (Cookie Cats).
   We have NOT found *naturally-ambiguous real data* where two opposing mechanisms produce a true
   population-level dominance flip. A Senu study engineered to sit exactly on that knife-edge — where the net
   sign genuinely depends on the measured magnitudes and could plausibly go either way — is the single most
   valuable case to manufacture. It's what promotes the wedge from LEAD to PROMOTED.
2. **Uncovered taxonomy patterns.** Any pattern above with no labeled Senu case. Cannibalization,
   gross-vs-net, and segment-mix flips are especially load-bearing for the "audit your test wins" wedge.
3. **Negative-control / confounding validation.** Cases that let a hidden confounder fake the mechanism, to
   test whether the watchdog correctly ABSTAINS (CAN'T-VALIDATE) rather than confidently mis-calling.
4. **Per-customer transfer.** Does a mechanism learned on one population hold on another? Needed to validate
   the Senu-trained model's transfer claim (the fine-tune track, #536).
5. **Abstain-boundary mapping.** Cases whose mechanism is deliberately *not* observable in the behavior
   schema — to confirm the engine abstains instead of guessing (the "swipe-delete" boundary).

## Discipline reminders (from the calibration contract + campaign lessons)

- **3 sealed artifacts:** human-truth ≠ engine-blind ≠ measured-truth. WIN = engine-blind vs measured-truth.
- **Never author one artifact to match another.** Register only a genuine counter-intuitive lean.
- **Outcomes carry variance**, not a ≥1 ceiling binary (Beat-the-Clock Exp-2 lesson).
- **Role-named arms at the source** (game emits `calm`/`urgent`), headline-arm first, zero game↔engine build
  coupling (contract §11).
- **Power-first:** design to pass `preFlightCheck`'s blocking `power` check, don't discover N at the gate.
- **Learning-curve gate (Phase-1, month 4–5):** track whether new counter-intuitive cases increasingly fall
  into already-seen patterns (curve bends → taxonomy is finite → bet works) vs keep surprising (flat → stop).
  Every study should be tagged with its taxonomy pattern so this curve can be measured.

## What "improves the engine" concretely means

A study improves the engine if its results do at least one of:
- **Promote** a capability (LEAD → PROMOTED) by supplying the missing real evidence (esp. the B2 flip).
- **Extend coverage** to a taxonomy pattern the engine hasn't been validated on.
- **Validate the guard** (confirm it abstains under confounding / calls the flip under clean data).
- **Feed the calibrator** (#222) with a real predicted-vs-actual pair (engine-blind vs measured).
- **Test transfer** for the Senu-trained model track.

Rank proposals by which of these they achieve and how decisively.
