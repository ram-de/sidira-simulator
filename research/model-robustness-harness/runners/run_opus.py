import json, time, re, urllib.request, urllib.error
from build_cases import build

# --- read key without echoing ---
KEY=None
for line in open("/Users/ram/Projects/sidira-simulator/backend/.env"):
    line=line.strip()
    if line.startswith("ANTHROPIC_API_KEY="):
        KEY=line.split("=",1)[1].strip().strip('"').strip("'")
        break
assert KEY, "no key"

SYS=("You are forecasting the direction of a product A/B test outcome. Answer with exactly one of: "
     "UP, DOWN, UNSURE on the first line, then a confidence between 0 and 1 on the second line. No other text.")
URL="https://api.anthropic.com/v1/messages"

def parse(text):
    up=text.upper()
    if "DOWN" in up: sign=-1
    elif "UP" in up: sign=1
    else: sign=0
    m=re.search(r"(?<![\d.])(0?\.\d+|1(?:\.0+)?|0)(?![\d])", text)
    conf=None
    for mm in re.finditer(r"\d*\.?\d+", text):
        try:
            v=float(mm.group())
            if 0.0<=v<=1.0:
                conf=v; break
        except: pass
    return sign, conf

def call(narrative):
    body=json.dumps({"model":"claude-opus-4-8","max_tokens":20,
                     "system":SYS,"messages":[{"role":"user","content":narrative}]}).encode()
    req=urllib.request.Request(URL,data=body,method="POST")
    req.add_header("x-api-key",KEY)
    req.add_header("anthropic-version","2023-06-01")
    req.add_header("content-type","application/json")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=60) as r:
                d=json.loads(r.read())
            return "".join(b.get("text","") for b in d["content"] if b.get("type")=="text")
        except Exception as e:
            if attempt==2: raise
            time.sleep(1)

cases=build()
cache={}
out=[]
for i,c in enumerate(cases):
    nar=c["narrative"]
    if nar not in cache:
        raw=call(nar)
        cache[nar]=raw
        time.sleep(0.3)
    else:
        raw=cache[nar]
    sign,conf=parse(raw)
    rec=dict(tag=c["tag"],battery=c["battery"],narrative=nar,raw_opus=raw,
             opus_sign=sign,opus_conf=conf,truth_sign=c["truth_sign"],
             llama_sign=c["llama_sign"],grounded_sign=c["grounded_sign"])
    out.append(rec)
    print(f'{i+1:2d}/{len(cases)} {c["battery"]:6s} {c["tag"]:28s} opus={sign:+d} conf={conf} | truth={c["truth_sign"]:+d} llama={c["llama_sign"]:+d} grd={c["grounded_sign"]:+d}')

with open("opus_llm_log.jsonl","w") as f:
    for r in out:
        f.write(json.dumps(r)+"\n")
print("WROTE opus_llm_log.jsonl", len(out),"lines; unique narratives called:",len(cache))
