# Competitive read — Artificial Societies (societies.io)

*Best-funded player in LLM-persona audience simulation. Their public record strengthens our thesis
and leaves the counter-intuitive/causal/generalization niche open.*

## Who
Founded 2024, James He (ex-Cambridge comp-social-science; first large-scale LLM-society paper) +
Patrick Sharpe. YC W25, ~$5.35M seed (Point72). Inspired by Stanford "Generative Agent Simulations
of 1,000 People" (arxiv 2411.10109).

## What they do
Draft a message/post/ad → multi-agent sim (300–5,000+ interconnected personas) reacts + influences
each other → score + messaging insights. Customers = marketers/comms/creatives. The job is **"will
this message resonate / spread"** — almost entirely **LinkedIn/X post engagement.**

## Their actual technical bets
1. **Per-individual grounding** — personas built from real people's public profiles (LinkedIn/X) +
   web deep-research, not demographic stereotypes. DB claims "2.5M real persona profiles."
2. **Social-influence GRAPH + multi-agent interaction** — personas react to each other (conformity,
   spread). Their best real-world predictor turned out to be *simulated message-spread*, so the graph
   is load-bearing for their use case.
3. **Per-persona "internally coherent belief system"** (consistency across hundreds of questions).
4. **Calibration vs human test-retest reliability**, with an explicit anti-overfitting ceiling (~95%).

## Their accuracy claims — all self-reported
- **R²=0.78** predicting LinkedIn post performance; **"80%+"** vs out-of-box LLM baselines (Sonnet 3.7
  67% / Gemini 64% / GPT-4o 60%); "95% of human self-replication level."
- **No independent held-out benchmark found.** Benchmarks are against *survey test-retest noise* and
  *deliberately weak LLM baselines*, not purpose-built engagement models or real campaign outcomes.
- HN commenters pressed for **simulated-vs-actual campaign pairs** and the definition of the outcome
  variable (likes? reposts?) → **unanswered.** A Director of Market Research tested two email headlines
  — one he knows works (scored 88 "Exceptional") and one he's sure does NOT (scored 81 "Very high") —
  and asked what they do about false positives → **no answer.** Strong signal the tool **scores almost
  everything highly** (the same fake-confidence we saw: 30 identical persona votes).
- Founder, candidly: accuracy is their #1 challenge, "still early days… across all contexts."

## The key insight for us
**Their entire accuracy story is on the intuition-ALIGNED, self-fulfilling task** (a punchy post reads
as punchy to humans and LLMs alike). That is the *opposite* of our problem — **counter-intuitive
product-change A/B outcomes where the winning variant looks worse to intuition** (grocery trade-down,
membership frequency-vs-promo). Their R²=0.78 on engagement says nothing about calling a counter-intuitive
change; the false-positive anecdote suggests they'd fail it the same way our personas do (at chance).

## Borrow / Ignore
**Borrow:**
- **Per-individual grounding over stereotypes** (matches our empirical-grounding pivot).
- **Empirically select a calibrated readout metric** — their win was discovering *spread* (not sentiment)
  tracks the outcome. Same spirit as our "read metric alongside sentiment, never alone" + the #222 calibrator.
- **Human test-retest reliability as an honest accuracy ceiling** for anything we publish.
- **Their gap is our discipline:** demand simulated-vs-actual pairs. Our sealed blind tests + real
  product-change portfolio scored on DIRECTION is *stronger* methodology than anything they've shown.

**Ignore (off-target for A/B direction):**
- **The social-influence graph** — helps virality/contagion, largely irrelevant to retention/conversion/
  pricing mechanisms, which are individual-utility effects, not peer cascades. Don't import it expecting
  it to fix causal A/B prediction.
- **The engagement-accuracy framing** — wrong task; it rewards intuition-matching.
- They have **no causal/uplift machinery and no negative-control / external-validity layer** — exactly
  our wedge. Their model "tracks intuition," the failure mode we already diagnosed in our own engine.

## Net positioning
The best-funded competitor validates only on the easy, intuition-aligned task and ducks the
simulated-vs-actual and false-positive questions. That **vacates** the hard, valuable ground:
counter-intuitive direction calls, causal grounding, and **generalization/external-validity auditing
of real test wins** — which is where our three sealed cases + the ALDI audit already operate.
