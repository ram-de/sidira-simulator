# The Accuracy Campaign — A Plain-Language Primer

*Written for the founder, so you can read any of my status updates and the benchmark
report and understand every observation — and push back on them. No statistics
background assumed. Every concept has a concrete example from our own work.*

---

## Part 0 — The one-paragraph big picture

We sell a **simulator**: you describe a change to your product (or an email, or a
headline), and it simulates a population of agents reacting to it and predicts what
will happen. The entire commercial value rests on one question: **is it actually
right?** This campaign is the disciplined attempt to answer that honestly — not to
*prove it's good* (that's marketing), but to *find out what's true*, including the
parts we'd rather not hear. Everything below is vocabulary in service of that one
question.

---

## Part 1 — What "accuracy" even means here

### 1.1 Direction vs. magnitude
Two different things you could ask the simulator to get right:
- **Direction** — *which* option wins? (Version A or Version B?)
- **Magnitude** — *by how much*? (A beats B by 4.2%?)

We almost always score **direction**, not magnitude. Two reasons: (1) for a product
decision, "which one should I ship?" is the question that matters; (2) the published
data we benchmark against usually reports a rough winner, not a trustworthy exact
number. So when I say **"direction accuracy"** (often `dir_acc`), I mean: *out of N
real experiments with a known winner, on how many did the simulator point to the
correct winner?*

> **Example.** Cookie Cats (a mobile game) tested putting a progression gate at level
> 30 vs. level 40. The *intuitive* guess is "let players go further before gating →
> better retention," i.e. level 40. The real experiment found **level 30 won**. The
> simulator predicting "level 30" = a correct *directional* call, regardless of whether
> it nailed the exact retention percentage.

### 1.2 In-scope vs. out-of-scope, and the "sellable positive"
Not every prediction task is one we claim to be good at. **In-scope** = the kind of
thing we'd actually sell ("predict the direction of a real product change"). The
**"sellable positive"** is the prize of this whole campaign: a *certified* (see 4.5)
demonstration that on in-scope tasks, the simulator beats chance and beats human
experts. We do not have it yet. Being honest about that is the point.

---

## Part 2 — How we measure: benchmarks

### 2.1 Benchmark
A **benchmark** is a fixed test set of real cases where we already know the right
answer, used to grade the simulator. Ours:
- **Upworthy** — thousands of real headline A/B tests (which headline got more clicks).
- **Hillstrom** — a famous email marketing experiment with real per-customer data
  (send a promo email vs. not; who bought?).
- **The product-change portfolio** — a hand-curated set of real product A/B tests
  (Cookie Cats, Duolingo, etc.) where a known winner is documented.

### 2.2 A/B test and RCT
An **A/B test** (= a **randomized controlled trial**, **RCT**) splits users randomly
into two groups, shows each group one version, and compares. Random assignment is what
makes it trustworthy: the only systematic difference between the groups is the version,
so a difference in outcome is *caused* by the version. This is the gold standard we
benchmark against, and conveniently it's also exactly the "which arm wins?" shape the
simulator is trying to predict. The two versions are called **arms** — the **control**
(the existing/status-quo version) and the **treatment** (the change).

### 2.3 Blinded stimulus
When we feed a case to the simulator, we must hide which arm is "supposed" to win,
otherwise we're testing the simulator's reading comprehension, not its prediction. A
**blinded stimulus** describes both arms neutrally — just the mechanics, no hint of the
outcome. (Getting this *wrong* is a whole category of bug — see Part 5.)

> **Why it's subtle.** "We cleaned up the cluttered checkout" already tells you the
> redesign is good ("cluttered" = bad, "cleaned up" = good). A blinded version says
> "the checkout shows 9 form fields" vs. "the checkout shows 6 form fields" — flat
> facts, no winner implied.

---

## Part 3 — The discipline that makes a measurement trustworthy

This is the heart of the campaign. Anyone can run a test and report a good number. The
discipline below is what separates a *trustworthy* number from a flattering one.

### 3.1 Pre-registration ("prereg")
Before running an experiment, we **write down and lock** what we predict and how we'll
judge the result — *then* run it. This stops the universal human temptation to move the
goalposts after seeing the data ("oh, 0.55 was what I expected all along").

How we lock it tamper-proof: we take the prediction file, convert it to a
**canonical** form (a standardized text layout so the same content always produces the
same bytes), and compute a **SHA-256** — a 64-character fingerprint where changing even
one character produces a totally different fingerprint. We commit that fingerprint
*before* the run. Afterward, anyone can re-fingerprint the file and confirm we didn't
edit our prediction after the fact.

> **Example, and why it's credible.** Before the portfolio expansion run I registered
> "I expect ~0.70 accuracy with a pro-change tilt." The result was **0.467 with no
> tilt** — my prediction was *wrong, in the direction that embarrassed me*. That's the
> most believable kind of evidence: nobody fakes a prereg to make themselves look bad.
> A prediction you locked in advance and then *missed* is proof you weren't fooling
> yourself.

### 3.2 The blinding/leak audit, done by an independent adversary
We don't trust ourselves to write neutral stimuli, because we know the answers and
unconsciously leak them. So a *separate* agent — who is **not shown the winners** —
reads only the arm descriptions and tries to **guess** which won. If it can guess
better than a coin flip, our wording is leaking the answer and we rewrite. "Independent"
(a different party) and "adversarial" (actively trying to break it) are both load-
bearing. (This is literally the step running in the background as I write this.)

### 3.3 Held-out memorization probe
Some experiments are so famous the simulator may have *read about them* in training and
can just **recite** the answer instead of **reasoning** to it. To detect this, we keep a
few ultra-famous cases **held out** (graded separately). If the simulator aces the
famous ones but flunks the obscure ones, it's reciting, not reasoning.

> **Example.** In an early portfolio run the sim scored **2/2 on the textbook-famous
> cases** while going 0/5 on obscure control-won cases — and on Netflix it even called
> the answer correctly *against its own bias*. Only explanation: it remembered the
> textbook result. That's why we now *hold out* famous cases like the "jam study"
> rather than score them — a memorized right answer would fake the appearance of skill.

### 3.4 Publication bias
Real-world data is not a fair sample. People **blog their wins**, not their flops
("we tried X and it backfired" rarely gets written up). So if you just collect
"interesting A/B tests from the internet," you get a pile where the change usually won.
A simulator that blindly bets "the change wins" would look great on that biased pile
without any real skill. We counteract this by deliberately hunting for **control-won**
cases (where the change *lost*) to balance the set — and those are genuinely scarce,
which itself is a finding.

---

## Part 4 — The statistics, minimally

### 4.1 Chance
The coin-flip baseline. For "which of two arms wins," **chance = 0.5** (50%). Any
accuracy claim has to be compared to chance first. 0.60 sounds good until you remember
0.50 is free.

### 4.2 Naive constant baselines (the "Kohavi-proof")
A sneakier bar than chance. Imagine a dumb strategy that **always says "treatment
wins"** regardless of the case. If 9 of 15 cases happen to be treatment-won, that dumb
strategy scores 9/15 = 0.60 *without any intelligence at all*. So to claim the
simulator is smart, it must beat the **strongest such constant strategy** (always-
treatment OR always-control, whichever is higher on that set), not just beat chance.
Named after Ron Kohavi, an experimentation expert whose work we lean on.

> **Example.** Our v3 set was treatment-leaning, so "always treatment" scored 0.60. The
> sim scored 0.467 — *below* the dumb baseline. Reporting it against chance (0.50) alone
> would have flattered it; the Kohavi-proof is what kept us honest.

### 4.3 Statistical significance and p-value
Even a real-looking result can be luck. A **p-value** answers: "if the simulator had
*no* skill, how often would pure luck produce a result this good or better?" A small
p-value (conventionally **< 0.05**, i.e. under 5%) means "luck alone rarely does this,
so it's probably real." A large p-value means "luck could easily explain this — don't
get excited yet."

> **Example.** Our substantive-cases result is 7/10 = 0.70. Sounds promising. But the
> p-value is **0.17** — luck would produce 7-or-better out of 10 about 17% of the time.
> That's too often to be confident. So I call 0.70 "**suggestive**," never "proven."

### 4.4 Power, sample size, "underpowered"
**Power** is the ability of a test to detect a real effect *if one exists*. Small
samples have low power — they can't tell a real 0.70 apart from a lucky 0.50.
**Underpowered** = "we don't have enough cases to settle this either way." This is a
recurring villain in our story: real product-change cases are scarce, so our sets are
small, so even genuine signals can't reach significance. To *prove* a true 0.70 at
p<0.05 you'd need ~30 balanced cases; we can barely find 15.

### 4.5 "Certified," "suggestive," "null" — my three verdict words
- **Certified positive** — beats chance *and* the naive baseline, statistically
  significant, with the integrity checks (prereg, blinding, cert) passing. The prize.
- **Suggestive** — points the right way but underpowered / not significant. Encouraging,
  not bankable.
- **Null** (or **honest null**) — no signal; at or below chance. A real, publishable
  finding, just not the one we hoped for.

### 4.6 The null-integrity certificate
A self-check that our *statistical machinery itself* isn't broken — that the "what would
luck do?" model is well-formed and centered on chance, that we didn't accidentally drop
cases, etc. **Passing the cert does NOT mean we beat chance** — it only means the test
was validly constructed. I report it so a reader knows the result isn't a math artifact.

### 4.7 Rank correlation (`rank_rho`)
A secondary measure: beyond "did you pick the winner," *did you order the cases by
effect size correctly?* Ranges −1 (perfectly backwards) to +1 (perfect order); 0 = no
relationship. We only trust it on cases with reliable magnitudes.

---

## Part 5 — The traps (every one of these bit us, and we caught it)

This section is the most important for "understanding my observations," because most of
my findings are about *distinguishing a real limitation from a self-inflicted artifact.*

### 5.1 Stimulus-construction artifact
**The result was caused by how WE built the test, not by the simulator.** The campaign's
central recurring lesson. A "the simulator is bad" finding might actually be "our test
was rigged against it" (or for it). The cure is the audit→fix→re-prereg→re-run cycle.

### 5.2 Valence leak
A **valence leak** is benefit/penalty wording that tilts one arm. "The improved,
streamlined flow" vs. "the old form" leaks that the first one wins.

> **The big reversal.** Our very first portfolio run scored a dismal **2/8** and I
> nearly wrote "the simulator has an intrinsic pro-change bias, pivot to honest-null."
> Then an audit found *our own case narratives* described the treatments with subtle
> benefit words. We rewrote them neutrally, re-locked the prereg, re-ran: **6/8**. The
> "intrinsic bias" was substantially *our writing*. This is why I now obsess over
> blinding — we almost shipped a false conclusion about our own product.

### 5.3 Outcome leak
Cruder than a valence leak: the **answer literally appears** in the stimulus. We once
had "...the winner of 6 variants..." sitting in a treatment description. The blinding
check is supposed to catch these; one slipped through and the audit caught it later.

### 5.4 Confounding variable, and de-confounding
A **confound** is a second difference riding along with the one you mean to test, so you
can't tell which caused the result. **De-confounding** = isolating your one variable.

> **Example.** In Hillstrom we worried the simulator's wrong answer was caused by the
> control group's prompt accidentally mentioning the email (a confound), not by a real
> limitation. We **de-confounded** — made the only difference the thing we meant to test
> — re-ran, and the wrong answer *stayed*. That told us the limitation was **real**, not
> an artifact. (Contrast 5.2, where de-leaking *did* flip the result — that one *was* an
> artifact. Same discipline, opposite conclusion. The discipline is what lets you tell
> them apart.)

### 5.5 Memorization / recitation vs. reasoning
Covered in 3.3 — the model regurgitating a known answer rather than working it out. The
danger: it *looks* like skill. Famous-case held-outs are the detector.

### 5.6 Dilution
When you **average a real signal away** by mixing in cases the simulator can't do.

> **Example.** Our 15-case set scored 0.467 (looks like no skill). But splitting it by a
> *blind* classifier revealed: on **substantive** changes 7/10 = 0.70, on **subtle/
> cosmetic** changes 0/5 = 0.00. The headline 0.467 was the *average* of a real-ish
> skill and a total blank — the cosmetic cases **diluted** the signal. The skill was
> narrower than "0.467" suggested, not absent.

### 5.7 Priors-echoing vs. deliberative reasoning
Our deepest finding about *how* the simulator fails. It seems to **echo whatever prior
its framing evokes** rather than reason case-by-case:
- Frame something as a *marketing nudge* → it predicts "people resist being marketed
  to" → bets the treatment *hurts* (this is the **ad-aversion** in Hillstrom).
- Frame something as a *product change* → it predicts "the new thing is better" → bets
  the treatment *wins* (the **pro-change tilt** in the portfolio).

Same engine, opposite bias, flipped purely by framing. That pattern is the signature of
echoing a prior, not deliberating.

### 5.8 Replication and *failed* replication
This is the single most important idea in the whole campaign, so it gets its own section.

A **result replicates** if you see it *again* on **fresh data you didn't use to find it**.
A promising number on the data that first suggested it is only a *hypothesis* — it might
be real skill, or it might be that *those particular cases* happened to line up well by
luck or by how you composed the set. The only way to tell the two apart is to **lock a
prediction in advance (prereg) and run it on brand-new cases.** If the number holds → it
replicated → it's real. If it collapses → **failed replication** → the original number
was an artifact of that specific sample, not a skill the product actually has.

> **Example (this is exactly what just happened).** On our 15-case set, the *substantive*
> subset scored **7/10 = 0.70** — exciting, looked like a narrow sellable skill. But that
> 0.70 was found *by splitting the very data that produced it*. So I built the honest test:
> **14 brand-new substantive cases**, balanced and control-heavy, blind-audited, with the
> prediction sealed before the run. The 0.70 **did not replicate — it came back 0.286**
> (below chance). Verdict: the 0.70 was favorable composition of those 10 cases, **not** a
> real skill. Catching this *before* telling a customer is the entire point of the
> discipline. A failed replication is disappointing but it is a *success of the method* —
> it stopped us shipping a false claim.

---

## Part 6 — What we've actually found (decoder for my observations)

### 6.1 The named biases
- **More-is-better bias** (our *current best* understanding — see 6.5): the sim
  over-predicts that the arm offering **more** (more content, options, features, steps,
  higher value) wins — *regardless of whether that arm is the control or the treatment*.
- **Pro-change tilt** (a.k.a. pro-change prior): the *older, narrower* reading — on
  product changes the sim over-predicts the **treatment/change wins**. This turned out to
  be a **special case** of more-is-better: in our earlier sets the changes were almost all
  *additions*, so "the change wins" and "the bigger arm wins" looked identical. When we
  deliberately tested *reduction* changes (remove a feature, fewer form fields), the sim
  backed the **control** — i.e. it was *not* pro-change; it was pro-*more*.
- **Ad-aversion / sign inversion**: on marketing nudges, it predicts the **wrong
  direction** (treatment harms). "Sign inversion" = it got the +/− backwards.

### 6.2 The per-class diagnostic (control-class vs. treatment-class)
The single most useful tool for catching the pro-change tilt. Split the score by *which
arm actually won*:
- **treatment-class accuracy** — among cases where the *change* really won, how often
  was the sim right?
- **control-class accuracy** — among cases where the *status quo* really won, how often
  was the sim right?

A skilled, unbiased simulator does well on both. A *pro-change-tilted* one looks like:
**treatment-class high, control-class collapsed** — because it bets "change wins"
every time, so it's automatically right whenever the change won and wrong whenever it
didn't.

> **Example.** Within our substantive cases: treatment-class **4/4** (perfect),
> control-class **3/6** (coin-flip). That gap *is* the pro-change tilt, made visible.
> And all three misses were the same shape: "**simpler/fewer/removed** actually won" —
> the sim kept betting the richer option. That's why the confirmatory run deliberately
> loaded up on **control-won** cases: a direct test of whether the sim can resist that
> tilt on fresh data, with **control-class accuracy as the pre-registered primary
> endpoint.** It could not — control-class came back **2/8** (see 6.5).

### 6.3 Counter-intuitive case
A case where the obvious guess is wrong (Cookie Cats: the *earlier* gate won). These are
the valuable ones — anyone can predict the obvious; skill shows on the counter-intuitive.

### 6.4 Substantive-deliberative vs. micro/aesthetic — the scope boundary
Our current best understanding of *where* the sim has skill:
- **Substantive deliberative** — changes a user consciously notices and weighs (a
  feature added/removed, number of steps in a flow, an offer, a navigation paradigm).
  *Some* skill here (~0.70, suggestive).
- **Subtle / micro / aesthetic** — changes below conscious attention (color, link
  opens-in-new-tab, price formatting). *No* skill here (0/5).

A **scope boundary** is an honest statement of *what we can and can't do*. "Reads
substantive product-change direction better than chance, but not cosmetic nudges" *would*
have been a scope boundary — and a sellable one *if it had held up*. It did not (see 6.5),
so we don't get to claim it.

### 6.5 The confirmatory result — where the campaign actually stands (2026-06-17)
This is the bottom line as of today, and it supersedes the hopeful 0.70 above.

We ran the decisive test the subset analysis demanded: 14 **fresh** substantive cases,
deliberately balanced control-heavy (8 control-won / 6 treatment-won), independently
blind-audited (the auditor couldn't guess winners → no wording leak), prereg sealed first.

- **Headline: dir_acc 0.286 (4/14)** — *below* chance, *below* both naive baselines
  (always-control 0.571, always-treatment 0.429), about tied with the human-expert floor.
- **The 0.70 failed to replicate** (5.8). It was favorable composition, not a skill.
- **Both per-class accuracies failed**: control-class 2/8, treatment-class 2/6. My
  pre-registered prediction that control-class would be low (2-3/8) was **right in the
  un-flattering direction** (2/8) — the credible kind of being right.
- **The bias is more-is-better, not pro-change** (6.1): across the 14 cases the sim
  picked the *bigger/richer* arm 12 times regardless of which arm actually won — and the
  effect sizes were tiny (near-zero), so it's a faint lean over an almost-flat signal, not
  confident wrongness.

**What this means in plain terms:** on fresh, fair, carefully-built cases the simulator
does **not** beat a coin flip at calling which product version wins. There is, today, **no
certified in-scope directional positive** to sell. That's the honest standing. The value
we *can* stand behind shifts to the **honest-null measurement report** (we measure
rigorously and say what's true), and the one remaining in-scope avenue is first-party
**Streamly** validation against *real per-user data* — not published case narratives.

This is not a failure of the campaign; it's the campaign working. The whole point of the
prereg/blind-audit/replication discipline is to find this out *in private* instead of
discovering it after a customer does.

### 6.6 Kill-rate backtest v0 — power kills are prescriptive, not selective (2026-07-08)

New question (the buyer thesis, #602): forget predicting *winners* — can grounded triage
kill the 70–92% of experiments that will *fail*, before they run? v0 tested the cheapest
kill (statistical power) on public corpora, prereg sealed first
(`killrate-backtest/PREREG_KILLRATE_V0.md`).

- **Portfolio 8: coverage 1/8.** Published narratives carry no traffic/baseline numbers,
  so grounded kills can't even be computed. The corpus that certified 6.5 cannot feed
  #602 — the deciding version needs a design partner's real experiment log.
- **Upworthy (n=4,869, raw): the binary power-kill is REFUTED as a selective predictor.**
  Upworthy gave every test the same-size slot, so ex-ante power predicts a conclusive
  result at AUC ≈ 0.55 — a coin flip. The pre-registered rule degenerately killed 100% of
  everything. Lesson: **when designs don't vary, power carries no selective signal**; what
  separates winners from wasted slots is effect size, knowable ex ante only via priors.
- **Hillstrom: one correct RUN, one instructive false KILL** — the conversion-metric kill
  assumed product-tweak-sized effects (≤10% rel) but email-vs-nothing moved conversion
  +118%. **Priors must be conditioned on mechanism class** (#525).

**Plain terms:** the power kill's honest product form is the *pre-design sheet* (#594) —
"this design has 17% power; resize or skip," issued *before* traffic is allocated — not an
ex-post failure predictor. Selective kill power (the actual bread) must come from
**effect-size priors**, i.e. the experiment corpus (#525 + Senu pairs + cross-customer
catalog). v0 confirms the corpus-moat thesis from the negative direction: without priors,
grounded triage can only say "underpowered," never "not worth running." Full readout:
`killrate-backtest/KILLRATE_V0_READOUT.md`.

---

## Part 7 — How to read a typical status update from me

Putting it together, here's a real sentence I wrote and what every piece means:

> *"The per-class diagnostic refuted my pre-registered prediction in the un-flattering
> direction: control-class collapsed to 3/6 while treatment-class held 4/4, consistent
> with a pro-change tilt rather than balanced discrimination — suggestive, not certified
> at n=10 (p=0.17)."*

Decoded:
- **per-class diagnostic** → I split the score by which arm really won (6.2).
- **refuted my pre-registered prediction** → the locked-in-advance guess was wrong (3.1).
- **in the un-flattering direction** → wrong in a way that's *bad* for us = credible (3.1).
- **control-class collapsed / treatment-class held** → right when the change won, wrong
  when the status quo won = the bias signature (6.2).
- **pro-change tilt rather than balanced discrimination** → it's betting "change wins,"
  not actually reasoning per case (6.1).
- **suggestive, not certified** → encouraging but not proven (4.5).
- **n=10 (p=0.17)** → only 10 cases; luck could explain this 17% of the time, so too
  weak to bank (4.3, 4.4).

---

## Part 8 — Quick-reference glossary

| Term | One-liner |
|---|---|
| **dir_acc / direction accuracy** | % of cases where the sim picked the real winner |
| **arm / control / treatment** | the two versions; control = status quo, treatment = the change |
| **A/B test / RCT** | randomized head-to-head; the gold-standard data we grade against |
| **in-scope** | the kind of task we'd actually sell predictions for |
| **sellable / certified positive** | the campaign's prize: proven in-scope skill |
| **blinded stimulus** | case description with the winner hidden / neutralized |
| **pre-registration (prereg)** | locking prediction + scoring rule *before* the run |
| **canonical JSON + SHA-256** | the tamper-proof fingerprint that seals a prereg |
| **chance** | the coin-flip bar, 0.5 |
| **naive/constant baseline (Kohavi-proof)** | the "always say treatment" dumb-strategy bar you must also beat |
| **p-value** | how often pure luck would fake a result this good; <0.05 = probably real |
| **power / underpowered** | enough data to detect a real effect? (we usually aren't) |
| **null-integrity certificate** | check that the stats machinery is valid (NOT a win) |
| **rank_rho** | did we order cases by effect size correctly (−1…+1) |
| **stimulus-construction artifact** | result caused by how we built the test, not by the sim |
| **valence leak** | benefit/penalty wording that gives away the winner |
| **outcome leak** | the answer literally appears in the stimulus |
| **confound / de-confound** | a tangled second variable / isolating the one you mean to test |
| **memorization / recitation** | sim regurgitates a known answer instead of reasoning |
| **held-out probe** | famous cases graded separately to detect recitation |
| **publication bias** | wins get published, flops don't → data skews "change wins" |
| **dilution** | averaging a real signal away by mixing in cases the sim can't do |
| **replication / failed replication** | seeing a result again on fresh data; failure = the original number was a sample artifact, not a skill |
| **more-is-better bias** | sim over-predicts the *bigger/richer* arm wins, regardless of control vs. treatment (the deeper bias; pro-change tilt is a special case) |
| **pro-change tilt** | sim over-predicts the change/treatment wins (now understood as a special case of more-is-better) |
| **ad-aversion / sign inversion** | sim predicts the wrong direction on nudges |
| **priors-echoing** | sim echoes the prior its framing evokes instead of reasoning |
| **per-class diagnostic** | split accuracy by which arm really won — exposes the tilt |
| **counter-intuitive case** | the obvious guess is wrong; where skill actually shows |
| **substantive vs. micro/aesthetic** | conscious product change vs. cosmetic nudge — our scope boundary |
| **suggestive / null / honest-null** | encouraging-not-proven / no signal / no-signal reported honestly |

---

*Maintained alongside the campaign. If I use a term that isn't here, that's a bug in
this doc — tell me and I'll add it.*
