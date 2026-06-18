# PoC vendor shortlist + cost estimate (companion to POC_SELF_RUN_AB_SPEC.md)

Who to contact to run the self-run A/B PoC. **Structural fact:** recruitment and task execution are
usually *separate layers* — panels recruit + profile + redirect; you host the A/B task externally
(jsPsych / Gorilla / your app) and they route participants in/out via a completion code. Plan a
**recruit-where + build-where + analyze-how** stack. (Only Testable/Qualtrics bundle build+recruit.)

## Shortlist — contact/sign up for the PoC
1. **Prolific** *(recruit + profile)* — best default. Vetted ~200k pool, 300+ prescreens + custom
   screeners, first-class external-task redirect, strong ID/bot controls, hundreds in hours.
   ~$12/hr reward + **33.3% academic / 42.8% commercial** fee.
2. **CloudResearch Connect** *(recruit + profile)* — near-equal alternate; single fee (25/40%), very
   fast (500 in 1–2 hrs), strong vetting. Use as a 2nd panel to confirm the winner replicates.
3. **Testable** *(build + recruit in one)* — only budget-safe all-in-one with public pricing
   ($0–699/yr + commission, pay min $8/hr). Fastest single-vendor start for test #1.
4. **Gorilla.sc** *(build)* — best behavioral-task builder (native randomization, click/RT capture,
   attention checks). Pair with Prolific. **Commercial token price is sales-gated — get a quote.**
5. **Meta Ads → self-hosted task** *(alt recruit + real behavior)* — cheapest real-behavior-at-scale,
   esp. PH/SEA; the route to the powered benchmark. Build profiling + captcha/attention into the page.

**Skip for the PoC:** Respondent.io (wrong economics), raw MTurk (QC burden), Appen/Toloka/Remotasks
(vacated the research market), Optimizely/VWO/Qualtrics (over budget), all usability platforms (qual only).

## Recommended stack
- **PoC (~$1–3k):** recruit+profile on **Prolific** (custom screener for attitudinal features, keyed on
  participant ID); build task on **Gorilla** (no-code) or **jsPsych/lab.js** self-host (free, needs a
  dev) — or **Testable** to start fastest; collect the profiling survey *inside the task tool* keyed on
  ID so features join to outcomes; analyze in a notebook (two-proportion test + CIs — no feature-flag
  tool needed when the panel handles assignment); cross-check one test on **CloudResearch Connect**.
- **Powered benchmark ($10–15k):** scale on Prolific + CloudResearch (+ Clickworker / a SEA panel like
  Cint-API or Milieu for cost/geo); OR shift volume to **self-hosted task + Meta PH/SEA ad traffic**
  with **GrowthBook (free OSS)** or **Statsig (free 2M events)** doing assignment + stats + your own
  captcha/timing/attention filters. Offshore the build via **Upwork** (~$1–2k, escrow) if bandwidth is short.

## Cost estimate (vendor-grounded)

**PoC — 2–3 non-obvious A/Bs (~750 participants):**
| path | participant cost | build | total |
|---|---|---|---|
| Prolific + jsPsych (self-host, free build) | ~$3–4/participant (10-min profiling+task incl. fee) → ~$2.3–3k | ~$0 (OSS) + dev time | **~$2.5–3.5k** |
| Prolific + Gorilla | + Gorilla tokens (~$1–2+/participant; commercial gated) | tokens | **~$3–5k** (confirm token quote) |
| Testable all-in-one | min $8–12/hr + 10–30% commission | included | **~$1.5–3k** |
| **Meta PH ad traffic + self-host** | ~$0.38/completion (CPC ~$0.15 × ~40% complete) × 750 ≈ **~$285** | build + captcha | **~$0.5–1.5k** (but NO clean profiling) |

**Powered benchmark — 10–20 tests (~4,500 participants):**
- Panel path (Prolific/CloudResearch, large-effect designs ~300/test): **~$12–18k**.
- PH/SEA ad-traffic path (GrowthBook free + self-host): **~$2–5k** traffic — cheapest *if* audience fits
  and you accept noisier data + no survey profiling.

**Swing factors:** (1) design for LARGE counter-intuitive effects → ~150/arm, or N (and cost) balloons
10–20× on subtle effects; (2) cheap pool vs quality panel ≈ a wash after attention-check overhead;
(3) ad traffic is dramatically cheaper but trades away clean profiling + one-person-one-exposure.

## Pricing to confirm directly (highest-impact unknowns)
- Prolific exact fee tier + whether custom-screener answers export per-participant.
- CloudResearch Connect — no public rate card; written quote + commercial-use terms.
- Gorilla.sc commercial token price (academic £1.09 / public £1.71 are public; commercial gated).
- SEA panels (Cint, Milieu ~$2k/n=500, Clickworker) — all quote-based.
- **Ad CPC varies 5–10× by geo/industry — run a $100–200 live pilot before budgeting the benchmark.**

## Bottom line
Cheapest *valid* PoC ≈ **$2–3k** (Prolific + free OSS task), gating a **~$12–18k** powered benchmark
(or **~$2–5k** via PH ad traffic). All far below the value at stake — and a **design partner's history
remains free**, so run the PoC in parallel with outreach, not instead of it. See [[directional-sim-campaign-standing]].
