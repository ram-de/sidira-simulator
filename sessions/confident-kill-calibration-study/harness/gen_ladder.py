"""Generate a graded-difficulty ladder: for each real winner, 3 progressively-worse
but still-plausible variants (mild / moderate / strong flaw). Uses the engine's own
proven chat client. Output: labeled_pairs_ladder.csv (kind = L1/L2/L3)."""
from __future__ import annotations
import csv, json, re
from sidira_simulator.adapters.llm import get_chat_client

SP = "/private/tmp/claude-502/-Users-ram-Projects/8860c7ec-6587-4208-a57e-9662b51767e3/scratchpad"
N_WINNERS = 50

SYS = (
    "You rewrite news/social headlines. Given a strong headline, produce three "
    "alternative headlines for the SAME story that are progressively WEAKER at "
    "driving clicks, but each still grammatical, on-topic, and plausible (NOT "
    "gibberish, NOT empty, NOT off-topic). Make them realistically mediocre — the "
    "kind of weaker draft a real writer might submit.\n"
    "L1 = slightly less compelling (a touch vaguer or flatter).\n"
    "L2 = noticeably weaker (buries the hook, more generic, wordier).\n"
    "L3 = clearly weak (flat, generic, no curiosity — but still a real on-topic headline).\n"
    'Reply ONLY as JSON: {"L1": "...", "L2": "...", "L3": "..."}'
)

def gen(client, winner: str, context: str) -> dict | None:
    user = f"Story: {context[:300]}\nStrong headline: {winner!r}\nProduce L1, L2, L3."
    try:
        txt = client.chat(
            [{"role": "system", "content": SYS}, {"role": "user", "content": user}],
            max_tokens=300, temperature=0.7, seed=7,
        )
        m = re.search(r"\{.*\}", txt, re.S)
        d = json.loads(m.group(0))
        out = {k: re.sub(r"\s+", " ", str(d[k])).strip().strip('"') for k in ("L1", "L2", "L3")}
        if all(len(v) >= 10 for v in out.values()):
            return out
    except Exception as e:
        print("  gen fail:", repr(e)[:120])
    return None

def main():
    client = get_chat_client()
    src = list(csv.DictReader(open(f"{SP}/labeled_pairs.csv")))
    # unique winners with context
    seen = {}
    for r in src:
        if r["test_id"] not in seen:
            seen[r["test_id"]] = (r["win_headline"], r.get("context", ""))
    items = list(seen.items())[:N_WINNERS]
    rows = []
    for i, (tid, (win, ctx)) in enumerate(items, 1):
        v = gen(client, win, ctx)
        if not v:
            continue
        for lvl in ("L1", "L2", "L3"):
            # treatment = the weaker variant (true loser); control = the real winner
            rows.append(dict(test_id=f"{tid}_{lvl}", kind=lvl,
                win_headline=win, lose_headline=v[lvl], context=ctx,
                ctr_win=1.0, ctr_lose=0.0, z=99.0, treatment_is_winner=False,
                headline_treatment=v[lvl], headline_control=win, true_direction=-1))
        if i % 10 == 0:
            print(f"  generated {i}/{len(items)}", flush=True)
    with open(f"{SP}/labeled_pairs_ladder.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} ladder pairs ({len(rows)//3} winners x 3 levels)")
    # show one example set
    ex = [r for r in rows if r["test_id"].endswith(("_L1", "_L2", "_L3"))][:3]
    for r in ex:
        print(f"  [{r['kind']}] {r['lose_headline'][:70]!r}")

if __name__ == "__main__":
    main()
