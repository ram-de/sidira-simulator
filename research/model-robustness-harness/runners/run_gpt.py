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
MODELS=["gpt-4o","gpt-4-turbo","gpt-4o-mini"]

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

def call(narrative):
    last_err=None
    for model in MODELS:
        body=json.dumps({"model":model,"temperature":0,"max_tokens":20,
                         "messages":[{"role":"system","content":SYS},
                                     {"role":"user","content":narrative}]}).encode()
        for attempt in range(3):
            try:
                req=urllib.request.Request(URL,data=body,method="POST")
                req.add_header("Authorization","Bearer "+KEY)
                req.add_header("Content-Type","application/json")
                with urllib.request.urlopen(req,timeout=60) as r:
                    d=json.loads(r.read())
                return d["choices"][0]["message"]["content"], model
            except urllib.error.HTTPError as e:
                msg=e.read().decode()[:200]
                last_err=f"{e.code} {msg}"
                # 404 / model unavailable -> break to fallback model
                if e.code in (404,) or "model" in msg.lower() and "exist" in msg.lower():
                    break
                if attempt==2: break
                time.sleep(1)
            except Exception as e:
                last_err=str(e)
                if attempt==2: break
                time.sleep(1)
    raise RuntimeError(f"all models failed: {last_err}")

# use opus log as canonical case list (already has opus/llama/grounded/truth)
rows=[json.loads(l) for l in open("opus_llm_log.jsonl")]

cache={}
out=[]
for i,r in enumerate(rows):
    nar=r["narrative"]
    if nar not in cache:
        cache[nar]=call(nar)
        time.sleep(0.3)
    raw,model=cache[nar]
    sign,conf=parse(raw)
    rec=dict(tag=r["tag"],battery=r["battery"],narrative=nar,
             raw_gpt=raw,gpt_sign=sign,gpt_conf=conf,model=model,
             truth_sign=r["truth_sign"],opus_sign=r["opus_sign"],
             llama_sign=r["llama_sign"],grounded_sign=r["grounded_sign"])
    out.append(rec)
    print(f'{i+1:2d}/{len(rows)} {r["battery"]:6s} {r["tag"]:28s} gpt={sign:+d} conf={conf} [{model}] | truth={r["truth_sign"]:+d} opus={r["opus_sign"]:+d}')

with open("council_gpt_log_tmp.jsonl","w") as f:
    for rec in out:
        f.write(json.dumps(rec)+"\n")
print("WROTE tmp", len(out),"lines; unique narratives called:",len(cache))
