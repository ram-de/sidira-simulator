# Hypothesis H-001 — Smart Resume hero

> Submission this PM would paste into Pythia.
> Models a single feature change against the Feature Pack snapshot `2026-W21`
> and the Persona Pack `v_1` of customer `streamly_sample`.

---

## PR / change summary

**Title:** Replace the Continue Watching rail with a single Smart Resume hero.

**Author:** pm-jules (Product, Growth Pod)
**Target release:** 2026-W23
**Linked design:** `figma://streamly-sample/Home-2026-W23-SmartResume`
**Repos affected (in the would-be customer product):** `streamly-web`, `streamly-tv`, `streamly-mobile-rn`
**Feature pack capability touched:** `continue_watching` (modifies `home.continue_watching_rail`, adds `home.smart_resume_hero`)

### What changes

Currently the home screen shows:
1. Editorial / personalized **hero** at the top
2. **Continue Watching** rail (up to 10 tiles)
3. A stack of personalized rows (`Because you watched`, `Top picks for you`, …)

The proposal collapses (1) and (2) into a single **Smart Resume hero**:

- Top of home is one large card with the single most likely thing to resume:
  - For series viewers: the next episode (resume or next-up), full-bleed art, one big `Resume` button, a small `More options ↓` affordance that expands the legacy multi-tile row inline.
  - For movie / lapsed-mid-movie viewers: the in-progress movie with progress bar and `Resume`.
  - For cold-start (no in-progress titles): the existing editorial hero is shown verbatim (no regression for new users).
- The horizontal Continue Watching rail is **removed from the top of home** when a Smart Resume target exists. Users can still reach the full list via the `More options ↓` expander or via a `My Stuff` tab.

### Why we think this is a good idea

Heavy serial viewers tell us in NPS verbatims that the row is noise — they always tap the leftmost tile. Collapsing to a single hero is supposed to be one fewer decision and one fewer tap. Eng cost is small; the rail is reused inside the expander.

---

## Hypothesis (the thing Pythia is being asked to evaluate)

> **H-001:** Replacing the Continue Watching rail with a single Smart Resume hero will *increase* the rate at which a home-screen visit ends in a play, *without* materially decreasing the diversity of titles started.

### Predicted directional effects (per persona)

These predictions are explicit so the simulator can disagree with them.

| Persona                          | Predicted reaction              | Why we think so                                                                                |
|----------------------------------|----------------------------------|-------------------------------------------------------------------------------------------------|
| `alex_binge_marathoner`          | **Strong positive**              | Currently taps the leftmost tile every time; Smart Resume *is* that tile, made enormous.        |
| `marco_background_player`        | **Positive**                     | Wants the comfort show to keep playing without remote work; one button matches that intent.     |
| `tess_new_trialer`               | **Slightly negative**            | Cold-start should fall back to the editorial hero (no regression) — but during day 8-14 they'll have a sloppy resume target and the hero may pin them to it. |
| `rivka_weekend_movie_night`      | **Negative**                     | This persona deliberately browses for 5+ minutes; removing the visible rail of options will frustrate the ritual unless `More options` is obvious. |
| `noor_niche_genre_loyalist`      | **Neutral**                      | Already largely ignores the home surface; arrives via external referral and direct title links. |
| `ken_price_sensitive_lapser`     | **Neutral**                      | Not engaged enough to be affected; cancel intent is set elsewhere.                              |

### What "the answer is yes" looks like

- Weighted (`order_weighted`) home-visit-to-play uplift estimate ≥ +3 percentage points absolute, with confidence ≥ 0.70.
- No persona produces a strong-negative reaction worth ≥ 15% of order-weighted volume **unless** Pythia also surfaces a concrete mitigation (e.g., "show the row by default for households with ≥2 active profiles").
- Diversity-of-titles-started reduction ≤ 5% per simulated week.

### What "the answer is no, or not yet" looks like

- Pythia returns either:
  - A net negative on weighted home-visit-to-play, **or**
  - A strong-negative cluster (e.g., `rivka_weekend_movie_night` reacting badly) holding ≥15% of order-weighted volume with no proposed mitigation, **or**
  - Confidence < 0.55 (Pythia is itself uncertain — likely a feature-pack ambiguity).

### Diagnostic questions for agent chat after the simulation

After the simulation lands, PM intends to ask the agents directly:

1. (to `rivka_weekend_movie_night`) "If the rail is gone from the top of home, how do you decide what to watch tonight? Walk me through Friday."
2. (to `alex_binge_marathoner`) "If Smart Resume points to the wrong next-up — say, the wrong show — what do you do? Tap into it anyway, or scroll past?"
3. (to `marco_background_player`) "Would Smart Resume help reduce the number of 'are you still watching?' prompts you dismiss per week? Why or why not?"
4. (to `tess_new_trialer`) "On day 9 of your trial, you've sampled 5 titles. What does Smart Resume show you, and is that the right thing?"

These chats are also the place to capture "realistic / not realistic" calibration signal for Layer-3.

---

## Why this is a useful test case for Pythia itself

- **Forces the simulator to disagree across personas.** A single weighted number would hide the conflict between `alex_binge_marathoner` (loves it) and `rivka_weekend_movie_night` (hates it). The PM specifically wants to see the simulator surface that.
- **Touches a capability already in the Feature Pack.** The change is anchored to `continue_watching`, so simulator can reason about it against the reverse-PRD and reverse-Figma rather than from a free-form description.
- **Has a clean "yes / no / not yet" gate.** The success criteria are quantitative and pre-registered, so Layer-3 calibration can later score Pythia against real A/B results without rewriting the criteria after the fact.
