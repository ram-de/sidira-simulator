# Test-Win Generalization & Incrementality Audit — one-page template

**Use when:** either (a) a feature won in one market / segment / submarket and someone wants to roll
it out broadly — *"it worked in X, ship it everywhere"*; or (b) a promo / subsidy / fee change claims
to **generate incremental volume** — *"this grows orders for everyone."* The seductive, expensive
cases: real activity, but redistributed or substituted rather than net-new.

**Goal:** decide **before** the broad rollout whether the headline is **net-new value** or **gross
activity that moved from somewhere else**, by reading the experiment's **own internals**. A positive
headline metric is NOT sufficient evidence. The single most important question is the **counterfactual**:
*incremental relative to what the customer would otherwise have done?*

---

## Step 0 — Pull these from the winning experiment
- Headline metric Δ, CI, p-value
- **Per-order economics:** basket / subtotal Δ, **spend-per-customer Δ**, **contribution margin / order Δ**
- **Volume decomposition:** orders Δ vs active-customers Δ vs **frequency Δ** (a win on count ≠ a win on money)
- **Mix shift:** which merchants / SKUs / destinations / segments gained vs lost share
- **Net vs gross business metric (GOV / revenue):** incremental NEW demand vs redistributed
- **Incrementality decomposition:** incremental orders ÷ total *treated/subsidized* orders; and **what
  ELSE moved in the opposite direction** (other channels/states the same customer occupies — pickup,
  organic, full-price). A treated metric up while a sibling metric falls ≈ substitution, not growth.
- The **structural definition of the winning segment X** — what actually makes X special

## Step 1 — Is the win real demand, or redistribution / substitution? (the 6 tells)
Each tell is a red flag *even when the headline is positive*:
1. **Mix-shift win** — gains came from share moving between merchants/SKUs, not net-new demand.
2. **Shrinking baskets** — subtotal / AOV down → customers trading *down*, not buying more.
3. **Flat spend-per-customer** — lift is order-count / active-count only; no money growth.
4. **Net business metric ≈ a wash** — the winner's gain ≈ some loser's loss (a competitor/segment paid for it).
5. **Cannibalizes a higher-value state** — the win erodes a premium product (membership, full-price, loyalty, LTV).
6. **Counterfactual substitution** — the "new" activity *replaced a cheaper/existing state the same
   customer already occupied* (pickup→paid delivery, organic→paid, full-price→promo). The treated metric
   rises while its sibling falls ≈ the same amount → **net-new ≈ 0; you paid to relabel volume you
   already had.** Ask: *would this have happened anyway, just through a different (cheaper-to-serve)
   door?*

More tells firing = less the headline means. Tells 1/4/6 are the **gross-vs-net** family; always pull
the sibling metric that could be falling.

## Step 2 — Name the effect-modifier (one sentence)
> *"This worked because **⟨property of X⟩**. The sign flips wherever **⟨property⟩** is absent."*

## Step 3 — Transfer test
Is the effect-modifier **present in the target markets**?
- **Yes** → win likely generalizes.
- **No** → expect attenuation, null, or **sign inversion**. Do not extrapolate the headline.
- **Unknown** → the broad rollout is a real experiment, not a confirmation. Treat it as such.

## Step 4 — Fix the scorecard before testing
Make the PRIMARY endpoint the thing actually at risk — **margin, durable frequency, net GOV, rejoin/LTV** —
not the surface metric that's set up to win. Pre-register it.

## Verdict
| Verdict | Pattern |
|---|---|
| **SHIP-SAFE** | positive headline + 0 tells + effect-modifier present broadly |
| **FRAGILE WIN** | positive headline but ≥2 tells and/or effect-modifier absent → broad test on the real endpoint, expect non-replication |
| **REDISTRIBUTION / TRAP** | headline driven by mix-shift + net-wash + cannibalization → not a rollout candidate |

---

### Worked example — a "it worked in market X" price-transparency win → broad rollout
*(abstract archetype; numbers illustrative)*

| Step | Reading |
|---|---|
| Headline | orders **up** (sig) — looks like a win |
| Tells | **mix-shift family fires:** share moved to the cheapest, full-selection destination while premium destinations lost; baskets **shrank**; spend-per-customer **flat**; net business metric **a wash** (the magnet's gain ≈ a competitor's loss) |
| Effect-modifier | *worked because the price-magnet was cheap **AND full-selection**; the sign flips wherever the cheapest destination has weak selection* |
| Transfer | in target markets the cheapest destination has **weak selection → effect-modifier absent** |
| Verdict | **FRAGILE WIN** → on broad rollout the headline inverts for high-value users (a trade-down accelerator). |

The audit reaches the right call from the winning experiment's internals alone — no simulation,
no broad test needed to raise the alarm. This is the empirical/heterogeneity route's job.

### Worked example — a subsidy that claims to "generate incremental volume" (incrementality case)
*(abstract archetype; numbers illustrative)* — *Claim:* "the subsidy generates **incremental** activity
that wouldn't have happened, growing volume for everyone." A demand-side persona simulation endorses it
(near-unanimous "more", "incremental"); the audit lens predicts the opposite via the **counterfactual
substitution tell (#6)**.

| Step | Reading |
|---|---|
| Headline | the subsidized channel is **up** — "it worked on its own terms" |
| Tells | **#6 fires hard:** a sibling channel fell ~the same amount → the sibling metric was dropping. #3/#4 family: total volume **~flat** (a wash) |
| Counterfactual | the "new" subsidized activity **was already happening via a cheaper-to-serve channel** → the subsidy relabeled existing volume |
| Effect-modifier | works as *growth* only where the marginal unit is **truly net-new**, not where the subsidy is most attractive to those *already transacting* (who skew to substitution) |
| Verdict | **REDISTRIBUTION / TRAP** → measured: ~0% incremental, margin down (paid to subsidize would-have-happened-anyway activity). |

The lesson that generalizes: **incrementality lives in the counterfactual, not in the persona.** A
demand-side simulation ("would you do more? yes") is structurally blind to *what the activity replaced*;
only pulling the sibling metric from the experiment's own data reveals the substitution.
