# Design-partner outreach kit (ready-to-send)

Turnkey assets to START outreach. The ICP, qualification, and pilot mechanics are in
DESIGN_PARTNER_OUTREACH.md; this is the send-ready layer. **What only the founder can do:** actually
send these (from your identity / network) and book the calls — I can't send on your behalf.

## Build the first 15-target list (how to source names fast)
Target = mid-market, throughput-constrained experimenters (NOT Airbnb-scale). Sourcing, in order:
1. **Warm network** — ask 5 founder/investor/advisor contacts: "Who do you know running a lot of A/B
   tests at a $10–200M DTC / subscription / mobile / B2C-SaaS company?" Warm intros convert far higher.
2. **Tooling footprints** — companies publicly using Statsig / Eppo / GrowthBook / Optimizely / VWO
   (case studies, G2 reviews, conference talks) → they have experiment HISTORY. Pull the growth/exp lead.
3. **Communities** — CXL, Measurelab, Experiment Nation, Reforge/Demand Curve alumni; post + DM actives.
Track them in the sheet below; aim for ~15 to land 2–3.

## A. Cold email (primary — also in DESIGN_PARTNER_OUTREACH.md)
> **Subject:** Backtesting AI audience simulation against your A/B history
>
> Hi [Name] — I'm [Founder] at Sidira. We're building audience simulation to pre-screen which
> experiment ideas are worth testing, and we're validating it honestly before claiming anything.
>
> We're looking for 2–3 design partners who've run a solid number of A/B tests. The ask is low-risk:
> we backtest our simulation against your *past* experiments (known outcomes) and hand you a
> pre-registered accuracy scorecard for your domain — no production decisions, no traffic, just
> "could this have called your historical results?"
>
> If it's accurate, you get early access to prioritize your test roadmap and a say in the product. If
> not, you've spent ~a few hours and learned where AI simulation really stands. The persona build runs
> on your data in your environment / anonymized — raw user data doesn't have to leave your control.
>
> Worth 20 minutes to see if your experiment history fits?

## B. LinkedIn / DM variant (short)
> [Name] — building Sidira (AI audience simulation to pre-screen A/B ideas). Looking for 2–3 design
> partners with real A/B history: we backtest our model against your *past* experiments and give you a
> pre-registered accuracy scorecard — no traffic, no production risk. If it's good you get an early
> roadmap-prioritization tool; if not you've lost an hour. Open to a quick call?

## C. Warm-intro ask (to send to a mutual connection)
> Could you intro me to [Name] at [Company]? I'm looking for design partners with A/B-test history to
> backtest Sidira's audience-simulation accuracy — zero production risk to them (we score against their
> *past* experiments). One line from you and I'll take it from there.

## D. Tracking sheet (copy to a spreadsheet)
| Company | Contact / title | Segment | Source (warm/tool/community) | Status (to-contact / sent / replied / call / qualified / signed / passed) | Has ≥30 past experiments? | Renderable changes? | Notes / next step |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## E. On the qualification call (filter — full list in DESIGN_PARTNER_OUTREACH.md §5)
~30–50+ past experiments with clear winners? · changes renderable (UI/copy/pricing/flow)? ·
pre-treatment audience data to build packs? · a champion who'll get data + act? · any counter-intuitive
outcomes? → if yes, run the **PILOT_SCORECARD_TEMPLATE.md** (seal the GO/NO-GO rule before the backtest).
**Tell them up front:** for a high-confidence run we need a **v1.1-style rich per-user feature set** and a
**rendered treatment** (not just a prose change) — proven on the Streamly dry-run.

## Cadence
~15 contacted → ~5 calls → ~2–3 signed across *different* domains (don't conclude the thesis from one).
Run this IN PARALLEL with the $2–3k self-run PoC (POC_RUNBOOK.md) — partner data is free + representative;
the PoC is the owned/fast hedge. See [[directional-sim-campaign-standing]].
