# Design-partner outreach plan — validate the screening claim on real experiment history

**Status:** living doc (2026-06-18). **Why now:** the #342 campaign exhausted the cheap
technical levers with pre-registered negatives (see [[directional-sim-campaign-standing]] /
`hillstrom-benchmark/BENCHMARK_REPORT.md`). The product's commercial value is gated on the
*directional/screening* claim, which is unproven on public data and only testable at full
fidelity = a real customer's persona pack + real change + known outcome. **A historical-data
design-partner pilot is simultaneously the validation and the go-to-market on-ramp.**

**Goal:** sign **2–3 design partners** with real A/B experiment history and backtest the
screening claim against their known outcomes.

## 1. Design-partner ICP

NOT Airbnb-scale (won't engage a tiny startup; their bottleneck is test *throughput*, not
ideas; procurement friction). Target mid-market companies that **already experiment but are
throughput-constrained**:

- Growth-stage **DTC / e-commerce, subscription, mobile apps, B2C SaaS** (~$10M–$200M revenue).
- **Must-haves:** (a) real experiment history with **known winners** (the backtest substrate);
  (b) per-user / audience data to build persona packs; (c) **renderable** changes
  (UI / copy / pricing / flow / marketing — not opaque algorithm tweaks); (d) an internal champion.
- **Champion titles:** Head of Growth / Experimentation / CRO / Product Analytics / Lifecycle.
- **Bonus:** a history with **counter-intuitive** outcomes (the discriminating cases).

## 2. The offer (low-risk value exchange)

> "We backtest our audience simulation against your *past* experiments and give you a
> pre-registered accuracy scorecard for your domain. No production decisions, no traffic spent.
> If it's accurate, you get an early tool to prioritize your test roadmap and a voice in the
> product; if not, you've spent a few hours and learned where AI simulation actually stands."

Converts because: zero production risk, uses data they already have, honest answer either way.
We get: the validation substrate + a reference logo + product feedback.

## 3. Channels (priority order)

1. **Warm intros first** (founders' + investors' + advisors' networks). Ask specifically for
   "a head of growth/experimentation at a company that runs lots of A/B tests."
2. **Experimentation communities** — Statsig / Eppo / GrowthBook / Optimizely user communities;
   CXL & Measurelab (CRO); Experiment Nation / experimentation Slacks; Reforge & Demand Curve alumni.
3. **Targeted cold** — hand-built list of ~40 mid-market DTC/SaaS that publicly discuss
   experimentation (case studies, conference talks).
4. **Content as inbound** — publish the honest benchmark story ("We tried to predict A/B winners
   with AI — here's what actually worked"). The honesty is the hook; it pre-qualifies trust-oriented buyers.

## 4. Cold email (draft)

> **Subject:** Backtesting AI audience simulation against your A/B history
>
> Hi [Name] — I'm [Founder] at Sidira. We're building audience simulation to pre-screen which
> experiment ideas are worth testing, and we're validating it honestly before claiming anything.
>
> We're looking for 2–3 design partners who've run a solid number of A/B tests. The ask is
> low-risk: we backtest our simulation against your *past* experiments (known outcomes) and hand
> you a pre-registered accuracy scorecard for your domain — no production decisions, no traffic,
> just "could this have called your historical results?"
>
> If it's accurate, you get early access to prioritize your test roadmap and a say in the product.
> If not, you've spent ~a few hours and learned where AI simulation really stands. The persona
> build runs on your data in your environment / anonymized — raw user data doesn't have to leave
> your control.
>
> Worth 20 minutes to see if your experiment history fits?

## 5. Qualification (first call)

- How many past experiments with **clear recorded winners**? (~30–50+ for a meaningful backtest;
  fewer detects only large effects.)
- Are the **changes renderable**?
- **Pre-treatment audience data** to build packs?
- A **champion** who'll get us data and act on results?
- Any **counter-intuitive** outcomes in their history?

## 6. Pilot mechanics + honesty gate

- Scope: N historical experiments → build packs from their data → run the engine blinded →
  score direction/screening vs known winners. Use the **PILOT_SCORECARD_TEMPLATE.md**.
- **Pre-register GO / PIVOT / KILL before running** (hash + commit). Protects against
  rationalizing a weak result.
- Data handling: persona build runs on their data without exfiltrating raw PII (hardened with
  `--require-llm`); offer NDA + in-environment execution to kill the security objection early.

## 7. Targets & cadence

- Build a 40-name list → ~15 conversations → ~3–5 qualified → **2–3 signed across different
  domains** (don't conclude the thesis from one partner; one domain's data can be unfavorable).
- ~3–4 weeks to first signed partner if warm intros land; backtest itself is days once data is in.

## 8. What the pilot decides (tie to the standing)

- **GO** (screens well overall) → pursue the screening product; you now have what serious buyers want.
- **NARROW** (works on change-class X only) → scope the product to X — a real, honest wedge.
- **PIVOT** (ranks batches / predicts comprehension/objections but not per-test winners) → change
  the predicted target to where the tech is strong.
- **KILL** (clean full-fidelity null across classes + ≥2 partners) → redeploy the assets
  (persona pipeline, crawler, engine, eval methodology) to an adjacent problem; don't bleed out.
