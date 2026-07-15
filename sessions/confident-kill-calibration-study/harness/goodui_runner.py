"""GoodUI reverse-PRD experiment — the untested lever.

Each row is a REAL product/UI A/B test (GoodUI, power>=80%): a change to a screen,
with a real measured outcome (effect sign = did the change win or lose).

Encoded into the engine's DESIGNED machinery (unlike bare Upworthy headlines):
  reverse_prd     = the product context (which screen, what metric, current baseline)
  hypothesis.prose = the proposed change (the GoodUI change description)
A/B mode -> lift = engine's predicted direction of the change vs the current design.

Truth = sign(real effect). Measures: (1) does real product context beat the headline
floor? (2) can the engine confidently KILL the real losers without killing winners?

Checkpointed + resumable to results_goodui.csv.
"""
from __future__ import annotations
import os, sys, csv, time, asyncio, traceback
from datetime import datetime, timezone

from sidira_simulator.schemas.persona import Persona, PersonaPack, WeightSchemes
from sidira_simulator.schemas.feature_pack import Capability, ReverseFigma
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.simulation_runner import SimulationRunner

SP = "/private/tmp/claude-502/-Users-ram-Projects/8860c7ec-6587-4208-a57e-9662b51767e3/scratchpad"
PAIRS = f"{SP}/labeled_pairs_goodui.csv"
RESULTS = f"{SP}/results_goodui.csv"
POP = 10
RUN_SEED = 42

# E-commerce shopper panel — the audience GoodUI tests actually ran against.
_PERSONAS = [
    ("s_bargain", "Bargain hunter", "Shops online for the best deal; compares prices, hunts discounts and free shipping; abandons carts over unexpected costs; motivated by savings and urgency."),
    ("s_busy", "Time-pressed buyer", "Wants to buy fast with minimal friction; values speed, clear CTAs, saved details, few steps; frustrated by extra clicks, forms, or interruptions."),
    ("s_cautious", "Cautious first-timer", "New to the site, wary of trust; reassured by reviews, guarantees, security cues, clear return policy; hesitates without social proof or clarity."),
    ("s_researcher", "Thorough researcher", "Reads specs, reviews, and comparisons before buying; wants detailed product info, photos, and options; annoyed by hype or missing detail."),
    ("s_mobile", "Mobile scroller", "Shops on phone in short bursts; needs thumb-friendly layout, fast load, sticky buttons; drops off on cramped forms, tiny targets, or clutter."),
    ("s_loyal", "Returning loyalist", "Familiar repeat customer; values remembered preferences, quick reorder, recently-viewed; irritated when a redesign moves things or adds steps."),
    ("s_impulse", "Impulse buyer", "Buys on emotion and novelty; responds to imagery, scarcity, recommendations, and a frictionless path to purchase; distracted by anything slow."),
    ("s_skeptic", "Value skeptic", "Distrusts marketing pressure; put off by aggressive popups, forced actions, fake urgency; rewards honest, clear, low-pressure design."),
    ("s_deliberate", "Deliberate planner", "Plans purchases, uses cart as a shortlist, weighs options over sessions; values wishlists, saved carts, clear pricing; dislikes pressure to decide now."),
    ("s_gift", "Gift shopper", "Buying for someone else, unsure of exact needs; leans on categories, guides, recommendations, easy returns; wants reassurance the choice is safe."),
]

def _pack() -> PersonaPack:
    ps = [Persona(id=i, name=n, description=d) for i, n, d in _PERSONAS]
    return PersonaPack(version="goodui-shopper-v1", customer_id="harness",
        generated_at=datetime.now(timezone.utc), personas=ps,
        weights=WeightSchemes(head_count={p.id: 1.0/len(ps) for p in ps}), stability_score=1.0)

_PACK = _pack()

async def _run_one(change: str, screen: str, metric: str) -> dict:
    cap = Capability(
        name=f"{screen} screen", surfaces=[], roles=[], entry_points=[],
        reverse_prd=(
            f"This is the {screen} screen of an online store's website. The team optimizes "
            f"it for {metric}. The current design is the established baseline that shoppers "
            f"see today and are used to."
        ),
        reverse_figma=ReverseFigma(),
    )
    hyp = Hypothesis(
        capability_name=f"{screen} screen",
        prose=(
            f"The product team is considering this change to the {screen} screen: {change} "
            f"Would this change improve {metric} versus the current design, or hurt it?"
        ),
    )
    sim = await SimulationRunner().run(
        customer_id="harness", persona_pack=_PACK, capability=cap,
        feature_pack_version="goodui-v1", hypothesis=hyp,
        population_size=POP, run_seed=RUN_SEED, max_agents=POP, treatment_fraction=0.5,
    )
    r = sim.result
    split = {"positive": 0, "neutral": 0, "negative": 0}
    for a in (r.per_agent_analyses or []):
        split[a.sentiment] = split.get(a.sentiment, 0) + 1
    return {"lift": r.lift, "confidence_score": r.confidence_score,
            "pos": split["positive"], "neu": split["neutral"], "neg": split["negative"]}

FIELDS = ["test_id", "signal", "confidence_score", "true_direction", "effect",
          "metric", "screen", "power", "pos", "neu", "neg", "err"]

def _done():
    if not os.path.exists(RESULTS): return set()
    return {r["test_id"] for r in csv.DictReader(open(RESULTS))}

def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10**9
    pairs = list(csv.DictReader(open(PAIRS)))
    done = _done()
    todo = [p for p in pairs if p["test_id"] not in done][:limit]
    print(f"total={len(pairs)} done={len(done)} running={len(todo)}", flush=True)
    new = not os.path.exists(RESULTS)
    fh = open(RESULTS, "a", newline=""); w = csv.DictWriter(fh, fieldnames=FIELDS)
    if new: w.writeheader()
    t0 = time.time()
    for k, p in enumerate(todo, 1):
        row = {"test_id": p["test_id"], "true_direction": p["true_direction"],
               "effect": p["effect"], "metric": p["metric"], "screen": p["screen"],
               "power": p["power"], "err": ""}
        try:
            out = asyncio.run(_run_one(p["change"], p["screen"], p["metric"]))
            row.update(signal=out["lift"], confidence_score=out["confidence_score"],
                       pos=out["pos"], neu=out["neu"], neg=out["neg"])
            print(f"[{k}/{len(todo)}] {p['test_id']} lift={out['lift']} true={p['true_direction']} "
                  f"eff={p['effect']} split={out['pos']}/{out['neu']}/{out['neg']}", flush=True)
        except Exception as e:
            row.update(signal="", confidence_score="", pos="", neu="", neg="", err=repr(e)[:200])
            print(f"[{k}/{len(todo)}] {p['test_id']} ERROR {e!r}", flush=True); traceback.print_exc()
        w.writerow(row); fh.flush()
    fh.close(); print(f"DONE {len(todo)} in {time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    main()
