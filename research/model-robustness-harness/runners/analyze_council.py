import json
from collections import Counter

rows=[json.loads(l) for l in open("council_gpt55_log.jsonl")]

def name(s): return "UP" if s==1 else "DOWN" if s==-1 else "UNSURE"

# slices
by_cell=lambda ct:[r for r in rows if r["cell_type"]==ct]
FLIP=by_cell("FLIP")
GUESS=by_cell("GUESSABLE")
NULLc=by_cell("NULL")
REAL=by_cell("REAL")
scored=[r for r in rows if r["truth_sign"]!=0]           # null excluded
amb=[r for r in rows if r["battery"]=="AMBDOM"]
gnce=[r for r in rows if r["battery"]=="GNCE"]
cleanflip=[r for r in rows if r["tag"].startswith("DISAGREE-WIDE") or r["tag"].startswith("DISAGREE-NARROW")]

def tally(rs,key):
    return dict(Counter(name(r[key]) for r in rs))

def acc(rs,key):
    nn=[r for r in rs if r["truth_sign"]!=0]
    c=sum(1 for r in nn if r[key]==r["truth_sign"])
    return c,len(nn),(c/len(nn) if nn else float('nan'))

print("### Part 1 — gpt-5.5 SOLO")
print("\n[1] BIAS TALLY")
for lbl,rs in [("AMBDOM(38)",amb),("GNCE(21)",gnce),("TOTAL(59)",rows)]:
    print(f'  {lbl:12s} gpt55={tally(rs,"gpt55_sign")}  opus={tally(rs,"opus_sign")}  llama={tally(rs,"llama_sign")}')

print("\n[2] DIRECTIONAL ACCURACY (null excluded)")
for lbl,rs in [("OVERALL",scored),("AMBDOM",amb),("GNCE",gnce),
               ("clean FLIP (WIDE+NARROW, n=12)",cleanflip),
               ("all FLIP (24)",FLIP),("GUESSABLE (24)",GUESS),("REAL (2)",REAL)]:
    g=acc(rs,"gpt55_sign");o=acc(rs,"opus_sign");l=acc(rs,"llama_sign");gr=acc(rs,"grounded_sign")
    print(f'  {lbl:32s} gpt55 {g[0]}/{g[1]}={g[2]:.2f} | opus {o[2]:.2f} | llama {l[2]:.2f} | grounded {gr[2]:.2f}')

# abstention on scored cells
abst=sum(1 for r in scored if r["gpt55_sign"]==0)
print(f'\n  gpt55 abstain(UNSURE) on scored cells: {abst}/{len(scored)}')
abst_flip=sum(1 for r in FLIP if r["gpt55_sign"]==0)
print(f'  gpt55 abstain on FLIP cells: {abst_flip}/{len(FLIP)}')

print("\n### Part 2 — gpt-5.5 + Opus COUNCIL")
def agree(r): return r["gpt55_sign"]==r["opus_sign"]

print("\n[4] AGREEMENT STRUCTURE (gpt55 vs opus)")
for lbl,rs in [("FLIP (24)",FLIP),("clean FLIP (12)",cleanflip),("GUESSABLE (24)",GUESS),
               ("NULL (9)",NULLc),("REAL (2)",REAL)]:
    ag=sum(1 for r in rs if agree(r)); n=len(rs)
    print(f'  {lbl:16s} agree={ag}/{n}={ag/n:.2f}  disagree={n-ag}/{n}={(n-ag)/n:.2f}')

print("\n[5] FALSE-CONFIDENCE: among FLIP cells where gpt55==opus, is the agreed sign right?")
ag_flip=[r for r in FLIP if agree(r)]
c=sum(1 for r in ag_flip if r["opus_sign"]==r["truth_sign"])
print(f'  agreed FLIP cells: {len(ag_flip)}; agreed-sign correct: {c}/{len(ag_flip) if ag_flip else 0}')

print("\n[6] ABSTAIN-GATE  (abstain when gpt55!=opus; else take agreed sign)")
kept=[r for r in scored if agree(r)]
kc=sum(1 for r in kept if r["opus_sign"]==r["truth_sign"])
print(f'  KEPT set (scored, agree): {len(kept)} cases; accuracy {kc}/{len(kept)}={kc/len(kept):.2f}')
print(f'  baseline gpt55 solo (scored): {acc(scored,"gpt55_sign")[2]:.2f}; opus solo: {acc(scored,"opus_sign")[2]:.2f}')
# flip abstained
flip_abst=sum(1 for r in FLIP if not agree(r))
print(f'  FLIP cells correctly ABSTAINED (disagree): {flip_abst}/{len(FLIP)}={flip_abst/len(FLIP):.2f}')
gu_keptright=sum(1 for r in GUESS if agree(r) and r["opus_sign"]==r["truth_sign"] and r["truth_sign"]!=0)
gu_nn=[r for r in GUESS if r["truth_sign"]!=0]
print(f'  GUESSABLE kept-and-right: {gu_keptright}/{len(gu_nn)}={gu_keptright/len(gu_nn):.2f}')
# grounded on the abstained/flip cells
gr_flip=acc(FLIP,"grounded_sign")
print(f'  grounded-sim on FLIP cells (what gate throws away): {gr_flip[0]}/{gr_flip[1]}={gr_flip[2]:.2f}')

print("\n[7] 3-WAY (add llama). flip-flag = not all of {gpt55,opus,llama} equal")
def all3_agree(r): return r["gpt55_sign"]==r["opus_sign"]==r["llama_sign"]
for lbl,rs in [("FLIP (24)",FLIP),("clean FLIP (12)",cleanflip),("GUESSABLE (24)",GUESS)]:
    f2=sum(1 for r in rs if not agree(r))            # 2-model flag
    f3=sum(1 for r in rs if not all3_agree(r))       # 3-model flag
    print(f'  {lbl:16s} 2-model flag(disagree)={f2}/{len(rs)}={f2/len(rs):.2f}  3-model flag={f3}/{len(rs)}={f3/len(rs):.2f}')
# 3-way gate: keep only when all3 agree
kept3=[r for r in scored if all3_agree(r)]
kc3=sum(1 for r in kept3 if r["gpt55_sign"]==r["truth_sign"])
print(f'  3-way KEPT set: {len(kept3)} cases; accuracy {kc3}/{len(kept3) if kept3 else 0}'+(f'={kc3/len(kept3):.2f}' if kept3 else ''))
