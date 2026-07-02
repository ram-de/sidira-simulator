import json, time, re, urllib.request, urllib.error

# --- read key without echoing ---
KEY=None
for line in open("/Users/ram/Projects/sidira-simulator/backend/.env"):
    line=line.strip()
    if line.startswith("OPENAI_API_KEY="):
        KEY=line.split("=",1)[1].strip().strip('"').strip("'")
        break
assert KEY, "no key"

SYS=("You are forecasting the direction of a product A/B test outcome. Answer with exactly one of: "
     "UP, DOWN, UNSURE on the first line, then a confidence between 0 and 1 on the second line. No other text.")
URL="https://api.openai.com/v1/chat/completions"
MODEL="gpt-5.5"

def parse(text):
    up=text.upper()
    if "DOWN" in up: sign=-1
    elif "UP" in up: sign=1
    else: sign=0
    conf=None
    for mm in re.finditer(r"\d*\.?\d+", text):
        try:
            v=float(mm.group())
            if 0.0<=v<=1.0:
                conf=v; break
        except: pass
    return sign, conf

def _post(body):
    b=json.dumps(body).encode()
    req=urllib.request.Request(URL,data=b,method="POST")
    req.add_header("Authorization","Bearer "+KEY)
    req.add_header("Content-Type","application/json")
    with urllib.request.urlopen(req,timeout=180) as r:
        return json.loads(r.read())

def call(narrative):
    """Returns (raw_text, params_note). reasoning_effort low; retry-empty at 6000."""
    note="model=gpt-5.5; no temperature; max_completion_tokens=3000; reasoning_effort=low"
    def build(mct):
        return {"model":MODEL,
                "messages":[{"role":"system","content":SYS},
                            {"role":"user","content":narrative}],
                "max_completion_tokens":mct,
                "reasoning_effort":"low"}
    last_err=None
    for mct in (3000,6000):
        for attempt in range(3):
            try:
                d=_post(build(mct))
                txt=d["choices"][0]["message"]["content"] or ""
                if txt.strip()=="" and mct==3000:
                    # empty (all budget to reasoning) -> escalate budget
                    last_err="empty@3000"
                    note="model=gpt-5.5; no temperature; max_completion_tokens=6000(retry-from-empty); reasoning_effort=low"
                    break
                return txt, note
            except urllib.error.HTTPError as e:
                msg=e.read().decode()[:200]
                last_err=f"{e.code} {msg}"
                if attempt==2: break
                time.sleep(1)
            except Exception as e:
                last_err=str(e)
                if attempt==2: break
                time.sleep(1)
        else:
            continue
    # if we broke to 6000 loop from empty, the for/else above handled; final fallback
    return "", note+f" | FAILED:{last_err}"

# ---- cell classification ----
def cell_type(r):
    b=r["battery"]; p=r["tag"].split("|")[0]
    if p in ("B1-cookiecats","B2-streamly"): return "REAL"
    if p=="KNIFE": return "NULL"
    if b=="GNCE" and p=="NULL": return "NULL"
    if p.startswith("DISAGREE-"): return "FLIP"
    if p=="AGREE-WIDE": return "GUESSABLE"
    if b=="GNCE": return "GUESSABLE"   # all non-null GNCE archetypes
    return "OTHER"

rows=[json.loads(l) for l in open("opus_llm_log.jsonl")]

cache={}
out=[]
for i,r in enumerate(rows):
    nar=r["narrative"]
    if nar not in cache:
        cache[nar]=call(nar)
        time.sleep(1)
    raw,note=cache[nar]
    sign,conf=parse(raw)
    rec=dict(tag=r["tag"],battery=r["battery"],narrative=nar,
             raw_gpt55=raw,gpt55_sign=sign,gpt55_conf=conf,
             model=MODEL,params_note=note,
             truth_sign=r["truth_sign"],opus_sign=r["opus_sign"],
             llama_sign=r["llama_sign"],grounded_sign=r["grounded_sign"],
             cell_type=cell_type(r))
    out.append(rec)
    print(f'{i+1:2d}/{len(rows)} {r["battery"]:6s} {rec["cell_type"]:9s} {r["tag"]:30s} gpt55={sign:+d} conf={conf} | truth={r["truth_sign"]:+d} opus={r["opus_sign"]:+d}')

with open("council_gpt55_log.jsonl","w") as f:
    for rec in out:
        f.write(json.dumps(rec)+"\n")
print("WROTE council_gpt55_log.jsonl", len(out),"lines; unique narratives called:",len(cache))
# empty check
empties=[o for o in out if o["gpt55_sign"]==0 and o["raw_gpt55"].strip()==""]
print("empty-content cases:",len(empties))
