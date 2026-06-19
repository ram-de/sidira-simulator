# Paid recruitment — India / Chennai (scale-up beyond friends-&-family)

For getting MORE players paid (beyond the free F&F seed). Companion to
`sessions/agent-behavior-spec/POC_VENDOR_SHORTLIST.md` (which is US-oriented). **Every panel/agency
price below is QUOTE-ONLY — verify directly; ad/campus figures are calibration estimates.**

## Three headline truths
1. **No vendor publishes India CPI** — all quote-only.
2. **Prolific & CloudResearch Connect do NOT serve India** (OECD-/US-only) → use them for the US half
   of the pool, not the India half.
3. **Microtask boards (Clickworker/Microworkers/MTurk) can't target a city** and give professional
   task-takers, not a representative Chennai consumer sample → OK for QA/flow-testing only.

## Ranked shortlist (cheapest valid path first)
1. **Meta self-serve ads, Chennai geo + Tamil/English, conversion-optimized** — cheapest route to real
   local consumers you control end-to-end. India Meta CPC ~$0.05–0.25; realistic **~$3–5 per *valid*
   completion** all-in (ad + incentive + fraud filtering) → 60–100 ≈ $180–500. **Run a $30–50 pilot
   first** to calibrate. Mandatory anti-fraud (India inventory has ~20–35% invalid traffic): pay
   incentive **only on validation**, optimize the campaign for a validated-completion conversion event
   (not clicks), layered on-page screening (honeypot + attention traps + completion-time floor +
   device/IP dedupe). Pay via UPI/Amazon Pay (~₹50–150). Advertise honestly ("short research game,
   get ₹X") — no "earn money fast" framing.
2. **Paid student-recruiter + campus WhatsApp/Telegram (unique single-use links)** — ~**$75–200 all-in**,
   fastest, in budget, *if* a young/student skew is acceptable. Hire 1–2 students via Internshala/Apna;
   enforce unique links + server-side completion verification + pay-on-valid; mix 2–3 colleges to dilute
   single-site/gender skew (several Chennai colleges are women's-only).
3. **Cint (Cint Exchange)** — the only true self-serve panel marketplace purpose-built for external-URL
   redirect that plausibly fits the budget. Verify in-platform: India CPI, account minimum/deposit,
   Chennai/Tamil Nadu sub-national granularity, Tamil delivery. Best path for a *cleaner, representative*
   sample than ads/campus.
4. **Kantar Profiles (Gateway API)** — strong fallback to Cint (best-documented fraud controls + a
   confirmed redirect API). Ask the **minimum project spend** up front (the real risk at this size).
5. **Smallest Chennai-local MR vendor** (ARS Market Research, then PannelPlus/Brand Kare) — only for a
   managed Tamil-native recruit; negotiate a stripped-down online-redirect job. Likely above budget.

**Skip:** Prolific / CloudResearch Connect (no India), Sago & GfK/NIQ (wrong mechanic/geo), big agencies
Hansa/Kadence/Ipsos/Nielsen (minimums ~$1.8–6k, far above budget), microtask boards for *representative*
data (city-untargetable).

## For OUR US+India split pool
- **F&F itself needs no vendor** — just send the per-recipient links to people you know (free, high
  completion). Vendors are for the *paid scale-up*.
- If scaling paid: **US half** → Prolific / CloudResearch Connect (they serve US, ~$2–4/complete, clean
  redirect + screener); **India half** → Meta Chennai ads (cheapest) or Cint.
- Consistency rule still holds: build the persona pack from the **same pooled players** you score against
  (US+India together = one consistent pool). Don't build from one group and test another. See
  [[directional-sim-campaign-standing]] / `FF_GAME_DESIGN.md`.
- Once the game is hosted (#445), **the Meta-geo-ads route is the cheapest, most controllable scale path**
  for the India side — and it works identically for any geo, so the same hosted link scales worldwide.
