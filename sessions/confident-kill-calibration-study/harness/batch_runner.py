"""Phase 2/3 — run the Sidira engine on Upworthy A/B pairs, checkpointed + resumable.

Encodes each pair as the engine's "current product vs proposed change":
  control headline -> Capability.reverse_prd   (the incumbent)
  treatment headline -> Hypothesis.prose       (the change)
A/B mode (treatment_fraction=0.5) -> result.lift = sign of treatment-vs-control lean.

Records per pair: signal(=lift), confidence_score, sentiment split, plus the
ground truth (true_direction, real_lift signed). Appends to results.csv after each
run; on restart it skips test_ids already present, so the batch is resumable.

Usage:  python batch_runner.py [N]     # N = max pairs this invocation (default all)
"""
from __future__ import annotations
import os, sys, csv, time, asyncio, traceback
from datetime import datetime, timezone

from sidira_simulator.schemas.persona import Persona, PersonaPack, WeightSchemes
from sidira_simulator.schemas.feature_pack import Capability, ReverseFigma
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.simulation_runner import SimulationRunner

SP = "/private/tmp/claude-502/-Users-ram-Projects/8860c7ec-6587-4208-a57e-9662b51767e3/scratchpad"
PAIRS = os.environ.get("SIDIRA_PAIRS", f"{SP}/labeled_pairs.csv")
RESULTS = os.environ.get("SIDIRA_RESULTS", f"{SP}/results.csv")
POP = int(os.environ.get("SIDIRA_POP", "10"))   # per-arm agent target
RUN_SEED = 42

# Fixed general-audience panel — US online-news / social-media readers, the
# audience Upworthy A/B-tested against. Deliberately generic (a pre-partner
# Sidira has no client persona pack); this is the honest baseline population.
_PERSONAS = [
    ("p_commuter", "Busy commuter", "Scrolls a news feed on the phone during a commute; skims headlines fast, taps only what grabs curiosity or emotion in the first few words."),
    ("p_dealhunter", "Practical skeptic", "Wary of clickbait and hype; distrusts over-promising headlines, responds to concrete, specific, credible claims over vague teasers."),
    ("p_activist", "Cause-driven reader", "Cares about social justice, politics, and human-interest stories; shares content that aligns with values and moral outrage or uplift."),
    ("p_parent", "Family-minded parent", "Drawn to stories about kids, health, safety, relationships; emotional, warm framings land; cynical or edgy tones put them off."),
    ("p_entertain", "Entertainment seeker", "Browses for fun, surprise, and novelty; loves 'you won't believe' surprise and humor; bored by dry or worthy-sounding headlines."),
    ("p_news", "Informed news junkie", "Follows current events closely; prefers substance and clear stakes; rewards headlines that signal real news over manipulative curiosity gaps."),
    ("p_young", "Gen-Z scroller", "Fast, meme-fluent, ironic; allergic to try-hard or corporate voice; responds to authenticity, boldness, and cultural relevance."),
    ("p_older", "Older casual reader", "Reads for human interest and inspiration; literal reader, likes clear plain-language headlines, distrusts slangy or cryptic ones."),
    ("p_share", "Social sharer", "Motivated by what makes them look good to friends; shares uplifting, surprising, or identity-affirming stories; headline must be 'share-worthy'."),
    ("p_curious", "Curiosity-driven", "Clicks on knowledge gaps and intriguing setups; loves a good mystery or twist, but rolls eyes at obvious bait that under-delivers."),
]

def _load_personas():
    """Optional richer panel via SIDIRA_PERSONAS_JSON (list of [id,name,description])."""
    pj = os.environ.get("SIDIRA_PERSONAS_JSON")
    if pj and os.path.exists(pj):
        import json
        data = json.load(open(pj))
        print(f"persona panel: {len(data)} rich personas from {os.path.basename(pj)}", flush=True)
        return [tuple(x) for x in data]
    print(f"persona panel: {len(_PERSONAS)} built-in generic personas", flush=True)
    return _PERSONAS

def _pack() -> PersonaPack:
    personas = [Persona(id=i, name=n, description=d) for i, n, d in _load_personas()]
    n = len(personas)
    return PersonaPack(
        version="harness-upworthy-v1", customer_id="harness",
        generated_at=datetime.now(timezone.utc), personas=personas,
        weights=WeightSchemes(head_count={p.id: 1.0 / n for p in personas}),
        stability_score=1.0,
    )

_PACK = _pack()

async def _run_one(treatment: str, control: str, context: str = "") -> dict:
    ctx = f" The story is about: {context}" if context else ""
    cap = Capability(
        name="Headline", surfaces=[], roles=[], entry_points=[],
        reverse_prd=(
            f"A story appears in the reader's social-media feed as a headline they can click."
            f"{ctx} It is currently headlined: {control!r}. Readers scan the feed and click a "
            f"headline only if it grabs them."
        ),
        reverse_figma=ReverseFigma(),
    )
    hyp = Hypothesis(
        capability_name="Headline",
        prose=(
            f"Test an alternative headline for this same story: {treatment!r}. "
            f"Which headline makes this reader more likely to click?"
        ),
    )
    sim = await SimulationRunner().run(
        customer_id="harness", persona_pack=_PACK, capability=cap,
        feature_pack_version="harness-v1", hypothesis=hyp,
        population_size=POP, run_seed=RUN_SEED, max_agents=POP,
        treatment_fraction=0.5,
    )
    r = sim.result
    split = {"positive": 0, "neutral": 0, "negative": 0}
    for a in (r.per_agent_analyses or []):
        split[a.sentiment] = split.get(a.sentiment, 0) + 1
    return {"lift": r.lift, "confidence_score": r.confidence_score,
            "pos": split["positive"], "neu": split["neutral"], "neg": split["negative"]}

FIELDS = ["test_id", "kind", "signal", "confidence_score", "true_direction", "real_lift",
          "z", "pos", "neu", "neg", "treatment_is_winner", "err"]

def _done_ids() -> set:
    if not os.path.exists(RESULTS):
        return set()
    return {row["test_id"] for row in csv.DictReader(open(RESULTS))}

def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10**9
    pairs = list(csv.DictReader(open(PAIRS)))
    done = _done_ids()
    todo = [p for p in pairs if p["test_id"] not in done][:limit]
    print(f"pairs total={len(pairs)} done={len(done)} running_now={len(todo)}", flush=True)
    new_file = not os.path.exists(RESULTS)
    fh = open(RESULTS, "a", newline="")
    w = csv.DictWriter(fh, fieldnames=FIELDS)
    if new_file:
        w.writeheader()
    t0 = time.time()
    for k, p in enumerate(todo, 1):
        tw = p["treatment_is_winner"].strip().lower() == "true"
        ctr_w, ctr_l = float(p["ctr_win"]), float(p["ctr_lose"])
        real_lift = (ctr_w - ctr_l) if tw else (ctr_l - ctr_w)   # signed by assignment
        row = {"test_id": p["test_id"], "kind": p.get("kind", ""),
               "true_direction": p["true_direction"],
               "real_lift": round(real_lift, 6), "z": p["z"],
               "treatment_is_winner": tw, "err": ""}
        try:
            ts = time.time()
            out = asyncio.run(_run_one(p["headline_treatment"], p["headline_control"], p.get("context", "")))
            row.update(signal=out["lift"], confidence_score=out["confidence_score"],
                       pos=out["pos"], neu=out["neu"], neg=out["neg"])
            dt = time.time() - ts
            print(f"[{k}/{len(todo)}] {p['test_id'][:10]} lift={out['lift']} "
                  f"conf={out['confidence_score']} split={out['pos']}/{out['neu']}/{out['neg']} "
                  f"true={p['true_direction']} {dt:.1f}s", flush=True)
        except Exception as e:
            row.update(signal="", confidence_score="", pos="", neu="", neg="", err=repr(e)[:200])
            print(f"[{k}/{len(todo)}] {p['test_id'][:10]} ERROR {e!r}", flush=True)
            traceback.print_exc()
        w.writerow(row); fh.flush()
    fh.close()
    print(f"DONE {len(todo)} runs in {time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    main()
